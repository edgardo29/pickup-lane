"""Refuse requests that repeat a singular security header (P06.R03)."""

from __future__ import annotations

from collections import Counter

from fastapi import status
from starlette.types import ASGIApp, Receive, Scope, Send

from backend.observability.http_errors import public_error_response

# Headers the app reads as one value for login, App Check, Stripe signatures,
# and idempotency. The framework keeps only the first copy of a repeated
# header, so a repeat is refused rather than letting one copy be chosen.
# ASGI servers pass header names in lowercase.
SINGULAR_SECURITY_HEADERS = frozenset(
    {
        b"authorization",
        b"x-firebase-appcheck",
        b"stripe-signature",
        b"idempotency-key",
    }
)

REPEATED_SECURITY_HEADER_CODE = "API.REPEATED_SECURITY_HEADER"
REPEATED_SECURITY_HEADER_MESSAGE = "A security header was sent more than once."
REPEATED_SECURITY_HEADER_DETAIL = "Send each security header only once."


class RepeatedSecurityHeaderMiddleware:
    """Refuse a repeated security header with 400, as RFC 6750 section 3.1 does."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            counts = Counter(name for name, _value in scope["headers"])
            if any(counts[name] > 1 for name in SINGULAR_SECURITY_HEADERS):
                response = public_error_response(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    code=REPEATED_SECURITY_HEADER_CODE,
                    message=REPEATED_SECURITY_HEADER_MESSAGE,
                    detail=REPEATED_SECURITY_HEADER_DETAIL,
                )
                await response(scope, receive, send)
                return

        await self.app(scope, receive, send)
