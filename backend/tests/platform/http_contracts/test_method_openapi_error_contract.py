from __future__ import annotations

import json

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from backend.observability.openapi_contracts import (
    PUBLIC_ERROR_SCHEMA,
    VALIDATION_ERROR_SCHEMA,
)
from backend.settings import build_settings, reset_settings_cache

pytestmark = pytest.mark.no_db_cleanup

_TEST_DATABASE_URL = "postgresql+psycopg://db.example.invalid:5432/pickup_lane_test_db"
_ALLOWED_ORIGIN = "https://app.example.invalid"


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


def _api_routes(app) -> tuple[APIRoute, ...]:
    return tuple(route for route in app.routes if isinstance(route, APIRoute))


def _operation(schema: dict[str, object], path: str, method: str) -> dict[str, object]:
    return schema["paths"][path][method]


def _response_codes(schema: dict[str, object], path: str, method: str) -> set[str]:
    operation = _operation(schema, path, method)
    return set(operation["responses"])


@pytest.mark.requirement("WS02-05A-R2")
def test_unsupported_method_remains_framework_owned_with_stable_public_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _create_app(monkeypatch)
    live_route = next(route for route in _api_routes(app) if route.path == "/live")

    with TestClient(app, follow_redirects=False, raise_server_exceptions=False) as client:
        response = client.post("/live", headers={"Host": "testserver"})

    payload = response.json()
    assert response.status_code == 405
    assert response.headers["Allow"] == "GET"
    assert payload["code"] == "API.METHOD_NOT_ALLOWED"
    assert payload["message"] == "Method Not Allowed"
    assert payload["correlation_id"] == response.headers["X-Request-ID"]
    assert "POST" not in live_route.methods


@pytest.mark.requirement("WS02-05A-R3")
def test_openapi_error_components_match_runtime_public_error_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    schema = _create_app(monkeypatch).openapi()
    schemas = schema["components"]["schemas"]

    public_error = schemas[PUBLIC_ERROR_SCHEMA]
    validation_error = schemas[VALIDATION_ERROR_SCHEMA]

    assert public_error["required"] == ["detail", "code", "message", "correlation_id"]
    assert set(public_error["properties"]) == {
        "detail",
        "code",
        "message",
        "correlation_id",
        "details",
    }
    assert public_error["additionalProperties"] is False
    assert public_error["properties"]["correlation_id"]["format"] == "uuid"
    assert validation_error["required"] == public_error["required"]
    assert validation_error["additionalProperties"] is False
    assert validation_error["properties"]["detail"]["type"] == "array"
    assert validation_error["properties"]["detail"]["items"]["required"] == [
        "loc",
        "msg",
        "type",
    ]


@pytest.mark.requirement("WS02-05A-R2", "WS02-05A-R3", "WS02-05A-R6")
def test_route_derived_error_documentation_matches_current_route_classification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    schema = _create_app(monkeypatch).openapi()

    assert {"401", "403", "405", "503"} <= _response_codes(schema, "/admin/users", "get")
    assert {"401", "403", "404", "405", "503"} <= _response_codes(
        schema,
        "/users/{user_id}",
        "get",
    )
    assert {"401", "403", "409", "413", "415", "422", "429", "503"} <= _response_codes(
        schema,
        "/chat-messages",
        "post",
    )
    assert {"405", "503"} <= _response_codes(schema, "/ready", "get")
    assert "405" in _response_codes(schema, "/live", "get")

    webhook_codes = _response_codes(schema, "/stripe/webhook", "post")
    assert "405" not in webhook_codes
    assert {"409", "422", "503"} <= webhook_codes

    tombstone = _operation(schema, "/venues", "post")
    assert tombstone["deprecated"] is True
    assert "410" in tombstone["responses"]
    assert "requestBody" not in tombstone


@pytest.mark.requirement("WS02-05A-R3")
def test_openapi_public_error_schemas_do_not_expose_sensitive_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    schema = _create_app(monkeypatch).openapi()
    error_schemas = {
        PUBLIC_ERROR_SCHEMA: schema["components"]["schemas"][PUBLIC_ERROR_SCHEMA],
        VALIDATION_ERROR_SCHEMA: schema["components"]["schemas"][VALIDATION_ERROR_SCHEMA],
    }
    serialized = json.dumps(error_schemas, sort_keys=True).lower()

    forbidden_fragments = (
        "database_url",
        "password",
        "private url",
        "provider diagnostic",
        "raw request body",
        "secret",
        "sql",
        "submitted sensitive",
        "traceback",
    )
    for fragment in forbidden_fragments:
        assert fragment not in serialized
