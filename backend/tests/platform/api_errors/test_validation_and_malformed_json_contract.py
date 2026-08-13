from __future__ import annotations

import uuid
from typing import Mapping

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from backend.settings import build_settings, reset_settings_cache

pytestmark = pytest.mark.no_db_cleanup

_TEST_DATABASE_URL = "postgresql+psycopg://127.0.0.1:5432/pickup_lane_test_db"
_ALLOWED_ORIGIN = "https://app.example.invalid"
_SECRET_TITLE = "synthetic-secret-token-too-long"
_PRIVATE_DATABASE_URL = "postgresql://private_user:private_pass@example.invalid/db"


class _NestedPayload(BaseModel):
    count: int


class _ValidationPayload(BaseModel):
    title: str = Field(max_length=5)
    nested: _NestedPayload


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


def _create_app_with_validation_route(monkeypatch: pytest.MonkeyPatch):
    for name, value in _settings_env().items():
        monkeypatch.setenv(name, value)
    reset_settings_cache()

    import backend.main as main_module

    settings = build_settings(
        _settings_env(),
        load_dotenv_file=False,
        validate_full=True,
    )
    app = main_module.create_app(settings)

    @app.post("/synthetic-validation")
    def synthetic_validation(payload: _ValidationPayload) -> dict[str, object]:
        return payload.model_dump()

    return app


def _assert_correlation(payload: Mapping[str, object], response_headers: Mapping[str, str]) -> None:
    correlation_id = payload["correlation_id"]
    assert isinstance(correlation_id, str)
    parsed = uuid.UUID(correlation_id)
    assert parsed.version == 4
    assert str(parsed) == correlation_id
    assert response_headers["X-Request-ID"] == correlation_id


def _assert_validation_payload_is_bounded(payload: Mapping[str, object]) -> None:
    assert payload["message"] in {
        "Request validation failed.",
        "Malformed JSON request body.",
    }
    detail = payload["detail"]
    assert isinstance(detail, list)
    assert detail
    for error in detail:
        assert set(error) <= {"loc", "msg", "type", "url"}
        assert isinstance(error["loc"], list)
        assert isinstance(error["msg"], str)
        assert isinstance(error["type"], str)

    details = payload["details"]
    assert isinstance(details, dict)
    field_errors = details["field_errors"]
    assert isinstance(field_errors, list)
    assert len(field_errors) == len(detail)
    for field_error in field_errors:
        assert set(field_error) == {"location", "description", "error_type"}
        assert isinstance(field_error["location"], str)
        assert isinstance(field_error["description"], str)
        assert isinstance(field_error["error_type"], str)


@pytest.mark.requirement("WS02-04A-R2")
def test_validation_error_excludes_submitted_values_and_uses_safe_structure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _create_app_with_validation_route(monkeypatch)

    with TestClient(app, follow_redirects=False, raise_server_exceptions=False) as client:
        response = client.post(
            "/synthetic-validation",
            headers={"Host": "testserver"},
            json={
                "title": _SECRET_TITLE,
                "nested": {"count": _PRIVATE_DATABASE_URL},
            },
        )

    assert response.status_code == 422
    assert _SECRET_TITLE not in response.text
    assert _PRIVATE_DATABASE_URL not in response.text
    assert "private_pass" not in response.text
    payload = response.json()
    assert payload["code"] == "API.VALIDATION_FAILED"
    _assert_validation_payload_is_bounded(payload)
    _assert_correlation(payload, response.headers)
    assert payload["detail"] == [
        {
            "loc": ["body", "title"],
            "msg": "String should have at most 5 characters",
            "type": "string_too_long",
        },
        {
            "loc": ["body", "nested", "count"],
            "msg": "Input should be a valid integer, unable to parse string as an integer",
            "type": "int_parsing",
        },
    ]


@pytest.mark.requirement("WS02-04A-R2")
def test_malformed_json_error_excludes_raw_body_and_parser_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _create_app_with_validation_route(monkeypatch)

    with TestClient(app, follow_redirects=False, raise_server_exceptions=False) as client:
        response = client.post(
            "/synthetic-validation",
            headers={
                "Host": "testserver",
                "Content-Type": "application/json",
            },
            content=f'{{"title": "{_SECRET_TITLE}',
        )

    assert response.status_code == 422
    assert _SECRET_TITLE not in response.text
    assert "JSONDecodeError" not in response.text
    payload = response.json()
    assert payload["code"] == "API.MALFORMED_JSON"
    assert payload["message"] == "Malformed JSON request body."
    _assert_validation_payload_is_bounded(payload)
    _assert_correlation(payload, response.headers)
    assert payload["detail"] == [
        {
            "loc": ["body", 10],
            "msg": "JSON decode error",
            "type": "json_invalid",
        }
    ]
