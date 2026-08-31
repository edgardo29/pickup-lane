"""Targeted PaymentIntent recovery through the canonical observation path."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models import Booking, Game, Payment
from backend.observability.timeouts import PublicTimeoutError
from backend.services.payment_lifecycle_policy import canonical_fingerprint
from backend.services.stripe_service import (
    StripeConfigError,
    create_payment_intent,
    retrieve_payment_intent,
)


def _creation_identity(payment: Payment, booking: Booking) -> dict[str, object]:
    metadata = dict(payment.payment_metadata or {})
    if metadata.get("source") == "waitlist_auto_promote":
        return {
            "payment_id": str(payment.id),
            "booking_id": str(booking.id),
            "payer_user_id": str(payment.payer_user_id),
            "provider_customer_id": payment.provider_customer_id,
            "amount_cents": payment.amount_cents,
            "currency": payment.currency,
            "game_id": str(booking.game_id),
            "participant_count": booking.participant_count,
            "waitlist_entry_id": metadata.get("waitlist_entry_id"),
        }
    return {
        "payment_id": str(payment.id),
        "booking_id": str(booking.id),
        "payer_user_id": str(payment.payer_user_id),
        "provider_customer_id": payment.provider_customer_id,
        "amount_cents": payment.amount_cents,
        "currency": payment.currency,
        "game_id": str(booking.game_id),
        "participant_count": booking.participant_count,
        "credit_applied_cents": metadata.get("credit_applied_cents", 0),
        "checkout_total_cents": metadata.get("checkout_total_cents"),
    }


def _creation_metadata(payment: Payment, booking: Booking) -> dict[str, object]:
    metadata = dict(payment.payment_metadata or {})
    if metadata.get("source") == "waitlist_auto_promote":
        return {
            "source": "waitlist_auto_promote",
            "user_id": str(payment.payer_user_id),
            "game_id": str(booking.game_id),
            "booking_id": str(booking.id),
            "payment_id": str(payment.id),
            "waitlist_entry_id": metadata.get("waitlist_entry_id"),
            "authorized_amount_cents": metadata.get("authorized_amount_cents"),
        }
    return {
        "payment_id": str(payment.id),
        "booking_id": str(booking.id),
        "game_id": str(booking.game_id),
        "user_id": str(payment.payer_user_id),
        "checkout_total_cents": metadata.get("checkout_total_cents"),
        "credit_applied_cents": metadata.get("credit_applied_cents"),
        "minimum_charge_adjustment_cents": metadata.get(
            "minimum_charge_adjustment_cents"
        ),
        "stripe_amount_cents": payment.amount_cents,
    }


def reconcile_payment_intent(db: Session, payment_id: uuid.UUID) -> str:
    payment = db.get(Payment, payment_id)
    if payment is None:
        return "permanent_failure"
    if payment.payment_status in {"succeeded", "canceled"}:
        return "already_terminal"
    if payment.booking_id is None:
        return "permanent_failure"
    booking = db.get(Booking, payment.booking_id)
    if booking is None:
        return "permanent_failure"
    if canonical_fingerprint(_creation_identity(payment, booking)) != (
        payment.creation_fingerprint
    ):
        return "permanent_failure"

    provider_payment_intent_id = payment.provider_payment_intent_id
    amount_cents = payment.amount_cents
    currency = payment.currency
    idempotency_key = payment.idempotency_key
    customer_id = payment.provider_customer_id
    metadata = _creation_metadata(payment, booking)
    db.commit()

    try:
        if provider_payment_intent_id:
            provider_result = retrieve_payment_intent(provider_payment_intent_id)
        else:
            provider_result = create_payment_intent(
                amount_cents=amount_cents,
                currency=currency,
                idempotency_key=idempotency_key,
                metadata=metadata,
                customer_id=customer_id,
            )
    except StripeConfigError:
        return "permanent_failure"
    except PublicTimeoutError:
        _expire_payment_hold_if_stale(db, payment_id)
        return "retry"
    except Exception:  # noqa: BLE001 - reconcile retry preserves unknown provider result
        _expire_payment_hold_if_stale(db, payment_id)
        return "retry"

    from backend.services.checkout_service import expire_stale_pending_checkouts
    from backend.services.stripe_webhook_service import (
        apply_authoritative_payment_intent_observation,
        lock_booking_payment_domain,
    )

    payment = db.get(Payment, payment_id)
    if payment is None:
        return "permanent_failure"
    lock_booking_payment_domain(db, payment)
    payment = db.scalars(
        select(Payment).where(Payment.id == payment_id).with_for_update()
    ).one()
    if payment.provider_payment_intent_id not in {None, provider_result.id}:
        return "permanent_failure"
    if payment.provider_payment_intent_id is None:
        payment.provider_payment_intent_id = provider_result.id
        db.add(payment)
        db.flush()

    booking = db.get(Booking, payment.booking_id)
    game = db.get(Game, booking.game_id) if booking is not None else None
    if booking is None or game is None:
        return "permanent_failure"
    database_now = db.scalar(select(func.now()))
    expire_stale_pending_checkouts(
        db,
        game,
        database_now,
        enqueue_reconciliation=False,
    )
    outcome = apply_authoritative_payment_intent_observation(
        db,
        payment=payment,
        observation=provider_result,
        source="payment_reconcile",
        now=database_now,
    )
    if outcome == "failed":
        return "permanent_failure"
    db.flush()
    if payment.payment_status in {
        "requires_payment_method",
        "requires_confirmation",
        "requires_action",
        "processing",
        "requires_capture",
        "unknown",
    }:
        return "retry"
    return "processed"


def _expire_payment_hold_if_stale(db: Session, payment_id: uuid.UUID) -> None:
    from backend.services.stripe_webhook_service import (
        expire_payment_checkout_hold_if_stale,
    )

    expire_payment_checkout_hold_if_stale(db, payment_id)
    db.flush()
