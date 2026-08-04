"""Shared observability primitives for safe correlation and event metadata."""

from backend.observability.correlation import (
    CORRELATION_ID_HEADER,
    CorrelationIdError,
    correlation_context,
    generate_correlation_id,
    get_correlation_id,
    reset_correlation_id,
    resolve_correlation_id,
    set_correlation_id,
    validate_correlation_id,
)
from backend.observability.errors import PublicErrorDescriptor, PublicErrorError
from backend.observability.events import EventEnvelope, EventEnvelopeError
from backend.observability.redaction import REDACTION_MARKER, redact_value
from backend.observability.telemetry import (
    TelemetryLabelError,
    validate_telemetry_label,
    validate_telemetry_labels,
)

__all__ = [
    "CORRELATION_ID_HEADER",
    "CorrelationIdError",
    "EventEnvelope",
    "EventEnvelopeError",
    "PublicErrorDescriptor",
    "PublicErrorError",
    "REDACTION_MARKER",
    "TelemetryLabelError",
    "correlation_context",
    "generate_correlation_id",
    "get_correlation_id",
    "redact_value",
    "reset_correlation_id",
    "resolve_correlation_id",
    "set_correlation_id",
    "validate_correlation_id",
    "validate_telemetry_label",
    "validate_telemetry_labels",
]
