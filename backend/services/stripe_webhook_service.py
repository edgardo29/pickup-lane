"""Application logic for trusted Stripe webhook events."""

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import (
    AdminFinancialOutcome,
    Booking,
    CommunityPublishAttempt,
    Game,
    GameCreditUsage,
    GameParticipant,
    HostPublishFee,
    Notification,
    Payment,
    PaymentCompensation,
    PaymentEvent,
    Refund,
    User,
    WaitlistEntry,
)
from backend.observability.timeouts import PublicTimeoutError
from backend.services.admin_financial_outcome_service import (
    create_financial_outcome_notice_if_needed,
)
from backend.services.admin_money_issue_query_service import list_related_money_issues
from backend.services.admin_money_issue_service import (
    append_money_issue_event,
    stage_refund_money_issue,
)
from backend.services.community_game_publish_service import (
    finalize_community_publish_attempt_success,
    mark_community_publish_attempt_failed_or_canceled,
    mark_community_publish_attempt_processing,
)
from backend.services.game_credit_service import (
    RESTORED_USAGE_STATUS,
    redeem_reserved_game_credits,
    release_reserved_game_credits,
)
from backend.services.game_notification_service import (
    create_or_reopen_booking_refunded_notification,
    create_waitlist_payment_failed_notification,
    create_waitlist_promotion_notification,
)
from backend.services.game_rules import (
    ACTIVE_PAYMENT_HOLD_BOOKING_STATUSES,
    build_game_conflict_detail,
    game_requires_app_player_payment,
)
from backend.services.game_service import (
    count_roster_players,
    get_next_roster_order,
    sync_game_capacity_status,
)
from backend.services.moderation_surfacing_service import surface_community_game_text
from backend.services.notification_event_service import (
    build_game_notification_fields,
    reopen_aggregated_notification,
)
from backend.services.payment_event_service import build_payment_event_conflict_detail
from backend.services.payment_job_service import enqueue_webhook_event_job
from backend.services.payment_lifecycle_policy import (
    exact_provider_payment_status,
    normalize_provider_payment_status,
    provider_observation_can_advance,
)
from backend.services.payment_rules import (
    COLLECTED_PAYMENT_STATUSES,
    PENDING_PAYMENT_STATUSES,
)
from backend.services.refund_event_service import record_refund_event
from backend.services.status_history_service import (
    add_booking_status_history_if_changed,
    add_participant_status_history_if_changed,
)
from backend.services.stripe_service import (
    StripeConfigError,
    StripePaymentIntentResult,
    retrieve_payment_intent,
)

HANDLED_PAYMENT_INTENT_EVENTS = {
    "payment_intent.succeeded",
    "payment_intent.payment_failed",
    "payment_intent.canceled",
    "payment_intent.processing",
    "payment_intent.requires_action",
    "payment_intent.requires_confirmation",
    "payment_intent.requires_capture",
}
HANDLED_REFUND_EVENTS = {
    "refund.created",
    "refund.updated",
    "refund.failed",
    "charge.refund.updated",
}
HANDLED_STRIPE_EVENTS = HANDLED_PAYMENT_INTENT_EVENTS | HANDLED_REFUND_EVENTS


def stripe_object_to_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value

    if hasattr(value, "to_dict_recursive"):
        return value.to_dict_recursive()

    if hasattr(value, "to_dict"):
        return value.to_dict()

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Stripe webhook payload could not be parsed.",
    )


def record_and_process_stripe_webhook_event(
    db: Session,
    stripe_event: Any,
) -> dict[str, object]:
    event_payload = stripe_object_to_dict(stripe_event)
    provider_event_id = event_payload.get("id")
    event_type = event_payload.get("type")
    if not isinstance(provider_event_id, str) or not provider_event_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stripe event is missing id.",
        )

    if not isinstance(event_type, str) or not event_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stripe event is missing type.",
        )

    existing_event = db.scalars(
        select(PaymentEvent)
        .where(PaymentEvent.provider_event_id == provider_event_id)
        .limit(1)
    ).first()
    if existing_event is not None:
        return {
            "received": True,
            "duplicate": True,
            "processing_status": existing_event.processing_status,
        }

    provider_created = event_payload.get("created")
    if not isinstance(provider_created, int):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stripe event is missing created time.",
        )
    now = datetime.now(timezone.utc)
    event_envelope = normalize_stripe_event_envelope(event_payload)
    payment_event = PaymentEvent(
        id=uuid.uuid4(),
        payment_id=None,
        provider="stripe",
        provider_event_id=provider_event_id,
        event_type=event_type,
        event_envelope=event_envelope,
        provider_created_at=datetime.fromtimestamp(provider_created, tz=timezone.utc),
        processing_status=(
            "pending" if event_type in HANDLED_STRIPE_EVENTS else "ignored"
        ),
        processed_at=None,
        processing_error_code=(
            None if event_type in HANDLED_STRIPE_EVENTS else "unsupported_event"
        ),
        created_at=now,
    )

    try:
        db.add(payment_event)
        db.flush()
        if event_type in HANDLED_STRIPE_EVENTS:
            enqueue_webhook_event_job(db, payment_event.id)
        db.commit()
        db.refresh(payment_event)
    except IntegrityError as exc:
        db.rollback()
        if "uq_payment_events_provider_event_id" in str(exc.orig):
            return {
                "received": True,
                "duplicate": True,
                "processing_status": "duplicate",
            }

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_payment_event_conflict_detail(exc),
        ) from exc

    return {
        "received": True,
        "duplicate": False,
        "processing_status": payment_event.processing_status,
    }


def normalize_stripe_event_envelope(event_payload: dict[str, Any]) -> dict[str, Any]:
    data = event_payload.get("data")
    provider_object = data.get("object") if isinstance(data, dict) else None
    if not isinstance(provider_object, dict):
        provider_object = {}
    metadata = get_stripe_object_metadata(provider_object)
    safe_metadata_keys = {
        "payment_id",
        "booking_id",
        "game_id",
        "user_id",
        "community_publish_attempt_id",
        "host_publish_fee_id",
        "refund_id",
        "checkout_total_cents",
        "credit_applied_cents",
        "minimum_charge_adjustment_cents",
        "stripe_amount_cents",
    }
    safe_object: dict[str, Any] = {
        "id": provider_object.get("id"),
        "status": provider_object.get("status"),
        "amount": provider_object.get("amount"),
        "amount_received": provider_object.get("amount_received"),
        "currency": provider_object.get("currency"),
        "customer": provider_object.get("customer"),
        "payment_intent": provider_object.get("payment_intent"),
        "charge": provider_object.get("charge"),
        "latest_charge": get_latest_charge_id(provider_object),
        "cancellation_reason": provider_object.get("cancellation_reason"),
        "metadata": {
            key: value for key, value in metadata.items() if key in safe_metadata_keys
        },
    }
    last_error = provider_object.get("last_payment_error")
    if isinstance(last_error, dict):
        safe_object["last_payment_error"] = {"code": last_error.get("code")}
    return {
        "id": event_payload.get("id"),
        "type": event_payload.get("type"),
        "created": event_payload.get("created"),
        "data": {"object": safe_object},
    }


def build_payment_intent_observation_envelope(
    payment: Payment,
    observation: StripePaymentIntentResult,
    *,
    source: str,
    now: datetime,
) -> dict[str, Any]:
    event_type = {
        "succeeded": "payment_intent.succeeded",
        "processing": "payment_intent.processing",
        "requires_action": "payment_intent.requires_action",
        "requires_confirmation": "payment_intent.requires_confirmation",
        "requires_capture": "payment_intent.requires_capture",
        "canceled": "payment_intent.canceled",
    }.get(observation.status, "payment_intent.payment_failed")
    metadata = dict(observation.metadata or payment.payment_metadata or {})
    payment_intent: dict[str, Any] = {
        "id": observation.id,
        "status": observation.status,
        "amount": observation.amount_cents or payment.amount_cents,
        "amount_received": observation.amount_received_cents,
        "currency": (observation.currency or payment.currency).lower(),
        "customer": observation.customer_id or payment.provider_customer_id,
        "latest_charge": observation.latest_charge_id,
        "metadata": metadata,
    }
    if observation.failure_code:
        payment_intent["last_payment_error"] = {"code": observation.failure_code}
    return normalize_stripe_event_envelope(
        {
            "id": f"{source}:{payment.id}",
            "type": event_type,
            "created": int(now.timestamp()),
            "data": {"object": payment_intent},
        }
    )


def apply_authoritative_payment_intent_observation(
    db: Session,
    *,
    payment: Payment,
    observation: StripePaymentIntentResult,
    source: str,
    now: datetime,
) -> str:
    envelope = build_payment_intent_observation_envelope(
        payment,
        observation,
        source=source,
        now=now,
    )
    event = PaymentEvent(
        id=uuid.uuid4(),
        payment_id=payment.id,
        provider="stripe",
        provider_event_id=str(envelope["id"]),
        event_type=str(envelope["type"]),
        event_envelope=envelope,
        provider_created_at=now,
        processing_status="processing",
        created_at=now,
    )
    process_payment_intent_event(db, event, envelope, now)
    return event.processing_status


def process_stored_stripe_event(db: Session, event_id: uuid.UUID) -> str:
    event = db.get(PaymentEvent, event_id)
    if event is None:
        return "failed"
    if event.processing_status in {"processed", "ignored"}:
        return event.processing_status
    event_payload = event.event_envelope
    if event.event_type in HANDLED_PAYMENT_INTENT_EVENTS:
        payment_intent = get_payment_intent_payload(event_payload)
        provider_payment_intent_id = (
            payment_intent.get("id") if payment_intent is not None else None
        )
        payment = (
            db.scalars(
                select(Payment)
                .where(
                    Payment.provider_payment_intent_id
                    == provider_payment_intent_id
                )
                .limit(1)
            ).first()
            if isinstance(provider_payment_intent_id, str)
            else None
        )
        if payment is not None:
            event.payment_id = payment.id
            db.add(event)
            db.flush()
            db.commit()
            try:
                observation = retrieve_payment_intent(provider_payment_intent_id)
            except StripeConfigError:
                event = db.get(PaymentEvent, event_id)
                mark_event_failed(event, "stripe_configuration_unavailable")
                db.add(event)
                return "failed"
            except PublicTimeoutError:
                expire_payment_checkout_hold_if_stale(db, payment.id)
                event = db.get(PaymentEvent, event_id)
                event.processing_status = "pending"
                event.processing_error_code = "stripe_payment_intent_read_timeout"
                db.add(event)
                return "retry"
            except Exception:  # noqa: BLE001 - webhook read failure leaves event retryable
                expire_payment_checkout_hold_if_stale(db, payment.id)
                event = db.get(PaymentEvent, event_id)
                event.processing_status = "pending"
                event.processing_error_code = "stripe_payment_intent_read_failed"
                db.add(event)
                return "retry"
            payment = db.get(Payment, payment.id)
            event = db.get(PaymentEvent, event_id)
            database_now = db.scalar(select(func.now()))
            event_payload = build_payment_intent_observation_envelope(
                payment,
                observation,
                source=f"webhook_{event.provider_event_id}",
                now=database_now,
            )
    database_now = db.scalar(select(func.now()))
    process_stripe_event(
        db,
        event,
        event_payload,
        database_now,
    )
    db.add(event)
    return event.processing_status


def mark_stored_event_exhausted(db: Session, event_id: uuid.UUID) -> None:
    event = db.scalars(
        select(PaymentEvent).where(PaymentEvent.id == event_id).with_for_update()
    ).first()
    if event is None or event.processing_status in {"processed", "ignored"}:
        return
    expire_stored_payment_event_hold_if_stale(db, event)
    mark_event_failed(event, "stripe_webhook_processing_exhausted")
    db.add(event)


def surface_community_publish_fee_game_if_needed(
    db: Session,
    payment_event: PaymentEvent,
) -> None:
    if (
        payment_event.processing_status != "processed"
        or payment_event.event_type != "payment_intent.succeeded"
        or payment_event.payment_id is None
    ):
        return

    payment = db.get(Payment, payment_event.payment_id)
    if (
        payment is None
        or payment.payment_type != "community_publish_fee"
        or payment.game_id is None
    ):
        return

    surface_community_game_text(db, game_id=payment.game_id)


def get_payment_intent_payload(event_payload: dict[str, Any]) -> dict[str, Any] | None:
    data = event_payload.get("data")
    if not isinstance(data, dict):
        return None

    payment_intent = data.get("object")
    if not isinstance(payment_intent, dict):
        return None

    return payment_intent


def get_refund_payload(event_payload: dict[str, Any]) -> dict[str, Any] | None:
    data = event_payload.get("data")
    if not isinstance(data, dict):
        return None

    refund = data.get("object")
    if not isinstance(refund, dict):
        return None

    return refund


def get_latest_charge_id(payment_intent: dict[str, Any]) -> str | None:
    latest_charge = payment_intent.get("latest_charge")
    if isinstance(latest_charge, str):
        return latest_charge

    if isinstance(latest_charge, dict):
        latest_charge_id = latest_charge.get("id")
        if isinstance(latest_charge_id, str):
            return latest_charge_id

    return None


def get_payment_intent_amount_cents(payment_intent: dict[str, Any]) -> int | None:
    amount_received = payment_intent.get("amount_received")
    if isinstance(amount_received, int) and amount_received > 0:
        return amount_received

    amount = payment_intent.get("amount")
    if isinstance(amount, int):
        return amount

    return None


def get_payment_intent_currency(payment_intent: dict[str, Any]) -> str | None:
    currency = payment_intent.get("currency")
    if not isinstance(currency, str):
        return None

    return currency.upper()


def get_stripe_object_metadata(stripe_object: dict[str, Any]) -> dict[str, str]:
    metadata = stripe_object.get("metadata")
    if not isinstance(metadata, dict):
        return {}

    return {
        str(key): str(value)
        for key, value in metadata.items()
        if value is not None
    }


def get_payment_intent_metadata(payment_intent: dict[str, Any]) -> dict[str, str]:
    return get_stripe_object_metadata(payment_intent)


def get_refund_amount_cents(refund: dict[str, Any]) -> int | None:
    amount = refund.get("amount")
    if isinstance(amount, int):
        return amount

    return None


def get_refund_currency(refund: dict[str, Any]) -> str | None:
    currency = refund.get("currency")
    if not isinstance(currency, str):
        return None

    return currency.upper()


def get_payment_failure_fields(
    payment_intent: dict[str, Any],
    *,
    fallback_code: str,
    fallback_message: str,
) -> tuple[str, str]:
    last_payment_error = payment_intent.get("last_payment_error")
    error_code: str | None = None
    error_message: str | None = None

    if isinstance(last_payment_error, dict):
        error_code = last_payment_error.get("code")
        error_message = last_payment_error.get("message")

    cancellation_reason = payment_intent.get("cancellation_reason")
    if not isinstance(error_code, str) or not error_code:
        error_code = cancellation_reason if isinstance(cancellation_reason, str) else None

    failure_code = error_code or fallback_code
    failure_message = error_message or fallback_message
    return failure_code, failure_message


def get_locked_payment_by_intent(
    db: Session, provider_payment_intent_id: str
) -> Payment | None:
    return db.scalars(
        select(Payment)
        .where(Payment.provider_payment_intent_id == provider_payment_intent_id)
        .with_for_update()
        .limit(1)
    ).first()


def get_locked_payment(db: Session, payment_id: uuid.UUID | None) -> Payment | None:
    if payment_id is None:
        return None

    return db.scalars(
        select(Payment).where(Payment.id == payment_id).with_for_update()
    ).first()


def get_locked_community_publish_attempt_by_payment(
    db: Session,
    payment_id: uuid.UUID,
) -> CommunityPublishAttempt | None:
    return db.scalars(
        select(CommunityPublishAttempt)
        .where(CommunityPublishAttempt.payment_id == payment_id)
        .with_for_update()
        .limit(1)
    ).first()


def get_locked_booking(db: Session, booking_id: uuid.UUID | None) -> Booking | None:
    if booking_id is None:
        return None

    lock_state = get_payment_domain_lock_state(db)
    if booking_id in lock_state["booking_ids"]:
        return db.get(Booking, booking_id)
    return db.scalars(
        select(Booking).where(Booking.id == booking_id).with_for_update()
    ).first()


def get_locked_game(db: Session, game_id: uuid.UUID | None) -> Game | None:
    if game_id is None:
        return None

    lock_state = get_payment_domain_lock_state(db)
    if game_id in lock_state["game_ids"]:
        return db.get(Game, game_id)
    return db.scalars(
        select(Game).where(Game.id == game_id).with_for_update()
    ).first()


def expire_unresolved_checkout_hold_if_stale(
    db: Session,
    booking: Booking | None,
    now: datetime,
) -> bool:
    if (
        booking is None
        or booking.booking_status != "pending_payment"
        or booking.expires_at is None
        or booking.expires_at > now
    ):
        return False

    game = get_locked_game(db, booking.game_id)
    if game is None:
        return False

    from backend.services.checkout_service import expire_stale_pending_checkouts

    expire_stale_pending_checkouts(db, game, now)
    return True


def expire_payment_checkout_hold_if_stale(
    db: Session,
    payment_id: uuid.UUID,
    *,
    now: datetime | None = None,
) -> bool:
    payment_reference = db.get(Payment, payment_id)
    if (
        payment_reference is None
        or payment_reference.payment_type != "booking"
        or payment_reference.booking_id is None
    ):
        return False
    booking = lock_booking_payment_domain_by_booking_id(
        db,
        payment_reference.booking_id,
    )
    if booking is None:
        return False
    database_now = now or db.scalar(select(func.now()))
    return expire_unresolved_checkout_hold_if_stale(db, booking, database_now)


def expire_stored_payment_event_hold_if_stale(
    db: Session,
    event: PaymentEvent,
    *,
    now: datetime | None = None,
) -> bool:
    if event.payment_id is not None:
        return expire_payment_checkout_hold_if_stale(db, event.payment_id, now=now)

    payment_intent = get_payment_intent_payload(event.event_envelope)
    provider_payment_intent_id = (
        payment_intent.get("id") if payment_intent is not None else None
    )
    if not isinstance(provider_payment_intent_id, str):
        return False
    payment = db.scalars(
        select(Payment)
        .where(Payment.provider_payment_intent_id == provider_payment_intent_id)
        .limit(1)
    ).first()
    if payment is None:
        return False
    event.payment_id = payment.id
    db.add(event)
    return expire_payment_checkout_hold_if_stale(db, payment.id, now=now)


def lock_booking_payment_domain_by_booking_id(
    db: Session,
    booking_id: uuid.UUID,
) -> Booking | None:
    lock_state = get_payment_domain_lock_state(db)
    if booking_id in lock_state["domain_booking_ids"]:
        return db.get(Booking, booking_id)

    game_id = db.scalar(select(Booking.game_id).where(Booking.id == booking_id))
    if game_id is None:
        return None

    lock_state = get_payment_domain_lock_state(db)
    db.scalars(select(Game).where(Game.id == game_id).with_for_update()).one()
    booking = db.scalars(
        select(Booking).where(Booking.id == booking_id).with_for_update()
    ).one()
    locked_waitlists = db.scalars(
        select(WaitlistEntry)
        .where(WaitlistEntry.promoted_booking_id == booking.id)
        .order_by(WaitlistEntry.id.asc())
        .with_for_update()
    ).all()
    db.scalars(
        select(GameParticipant)
        .where(GameParticipant.booking_id == booking.id)
        .order_by(GameParticipant.id.asc())
        .with_for_update()
    ).all()

    lock_state["game_ids"].add(game_id)
    lock_state["booking_ids"].add(booking.id)
    lock_state["waitlist_ids"].update(
        entry.id for entry in locked_waitlists
    )
    lock_state["participant_booking_ids"].add(booking.id)
    lock_state["domain_booking_ids"].add(booking.id)
    return booking


def get_payment_domain_lock_state(db: Session) -> dict[str, Any]:
    transaction = db.get_transaction()
    state = db.info.get("ws05_02_payment_domain_lock_state")
    if state is None or state["transaction"] is not transaction:
        state = {
            "transaction": transaction,
            "domain_booking_ids": set(),
            "game_ids": set(),
            "booking_ids": set(),
            "waitlist_ids": set(),
            "participant_booking_ids": set(),
        }
        db.info["ws05_02_payment_domain_lock_state"] = state
    return state


def lock_booking_payment_domain(
    db: Session,
    payment: Payment,
) -> Booking | None:
    if payment.booking_id is None:
        return None
    return lock_booking_payment_domain_by_booking_id(db, payment.booking_id)


def get_locked_refund_by_provider_id(
    db: Session, provider_refund_id: str
) -> Refund | None:
    return db.scalars(
        select(Refund)
        .where(Refund.provider_refund_id == provider_refund_id)
        .with_for_update()
        .limit(1)
    ).first()


def get_refund_by_provider_id(
    db: Session, provider_refund_id: str
) -> Refund | None:
    return db.scalars(
        select(Refund)
        .where(Refund.provider_refund_id == provider_refund_id)
        .limit(1)
    ).first()


def get_locked_host_publish_fee(
    db: Session,
    host_publish_fee_id: uuid.UUID | None,
) -> HostPublishFee | None:
    if host_publish_fee_id is None:
        return None

    return db.scalars(
        select(HostPublishFee)
        .where(HostPublishFee.id == host_publish_fee_id)
        .with_for_update()
    ).first()


def get_locked_booking_participants(
    db: Session, booking_id: uuid.UUID, statuses: set[str]
) -> list[GameParticipant]:
    statement = (
        select(GameParticipant)
        .where(
            GameParticipant.booking_id == booking_id,
            GameParticipant.participant_status.in_(statuses),
        )
        .order_by(
            GameParticipant.roster_order.asc().nulls_last(),
            GameParticipant.joined_at.asc(),
        )
    )
    lock_state = get_payment_domain_lock_state(db)
    if booking_id not in lock_state["participant_booking_ids"]:
        statement = statement.with_for_update()
    return list(
        db.scalars(statement).all()
    )


def mark_event_processed(event: PaymentEvent, now: datetime) -> None:
    event.processing_status = "processed"
    event.processed_at = now
    event.processing_error_code = None


def mark_event_failed(event: PaymentEvent, error: str) -> None:
    event.processing_status = "failed"
    event.processed_at = None
    event.processing_error_code = safe_event_error_code(error)


def mark_event_ignored(event: PaymentEvent, reason: str) -> None:
    event.processing_status = "ignored"
    event.processed_at = None
    event.processing_error_code = safe_event_error_code(reason)


def safe_event_error_code(value: str) -> str:
    normalized = "".join(
        character if character.isalnum() else "_" for character in value.lower()
    ).strip("_")
    return normalized[:100] or "event_processing_error"


def add_booking_status_history(
    db: Session,
    booking: Booking,
    *,
    old_booking_status: str,
    old_payment_status: str,
    reason: str,
) -> None:
    add_booking_status_history_if_changed(
        db,
        booking,
        old_booking_status=old_booking_status,
        old_payment_status=old_payment_status,
        reason=reason,
        change_source="payment_webhook",
    )


def add_participant_status_history(
    db: Session,
    participant: GameParticipant,
    *,
    old_participant_status: str,
    old_attendance_status: str,
    reason: str,
) -> None:
    add_participant_status_history_if_changed(
        db,
        participant,
        old_participant_status=old_participant_status,
        old_attendance_status=old_attendance_status,
        reason=reason,
        change_source="payment_webhook",
    )


def validate_payment_intent_references(
    payment: Payment,
    booking: Booking | None,
    payment_intent: dict[str, Any],
    *,
    require_metadata: bool,
) -> str | None:
    amount_cents = get_payment_intent_amount_cents(payment_intent)
    if amount_cents != payment.amount_cents:
        return "Stripe amount does not match internal payment amount."

    currency = get_payment_intent_currency(payment_intent)
    if currency != payment.currency:
        return "Stripe currency does not match internal payment currency."

    if booking is None:
        return "Internal booking for this payment was not found."

    provider_customer_id = payment_intent.get("customer")
    if not payment.provider_customer_id:
        return "Internal payment is missing its Stripe Customer identity."
    if provider_customer_id != payment.provider_customer_id:
        return "Stripe Customer does not match the internal payment owner."

    metadata = get_payment_intent_metadata(payment_intent)
    expected_metadata = {
        "user_id": str(payment.payer_user_id),
        "booking_id": str(booking.id),
        "payment_id": str(payment.id),
        "game_id": str(booking.game_id),
    }

    for key, expected_value in expected_metadata.items():
        actual_value = metadata.get(key)
        if actual_value is None and not require_metadata:
            continue

        if actual_value != expected_value:
            return f"Stripe metadata {key} does not match internal records."

    return None


def validate_community_publish_fee_intent_references(
    payment: Payment,
    attempt: CommunityPublishAttempt | None,
    payment_intent: dict[str, Any],
    *,
    require_metadata: bool,
) -> str | None:
    amount_cents = get_payment_intent_amount_cents(payment_intent)
    if amount_cents != payment.amount_cents:
        return "Stripe amount does not match internal publish fee amount."

    currency = get_payment_intent_currency(payment_intent)
    if currency != payment.currency:
        return "Stripe currency does not match internal publish fee currency."

    if payment.payment_type != "community_publish_fee":
        return "Internal payment is not a community publish fee."

    if payment.booking_id is not None:
        return "Community publish fee payment cannot reference a booking."

    if attempt is None:
        return "Internal community publish attempt for this payment was not found."

    if attempt.payment_id != payment.id:
        return "Publish attempt payment_id does not match internal payment."

    if attempt.host_user_id != payment.payer_user_id:
        return "Publish attempt host does not match payment payer."

    if attempt.amount_cents != payment.amount_cents:
        return "Publish attempt amount does not match internal payment amount."

    if attempt.currency != payment.currency:
        return "Publish attempt currency does not match internal payment currency."

    metadata = get_payment_intent_metadata(payment_intent)
    expected_metadata = {
        "source": "community_publish_fee",
        "host_user_id": str(payment.payer_user_id),
        "community_publish_attempt_id": str(attempt.id),
        "payment_id": str(payment.id),
        "amount_cents": str(payment.amount_cents),
    }

    for key, expected_value in expected_metadata.items():
        actual_value = metadata.get(key)
        if actual_value is None and not require_metadata:
            continue

        if actual_value != expected_value:
            return f"Stripe metadata {key} does not match internal publish records."

    return None


def apply_community_publish_fee_succeeded(
    db: Session,
    event: PaymentEvent,
    payment: Payment,
    payment_intent: dict[str, Any],
    now: datetime,
) -> None:
    attempt = get_locked_community_publish_attempt_by_payment(db, payment.id)
    validation_error = validate_community_publish_fee_intent_references(
        payment,
        attempt,
        payment_intent,
        require_metadata=True,
    )
    if validation_error is not None:
        mark_event_failed(event, validation_error)
        return

    if (
        payment.payment_status in COLLECTED_PAYMENT_STATUSES
        and attempt is not None
        and attempt.attempt_status == "succeeded"
    ):
        mark_event_processed(event, now)
        return

    try:
        with db.begin_nested():
            finalize_community_publish_attempt_success(
                db,
                payment=payment,
                provider_charge_id=get_latest_charge_id(payment_intent),
                now=now,
            )
    except ValueError as exc:
        mark_event_failed(event, str(exc))
        return
    except IntegrityError as exc:
        mark_event_failed(event, build_game_conflict_detail(exc))
        return

    mark_event_processed(event, now)


def apply_community_publish_fee_processing(
    db: Session,
    event: PaymentEvent,
    payment: Payment,
    payment_intent: dict[str, Any],
    now: datetime,
) -> None:
    attempt = get_locked_community_publish_attempt_by_payment(db, payment.id)
    validation_error = validate_community_publish_fee_intent_references(
        payment,
        attempt,
        payment_intent,
        require_metadata=True,
    )
    if validation_error is not None:
        mark_event_failed(event, validation_error)
        return

    if payment.payment_status in COLLECTED_PAYMENT_STATUSES:
        mark_event_ignored(event, "Processing event arrived after payment success.")
        return

    try:
        mark_community_publish_attempt_processing(
            db,
            payment=payment,
            provider_charge_id=get_latest_charge_id(payment_intent),
            now=now,
        )
    except ValueError as exc:
        mark_event_failed(event, str(exc))
        return

    mark_event_processed(event, now)


def apply_community_publish_fee_failed_or_canceled(
    db: Session,
    event: PaymentEvent,
    payment: Payment,
    payment_intent: dict[str, Any],
    now: datetime,
    *,
    is_canceled: bool,
) -> None:
    attempt = get_locked_community_publish_attempt_by_payment(db, payment.id)
    validation_error = validate_community_publish_fee_intent_references(
        payment,
        attempt,
        payment_intent,
        require_metadata=True,
    )
    if validation_error is not None:
        mark_event_failed(event, validation_error)
        return

    if payment.payment_status in COLLECTED_PAYMENT_STATUSES:
        mark_event_ignored(
            event,
            "Failure or cancel event arrived after payment success.",
        )
        return

    if is_canceled:
        payment_status = "canceled"
        attempt_status = "cancelled"
        fallback_code = "payment_intent_canceled"
        fallback_message = "Stripe payment intent was canceled."
    else:
        payment_status = "failed"
        attempt_status = "failed"
        fallback_code = "payment_intent_payment_failed"
        fallback_message = "Stripe payment intent failed."

    failure_code, failure_message = get_payment_failure_fields(
        payment_intent,
        fallback_code=fallback_code,
        fallback_message=fallback_message,
    )

    try:
        mark_community_publish_attempt_failed_or_canceled(
            db,
            payment=payment,
            provider_charge_id=get_latest_charge_id(payment_intent),
            now=now,
            payment_status=payment_status,
            attempt_status=attempt_status,
            failure_code=failure_code,
            failure_message=failure_message,
        )
    except ValueError as exc:
        mark_event_failed(event, str(exc))
        return

    mark_event_processed(event, now)


def get_waitlist_auto_promote_entry(
    db: Session,
    payment: Payment,
) -> WaitlistEntry | None:
    metadata = payment.payment_metadata or {}
    if metadata.get("source") != "waitlist_auto_promote":
        return None

    waitlist_entry_id = metadata.get("waitlist_entry_id")
    if not waitlist_entry_id:
        return None

    try:
        parsed_waitlist_entry_id = uuid.UUID(str(waitlist_entry_id))
    except ValueError:
        return None

    statement = select(WaitlistEntry).where(
        WaitlistEntry.id == parsed_waitlist_entry_id
    )
    lock_state = get_payment_domain_lock_state(db)
    if parsed_waitlist_entry_id not in lock_state["waitlist_ids"]:
        statement = statement.with_for_update()
    return db.scalars(statement).first()


def booking_confirmed_aggregation_key(game_id: uuid.UUID, booking_id: uuid.UUID) -> str:
    return f"game:{game_id}:booking:{booking_id}:booking_confirmed"


def payment_failed_aggregation_key(
    game_id: uuid.UUID,
    booking_id: uuid.UUID,
    payment_id: uuid.UUID,
) -> str:
    return f"game:{game_id}:booking:{booking_id}:payment:{payment_id}:payment_failed"


def resolve_unread_payment_failed_notifications(
    db: Session,
    *,
    game: Game,
    booking: Booking,
    read_at: datetime,
) -> None:
    notifications = db.scalars(
        select(Notification).where(
            Notification.user_id == booking.buyer_user_id,
            Notification.notification_type == "payment_failed",
            Notification.notification_domain == "game",
            Notification.is_read.is_(False),
            (
                (Notification.related_booking_id == booking.id)
                | (Notification.related_game_id == game.id)
            ),
        )
    ).all()

    for notification in notifications:
        notification.is_read = True
        if notification.read_at is None:
            notification.read_at = read_at
        notification.updated_at = read_at
        db.add(notification)


def create_booking_confirmed_notification(
    db: Session,
    *,
    game: Game,
    booking: Booking,
    payment: Payment,
    now: datetime,
) -> None:
    resolve_unread_payment_failed_notifications(
        db,
        game=game,
        booking=booking,
        read_at=now,
    )
    aggregation_key = booking_confirmed_aggregation_key(game.id, booking.id)
    reopen_aggregated_notification(
        db,
        user_id=booking.buyer_user_id,
        notification_type="booking_confirmed",
        notification_category="game_activity",
        notification_domain="game",
        aggregation_key=aggregation_key,
        values={
            **build_game_notification_fields(
                game,
                "booking_confirmed",
                event_at=now,
                body="Your booking for this official game was confirmed.",
                aggregation_key=aggregation_key,
            ),
            "actor_user_id": None,
            "related_game_id": game.id,
            "related_booking_id": booking.id,
            "related_payment_id": payment.id,
            "related_participant_id": None,
            "related_refund_id": None,
        },
        aggregate_count_mode="clear",
    )


def create_checkout_payment_failed_notification(
    db: Session,
    *,
    game: Game,
    booking: Booking,
    payment: Payment,
    now: datetime,
    restored_credit: bool,
) -> None:
    body = (
        "Your payment could not be completed, so your checkout hold was released "
        "and your reserved credit was restored. You were not added to the game."
        if restored_credit
        else (
            "Your payment could not be completed, so your checkout hold was "
            "released. You were not added to the game."
        )
    )
    aggregation_key = payment_failed_aggregation_key(game.id, booking.id, payment.id)
    reopen_aggregated_notification(
        db,
        user_id=booking.buyer_user_id,
        notification_type="payment_failed",
        notification_category="game_activity",
        notification_domain="game",
        aggregation_key=aggregation_key,
        values={
            **build_game_notification_fields(
                game,
                "payment_failed",
                event_at=now,
                body=body,
                aggregation_key=aggregation_key,
            ),
            "actor_user_id": None,
            "related_game_id": game.id,
            "related_booking_id": booking.id,
            "related_payment_id": payment.id,
            "related_participant_id": None,
            "related_refund_id": None,
        },
        aggregate_count_mode="clear",
    )


def expire_late_successful_payment(
    db: Session,
    *,
    game: Game,
    booking: Booking,
    payment: Payment,
    payment_intent: dict[str, Any],
    now: datetime,
) -> str | None:
    try:
        release_reserved_game_credits(
            db,
            booking.id,
            now=now,
            reason_code="late_payment_after_checkout_hold_expired",
            user_id=booking.buyer_user_id,
        )
    except ValueError as exc:
        return str(exc)

    old_booking_status = booking.booking_status
    old_payment_status = booking.payment_status
    old_reservation_status = booking.reservation_status
    payment.payment_status = "succeeded"
    payment.provider_status = "succeeded"
    payment.provider_charge_id = get_latest_charge_id(payment_intent)
    payment.paid_at = payment.paid_at or now
    payment.failure_code = None
    payment.failure_message = None
    payment.updated_at = now
    db.add(payment)

    waitlist_entry = get_waitlist_auto_promote_entry(db, payment)
    pending_participants = get_locked_booking_participants(
        db, booking.id, {"pending_payment"}
    )
    participant_failure_status = "removed" if waitlist_entry is not None else "cancelled"
    for participant in pending_participants:
        old_participant_status = participant.participant_status
        old_attendance_status = participant.attendance_status
        participant.participant_status = participant_failure_status
        participant.attendance_status = "not_applicable"
        participant.cancellation_type = "payment_failed"
        participant.cancelled_at = participant.cancelled_at or now
        participant.updated_at = now
        db.add(participant)
        add_participant_status_history(
            db,
            participant,
            old_participant_status=old_participant_status,
            old_attendance_status=old_attendance_status,
            reason="Late Stripe payment succeeded after the checkout hold expired.",
        )

    if (
        old_booking_status == "capacity_conflict"
        or old_reservation_status == "capacity_conflict"
    ):
        next_booking_status = "capacity_conflict"
        next_reservation_status = "capacity_conflict"
        compensation_reason = "capacity_conflict"
    elif old_booking_status == "cancelled":
        next_booking_status = "cancelled"
        next_reservation_status = (
            old_reservation_status
            if old_reservation_status in {"released", "not_required"}
            else "released"
        )
        compensation_reason = "booking_cancelled"
    else:
        next_booking_status = (
            "expired" if old_booking_status == "pending_payment" else old_booking_status
        )
        next_reservation_status = (
            old_reservation_status
            if old_reservation_status in {"released", "not_required"}
            else "released"
        )
        compensation_reason = "reservation_expired"

    booking.booking_status = next_booking_status
    booking.reservation_status = next_reservation_status
    booking.payment_status = "paid"
    booking.expires_at = None
    booking.updated_at = now
    db.add(booking)
    add_booking_status_history(
        db,
        booking,
        old_booking_status=old_booking_status,
        old_payment_status=old_payment_status,
        reason="Late Stripe payment succeeded after the checkout hold expired.",
    )

    if waitlist_entry is not None:
        waitlist_entry.waitlist_status = "payment_failed"
        waitlist_entry.promoted_booking_id = booking.id
        waitlist_entry.cancelled_at = waitlist_entry.cancelled_at or now
        waitlist_entry.updated_at = now
        db.add(waitlist_entry)
        create_waitlist_payment_failed_notification(
            db,
            game,
            booking,
            payment,
            now,
        )

    ensure_payment_compensation(
        db,
        payment=payment,
        booking=booking,
        reason=compensation_reason,
        now=now,
    )

    sync_game_capacity_status(db, game)
    game.updated_at = now
    db.add(game)
    return None


def ensure_payment_compensation(
    db: Session,
    *,
    payment: Payment,
    booking: Booking,
    reason: str,
    now: datetime,
) -> PaymentCompensation:
    existing = db.scalars(
        select(PaymentCompensation)
        .where(
            PaymentCompensation.payment_id == payment.id,
            PaymentCompensation.booking_id == booking.id,
            PaymentCompensation.status.in_({"required", "processing"}),
        )
        .with_for_update()
        .limit(1)
    ).first()
    if existing is not None:
        return existing
    compensation = PaymentCompensation(
        id=uuid.uuid4(),
        payment_id=payment.id,
        booking_id=booking.id,
        action="refund",
        reason=reason,
        amount_cents=payment.amount_cents,
        currency=payment.currency,
        status="required",
        created_at=now,
        updated_at=now,
    )
    db.add(compensation)
    db.flush()
    return compensation


def apply_payment_intent_succeeded(
    db: Session,
    event: PaymentEvent,
    payment: Payment,
    payment_intent: dict[str, Any],
    now: datetime,
) -> None:
    booking = get_locked_booking(db, payment.booking_id)
    validation_error = validate_payment_intent_references(
        payment,
        booking,
        payment_intent,
        require_metadata=True,
    )
    if validation_error is not None:
        mark_event_failed(event, validation_error)
        return

    game = get_locked_game(db, booking.game_id)
    if game is None or not game_requires_app_player_payment(game):
        mark_event_failed(event, "Internal game is not eligible for Stripe booking payment.")
        return

    if booking.booking_status in {"confirmed", "partially_cancelled"}:
        if payment.payment_status not in COLLECTED_PAYMENT_STATUSES:
            payment.payment_status = "succeeded"
            payment.provider_status = "succeeded"
            payment.provider_charge_id = get_latest_charge_id(payment_intent)
            payment.paid_at = payment.paid_at or now
            payment.failure_code = None
            payment.failure_message = None
            payment.updated_at = now
            db.add(payment)
        elif payment.provider_charge_id is None:
            payment.provider_charge_id = get_latest_charge_id(payment_intent)
            payment.updated_at = now
            db.add(payment)
        mark_event_processed(event, now)
        return

    if booking.booking_status != "pending_payment":
        late_payment_error = expire_late_successful_payment(
            db,
            game=game,
            booking=booking,
            payment=payment,
            payment_intent=payment_intent,
            now=now,
        )
        if late_payment_error is not None:
            mark_event_failed(event, late_payment_error)
            return
        mark_event_processed(event, now)
        return

    hold_is_valid = (
        booking.expires_at is not None
        and booking.expires_at > now
        and booking.payment_status in ACTIVE_PAYMENT_HOLD_BOOKING_STATUSES
    )
    if not hold_is_valid:
        late_payment_error = expire_late_successful_payment(
            db,
            game=game,
            booking=booking,
            payment=payment,
            payment_intent=payment_intent,
            now=now,
        )
        if late_payment_error is not None:
            mark_event_failed(event, late_payment_error)
            return
        mark_event_processed(event, now)
        return

    pending_participants = get_locked_booking_participants(
        db, booking.id, {"pending_payment"}
    )
    if len(pending_participants) != booking.participant_count:
        mark_event_failed(
            event,
            "Pending participant count does not match the booking party size.",
        )
        return

    current_roster_count = count_roster_players(db, booking.game_id, now=now)
    if current_roster_count > game.total_spots:
        record_capacity_conflict_after_success(
            db,
            game=game,
            booking=booking,
            payment=payment,
            payment_intent=payment_intent,
            pending_participants=pending_participants,
            now=now,
        )
        mark_event_processed(event, now)
        return

    try:
        redeem_reserved_game_credits(
            db,
            booking.id,
            now=now,
            user_id=booking.buyer_user_id,
        )
    except ValueError as exc:
        mark_event_failed(event, str(exc))
        return

    old_booking_status = booking.booking_status
    old_payment_status = booking.payment_status
    next_roster_order = get_next_roster_order(db, booking.game_id)

    payment.payment_status = "succeeded"
    payment.provider_status = "succeeded"
    payment.provider_charge_id = get_latest_charge_id(payment_intent)
    payment.paid_at = payment.paid_at or now
    payment.failure_code = None
    payment.failure_message = None
    payment.updated_at = now
    db.add(payment)

    for index, participant in enumerate(pending_participants):
        old_participant_status = participant.participant_status
        old_attendance_status = participant.attendance_status
        participant.participant_status = "confirmed"
        participant.attendance_status = "unknown"
        participant.confirmed_at = participant.confirmed_at or now
        participant.roster_order = participant.roster_order or next_roster_order + index
        participant.updated_at = now
        db.add(participant)
        add_participant_status_history(
            db,
            participant,
            old_participant_status=old_participant_status,
            old_attendance_status=old_attendance_status,
            reason="Stripe payment_intent.succeeded confirmed payment.",
        )

    booking.booking_status = "confirmed"
    booking.reservation_status = "confirmed"
    booking.payment_status = "paid"
    booking.booked_at = booking.booked_at or now
    booking.expires_at = None
    booking.updated_at = now
    db.add(booking)
    add_booking_status_history(
        db,
        booking,
        old_booking_status=old_booking_status,
        old_payment_status=old_payment_status,
        reason="Stripe payment_intent.succeeded confirmed payment.",
    )

    sync_game_capacity_status(db, game)
    game.updated_at = now
    db.add(game)
    waitlist_entry = get_waitlist_auto_promote_entry(db, payment)
    if waitlist_entry is not None:
        waitlist_entry.waitlist_status = "accepted"
        waitlist_entry.promoted_booking_id = booking.id
        waitlist_entry.promoted_at = waitlist_entry.promoted_at or now
        waitlist_entry.updated_at = now
        db.add(waitlist_entry)
        create_waitlist_promotion_notification(
            db,
            game,
            waitlist_entry,
            pending_participants[0],
            now,
            payment,
        )
    else:
        create_booking_confirmed_notification(
            db,
            game=game,
            booking=booking,
            payment=payment,
            now=now,
        )
    mark_event_processed(event, now)


def record_capacity_conflict_after_success(
    db: Session,
    *,
    game: Game,
    booking: Booking,
    payment: Payment,
    payment_intent: dict[str, Any],
    pending_participants: list[GameParticipant],
    now: datetime,
) -> None:
    release_reserved_game_credits(
        db,
        booking.id,
        now=now,
        reason_code="payment_capacity_conflict",
        user_id=booking.buyer_user_id,
    )
    old_booking_status = booking.booking_status
    old_payment_status = booking.payment_status
    payment.payment_status = "succeeded"
    payment.provider_status = "succeeded"
    payment.provider_charge_id = get_latest_charge_id(payment_intent)
    payment.paid_at = payment.paid_at or now
    payment.failure_code = None
    payment.failure_message = None
    payment.updated_at = now
    db.add(payment)
    booking.booking_status = "capacity_conflict"
    booking.reservation_status = "capacity_conflict"
    booking.payment_status = "paid"
    booking.expires_at = None
    booking.updated_at = now
    db.add(booking)
    for participant in pending_participants:
        old_participant_status = participant.participant_status
        old_attendance_status = participant.attendance_status
        participant.participant_status = "cancelled"
        participant.attendance_status = "not_applicable"
        participant.cancellation_type = "payment_failed"
        participant.cancelled_at = participant.cancelled_at or now
        participant.updated_at = now
        db.add(participant)
        add_participant_status_history(
            db,
            participant,
            old_participant_status=old_participant_status,
            old_attendance_status=old_attendance_status,
            reason="Stripe succeeded but current capacity could not be granted.",
        )
    add_booking_status_history(
        db,
        booking,
        old_booking_status=old_booking_status,
        old_payment_status=old_payment_status,
        reason="Stripe succeeded but current capacity could not be granted.",
    )
    ensure_payment_compensation(
        db,
        payment=payment,
        booking=booking,
        reason="capacity_conflict",
        now=now,
    )
    sync_game_capacity_status(db, game)
    game.updated_at = now
    db.add(game)


def apply_payment_intent_processing(
    db: Session,
    event: PaymentEvent,
    payment: Payment,
    payment_intent: dict[str, Any],
    now: datetime,
) -> None:
    booking = get_locked_booking(db, payment.booking_id)
    validation_error = validate_payment_intent_references(
        payment,
        booking,
        payment_intent,
        require_metadata=True,
    )
    if validation_error is not None:
        mark_event_failed(event, validation_error)
        return

    if payment.payment_status in COLLECTED_PAYMENT_STATUSES:
        mark_event_ignored(event, "Processing event arrived after payment success.")
        return

    if payment.payment_status not in PENDING_PAYMENT_STATUSES:
        mark_event_ignored(event, "Payment is no longer pending.")
        return

    expire_unresolved_checkout_hold_if_stale(db, booking, now)
    booking = get_locked_booking(db, payment.booking_id)
    old_booking_status = booking.booking_status
    old_payment_status = booking.payment_status
    exact_provider_status = exact_provider_payment_status(
        str(payment_intent.get("status") or "processing")
    )
    normalized_status = normalize_provider_payment_status(exact_provider_status)
    if not provider_observation_can_advance(payment.payment_status, normalized_status):
        mark_event_ignored(event, "Provider observation would regress payment state.")
        return
    payment.provider_status = exact_provider_status
    payment.payment_status = normalized_status
    payment.updated_at = now
    db.add(payment)

    if booking.booking_status == "pending_payment":
        booking.payment_status = "processing"
        booking.updated_at = now
        db.add(booking)
        add_booking_status_history(
            db,
            booking,
            old_booking_status=old_booking_status,
            old_payment_status=old_payment_status,
            reason="Stripe payment_intent.processing updated payment state.",
        )

    mark_event_processed(event, now)


def apply_payment_intent_pending_observation(
    db: Session,
    event: PaymentEvent,
    payment: Payment,
    payment_intent: dict[str, Any],
    now: datetime,
) -> None:
    booking = get_locked_booking(db, payment.booking_id)
    validation_error = validate_payment_intent_references(
        payment,
        booking,
        payment_intent,
        require_metadata=True,
    )
    if validation_error is not None:
        mark_event_failed(event, validation_error)
        return
    exact_provider_status = exact_provider_payment_status(
        str(payment_intent.get("status") or "")
    )
    observed_status = normalize_provider_payment_status(exact_provider_status)
    if observed_status not in PENDING_PAYMENT_STATUSES:
        mark_event_failed(event, "PaymentIntent has an invalid pending status.")
        return
    if not provider_observation_can_advance(payment.payment_status, observed_status):
        mark_event_ignored(event, "Provider observation would regress payment state.")
        return
    expire_unresolved_checkout_hold_if_stale(db, booking, now)
    booking = get_locked_booking(db, payment.booking_id)
    old_booking_status = booking.booking_status
    old_payment_status = booking.payment_status
    waitlist_entry = get_waitlist_auto_promote_entry(db, payment)
    if (
        waitlist_entry is not None
        and booking.booking_status == "pending_payment"
        and observed_status in {"requires_action", "requires_payment_method"}
    ):
        game = get_locked_game(db, booking.game_id)
        booking_participants = get_locked_booking_participants(
            db,
            booking.id,
            {"pending_payment"},
        )
        if game is None or not booking_participants:
            mark_event_failed(
                event,
                "Waitlist auto-promotion state is missing for provider failure.",
            )
            return
        from backend.services.game_waitlist_service import (
            mark_paid_waitlist_auto_promotion_failed,
        )

        mark_paid_waitlist_auto_promotion_failed(
            db,
            game,
            waitlist_entry,
            booking,
            booking_participants,
            payment,
            now,
            payment_status=observed_status,
            failure_code=f"waitlist_auto_charge_{observed_status}",
            failure_message="Saved card auto-charge could not complete off-session.",
        )
        mark_event_processed(event, now)
        return
    payment.provider_status = exact_provider_status
    payment.payment_status = observed_status
    failure_code, _ = get_payment_failure_fields(
        payment_intent,
        fallback_code="payment_requires_update",
        fallback_message="Payment requires another step.",
    )
    payment.failure_code = failure_code if observed_status == "requires_payment_method" else None
    payment.failure_message = None
    payment.updated_at = now
    db.add(payment)
    if booking.booking_status == "pending_payment":
        booking.payment_status = (
            "requires_action" if observed_status == "requires_action" else "processing"
        )
        booking.updated_at = now
        db.add(booking)
        add_booking_status_history(
            db,
            booking,
            old_booking_status=old_booking_status,
            old_payment_status=old_payment_status,
            reason="Stripe updated the pending PaymentIntent state.",
        )
    mark_event_processed(event, now)


def fail_pending_booking_hold(
    db: Session,
    payment: Payment,
    payment_intent: dict[str, Any],
    now: datetime,
    *,
    payment_status: str,
    booking_status: str,
    fallback_code: str,
    fallback_message: str,
    history_reason: str,
    restored_credit: bool = False,
    emit_checkout_failure_notification: bool = False,
) -> None:
    failure_code, failure_message = get_payment_failure_fields(
        payment_intent,
        fallback_code=fallback_code,
        fallback_message=fallback_message,
    )
    payment.payment_status = payment_status
    payment.provider_status = exact_provider_payment_status(
        str(
            payment_intent.get("status")
            or ("canceled" if payment_status == "canceled" else "")
        )
    )
    payment.provider_charge_id = get_latest_charge_id(payment_intent)
    payment.failure_code = failure_code
    payment.failure_message = failure_message
    payment.paid_at = None
    payment.updated_at = now
    db.add(payment)

    booking = get_locked_booking(db, payment.booking_id)
    if booking is None:
        return

    if booking.booking_status != "pending_payment":
        return

    game = get_locked_game(db, booking.game_id)
    old_booking_status = booking.booking_status
    old_payment_status = booking.payment_status
    booking.booking_status = booking_status
    booking.reservation_status = "released"
    booking.payment_status = "failed"
    booking.expires_at = None
    booking.updated_at = now
    db.add(booking)
    add_booking_status_history(
        db,
        booking,
        old_booking_status=old_booking_status,
        old_payment_status=old_payment_status,
        reason=history_reason,
    )

    waitlist_entry = get_waitlist_auto_promote_entry(db, payment)
    pending_participants = get_locked_booking_participants(
        db, booking.id, {"pending_payment"}
    )
    participant_failure_status = "removed" if waitlist_entry is not None else "cancelled"
    for participant in pending_participants:
        old_participant_status = participant.participant_status
        old_attendance_status = participant.attendance_status
        participant.participant_status = participant_failure_status
        participant.attendance_status = "not_applicable"
        participant.cancellation_type = "payment_failed"
        participant.cancelled_at = participant.cancelled_at or now
        participant.updated_at = now
        db.add(participant)
        add_participant_status_history(
            db,
            participant,
            old_participant_status=old_participant_status,
            old_attendance_status=old_attendance_status,
            reason=history_reason,
        )

    if game is not None:
        if waitlist_entry is not None and booking is not None:
            waitlist_entry.waitlist_status = "payment_failed"
            waitlist_entry.promoted_booking_id = booking.id
            waitlist_entry.cancelled_at = waitlist_entry.cancelled_at or now
            waitlist_entry.updated_at = now
            db.add(waitlist_entry)
            create_waitlist_payment_failed_notification(
                db,
                game,
                booking,
                payment,
                now,
            )
        elif emit_checkout_failure_notification:
            create_checkout_payment_failed_notification(
                db,
                game=game,
                booking=booking,
                payment=payment,
                now=now,
                restored_credit=restored_credit,
            )
        sync_game_capacity_status(db, game)
        game.updated_at = now
        db.add(game)


def apply_payment_intent_failed_or_canceled(
    db: Session,
    event: PaymentEvent,
    payment: Payment,
    payment_intent: dict[str, Any],
    now: datetime,
    *,
    is_canceled: bool,
) -> None:
    booking = get_locked_booking(db, payment.booking_id)
    validation_error = validate_payment_intent_references(
        payment,
        booking,
        payment_intent,
        require_metadata=True,
    )
    if validation_error is not None:
        mark_event_failed(event, validation_error)
        return

    if payment.payment_status in COLLECTED_PAYMENT_STATUSES:
        mark_event_ignored(event, "Failure or cancel event arrived after payment success.")
        return

    waitlist_entry = get_waitlist_auto_promote_entry(db, payment)
    if is_canceled:
        terminal_payment_status = "canceled"
        terminal_booking_status = "failed"
        fallback_code = "payment_intent_canceled"
        fallback_message = "Stripe payment intent was canceled."
        history_reason = (
            "Stripe payment_intent.canceled failed waitlist auto-promotion."
            if waitlist_entry is not None
            else "Stripe payment_intent.canceled released checkout hold."
        )
    else:
        terminal_payment_status = "failed"
        terminal_booking_status = "failed"
        fallback_code = "payment_intent_payment_failed"
        fallback_message = "Stripe payment intent failed."
        history_reason = "Stripe payment_intent.payment_failed released checkout hold."

    if payment.payment_status == terminal_payment_status:
        mark_event_processed(event, now)
        return

    if booking.booking_status == "pending_payment":
        try:
            released_credit_usages = release_reserved_game_credits(
                db,
                booking.id,
                now=now,
                reason_code=fallback_code,
                user_id=booking.buyer_user_id,
            )
        except ValueError as exc:
            mark_event_failed(event, str(exc))
            return
    else:
        released_credit_usages = []

    fail_pending_booking_hold(
        db,
        payment,
        payment_intent,
        now,
        payment_status=terminal_payment_status,
        booking_status=terminal_booking_status,
        fallback_code=fallback_code,
        fallback_message=fallback_message,
        history_reason=history_reason,
        restored_credit=bool(released_credit_usages),
        emit_checkout_failure_notification=not is_canceled,
    )
    mark_event_processed(event, now)


def parse_metadata_uuid(metadata: dict[str, str], key: str) -> uuid.UUID | None:
    value = metadata.get(key)
    if value is None:
        return None

    try:
        return uuid.UUID(value)
    except ValueError:
        return None


def map_stripe_refund_event_status(event_type: str, refund: dict[str, Any]) -> str:
    if event_type == "refund.failed":
        return "failed"

    stripe_status = str(refund.get("status") or "").strip().lower()
    if stripe_status == "succeeded":
        return "succeeded"

    if stripe_status == "failed":
        return "failed"

    if stripe_status in {"canceled", "cancelled"}:
        return "cancelled"

    return "processing"


def get_active_user_id_or_none(
    db: Session, user_id: uuid.UUID | None
) -> uuid.UUID | None:
    if user_id is None:
        return None

    user = db.get(User, user_id)
    if user is None or user.deleted_at is not None:
        return None

    return user.id


def recover_refund_from_metadata(
    db: Session,
    refund_payload: dict[str, Any],
    now: datetime,
) -> Refund | None:
    provider_refund_id = refund_payload.get("id")
    if not isinstance(provider_refund_id, str) or not provider_refund_id:
        return None

    metadata = get_stripe_object_metadata(refund_payload)
    if metadata.get("source") != "official_game_cancel":
        return None

    payment_id = parse_metadata_uuid(metadata, "payment_id")
    booking_id = parse_metadata_uuid(metadata, "booking_id")
    if booking_id is None:
        return None
    booking = lock_booking_payment_domain_by_booking_id(db, booking_id)
    payment = get_locked_payment(db, payment_id)
    if payment is None or booking is None or payment.booking_id != booking.id:
        return None

    amount_cents = get_refund_amount_cents(refund_payload)
    currency = get_refund_currency(refund_payload)
    if (
        amount_cents is None
        or amount_cents <= 0
        or amount_cents > payment.amount_cents
        or currency != payment.currency
    ):
        return None

    admin_user_id = get_active_user_id_or_none(
        db,
        parse_metadata_uuid(metadata, "admin_user_id"),
    )
    recovered_refund = Refund(
        id=uuid.uuid4(),
        payment_id=payment.id,
        booking_id=booking.id,
        participant_id=None,
        origin_workflow="official_game_cancellation",
        provider="stripe",
        provider_refund_id=provider_refund_id,
        provider_charge_id=payment.provider_charge_id,
        provider_status=None,
        provider_status_observed_at=None,
        last_refund_event_at=None,
        amount_cents=amount_cents,
        currency=currency,
        refund_reason="game_cancelled",
        refund_status="processing",
        requested_by_user_id=admin_user_id,
        approved_by_user_id=admin_user_id,
        requested_at=now,
        approved_at=now,
        refunded_at=None,
        created_at=now,
        updated_at=now,
    )
    db.add(recovered_refund)
    db.flush()
    return recovered_refund


def sync_refunded_payment_and_booking(
    db: Session,
    payment: Payment,
    booking: Booking | None,
    host_publish_fee: HostPublishFee | None,
    now: datetime,
) -> None:
    refunded_cents = (
        db.scalar(
            select(func.coalesce(func.sum(Refund.amount_cents), 0)).where(
                Refund.payment_id == payment.id,
                Refund.refund_status == "succeeded",
            )
        )
        or 0
    )
    if refunded_cents <= 0:
        return

    next_booking_payment_status = (
        "refunded" if refunded_cents >= payment.amount_cents else "partially_refunded"
    )

    if host_publish_fee is not None and refunded_cents >= payment.amount_cents:
        host_publish_fee.fee_status = "refunded"
        host_publish_fee.updated_at = now
        db.add(host_publish_fee)

    if booking is not None:
        booking.payment_status = next_booking_payment_status
        booking.updated_at = now
        db.add(booking)


def sync_financial_outcome_for_refund(
    db: Session,
    refund: Refund,
    refund_status: str,
    now: datetime,
) -> None:
    financial_outcome = db.scalar(
        select(AdminFinancialOutcome)
        .where(AdminFinancialOutcome.refund_id == refund.id)
        .with_for_update()
        .limit(1)
    )
    if financial_outcome is None:
        return

    if refund_status == "succeeded":
        financial_outcome.applied_status = "applied"
        financial_outcome.failure_reason = None
        financial_outcome.applied_at = financial_outcome.applied_at or now
    elif refund_status in {"failed", "cancelled"}:
        financial_outcome.applied_status = "failed"
        financial_outcome.failure_reason = (
            financial_outcome.failure_reason or f"Stripe refund {refund_status}."
        )
        financial_outcome.applied_at = financial_outcome.applied_at or now
    else:
        financial_outcome.applied_status = "pending"

    financial_outcome.updated_at = now
    db.add(financial_outcome)
    create_financial_outcome_notice_if_needed(
        db,
        financial_outcome=financial_outcome,
        created_by_user_id=financial_outcome.created_by_user_id,
    )


def booking_has_restored_game_credit(db: Session, booking_id: uuid.UUID) -> bool:
    restored_credit_count = (
        db.scalar(
            select(func.count())
            .select_from(GameCreditUsage)
            .where(
                GameCreditUsage.booking_id == booking_id,
                GameCreditUsage.usage_status == RESTORED_USAGE_STATUS,
            )
        )
        or 0
    )
    return int(restored_credit_count) > 0


def validate_refund_event_references(
    refund: Refund,
    refund_payload: dict[str, Any],
) -> str | None:
    amount_cents = get_refund_amount_cents(refund_payload)
    if amount_cents != refund.amount_cents:
        return "Stripe refund amount does not match internal refund amount."

    currency = get_refund_currency(refund_payload)
    if currency != refund.currency:
        return "Stripe refund currency does not match internal refund currency."

    return None


def process_refund_event(
    db: Session,
    event: PaymentEvent,
    event_payload: dict[str, Any],
    now: datetime,
) -> None:
    refund_payload = get_refund_payload(event_payload)
    if refund_payload is None:
        mark_event_failed(event, "Refund event payload is missing data.object.")
        return

    provider_refund_id = refund_payload.get("id")
    if not isinstance(provider_refund_id, str) or not provider_refund_id:
        mark_event_failed(event, "Refund payload is missing id.")
        return

    refund_reference = get_refund_by_provider_id(db, provider_refund_id)
    if refund_reference is None:
        refund = recover_refund_from_metadata(
            db,
            refund_payload,
            now,
        )
    else:
        if refund_reference.booking_id is not None:
            lock_booking_payment_domain_by_booking_id(db, refund_reference.booking_id)
        refund = get_locked_refund_by_provider_id(db, provider_refund_id)

    if refund is None:
        mark_event_ignored(event, "No internal refund matched this Stripe refund.")
        return

    event.payment_id = refund.payment_id
    validation_error = validate_refund_event_references(refund, refund_payload)
    if validation_error is not None:
        mark_event_failed(event, validation_error)
        return

    payment = get_locked_payment(db, refund.payment_id)
    booking = get_locked_booking(db, refund.booking_id)
    host_publish_fee = get_locked_host_publish_fee(db, refund.host_publish_fee_id)
    if payment is None:
        mark_event_failed(event, "Internal payment for this refund was not found.")
        return

    if refund.host_publish_fee_id is not None and host_publish_fee is None:
        mark_event_failed(
            event,
            "Internal host publish fee for this refund was not found.",
        )
        return

    if host_publish_fee is not None and (
        payment.payment_type != "community_publish_fee"
        or host_publish_fee.payment_id != payment.id
    ):
        mark_event_failed(
            event,
            "Host publish fee refund does not match the internal payment.",
        )
        return

    refund_status = map_stripe_refund_event_status(
        event_payload["type"], refund_payload
    )
    refund_event = record_refund_event(
        db,
        refund=refund,
        event_type="provider_result_recorded",
        event_source="webhook",
        provider="stripe",
        provider_event_id=event.provider_event_id,
        provider_refund_id=provider_refund_id,
        provider_charge_id=refund_payload.get("charge") or payment.provider_charge_id,
        provider_status=refund_status,
        new_refund_status=refund_status,
        reason_code=f"stripe_webhook_{refund_status}",
        summary="Stripe refund webhook result recorded.",
        occurred_at=now,
    )
    if refund_status in {"failed", "cancelled"}:
        stage_refund_money_issue(
            db,
            refund=refund,
            payment=payment,
            issue_type="refund_failed"
            if refund_status == "failed"
            else "refund_cancelled",
            reason_code=f"stripe_webhook_{refund_status}",
            summary="Stripe reported that a refund did not complete.",
            refund_event=refund_event,
            now=now,
        )
    elif refund_status == "succeeded":
        for money_issue in list_related_money_issues(
            db,
            refund_id=refund.id,
            status_filter="open",
            limit=10,
        ):
            previous_action = money_issue.recommended_action_code
            money_issue.latest_reason_code = "stripe_webhook_succeeded"
            money_issue.latest_summary = "Stripe confirmed the refund succeeded."
            money_issue.recommended_action_code = "review_and_resolve_no_action"
            money_issue.updated_at = now
            append_money_issue_event(
                db,
                money_issue=money_issue,
                event_type="refund_outcome_linked",
                event_source="system",
                refund_event_id=refund_event.id,
                reason_code="stripe_webhook_succeeded",
                summary="Stripe confirmed the refund succeeded.",
                previous_recommended_action_code=previous_action,
                new_recommended_action_code=money_issue.recommended_action_code,
                occurred_at=now,
            )
    sync_financial_outcome_for_refund(db, refund, refund_status, now)

    if refund_status == "succeeded":
        db.flush()
        sync_refunded_payment_and_booking(
            db,
            payment,
            booking,
            host_publish_fee,
            now,
        )
        if booking is not None:
            game = get_locked_game(db, booking.game_id)
            if game is not None:
                create_or_reopen_booking_refunded_notification(
                    db,
                    db_game=game,
                    booking=booking,
                    payment=payment,
                    refund=refund,
                    now=now,
                    stripe_refund_processed=True,
                    credit_restored=booking_has_restored_game_credit(db, booking.id),
                )

    mark_event_processed(event, now)


def process_payment_intent_event(
    db: Session,
    event: PaymentEvent,
    event_payload: dict[str, Any],
    now: datetime,
) -> None:
    event_type = event_payload["type"]
    payment_intent = get_payment_intent_payload(event_payload)
    if payment_intent is None:
        mark_event_failed(event, "PaymentIntent event payload is missing data.object.")
        return

    payment_intent_id = payment_intent.get("id")
    if not isinstance(payment_intent_id, str) or not payment_intent_id:
        mark_event_failed(event, "PaymentIntent payload is missing id.")
        return

    payment_reference = db.scalars(
        select(Payment)
        .where(Payment.provider_payment_intent_id == payment_intent_id)
        .limit(1)
    ).first()
    if payment_reference is not None and payment_reference.payment_type == "booking":
        lock_booking_payment_domain(db, payment_reference)
    payment = get_locked_payment_by_intent(db, payment_intent_id)
    if payment is None:
        mark_event_failed(event, "No internal payment matched this PaymentIntent.")
        return

    persisted_event = db.scalars(
        select(PaymentEvent)
        .where(PaymentEvent.id == event.id)
        .with_for_update()
        .limit(1)
    ).first()
    if persisted_event is not None:
        event = persisted_event

    event.payment_id = payment.id

    if payment.payment_type == "community_publish_fee":
        if event_type == "payment_intent.succeeded":
            apply_community_publish_fee_succeeded(
                db, event, payment, payment_intent, now
            )
            return

        if event_type == "payment_intent.processing":
            apply_community_publish_fee_processing(
                db, event, payment, payment_intent, now
            )
            return

        if event_type == "payment_intent.payment_failed":
            apply_community_publish_fee_failed_or_canceled(
                db, event, payment, payment_intent, now, is_canceled=False
            )
            return

        if event_type == "payment_intent.canceled":
            apply_community_publish_fee_failed_or_canceled(
                db, event, payment, payment_intent, now, is_canceled=True
            )
            return

    if payment.payment_type != "booking":
        mark_event_ignored(event, "PaymentIntent event matched unsupported payment type.")
        return

    if event_type == "payment_intent.succeeded":
        apply_payment_intent_succeeded(db, event, payment, payment_intent, now)
        return

    if event_type == "payment_intent.processing":
        apply_payment_intent_processing(db, event, payment, payment_intent, now)
        return

    if event_type in {
        "payment_intent.requires_action",
        "payment_intent.requires_confirmation",
        "payment_intent.requires_capture",
    }:
        apply_payment_intent_pending_observation(
            db, event, payment, payment_intent, now
        )
        return

    if event_type == "payment_intent.payment_failed":
        observed_status = normalize_provider_payment_status(
            str(payment_intent.get("status") or "")
        )
        if observed_status in PENDING_PAYMENT_STATUSES:
            apply_payment_intent_pending_observation(
                db, event, payment, payment_intent, now
            )
            return
        apply_payment_intent_failed_or_canceled(
            db, event, payment, payment_intent, now, is_canceled=False
        )
        return

    if event_type == "payment_intent.canceled":
        apply_payment_intent_failed_or_canceled(
            db, event, payment, payment_intent, now, is_canceled=True
        )


def process_stripe_event(
    db: Session,
    event: PaymentEvent,
    event_payload: dict[str, Any],
    now: datetime,
) -> None:
    if event.event_type not in HANDLED_STRIPE_EVENTS:
        mark_event_ignored(event, "Unhandled Stripe event type.")
        return

    if event.event_type in HANDLED_PAYMENT_INTENT_EVENTS:
        process_payment_intent_event(db, event, event_payload, now)
        return

    process_refund_event(db, event, event_payload, now)
