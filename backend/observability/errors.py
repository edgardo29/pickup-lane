"""Safe public error descriptors for a future stable API error envelope."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from backend.observability.correlation import validate_correlation_id
from backend.observability.redaction import contains_sensitive_text, is_sensitive_key
from backend.observability.telemetry import TelemetryLabelError, validate_error_code


class PublicErrorError(ValueError):
    """Raised when a public error descriptor would expose unsafe data."""


@dataclass(frozen=True)
class PublicErrorDescriptor:
    """Stable client-facing error metadata without internal exception details."""

    code: str
    message: str
    correlation_id: str | None = None
    details: Mapping[str, Any] | None = field(default=None)

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "code", validate_error_code(self.code))
            object.__setattr__(self, "message", _validate_public_message(self.message))
            if self.correlation_id is not None:
                object.__setattr__(
                    self,
                    "correlation_id",
                    validate_correlation_id(self.correlation_id),
                )
            if self.details is not None:
                object.__setattr__(self, "details", _validate_public_details(self.details))
        except (TelemetryLabelError, ValueError) as exc:
            raise PublicErrorError(str(exc)) from exc

    def to_dict(self) -> dict[str, object]:
        """Serialize safe public error fields."""

        payload: dict[str, object] = {
            "code": self.code,
            "message": self.message,
        }
        if self.correlation_id is not None:
            payload["correlation_id"] = self.correlation_id
        if self.details is not None:
            payload["details"] = _to_plain_public_value(self.details)
        return payload


def _validate_public_message(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PublicErrorError("Public error message must be a non-empty string.")
    if contains_sensitive_text(value):
        raise PublicErrorError("Public error message contains unsafe details.")
    return value


def _validate_public_details(details: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(details, Mapping):
        raise PublicErrorError("Public error details must be a mapping.")
    validated = {
        _validate_detail_key(key): _validate_detail_value(value)
        for key, value in sorted(details.items())
    }
    return MappingProxyType(validated)


def _validate_detail_key(key: object) -> str:
    if not isinstance(key, str) or not key.strip():
        raise PublicErrorError("Public error detail keys must be strings.")
    if key != key.strip() or is_sensitive_key(key):
        raise PublicErrorError("Public error detail key is unsafe.")
    if not key.replace("_", "").isalnum() or key.lower() != key:
        raise PublicErrorError("Public error detail key must be snake case.")
    return key


def _validate_detail_value(value: Any) -> Any:
    if isinstance(value, BaseException):
        raise PublicErrorError("Exception objects cannot be public error details.")
    if isinstance(value, Mapping):
        return _validate_public_details(value)
    if _is_non_string_sequence(value):
        return tuple(_validate_detail_value(item) for item in value)
    if isinstance(value, str):
        return _validate_public_message(value)
    if value is None or isinstance(value, bool | int | float):
        return value
    raise PublicErrorError("Public error detail value is not serializable safely.")


def _is_non_string_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray)


def _to_plain_public_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _to_plain_public_value(item) for key, item in value.items()}
    if _is_non_string_sequence(value):
        return [_to_plain_public_value(item) for item in value]
    return value
