from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Mapping

import pytest
from fastapi.testclient import TestClient

from backend.observability.http_errors import public_error_response
from backend.settings import build_settings, reset_settings_cache

pytestmark = pytest.mark.no_db_cleanup

_REPO_ROOT = Path(__file__).resolve().parents[4]
_TEST_DATABASE_URL = "postgresql+psycopg://127.0.0.1:5432/pickup_lane_test_db"
_ALLOWED_ORIGIN = "https://app.example.invalid"
_VALID_CORRELATION_ID = "123e4567-e89b-42d3-a456-426614174000"


def _settings_env(**overrides: str | None) -> dict[str, str]:
    env = {
        "APP_ENV": "test",
        "DATABASE_URL": _TEST_DATABASE_URL,
        "INBOX_TOKEN_SECRET": "synthetic-independent-api-error-token",
        "ALLOWED_HOSTS": "testserver,api.example.invalid",
        "CORS_ALLOWED_ORIGINS": _ALLOWED_ORIGIN,
        "ENABLE_API_DOCS": "true",
        "ENABLE_DB_HEALTH": "false",
        "ENABLE_STRIPE_PAYMENTS": "false",
    }
    for name, value in overrides.items():
        if value is None:
            env.pop(name, None)
        else:
            env[name] = value
    return env


def _create_app(monkeypatch: pytest.MonkeyPatch, **overrides: str | None):
    for name, value in _settings_env(**overrides).items():
        monkeypatch.setenv(name, value)
    reset_settings_cache()

    import backend.main as main_module

    settings = build_settings(
        _settings_env(**overrides),
        load_dotenv_file=False,
        validate_full=True,
    )
    return main_module.create_app(settings)


def _assert_canonical_uuidv4(value: str) -> None:
    parsed = uuid.UUID(value)
    assert parsed.version == 4
    assert str(parsed) == value


def _assert_public_error_envelope(
    payload: Mapping[str, object],
    *,
    code: str,
    detail: object,
    message: str,
) -> None:
    assert set(payload) in (
        {"detail", "code", "message", "correlation_id"},
        {"detail", "code", "message", "correlation_id", "details"},
    )
    assert payload["detail"] == detail
    assert payload["code"] == code
    assert payload["message"] == message
    assert isinstance(payload["correlation_id"], str)
    _assert_canonical_uuidv4(payload["correlation_id"])


@pytest.mark.requirement("WS02-04A-R1")
def test_framework_404_uses_stable_public_error_envelope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _create_app(monkeypatch)

    with TestClient(app, follow_redirects=False, raise_server_exceptions=False) as client:
        response = client.get(
            "/missing-route",
            headers={
                "Host": "testserver",
                "X-Request-ID": _VALID_CORRELATION_ID,
            },
        )

    assert response.status_code == 404
    payload = response.json()
    _assert_public_error_envelope(
        payload,
        code="API.NOT_FOUND",
        detail="Not Found",
        message="Not Found",
    )
    assert response.headers["X-Request-ID"] == _VALID_CORRELATION_ID
    assert payload["correlation_id"] == response.headers["X-Request-ID"]


@pytest.mark.requirement("WS02-04A-R1")
def test_public_error_response_uses_en02_descriptor_shape_and_optional_details() -> None:
    response = public_error_response(
        status_code=409,
        code="API.CONFLICT",
        message="Conflict.",
        detail={"message": "Conflict.", "safe": True},
        details={"outcome": "conflict", "retryable": False},
        correlation_id=_VALID_CORRELATION_ID,
    )

    assert response.status_code == 409
    payload = json.loads(response.body)
    assert payload == {
        "detail": {"message": "Conflict.", "safe": True},
        "code": "API.CONFLICT",
        "message": "Conflict.",
        "correlation_id": _VALID_CORRELATION_ID,
        "details": {"outcome": "conflict", "retryable": False},
    }
    assert response.headers["X-Request-ID"] == _VALID_CORRELATION_ID


@pytest.mark.requirement("WS02-04A-R1")
def test_current_frontend_api_client_uses_top_level_detail_and_code() -> None:
    source = (_REPO_ROOT / "frontend/src/lib/apiClient.js").read_text()

    assert "const detail = errorBody?.detail" in source
    assert "errorBody?.code || errorBody?.detail?.code || ''" in source
    assert "formatApiErrorMessage(detail, response.status)" in source
    assert "this.detail = detail" in source
