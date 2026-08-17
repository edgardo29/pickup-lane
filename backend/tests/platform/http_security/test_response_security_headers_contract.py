from __future__ import annotations

import re
from collections.abc import Mapping

import pytest
from fastapi.testclient import TestClient
from starlette.datastructures import MutableHeaders

from backend.observability.http_contracts import RouteMatch
from backend.settings import SettingsError, build_settings, reset_settings_cache

pytestmark = pytest.mark.no_db_cleanup

_TEST_DATABASE_URL = "postgresql+psycopg://db.example.invalid:5432/pickup_lane_test_db"
_PRODUCTION_DATABASE_URL = "postgresql+psycopg://db.example.invalid:5432/pickup_lane_prod"
_ALLOWED_ORIGIN = "https://app.example.invalid"
_FIREBASE_ADMIN_JSON = '{"type":"service_account","project_id":"pickup-lane-synthetic"}'


def _settings_env(**overrides: str | None) -> dict[str, str]:
    env = {
        "APP_ENV": "test",
        "DATABASE_URL": _TEST_DATABASE_URL,
        "INBOX_TOKEN_SECRET": "synthetic-independent-http-security-token",
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


def _production_like_settings_env(app_env: str, **overrides: str | None) -> dict[str, str]:
    env = {
        "APP_ENV": app_env,
        "DATABASE_URL": _PRODUCTION_DATABASE_URL,
        "INBOX_TOKEN_SECRET": "synthetic-independent-http-security-token",
        "ALLOWED_HOSTS": "api.example.invalid",
        "CORS_ALLOWED_ORIGINS": _ALLOWED_ORIGIN,
        "ENABLE_DB_HEALTH": "false",
        "FIREBASE_ADMIN_CREDENTIALS_JSON": _FIREBASE_ADMIN_JSON,
        "FIREBASE_PROJECT_ID": "pickup-lane-synthetic",
        "FIREBASE_APP_CHECK_MODE": "disabled",
        "ENABLE_STRIPE_PAYMENTS": "false",
        "R2_ACCOUNT_ID": "synthetic-r2-account",
        "R2_ACCESS_KEY_ID": "synthetic-r2-access-key-id",
        "R2_SECRET_ACCESS_KEY": "synthetic-r2-secret-access-key",
        "R2_BUCKET_NAME": "pickup-lane-synthetic-bucket",
        "R2_ENDPOINT_URL": "https://synthetic-r2-account.r2.cloudflarestorage.com",
    }
    for name, value in overrides.items():
        if value is None:
            env.pop(name, None)
        else:
            env[name] = value
    return env


def _build(env: Mapping[str, str]):
    return build_settings(env, load_dotenv_file=False, validate_full=True)


def _import_main(monkeypatch: pytest.MonkeyPatch):
    for name, value in _settings_env().items():
        monkeypatch.setenv(name, value)
    reset_settings_cache()

    import backend.main as main_module

    return main_module


def _create_app(monkeypatch: pytest.MonkeyPatch, **overrides: str | None):
    main_module = _import_main(monkeypatch)
    settings = _build(_settings_env(**overrides))
    return main_module.create_app(settings), main_module


def _headers_for(
    main_module,
    *,
    method: str = "GET",
    path: str = "/resource",
    status_code: int = 200,
    content_type: str = "application/json",
    private_routes: tuple[RouteMatch, ...] = (),
    existing_cache_control: str | None = None,
) -> MutableHeaders:
    message = {"type": "http.response.start", "status": status_code, "headers": []}
    headers = MutableHeaders(scope=message)
    if content_type:
        headers["Content-Type"] = content_type
    if existing_cache_control is not None:
        headers["Cache-Control"] = existing_cache_control

    main_module._apply_response_security_headers(
        headers,
        method=method,
        path=path,
        private_routes=private_routes,
        status_code=status_code,
    )
    return headers


def _assert_api_security_headers(
    headers: Mapping[str, str],
    *,
    cache_control: str = "no-store",
) -> None:
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["Referrer-Policy"] == "no-referrer"
    assert headers["Cache-Control"] == cache_control


@pytest.mark.requirement("WS02-03-R5")
def test_public_api_json_response_gets_api_security_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    main_module = _import_main(monkeypatch)

    headers = _headers_for(main_module, path="/games")

    _assert_api_security_headers(headers)


@pytest.mark.requirement("WS02-03-R5")
def test_private_api_json_response_gets_private_no_store_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    main_module = _import_main(monkeypatch)
    private_routes = (
        RouteMatch(
            path="/admin/example",
            methods=frozenset({"GET"}),
            path_regex=re.compile(r"^/admin/example$"),
        ),
    )

    headers = _headers_for(
        main_module,
        path="/admin/example",
        private_routes=private_routes,
    )

    _assert_api_security_headers(headers, cache_control="private, no-store")


@pytest.mark.requirement("WS02-03-R5")
def test_explicit_route_cache_policy_is_preserved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    main_module = _import_main(monkeypatch)

    headers = _headers_for(
        main_module,
        path="/live",
        existing_cache_control="private, max-age=0",
    )

    _assert_api_security_headers(headers, cache_control="private, max-age=0")


@pytest.mark.requirement("WS02-03-R5")
@pytest.mark.parametrize(
    ("path", "status_code", "content_type"),
    [
        ("/missing-route", 404, "application/json"),
        ("/validation-error", 422, "application/json"),
        ("/server-error", 500, "application/json"),
        ("/empty", 204, ""),
    ],
)
def test_error_and_no_content_responses_receive_api_security_headers(
    monkeypatch: pytest.MonkeyPatch,
    path: str,
    status_code: int,
    content_type: str,
) -> None:
    main_module = _import_main(monkeypatch)

    headers = _headers_for(
        main_module,
        path=path,
        status_code=status_code,
        content_type=content_type,
    )

    _assert_api_security_headers(headers)


@pytest.mark.requirement("WS02-03-R6")
def test_docs_html_gets_documentation_specific_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, _main_module = _create_app(monkeypatch)

    with TestClient(app, follow_redirects=False) as client:
        response = client.get("/docs", headers={"Host": "testserver"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    _assert_api_security_headers(response.headers)
    assert response.headers["Content-Security-Policy"] == "frame-ancestors 'none'"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "geolocation=()" in response.headers["Permissions-Policy"]


@pytest.mark.requirement("WS02-03-R6")
def test_openapi_json_keeps_json_policy_without_docs_html_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, _main_module = _create_app(monkeypatch)

    with TestClient(app, follow_redirects=False) as client:
        response = client.get("/openapi.json", headers={"Host": "testserver"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    _assert_api_security_headers(response.headers)
    assert "Content-Security-Policy" not in response.headers
    assert "X-Frame-Options" not in response.headers
    assert "Permissions-Policy" not in response.headers


@pytest.mark.requirement("WS02-03-R6")
@pytest.mark.parametrize("app_env", ["preview", "staging", "production"])
def test_production_like_environments_do_not_enable_api_docs_by_default(
    app_env: str,
) -> None:
    settings = _build(_production_like_settings_env(app_env, ENABLE_API_DOCS=None))

    assert settings.enable_api_docs is False


@pytest.mark.requirement("WS02-03-R6")
def test_production_rejects_explicit_api_docs_enable() -> None:
    with pytest.raises(SettingsError) as exc_info:
        _build(_production_like_settings_env("production", ENABLE_API_DOCS="true"))

    assert "ENABLE_API_DOCS" in str(exc_info.value)


@pytest.mark.requirement("WS02-03-R6")
def test_docs_disabled_app_surfaces_are_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, _main_module = _create_app(monkeypatch, ENABLE_API_DOCS="false")

    with TestClient(app, follow_redirects=False) as client:
        docs_response = client.get("/docs", headers={"Host": "testserver"})
        redoc_response = client.get("/redoc", headers={"Host": "testserver"})
        openapi_response = client.get("/openapi.json", headers={"Host": "testserver"})

    assert docs_response.status_code == 404
    assert docs_response.headers["content-type"].startswith("application/json")
    assert redoc_response.status_code == 404
    assert redoc_response.headers["content-type"].startswith("application/json")
    assert openapi_response.status_code == 404
    assert openapi_response.headers["content-type"].startswith("application/json")


@pytest.mark.requirement("WS02-03-R5")
def test_health_and_db_health_responses_receive_api_security_headers_without_database_contact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, main_module = _create_app(monkeypatch, ENABLE_DB_HEALTH="true")
    monkeypatch.setattr(main_module, "_database_ready", lambda: False)

    with TestClient(app, follow_redirects=False) as client:
        live_response = client.get("/live", headers={"Host": "testserver"})
        db_health_response = client.get("/db-health", headers={"Host": "testserver"})

    assert live_response.status_code == 200
    _assert_api_security_headers(live_response.headers)
    assert db_health_response.status_code == 503
    _assert_api_security_headers(db_health_response.headers)


@pytest.mark.requirement("WS02-03-R5")
@pytest.mark.parametrize(
    ("database_ready", "expected_status_code", "expected_health_status"),
    [
        (True, 200, "ready"),
        (False, 503, "not_ready"),
    ],
)
def test_ready_response_receives_api_security_headers_with_controlled_database_state(
    monkeypatch: pytest.MonkeyPatch,
    database_ready: bool,
    expected_status_code: int,
    expected_health_status: str,
) -> None:
    app, main_module = _create_app(monkeypatch)
    monkeypatch.setattr(main_module, "_database_ready", lambda: database_ready)

    with TestClient(app, follow_redirects=False) as client:
        response = client.get("/ready", headers={"Host": "testserver"})

    assert response.status_code == expected_status_code
    assert response.json()["status"] == expected_health_status
    _assert_api_security_headers(response.headers)


@pytest.mark.requirement("WS02-03-R5")
def test_webhook_error_response_class_gets_api_security_headers_without_provider_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    main_module = _import_main(monkeypatch)

    headers = _headers_for(
        main_module,
        method="POST",
        path="/stripe/webhook",
        status_code=400,
    )

    _assert_api_security_headers(headers)
