"""FastAPI error normalization using the EN-02 public error primitives."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from http import HTTPStatus
import logging
from typing import Any

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.datastructures import Headers, MutableHeaders
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from backend.observability.correlation import (
    CORRELATION_ID_HEADER,
    CorrelationIdError,
    generate_correlation_id,
    get_correlation_id,
    reset_correlation_id,
    set_correlation_id,
    validate_correlation_id,
)
from backend.observability.errors import PublicErrorDescriptor
from backend.observability.redaction import (
    REDACTION_MARKER,
    contains_sensitive_text,
    redact_value,
)

logger = logging.getLogger(__name__)

GENERIC_UNEXPECTED_DETAIL = "An unexpected error occurred."
GENERIC_UNEXPECTED_MESSAGE = "Something went wrong. Please try again."
VALIDATION_FAILED_MESSAGE = "Request validation failed."
MALFORMED_JSON_MESSAGE = "Malformed JSON request body."
HTTP_STATUS_UNPROCESSABLE_ENTITY = 422

_STATUS_ERROR_CODES: dict[int, str] = {
    status.HTTP_400_BAD_REQUEST: "API.BAD_REQUEST",
    status.HTTP_401_UNAUTHORIZED: "AUTH.UNAUTHENTICATED",
    status.HTTP_403_FORBIDDEN: "AUTH.FORBIDDEN",
    status.HTTP_404_NOT_FOUND: "API.NOT_FOUND",
    status.HTTP_405_METHOD_NOT_ALLOWED: "API.METHOD_NOT_ALLOWED",
    status.HTTP_409_CONFLICT: "API.CONFLICT",
    status.HTTP_413_CONTENT_TOO_LARGE: "API.REQUEST_BODY_TOO_LARGE",
    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: "API.UNSUPPORTED_CONTENT_ENCODING",
    HTTP_STATUS_UNPROCESSABLE_ENTITY: "API.VALIDATION_FAILED",
    status.HTTP_500_INTERNAL_SERVER_ERROR: "API.UNEXPECTED",
    status.HTTP_503_SERVICE_UNAVAILABLE: "API.SERVICE_UNAVAILABLE",
}
_STATUS_MESSAGES: dict[int, str] = {
    status.HTTP_400_BAD_REQUEST: "Bad request.",
    status.HTTP_401_UNAUTHORIZED: "Authentication is required.",
    status.HTTP_403_FORBIDDEN: "Permission denied.",
    status.HTTP_404_NOT_FOUND: "Not found.",
    status.HTTP_405_METHOD_NOT_ALLOWED: "Method not allowed.",
    status.HTTP_409_CONFLICT: "Conflict.",
    status.HTTP_413_CONTENT_TOO_LARGE: "Request body is too large.",
    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: "Unsupported content encoding.",
    HTTP_STATUS_UNPROCESSABLE_ENTITY: VALIDATION_FAILED_MESSAGE,
    status.HTTP_500_INTERNAL_SERVER_ERROR: GENERIC_UNEXPECTED_MESSAGE,
    status.HTTP_503_SERVICE_UNAVAILABLE: "Service unavailable.",
}


class CorrelationIdMiddleware:
    """Set a safe request correlation ID and mirror it in HTTP responses."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        correlation_id = _resolve_request_correlation_id(scope)
        token = set_correlation_id(correlation_id)

        async def send_with_correlation_header(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers.setdefault(CORRELATION_ID_HEADER, correlation_id)
            await send(message)

        try:
            await self.app(scope, receive, send_with_correlation_header)
        finally:
            reset_correlation_id(token)


def register_exception_handlers(app) -> None:
    """Install application-owned stable error handlers."""

    app.add_exception_handler(
        RequestValidationError,
        handle_request_validation_error,
    )
    app.add_exception_handler(
        StarletteHTTPException,
        handle_http_exception,
    )
    app.add_exception_handler(
        Exception,
        handle_unexpected_exception,
    )


def public_error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    detail: Any,
    details: Mapping[str, Any] | None = None,
    correlation_id: str | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    """Build a stable public error response for app-owned middleware."""

    return _public_error_response(
        status_code=status_code,
        code=code,
        message=message,
        detail=detail,
        details=details,
        correlation_id=correlation_id,
        headers=headers,
    )


async def handle_request_validation_error(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Return deterministic validation details without submitted values."""

    del request
    validation_errors = _sanitize_validation_errors(exc.errors())
    malformed_json = _has_malformed_json_error(validation_errors)
    message = MALFORMED_JSON_MESSAGE if malformed_json else VALIDATION_FAILED_MESSAGE
    code = "API.MALFORMED_JSON" if malformed_json else "API.VALIDATION_FAILED"
    details = {"field_errors": _field_error_details(validation_errors)}

    return _public_error_response(
        status_code=HTTP_STATUS_UNPROCESSABLE_ENTITY,
        code=code,
        message=message,
        detail=validation_errors,
        details=details,
    )


async def handle_http_exception(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    """Normalize framework and route HTTP exceptions."""

    del request
    default_message = _default_status_message(exc.status_code)
    detail = _sanitize_detail(exc.detail, fallback=default_message)
    message = _message_from_detail(detail, fallback=default_message)

    return _public_error_response(
        status_code=exc.status_code,
        code=_error_code_for_status(exc.status_code),
        message=message,
        detail=detail,
        headers=exc.headers,
    )


async def handle_unexpected_exception(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Hide unhandled exception details behind the EN-02 public descriptor."""

    del request, exc
    correlation_id = _current_or_generated_correlation_id()
    logger.error(
        "Unhandled application exception.",
        extra={
            "pickup_lane_error": redact_value(
                {
                    "error_code": "API.UNEXPECTED",
                    "correlation_id": correlation_id,
                }
            )
        },
    )
    return _public_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="API.UNEXPECTED",
        message=GENERIC_UNEXPECTED_MESSAGE,
        detail=GENERIC_UNEXPECTED_DETAIL,
        correlation_id=correlation_id,
    )


def _resolve_request_correlation_id(scope: Scope) -> str:
    headers = Headers(scope=scope)
    incoming_value = headers.get(CORRELATION_ID_HEADER)
    if incoming_value:
        try:
            return validate_correlation_id(incoming_value)
        except CorrelationIdError:
            return generate_correlation_id()

    return generate_correlation_id()


def _public_error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    detail: Any,
    details: Mapping[str, Any] | None = None,
    correlation_id: str | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    active_correlation_id = correlation_id or _current_or_generated_correlation_id()
    descriptor = PublicErrorDescriptor(
        code=code,
        message=message,
        correlation_id=active_correlation_id,
        details=details,
    )
    body = {"detail": detail, **descriptor.to_dict()}
    response_headers = dict(headers or {})
    response_headers.setdefault(CORRELATION_ID_HEADER, active_correlation_id)
    return JSONResponse(
        status_code=status_code,
        content=body,
        headers=response_headers,
    )


def _current_or_generated_correlation_id() -> str:
    return get_correlation_id() or generate_correlation_id()


def _error_code_for_status(status_code: int) -> str:
    return _STATUS_ERROR_CODES.get(status_code, "API.HTTP_ERROR")


def _default_status_message(status_code: int) -> str:
    if status_code in _STATUS_MESSAGES:
        return _STATUS_MESSAGES[status_code]

    try:
        return f"{HTTPStatus(status_code).phrase}."
    except ValueError:
        return "Request failed."


def _message_from_detail(detail: Any, *, fallback: str) -> str:
    if (
        isinstance(detail, str)
        and detail != REDACTION_MARKER
        and _is_safe_public_text(detail)
    ):
        return detail

    if isinstance(detail, Mapping):
        message = detail.get("message")
        if isinstance(message, str) and _is_safe_public_text(message):
            return message

    return fallback


def _sanitize_validation_errors(errors: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [_sanitize_validation_error(error) for error in errors]


def _sanitize_validation_error(error: Mapping[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {
        "loc": _sanitize_location(error.get("loc", ())),
        "msg": _safe_public_text(error.get("msg"), fallback="Invalid input."),
        "type": _safe_public_text(error.get("type"), fallback="value_error"),
    }
    url = error.get("url")
    if isinstance(url, str) and _is_safe_public_text(url):
        sanitized["url"] = url
    return sanitized


def _sanitize_location(location: object) -> list[str | int]:
    if _is_non_string_sequence(location):
        return [_sanitize_location_item(item) for item in location]

    return [_sanitize_location_item(location)]


def _sanitize_location_item(item: object) -> str | int:
    if isinstance(item, int):
        return item
    if isinstance(item, str) and _is_safe_public_text(item):
        return item
    return REDACTION_MARKER


def _has_malformed_json_error(errors: Sequence[Mapping[str, Any]]) -> bool:
    for error in errors:
        error_type = str(error.get("type", ""))
        message = str(error.get("msg", ""))
        location = error.get("loc", [])
        first_location = location[0] if location else None
        if error_type.startswith("json_") and first_location == "body":
            return True
        if "json" in message.lower() and first_location == "body":
            return True
    return False


def _field_error_details(errors: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "location": ".".join(str(item) for item in error["loc"]),
            "description": error["msg"],
            "error_type": error["type"],
        }
        for error in errors
    ]


def _sanitize_detail(detail: Any, *, fallback: str) -> Any:
    sanitized = _sanitize_public_value(detail)
    if sanitized is None:
        return fallback
    return sanitized


def _sanitize_public_value(value: Any) -> Any:
    if isinstance(value, BaseException):
        return REDACTION_MARKER

    if isinstance(value, Mapping):
        return {
            _sanitize_public_key(key): _sanitize_public_value(item)
            for key, item in value.items()
        }

    if _is_non_string_sequence(value):
        return [_sanitize_public_value(item) for item in value]

    if isinstance(value, str):
        return value if _is_safe_public_text(value) else REDACTION_MARKER

    if value is None or isinstance(value, bool | int | float):
        return value

    return REDACTION_MARKER


def _sanitize_public_key(key: object) -> str:
    if isinstance(key, str) and _is_safe_public_text(key):
        return key
    return REDACTION_MARKER


def _safe_public_text(value: object, *, fallback: str) -> str:
    if isinstance(value, str) and _is_safe_public_text(value):
        return value
    return fallback


def _is_safe_public_text(value: str) -> bool:
    return bool(value.strip()) and not contains_sensitive_text(value)


def _is_non_string_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(
        value,
        str | bytes | bytearray,
    )
