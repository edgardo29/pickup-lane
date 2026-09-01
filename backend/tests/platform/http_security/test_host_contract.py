from __future__ import annotations

from collections.abc import Mapping

import pytest
from fastapi.testclient import TestClient

from backend.settings import SettingsError, build_settings, reset_settings_cache

pytestmark = pytest.mark.no_db_cleanup

_PRODUCTION_DATABASE_URL = "postgresql+psycopg://db.example.invalid:5432/pickup_lane_prod"
_TEST_DATABASE_URL = "postgresql+psycopg://db.example.invalid:5432/pickup_lane_test_db"
_FIREBASE_ADMIN_JSON = '{"type":"service_account","project_id":"pickup-lane-synthetic"}'
_STATIC_ASSET_PATH = "/static/seed/venues/harrison-park/gallery-1.webp"


def _settings_env(app_env: str = "test", **overrides: str | None) -> dict[str, str]:
    database_url = _TEST_DATABASE_URL if app_env in {"test", "ci"} else _PRODUCTION_DATABASE_URL
    env = {
        "APP_ENV": app_env,
        "DATABASE_URL": database_url,
        "INBOX_TOKEN_SECRET": "synthetic-independent-http-security-token",
        "ALLOWED_HOSTS": "testserver,api.example.invalid",
        "CORS_ALLOWED_ORIGINS": "https://app.example.invalid",
        "ENABLE_API_DOCS": "true" if app_env == "test" else "false",
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
    if app_env in {"preview", "staging", "production"}:
        env.update(DB_POOL_SIZE="5", DB_MAX_OVERFLOW="2")
    for name, value in overrides.items():
        if value is None:
            env.pop(name, None)
        else:
            env[name] = value
    return env


def _build(env: Mapping[str, str]):
    return build_settings(env, load_dotenv_file=False, validate_full=True)


def _assert_rejected(env: Mapping[str, str], *, mentions: tuple[str, ...]) -> str:
    with pytest.raises(SettingsError) as exc_info:
        _build(env)

    message = str(exc_info.value)
    for fragment in mentions:
        assert fragment in message
    return message


def _import_main(monkeypatch: pytest.MonkeyPatch):
    for name, value in _settings_env().items():
        monkeypatch.setenv(name, value)
    reset_settings_cache()

    import backend.main as main_module

    return main_module


def _create_app(monkeypatch: pytest.MonkeyPatch, **overrides: str | None):
    main_module = _import_main(monkeypatch)
    settings = _build(_settings_env(**overrides))
    return main_module.create_app(settings)


@pytest.mark.requirement("WS02-03-R2")
def test_allowed_hosts_normalize_case_trailing_dot_and_duplicates() -> None:
    settings = _build(
        _settings_env(
            "production",
            ALLOWED_HOSTS=" API.EXAMPLE.INVALID. ,api.example.invalid",
        )
    )

    assert settings.allowed_hosts == ("api.example.invalid",)


@pytest.mark.requirement("WS02-03-R2")
def test_production_like_allowed_hosts_must_be_explicit() -> None:
    _assert_rejected(
        _settings_env("production", ALLOWED_HOSTS=None),
        mentions=("ALLOWED_HOSTS", "explicit"),
    )


@pytest.mark.requirement("WS02-03-R2")
@pytest.mark.parametrize(
    "raw_hosts",
    [
        "*",
        "localhost",
        "127.0.0.1",
        "https://api.example.invalid",
        "api.example.invalid/path",
        "api.example.invalid?query=true",
        "api.example.invalid#fragment",
        "user@api.example.invalid",
        "api.example.invalid:443",
        "api..example.invalid",
        "-api.example.invalid",
        "api_example.invalid",
        "api\\example.invalid",
        "api\x7fexample.invalid",
        "",
    ],
)
def test_production_like_allowed_hosts_reject_unsafe_values(raw_hosts: str) -> None:
    _assert_rejected(
        _settings_env("production", ALLOWED_HOSTS=raw_hosts),
        mentions=("ALLOWED_HOSTS",),
    )


@pytest.mark.requirement("WS02-03-R3")
@pytest.mark.parametrize(
    ("method_name", "path"),
    [
        ("get", "/"),
        ("get", "/live"),
        ("get", "/docs"),
        ("get", "/openapi.json"),
        ("get", "/missing-route"),
        ("post", "/stripe/webhook"),
        ("get", _STATIC_ASSET_PATH),
    ],
)
def test_invalid_host_is_rejected_before_route_or_static_exposure(
    monkeypatch: pytest.MonkeyPatch,
    method_name: str,
    path: str,
) -> None:
    app = _create_app(monkeypatch)

    with TestClient(app, follow_redirects=False) as client:
        response = getattr(client, method_name)(
            path,
            headers={"Host": "attacker.example.invalid"},
        )

    assert response.status_code == 400
    assert "Invalid host header" in response.text
    assert "testserver" not in response.text
    assert "api.example.invalid" not in response.text


@pytest.mark.requirement("WS02-03-R3")
def test_allowed_host_reaches_api_docs_openapi_and_static_asset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _create_app(monkeypatch)

    with TestClient(app, follow_redirects=False) as client:
        root_response = client.get("/", headers={"Host": "testserver"})
        live_response = client.get("/live", headers={"Host": "testserver"})
        docs_response = client.get("/docs", headers={"Host": "testserver"})
        openapi_response = client.get("/openapi.json", headers={"Host": "testserver"})
        static_response = client.get(_STATIC_ASSET_PATH, headers={"Host": "testserver"})

    assert root_response.status_code == 200
    assert live_response.status_code == 200
    assert docs_response.status_code == 200
    assert docs_response.headers["content-type"].startswith("text/html")
    assert openapi_response.status_code == 200
    assert openapi_response.headers["content-type"].startswith("application/json")
    assert static_response.status_code == 200
    assert static_response.headers["content-type"] == "image/webp"


@pytest.mark.requirement("WS02-03-R3")
def test_trusted_host_middleware_is_canonical_and_does_not_redirect_www(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    main_module = _import_main(monkeypatch)
    app = _create_app(monkeypatch)
    trusted_host_middleware = [
        middleware
        for middleware in app.user_middleware
        if middleware.cls is main_module.TrustedHostMiddleware
    ]

    assert len(trusted_host_middleware) == 1
    assert trusted_host_middleware[0].kwargs == {
        "allowed_hosts": ["testserver", "api.example.invalid"],
        "www_redirect": False,
    }
