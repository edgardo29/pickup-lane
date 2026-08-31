"""Official game checkout orchestration and payment state helpers."""

import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import (
    Booking,
    Game,
    GameParticipant,
    Payment,
    PaymentCompensation,
    PaymentConfirmationAttempt,
    User,
    WaitlistEntry,
)
from backend.observability.timeouts import PublicTimeoutError
from backend.schemas.checkout_schema import (
    GameCheckoutPaymentIntentCreate,
    GameCheckoutPaymentIntentRead,
    GameCheckoutStatusRead,
)
from backend.services.auth_service import user_is_active_admin
from backend.services.game_credit_service import (
    CONSUMING_REDEEM_STATUSES,
    GameCreditApplication,
    GameCreditInsufficientBalanceError,
    GameCreditReservationConflictError,
    calculate_user_game_credit_application,
    get_available_game_credit_balance,
    get_booking_credit_usage_total,
    redeem_reserved_game_credits,
    release_reserved_game_credits,
    reserve_game_credits,
)
from backend.services.game_notification_service import (
    create_waitlist_payment_failed_notification,
)
from backend.services.game_rules import (
    JOINABLE_GAME_STATUSES,
    build_game_conflict_detail,
    game_requires_app_player_payment,
    require_join_ready_user,
    require_minimum_age,
    require_roster_window_open,
    validate_guest_count,
)
from backend.services.game_service import (
    build_booking_participants,
    count_roster_players,
    get_existing_active_participant,
    get_existing_active_waitlist_entry,
    get_next_roster_order,
    sync_game_capacity_status,
)
from backend.services.payment_job_service import enqueue_payment_reconcile_job
from backend.services.payment_lifecycle_policy import (
    canonical_fingerprint,
)
from backend.services.payment_method_service import (
    get_current_user_saved_payment_method_for_checkout,
)
from backend.services.payment_rules import PENDING_PAYMENT_STATUSES
from backend.services.status_history_service import (
    add_booking_status_history_if_changed,
    add_participant_status_history_if_changed,
)
from backend.services.stripe_service import (
    StripeConfigError,
    confirm_payment_intent,
    create_payment_intent,
    get_stripe_currency,
    map_payment_intent_status,
    retrieve_payment_intent,
    stripe_payments_enabled,
)
from backend.services.user_service import get_user_display_name
from backend.settings import get_settings

CHECKOUT_HOLD_MINUTES = 2
MINIMUM_USD_PAYMENT_INTENT_AMOUNT_CENTS = 50
CHECKOUT_PROVIDER_RESULT_RECORDING_FAILED_DETAIL = (
    "Stripe created this payment intent, but checkout state could not be recorded. "
    "Check checkout status before retrying."
)
CHECKOUT_PROVIDER_STATUS_RECORDING_FAILED_DETAIL = (
    "Stripe returned this payment intent status, but checkout state could not be "
    "recorded. Check checkout status before retrying."
)
STRIPE_PAYMENTS_DISABLED_DETAIL = "Stripe payments are disabled for this demo."
CHECKOUT_RETURN_URL_INVALID_DETAIL = "Checkout return URL is not supported."


def get_database_now(db: Session) -> datetime:
    database_now = db.scalar(select(func.now()))
    if not isinstance(database_now, datetime):
        raise RuntimeError(  # noqa: TRY004
            "PostgreSQL did not return the current database time"
        )
    return database_now


def get_locked_active_game_or_404(db: Session, game_id: uuid.UUID) -> Game:
    db_game = db.scalars(
        select(Game)
        .where(Game.id == game_id, Game.deleted_at.is_(None))
        .with_for_update()
    ).first()

    if db_game is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found.",
        )

    return db_game


def require_checkout_game_open(db_game: Game, current_user: User, now: datetime) -> None:
    if db_game.public_visibility_status != "visible":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found.",
        )

    require_join_ready_user(current_user)
    require_minimum_age(current_user, db_game.minimum_age)

    if db_game.host_user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hosts are already part of their own game.",
        )

    if not game_requires_app_player_payment(db_game):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stripe checkout is only available for official in-app games.",
        )

    if db_game.join_enforcement_status != "open":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This game is not open for checkout.",
        )

    if (
        db_game.publish_status != "published"
        or db_game.game_status not in JOINABLE_GAME_STATUSES
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This game is not open for checkout.",
        )

    require_roster_window_open(db_game, now, "Checkout is closed for this game.")


def require_stripe_payments_enabled() -> None:
    if not stripe_payments_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=STRIPE_PAYMENTS_DISABLED_DETAIL,
        )


def validate_checkout_return_url(
    return_url: str | None,
    *,
    game_id: uuid.UUID,
) -> str | None:
    if return_url is None:
        return None

    normalized = return_url.strip()
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=CHECKOUT_RETURN_URL_INVALID_DETAIL,
        )

    parsed = urlsplit(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=CHECKOUT_RETURN_URL_INVALID_DETAIL,
        )
    if parsed.username is not None or parsed.password is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=CHECKOUT_RETURN_URL_INVALID_DETAIL,
        )
    if parsed.query or parsed.fragment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=CHECKOUT_RETURN_URL_INVALID_DETAIL,
        )

    origin = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
    allowed_origins = {
        allowed.rstrip("/") for allowed in get_settings().cors_allowed_origins
    }
    if origin not in allowed_origins:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=CHECKOUT_RETURN_URL_INVALID_DETAIL,
        )

    expected_path = f"/games/{game_id}/checkout"
    if parsed.path != expected_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=CHECKOUT_RETURN_URL_INVALID_DETAIL,
        )

    return normalized


def require_provider_verified_checkout_payment_method(
    db: Session,
    payment_method_id: uuid.UUID | None,
    current_user: User,
    *,
    now: datetime,
) -> uuid.UUID:
    if payment_method_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Choose a saved card before checkout.",
        )

    saved_payment_method = get_current_user_saved_payment_method_for_checkout(
        db,
        payment_method_id,
        current_user,
        now=now,
    )
    if saved_payment_method is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Choose a saved card before checkout.",
        )
    return payment_method_id


def expire_stale_pending_checkouts(
    db: Session,
    db_game: Game,
    now: datetime,
    *,
    enqueue_reconciliation: bool = True,
) -> None:
    stale_bookings = db.scalars(
        select(Booking)
        .where(
            Booking.game_id == db_game.id,
            Booking.booking_status == "pending_payment",
            Booking.expires_at.is_not(None),
            Booking.expires_at <= now,
        )
        .order_by(Booking.id.asc())
        .with_for_update()
    ).all()

    if not stale_bookings:
        return

    stale_booking_ids = [booking.id for booking in stale_bookings]
    stale_waitlist_entries = db.scalars(
        select(WaitlistEntry)
        .where(
            WaitlistEntry.promoted_booking_id.in_(stale_booking_ids),
            WaitlistEntry.waitlist_status == "payment_processing",
        )
        .order_by(WaitlistEntry.id.asc())
        .with_for_update()
    ).all()
    stale_participants = db.scalars(
        select(GameParticipant)
        .where(
            GameParticipant.booking_id.in_(stale_booking_ids),
            GameParticipant.participant_status == "pending_payment",
        )
        .order_by(GameParticipant.id.asc())
        .with_for_update()
    ).all()
    stale_payments = db.scalars(
        select(Payment)
        .where(
            Payment.booking_id.in_(stale_booking_ids),
            Payment.payment_status.in_(PENDING_PAYMENT_STATUSES),
        )
        .order_by(Payment.id.asc())
        .with_for_update()
    ).all()
    waitlist_booking_ids = {
        waitlist_entry.promoted_booking_id
        for waitlist_entry in stale_waitlist_entries
        if waitlist_entry.promoted_booking_id is not None
    }

    for booking in stale_bookings:
        old_booking_status = booking.booking_status
        old_payment_status = booking.payment_status
        old_reservation_status = booking.reservation_status
        release_reserved_game_credits(
            db,
            booking.id,
            now=now,
            reason_code="checkout_hold_expired",
            user_id=booking.buyer_user_id,
        )
        booking.booking_status = "expired"
        booking.reservation_status = "released"
        booking.expires_at = None
        booking.updated_at = now
        db.add(booking)
        add_booking_status_history_if_changed(
            db,
            booking,
            old_booking_status=old_booking_status,
            old_payment_status=old_payment_status,
            old_reservation_status=old_reservation_status,
            reason="Checkout reservation expired with provider truth unresolved.",
            change_source="scheduled_job",
        )

    for participant in stale_participants:
        old_participant_status = participant.participant_status
        old_attendance_status = participant.attendance_status
        participant.participant_status = (
            "removed" if participant.booking_id in waitlist_booking_ids else "cancelled"
        )
        participant.cancellation_type = "payment_failed"
        participant.cancelled_at = now
        participant.updated_at = now
        db.add(participant)
        add_participant_status_history_if_changed(
            db,
            participant,
            old_participant_status=old_participant_status,
            old_attendance_status=old_attendance_status,
            reason="Checkout reservation expired with provider truth unresolved.",
            change_source="scheduled_job",
        )

    for waitlist_entry in stale_waitlist_entries:
        waitlist_entry.waitlist_status = "payment_failed"
        waitlist_entry.cancelled_at = waitlist_entry.cancelled_at or now
        waitlist_entry.updated_at = now
        db.add(waitlist_entry)

    for payment in stale_payments:
        payment.updated_at = now
        db.add(payment)
        if enqueue_reconciliation:
            enqueue_payment_reconcile_job(
                db,
                payment.id,
                reason="reservation_expiry",
            )

    bookings_by_id = {booking.id: booking for booking in stale_bookings}
    payments_by_booking_id = {
        payment.booking_id: payment
        for payment in stale_payments
        if payment.booking_id is not None
    }
    for waitlist_entry in stale_waitlist_entries:
        if waitlist_entry.promoted_booking_id is None:
            continue
        booking = bookings_by_id.get(waitlist_entry.promoted_booking_id)
        payment = payments_by_booking_id.get(waitlist_entry.promoted_booking_id)
        if booking is not None and payment is not None:
            create_waitlist_payment_failed_notification(
                db,
                db_game,
                booking,
                payment,
                now,
            )

    db.flush()
    sync_game_capacity_status(db, db_game)
    db_game.updated_at = now
    db.add(db_game)


def get_reusable_pending_checkout(
    db: Session,
    db_game: Game,
    current_user: User,
    *,
    party_size: int,
    subtotal_cents: int,
    now: datetime,
) -> tuple[Booking, Payment] | None:
    statement = (
        select(Booking, Payment)
        .join(Payment, Payment.booking_id == Booking.id)
        .where(
            Booking.game_id == db_game.id,
            Booking.buyer_user_id == current_user.id,
            Booking.booking_status == "pending_payment",
            Booking.payment_status.in_({"processing", "requires_action"}),
            Booking.participant_count == party_size,
            Booking.subtotal_cents == subtotal_cents,
            Booking.expires_at.is_not(None),
            Booking.expires_at > now,
            Payment.payment_type == "booking",
            Payment.payment_status.in_(PENDING_PAYMENT_STATUSES),
            or_(
                Payment.provider_payment_intent_id.is_not(None),
                Payment.payment_status == "unknown",
            ),
        )
        .order_by(Booking.created_at.desc())
        .limit(1)
    )

    row = db.execute(statement).first()
    if row is None:
        return None

    booking, payment = row
    pending_participant_count = (
        db.scalar(
            select(func.count())
            .select_from(GameParticipant)
            .where(
                GameParticipant.booking_id == booking.id,
                GameParticipant.game_id == db_game.id,
                GameParticipant.participant_status == "pending_payment",
            )
        )
        or 0
    )
    if pending_participant_count != party_size:
        return None

    return booking, payment


def build_pending_checkout_rows(
    db_game: Game,
    current_user: User,
    *,
    guest_count: int,
    party_size: int,
    subtotal_cents: int,
    platform_fee_cents: int,
    discount_cents: int,
    total_cents: int,
    now: datetime,
    payment_required: bool,
    credit_application: GameCreditApplication,
) -> tuple[Booking, Payment | None, list[GameParticipant]]:
    booking = Booking(
        id=uuid.uuid4(),
        game_id=db_game.id,
        buyer_user_id=current_user.id,
        booking_status="pending_payment",
        payment_status="processing",
        reservation_status="held",
        participant_count=party_size,
        subtotal_cents=subtotal_cents,
        platform_fee_cents=platform_fee_cents,
        discount_cents=discount_cents,
        total_cents=total_cents,
        currency=db_game.currency,
        price_per_player_snapshot_cents=db_game.price_per_player_cents,
        platform_fee_snapshot_cents=platform_fee_cents,
        booked_at=None,
        expires_at=now + timedelta(minutes=CHECKOUT_HOLD_MINUTES),
    )
    payment = None
    if payment_required:
        payment_id = uuid.uuid4()
        payment = Payment(
            id=payment_id,
            payer_user_id=current_user.id,
            booking_id=booking.id,
            game_id=None,
            payment_type="booking",
            provider="stripe",
            provider_payment_intent_id=None,
            provider_charge_id=None,
            idempotency_key=f"checkout:{booking.id}:{payment_id}:payment_intent",
            creation_fingerprint=canonical_fingerprint(
                {
                    "payment_id": str(payment_id),
                    "booking_id": str(booking.id),
                    "payer_user_id": str(current_user.id),
                    "provider_customer_id": current_user.stripe_customer_id,
                    "amount_cents": credit_application.stripe_amount_cents,
                    "currency": booking.currency,
                    "game_id": str(db_game.id),
                    "participant_count": party_size,
                    "credit_applied_cents": credit_application.credit_applied_cents,
                    "checkout_total_cents": total_cents,
                }
            ),
            provider_customer_id=current_user.stripe_customer_id,
            amount_cents=credit_application.stripe_amount_cents,
            currency=booking.currency,
            payment_status="requires_payment_method",
            paid_at=None,
            failure_code=None,
            failure_message=None,
            payment_metadata={
                "source": "game_checkout",
                "payment_id": str(payment_id),
                "booking_id": str(booking.id),
                "game_id": str(db_game.id),
                "user_id": str(current_user.id),
                "participant_count": party_size,
                "guest_count": guest_count,
                "checkout_hold_expires_at": booking.expires_at.isoformat(),
                "subtotal_cents": subtotal_cents,
                "platform_fee_cents": platform_fee_cents,
                "checkout_total_cents": subtotal_cents + platform_fee_cents,
                "available_credit_cents": credit_application.available_credit_cents,
                "credit_applied_cents": credit_application.credit_applied_cents,
                "minimum_charge_adjustment_cents": (
                    credit_application.minimum_charge_adjustment_cents
                ),
                "final_amount_due_cents": credit_application.final_amount_due_cents,
                "stripe_amount_cents": credit_application.stripe_amount_cents,
            },
        )
    participants = build_booking_participants(
        db_game,
        booking,
        current_user,
        get_user_display_name(current_user),
        guest_count,
        now,
        participant_status="pending_payment",
        first_roster_order=None,
    )

    return booking, payment, participants


def get_credit_application_for_booking(
    db: Session,
    booking: Booking,
    *,
    credit_owner_user_id: uuid.UUID,
    now: datetime,
) -> GameCreditApplication:
    credit_applied_cents = get_booking_credit_usage_total(
        db,
        booking.id,
        statuses=CONSUMING_REDEEM_STATUSES,
    )
    minimum_charge_adjustment_cents = max(
        booking.discount_cents - credit_applied_cents,
        0,
    )
    remaining_available_credit_cents = get_available_game_credit_balance(
        db,
        credit_owner_user_id,
        now=now,
    )
    available_credit_cents = remaining_available_credit_cents + credit_applied_cents
    return GameCreditApplication(
        available_credit_cents=available_credit_cents,
        credit_applied_cents=credit_applied_cents,
        minimum_charge_adjustment_cents=minimum_charge_adjustment_cents,
        final_amount_due_cents=booking.total_cents,
        stripe_amount_cents=booking.total_cents,
        payment_required=booking.total_cents > 0,
    )


def build_checkout_response(
    db: Session,
    booking: Booking,
    payment: Payment | None,
    client_secret: str | None,
    *,
    credit_application: GameCreditApplication | None = None,
    stripe_status: str | None = None,
) -> GameCheckoutPaymentIntentRead:
    if (
        payment is not None
        and payment.payment_status == "requires_action"
        and not client_secret
    ):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Stripe did not return a client secret for this payment.",
        )

    application = credit_application or get_credit_application_for_booking(
        db,
        booking,
        credit_owner_user_id=booking.buyer_user_id,
        now=datetime.now(timezone.utc),
    )
    checkout_total_cents = booking.subtotal_cents + booking.platform_fee_cents
    compensation = (
        db.scalars(
            select(PaymentCompensation)
            .where(
                PaymentCompensation.booking_id == booking.id,
                PaymentCompensation.status.in_({"required", "processing"}),
            )
            .order_by(PaymentCompensation.created_at.desc())
            .limit(1)
        ).first()
        if payment is not None
        else None
    )
    return GameCheckoutPaymentIntentRead(
        client_secret=client_secret,
        booking_id=booking.id,
        payment_id=payment.id if payment is not None else None,
        amount_cents=application.stripe_amount_cents,
        currency=booking.currency,
        stripe_status=stripe_status or (
            payment.payment_status if payment is not None else None
        ),
        subtotal_cents=booking.subtotal_cents,
        platform_fee_cents=booking.platform_fee_cents,
        checkout_total_cents=checkout_total_cents,
        available_credit_cents=application.available_credit_cents,
        credit_applied_cents=application.credit_applied_cents,
        minimum_charge_adjustment_cents=application.minimum_charge_adjustment_cents,
        final_amount_due_cents=application.final_amount_due_cents,
        stripe_amount_cents=application.stripe_amount_cents,
        payment_required=application.payment_required,
        booking_status=booking.booking_status,
        booking_payment_status=booking.payment_status,
        reservation_status=booking.reservation_status,
        payment_status=payment.payment_status if payment is not None else None,
        provider_status=payment.provider_status if payment is not None else None,
        compensation_status=compensation.status if compensation is not None else None,
    )


def confirm_credit_covered_checkout(
    db: Session,
    db_game: Game,
    booking: Booking,
    participants: list[GameParticipant],
    *,
    now: datetime,
) -> None:
    old_booking_status = booking.booking_status
    old_payment_status = booking.payment_status
    next_roster_order = get_next_roster_order(db, booking.game_id)

    for index, participant in enumerate(participants):
        old_participant_status = participant.participant_status
        old_attendance_status = participant.attendance_status
        participant.participant_status = "confirmed"
        participant.attendance_status = "unknown"
        participant.confirmed_at = participant.confirmed_at or now
        participant.roster_order = participant.roster_order or next_roster_order + index
        participant.updated_at = now
        db.add(participant)
        add_participant_status_history_if_changed(
            db,
            participant,
            old_participant_status=old_participant_status,
            old_attendance_status=old_attendance_status,
            reason="Game credit checkout confirmed without Stripe payment.",
        )

    booking.booking_status = "confirmed"
    booking.reservation_status = "confirmed"
    booking.payment_status = "paid"
    booking.booked_at = booking.booked_at or now
    booking.expires_at = None
    booking.updated_at = now
    db.add(booking)
    add_booking_status_history_if_changed(
        db,
        booking,
        old_booking_status=old_booking_status,
        old_payment_status=old_payment_status,
        reason="Game credit checkout confirmed without Stripe payment.",
    )

    sync_game_capacity_status(db, db_game)
    db_game.updated_at = now
    db.add(db_game)


def resume_pending_checkout_with_locked_game(
    db: Session,
    db_game: Game,
    checkout_request: GameCheckoutPaymentIntentCreate,
    current_user: User,
    *,
    return_url: str | None,
    party_size: int,
    subtotal_cents: int,
    now: datetime,
    provider_verified_payment_method_id: uuid.UUID | None = None,
) -> GameCheckoutPaymentIntentRead | None:
    reusable_checkout = get_reusable_pending_checkout(
        db,
        db_game,
        current_user,
        party_size=party_size,
        subtotal_cents=subtotal_cents,
        now=now,
    )
    if reusable_checkout is None:
        return None

    booking, payment = reusable_checkout
    locked_game_id = db_game.id
    booking_id = booking.id
    payment_id = payment.id
    payment_amount_cents = payment.amount_cents
    payment_currency = payment.currency
    participant_count = booking.participant_count
    saved_payment_method = None
    if payment.payment_status == "requires_payment_method":
        if provider_verified_payment_method_id != checkout_request.payment_method_id:
            db.rollback()
            verified_payment_method_id = require_provider_verified_checkout_payment_method(
                db,
                checkout_request.payment_method_id,
                current_user,
                now=now,
            )
            return resume_serialized_pending_checkout(
                db,
                locked_game_id,
                checkout_request,
                current_user,
                return_url=return_url,
                party_size=party_size,
                subtotal_cents=subtotal_cents,
                provider_verified_payment_method_id=verified_payment_method_id,
            )
        saved_payment_method = get_current_user_saved_payment_method_for_checkout(
            db,
            checkout_request.payment_method_id,
            current_user,
            now=now,
            verify_provider=False,
        )
        if saved_payment_method is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Choose a saved card before checkout.",
            )

    provider_payment_intent_id = payment.provider_payment_intent_id
    if provider_payment_intent_id is None:
        enqueue_payment_reconcile_job(
            db,
            payment.id,
            reason="payment_intent_creation",
        )
        db.commit()
        db.refresh(payment)
        db.refresh(booking)
        return build_checkout_response(
            db,
            booking,
            payment,
            None,
            stripe_status=payment.payment_status,
        )

    db.commit()
    try:
        payment_intent = retrieve_payment_intent(provider_payment_intent_id)
    except StripeConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except PublicTimeoutError:
        from backend.services.stripe_webhook_service import (
            lock_booking_payment_domain_by_booking_id,
        )

        timeout_now = get_database_now(db)
        booking = lock_booking_payment_domain_by_booking_id(db, booking_id)
        if (
            booking is not None
            and booking.expires_at is not None
            and booking.expires_at <= timeout_now
        ):
            db_game = db.get(Game, booking.game_id)
            if db_game is not None:
                expire_stale_pending_checkouts(
                    db,
                    db_game,
                    timeout_now,
                    enqueue_reconciliation=False,
                )
                enqueue_payment_reconcile_job(
                    db,
                    payment_id,
                    reason="checkout_status_refresh_timeout",
                )
                db.commit()
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Stripe could not retrieve this payment intent.",
        ) from exc

    stripe_status = payment_intent.status
    payment_status = map_payment_intent_status(stripe_status)
    if payment_status not in PENDING_PAYMENT_STATUSES and stripe_status != "succeeded":
        return None

    if stripe_status == "requires_payment_method":
        if saved_payment_method is None:
            verify_provider = (
                provider_verified_payment_method_id
                != checkout_request.payment_method_id
            )
            saved_payment_method = get_current_user_saved_payment_method_for_checkout(
                db,
                checkout_request.payment_method_id,
                current_user,
                now=now,
                verify_provider=verify_provider,
            )
            if saved_payment_method is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Choose a saved card before checkout.",
                )
        confirmation_identity = {
            "payment_id": str(payment_id),
            "booking_id": str(booking_id),
            "payer_user_id": str(current_user.id),
            "provider_customer_id": current_user.stripe_customer_id,
            "provider_payment_method_id": saved_payment_method.stripe_payment_method_id,
            "provider_payment_intent_id": provider_payment_intent_id,
            "amount_cents": payment_amount_cents,
            "currency": payment_currency,
            "game_id": str(locked_game_id),
            "participant_count": participant_count,
        }
        confirmation_fingerprint = canonical_fingerprint(confirmation_identity)
        confirmation_idempotency_key = (
            f"checkout-confirm:{payment_id}:{confirmation_fingerprint}"
        )
        from backend.services.stripe_webhook_service import (
            lock_booking_payment_domain_by_booking_id,
        )

        confirmation_now = get_database_now(db)
        booking = lock_booking_payment_domain_by_booking_id(db, booking_id)
        if booking is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Checkout state changed before payment confirmation.",
            )
        payment = db.scalars(
            select(Payment).where(Payment.id == payment_id).with_for_update()
        ).one()
        if (
            booking.reservation_status != "held"
            or booking.expires_at is None
            or booking.expires_at <= confirmation_now
        ):
            if booking.expires_at is not None and booking.expires_at <= confirmation_now:
                db_game = db.get(Game, booking.game_id)
                if db_game is not None:
                    expire_stale_pending_checkouts(
                        db,
                        db_game,
                        confirmation_now,
                        enqueue_reconciliation=False,
                    )
            return None
        confirmation_attempt = db.scalars(
            select(PaymentConfirmationAttempt).where(
                PaymentConfirmationAttempt.payment_id == payment_id,
                PaymentConfirmationAttempt.confirmation_fingerprint
                == confirmation_fingerprint,
            )
        ).first()
        if confirmation_attempt is None:
            confirmation_attempt = PaymentConfirmationAttempt(
                id=uuid.uuid4(),
                payment_id=payment_id,
                booking_id=booking_id,
                user_id=current_user.id,
                provider_customer_id=current_user.stripe_customer_id,
                provider_payment_method_id=(
                    saved_payment_method.stripe_payment_method_id
                ),
                confirmation_fingerprint=confirmation_fingerprint,
                confirmation_idempotency_key=confirmation_idempotency_key,
                outcome="pending",
            )
            db.add(confirmation_attempt)
        db.commit()
        try:
            payment_intent = confirm_payment_intent(
                provider_payment_intent_id,
                payment_method_id=saved_payment_method.stripe_payment_method_id,
                return_url=return_url,
                idempotency_key=confirmation_idempotency_key,
            )
        except StripeConfigError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc
        except PublicTimeoutError:
            timeout_now = get_database_now(db)
            booking = lock_booking_payment_domain_by_booking_id(db, booking_id)
            confirmation_attempt = db.scalars(
                select(PaymentConfirmationAttempt)
                .where(PaymentConfirmationAttempt.id == confirmation_attempt.id)
                .with_for_update()
            ).one()
            payment = db.scalars(
                select(Payment).where(Payment.id == payment_id).with_for_update()
            ).one()
            confirmation_attempt.outcome = "provider_unknown"
            confirmation_attempt.error_code = "confirmation_timeout_unknown"
            payment.payment_status = "unknown"
            payment.updated_at = timeout_now
            db.add(confirmation_attempt)
            db.add(payment)
            enqueue_payment_reconcile_job(
                db,
                payment.id,
                reason=f"confirmation_{confirmation_attempt.id}",
            )
            if (
                booking is not None
                and booking.expires_at is not None
                and booking.expires_at <= timeout_now
            ):
                db_game = db.get(Game, booking.game_id)
                if db_game is not None:
                    expire_stale_pending_checkouts(
                        db,
                        db_game,
                        timeout_now,
                        enqueue_reconciliation=False,
                    )
            db.commit()
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Stripe could not confirm this saved payment method.",
            ) from exc

        stripe_status = payment_intent.status

    try:
        from backend.services.stripe_webhook_service import (
            apply_authoritative_payment_intent_observation,
            lock_booking_payment_domain_by_booking_id,
        )

        observation_now = get_database_now(db)
        booking = lock_booking_payment_domain_by_booking_id(db, booking_id)
        if booking is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Checkout state changed before payment status could be saved.",
            )
        payment = db.scalars(
            select(Payment).where(Payment.id == payment_id).with_for_update()
        ).one()
        payment.provider_charge_id = payment_intent.latest_charge_id
        payment.updated_at = observation_now
        db.add(payment)
        if "confirmation_attempt" in locals():
            confirmation_attempt = db.scalars(
                select(PaymentConfirmationAttempt)
                .where(PaymentConfirmationAttempt.id == confirmation_attempt.id)
                .with_for_update()
            ).one()
            confirmation_attempt.outcome = {
                "succeeded": "succeeded",
                "requires_payment_method": "failed",
                "canceled": "failed",
                "unknown": "provider_unknown",
            }.get(stripe_status, "pending")
            confirmation_attempt.error_code = (
                f"confirmation_{stripe_status}"
                if confirmation_attempt.outcome == "failed"
                else None
            )
            confirmation_attempt.updated_at = observation_now
            if confirmation_attempt.outcome in {"succeeded", "failed"}:
                confirmation_attempt.resolved_at = observation_now
            db.add(confirmation_attempt)
            enqueue_payment_reconcile_job(
                db,
                payment.id,
                reason=f"confirmation_{confirmation_attempt.id}",
            )
        else:
            enqueue_payment_reconcile_job(
                db,
                payment.id,
                reason="checkout_status_refresh",
            )
        apply_authoritative_payment_intent_observation(
            db,
            payment=payment,
            observation=payment_intent,
            source="checkout_confirmation",
            now=observation_now,
        )
        db.commit()
        db.refresh(payment)
        db.refresh(booking)
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=CHECKOUT_PROVIDER_STATUS_RECORDING_FAILED_DETAIL,
        ) from exc
    return build_checkout_response(
        db,
        booking,
        payment,
        payment_intent.client_secret,
        stripe_status=stripe_status,
    )


def resume_serialized_pending_checkout(
    db: Session,
    game_id: uuid.UUID,
    checkout_request: GameCheckoutPaymentIntentCreate,
    current_user: User,
    *,
    return_url: str | None,
    party_size: int,
    subtotal_cents: int,
    provider_verified_payment_method_id: uuid.UUID | None = None,
) -> GameCheckoutPaymentIntentRead | None:
    db_game = get_locked_active_game_or_404(db, game_id)
    now = get_database_now(db)
    require_checkout_game_open(db_game, current_user, now)
    expire_stale_pending_checkouts(db, db_game, now)
    return resume_pending_checkout_with_locked_game(
        db,
        db_game,
        checkout_request,
        current_user,
        return_url=return_url,
        party_size=party_size,
        subtotal_cents=subtotal_cents,
        now=now,
        provider_verified_payment_method_id=provider_verified_payment_method_id,
    )


def create_game_checkout_payment_intent_workflow(
    db: Session,
    game_id: uuid.UUID,
    checkout_request: GameCheckoutPaymentIntentCreate,
    current_user: User,
    *,
    provider_verified_payment_method_id: uuid.UUID | None = None,
) -> GameCheckoutPaymentIntentRead:
    checkpoint_committed = False
    return_url = validate_checkout_return_url(
        checkout_request.return_url,
        game_id=game_id,
    )
    db_game = get_locked_active_game_or_404(db, game_id)
    now = get_database_now(db)
    require_checkout_game_open(db_game, current_user, now)
    require_stripe_payments_enabled()

    if db_game.currency != "USD":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game currency is not supported by checkout.",
        )

    guest_count = validate_guest_count(db_game, checkout_request.guest_count)
    party_size = guest_count + 1
    subtotal_cents = db_game.price_per_player_cents * party_size
    platform_fee_cents = 0
    checkout_total_cents = subtotal_cents + platform_fee_cents

    expire_stale_pending_checkouts(db, db_game, now)

    resumed_checkout = resume_pending_checkout_with_locked_game(
        db,
        db_game,
        checkout_request,
        current_user,
        return_url=return_url,
        party_size=party_size,
        subtotal_cents=subtotal_cents,
        now=now,
        provider_verified_payment_method_id=provider_verified_payment_method_id,
    )
    if resumed_checkout is not None:
        return resumed_checkout

    now = get_database_now(db)
    require_checkout_game_open(db_game, current_user, now)
    expire_stale_pending_checkouts(db, db_game, now)

    if get_existing_active_participant(db, db_game.id, current_user.id) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already joined this game.",
        )

    if get_existing_active_waitlist_entry(db, db_game.id, current_user.id) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You are already on the waitlist for this game.",
        )

    roster_count = count_roster_players(db, db_game.id, now=now)
    spots_left = max(db_game.total_spots - roster_count, 0)
    if party_size > spots_left:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not enough spots are available for checkout.",
        )

    credit_application = calculate_user_game_credit_application(
        db,
        current_user.id,
        total_amount_cents=checkout_total_cents,
        now=now,
        minimum_stripe_charge_cents=MINIMUM_USD_PAYMENT_INTENT_AMOUNT_CENTS,
    )
    if (
        credit_application.payment_required
        and credit_application.stripe_amount_cents
        < MINIMUM_USD_PAYMENT_INTENT_AMOUNT_CENTS
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stripe checkout requires a total of at least 50 cents.",
        )

    saved_payment_method = None
    if credit_application.payment_required:
        try:
            currency = get_stripe_currency()
        except StripeConfigError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc

        if db_game.currency != currency:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Game currency is not supported by Stripe checkout.",
            )

        if provider_verified_payment_method_id != checkout_request.payment_method_id:
            db.rollback()
            verified_payment_method_id = require_provider_verified_checkout_payment_method(
                db,
                checkout_request.payment_method_id,
                current_user,
                now=now,
            )
            return create_game_checkout_payment_intent_workflow(
                db,
                game_id,
                checkout_request,
                current_user,
                provider_verified_payment_method_id=verified_payment_method_id,
            )

        saved_payment_method = get_current_user_saved_payment_method_for_checkout(
            db,
            checkout_request.payment_method_id,
            current_user,
            now=now,
            verify_provider=False,
        )
        if saved_payment_method is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Choose a saved card before checkout.",
            )

    discount_cents = (
        credit_application.credit_applied_cents
        + credit_application.minimum_charge_adjustment_cents
    )
    booking, payment, participants = build_pending_checkout_rows(
        db_game,
        current_user,
        guest_count=guest_count,
        party_size=party_size,
        subtotal_cents=subtotal_cents,
        platform_fee_cents=platform_fee_cents,
        discount_cents=discount_cents,
        total_cents=credit_application.final_amount_due_cents,
        now=now,
        payment_required=credit_application.payment_required,
        credit_application=credit_application,
    )
    try:
        db.add(booking)
        if payment is not None:
            db.add(payment)
        db.add_all(participants)
        db.add(db_game)
        db.flush()

        if credit_application.credit_applied_cents > 0:
            reserve_game_credits(
                db,
                current_user.id,
                amount_cents=credit_application.credit_applied_cents,
                booking_id=booking.id,
                game_id=db_game.id,
                payment_id=payment.id if payment is not None else None,
                now=now,
                idempotency_scope=f"checkout:{booking.id}",
            )

        if not credit_application.payment_required:
            if credit_application.credit_applied_cents > 0:
                redeem_reserved_game_credits(
                    db,
                    booking.id,
                    now=now,
                    user_id=current_user.id,
                )
            confirm_credit_covered_checkout(
                db,
                db_game,
                booking,
                participants,
                now=now,
            )
            db.commit()
            db.refresh(booking)
            return build_checkout_response(
                db,
                booking,
                None,
                None,
                credit_application=credit_application,
            )

        if payment is None or saved_payment_method is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Checkout payment state could not be prepared.",
            )

        payment_id = payment.id
        booking_id = booking.id
        payment_amount_cents = payment.amount_cents
        payment_currency = payment.currency
        payment_idempotency_key = payment.idempotency_key
        current_user_id = current_user.id
        locked_game_id = db_game.id
        customer_id = current_user.stripe_customer_id
        db.commit()
        checkpoint_committed = True

        payment_intent = create_payment_intent(
            amount_cents=payment_amount_cents,
            currency=payment_currency,
            idempotency_key=payment_idempotency_key,
            metadata={
                "user_id": str(current_user_id),
                "game_id": str(locked_game_id),
                "booking_id": str(booking_id),
                "payment_id": str(payment_id),
                "checkout_total_cents": str(checkout_total_cents),
                "credit_applied_cents": str(
                    credit_application.credit_applied_cents
                ),
                "minimum_charge_adjustment_cents": str(
                    credit_application.minimum_charge_adjustment_cents
                ),
                "stripe_amount_cents": str(credit_application.stripe_amount_cents),
            },
            customer_id=customer_id,
        )
        stripe_status = payment_intent.status

        try:
            from backend.services.stripe_webhook_service import (
                apply_authoritative_payment_intent_observation,
                lock_booking_payment_domain_by_booking_id,
            )

            booking = lock_booking_payment_domain_by_booking_id(db, booking_id)
            if booking is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Checkout state changed before payment result could be saved."
                    ),
                )
            payment = db.scalars(
                select(Payment).where(Payment.id == payment_id).with_for_update()
            ).one()
            payment.provider_payment_intent_id = payment_intent.id
            payment.provider_charge_id = payment_intent.latest_charge_id
            payment.updated_at = datetime.now(timezone.utc)
            db.add(payment)
            db.flush()
            enqueue_payment_reconcile_job(
                db,
                payment.id,
                reason="payment_intent_creation",
            )
            observation_now = get_database_now(db)
            apply_authoritative_payment_intent_observation(
                db,
                payment=payment,
                observation=payment_intent,
                source="checkout_creation",
                now=observation_now,
            )
            db.commit()
            db.refresh(payment)
            db.refresh(booking)
        except Exception as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=CHECKOUT_PROVIDER_RESULT_RECORDING_FAILED_DETAIL,
            ) from exc

        if booking.booking_status != "pending_payment":
            return build_checkout_response(
                db,
                booking,
                payment,
                payment_intent.client_secret,
                credit_application=credit_application,
                stripe_status=stripe_status,
            )

        resumed_checkout = resume_serialized_pending_checkout(
            db,
            game_id,
            checkout_request,
            current_user,
            return_url=return_url,
            party_size=party_size,
            subtotal_cents=subtotal_cents,
            provider_verified_payment_method_id=checkout_request.payment_method_id,
        )
        if resumed_checkout is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Checkout payment state could not be resumed.",
            )
        return resumed_checkout
    except StripeConfigError as exc:
        if not checkpoint_committed:
            db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_game_conflict_detail(exc),
        ) from exc
    except (
        GameCreditInsufficientBalanceError,
        GameCreditReservationConflictError,
    ) as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except PublicTimeoutError:
        if checkpoint_committed and "payment_id" in locals():
            db.rollback()
            payment = db.get(Payment, payment_id)
            if payment is not None:
                payment.payment_status = "unknown"
                payment.updated_at = datetime.now(timezone.utc)
                db.add(payment)
                enqueue_payment_reconcile_job(
                    db,
                    payment.id,
                    reason="payment_intent_creation",
                )
                db.commit()
        else:
            db.rollback()
        raise
    except HTTPException:
        if not checkpoint_committed:
            db.rollback()
        raise
    except Exception as exc:
        if not checkpoint_committed:
            db.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Stripe could not create this payment intent.",
        ) from exc

    return build_checkout_response(
        db,
        booking,
        payment,
        payment_intent.client_secret,
        credit_application=credit_application,
        stripe_status=stripe_status,
    )


def get_game_checkout_status_workflow(
    db: Session,
    booking_id: uuid.UUID,
    current_user: User,
) -> GameCheckoutStatusRead:
    booking = db.get(Booking, booking_id)
    if booking is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found.",
        )

    if booking.buyer_user_id != current_user.id and not user_is_active_admin(
        current_user
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot view this checkout status.",
        )

    if (
        booking.booking_status == "pending_payment"
        and booking.expires_at is not None
    ):
        now = get_database_now(db)
        if booking.expires_at <= now:
            db_game = get_locked_active_game_or_404(db, booking.game_id)
            expire_stale_pending_checkouts(db, db_game, now)
            db.commit()
            booking = db.get(Booking, booking_id)
            if booking is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Booking not found.",
                )

    payment = db.scalars(
        select(Payment)
        .where(Payment.booking_id == booking.id, Payment.payment_type == "booking")
        .order_by(Payment.created_at.desc())
        .limit(1)
    ).first()
    credit_application = get_credit_application_for_booking(
        db,
        booking,
        credit_owner_user_id=booking.buyer_user_id,
        now=datetime.now(timezone.utc),
    )
    compensation = db.scalars(
        select(PaymentCompensation)
        .where(
            PaymentCompensation.booking_id == booking.id,
            PaymentCompensation.status.in_({"required", "processing"}),
        )
        .order_by(PaymentCompensation.created_at.desc())
        .limit(1)
    ).first()

    return GameCheckoutStatusRead(
        booking_id=booking.id,
        booking_status=booking.booking_status,
        booking_payment_status=booking.payment_status,
        reservation_status=booking.reservation_status,
        payment_id=payment.id if payment is not None else None,
        payment_status=payment.payment_status if payment is not None else None,
        provider_status=payment.provider_status if payment is not None else None,
        compensation_status=compensation.status if compensation is not None else None,
        amount_cents=credit_application.stripe_amount_cents,
        currency=booking.currency,
        subtotal_cents=booking.subtotal_cents,
        platform_fee_cents=booking.platform_fee_cents,
        checkout_total_cents=booking.subtotal_cents + booking.platform_fee_cents,
        available_credit_cents=credit_application.available_credit_cents,
        credit_applied_cents=credit_application.credit_applied_cents,
        minimum_charge_adjustment_cents=(
            credit_application.minimum_charge_adjustment_cents
        ),
        final_amount_due_cents=credit_application.final_amount_due_cents,
        stripe_amount_cents=credit_application.stripe_amount_cents,
        payment_required=credit_application.payment_required,
    )
