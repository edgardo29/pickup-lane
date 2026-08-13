from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Mapping

import pytest
from fastapi.testclient import TestClient

from backend.observability.correlation import CORRELATION_ID_HEADER, correlation_context
from backend.observability.http_errors import (
    GENERIC_UNEXPECTED_DETAIL,
    GENERIC_UNEXPECTED_MESSAGE,
    handle_unexpected_exception,
)
from backend.observability.timeouts import (
    DATABASE_TIMEOUT_CODE,
    DEPENDENCY_MUTATION_TIMEOUT_UNKNOWN_CODE,
    DEPENDENCY_READ_TIMEOUT_CODE,
    DatabaseTimeoutError,
    DependencyMutationTimeoutUnknownError,
    DependencyReadTimeoutError,
)
from backend.settings import build_settings, reset_settings_cache

pytestmark = pytest.mark.no_db_cleanup

_TEST_DATABASE_URL = "postgresql+psycopg://127.0.0.1:5432/pickup_lane_test_db"
_ALLOWED_ORIGIN = "https://app.example.invalid"
_ERROR_LOGGER = "backend.observability.http_errors"
_LOG_SAFE_CORRELATION_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
_SENSITIVE_SENTINELS = (
    "synthetic-raw-exception-text",
    "Bearer synthetic-token",
    "postgresql://private_user:private_pass@example.invalid/db",
    "stripe provider diagnostic",
    "/Users/private/source/path.py",
    "session=synthetic-cookie",
    "https://storage.example.invalid/object?X-Amz-Signature=synthetic",
    "submitted-private-value",
    "SyntheticPrivateObject(secret)",
)


class _SyntheticPrivateObject:
    def __repr__(self) -> str:
        return "SyntheticPrivateObject(secret)"


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


def _unexpected_response(exc: Exception) -> tuple[int, dict[str, Any], Mapping[str, str]]:
    with correlation_context(_LOG_SAFE_CORRELATION_ID):
        response = asyncio.run(
            handle_unexpected_exception(
                None,  # type: ignore[arg-type]
                exc,
            )
        )
    return response.status_code, json.loads(response.body), response.headers


@pytest.mark.requirement("WS02-04A-R5")
def test_generic_unexpected_exception_response_and_log_exclude_private_values(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    app = _create_app(monkeypatch)
    caplog.set_level(logging.ERROR, logger=_ERROR_LOGGER)

    @app.get("/synthetic-unexpected")
    def synthetic_unexpected() -> None:
        raise RuntimeError(
            " | ".join(
                (
                    *_SENSITIVE_SENTINELS,
                    repr(_SyntheticPrivateObject()),
                )
            )
        )

    with TestClient(app, follow_redirects=False, raise_server_exceptions=False) as client:
        response = client.get(
            "/synthetic-unexpected",
            headers={
                "Host": "testserver",
                CORRELATION_ID_HEADER: _LOG_SAFE_CORRELATION_ID,
            },
        )

    assert response.status_code == 500
    payload = response.json()
    assert payload["code"] == "API.UNEXPECTED"
    assert payload["message"] == GENERIC_UNEXPECTED_MESSAGE
    assert payload["detail"] == GENERIC_UNEXPECTED_DETAIL
    assert response.headers["X-Request-ID"] == payload["correlation_id"]

    for sentinel in _SENSITIVE_SENTINELS:
        assert sentinel not in response.text
        assert sentinel not in caplog.text

    records = [record for record in caplog.records if record.name == _ERROR_LOGGER]
    assert len(records) == 1
    assert records[0].message == "Unhandled application exception."
    logged_context = records[0].__dict__["pickup_lane_error"]
    assert logged_context == {
        "correlation_id": payload["correlation_id"],
        "error_code": "API.UNEXPECTED",
    }


@pytest.mark.requirement("WS02-04A-R5")
@pytest.mark.parametrize(
    ("exc", "expected_code", "expected_message", "expected_details"),
    [
        (
            DependencyReadTimeoutError(
                provider_kind="stripe",
                operation="payment.lookup",
            ),
            DEPENDENCY_READ_TIMEOUT_CODE,
            "Dependency read timed out.",
            {
                "outcome": "retry_later",
                "timeout_class": "dependency_read_timeout",
            },
        ),
        (
            DependencyMutationTimeoutUnknownError(
                provider_kind="stripe",
                operation="payment.confirm",
            ),
            DEPENDENCY_MUTATION_TIMEOUT_UNKNOWN_CODE,
            "Dependency mutation outcome is unknown.",
            {
                "outcome": "unknown",
                "timeout_class": "dependency_mutation_timeout",
            },
        ),
        (
            DatabaseTimeoutError(timeout_kind="statement"),
            DATABASE_TIMEOUT_CODE,
            "Database operation timed out.",
            {
                "outcome": "retry_later",
                "timeout_class": "database_timeout",
                "timeout_kind": "statement",
            },
        ),
    ],
)
def test_timeout_exceptions_use_bounded_503_public_and_log_contracts(
    caplog: pytest.LogCaptureFixture,
    exc: Exception,
    expected_code: str,
    expected_message: str,
    expected_details: dict[str, str],
) -> None:
    caplog.set_level(logging.WARNING, logger=_ERROR_LOGGER)

    response_status, payload, headers = _unexpected_response(exc)

    assert response_status == 503
    assert payload["code"] == expected_code
    assert payload["message"] == expected_message
    assert payload["details"] == expected_details
    assert headers["X-Request-ID"] == payload["correlation_id"]
    for sentinel in _SENSITIVE_SENTINELS:
        assert sentinel not in json.dumps(payload)
        assert sentinel not in caplog.text

    records = [record for record in caplog.records if record.name == _ERROR_LOGGER]
    assert len(records) == 1
    assert records[0].message == "Application operation timed out."
    logged_context = records[0].__dict__["pickup_lane_error"]
    assert logged_context["correlation_id"] == payload["correlation_id"]
    assert logged_context["error_code"] == expected_code
