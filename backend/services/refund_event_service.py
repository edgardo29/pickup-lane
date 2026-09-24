"""Refund event helpers for provider and reconciliation history."""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Refund, RefundEvent
from backend.services.refund_attempt_policy import canonical_provider_attempt_event

_UNSET_REFUND_STATUS = object()

PROVIDER_STATUS_TO_REFUND_STATUS = {
    "processing": "processing",
    "succeeded": "succeeded",
    "failed": "failed",
    "cancelled": "cancelled",
    "canceled": "cancelled",
}

TERMINAL_PROVIDER_REFUND_STATUSES = {"succeeded", "failed", "cancelled"}


def provider_observation_can_update_refund(
    *, current_status: str, observed_status: str | None
) -> bool:
    """Keep provider observations monotonic for one immutable refund attempt."""
    if observed_status is None or observed_status == current_status:
        return True
    if current_status == "succeeded":
        return False
    if observed_status == "succeeded":
        return True
    return current_status not in {"failed", "cancelled"}


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
    refund_id: uuid.UUID,
    idempotency_key: str | None,
) -> RefundEvent | None:
    if idempotency_key is None:
        return None
    return db.scalars(
        select(RefundEvent).where(
            RefundEvent.refund_id == refund_id,
            RefundEvent.idempotency_key == idempotency_key,
        )
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


def _refund_event_replay_matches(
    event: RefundEvent,
    *,
    refund: Refund,
    event_type: str,
    event_source: str,
    actor_user_id: uuid.UUID | None,
    admin_action_id: uuid.UUID | None,
    attempt_number: int,
    attempt_amount_cents: int,
    attempt_currency: str,
    attempt_request_key: str | None,
    provider: str | None,
    provider_event_id: str | None,
    provider_refund_id: str | None,
    provider_charge_id: str | None,
    provider_status: str | None,
    new_refund_status: str | None,
    reason_code: str,
    summary: str,
    metadata: dict[str, Any] | None,
) -> bool:
    return (
        event.refund_id == refund.id
        and event.event_type == event_type
        and event.event_source == event_source
        and event.actor_user_id == actor_user_id
        and event.admin_action_id == admin_action_id
        and event.attempt_number == attempt_number
        and event.attempt_amount_cents == attempt_amount_cents
        and event.attempt_currency == attempt_currency
        and event.attempt_request_key == attempt_request_key
        and event.provider == provider
        and event.provider_event_id == provider_event_id
        and event.provider_refund_id == provider_refund_id
        and event.provider_charge_id == provider_charge_id
        and event.provider_status == provider_status
        and event.new_refund_status == new_refund_status
        and event.reason_code == reason_code
        and event.summary == summary
        and event.event_metadata == metadata
    )


def get_refund_attempt_by_provider_refund_id(
    db: Session,
    *,
    provider: str,
    provider_refund_id: str,
) -> RefundEvent | None:
    """Return one canonical immutable attempt for a provider refund identity."""
    matching_rows = list(db.scalars(
        select(RefundEvent)
        .where(
            RefundEvent.provider == provider,
            RefundEvent.provider_refund_id == provider_refund_id,
        )
        .order_by(RefundEvent.occurred_at.asc(), RefundEvent.id.asc())
    ).all())
    canonical_rows: list[RefundEvent] = []
    for refund_id, attempt_number in dict.fromkeys(
        (row.refund_id, row.attempt_number) for row in matching_rows
    ):
        attempt_rows = list(
            db.scalars(
                select(RefundEvent)
                .where(
                    RefundEvent.refund_id == refund_id,
                    RefundEvent.attempt_number == attempt_number,
                )
                .order_by(RefundEvent.occurred_at.asc(), RefundEvent.id.asc())
            ).all()
        )
        canonical = canonical_provider_attempt_event(
            attempt_rows,
            attempt_number=attempt_number,
        )
        if (
            canonical is not None
            and canonical.provider == provider
            and canonical.provider_refund_id == provider_refund_id
        ):
            canonical_rows.append(canonical)
    return canonical_rows[0] if len(canonical_rows) == 1 else None


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
    new_refund_status: str | None | object = _UNSET_REFUND_STATUS,
    previous_refund_status: str | None = None,
    metadata: dict[str, Any] | None = None,
    attempt_number: int | None = None,
    attempt_amount_cents: int | None = None,
    attempt_currency: str | None = None,
    attempt_request_key: str | None = None,
    apply_to_refund: bool = True,
) -> RefundEvent:
    now = occurred_at or datetime.now(timezone.utc)
    normalized_provider_status = normalize_provider_refund_status(provider_status)
    effective_provider = provider or refund.provider
    existing_provider_event = get_refund_event_by_provider_event_id(
        db,
        provider=effective_provider,
        provider_event_id=provider_event_id,
    )

    effective_provider_refund_id = provider_refund_id or refund.provider_refund_id
    effective_provider_charge_id = provider_charge_id or refund.provider_charge_id
    event_attempt_number = (
        refund.current_attempt_number if attempt_number is None else attempt_number
    )
    event_attempt_amount = (
        refund.amount_cents if attempt_amount_cents is None else attempt_amount_cents
    )
    event_attempt_currency = (
        refund.currency if attempt_currency is None else attempt_currency
    )
    event_attempt_request_key = (
        refund.stripe_request_key
        if attempt_request_key is None and event_attempt_number > 0
        else attempt_request_key
    )
    expected_key = (
        f"refund:{refund.id}:attempt:{event_attempt_number}"
        if event_attempt_number > 0
        else None
    )
    if (
        event_attempt_number < 0
        or event_attempt_amount <= 0
        or event_attempt_currency != "USD"
        or event_attempt_request_key != expected_key
    ):
        raise ValueError("refund event attempt snapshot is invalid")
    effective_new_refund_status = (
        map_provider_status_to_refund_status(normalized_provider_status)
        if new_refund_status is _UNSET_REFUND_STATUS
        else new_refund_status
    )
    if effective_new_refund_status is not None and not isinstance(
        effective_new_refund_status, str
    ):
        raise TypeError("new_refund_status must be a string or null")
    if (
        apply_to_refund
        and effective_new_refund_status == "succeeded"
        and event_type not in {"provider_result_recorded", "reconciliation_checked"}
    ):
        raise ValueError("only authoritative provider observations may apply success")

    replay_identity = {
        "refund": refund,
        "event_type": event_type,
        "event_source": event_source,
        "actor_user_id": actor_user_id,
        "admin_action_id": admin_action_id,
        "attempt_number": event_attempt_number,
        "attempt_amount_cents": event_attempt_amount,
        "attempt_currency": event_attempt_currency,
        "attempt_request_key": event_attempt_request_key,
        "provider": effective_provider,
        "provider_event_id": provider_event_id,
        "provider_refund_id": effective_provider_refund_id,
        "provider_charge_id": effective_provider_charge_id,
        "provider_status": normalized_provider_status,
        "new_refund_status": effective_new_refund_status,
        "reason_code": reason_code,
        "summary": summary,
        "metadata": metadata,
    }
    existing_event = get_refund_event_by_idempotency_key(
        db, refund.id, idempotency_key
    )
    if existing_event is not None:
        if not _refund_event_replay_matches(existing_event, **replay_identity):
            raise ValueError("refund event idempotency key conflicts with existing event")
        existing_event._recorded_now = False
        return existing_event
    if existing_provider_event is not None:
        if not _refund_event_replay_matches(existing_provider_event, **replay_identity):
            raise ValueError("provider event identity conflicts with existing refund event")
        existing_provider_event._recorded_now = False
        return existing_provider_event

    event_previous_refund_status = previous_refund_status or refund.refund_status
    provider_observation = event_type in {
        "provider_result_recorded",
        "provider_outcome_unknown",
        "reconciliation_checked",
    }
    observation_updates_refund = not provider_observation or provider_observation_can_update_refund(
        current_status=refund.refund_status,
        observed_status=effective_new_refund_status,
    )
    effective_apply_to_refund = apply_to_refund and observation_updates_refund
    if effective_apply_to_refund and effective_new_refund_status is not None:
        refund.refund_status = effective_new_refund_status
        if effective_new_refund_status in {"approved", "processing", "succeeded"}:
            refund.approved_at = refund.approved_at or now
        if effective_new_refund_status == "succeeded":
            refund.refunded_at = refund.refunded_at or now
        elif effective_new_refund_status != "succeeded":
            refund.refunded_at = None

    if effective_apply_to_refund and effective_provider is not None:
        refund.provider = effective_provider
    if effective_apply_to_refund and effective_provider_refund_id is not None:
        refund.provider_refund_id = effective_provider_refund_id
    if effective_apply_to_refund and effective_provider_charge_id is not None:
        refund.provider_charge_id = effective_provider_charge_id
    if effective_apply_to_refund and normalized_provider_status is not None:
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
        attempt_number=event_attempt_number,
        attempt_amount_cents=event_attempt_amount,
        attempt_currency=event_attempt_currency,
        attempt_request_key=event_attempt_request_key,
        provider=effective_provider,
        provider_event_id=provider_event_id,
        provider_refund_id=effective_provider_refund_id,
        provider_charge_id=effective_provider_charge_id,
        provider_status=normalized_provider_status,
        previous_refund_status=event_previous_refund_status,
        new_refund_status=effective_new_refund_status,
        reason_code=reason_code,
        summary=summary,
        event_metadata=metadata,
        occurred_at=now,
        created_at=now,
    )
    db.add(refund_event)
    db.flush()
    refund_event._recorded_now = True
    return refund_event
