"""Correlation ID generation, validation, and request-local context."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar, Token
import re
import uuid


CORRELATION_ID_HEADER = "X-Request-ID"
_CANONICAL_UUID_TEXT_LENGTH = 36
_CONTROL_CHARACTER_RE = re.compile(r"[\x00-\x1f\x7f]")
_correlation_id: ContextVar[str | None] = ContextVar(
    "pickup_lane_correlation_id",
    default=None,
)


class CorrelationIdError(ValueError):
    """Raised when a correlation identifier is not safe to accept."""


def generate_correlation_id() -> str:
    """Generate a canonical server-owned UUIDv4 correlation identifier."""

    return str(uuid.uuid4())


def validate_correlation_id(value: object) -> str:
    """Validate a canonical UUIDv4 correlation identifier.

    Externally supplied values are treated as untrusted input. EN-02 does not
    accept arbitrary request-ID formats because the approved decisions do not
    define a broader safe external format.
    """

    if not isinstance(value, str):
        raise CorrelationIdError("Correlation ID must be a string.")

    if value != value.strip():
        raise CorrelationIdError("Correlation ID must not contain padding.")

    if _CONTROL_CHARACTER_RE.search(value):
        raise CorrelationIdError("Correlation ID must not contain control characters.")

    if len(value) != _CANONICAL_UUID_TEXT_LENGTH:
        raise CorrelationIdError("Correlation ID must be a canonical UUID.")

    try:
        parsed = uuid.UUID(value)
    except ValueError as exc:
        raise CorrelationIdError("Correlation ID must be a canonical UUID.") from exc

    if parsed.version != 4 or str(parsed) != value:
        raise CorrelationIdError("Correlation ID must be a canonical UUIDv4 value.")

    return value


def resolve_correlation_id(incoming_value: object | None = None) -> str:
    """Return a trusted correlation ID, generating one when none was supplied."""

    if incoming_value is None or incoming_value == "":
        return generate_correlation_id()

    return validate_correlation_id(incoming_value)


def set_correlation_id(correlation_id: object) -> Token[str | None]:
    """Set request/event-local correlation context and return a reset token."""

    return _correlation_id.set(validate_correlation_id(correlation_id))


def get_correlation_id() -> str | None:
    """Return the current context correlation ID, if one has been set."""

    return _correlation_id.get()


def reset_correlation_id(token: Token[str | None]) -> None:
    """Reset correlation context using the token returned by set_correlation_id."""

    _correlation_id.reset(token)


@contextmanager
def correlation_context(correlation_id: object) -> Iterator[str]:
    """Temporarily set correlation context and restore the prior value."""

    token = set_correlation_id(correlation_id)
    try:
        yield get_correlation_id() or ""
    finally:
        reset_correlation_id(token)
