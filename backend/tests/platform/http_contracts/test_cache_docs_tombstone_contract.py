from __future__ import annotations

from collections.abc import Mapping

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from starlette.datastructures import MutableHeaders

from backend.observability.http_contracts import private_route_matches, route_is_tombstone
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
        "INBOX_TOKEN_SECRET": "synthetic-independent-http-contract-token",
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
        "INBOX_TOKEN_SECRET": "synthetic-independent-http-contract-token",
        "ALLOWED_HOSTS": "api.example.invalid",
        "CORS_ALLOWED_ORIGINS": _ALLOWED_ORIGIN,
        "ENABLE_DB_HEALTH": "false",
        "DB_POOL_SIZE": "5",
        "DB_MAX_OVERFLOW": "2",
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


def _create_app(monkeypatch: pytest.MonkeyPatch, **overrides: str | None):
    for name, value in _settings_env(**overrides).items():
        monkeypatch.setenv(name, value)
    reset_settings_cache()

    import backend.main as main_module

    settings = _build(_settings_env(**overrides))
    return main_module.create_app(settings), main_module


def _api_routes(app) -> tuple[APIRoute, ...]:
    return tuple(route for route in app.routes if isinstance(route, APIRoute))


def _headers_for(
    main_module,
    *,
    method: str = "GET",
    path: str = "/resource",
    status_code: int = 200,
    content_type: str = "application/json",
    existing_cache_control: str | None = None,
    private_routes=(),
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


@pytest.mark.requirement("WS02-05A-R4")
def test_sensitive_private_surfaces_are_classified_private_no_store(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, main_module = _create_app(monkeypatch)
    private_routes = private_route_matches(app.routes)

    sensitive_routes = {
        ("GET", "/admin/users"),
        ("GET", "/inbox/counts"),
        ("POST", "/chat-messages"),
        ("GET", "/payments"),
        ("GET", "/users/me"),
    }
    assert all(
        any(route.matches(method=method, path=path) for route in private_routes)
        for method, path in sensitive_routes
    )

    for method, path in sensitive_routes:
        message = {"type": "http.response.start", "status": 200, "headers": []}
        headers = MutableHeaders(scope=message)
        headers["Content-Type"] = "application/json"
        main_module._apply_response_security_headers(
            headers,
            method=method,
            path=path,
            private_routes=private_routes,
            status_code=200,
        )
        assert headers["Cache-Control"] == "private, no-store"


@pytest.mark.requirement("WS02-05A-R4", "WS02-05A-R5")
def test_public_api_errors_health_docs_and_openapi_are_no_store(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, main_module = _create_app(monkeypatch)
    monkeypatch.setattr(main_module, "_database_ready", lambda: True)

    with TestClient(app, follow_redirects=False, raise_server_exceptions=False) as client:
        live_response = client.get("/live", headers={"Host": "testserver"})
        ready_response = client.get("/ready", headers={"Host": "testserver"})
        missing_response = client.get("/missing-route", headers={"Host": "testserver"})
        docs_response = client.get("/docs", headers={"Host": "testserver"})
        openapi_response = client.get("/openapi.json", headers={"Host": "testserver"})

    assert live_response.status_code == 200
    assert ready_response.status_code == 200
    assert missing_response.status_code == 404
    assert docs_response.status_code == 200
    assert openapi_response.status_code == 200
    assert live_response.headers["Cache-Control"] == "no-store"
    assert ready_response.headers["Cache-Control"] == "no-store"
    assert missing_response.headers["Cache-Control"] == "no-store"
    assert docs_response.headers["Cache-Control"] == "no-store"
    assert openapi_response.headers["Cache-Control"] == "no-store"
    assert "Content-Security-Policy" in docs_response.headers
    assert "Content-Security-Policy" not in openapi_response.headers


@pytest.mark.requirement("WS02-05A-R4")
def test_cache_policy_preserves_route_owned_values_and_excludes_static_redirects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _app, main_module = _create_app(monkeypatch)

    strict_headers = _headers_for(
        main_module,
        path="/live",
        existing_cache_control="private, max-age=0",
    )
    redirect_headers = _headers_for(
        main_module,
        path="/live/",
        status_code=307,
    )
    static_headers = _headers_for(
        main_module,
        path="/static/missing.txt",
        status_code=404,
        content_type="application/json",
    )

    assert strict_headers["Cache-Control"] == "private, max-age=0"
    assert "Cache-Control" not in redirect_headers
    assert "Cache-Control" not in static_headers


@pytest.mark.requirement("WS02-05A-R5")
def test_docs_exposure_policy_is_source_owned_and_independent_from_auth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for app_env in ("preview", "staging", "production"):
        settings = _build(_production_like_settings_env(app_env, ENABLE_API_DOCS=None))
        assert settings.enable_api_docs is False

    with pytest.raises(SettingsError) as exc_info:
        _build(_production_like_settings_env("production", ENABLE_API_DOCS="true"))

    assert "ENABLE_API_DOCS" in str(exc_info.value)

    app, _main_module = _create_app(monkeypatch, ENABLE_API_DOCS="false")
    with TestClient(app, follow_redirects=False, raise_server_exceptions=False) as client:
        docs_response = client.get("/docs", headers={"Host": "testserver"})
        redoc_response = client.get("/redoc", headers={"Host": "testserver"})
        openapi_response = client.get("/openapi.json", headers={"Host": "testserver"})
        auth_response = client.get("/users/me", headers={"Host": "testserver"})

    assert docs_response.status_code == 404
    assert redoc_response.status_code == 404
    assert openapi_response.status_code == 404
    assert auth_response.status_code == 401
    assert auth_response.headers["Cache-Control"] == "private, no-store"


@pytest.mark.requirement("WS02-05A-R6")
def test_registered_tombstones_remain_visible_deprecated_and_bodyless_in_openapi(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, _main_module = _create_app(monkeypatch)
    schema = app.openapi()
    tombstones = [route for route in _api_routes(app) if route_is_tombstone(route)]

    assert len(tombstones) == 45
    for route in tombstones:
        assert route.include_in_schema is True
        for method in route.methods or ():
            operation = schema["paths"][route.path][method.lower()]
            assert operation["deprecated"] is True
            assert "410" in operation["responses"]
            assert "requestBody" not in operation

    assert schema["paths"]["/venues"]["post"]["deprecated"] is True
    assert "410" in schema["paths"]["/venues"]["post"]["responses"]
