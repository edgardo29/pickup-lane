"""Pure WS05-02 payment, reservation, and provider identity policy."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

PAYMENT_STATES = frozenset(
    {
        "requires_payment_method",
        "requires_confirmation",
        "requires_action",
        "processing",
        "requires_capture",
        "succeeded",
        "failed",
        "canceled",
        "unknown",
    }
)
PROVIDER_PAYMENT_INTENT_STATES = frozenset(PAYMENT_STATES - {"failed", "unknown"})
PENDING_PAYMENT_STATES = frozenset(
    {
        "requires_payment_method",
        "requires_confirmation",
        "requires_action",
        "processing",
        "requires_capture",
        "unknown",
    }
)
TERMINAL_PAYMENT_STATES = frozenset({"succeeded", "canceled"})
RESERVATION_STATES = frozenset(
    {"not_required", "held", "confirmed", "released", "capacity_conflict"}
)
WEBHOOK_RETRY_DELAYS_SECONDS = (1, 5, 30, 120)
PAYMENT_RECONCILE_RETRY_DELAYS_SECONDS = (1, 5, 30, 120)
PAYMENT_METHOD_RECONCILE_RETRY_DELAYS_SECONDS = (1, 5, 30, 120)
PAYMENT_JOB_MAXIMUM_ATTEMPTS = 5

def canonical_fingerprint(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def normalize_provider_payment_status(provider_status: str | None) -> str:
    exact_status = exact_provider_payment_status(provider_status)
    if exact_status in PROVIDER_PAYMENT_INTENT_STATES:
        return exact_status
    return "unknown"


def exact_provider_payment_status(provider_status: str | None) -> str | None:
    if provider_status is None:
        return None
    exact_status = str(provider_status).strip()
    return exact_status or None


def provider_observation_can_advance(
    current_state: str,
    observed_state: str,
) -> bool:
    if current_state == observed_state:
        return True
    if current_state in TERMINAL_PAYMENT_STATES:
        return False
    if current_state == "failed":
        return observed_state in {"succeeded", "canceled"}
    if observed_state == "unknown":
        return current_state not in TERMINAL_PAYMENT_STATES
    return observed_state in PAYMENT_STATES


def retry_delay_seconds(attempt_count: int, schedule: tuple[int, ...]) -> int:
    if attempt_count < 1:
        raise ValueError("attempt_count must be positive")
    return schedule[min(attempt_count - 1, len(schedule) - 1)]


def booking_reservation_pair_is_valid(
    booking_status: str,
    reservation_status: str,
    *,
    has_expiry: bool,
) -> bool:
    expected = {
        "pending_payment": {"held"},
        "confirmed": {"confirmed"},
        "partially_cancelled": {"confirmed"},
        "waitlisted": {"not_required"},
        "expired": {"released"},
        "failed": {"released"},
        "capacity_conflict": {"capacity_conflict"},
        "cancelled": {"released", "not_required"},
    }
    return (
        reservation_status in expected.get(booking_status, set())
        and has_expiry == (reservation_status == "held")
    )
