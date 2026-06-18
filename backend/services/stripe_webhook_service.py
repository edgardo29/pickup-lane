"""Application logic for trusted Stripe webhook events."""

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import (
    Booking,
    Game,
    GameCreditUsage,
    GameParticipant,
    Notification,
    Payment,
    PaymentEvent,
    Refund,
    User,
    WaitlistEntry,
)
from backend.services.payment_event_service import build_payment_event_conflict_detail
from backend.services.game_credit_service import (
    RESTORED_USAGE_STATUS,
    redeem_reserved_game_credits,
    release_reserved_game_credits,
)
from backend.services.game_service import (
    count_roster_players,
    create_or_reopen_booking_refunded_notification,
    create_waitlist_payment_failed_notification,
    create_waitlist_promotion_notification,
    game_requires_app_player_payment,
    get_next_roster_order,
    sync_game_capacity_status,
)
from backend.services.notification_service import (
    build_game_notification_fields,
    reopen_aggregated_notification,
)
from backend.services.status_history_service import (
    add_booking_status_history_if_changed,
    add_participant_status_history_if_changed,
)

HANDLED_PAYMENT_INTENT_EVENTS = {
    "payment_intent.succeeded",
    "payment_intent.payment_failed",
    "payment_intent.canceled",
    "payment_intent.processing",
}
HANDLED_REFUND_EVENTS = {
    "refund.created",
    "refund.updated",
    "refund.failed",
    "charge.refund.updated",
}
HANDLED_STRIPE_EVENTS = HANDLED_PAYMENT_INTENT_EVENTS | HANDLED_REFUND_EVENTS
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


def get_locked_payment(db: Session, payment_id: uuid.UUID | None) -> Payment | None:
    if payment_id is None:
        return None

    return db.scalars(
        select(Payment).where(Payment.id == payment_id).with_for_update()
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


def get_locked_refund_by_provider_id(
    db: Session, provider_refund_id: str
) -> Refund | None:
    return db.scalars(
        select(Refund)
        .where(Refund.provider_refund_id == provider_refund_id)
        .with_for_update()
        .limit(1)
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

    return db.get(WaitlistEntry, parsed_waitlist_entry_id)


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
    payment.provider_charge_id = get_latest_charge_id(payment_intent)
    payment.paid_at = payment.paid_at or now
    payment.failure_code = None
    payment.failure_message = None
    payment.failure_reason = None
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
    restored_credit: bool = False,
    emit_checkout_failure_notification: bool = False,
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
        require_metadata=False,
    )
    if validation_error is not None:
        mark_event_failed(event, validation_error)
        return

    if payment.payment_status in POST_SUCCESS_INTERNAL_PAYMENT_STATUSES:
        mark_event_ignored(event, "Failure or cancel event arrived after payment success.")
        return

    waitlist_entry = get_waitlist_auto_promote_entry(db, payment)
    if is_canceled:
        terminal_payment_status = "canceled"
        terminal_booking_status = "failed" if waitlist_entry is not None else "expired"
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
                release_reason=fallback_code,
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
    payment = get_locked_payment(db, payment_id)
    booking = get_locked_booking(db, booking_id)
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
        provider_refund_id=provider_refund_id,
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

    next_payment_status = (
        "refunded" if refunded_cents >= payment.amount_cents else "partially_refunded"
    )
    payment.payment_status = next_payment_status
    payment.updated_at = now
    db.add(payment)

    if booking is not None:
        booking.payment_status = next_payment_status
        booking.updated_at = now
        db.add(booking)


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

    refund = get_locked_refund_by_provider_id(db, provider_refund_id)
    if refund is None:
        refund = recover_refund_from_metadata(db, refund_payload, now)

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
    if payment is None:
        mark_event_failed(event, "Internal payment for this refund was not found.")
        return

    refund_status = map_stripe_refund_event_status(
        event_payload["type"], refund_payload
    )
    refund.refund_status = refund_status
    refund.updated_at = now
    if refund_status in {"processing", "succeeded"} and refund.approved_at is None:
        refund.approved_at = now
    if refund_status == "succeeded":
        refund.refunded_at = refund.refunded_at or now
    elif refund_status in {"failed", "cancelled"}:
        refund.refunded_at = None
    db.add(refund)

    if refund_status == "succeeded":
        db.flush()
        sync_refunded_payment_and_booking(db, payment, booking, now)
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
    if event.event_type not in HANDLED_STRIPE_EVENTS:
        mark_event_ignored(event, "Unhandled Stripe event type.")
        return

    if event.event_type in HANDLED_PAYMENT_INTENT_EVENTS:
        process_payment_intent_event(db, event, event_payload, now)
        return

    process_refund_event(db, event, event_payload, now)
