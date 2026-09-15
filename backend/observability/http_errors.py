"""FastAPI error normalization using the EN-02 public error primitives."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from http import HTTPStatus
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
    optional_correlation_context,
    reset_correlation_id,
    set_correlation_id,
    validate_correlation_id,
)
from backend.observability.errors import PublicErrorDescriptor
from backend.observability.events import EventEnvelope
from backend.observability.redaction import (
    REDACTION_MARKER,
    contains_sensitive_text,
)
from backend.observability.structured_logging import (
    RuntimeEventEmitter,
    emit_event,
    emit_event_with_correlation,
    event_emitter_context,
)
from backend.observability.telemetry import TelemetryLabelError, validate_error_code
from backend.observability.timeouts import public_timeout_contract

GENERIC_UNEXPECTED_DETAIL = "An unexpected error occurred."
GENERIC_UNEXPECTED_MESSAGE = "Something went wrong. Please try again."
VALIDATION_FAILED_MESSAGE = "Request validation failed."
MALFORMED_JSON_MESSAGE = "Malformed JSON request body."
HTTP_STATUS_UNPROCESSABLE_ENTITY = 422
_REQUEST_LOGGING_STATE_KEY = "_pickup_lane_logging"

_STATUS_ERROR_CODES: dict[int, str] = {
    status.HTTP_400_BAD_REQUEST: "API.BAD_REQUEST",
    status.HTTP_401_UNAUTHORIZED: "AUTH.UNAUTHENTICATED",
    status.HTTP_403_FORBIDDEN: "AUTH.FORBIDDEN",
    status.HTTP_404_NOT_FOUND: "API.NOT_FOUND",
    status.HTTP_405_METHOD_NOT_ALLOWED: "API.METHOD_NOT_ALLOWED",
    status.HTTP_409_CONFLICT: "API.CONFLICT",
    status.HTTP_429_TOO_MANY_REQUESTS: "API.RATE_LIMITED",
    status.HTTP_413_CONTENT_TOO_LARGE: "API.REQUEST_BODY_TOO_LARGE",
    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: "API.UNSUPPORTED_MEDIA_TYPE",
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
    status.HTTP_429_TOO_MANY_REQUESTS: "Rate limit exceeded.",
    status.HTTP_413_CONTENT_TOO_LARGE: "Request body is too large.",
    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: "Unsupported media type.",
    HTTP_STATUS_UNPROCESSABLE_ENTITY: VALIDATION_FAILED_MESSAGE,
    status.HTTP_500_INTERNAL_SERVER_ERROR: GENERIC_UNEXPECTED_MESSAGE,
    status.HTTP_503_SERVICE_UNAVAILABLE: "Service unavailable.",
}
_APPROVED_HTTP_EXCEPTION_HEADERS: dict[int, dict[str, str]] = {
    status.HTTP_401_UNAUTHORIZED: {"www-authenticate": "WWW-Authenticate"},
    status.HTTP_405_METHOD_NOT_ALLOWED: {"allow": "Allow"},
    status.HTTP_429_TOO_MANY_REQUESTS: {"retry-after": "Retry-After"},
}


class CorrelationIdMiddleware:
    """Set a safe request correlation ID and mirror it in HTTP responses."""

    def __init__(self, app: ASGIApp, *, event_emitter: RuntimeEventEmitter) -> None:
        self.app = app
        self._event_emitter = event_emitter

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        correlation_id = _resolve_request_correlation_id(scope)
        token = set_correlation_id(correlation_id)
        logging_state = {
            "correlation_id": correlation_id,
            "event_emitter": self._event_emitter,
            "http_method": _http_method(scope),
            "http_status_code": None,
            "response_started": False,
            "route_template": "/{unmatched}",
        }
        state = scope.setdefault("state", {})
        if isinstance(state, dict):
            state[_REQUEST_LOGGING_STATE_KEY] = logging_state

        async def send_with_correlation_header(message: Message) -> None:
            if message["type"] == "http.response.start":
                if not logging_state["response_started"]:
                    logging_state["http_status_code"] = int(message["status"])
                    logging_state["response_started"] = True
                headers = MutableHeaders(scope=message)
                headers.setdefault(CORRELATION_ID_HEADER, correlation_id)
            await send(message)

        try:
            with event_emitter_context(self._event_emitter):
                try:
                    await self.app(scope, receive, send_with_correlation_header)
                except BaseException:
                    logging_state["route_template"] = _route_template(scope)
                    raise
                logging_state["route_template"] = _route_template(scope)
                status_code = logging_state["http_status_code"]
                if isinstance(status_code, int):
                    _emit_http_completion(
                        status_code=status_code,
                        method=str(logging_state["http_method"]),
                        route_template=str(logging_state["route_template"]),
                    )
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
    code = _error_code_from_detail(detail) or _error_code_for_status(exc.status_code)

    return _public_error_response(
        status_code=exc.status_code,
        code=code,
        message=message,
        detail=detail,
        headers=_approved_http_exception_headers(exc.status_code, exc.headers),
    )


async def handle_unexpected_exception(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Hide unhandled exception details behind the EN-02 public descriptor."""

    logging_state = _request_logging_state(request)
    correlation_id = (
        str(logging_state["correlation_id"])
        if logging_state is not None
        else _current_or_generated_correlation_id()
    )
    timeout_contract = public_timeout_contract(exc)
    if timeout_contract is not None:
        timeout_labels = timeout_contract.telemetry_labels
        _emit_outer_request_event(
            logging_state,
            correlation_id,
            "application.timeout",
            "warning",
            {
                "operation": timeout_labels.get("operation", "application.timeout"),
                "provider_kind": timeout_labels.get("provider_kind"),
                "resource_kind": timeout_labels.get("resource_kind"),
                "result": timeout_labels.get("outcome", "retry_later"),
                "stable_error_code": timeout_contract.code,
            },
        )
        response = _public_error_response(
            status_code=timeout_contract.status_code,
            code=timeout_contract.code,
            message=timeout_contract.message,
            detail=timeout_contract.detail,
            details=timeout_contract.details,
            correlation_id=correlation_id,
        )
        _emit_outer_completion(
            logging_state, correlation_id, timeout_contract.status_code
        )
        return response

    del exc
    _emit_outer_request_event(
        logging_state,
        correlation_id,
        "application.unexpected_error",
        "error",
        {
            "operation": "http.request",
            "result": "failed",
            "stable_error_code": "API.UNEXPECTED",
        },
    )
    response = _public_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="API.UNEXPECTED",
        message=GENERIC_UNEXPECTED_MESSAGE,
        detail=GENERIC_UNEXPECTED_DETAIL,
        correlation_id=correlation_id,
    )
    _emit_outer_completion(
        logging_state,
        correlation_id,
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
    return response


def _request_logging_state(request: Request | None) -> dict[str, object] | None:
    if request is None:
        return None
    scope = getattr(request, "scope", None)
    if not isinstance(scope, dict):
        return None
    state = scope.get("state")
    if not isinstance(state, dict):
        return None
    candidate = state.get(_REQUEST_LOGGING_STATE_KEY)
    if not isinstance(candidate, dict):
        return None
    correlation_id = candidate.get("correlation_id")
    emitter = candidate.get("event_emitter")
    try:
        validate_correlation_id(correlation_id)
    except CorrelationIdError:
        return None
    if not isinstance(emitter, RuntimeEventEmitter):
        return None
    return candidate


def _emit_outer_request_event(
    logging_state: dict[str, object] | None,
    correlation_id: str,
    event_name: str,
    severity: str,
    fields: Mapping[str, object],
) -> None:
    clean_fields = {key: value for key, value in fields.items() if value is not None}
    if logging_state is not None:
        emit_event_with_correlation(
            logging_state["event_emitter"],  # type: ignore[arg-type]
            correlation_id,
            event_name,
            severity,
            clean_fields,
        )
        return
    with optional_correlation_context(correlation_id):
        emit_event(event_name, severity, clean_fields)


def _emit_outer_completion(
    logging_state: dict[str, object] | None,
    correlation_id: str,
    fallback_status: int,
) -> None:
    if logging_state is None:
        return
    captured_status = logging_state.get("http_status_code")
    status_code = (
        captured_status if isinstance(captured_status, int) else fallback_status
    )
    route_template = str(logging_state.get("route_template") or "/{unmatched}")
    method = str(logging_state.get("http_method") or "other")
    emitter = logging_state["event_emitter"]
    with optional_correlation_context(correlation_id), event_emitter_context(emitter):  # type: ignore[arg-type]
        _emit_http_completion(
            status_code=status_code,
            method=method,
            route_template=route_template,
        )


def _emit_http_completion(
    *,
    status_code: int,
    method: str,
    route_template: str,
) -> None:
    if status_code < 400:
        severity, result = "info", "success"
    elif status_code < 500:
        severity, result = "warning", "client_error"
    else:
        severity, result = "error", "server_error"
    emit_event(
        "http.request",
        severity,
        {
            "http_method": method,
            "http_status_code": status_code,
            "labels": {"route_template": route_template},
            "result": result,
        },
    )


def _http_method(scope: Scope) -> str:
    method = str(scope.get("method") or "").lower()
    return (
        method
        if method in {"delete", "get", "head", "options", "patch", "post", "put"}
        else "other"
    )


def _route_template(scope: Scope) -> str:
    route = scope.get("route")
    candidate = getattr(route, "path", None)
    if not isinstance(candidate, str):
        return "/{unmatched}"
    try:
        EventEnvelope(
            event_name="http.request",
            occurred_at=datetime.now(timezone.utc),
            labels={"route_template": candidate},
        )
    except Exception:  # noqa: BLE001 - unsafe paths collapse to one fixed route.
        return "/{unmatched}"
    return candidate


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


def _approved_http_exception_headers(
    status_code: int,
    headers: Mapping[str, str] | None,
) -> dict[str, str]:
    approved_names = _APPROVED_HTTP_EXCEPTION_HEADERS.get(status_code)
    if not approved_names or not headers:
        return {}

    filtered: dict[str, str] = {}
    for name, value in headers.items():
        canonical_name = approved_names.get(name.lower())
        if canonical_name is not None:
            filtered[canonical_name] = value
    return filtered


def _error_code_from_detail(detail: Any) -> str | None:
    if not isinstance(detail, Mapping):
        return None

    try:
        return validate_error_code(detail.get("code"))
    except TelemetryLabelError:
        return None


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


def _sanitize_validation_errors(
    errors: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
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
