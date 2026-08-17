from __future__ import annotations

from collections.abc import Mapping
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.services.app_check_service as app_check_service
from backend.firebase_admin_client import FirebaseAppCheckUnavailableError
from backend.observability.timeouts import DependencyReadTimeoutError
from backend.services.app_check_middleware import (
    APP_CHECK_INVALID_CODE,
    APP_CHECK_REQUIRED_CODE,
    APP_CHECK_UNAVAILABLE_CODE,
    AppCheckEvent,
    AppCheckMiddleware,
)
from backend.services.app_check_policy import build_app_check_route_policy
from backend.services.app_check_service import (
    APP_CHECK_HEADER_NAME,
    AppCheckVerificationOutcome,
    AppCheckVerificationResult,
    verify_app_check_token,
)
from backend.settings import build_settings

pytestmark = [pytest.mark.no_db_cleanup, pytest.mark.suite_type("ordinary")]

TEST_DATABASE_URL = "postgresql+psycopg://db.example.invalid:5432/pickup_lane_test_db"
SUPPORTED_APP_ID = "1:123456789:web:supported"
OTHER_APP_ID = "1:123456789:web:other"
ALLOWED_ORIGIN = "https://app.example.invalid"


def _settings(mode: str = "enforced"):
    return build_settings(
        {
            "APP_ENV": "test",
            "DATABASE_URL": TEST_DATABASE_URL,
            "INBOX_TOKEN_SECRET": "synthetic-independent-app-check-token",
            "ALLOWED_HOSTS": "testserver,api.example.invalid",
            "CORS_ALLOWED_ORIGINS": ALLOWED_ORIGIN,
            "ENABLE_API_DOCS": "true",
            "ENABLE_DB_HEALTH": "false",
            "ENABLE_STRIPE_PAYMENTS": "false",
            "FIREBASE_APP_CHECK_MODE": mode,
            "FIREBASE_APP_CHECK_APP_ID": SUPPORTED_APP_ID,
        },
        load_dotenv_file=False,
        validate_full=True,
    )


def _workflow_app(
    *,
    mode: str,
    verifier,
    recorder=None,
) -> tuple[FastAPI, list[str], list[AppCheckEvent]]:
    app = FastAPI()
    side_effects: list[str] = []
    recorded: list[AppCheckEvent] = []

    @app.post("/games", tags=["games"])
    def create_game():
        side_effects.append("executed")
        return {"ok": True}

    def capture(event: AppCheckEvent, _settings) -> None:
        recorded.append(event)

    app.add_middleware(
        AppCheckMiddleware,
        settings=_settings(mode),
        route_policy=build_app_check_route_policy(app),
        verifier=verifier,
        event_recorder=recorder or capture,
    )
    return app, side_effects, recorded


def _fixed_verifier(outcome: AppCheckVerificationOutcome):
    def verifier(_headers, _settings):
        return AppCheckVerificationResult(outcome)

    return verifier


@pytest.mark.requirement("WS03-03B-R3", "WS03-03B-R6")
def test_verifier_accepts_only_provider_verified_expected_app_id(monkeypatch) -> None:
    monkeypatch.setattr(
        app_check_service,
        "verify_firebase_app_check_token",
        lambda token: {"app_id": SUPPORTED_APP_ID},
    )
    settings = SimpleNamespace(firebase_app_check_app_id=SUPPORTED_APP_ID)

    result = verify_app_check_token({APP_CHECK_HEADER_NAME: "provider-token"}, settings)

    assert result.outcome is AppCheckVerificationOutcome.VALID


@pytest.mark.requirement("WS03-03B-R3", "WS03-03B-R6")
def test_verifier_rejects_provider_valid_wrong_app_id(monkeypatch) -> None:
    monkeypatch.setattr(
        app_check_service,
        "verify_firebase_app_check_token",
        lambda token: {"app_id": OTHER_APP_ID},
    )
    settings = SimpleNamespace(firebase_app_check_app_id=SUPPORTED_APP_ID)

    result = verify_app_check_token({APP_CHECK_HEADER_NAME: "provider-token"}, settings)

    assert result.outcome is AppCheckVerificationOutcome.INVALID


@pytest.mark.requirement("WS03-03B-R3")
@pytest.mark.parametrize(
    ("headers", "expected"),
    [
        ({}, AppCheckVerificationOutcome.MISSING),
        ({APP_CHECK_HEADER_NAME: "   "}, AppCheckVerificationOutcome.MISSING),
        ({"x-firebase-appcheck": "provider-token"}, AppCheckVerificationOutcome.VALID),
    ],
)
def test_verifier_reads_only_the_dedicated_header_case_insensitively(
    monkeypatch,
    headers: Mapping[str, str],
    expected: AppCheckVerificationOutcome,
) -> None:
    monkeypatch.setattr(
        app_check_service,
        "verify_firebase_app_check_token",
        lambda token: {"app_id": SUPPORTED_APP_ID},
    )
    settings = SimpleNamespace(firebase_app_check_app_id=SUPPORTED_APP_ID)

    result = verify_app_check_token(headers, settings)

    assert result.outcome is expected


@pytest.mark.requirement("WS03-03B-R3", "WS03-03B-R4")
def test_verifier_classifies_provider_rejection_and_unavailable_boundaries(
    monkeypatch,
) -> None:
    settings = SimpleNamespace(firebase_app_check_app_id=SUPPORTED_APP_ID)

    def reject(_token):
        raise ValueError("provider rejected synthetic token")

    monkeypatch.setattr(app_check_service, "verify_firebase_app_check_token", reject)
    invalid = verify_app_check_token({APP_CHECK_HEADER_NAME: "bad"}, settings)

    def unavailable(_token):
        raise FirebaseAppCheckUnavailableError("provider boundary unavailable")

    monkeypatch.setattr(app_check_service, "verify_firebase_app_check_token", unavailable)
    unavailable_result = verify_app_check_token({APP_CHECK_HEADER_NAME: "ok"}, settings)

    def timeout(_token):
        raise DependencyReadTimeoutError(
            provider_kind="firebase",
            operation="firebase.app_check.verify",
        )

    monkeypatch.setattr(app_check_service, "verify_firebase_app_check_token", timeout)
    timeout_result = verify_app_check_token({APP_CHECK_HEADER_NAME: "ok"}, settings)

    assert invalid.outcome is AppCheckVerificationOutcome.INVALID
    assert unavailable_result.outcome is AppCheckVerificationOutcome.PROVIDER_UNAVAILABLE
    assert timeout_result.outcome is AppCheckVerificationOutcome.PROVIDER_UNAVAILABLE


@pytest.mark.requirement("WS03-03B-R4", "WS03-03B-R6")
def test_disabled_mode_is_inert_and_does_not_call_verifier() -> None:
    def verifier(_headers, _settings):
        raise AssertionError("disabled App Check must not verify")

    app, side_effects, recorded = _workflow_app(
        mode="disabled",
        verifier=verifier,
    )

    with TestClient(app) as client:
        response = client.post("/games")

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert side_effects == ["executed"]
    assert recorded == []


@pytest.mark.requirement("WS03-03B-R4", "WS03-03B-R5", "WS03-03B-R6")
def test_observe_mode_records_bounded_outcome_and_preserves_route_behavior() -> None:
    app, side_effects, recorded = _workflow_app(
        mode="observe",
        verifier=_fixed_verifier(AppCheckVerificationOutcome.INVALID),
    )

    with TestClient(app) as client:
        response = client.post("/games")

    assert response.status_code == 200
    assert side_effects == ["executed"]
    assert len(recorded) == 1
    assert recorded[0].operation == "app_check.observe"
    assert recorded[0].outcome is AppCheckVerificationOutcome.INVALID
    assert recorded[0].route_template == "/games"
    assert recorded[0].route_family == "api.games"
    assert recorded[0].stable_error_code == APP_CHECK_INVALID_CODE


@pytest.mark.requirement("WS03-03B-R3", "WS03-03B-R4", "WS03-03B-R6")
@pytest.mark.parametrize(
    ("outcome", "status_code", "error_code", "message"),
    [
        (
            AppCheckVerificationOutcome.MISSING,
            403,
            APP_CHECK_REQUIRED_CODE,
            "App verification required.",
        ),
        (
            AppCheckVerificationOutcome.INVALID,
            403,
            APP_CHECK_INVALID_CODE,
            "App verification failed.",
        ),
        (
            AppCheckVerificationOutcome.PROVIDER_UNAVAILABLE,
            503,
            APP_CHECK_UNAVAILABLE_CODE,
            "App verification is unavailable.",
        ),
    ],
)
def test_enforced_mode_denies_before_endpoint_side_effects_with_safe_public_errors(
    outcome: AppCheckVerificationOutcome,
    status_code: int,
    error_code: str,
    message: str,
) -> None:
    app, side_effects, recorded = _workflow_app(
        mode="enforced",
        verifier=_fixed_verifier(outcome),
    )

    with TestClient(app) as client:
        response = client.post("/games")

    assert response.status_code == status_code
    assert response.json()["code"] == error_code
    assert response.json()["message"] == message
    assert response.json()["detail"] == message
    assert response.headers["X-Request-ID"] == response.json()["correlation_id"]
    assert side_effects == []
    assert len(recorded) == 1
    assert recorded[0].operation == "app_check.enforce"
    assert recorded[0].outcome is outcome


@pytest.mark.requirement("WS03-03B-R4", "WS03-03B-R6")
def test_enforced_valid_outcome_continues_to_endpoint_and_records_event() -> None:
    app, side_effects, recorded = _workflow_app(
        mode="enforced",
        verifier=_fixed_verifier(AppCheckVerificationOutcome.VALID),
    )

    with TestClient(app) as client:
        response = client.post("/games")

    assert response.status_code == 200
    assert side_effects == ["executed"]
    assert len(recorded) == 1
    assert recorded[0].outcome is AppCheckVerificationOutcome.VALID
    assert recorded[0].stable_error_code is None


@pytest.mark.requirement("WS03-03B-R4", "WS03-03B-R6")
def test_recorder_failure_does_not_change_enforced_decision() -> None:
    def failing_recorder(_event, _settings):
        raise RuntimeError("synthetic recorder failure")

    app, side_effects, _recorded = _workflow_app(
        mode="enforced",
        verifier=_fixed_verifier(AppCheckVerificationOutcome.MISSING),
        recorder=failing_recorder,
    )

    with TestClient(app) as client:
        response = client.post("/games")

    assert response.status_code == 403
    assert response.json()["code"] == APP_CHECK_REQUIRED_CODE
    assert side_effects == []


@pytest.mark.requirement("WS03-03B-R4", "WS03-03B-R5", "WS03-03B-R6")
def test_real_app_check_denial_preserves_outer_cors_security_and_correlation() -> None:
    from backend.main import create_app

    app = create_app(_settings("enforced"))

    with TestClient(app, follow_redirects=False) as client:
        response = client.get(
            "/games/browse",
            headers={"Host": "testserver", "Origin": ALLOWED_ORIGIN},
        )

    assert response.status_code == 403
    assert response.json()["code"] == APP_CHECK_REQUIRED_CODE
    assert response.headers["X-Request-ID"] == response.json()["correlation_id"]
    assert response.headers["Access-Control-Allow-Origin"] == ALLOWED_ORIGIN
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["Cache-Control"] == "no-store"
