"""Telemetry label safety rules for bounded, low-cardinality attributes."""

from __future__ import annotations

from collections.abc import Mapping
import re
from types import MappingProxyType
from urllib.parse import urlsplit

from backend.observability.redaction import contains_sensitive_text


LOW_CARDINALITY_LABEL_NAMES = frozenset(
    {
        "actor_kind",
        "environment",
        "error_code",
        "job_type",
        "operation",
        "outcome",
        "provider_kind",
        "resource_kind",
        "result",
        "route_template",
    }
)
PROHIBITED_LABEL_NAMES = frozenset(
    {
        "booking_id",
        "correlation_id",
        "email",
        "exception",
        "exception_message",
        "free_text",
        "idempotency_key",
        "message",
        "object_key",
        "payment_id",
        "phone",
        "provider_event_id",
        "raw_route_parameter",
        "request_id",
        "url",
        "user_id",
    }
)
ALLOWED_ENVIRONMENTS = frozenset(
    {"ci", "development", "local", "preview", "production", "staging", "test"}
)
# Existing operational event, reason, and status code columns use bounded
# string fields. EN-02 keeps shared code-like telemetry tokens in that range.
_MAX_CONTROLLED_TOKEN_LENGTH = 80
_MAX_ROUTE_TEMPLATE_LENGTH = 160
_LOW_CARDINALITY_TOKEN_RE = re.compile(
    r"^[a-z][a-z0-9_]*(?:[.:][a-z][a-z0-9_]*)*$"
)
_ERROR_CODE_RE = re.compile(r"^[A-Z][A-Z0-9_]*(?:[.:][A-Z][A-Z0-9_]*)*$")
_ROUTE_TEMPLATE_RE = re.compile(r"^/[A-Za-z0-9_{}./:-]*$")
_UUID_RE = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-"
    r"[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}\b"
)
_PROVIDER_IDENTIFIER_RE = re.compile(
    r"^(?:evt|pi|ch|cus|pm|seti|re|rf|fr|file)_[A-Za-z0-9_]+$"
)
_PHONEISH_RE = re.compile(
    r"(?<!\d)(?:\+?1[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}(?!\d)"
)


class TelemetryLabelError(ValueError):
    """Raised when a telemetry label is unbounded or privacy-unsafe."""


def validate_telemetry_label(name: object, value: object) -> str:
    """Validate one low-cardinality telemetry label value."""

    if not isinstance(name, str) or not name:
        raise TelemetryLabelError("Telemetry label name must be a non-empty string.")
    if not isinstance(value, str) or not value:
        raise TelemetryLabelError("Telemetry label value must be a non-empty string.")

    if name != name.strip() or name != name.lower():
        raise TelemetryLabelError("Telemetry label name must be canonical snake case.")

    if name in PROHIBITED_LABEL_NAMES or name not in LOW_CARDINALITY_LABEL_NAMES:
        raise TelemetryLabelError(f"Telemetry label {name!r} is not allowed.")

    if name == "route_template":
        if not _valid_route_template(value):
            raise TelemetryLabelError("Telemetry route template must be bounded.")
        return value

    if _is_prohibited_label_value(value):
        raise TelemetryLabelError("Telemetry label value is not privacy-safe.")

    if name == "environment":
        if value not in ALLOWED_ENVIRONMENTS:
            raise TelemetryLabelError("Telemetry environment is not approved.")
        return value

    if name == "error_code":
        if not _valid_error_code(value):
            raise TelemetryLabelError("Telemetry error code must be stable.")
        return value

    if not _valid_low_cardinality_token(value):
        raise TelemetryLabelError("Telemetry label value must be bounded.")

    return value


def validate_telemetry_labels(labels: Mapping[str, str] | None) -> Mapping[str, str]:
    """Validate a label mapping and return immutable deterministic storage."""

    if labels is None:
        return MappingProxyType({})

    validated = {
        name: validate_telemetry_label(name, value)
        for name, value in sorted(labels.items())
    }
    return MappingProxyType(validated)


def validate_error_code(value: object) -> str:
    """Validate a stable machine error code."""

    if not isinstance(value, str) or not _valid_error_code(value):
        raise TelemetryLabelError("Error code must be a stable machine code.")
    if _is_prohibited_label_value(value):
        raise TelemetryLabelError("Error code must not contain sensitive data.")
    return value


def validate_low_cardinality_token(value: object) -> str:
    """Validate an enum-like value suitable for operational event fields."""

    if not isinstance(value, str) or not _valid_low_cardinality_token(value):
        raise TelemetryLabelError("Value must be a bounded low-cardinality token.")
    if _is_prohibited_label_value(value):
        raise TelemetryLabelError("Value must not contain sensitive data.")
    return value


def _valid_low_cardinality_token(value: str) -> bool:
    return (
        len(value) <= _MAX_CONTROLLED_TOKEN_LENGTH
        and _LOW_CARDINALITY_TOKEN_RE.fullmatch(value) is not None
    )


def _valid_error_code(value: str) -> bool:
    return (
        len(value) <= _MAX_CONTROLLED_TOKEN_LENGTH
        and _ERROR_CODE_RE.fullmatch(value) is not None
    )


def _valid_route_template(value: str) -> bool:
    if len(value) > _MAX_ROUTE_TEMPLATE_LENGTH:
        return False
    if _ROUTE_TEMPLATE_RE.fullmatch(value) is None:
        return False
    if contains_sensitive_text(value):
        return False
    if _UUID_RE.search(value) or _PROVIDER_IDENTIFIER_RE.search(value):
        return False
    if "?" in value or "#" in value or "\\" in value:
        return False
    try:
        parsed = urlsplit(value)
    except ValueError:
        return False
    return not (parsed.scheme and parsed.netloc)


def _is_prohibited_label_value(value: str) -> bool:
    if value != value.strip():
        return True
    if contains_sensitive_text(value):
        return True
    if _UUID_RE.search(value) or _PROVIDER_IDENTIFIER_RE.fullmatch(value):
        return True
    if _PHONEISH_RE.search(value):
        return True
    if any(character.isspace() for character in value):
        return True
    if "/" in value or "\\" in value:
        return True

    try:
        parsed = urlsplit(value)
    except ValueError:
        return True

    return bool(parsed.scheme and parsed.netloc)
