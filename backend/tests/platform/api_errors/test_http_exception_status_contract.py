from __future__ import annotations

import asyncio
import json
from typing import Any, Mapping

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.observability.http_errors import handle_http_exception
from backend.settings import build_settings, reset_settings_cache

pytestmark = pytest.mark.no_db_cleanup

_TEST_DATABASE_URL = "postgresql+psycopg://127.0.0.1:5432/pickup_lane_test_db"
_ALLOWED_ORIGIN = "https://app.example.invalid"


def _settings_env(**overrides: str | None) -> dict[str, str]:
    env = {
        "APP_ENV": "test",
        "DATABASE_URL": _TEST_DATABASE_URL,
        "INBOX_TOKEN_SECRET": "synthetic-independent-api-error-token",
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


def _normalized_http_exception(
    status_code: int,
    detail: Any,
    *,
    headers: Mapping[str, str] | None = None,
) -> tuple[int, dict[str, Any], Mapping[str, str]]:
    response = asyncio.run(
        handle_http_exception(
            None,  # type: ignore[arg-type]
            StarletteHTTPException(
                status_code=status_code,
                detail=detail,
                headers=headers,
            ),
        )
    )
    return response.status_code, json.loads(response.body), response.headers


@pytest.mark.requirement("WS02-04A-R3")
@pytest.mark.parametrize(
    ("status_code", "detail", "expected_code", "expected_message"),
    [
        (status.HTTP_400_BAD_REQUEST, "Bad synthetic request.", "API.BAD_REQUEST", "Bad synthetic request."),
        (
            status.HTTP_401_UNAUTHORIZED,
            "Authentication is required.",
            "AUTH.UNAUTHENTICATED",
            "Authentication is required.",
        ),
        (status.HTTP_403_FORBIDDEN, "Permission denied.", "AUTH.FORBIDDEN", "Permission denied."),
        (status.HTTP_404_NOT_FOUND, "Resource missing.", "API.NOT_FOUND", "Resource missing."),
        (
            status.HTTP_405_METHOD_NOT_ALLOWED,
            "Method Not Allowed",
            "API.METHOD_NOT_ALLOWED",
            "Method Not Allowed",
        ),
        (status.HTTP_409_CONFLICT, "Conflict.", "API.CONFLICT", "Conflict."),
        (
            status.HTTP_413_CONTENT_TOO_LARGE,
            "Request body is too large.",
            "API.REQUEST_BODY_TOO_LARGE",
            "Request body is too large.",
        ),
        (
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            "Unsupported media type.",
            "API.UNSUPPORTED_MEDIA_TYPE",
            "Unsupported media type.",
        ),
        (status.HTTP_429_TOO_MANY_REQUESTS, "Rate limit exceeded.", "API.RATE_LIMITED", "Rate limit exceeded."),
        (
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Service unavailable.",
            "API.SERVICE_UNAVAILABLE",
            "Service unavailable.",
        ),
    ],
)
def test_current_http_exception_statuses_map_to_stable_public_codes(
    status_code: int,
    detail: str,
    expected_code: str,
    expected_message: str,
) -> None:
    response_status, payload, _headers = _normalized_http_exception(status_code, detail)

    assert response_status == status_code
    assert payload["detail"] == detail
    assert payload["code"] == expected_code
    assert payload["message"] == expected_message


@pytest.mark.requirement("WS02-04A-R3")
def test_retired_route_lowercase_detail_code_does_not_become_top_level_code() -> None:
    response_status, payload, _headers = _normalized_http_exception(
        status.HTTP_410_GONE,
        {
            "code": "booking_scaffold_removed",
            "message": "Generic booking mutations are retired.",
        },
    )

    assert response_status == status.HTTP_410_GONE
    assert payload["detail"] == {
        "code": "booking_scaffold_removed",
        "message": "Generic booking mutations are retired.",
    }
    assert payload["code"] == "API.HTTP_ERROR"
    assert payload["message"] == "Generic booking mutations are retired."


@pytest.mark.requirement("WS02-04A-R3")
def test_other_http_exception_uses_safe_detail_code_or_fallback() -> None:
    response_status, payload, _headers = _normalized_http_exception(
        status.HTTP_418_IM_A_TEAPOT,
        {"code": "API.CUSTOM_FAILURE", "message": "Custom failure."},
    )

    assert response_status == status.HTTP_418_IM_A_TEAPOT
    assert payload["code"] == "API.CUSTOM_FAILURE"
    assert payload["message"] == "Custom failure."

    response_status, payload, _headers = _normalized_http_exception(
        status.HTTP_418_IM_A_TEAPOT,
        "postgresql://private_user:private_pass@example.invalid/db",
    )

    assert response_status == status.HTTP_418_IM_A_TEAPOT
    assert payload["detail"] == "[REDACTED]"
    assert payload["code"] == "API.HTTP_ERROR"
    assert payload["message"] == "I'm a Teapot."


@pytest.mark.requirement("WS02-04A-R3")
@pytest.mark.parametrize(
    ("headers", "content", "expected_status", "expected_code", "expected_detail"),
    [
        (
            {"Content-Type": "application/json"},
            {"display_name": "x" * 50},
            status.HTTP_413_CONTENT_TOO_LARGE,
            "API.REQUEST_BODY_TOO_LARGE",
            "Request body exceeds the approved application limit.",
        ),
        (
            {"Content-Type": "text/plain"},
            "hello",
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            "API.UNSUPPORTED_MEDIA_TYPE",
            "This endpoint accepts JSON request bodies.",
        ),
        (
            {"Content-Type": "application/json", "Content-Encoding": "gzip"},
            {"display_name": "safe"},
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            "API.UNSUPPORTED_CONTENT_ENCODING",
            "Compressed request bodies are not supported for this endpoint.",
        ),
    ],
)
def test_request_body_middleware_errors_use_stable_status_and_codes(
    monkeypatch: pytest.MonkeyPatch,
    headers: dict[str, str],
    content: object,
    expected_status: int,
    expected_code: str,
    expected_detail: str,
) -> None:
    app = _create_app(monkeypatch, ORDINARY_JSON_REQUEST_BODY_LIMIT_BYTES="32")
    request_headers = {"Host": "testserver", **headers}

    with TestClient(app, follow_redirects=False, raise_server_exceptions=False) as client:
        if isinstance(content, str):
            response = client.patch(
                "/users/me",
                headers=request_headers,
                content=content,
            )
        else:
            response = client.patch(
                "/users/me",
                headers=request_headers,
                json=content,
            )

    assert response.status_code == expected_status
    payload = response.json()
    assert payload["code"] == expected_code
    assert payload["detail"] == expected_detail
    assert payload["message"]
    assert response.headers["X-Request-ID"] == payload["correlation_id"]
