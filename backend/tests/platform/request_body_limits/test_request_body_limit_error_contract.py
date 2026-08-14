from __future__ import annotations

import pytest
from fastapi import Body, FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from backend.observability.request_body_limits import (
    RequestBodyLimitMiddleware,
    RequestBodyLimitRoute,
)
from backend.settings import build_settings, reset_settings_cache

pytestmark = pytest.mark.no_db_cleanup

_TEST_DATABASE_URL = "postgresql+psycopg://db.example.invalid:5432/pickup_lane_test_db"
_ALLOWED_ORIGIN = "https://app.example.invalid"
_REQUEST_ID = "11111111-1111-4111-8111-111111111111"
_PRIVATE_BODY = b"sk_test_secret DATABASE_URL=postgresql://user:pass@example.invalid/db"
_PRIVATE_SIGNATURE = "t=1,v1=sk_test_signature_secret"
_PRIVATE_HEADER = "Bearer private-provider-token"


def _settings_env(**overrides: str | None) -> dict[str, str]:
    env = {
        "APP_ENV": "test",
        "DATABASE_URL": _TEST_DATABASE_URL,
        "INBOX_TOKEN_SECRET": "synthetic-independent-request-limit-token",
        "ALLOWED_HOSTS": "testserver,api.example.invalid",
        "CORS_ALLOWED_ORIGINS": _ALLOWED_ORIGIN,
        "ENABLE_API_DOCS": "false",
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


def _synthetic_ordinary_app(*, limit_bytes: int = 1024) -> FastAPI:
    app = FastAPI()

    @app.post("/ordinary")
    def ordinary_route(payload: dict = Body(...)):
        return payload

    route = next(route for route in app.routes if isinstance(route, APIRoute))
    app.add_middleware(
        RequestBodyLimitMiddleware,
        ordinary_json_request_body_limit_bytes=limit_bytes,
        ordinary_json_body_routes=(
            RequestBodyLimitRoute(
                path=route.path,
                methods=frozenset({"POST"}),
                path_regex=route.path_regex,
            ),
        ),
        platform_notice_request_body_limit_bytes=163_840,
        stripe_webhook_request_body_limit_bytes=65_536,
    )
    return app


def _assert_common_safe_error_contract(response, *, expected_status: int, expected_code: str) -> None:
    assert response.status_code == expected_status
    payload = response.json()
    assert payload["code"] == expected_code
    assert payload["message"]
    assert payload["detail"]
    assert payload["correlation_id"] == _REQUEST_ID
    assert response.headers["X-Request-ID"] == _REQUEST_ID
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["Cache-Control"] in {"no-store", "private, no-store"}
    assert response.headers["Access-Control-Allow-Origin"] == _ALLOWED_ORIGIN

    rendered = response.text
    for unsafe in (
        _PRIVATE_BODY.decode(),
        "sk_test_secret",
        "DATABASE_URL",
        "postgresql://user:pass",
        _PRIVATE_SIGNATURE,
        _PRIVATE_HEADER,
        "Traceback",
        "RequestBodyLimitExceeded",
    ):
        assert unsafe not in rendered


@pytest.mark.requirement("WS02-04B2A1-R5", "WS02-04B2A1-R2")
def test_signed_stripe_oversized_body_uses_safe_stable_413(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _create_app(monkeypatch, STRIPE_WEBHOOK_REQUEST_BODY_LIMIT_BYTES="16")

    with TestClient(app, follow_redirects=False, raise_server_exceptions=False) as client:
        response = client.post(
            "/stripe/webhook",
            headers={
                "Host": "testserver",
                "Origin": _ALLOWED_ORIGIN,
                "X-Request-ID": _REQUEST_ID,
                "Stripe-Signature": _PRIVATE_SIGNATURE,
                "X-Private-Token": _PRIVATE_HEADER,
            },
            content=_PRIVATE_BODY,
        )

    _assert_common_safe_error_contract(
        response,
        expected_status=413,
        expected_code="API.REQUEST_BODY_TOO_LARGE",
    )
    assert response.json()["detail"] == "Request body exceeds the approved application limit."


@pytest.mark.requirement("WS02-04B2A1-R5", "WS02-04B2A1-R4")
def test_platform_notice_unsupported_content_encoding_uses_safe_stable_415(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _create_app(monkeypatch, PLATFORM_NOTICE_REQUEST_BODY_LIMIT_BYTES="1024")

    with TestClient(app, follow_redirects=False, raise_server_exceptions=False) as client:
        response = client.post(
            "/admin/platform-notices",
            headers={
                "Host": "testserver",
                "Origin": _ALLOWED_ORIGIN,
                "X-Request-ID": _REQUEST_ID,
                "Content-Type": "application/json",
                "Content-Encoding": "br",
                "X-Private-Token": _PRIVATE_HEADER,
            },
            content=_PRIVATE_BODY,
        )

    _assert_common_safe_error_contract(
        response,
        expected_status=415,
        expected_code="API.UNSUPPORTED_CONTENT_ENCODING",
    )
    assert response.json()["detail"] == "Compressed request bodies are not supported for this endpoint."


@pytest.mark.requirement("WS02-04B2A2C-R6")
def test_ordinary_oversized_body_uses_safe_stable_413(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _create_app(monkeypatch, ORDINARY_JSON_REQUEST_BODY_LIMIT_BYTES="16")

    with TestClient(app, follow_redirects=False, raise_server_exceptions=False) as client:
        response = client.patch(
            "/users/me",
            headers={
                "Host": "testserver",
                "Origin": _ALLOWED_ORIGIN,
                "X-Request-ID": _REQUEST_ID,
                "Content-Type": "application/json",
                "Authorization": _PRIVATE_HEADER,
                "X-Private-Token": _PRIVATE_HEADER,
            },
            content=_PRIVATE_BODY,
        )

    _assert_common_safe_error_contract(
        response,
        expected_status=413,
        expected_code="API.REQUEST_BODY_TOO_LARGE",
    )
    assert response.json()["detail"] == "Request body exceeds the approved application limit."


@pytest.mark.requirement("WS02-04B2A2C-R6")
def test_ordinary_unsupported_content_encoding_uses_safe_stable_415(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _create_app(monkeypatch, ORDINARY_JSON_REQUEST_BODY_LIMIT_BYTES="1024")

    with TestClient(app, follow_redirects=False, raise_server_exceptions=False) as client:
        response = client.patch(
            "/users/me",
            headers={
                "Host": "testserver",
                "Origin": _ALLOWED_ORIGIN,
                "X-Request-ID": _REQUEST_ID,
                "Content-Type": "application/json",
                "Content-Encoding": "gzip",
                "Authorization": _PRIVATE_HEADER,
                "X-Private-Token": _PRIVATE_HEADER,
            },
            content=_PRIVATE_BODY,
        )

    _assert_common_safe_error_contract(
        response,
        expected_status=415,
        expected_code="API.UNSUPPORTED_CONTENT_ENCODING",
    )
    assert response.json()["detail"] == "Compressed request bodies are not supported for this endpoint."


@pytest.mark.requirement("WS02-04B2A2C-R6")
def test_supported_json_request_remains_compatible_with_ordinary_limit() -> None:
    app = _synthetic_ordinary_app(limit_bytes=1024)

    with TestClient(app, follow_redirects=False, raise_server_exceptions=False) as client:
        response = client.post(
            "/ordinary",
            headers={"Content-Type": "application/json"},
            content=b'{"value":"accepted"}',
        )

    assert response.status_code == 200
    assert response.json() == {"value": "accepted"}


@pytest.mark.requirement("WS02-04B2A2C-R6")
def test_missing_content_type_is_not_rejected_by_a2c_size_limiter() -> None:
    app = _synthetic_ordinary_app(limit_bytes=1024)

    with TestClient(app, follow_redirects=False, raise_server_exceptions=False) as client:
        response = client.post("/ordinary", content=b'{"value":"accepted"}')

    assert response.status_code == 422
    assert "API.UNSUPPORTED_MEDIA_TYPE" not in response.text
    assert "API.UNSUPPORTED_CONTENT_ENCODING" not in response.text
