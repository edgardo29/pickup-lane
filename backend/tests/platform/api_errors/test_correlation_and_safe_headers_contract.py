from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any, Mapping

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.observability.correlation import get_correlation_id
from backend.observability.http_errors import handle_http_exception
from backend.settings import build_settings, reset_settings_cache

pytestmark = pytest.mark.no_db_cleanup

_TEST_DATABASE_URL = "postgresql+psycopg://127.0.0.1:5432/pickup_lane_test_db"
_ALLOWED_ORIGIN = "https://app.example.invalid"
_VALID_CORRELATION_ID = "123e4567-e89b-42d3-a456-426614174010"
_MALICIOUS_REQUEST_ID = "booking_12345"


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


def _normalized_http_exception(
    status_code: int,
    *,
    detail: Any = "Synthetic safe detail.",
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


def _assert_canonical_uuidv4(value: str) -> None:
    parsed = uuid.UUID(value)
    assert parsed.version == 4
    assert str(parsed) == value


def _assert_body_header_correlation(payload: Mapping[str, object], headers: Mapping[str, str]) -> None:
    correlation_id = payload["correlation_id"]
    assert isinstance(correlation_id, str)
    _assert_canonical_uuidv4(correlation_id)
    assert headers["X-Request-ID"] == correlation_id


@pytest.mark.requirement("WS02-04A-R4")
def test_valid_incoming_request_id_is_accepted_and_mirrored(
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

    payload = response.json()
    assert response.status_code == 404
    assert response.headers["X-Request-ID"] == _VALID_CORRELATION_ID
    assert payload["correlation_id"] == _VALID_CORRELATION_ID
    assert get_correlation_id() is None


@pytest.mark.requirement("WS02-04A-R4")
def test_invalid_and_missing_request_ids_receive_safe_generated_correlation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _create_app(monkeypatch)

    with TestClient(app, follow_redirects=False, raise_server_exceptions=False) as client:
        invalid_response = client.get(
            "/missing-route",
            headers={
                "Host": "testserver",
                "X-Request-ID": _MALICIOUS_REQUEST_ID,
            },
        )
        missing_response = client.get(
            "/missing-route",
            headers={"Host": "testserver"},
        )

    invalid_payload = invalid_response.json()
    missing_payload = missing_response.json()
    assert invalid_response.headers["X-Request-ID"] != _MALICIOUS_REQUEST_ID
    _assert_body_header_correlation(invalid_payload, invalid_response.headers)
    _assert_body_header_correlation(missing_payload, missing_response.headers)
    assert invalid_payload["correlation_id"] != missing_payload["correlation_id"]
    assert get_correlation_id() is None


@pytest.mark.requirement("WS02-04A-R4")
@pytest.mark.parametrize(
    ("status_code", "header_name", "header_value", "canonical_name"),
    [
        (status.HTTP_401_UNAUTHORIZED, "wWw-aUtHeNtIcAtE", "Bearer", "WWW-Authenticate"),
        (status.HTTP_405_METHOD_NOT_ALLOWED, "aLlOw", "GET", "Allow"),
        (status.HTTP_429_TOO_MANY_REQUESTS, "rEtRy-aFtEr", "7", "Retry-After"),
    ],
)
def test_approved_http_exception_headers_are_preserved_case_insensitively(
    status_code: int,
    header_name: str,
    header_value: str,
    canonical_name: str,
) -> None:
    response_status, payload, headers = _normalized_http_exception(
        status_code,
        headers={header_name: header_value},
    )

    assert response_status == status_code
    assert headers[canonical_name] == header_value
    _assert_body_header_correlation(payload, headers)


@pytest.mark.requirement("WS02-04A-R4")
def test_framework_method_not_allowed_preserves_framework_owned_allow_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _create_app(monkeypatch)

    with TestClient(app, follow_redirects=False, raise_server_exceptions=False) as client:
        response = client.post("/live", headers={"Host": "testserver"})

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    assert response.headers["Allow"] == "GET"
    payload = response.json()
    assert payload["code"] == "API.METHOD_NOT_ALLOWED"
    _assert_body_header_correlation(payload, response.headers)


@pytest.mark.requirement("WS02-04A-R4")
def test_rejected_http_exception_headers_are_not_forwarded() -> None:
    rejected_headers = {
        "X-Request-ID": _MALICIOUS_REQUEST_ID,
        "x-request-id": "provider-request-456",
        "X-Internal": "synthetic-internal-context",
        "Set-Cookie": "session=synthetic-secret",
        "Location": "https://evil.example.invalid/redirect",
        "Access-Control-Allow-Origin": "https://evil.example.invalid",
        "Cache-Control": "public, max-age=3600",
    }

    _response_status, payload, headers = _normalized_http_exception(
        status.HTTP_400_BAD_REQUEST,
        detail="Bad synthetic request.",
        headers=rejected_headers,
    )

    _assert_body_header_correlation(payload, headers)
    assert headers["X-Request-ID"] != _MALICIOUS_REQUEST_ID
    for header_name in (
        "X-Internal",
        "Set-Cookie",
        "Location",
        "Access-Control-Allow-Origin",
        "Cache-Control",
    ):
        assert header_name not in headers


@pytest.mark.requirement("WS02-04A-R4")
@pytest.mark.parametrize(
    ("status_code", "header_name"),
    [
        (status.HTTP_503_SERVICE_UNAVAILABLE, "Retry-After"),
        (status.HTTP_400_BAD_REQUEST, "Allow"),
        (status.HTTP_403_FORBIDDEN, "WWW-Authenticate"),
    ],
)
def test_wrong_status_header_pairs_are_not_preserved(
    status_code: int,
    header_name: str,
) -> None:
    _response_status, payload, headers = _normalized_http_exception(
        status_code,
        headers={header_name: "synthetic-protocol-value"},
    )

    _assert_body_header_correlation(payload, headers)
    assert header_name not in headers


@pytest.mark.requirement("WS02-04A-R4")
def test_outer_middleware_headers_survive_after_exception_header_filtering(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _create_app(monkeypatch)

    @app.get("/synthetic-header-filter")
    def synthetic_header_filter() -> None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bad synthetic request.",
            headers={
                "Access-Control-Allow-Origin": "https://evil.example.invalid",
                "Cache-Control": "public, max-age=3600",
                "X-Request-ID": _MALICIOUS_REQUEST_ID,
            },
        )

    with TestClient(app, follow_redirects=False, raise_server_exceptions=False) as client:
        response = client.get(
            "/synthetic-header-filter",
            headers={
                "Host": "testserver",
                "Origin": _ALLOWED_ORIGIN,
            },
        )

    payload = response.json()
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.headers["Access-Control-Allow-Origin"] == _ALLOWED_ORIGIN
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Request-ID"] != _MALICIOUS_REQUEST_ID
    _assert_body_header_correlation(payload, response.headers)
