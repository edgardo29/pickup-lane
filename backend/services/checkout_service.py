"""Official game checkout orchestration and payment state helpers."""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import Booking, Game, GameParticipant, Payment, User
from backend.schemas.checkout_schema import (
    GameCheckoutPaymentIntentCreate,
    GameCheckoutPaymentIntentRead,
    GameCheckoutStatusRead,
)
from backend.services.admin_permission_service import (
    PERMISSION_MONEY_READ,
    user_has_admin_permission,
)
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
)
from backend.services.user_service import get_user_display_name

CHECKOUT_HOLD_MINUTES = 15
MINIMUM_USD_PAYMENT_INTENT_AMOUNT_CENTS = 50


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

    if (
        db_game.publish_status != "published"
        or db_game.game_status not in JOINABLE_GAME_STATUSES
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This game is not open for checkout.",
        )

    require_roster_window_open(db_game, now, "Checkout is closed for this game.")


def expire_stale_pending_checkouts(db: Session, db_game: Game, now: datetime) -> None:
    stale_bookings = db.scalars(
        select(Booking).where(
            Booking.game_id == db_game.id,
            Booking.booking_status == "pending_payment",
            Booking.expires_at.is_not(None),
            Booking.expires_at <= now,
        )
    ).all()

    if not stale_bookings:
        return

    stale_booking_ids = [booking.id for booking in stale_bookings]
    stale_participants = db.scalars(
        select(GameParticipant).where(
            GameParticipant.booking_id.in_(stale_booking_ids),
            GameParticipant.participant_status == "pending_payment",
        )
    ).all()
    stale_payments = db.scalars(
        select(Payment).where(
            Payment.booking_id.in_(stale_booking_ids),
            Payment.payment_status.in_(PENDING_PAYMENT_STATUSES),
        )
    ).all()

    for booking in stale_bookings:
        release_reserved_game_credits(
            db,
            booking.id,
            now=now,
            release_reason="checkout_hold_expired",
            user_id=booking.buyer_user_id,
        )
        booking.booking_status = "expired"
        booking.payment_status = "failed"
        booking.updated_at = now
        db.add(booking)

    for participant in stale_participants:
        participant.participant_status = "cancelled"
        participant.cancellation_type = "payment_failed"
        participant.cancelled_at = now
        participant.updated_at = now
        db.add(participant)

    for payment in stale_payments:
        payment.payment_status = "canceled"
        payment.failure_code = "checkout_hold_expired"
        payment.failure_message = "Checkout hold expired before payment confirmation."
        payment.failure_reason = "checkout_hold_expired"
        payment.updated_at = now
        db.add(payment)

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
            Booking.payment_status == "processing",
            Booking.participant_count == party_size,
            Booking.subtotal_cents == subtotal_cents,
            Booking.expires_at.is_not(None),
            Booking.expires_at > now,
            Payment.payment_type == "booking",
            Payment.payment_status.in_(PENDING_PAYMENT_STATUSES),
            Payment.provider_payment_intent_id.is_not(None),
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
            amount_cents=credit_application.stripe_amount_cents,
            currency=booking.currency,
            payment_status="requires_payment_method",
            paid_at=None,
            failure_code=None,
            failure_message=None,
            failure_reason=None,
            payment_metadata={
                "source": "game_checkout",
                "game_id": str(db_game.id),
                "user_id": str(current_user.id),
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
    checkout_total_cents = booking.subtotal_cents + booking.platform_fee_cents
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
    if payment is not None and not client_secret:
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
        payment_status=payment.payment_status if payment is not None else None,
    )


def keep_payment_pending_until_webhook(stripe_status: str) -> str:
    internal_status = map_payment_intent_status(stripe_status)
    if internal_status == "succeeded":
        return "processing"

    return internal_status


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


def create_game_checkout_payment_intent_workflow(
    db: Session,
    game_id: uuid.UUID,
    checkout_request: GameCheckoutPaymentIntentCreate,
    current_user: User,
) -> GameCheckoutPaymentIntentRead:
    now = datetime.now(timezone.utc)
    db_game = get_locked_active_game_or_404(db, game_id)
    require_checkout_game_open(db_game, current_user, now)

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

    reusable_checkout = get_reusable_pending_checkout(
        db,
        db_game,
        current_user,
        party_size=party_size,
        subtotal_cents=subtotal_cents,
        now=now,
    )
    if reusable_checkout is not None:
        booking, payment = reusable_checkout
        saved_payment_method = None
        if payment.payment_status == "requires_payment_method":
            saved_payment_method = get_current_user_saved_payment_method_for_checkout(
                db,
                checkout_request.payment_method_id,
                current_user,
                now=now,
            )
            if saved_payment_method is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Choose a saved card before checkout.",
                )

        try:
            payment_intent = retrieve_payment_intent(payment.provider_payment_intent_id)
        except StripeConfigError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Stripe could not retrieve this payment intent.",
            ) from exc

        stripe_status = payment_intent.status
        payment_status = map_payment_intent_status(stripe_status)
        if payment_status in PENDING_PAYMENT_STATUSES or stripe_status == "succeeded":
            if stripe_status == "requires_payment_method":
                if saved_payment_method is None:
                    saved_payment_method = (
                        get_current_user_saved_payment_method_for_checkout(
                            db,
                            checkout_request.payment_method_id,
                            current_user,
                            now=now,
                        )
                    )
                    if saved_payment_method is None:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Choose a saved card before checkout.",
                        )
                try:
                    payment_intent = confirm_payment_intent(
                        payment.provider_payment_intent_id,
                        payment_method_id=(
                            saved_payment_method.stripe_payment_method_id
                        ),
                        return_url=checkout_request.return_url,
                    )
                except StripeConfigError as exc:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail=str(exc),
                    ) from exc
                except Exception as exc:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail="Stripe could not confirm this saved payment method.",
                    ) from exc

                stripe_status = payment_intent.status

            payment_status = keep_payment_pending_until_webhook(stripe_status)

            payment.payment_status = payment_status
            payment.provider_charge_id = payment_intent.latest_charge_id
            payment.updated_at = now
            db.add(payment)
            db.commit()
            db.refresh(payment)
            db.refresh(booking)
            return build_checkout_response(
                db,
                booking,
                payment,
                payment_intent.client_secret,
                stripe_status=stripe_status,
            )

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

    roster_count = count_roster_players(db, db_game.id)
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

        saved_payment_method = get_current_user_saved_payment_method_for_checkout(
            db,
            checkout_request.payment_method_id,
            current_user,
            now=now,
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
    if roster_count + party_size >= db_game.total_spots:
        db_game.game_status = "full"
        db_game.updated_at = now

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

        payment_intent = create_payment_intent(
            amount_cents=payment.amount_cents,
            currency=payment.currency,
            idempotency_key=payment.idempotency_key,
            metadata={
                "user_id": str(current_user.id),
                "game_id": str(db_game.id),
                "booking_id": str(booking.id),
                "payment_id": str(payment.id),
                "checkout_total_cents": str(checkout_total_cents),
                "credit_applied_cents": str(
                    credit_application.credit_applied_cents
                ),
                "minimum_charge_adjustment_cents": str(
                    credit_application.minimum_charge_adjustment_cents
                ),
                "stripe_amount_cents": str(credit_application.stripe_amount_cents),
            },
            customer_id=current_user.stripe_customer_id,
        )
        stripe_status = payment_intent.status
        if saved_payment_method is not None:
            payment_intent = confirm_payment_intent(
                payment_intent.id,
                payment_method_id=saved_payment_method.stripe_payment_method_id,
                return_url=checkout_request.return_url,
            )
            stripe_status = payment_intent.status

        payment.provider_payment_intent_id = payment_intent.id
        payment.provider_charge_id = payment_intent.latest_charge_id
        payment.payment_status = keep_payment_pending_until_webhook(stripe_status)
        payment.updated_at = now
        db.add(payment)
        db.commit()
        db.refresh(booking)
        db.refresh(payment)
    except StripeConfigError as exc:
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
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
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

    if booking.buyer_user_id != current_user.id and not user_has_admin_permission(
        current_user,
        PERMISSION_MONEY_READ,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot view this checkout status.",
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

    return GameCheckoutStatusRead(
        booking_id=booking.id,
        booking_status=booking.booking_status,
        booking_payment_status=booking.payment_status,
        payment_id=payment.id if payment is not None else None,
        payment_status=payment.payment_status if payment is not None else None,
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
