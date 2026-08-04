"""Safe structured event-envelope contract for future observability wiring."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json

from backend.observability.correlation import get_correlation_id, validate_correlation_id
from backend.observability.redaction import contains_sensitive_text
from backend.observability.telemetry import (
    TelemetryLabelError,
    validate_error_code,
    validate_low_cardinality_token,
    validate_telemetry_label,
    validate_telemetry_labels,
)


EVENT_SCHEMA_VERSION = "1"


class EventEnvelopeError(ValueError):
    """Raised when an event envelope would include unsafe metadata."""


@dataclass(frozen=True)
class EventEnvelope:
    """Bounded structured event metadata without payloads or free-form text."""

    event_name: str
    occurred_at: datetime
    schema_version: str = EVENT_SCHEMA_VERSION
    environment: str | None = None
    release: str | None = None
    source_identity: str | None = None
    correlation_id: str | None = None
    request_id: str | None = None
    actor_kind: str | None = None
    operation: str | None = None
    resource_kind: str | None = None
    result: str | None = None
    stable_error_code: str | None = None
    provider_kind: str | None = None
    labels: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        try:
            _validate_schema_version(self.schema_version)
            _validate_event_name(self.event_name)
            _validate_occurred_at(self.occurred_at)
            object.__setattr__(self, "environment", _validate_optional_label(
                "environment",
                self.environment,
            ))
            object.__setattr__(self, "correlation_id", _validate_optional_id(
                self.correlation_id if self.correlation_id is not None else get_correlation_id()
            ))
            object.__setattr__(
                self,
                "request_id",
                _validate_optional_id(self.request_id),
            )
            object.__setattr__(self, "actor_kind", _validate_optional_label(
                "actor_kind",
                self.actor_kind,
            ))
            object.__setattr__(self, "operation", _validate_optional_label(
                "operation",
                self.operation,
            ))
            object.__setattr__(self, "resource_kind", _validate_optional_label(
                "resource_kind",
                self.resource_kind,
            ))
            object.__setattr__(self, "result", _validate_optional_label(
                "result",
                self.result,
            ))
            object.__setattr__(
                self,
                "stable_error_code",
                _validate_optional_error_code(self.stable_error_code),
            )
            object.__setattr__(self, "provider_kind", _validate_optional_label(
                "provider_kind",
                self.provider_kind,
            ))
            object.__setattr__(self, "release", _validate_release_identity(self.release))
            object.__setattr__(
                self,
                "source_identity",
                _validate_release_identity(self.source_identity),
            )
            object.__setattr__(self, "labels", validate_telemetry_labels(self.labels))
        except (TelemetryLabelError, ValueError) as exc:
            raise EventEnvelopeError(str(exc)) from exc

    def to_dict(self) -> dict[str, object]:
        """Serialize the envelope deterministically without empty fields."""

        payload: dict[str, object] = {
            "event_name": self.event_name,
            "occurred_at": _format_timestamp(self.occurred_at),
            "schema_version": self.schema_version,
        }
        optional_fields = {
            "actor_kind": self.actor_kind,
            "correlation_id": self.correlation_id,
            "environment": self.environment,
            "provider_kind": self.provider_kind,
            "release": self.release,
            "request_id": self.request_id,
            "resource_kind": self.resource_kind,
            "result": self.result,
            "source_identity": self.source_identity,
            "stable_error_code": self.stable_error_code,
            "operation": self.operation,
        }
        payload.update(
            (key, value)
            for key, value in sorted(optional_fields.items())
            if value is not None
        )
        if self.labels:
            payload["labels"] = dict(sorted(self.labels.items()))
        return payload

    def to_json(self) -> str:
        """Serialize the envelope to deterministic JSON."""

        return json.dumps(self.to_dict(), separators=(",", ":"), sort_keys=True)


def _validate_schema_version(value: str) -> None:
    if value != EVENT_SCHEMA_VERSION:
        raise EventEnvelopeError("Event schema version is not supported.")


def _validate_event_name(value: str) -> None:
    try:
        validate_low_cardinality_token(value)
    except TelemetryLabelError as exc:
        raise EventEnvelopeError("Event name must be a bounded code token.") from exc


def _validate_occurred_at(value: datetime) -> None:
    if not isinstance(value, datetime):
        raise EventEnvelopeError("Event timestamp must be a datetime.")
    if value.tzinfo is None or value.utcoffset() is None:
        raise EventEnvelopeError("Event timestamp must be timezone-aware.")


def _validate_optional_id(value: str | None) -> str | None:
    if value is None:
        return None
    return validate_correlation_id(value)


def _validate_optional_label(name: str, value: str | None) -> str | None:
    if value is None:
        return None
    return validate_telemetry_label(name, value)


def _validate_optional_error_code(value: str | None) -> str | None:
    if value is None:
        return None
    return validate_error_code(value)


def _validate_release_identity(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or value != value.strip() or not value:
        raise EventEnvelopeError("Release identity must be a non-empty string.")
    if any(character in value for character in ("\x00", "\n", "\r", "\t")):
        raise EventEnvelopeError("Release identity must not contain controls.")
    if contains_sensitive_text(value):
        raise EventEnvelopeError("Release identity must not contain sensitive data.")
    return value


def _format_timestamp(value: datetime) -> str:
    utc_value = value.astimezone(timezone.utc)
    return utc_value.isoformat().replace("+00:00", "Z")
