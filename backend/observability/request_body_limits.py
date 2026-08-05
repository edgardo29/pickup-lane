"""Source-owned request body limits for approved request classes."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import status
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from backend.observability.http_errors import public_error_response


DEFAULT_PLATFORM_NOTICE_REQUEST_BODY_LIMIT_BYTES = 160 * 1024
DEFAULT_STRIPE_WEBHOOK_REQUEST_BODY_LIMIT_BYTES = 64 * 1024

PLATFORM_NOTICE_CREATE_PATH = "/admin/platform-notices"
STRIPE_WEBHOOK_PATH = "/stripe/webhook"

REQUEST_BODY_TOO_LARGE_CODE = "API.REQUEST_BODY_TOO_LARGE"
REQUEST_BODY_TOO_LARGE_MESSAGE = "Request body is too large."
REQUEST_BODY_TOO_LARGE_DETAIL = "Request body exceeds the approved application limit."
UNSUPPORTED_CONTENT_ENCODING_CODE = "API.UNSUPPORTED_CONTENT_ENCODING"
UNSUPPORTED_CONTENT_ENCODING_MESSAGE = "Unsupported content encoding."
UNSUPPORTED_CONTENT_ENCODING_DETAIL = (
    "Compressed request bodies are not supported for this endpoint."
)

_CONTENT_ENCODING_HEADER = b"content-encoding"
_CONTENT_LENGTH_HEADER = b"content-length"
_STRIPE_SIGNATURE_HEADER = b"stripe-signature"


class RequestBodyLimitExceeded(Exception):
    """Raised when a limited ASGI request exceeds its approved byte budget."""


@dataclass(frozen=True)
class RequestBodyLimit:
    """A selected application-owned request body limit."""

    name: str
    limit_bytes: int


class RequestBodyLimitMiddleware:
    """Count request bytes for the approved limited request classes only."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        platform_notice_request_body_limit_bytes: int,
        stripe_webhook_request_body_limit_bytes: int,
    ) -> None:
        self.app = app
        self._platform_notice_limit = RequestBodyLimit(
            name="platform_notice_create",
            limit_bytes=platform_notice_request_body_limit_bytes,
        )
        self._stripe_webhook_limit = RequestBodyLimit(
            name="stripe_webhook",
            limit_bytes=stripe_webhook_request_body_limit_bytes,
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_limit = self._limit_for_scope(scope)
        if request_limit is None:
            await self.app(scope, receive, send)
            return

        if _has_unsupported_content_encoding(scope):
            await self._send_unsupported_content_encoding(scope, receive, send)
            return

        declared_length = _single_valid_content_length(scope)
        if declared_length is not None and declared_length > request_limit.limit_bytes:
            await self._send_request_body_too_large(scope, receive, send)
            return

        response_started = False

        async def send_with_state(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        limited_receive = _CountingReceive(receive, request_limit.limit_bytes)
        try:
            await self.app(scope, limited_receive, send_with_state)
        except RequestBodyLimitExceeded:
            if response_started:
                raise
            await self._send_request_body_too_large(scope, receive, send)

    def _limit_for_scope(self, scope: Scope) -> RequestBodyLimit | None:
        method = str(scope.get("method") or "").upper()
        path = _normalized_path(scope)

        if method == "POST" and path == PLATFORM_NOTICE_CREATE_PATH:
            return self._platform_notice_limit
        if (
            method == "POST"
            and path == STRIPE_WEBHOOK_PATH
            and _has_header(scope, _STRIPE_SIGNATURE_HEADER)
        ):
            return self._stripe_webhook_limit
        return None

    async def _send_request_body_too_large(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        response = public_error_response(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            code=REQUEST_BODY_TOO_LARGE_CODE,
            message=REQUEST_BODY_TOO_LARGE_MESSAGE,
            detail=REQUEST_BODY_TOO_LARGE_DETAIL,
        )
        await response(scope, receive, send)

    async def _send_unsupported_content_encoding(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        response = public_error_response(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            code=UNSUPPORTED_CONTENT_ENCODING_CODE,
            message=UNSUPPORTED_CONTENT_ENCODING_MESSAGE,
            detail=UNSUPPORTED_CONTENT_ENCODING_DETAIL,
        )
        await response(scope, receive, send)


class _CountingReceive:
    def __init__(self, receive: Receive, limit_bytes: int) -> None:
        self._receive = receive
        self._limit_bytes = limit_bytes
        self._received_bytes = 0

    async def __call__(self) -> Message:
        message = await self._receive()
        if message["type"] != "http.request":
            return message

        body = message.get("body", b"")
        if body:
            self._received_bytes += len(body)
            if self._received_bytes > self._limit_bytes:
                raise RequestBodyLimitExceeded
        return message


def _normalized_path(scope: Scope) -> str:
    path = str(scope.get("path") or "")
    if path != "/" and path.endswith("/"):
        return path.rstrip("/")
    return path


def _has_header(scope: Scope, header_name: bytes) -> bool:
    return any(name.lower() == header_name for name, _value in _raw_headers(scope))


def _has_unsupported_content_encoding(scope: Scope) -> bool:
    values = [
        value.decode("latin-1").strip().lower()
        for name, value in _raw_headers(scope)
        if name.lower() == _CONTENT_ENCODING_HEADER
    ]
    for value in values:
        encodings = [encoding.strip() for encoding in value.split(",")]
        if any(encoding and encoding != "identity" for encoding in encodings):
            return True
    return False


def _single_valid_content_length(scope: Scope) -> int | None:
    values = [
        value.decode("latin-1").strip()
        for name, value in _raw_headers(scope)
        if name.lower() == _CONTENT_LENGTH_HEADER
    ]
    if len(values) != 1:
        return None

    value = values[0]
    if not value.isdecimal():
        return None
    return int(value)


def _raw_headers(scope: Scope) -> list[tuple[bytes, bytes]]:
    return list(scope.get("headers") or [])
