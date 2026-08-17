from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from backend.services.app_check_policy import (
    AppCheckPolicyError,
    AppCheckRouteDisposition,
    AppCheckRoutePolicyEntry,
    SUPPORTED_BROWSER_API_ROUTE_TAGS,
    build_app_check_route_policy,
)
from backend.settings import build_settings

pytestmark = [pytest.mark.no_db_cleanup, pytest.mark.suite_type("ordinary")]

TEST_DATABASE_URL = "postgresql+psycopg://db.example.invalid:5432/pickup_lane_test_db"
ALLOWED_ORIGIN = "https://app.example.invalid"
SUPPORTED_APP_ID = "1:123456789:web:supported"


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


@pytest.mark.requirement("WS03-03B-R4", "WS03-03B-R5", "WS03-03B-R7")
def test_current_registered_routes_are_precomputed_and_fully_classified() -> None:
    from backend.main import create_app

    app = create_app(_settings("disabled"))
    policy = app.state.app_check_route_policy
    entries = policy.entries

    assert entries
    assert all(isinstance(entry, AppCheckRoutePolicyEntry) for entry in entries)
    assert "/games/browse" in policy.included_route_templates()
    assert "/admin/users/{user_id}/delete" in policy.included_route_templates()
    assert "/" in policy.excluded_route_templates()
    assert "/live" in policy.excluded_route_templates()
    assert "/ready" in policy.excluded_route_templates()
    assert "/stripe/webhook" in policy.excluded_route_templates()
    assert all(not hasattr(entry, "endpoint") for entry in entries)


@pytest.mark.requirement("WS03-03B-R5", "WS03-03B-R6")
def test_policy_matches_only_precomputed_method_path_and_disposition() -> None:
    from backend.main import create_app

    policy = create_app(_settings("disabled")).state.app_check_route_policy

    included = policy.match(method="GET", path="/games/browse")
    provider_callback = policy.match(method="POST", path="/stripe/webhook")
    health = policy.match(method="GET", path="/live")
    preflight = policy.match(method="OPTIONS", path="/games/browse")
    method_mismatch = policy.match(method="DELETE", path="/auth/me")
    unmatched = policy.match(method="GET", path="/not-a-route")

    assert included is not None
    assert included.applies is True
    assert included.route_template == "/games/browse"
    assert included.route_family == "api.games"
    assert provider_callback is not None
    assert provider_callback.disposition is AppCheckRouteDisposition.EXCLUDED
    assert provider_callback.route_family == "provider_callback"
    assert health is not None
    assert health.disposition is AppCheckRouteDisposition.EXCLUDED
    assert preflight is None
    assert method_mismatch is None
    assert unmatched is None


@pytest.mark.requirement("WS03-03B-R5", "WS03-03B-R7")
def test_registered_unclassified_api_route_fails_policy_construction() -> None:
    app = FastAPI()

    @app.get("/new-provider-surface", tags=["new_provider_surface"])
    def new_provider_surface():
        return {"ok": True}

    with pytest.raises(AppCheckPolicyError, match="Unclassified API route"):
        build_app_check_route_policy(app)


@pytest.mark.requirement("WS03-03B-R5", "WS03-03B-R7")
def test_supported_browser_route_tags_are_explicit_not_prefix_only() -> None:
    assert "games" in SUPPORTED_BROWSER_API_ROUTE_TAGS
    assert "admin_official_games" in SUPPORTED_BROWSER_API_ROUTE_TAGS
    assert "stripe" not in SUPPORTED_BROWSER_API_ROUTE_TAGS
    assert all(tag and not tag.startswith("/") for tag in SUPPORTED_BROWSER_API_ROUTE_TAGS)


@pytest.mark.requirement("WS03-03B-R4", "WS03-03B-R5", "WS03-03B-R6")
def test_unmatched_and_method_mismatch_requests_preserve_normal_404_and_405() -> None:
    from backend.main import create_app

    app = create_app(_settings("enforced"))

    with TestClient(app, follow_redirects=False, raise_server_exceptions=False) as client:
        missing_response = client.get("/not-a-route", headers={"Host": "testserver"})
        method_response = client.delete("/auth/me", headers={"Host": "testserver"})

    assert missing_response.status_code == 404
    assert missing_response.json()["code"] == "API.NOT_FOUND"
    assert method_response.status_code == 405
    assert method_response.json()["code"] == "API.METHOD_NOT_ALLOWED"


@pytest.mark.requirement("WS03-03B-R4", "WS03-03B-R5")
def test_cors_preflight_remains_outside_app_check_but_actual_request_is_evaluated() -> None:
    from backend.main import create_app

    app = create_app(_settings("enforced"))

    with TestClient(app, follow_redirects=False, raise_server_exceptions=False) as client:
        preflight = client.options(
            "/games/browse",
            headers={
                "Host": "testserver",
                "Origin": ALLOWED_ORIGIN,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "X-Firebase-AppCheck",
            },
        )
        actual = client.get(
            "/games/browse",
            headers={"Host": "testserver", "Origin": ALLOWED_ORIGIN},
        )

    assert preflight.status_code == 200
    assert preflight.text == "OK"
    assert preflight.headers["Access-Control-Allow-Origin"] == ALLOWED_ORIGIN
    assert "X-Firebase-AppCheck" in preflight.headers["Access-Control-Allow-Headers"]
    assert actual.status_code == 403
    assert actual.json()["code"] == "APP_CHECK.REQUIRED"
    assert actual.headers["Access-Control-Allow-Origin"] == ALLOWED_ORIGIN
