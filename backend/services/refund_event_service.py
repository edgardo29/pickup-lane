"""Refund event helpers for provider and reconciliation history."""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Refund, RefundEvent

PROVIDER_STATUS_TO_REFUND_STATUS = {
    "processing": "processing",
    "succeeded": "succeeded",
    "failed": "failed",
    "cancelled": "cancelled",
    "canceled": "cancelled",
}


def normalize_provider_refund_status(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = value.strip().lower()
    if normalized == "canceled":
        return "cancelled"
    if normalized in {"processing", "succeeded", "failed", "cancelled"}:
        return normalized
    return "unknown"


def map_provider_status_to_refund_status(provider_status: str | None) -> str | None:
    if provider_status is None:
        return None
    return PROVIDER_STATUS_TO_REFUND_STATUS.get(provider_status)


def get_refund_event_by_idempotency_key(
    db: Session,
    idempotency_key: str | None,
) -> RefundEvent | None:
    if idempotency_key is None:
        return None
    return db.scalars(
        select(RefundEvent).where(RefundEvent.idempotency_key == idempotency_key)
    ).first()


def get_refund_event_by_provider_event_id(
    db: Session,
    *,
    provider: str | None,
    provider_event_id: str | None,
) -> RefundEvent | None:
    if provider is None or provider_event_id is None:
        return None
    return db.scalars(
        select(RefundEvent).where(
            RefundEvent.provider == provider,
            RefundEvent.provider_event_id == provider_event_id,
        )
    ).first()


def record_refund_event(
    db: Session,
    *,
    refund: Refund,
    event_type: str,
    event_source: str,
    reason_code: str,
    summary: str,
    occurred_at: datetime | None = None,
    actor_user_id: uuid.UUID | None = None,
    admin_action_id: uuid.UUID | None = None,
    idempotency_key: str | None = None,
    provider: str | None = None,
    provider_event_id: str | None = None,
    provider_refund_id: str | None = None,
    provider_charge_id: str | None = None,
    provider_status: str | None = None,
    new_refund_status: str | None = None,
    previous_refund_status: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> RefundEvent:
    existing_event = get_refund_event_by_idempotency_key(db, idempotency_key)
    if existing_event is not None:
        return existing_event

    now = occurred_at or datetime.now(timezone.utc)
    normalized_provider_status = normalize_provider_refund_status(provider_status)
    effective_provider = provider or refund.provider
    existing_provider_event = get_refund_event_by_provider_event_id(
        db,
        provider=effective_provider,
        provider_event_id=provider_event_id,
    )
    if existing_provider_event is not None:
        return existing_provider_event

    effective_provider_refund_id = provider_refund_id or refund.provider_refund_id
    effective_provider_charge_id = provider_charge_id or refund.provider_charge_id
    effective_new_refund_status = new_refund_status or map_provider_status_to_refund_status(
        normalized_provider_status
    )

    event_previous_refund_status = previous_refund_status or refund.refund_status
    if effective_new_refund_status is not None:
        refund.refund_status = effective_new_refund_status
        if effective_new_refund_status in {"approved", "processing", "succeeded"}:
            refund.approved_at = refund.approved_at or now
        if effective_new_refund_status == "succeeded":
            refund.refunded_at = refund.refunded_at or now
        elif effective_new_refund_status != "succeeded":
            refund.refunded_at = None

    if effective_provider is not None:
        refund.provider = effective_provider
    if effective_provider_refund_id is not None:
        refund.provider_refund_id = effective_provider_refund_id
    if effective_provider_charge_id is not None:
        refund.provider_charge_id = effective_provider_charge_id
    if normalized_provider_status is not None:
        refund.provider_status = normalized_provider_status
        refund.provider_status_observed_at = now

    refund.last_refund_event_at = now
    refund.updated_at = now
    db.add(refund)

    refund_event = RefundEvent(
        id=uuid.uuid4(),
        refund_id=refund.id,
        event_type=event_type,
        event_source=event_source,
        actor_user_id=actor_user_id,
        admin_action_id=admin_action_id,
        idempotency_key=idempotency_key,
        provider=effective_provider,
        provider_event_id=provider_event_id,
        provider_refund_id=effective_provider_refund_id,
        provider_charge_id=effective_provider_charge_id,
        provider_status=normalized_provider_status,
        previous_refund_status=event_previous_refund_status,
        new_refund_status=refund.refund_status,
        reason_code=reason_code,
        summary=summary,
        event_metadata=metadata,
        occurred_at=now,
        created_at=now,
    )
    db.add(refund_event)
    db.flush()
    return refund_event
