"""Waitlist workflow orchestration for game joins and promotion."""

import uuid
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import (
    Booking,
    Game,
    GameParticipant,
    Payment,
    User,
    UserPaymentMethod,
    WaitlistEntry,
)
from backend.schemas.game_schema import GameJoinCreate
from backend.services.game_rules import (
    AUTO_CHARGE_CONSENT_VERSION_MAX_LENGTH,
    WAITLIST_PROMOTION_CANDIDATE_STATUSES,
    game_requires_app_player_payment,
    is_roster_locked,
)
from backend.services.game_service import (
    count_roster_players,
    get_booking_participants,
    get_existing_active_participant,
    get_next_roster_order,
    get_next_waitlist_position,
    sync_game_capacity_status,
)
from backend.services.game_notification_service import (
    create_waitlist_payment_failed_notification,
    create_waitlist_promotion_notification,
)
from backend.services.payment_method_service import is_saved_payment_method_expired
from backend.services.stripe_service import (
    StripeConfigError,
    StripePaymentIntentResult,
    confirm_payment_intent,
    create_payment_intent,
    map_payment_intent_status,
)


def get_authorized_waitlist_payment_method(
    db: Session,
    joining_user_id: uuid.UUID,
    joining_user_stripe_customer_id: str | None,
    payment_method_id: uuid.UUID | None,
    now: datetime,
) -> UserPaymentMethod:
    if payment_method_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Choose a saved card before joining this waitlist.",
        )

    payment_method = db.get(UserPaymentMethod, payment_method_id)
    if payment_method is None or payment_method.user_id != joining_user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment method not found.",
        )

    if payment_method.method_status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only active payment methods can be used for waitlist auto-charge.",
        )

    if is_saved_payment_method_expired(payment_method, now):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This saved card is expired. Choose another card.",
        )

    if (
        not joining_user_stripe_customer_id
        or payment_method.stripe_customer_id != joining_user_stripe_customer_id
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This payment method is not linked to your Stripe customer.",
        )

    return payment_method


def normalize_auto_charge_consent_version(version: str | None) -> str:
    normalized_version = " ".join((version or "").strip().split())
    if not normalized_version:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="auto_charge_consent_version is required for this waitlist.",
        )

    if len(normalized_version) > AUTO_CHARGE_CONSENT_VERSION_MAX_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "auto_charge_consent_version must be "
                f"{AUTO_CHARGE_CONSENT_VERSION_MAX_LENGTH} characters or fewer."
            ),
        )

    return normalized_version


def build_waitlist_entry_for_join(
    db: Session,
    db_game: Game,
    booking: Booking,
    joining_user: User,
    join_request: GameJoinCreate,
    now: datetime,
) -> WaitlistEntry:
    authorized_payment_method: UserPaymentMethod | None = None
    auto_charge_consent_version: str | None = None

    if game_requires_app_player_payment(db_game):
        if not join_request.auto_charge_consent_accepted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "You must authorize Pickup Lane to charge your saved card "
                    "if a spot opens before joining this waitlist."
                ),
            )
        auto_charge_consent_version = normalize_auto_charge_consent_version(
            join_request.auto_charge_consent_version
        )
        authorized_payment_method = get_authorized_waitlist_payment_method(
            db,
            joining_user.id,
            joining_user.stripe_customer_id,
            join_request.payment_method_id,
            now,
        )

    return WaitlistEntry(
        id=uuid.uuid4(),
        game_id=db_game.id,
        user_id=joining_user.id,
        party_size=booking.participant_count,
        position=get_next_waitlist_position(db, db_game.id),
        waitlist_status="active",
        auto_charge_consent_at=now if authorized_payment_method is not None else None,
        auto_charge_consent_version=auto_charge_consent_version,
        authorized_payment_method_id=(
            authorized_payment_method.id if authorized_payment_method is not None else None
        ),
        authorized_stripe_payment_method_id=(
            authorized_payment_method.stripe_payment_method_id
            if authorized_payment_method is not None
            else None
        ),
        authorized_payment_method_brand=(
            authorized_payment_method.card_brand
            if authorized_payment_method is not None
            else None
        ),
        authorized_payment_method_last4=(
            authorized_payment_method.card_last4
            if authorized_payment_method is not None
            else None
        ),
        authorized_amount_cents=(
            booking.total_cents if authorized_payment_method is not None else None
        ),
        joined_at=now,
    )


def create_waitlist_auto_charge_payment(
    db_game: Game,
    booking: Booking,
    waitlist_entry: WaitlistEntry,
    now: datetime,
) -> Payment:
    payment_id = uuid.uuid4()
    return Payment(
        id=payment_id,
        payer_user_id=booking.buyer_user_id,
        booking_id=booking.id,
        game_id=None,
        payment_type="booking",
        provider="stripe",
        provider_payment_intent_id=None,
        provider_charge_id=None,
        idempotency_key=(
            f"waitlist:{waitlist_entry.id}:booking:{booking.id}:auto_charge"
        ),
        amount_cents=booking.total_cents,
        currency=booking.currency,
        payment_status="requires_payment_method",
        paid_at=None,
        failure_code=None,
        failure_message=None,
        payment_metadata={
            "source": "waitlist_auto_promote",
            "game_id": str(db_game.id),
            "booking_id": str(booking.id),
            "waitlist_entry_id": str(waitlist_entry.id),
            "user_id": str(booking.buyer_user_id),
            "authorized_amount_cents": waitlist_entry.authorized_amount_cents,
            "auto_charge_consent_version": (
                waitlist_entry.auto_charge_consent_version
            ),
            "auto_charge_consent_at": (
                waitlist_entry.auto_charge_consent_at.isoformat()
                if waitlist_entry.auto_charge_consent_at is not None
                else None
            ),
        },
        created_at=now,
        updated_at=now,
    )


def mark_paid_waitlist_auto_promotion_processing(
    db: Session,
    waitlist_entry: WaitlistEntry,
    booking: Booking,
    booking_participants: list[GameParticipant],
    now: datetime,
) -> None:
    waitlist_entry.waitlist_status = "payment_processing"
    waitlist_entry.promoted_booking_id = booking.id
    waitlist_entry.promoted_at = waitlist_entry.promoted_at or now
    waitlist_entry.updated_at = now
    db.add(waitlist_entry)

    booking.booking_status = "pending_payment"
    booking.payment_status = "processing"
    booking.expires_at = None
    booking.updated_at = now
    db.add(booking)

    for booking_participant in booking_participants:
        booking_participant.participant_status = "pending_payment"
        booking_participant.attendance_status = "not_applicable"
        booking_participant.roster_order = None
        booking_participant.updated_at = now
        db.add(booking_participant)


def mark_paid_waitlist_auto_promotion_failed(
    db: Session,
    db_game: Game,
    waitlist_entry: WaitlistEntry,
    booking: Booking,
    booking_participants: list[GameParticipant],
    payment: Payment | None,
    now: datetime,
    *,
    payment_status: str | None,
    failure_code: str,
    failure_message: str,
) -> None:
    if payment is not None:
        payment.payment_status = payment_status or "failed"
        payment.failure_code = failure_code
        payment.failure_message = failure_message
        payment.updated_at = now
        db.add(payment)

    waitlist_entry.waitlist_status = "payment_failed"
    waitlist_entry.promoted_booking_id = booking.id
    waitlist_entry.promoted_at = waitlist_entry.promoted_at or now
    waitlist_entry.cancelled_at = now
    waitlist_entry.updated_at = now
    db.add(waitlist_entry)

    booking.booking_status = "failed"
    booking.payment_status = "failed"
    booking.expires_at = None
    booking.updated_at = now
    db.add(booking)

    for booking_participant in booking_participants:
        booking_participant.participant_status = "removed"
        booking_participant.attendance_status = "not_applicable"
        booking_participant.cancellation_type = "payment_failed"
        booking_participant.cancelled_at = now
        booking_participant.roster_order = None
        booking_participant.updated_at = now
        db.add(booking_participant)

    create_waitlist_payment_failed_notification(
        db,
        db_game,
        booking,
        payment,
        now,
    )


def confirm_paid_waitlist_auto_promotion(
    db: Session,
    db_game: Game,
    waitlist_entry: WaitlistEntry,
    booking: Booking,
    booking_participants: list[GameParticipant],
    payment: Payment,
    payment_intent: StripePaymentIntentResult,
    now: datetime,
) -> None:
    next_roster_order = get_next_roster_order(db, db_game.id)
    for index, booking_participant in enumerate(booking_participants):
        booking_participant.participant_status = "confirmed"
        booking_participant.attendance_status = "unknown"
        booking_participant.confirmed_at = now
        booking_participant.roster_order = next_roster_order + index
        booking_participant.updated_at = now
        db.add(booking_participant)

    booking.booking_status = "confirmed"
    booking.payment_status = "paid"
    booking.booked_at = now
    booking.expires_at = None
    booking.updated_at = now
    db.add(booking)

    payment.payment_status = "succeeded"
    payment.provider_charge_id = payment_intent.latest_charge_id
    payment.paid_at = now
    payment.failure_code = None
    payment.failure_message = None
    payment.updated_at = now
    db.add(payment)

    waitlist_entry.waitlist_status = "accepted"
    waitlist_entry.promoted_booking_id = booking.id
    waitlist_entry.promoted_at = waitlist_entry.promoted_at or now
    waitlist_entry.updated_at = now
    db.add(waitlist_entry)

    create_waitlist_promotion_notification(
        db,
        db_game,
        waitlist_entry,
        booking_participants[0],
        now,
        payment,
    )


def paid_waitlist_prerequisites_missing(
    waitlist_entry: WaitlistEntry,
    booking: Booking,
) -> bool:
    return (
        waitlist_entry.auto_charge_consent_at is None
        or not waitlist_entry.auto_charge_consent_version
        or not waitlist_entry.authorized_stripe_payment_method_id
        or waitlist_entry.authorized_amount_cents is None
        or waitlist_entry.authorized_amount_cents < booking.total_cents
    )


def attempt_paid_waitlist_auto_promotion(
    db: Session,
    db_game: Game,
    waitlist_entry: WaitlistEntry,
    booking: Booking,
    booking_participants: list[GameParticipant],
    now: datetime,
) -> tuple[str, int]:
    if paid_waitlist_prerequisites_missing(waitlist_entry, booking):
        mark_paid_waitlist_auto_promotion_failed(
            db,
            db_game,
            waitlist_entry,
            booking,
            booking_participants,
            None,
            now,
            payment_status=None,
            failure_code="waitlist_auto_charge_missing_prerequisite",
            failure_message="Waitlist auto-charge prerequisites were missing.",
        )
        return "failed", 0

    mark_paid_waitlist_auto_promotion_processing(
        db,
        waitlist_entry,
        booking,
        booking_participants,
        now,
    )
    payment = create_waitlist_auto_charge_payment(
        db_game,
        booking,
        waitlist_entry,
        now,
    )
    db.add(payment)
    db.flush()

    try:
        buyer_user = db.get(User, booking.buyer_user_id)
        payment_intent = create_payment_intent(
            amount_cents=payment.amount_cents,
            currency=payment.currency,
            idempotency_key=payment.idempotency_key,
            metadata={
                "source": "waitlist_auto_promote",
                "user_id": str(booking.buyer_user_id),
                "game_id": str(db_game.id),
                "booking_id": str(booking.id),
                "payment_id": str(payment.id),
                "waitlist_entry_id": str(waitlist_entry.id),
                "authorized_amount_cents": str(waitlist_entry.authorized_amount_cents),
            },
            customer_id=buyer_user.stripe_customer_id if buyer_user is not None else None,
        )
        payment.provider_payment_intent_id = payment_intent.id
        payment.payment_status = "processing"
        payment.updated_at = now
        db.add(payment)

        payment_intent = confirm_payment_intent(
            payment_intent.id,
            payment_method_id=waitlist_entry.authorized_stripe_payment_method_id,
            off_session=True,
        )
        payment.provider_payment_intent_id = payment_intent.id
        payment.provider_charge_id = payment_intent.latest_charge_id
        payment.updated_at = now
        db.add(payment)
    except StripeConfigError as exc:
        mark_paid_waitlist_auto_promotion_failed(
            db,
            db_game,
            waitlist_entry,
            booking,
            booking_participants,
            payment,
            now,
            payment_status="failed",
            failure_code="waitlist_auto_charge_stripe_config_error",
            failure_message=str(exc),
        )
        return "failed", 0
    except Exception as exc:
        mark_paid_waitlist_auto_promotion_failed(
            db,
            db_game,
            waitlist_entry,
            booking,
            booking_participants,
            payment,
            now,
            payment_status="failed",
            failure_code="waitlist_auto_charge_stripe_error",
            failure_message=str(exc) or "Stripe could not complete auto-charge.",
        )
        return "failed", 0

    payment_status = map_payment_intent_status(payment_intent.status)
    if payment_status == "succeeded":
        confirm_paid_waitlist_auto_promotion(
            db,
            db_game,
            waitlist_entry,
            booking,
            booking_participants,
            payment,
            payment_intent,
            now,
        )
        return "succeeded", len(booking_participants)

    if payment_status == "processing":
        payment.payment_status = "processing"
        payment.updated_at = now
        db.add(payment)
        return "processing", len(booking_participants)

    mark_paid_waitlist_auto_promotion_failed(
        db,
        db_game,
        waitlist_entry,
        booking,
        booking_participants,
        payment,
        now,
        payment_status=payment_status,
        failure_code=f"waitlist_auto_charge_{payment_status}",
        failure_message="Waitlist auto-charge could not be completed.",
    )
    return "failed", 0


def promote_waitlist_entries(db: Session, db_game: Game, now: datetime) -> None:
    if not db_game.waitlist_enabled:
        sync_game_capacity_status(db, db_game)
        return

    if is_roster_locked(db_game, now):
        sync_game_capacity_status(db, db_game)
        return

    available_spots = max(db_game.total_spots - count_roster_players(db, db_game.id), 0)
    if available_spots <= 0:
        sync_game_capacity_status(db, db_game)
        return
    app_payment_required = game_requires_app_player_payment(db_game)

    waitlist_entries = list(
        db.scalars(
            select(WaitlistEntry)
            .where(
                WaitlistEntry.game_id == db_game.id,
                WaitlistEntry.waitlist_status.in_(WAITLIST_PROMOTION_CANDIDATE_STATUSES),
            )
            .order_by(WaitlistEntry.position.asc(), WaitlistEntry.joined_at.asc())
        ).all()
    )

    for waitlist_entry in waitlist_entries:
        if waitlist_entry.party_size > available_spots:
            continue

        participant = get_existing_active_participant(
            db, db_game.id, waitlist_entry.user_id
        )
        if participant is None or participant.participant_status != "waitlisted":
            waitlist_entry.waitlist_status = "removed"
            waitlist_entry.updated_at = now
            db.add(waitlist_entry)
            continue

        booking = db.get(Booking, participant.booking_id) if participant.booking_id else None
        if booking is None:
            waitlist_entry.waitlist_status = "removed"
            waitlist_entry.updated_at = now
            db.add(waitlist_entry)
            continue

        booking_participants = get_booking_participants(
            db, db_game.id, booking.id, {"waitlisted"}
        )
        if len(booking_participants) != waitlist_entry.party_size:
            waitlist_entry.party_size = len(booking_participants)

        if not booking_participants or len(booking_participants) > available_spots:
            db.add(waitlist_entry)
            continue

        if app_payment_required:
            promotion_status, held_spots = attempt_paid_waitlist_auto_promotion(
                db,
                db_game,
                waitlist_entry,
                booking,
                booking_participants,
                now,
            )
            if promotion_status in {"succeeded", "processing"}:
                available_spots -= held_spots
                if available_spots <= 0:
                    break
            continue

        next_roster_order = get_next_roster_order(db, db_game.id)
        for index, booking_participant in enumerate(booking_participants):
            booking_participant.participant_status = "confirmed"
            booking_participant.attendance_status = "unknown"
            booking_participant.confirmed_at = now
            booking_participant.roster_order = next_roster_order + index
            booking_participant.updated_at = now
            db.add(booking_participant)

        booking.booking_status = "confirmed"
        booking.payment_status = "not_required"
        booking.booked_at = now
        booking.updated_at = now
        db.add(booking)

        waitlist_entry.waitlist_status = "accepted"
        waitlist_entry.promoted_booking_id = booking.id
        waitlist_entry.promoted_at = now
        waitlist_entry.updated_at = now
        db.add(waitlist_entry)
        create_waitlist_promotion_notification(
            db,
            db_game,
            waitlist_entry,
            participant,
            now,
        )

        available_spots -= len(booking_participants)
        if available_spots <= 0:
            break

    sync_game_capacity_status(db, db_game)
