"""Shared rules for admin operational records."""

import re
import uuid
from datetime import date, datetime
from typing import Any

from fastapi import HTTPException, status

MAX_REASON_LENGTH = 1000
MAX_IDEMPOTENCY_KEY_LENGTH = 160
MAX_METADATA_STRING_LENGTH = 2000
MAX_METADATA_LIST_LENGTH = 100
MAX_METADATA_DICT_KEYS = 100

FORBIDDEN_METADATA_KEY_FRAGMENTS = {
    "auth_user_id",
    "firebase_uid",
    "firebase",
    "stripe_customer_id",
    "stripe_payment_method_id",
    "card_fingerprint",
    "raw_payload",
    "raw_request",
    "request_body",
    "headers",
    "authorization",
    "token",
    "cookie",
    "client_secret",
    "stripe_payload",
    "message_body",
    "body_text",
}

SENSITIVE_NOTE_PATTERNS = (
    "authorization:",
    "bearer ",
    "client_secret",
    "firebase_uid",
    "stripe_customer_id",
    "stripe_payment_method_id",
    "card_fingerprint",
    "sk_live_",
    "sk_test_",
)

SENSITIVE_METADATA_VALUE_PATTERNS = SENSITIVE_NOTE_PATTERNS + (
    "whsec_",
    "rk_live_",
    "rk_test_",
)

SENSITIVE_METADATA_VALUE_REGEXES = (
    re.compile(r"\b(pm|cus|seti|pi|ch|card)_[A-Za-z0-9]+"),
)


def normalize_optional_text(
    value: str | None,
    field_name: str,
    *,
    max_length: int = MAX_REASON_LENGTH,
) -> str | None:
    if value is None:
        return None

    normalized = " ".join(value.strip().split())
    if not normalized:
        return None

    if len(normalized) > max_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must be {max_length} characters or fewer.",
        )

    return normalized


def normalize_idempotency_key(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = value.strip()
    if not normalized:
        return None

    if len(normalized) > MAX_IDEMPOTENCY_KEY_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "idempotency_key must be "
                f"{MAX_IDEMPOTENCY_KEY_LENGTH} characters or fewer."
            ),
        )

    return normalized


def describe_fields(fields: tuple[str, ...] | list[str] | set[str]) -> str:
    return ", ".join(sorted(fields))


def validate_metadata_key(key: str) -> None:
    normalized_key = key.strip().lower()
    if not normalized_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="metadata keys cannot be empty.",
        )

    if any(fragment in normalized_key for fragment in FORBIDDEN_METADATA_KEY_FRAGMENTS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="metadata contains a forbidden sensitive field.",
        )


def validate_metadata_string_value(value: str) -> None:
    lower_value = value.lower()
    if any(pattern in lower_value for pattern in SENSITIVE_METADATA_VALUE_PATTERNS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="metadata contains a forbidden sensitive value.",
        )

    if any(regex.search(value) for regex in SENSITIVE_METADATA_VALUE_REGEXES):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="metadata contains a forbidden sensitive value.",
        )


def normalize_metadata_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float)):
        return value

    if isinstance(value, uuid.UUID):
        return str(value)

    if isinstance(value, datetime | date):
        return value.isoformat()

    if isinstance(value, str):
        if len(value) > MAX_METADATA_STRING_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "metadata string values must be "
                    f"{MAX_METADATA_STRING_LENGTH} characters or fewer."
                ),
            )
        validate_metadata_string_value(value)
        return value

    if isinstance(value, list):
        if len(value) > MAX_METADATA_LIST_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "metadata lists must contain "
                    f"{MAX_METADATA_LIST_LENGTH} items or fewer."
                ),
            )
        return [normalize_metadata_value(item) for item in value]

    if isinstance(value, dict):
        if len(value) > MAX_METADATA_DICT_KEYS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "metadata objects must contain "
                    f"{MAX_METADATA_DICT_KEYS} keys or fewer."
                ),
            )

        normalized_dict = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="metadata keys must be strings.",
                )
            validate_metadata_key(key)
            normalized_dict[key] = normalize_metadata_value(item)
        return normalized_dict

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="metadata values must be JSON primitives, arrays, or objects.",
    )
