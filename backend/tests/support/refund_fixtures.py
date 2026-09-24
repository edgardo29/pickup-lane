"""Canonical Refund fixtures that preserve production identity invariants."""

import uuid
from datetime import datetime, timezone
from typing import Any

from backend.models import Refund, RefundEvent


def build_direct_admin_refund(
    *,
    payment_id: uuid.UUID,
    amount_cents: int,
    refund_status: str,
    provider_charge_id: str | None,
    booking_id: uuid.UUID | None = None,
    participant_id: uuid.UUID | None = None,
    host_publish_fee_id: uuid.UUID | None = None,
    provider_refund_id: str | None = None,
    provider_status: str | None = None,
    requested_by_user_id: uuid.UUID | None = None,
    now: datetime | None = None,
) -> Refund:
    occurred_at = now or datetime.now(timezone.utc)
    refund_id = uuid.uuid4()
    attempt_number = 1
    started = provider_refund_id is not None or refund_status in {
        "processing",
        "succeeded",
        "failed",
        "cancelled",
    }
    return Refund(
        id=refund_id,
        payment_id=payment_id,
        booking_id=booking_id,
        participant_id=participant_id,
        host_publish_fee_id=host_publish_fee_id,
        origin_workflow="direct_admin_refund",
        origin_operation_key=f"direct_admin_refund:refund:{refund_id}",
        current_attempt_number=attempt_number,
        stripe_request_key=f"refund:{refund_id}:attempt:{attempt_number}",
        provider_attempt_started_at=occurred_at if started else None,
        provider="stripe",
        provider_refund_id=provider_refund_id,
        provider_charge_id=provider_charge_id,
        provider_status=provider_status,
        provider_status_observed_at=(
            occurred_at if provider_status is not None else None
        ),
        amount_cents=amount_cents,
        currency="USD",
        refund_reason="admin_refund",
        refund_status=refund_status,
        requested_by_user_id=requested_by_user_id,
        requested_at=occurred_at,
        approved_at=(
            occurred_at
            if refund_status in {"approved", "processing", "succeeded"}
            else None
        ),
        refunded_at=occurred_at if refund_status == "succeeded" else None,
        created_at=occurred_at,
        updated_at=occurred_at,
    )


def build_official_cancellation_refund(
    *,
    game_id: uuid.UUID,
    payment_id: uuid.UUID,
    booking_id: uuid.UUID,
    amount_cents: int,
    refund_status: str,
    provider_charge_id: str | None,
    provider_refund_id: str | None,
    requested_by_user_id: uuid.UUID | None = None,
    now: datetime | None = None,
) -> Refund:
    refund = build_direct_admin_refund(
        payment_id=payment_id,
        booking_id=booking_id,
        amount_cents=amount_cents,
        refund_status=refund_status,
        provider_charge_id=provider_charge_id,
        provider_refund_id=provider_refund_id,
        provider_status=(
            refund_status if refund_status in {"processing", "succeeded", "failed"}
            else None
        ),
        requested_by_user_id=requested_by_user_id,
        now=now,
    )
    refund.origin_workflow = "official_game_cancellation"
    refund.origin_operation_key = (
        f"official_game_cancellation:game:{game_id}:payment:{payment_id}"
    )
    refund.refund_reason = "game_cancelled"
    return refund


def build_publish_fee_refund(
    *,
    financial_outcome_id: uuid.UUID,
    payment_id: uuid.UUID,
    host_publish_fee_id: uuid.UUID,
    amount_cents: int,
    refund_status: str,
    provider_charge_id: str | None,
    provider_refund_id: str | None,
    requested_by_user_id: uuid.UUID | None = None,
    now: datetime | None = None,
) -> Refund:
    refund = build_direct_admin_refund(
        payment_id=payment_id,
        host_publish_fee_id=host_publish_fee_id,
        amount_cents=amount_cents,
        refund_status=refund_status,
        provider_charge_id=provider_charge_id,
        provider_refund_id=provider_refund_id,
        provider_status=(
            refund_status if refund_status in {"processing", "succeeded", "failed"}
            else None
        ),
        requested_by_user_id=requested_by_user_id,
        now=now,
    )
    refund.origin_workflow = "community_publish_fee_refund"
    refund.origin_operation_key = (
        f"community_publish_fee_refund:financial_outcome:{financial_outcome_id}"
    )
    refund.refund_reason = "publish_fee_refund"
    return refund


def build_refund_event(
    *,
    refund: Refund,
    event_type: str,
    event_source: str,
    reason_code: str,
    summary: str,
    new_refund_status: str | None,
    provider_event_id: str | None = None,
    provider_status: str | None = None,
    idempotency_key: str | None = None,
    metadata: dict[str, Any] | None = None,
    occurred_at: datetime | None = None,
) -> RefundEvent:
    event_at = occurred_at or datetime.now(timezone.utc)
    return RefundEvent(
        id=uuid.uuid4(),
        refund_id=refund.id,
        event_type=event_type,
        event_source=event_source,
        idempotency_key=idempotency_key,
        attempt_number=refund.current_attempt_number,
        attempt_amount_cents=refund.amount_cents,
        attempt_currency=refund.currency,
        attempt_request_key=refund.stripe_request_key,
        provider=refund.provider,
        provider_event_id=provider_event_id,
        provider_refund_id=refund.provider_refund_id,
        provider_charge_id=refund.provider_charge_id,
        provider_status=provider_status,
        previous_refund_status=refund.refund_status,
        new_refund_status=new_refund_status,
        reason_code=reason_code,
        summary=summary,
        event_metadata=metadata,
        occurred_at=event_at,
        created_at=event_at,
    )
