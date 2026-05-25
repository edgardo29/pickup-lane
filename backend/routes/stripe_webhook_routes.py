import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import (
    Booking,
    BookingStatusHistory,
    Game,
    GameParticipant,
    ParticipantStatusHistory,
    Payment,
    PaymentEvent,
)
from backend.routes.game_routes import (
    count_roster_players,
    game_requires_app_player_payment,
    get_next_roster_order,
    sync_game_capacity_status,
)
from backend.routes.payment_event_routes import build_payment_event_conflict_detail
from backend.services.stripe_service import StripeConfigError, construct_webhook_event

router = APIRouter(prefix="/stripe", tags=["stripe"])

HANDLED_PAYMENT_INTENT_EVENTS = {
    "payment_intent.succeeded",
    "payment_intent.payment_failed",
    "payment_intent.canceled",
    "payment_intent.processing",
}
PENDING_INTERNAL_PAYMENT_STATUSES = {
    "requires_payment_method",
    "requires_action",
    "processing",
}
POST_SUCCESS_INTERNAL_PAYMENT_STATUSES = {
    "succeeded",
    "refunded",
    "partially_refunded",
    "disputed",
}


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


def get_payment_intent_payload(event_payload: dict[str, Any]) -> dict[str, Any] | None:
    data = event_payload.get("data")
    if not isinstance(data, dict):
        return None

    payment_intent = data.get("object")
    if not isinstance(payment_intent, dict):
        return None

    return payment_intent


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


def get_payment_intent_metadata(payment_intent: dict[str, Any]) -> dict[str, str]:
    metadata = payment_intent.get("metadata")
    if not isinstance(metadata, dict):
        return {}

    return {
        str(key): str(value)
        for key, value in metadata.items()
        if value is not None
    }


def get_payment_failure_fields(
    payment_intent: dict[str, Any],
    *,
    fallback_code: str,
    fallback_message: str,
) -> tuple[str, str, str]:
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
    failure_reason = failure_code
    return failure_code, failure_message, failure_reason


def get_locked_payment_by_intent(
    db: Session, provider_payment_intent_id: str
) -> Payment | None:
    return db.scalars(
        select(Payment)
        .where(Payment.provider_payment_intent_id == provider_payment_intent_id)
        .with_for_update()
        .limit(1)
    ).first()


def get_locked_booking(db: Session, booking_id: uuid.UUID | None) -> Booking | None:
    if booking_id is None:
        return None

    return db.scalars(
        select(Booking).where(Booking.id == booking_id).with_for_update()
    ).first()


def get_locked_game(db: Session, game_id: uuid.UUID | None) -> Game | None:
    if game_id is None:
        return None

    return db.scalars(
        select(Game).where(Game.id == game_id).with_for_update()
    ).first()


def get_locked_booking_participants(
    db: Session, booking_id: uuid.UUID, statuses: set[str]
) -> list[GameParticipant]:
    return list(
        db.scalars(
            select(GameParticipant)
            .where(
                GameParticipant.booking_id == booking_id,
                GameParticipant.participant_status.in_(statuses),
            )
            .order_by(
                GameParticipant.roster_order.asc().nulls_last(),
                GameParticipant.joined_at.asc(),
            )
            .with_for_update()
        ).all()
    )


def mark_event_processed(event: PaymentEvent, now: datetime) -> None:
    event.processing_status = "processed"
    event.processed_at = now
    event.processing_error = None


def mark_event_failed(event: PaymentEvent, error: str) -> None:
    event.processing_status = "failed"
    event.processed_at = None
    event.processing_error = error


def mark_event_ignored(event: PaymentEvent, reason: str) -> None:
    event.processing_status = "ignored"
    event.processed_at = None
    event.processing_error = reason


def add_booking_status_history(
    db: Session,
    booking: Booking,
    *,
    old_booking_status: str,
    old_payment_status: str,
    reason: str,
) -> None:
    if (
        old_booking_status == booking.booking_status
        and old_payment_status == booking.payment_status
    ):
        return

    db.add(
        BookingStatusHistory(
            id=uuid.uuid4(),
            booking_id=booking.id,
            old_booking_status=old_booking_status,
            new_booking_status=booking.booking_status,
            old_payment_status=old_payment_status,
            new_payment_status=booking.payment_status,
            changed_by_user_id=None,
            change_source="payment_webhook",
            change_reason=reason,
        )
    )


def add_participant_status_history(
    db: Session,
    participant: GameParticipant,
    *,
    old_participant_status: str,
    old_attendance_status: str,
    reason: str,
) -> None:
    if (
        old_participant_status == participant.participant_status
        and old_attendance_status == participant.attendance_status
    ):
        return

    db.add(
        ParticipantStatusHistory(
            id=uuid.uuid4(),
            participant_id=participant.id,
            old_participant_status=old_participant_status,
            new_participant_status=participant.participant_status,
            old_attendance_status=old_attendance_status,
            new_attendance_status=participant.attendance_status,
            changed_by_user_id=None,
            change_source="payment_webhook",
            change_reason=reason,
        )
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

    if payment.payment_status in POST_SUCCESS_INTERNAL_PAYMENT_STATUSES:
        mark_event_processed(event, now)
        return

    payment.payment_status = "succeeded"
    payment.provider_charge_id = get_latest_charge_id(payment_intent)
    payment.paid_at = payment.paid_at or now
    payment.failure_code = None
    payment.failure_message = None
    payment.failure_reason = None
    payment.updated_at = now
    db.add(payment)

    if booking.booking_status != "pending_payment":
        mark_event_failed(
            event,
            "Payment succeeded for a booking that is no longer pending payment.",
        )
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

    if count_roster_players(db, booking.game_id) > game.total_spots:
        mark_event_failed(event, "Game roster is over capacity before confirmation.")
        return

    old_booking_status = booking.booking_status
    old_payment_status = booking.payment_status
    next_roster_order = get_next_roster_order(db, booking.game_id)

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
    mark_event_processed(event, now)


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
        require_metadata=False,
    )
    if validation_error is not None:
        mark_event_failed(event, validation_error)
        return

    if payment.payment_status in POST_SUCCESS_INTERNAL_PAYMENT_STATUSES:
        mark_event_ignored(event, "Processing event arrived after payment success.")
        return

    if payment.payment_status not in PENDING_INTERNAL_PAYMENT_STATUSES:
        mark_event_ignored(event, "Payment is no longer pending.")
        return

    old_booking_status = booking.booking_status
    old_payment_status = booking.payment_status
    payment.payment_status = "processing"
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
) -> None:
    failure_code, failure_message, failure_reason = get_payment_failure_fields(
        payment_intent,
        fallback_code=fallback_code,
        fallback_message=fallback_message,
    )
    payment.payment_status = payment_status
    payment.provider_charge_id = get_latest_charge_id(payment_intent)
    payment.failure_code = failure_code
    payment.failure_message = failure_message
    payment.failure_reason = failure_reason
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

    pending_participants = get_locked_booking_participants(
        db, booking.id, {"pending_payment"}
    )
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
            reason=history_reason,
        )

    if game is not None:
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
        require_metadata=False,
    )
    if validation_error is not None:
        mark_event_failed(event, validation_error)
        return

    if payment.payment_status in POST_SUCCESS_INTERNAL_PAYMENT_STATUSES:
        mark_event_ignored(event, "Failure or cancel event arrived after payment success.")
        return

    if is_canceled:
        terminal_payment_status = "canceled"
        terminal_booking_status = "expired"
        fallback_code = "payment_intent_canceled"
        fallback_message = "Stripe payment intent was canceled."
        history_reason = "Stripe payment_intent.canceled released checkout hold."
    else:
        terminal_payment_status = "failed"
        terminal_booking_status = "failed"
        fallback_code = "payment_intent_payment_failed"
        fallback_message = "Stripe payment intent failed."
        history_reason = "Stripe payment_intent.payment_failed released checkout hold."

    if payment.payment_status == terminal_payment_status:
        mark_event_processed(event, now)
        return

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

    payment = get_locked_payment_by_intent(db, payment_intent_id)
    if payment is None:
        mark_event_ignored(event, "No internal payment matched this PaymentIntent.")
        return

    event.payment_id = payment.id

    if event_type == "payment_intent.succeeded":
        apply_payment_intent_succeeded(db, event, payment, payment_intent, now)
        return

    if event_type == "payment_intent.processing":
        apply_payment_intent_processing(db, event, payment, payment_intent, now)
        return

    if event_type == "payment_intent.payment_failed":
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
    if event.event_type not in HANDLED_PAYMENT_INTENT_EVENTS:
        mark_event_ignored(event, "Unhandled Stripe event type.")
        return

    process_payment_intent_event(db, event, event_payload, now)


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def handle_stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(None, alias="Stripe-Signature"),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    if not stripe_signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe-Signature header.",
        )

    payload = await request.body()
    try:
        stripe_event = construct_webhook_event(payload, stripe_signature)
    except StripeConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Stripe webhook signature or payload.",
        ) from exc

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

    now = datetime.now(timezone.utc)
    payment_event = PaymentEvent(
        id=uuid.uuid4(),
        payment_id=None,
        provider="stripe",
        provider_event_id=provider_event_id,
        event_type=event_type,
        raw_payload=event_payload,
        processing_status="pending",
        processed_at=None,
        processing_error=None,
        created_at=now,
    )

    try:
        db.add(payment_event)
        process_stripe_event(db, payment_event, event_payload, now)
        db.add(payment_event)
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
