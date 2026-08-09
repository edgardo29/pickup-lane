"""OpenAPI contract augmentation for source-owned HTTP behavior."""

from __future__ import annotations

from typing import Any

from fastapi import status
from fastapi.openapi.utils import get_openapi
from fastapi.routing import APIRoute

from backend.observability.http_contracts import (
    iter_api_routes,
    route_has_request_body,
    route_is_private,
    route_is_provider_webhook,
    route_is_tombstone,
    route_uses_database,
)


PUBLIC_ERROR_SCHEMA = "PublicErrorResponse"
VALIDATION_ERROR_SCHEMA = "ValidationErrorResponse"
CHAT_RATE_LIMIT_ROUTE_KEYS = frozenset(
    {
        ("POST", "/chat-messages"),
        ("POST", "/need-a-sub/posts/{sub_post_id}/chat/messages"),
    }
)

ERROR_RESPONSE_DESCRIPTIONS = {
    status.HTTP_401_UNAUTHORIZED: "Authentication is required.",
    status.HTTP_403_FORBIDDEN: "Permission denied.",
    status.HTTP_404_NOT_FOUND: "Resource not found.",
    status.HTTP_405_METHOD_NOT_ALLOWED: "Method not allowed.",
    status.HTTP_409_CONFLICT: "Conflict.",
    status.HTTP_410_GONE: "Retired compatibility endpoint.",
    status.HTTP_413_CONTENT_TOO_LARGE: "Request body is too large.",
    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: "Unsupported media type.",
    status.HTTP_422_UNPROCESSABLE_CONTENT: "Request validation failed.",
    status.HTTP_429_TOO_MANY_REQUESTS: "Rate limit exceeded.",
    status.HTTP_503_SERVICE_UNAVAILABLE: "Service unavailable.",
}


def install_openapi_contracts(app) -> None:
    """Install a generated OpenAPI function enriched with runtime contracts."""

    def custom_openapi() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema

        schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
        apply_openapi_contracts(schema, app.routes)
        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi


def mark_tombstone_routes_deprecated(routes: list[object]) -> None:
    for route in iter_api_routes(routes):
        if route_is_tombstone(route):
            route.deprecated = True


def apply_openapi_contracts(schema: dict[str, Any], routes: list[object]) -> None:
    _ensure_error_components(schema)
    paths = schema.setdefault("paths", {})

    for route in iter_api_routes(routes):
        if not route.include_in_schema:
            continue

        for method in sorted(method.upper() for method in route.methods or ()):
            operation = paths.get(route.path, {}).get(method.lower())
            if not operation:
                continue

            _apply_operation_error_contract(operation, route=route, method=method)


def _ensure_error_components(schema: dict[str, Any]) -> None:
    components = schema.setdefault("components", {})
    schemas = components.setdefault("schemas", {})
    schemas.setdefault(PUBLIC_ERROR_SCHEMA, _public_error_schema())
    schemas.setdefault(VALIDATION_ERROR_SCHEMA, _validation_error_schema())


def _apply_operation_error_contract(
    operation: dict[str, Any],
    *,
    route: APIRoute,
    method: str,
) -> None:
    if route_is_tombstone(route):
        operation["deprecated"] = True
        operation.pop("requestBody", None)
        _set_error_response(operation, status.HTTP_410_GONE)

    if route_has_request_body(route) and not route_is_tombstone(route):
        _set_error_response(operation, status.HTTP_413_CONTENT_TOO_LARGE)
        _set_error_response(operation, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)
        _set_error_response(operation, status.HTTP_422_UNPROCESSABLE_CONTENT)

    if route_is_private(route):
        _set_error_response(operation, status.HTTP_401_UNAUTHORIZED)
        _set_error_response(operation, status.HTTP_403_FORBIDDEN)

    if "{" in route.path and "}" in route.path:
        _set_error_response(operation, status.HTTP_404_NOT_FOUND)

    if method in {"POST", "PUT", "PATCH", "DELETE"} and not route_is_tombstone(route):
        _set_error_response(operation, status.HTTP_409_CONFLICT)

    if route_uses_database(route) or route.path in {"/ready", "/db-health"}:
        _set_error_response(operation, status.HTTP_503_SERVICE_UNAVAILABLE)

    if (method, route.path) in CHAT_RATE_LIMIT_ROUTE_KEYS:
        _set_error_response(operation, status.HTTP_429_TOO_MANY_REQUESTS)

    if not route_is_provider_webhook(route):
        _set_error_response(operation, status.HTTP_405_METHOD_NOT_ALLOWED)


def _set_error_response(operation: dict[str, Any], status_code: int) -> None:
    schema_name = (
        VALIDATION_ERROR_SCHEMA
        if status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        else PUBLIC_ERROR_SCHEMA
    )
    operation.setdefault("responses", {})[str(status_code)] = {
        "description": ERROR_RESPONSE_DESCRIPTIONS[status_code],
        "content": {
            "application/json": {
                "schema": {"$ref": f"#/components/schemas/{schema_name}"},
            },
        },
    }


def _public_error_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "required": ["detail", "code", "message", "correlation_id"],
        "properties": {
            "detail": {
                "description": "Safe client-compatible error detail.",
                "anyOf": [
                    {"type": "string"},
                    {"type": "object"},
                    {"type": "array", "items": {}},
                    {"type": "null"},
                ],
            },
            "code": {
                "type": "string",
                "description": "Stable machine-readable error code.",
            },
            "message": {
                "type": "string",
                "description": "Safe public error message.",
            },
            "correlation_id": {
                "type": "string",
                "format": "uuid",
                "description": "Safe request correlation identifier.",
            },
            "details": {
                "type": "object",
                "description": "Optional safe structured error details.",
                "additionalProperties": True,
            },
        },
        "additionalProperties": False,
    }


def _validation_error_schema() -> dict[str, Any]:
    schema = _public_error_schema()
    schema["properties"]["detail"] = {
        "type": "array",
        "items": {
            "type": "object",
            "required": ["loc", "msg", "type"],
            "properties": {
                "loc": {
                    "type": "array",
                    "items": {
                        "anyOf": [
                            {"type": "string"},
                            {"type": "integer"},
                        ],
                    },
                },
                "msg": {"type": "string"},
                "type": {"type": "string"},
                "url": {"type": "string"},
            },
            "additionalProperties": False,
        },
    }
    return schema
