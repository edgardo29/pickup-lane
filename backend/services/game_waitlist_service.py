"""Waitlist workflow orchestration for game joins and promotion."""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models import (
    Booking,
    Game,
    GameParticipant,
    Payment,
    PaymentConfirmationAttempt,
    User,
    UserPaymentMethod,
    WaitlistEntry,
)
from backend.observability.timeouts import (
    DependencyMutationTimeoutUnknownError,
    PublicTimeoutError,
)
from backend.schemas.game_schema import GameJoinCreate
from backend.services.game_credit_service import release_reserved_game_credits
from backend.services.game_notification_service import (
    create_waitlist_payment_failed_notification,
    create_waitlist_promotion_notification,
)
from backend.services.game_rules import (
    AUTO_CHARGE_CONSENT_VERSION_MAX_LENGTH,
    WAITLIST_PROMOTION_CANDIDATE_STATUSES,
    game_requires_app_player_payment,
    is_roster_locked,
)
from backend.services.game_service import (
    count_roster_players,
    get_existing_active_participant,
    get_locked_game_or_404,
    get_next_roster_order,
    get_next_waitlist_position,
    sync_game_capacity_status,
)
from backend.services.payment_job_service import enqueue_payment_reconcile_job
from backend.services.payment_lifecycle_policy import canonical_fingerprint
from backend.services.payment_method_service import (
    apply_provider_verified_saved_payment_method,
    is_saved_payment_method_expired,
)
from backend.services.stripe_service import (
    StripeConfigError,
    confirm_payment_intent,
    create_payment_intent,
    map_payment_intent_status,
    retrieve_payment_method,
)

PAYMENT_PROCESSING_HOLD_MINUTES = 2
WAITLIST_AUTO_PROMOTION_CHECKPOINT_FAILED_DETAIL = (
    "Waitlist promotion payment checkpoint could not be saved. Please try again."
)
WAITLIST_AUTO_PROMOTION_PROVIDER_RESULT_RECORDING_FAILED_DETAIL = (
    "Stripe created or updated this waitlist payment, but Pickup Lane could not "
    "save the matching local promotion state. Support must verify the payment "
    "before retrying."
)
WAITLIST_AUTO_PROMOTION_STATE_MISSING_DETAIL = (
    "Waitlist promotion state changed before the payment result could be recorded."
)


def commit_paid_waitlist_auto_promotion_state(db: Session, *, detail: str) -> None:
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        ) from exc


def get_database_now(db: Session) -> datetime:
    if not isinstance(db, Session):
        return datetime.now(timezone.utc)
    database_now = db.scalar(select(func.now()))
    if not isinstance(database_now, datetime):
        raise RuntimeError(  # noqa: TRY004
            "PostgreSQL did not return the current database time"
        )
    return database_now


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
    provider_customer_id: str,
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
        creation_fingerprint=canonical_fingerprint(
            {
                "payment_id": str(payment_id),
                "booking_id": str(booking.id),
                "payer_user_id": str(booking.buyer_user_id),
                "provider_customer_id": provider_customer_id,
                "amount_cents": booking.total_cents,
                "currency": booking.currency,
                "game_id": str(db_game.id),
                "participant_count": booking.participant_count,
                "waitlist_entry_id": str(waitlist_entry.id),
            }
        ),
        amount_cents=booking.total_cents,
        currency=booking.currency,
        provider_customer_id=provider_customer_id,
        payment_status="requires_payment_method",
        paid_at=None,
        failure_code=None,
        failure_message=None,
        payment_metadata={
            "source": "waitlist_auto_promote",
            "game_id": str(db_game.id),
            "booking_id": str(booking.id),
            "payment_id": str(payment_id),
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
    hold_expires_at = now + timedelta(minutes=PAYMENT_PROCESSING_HOLD_MINUTES)

    waitlist_entry.waitlist_status = "payment_processing"
    waitlist_entry.promoted_booking_id = booking.id
    waitlist_entry.promoted_at = waitlist_entry.promoted_at or now
    waitlist_entry.promotion_expires_at = hold_expires_at
    waitlist_entry.updated_at = now
    db.add(waitlist_entry)

    booking.booking_status = "pending_payment"
    booking.payment_status = "processing"
    booking.reservation_status = "held"
    booking.expires_at = hold_expires_at
    booking.updated_at = now
    db.add(booking)

    for booking_participant in booking_participants:
        booking_participant.participant_status = "pending_payment"
        booking_participant.attendance_status = "not_applicable"
        booking_participant.roster_order = None
        booking_participant.updated_at = now
        db.add(booking_participant)


def get_locked_paid_waitlist_auto_promotion_state(
    db: Session,
    *,
    game_id: uuid.UUID,
    waitlist_entry_id: uuid.UUID,
    booking_id: uuid.UUID,
    payment_id: uuid.UUID,
) -> tuple[Game, WaitlistEntry, Booking, list[GameParticipant], Payment]:
    db_game = get_locked_game_or_404(db, game_id)
    booking = db.scalar(
        select(Booking)
        .where(
            Booking.id == booking_id,
            Booking.game_id == game_id,
        )
        .with_for_update()
    )
    waitlist_entry = db.scalar(
        select(WaitlistEntry)
        .where(
            WaitlistEntry.id == waitlist_entry_id,
            WaitlistEntry.game_id == game_id,
        )
        .with_for_update()
    )
    booking_participants = list(
        db.scalars(
            select(GameParticipant)
            .where(
                GameParticipant.game_id == game_id,
                GameParticipant.booking_id == booking_id,
            )
            .order_by(GameParticipant.id.asc())
            .with_for_update()
        ).all()
    )
    payment = db.scalar(
        select(Payment)
        .where(
            Payment.id == payment_id,
            Payment.booking_id == booking_id,
        )
        .with_for_update()
    )

    if (
        booking is None
        or waitlist_entry is None
        or not booking_participants
        or payment is None
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=WAITLIST_AUTO_PROMOTION_STATE_MISSING_DETAIL,
        )

    return db_game, waitlist_entry, booking, booking_participants, payment


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
    release_reserved_game_credits(
        db,
        booking.id,
        now=now,
        reason_code=failure_code,
        user_id=booking.buyer_user_id,
    )

    if payment is not None:
        payment.payment_status = payment_status or "failed"
        payment.provider_status = (
            payment_status if payment_status not in {None, "failed", "unknown"} else None
        )
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
    booking.reservation_status = "released"
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


def paid_waitlist_prerequisites_missing(
    waitlist_entry: WaitlistEntry,
    booking: Booking,
) -> bool:
    return (
        waitlist_entry.auto_charge_consent_at is None
        or not waitlist_entry.auto_charge_consent_version
        or waitlist_entry.authorized_payment_method_id is None
        or not waitlist_entry.authorized_stripe_payment_method_id
        or waitlist_entry.authorized_amount_cents is None
        or waitlist_entry.authorized_amount_cents < booking.total_cents
    )


def fail_paid_waitlist_auto_promotion_after_checkpoint(
    db: Session,
    *,
    game_id: uuid.UUID,
    waitlist_entry_id: uuid.UUID,
    booking_id: uuid.UUID,
    payment_id: uuid.UUID,
    now: datetime,
    failure_code: str,
    failure_message: str,
) -> tuple[str, int]:
    (
        db_game,
        waitlist_entry,
        booking,
        booking_participants,
        payment,
    ) = get_locked_paid_waitlist_auto_promotion_state(
        db,
        game_id=game_id,
        waitlist_entry_id=waitlist_entry_id,
        booking_id=booking_id,
        payment_id=payment_id,
    )
    mark_paid_waitlist_auto_promotion_failed(
        db,
        db_game,
        waitlist_entry,
        booking,
        booking_participants,
        payment,
        now,
        payment_status="failed",
        failure_code=failure_code,
        failure_message=failure_message,
    )
    commit_paid_waitlist_auto_promotion_state(
        db,
        detail=WAITLIST_AUTO_PROMOTION_PROVIDER_RESULT_RECORDING_FAILED_DETAIL,
    )
    return "failed", 0


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

    buyer_user = db.get(User, booking.buyer_user_id)
    if buyer_user is None or not buyer_user.stripe_customer_id:
        mark_paid_waitlist_auto_promotion_failed(
            db,
            db_game,
            waitlist_entry,
            booking,
            booking_participants,
            None,
            now,
            payment_status=None,
            failure_code="waitlist_auto_charge_customer_missing",
            failure_message="Waitlist auto-charge customer identity was missing.",
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
        buyer_user.stripe_customer_id,
        now,
    )
    db.add(payment)
    db.flush()
    held_spots = len(booking_participants)
    buyer_user_id = booking.buyer_user_id
    booking_id = booking.id
    game_id = db_game.id
    payment_id = payment.id
    payment_amount_cents = payment.amount_cents
    payment_currency = payment.currency
    payment_idempotency_key = payment.idempotency_key
    waitlist_entry_id = waitlist_entry.id
    authorized_amount_cents = waitlist_entry.authorized_amount_cents
    authorized_payment_method_local_id = waitlist_entry.authorized_payment_method_id
    authorized_provider_payment_method_id = (
        waitlist_entry.authorized_stripe_payment_method_id
    )
    commit_paid_waitlist_auto_promotion_state(
        db,
        detail=WAITLIST_AUTO_PROMOTION_CHECKPOINT_FAILED_DETAIL,
    )

    try:
        stripe_payment_method = retrieve_payment_method(
            authorized_provider_payment_method_id
        )
    except StripeConfigError as exc:
        failure_now = get_database_now(db)
        return fail_paid_waitlist_auto_promotion_after_checkpoint(
            db,
            game_id=game_id,
            waitlist_entry_id=waitlist_entry_id,
            booking_id=booking_id,
            payment_id=payment_id,
            now=failure_now,
            failure_code="waitlist_auto_charge_payment_method_config_error",
            failure_message=str(exc),
        )
    except PublicTimeoutError:
        failure_now = get_database_now(db)
        return fail_paid_waitlist_auto_promotion_after_checkpoint(
            db,
            game_id=game_id,
            waitlist_entry_id=waitlist_entry_id,
            booking_id=booking_id,
            payment_id=payment_id,
            now=failure_now,
            failure_code="waitlist_auto_charge_payment_method_verification_timeout",
            failure_message="Saved card could not be verified before auto-charge.",
        )
    except Exception:  # noqa: BLE001 - verification failure definitively fails promotion
        failure_now = get_database_now(db)
        return fail_paid_waitlist_auto_promotion_after_checkpoint(
            db,
            game_id=game_id,
            waitlist_entry_id=waitlist_entry_id,
            booking_id=booking_id,
            payment_id=payment_id,
            now=failure_now,
            failure_code="waitlist_auto_charge_payment_method_verification_failed",
            failure_message="Saved card could not be verified before auto-charge.",
        )

    (
        db_game,
        waitlist_entry,
        booking,
        booking_participants,
        payment,
    ) = get_locked_paid_waitlist_auto_promotion_state(
        db,
        game_id=game_id,
        waitlist_entry_id=waitlist_entry_id,
        booking_id=booking_id,
        payment_id=payment_id,
    )
    buyer_user = db.get(User, buyer_user_id)
    authorized_payment_method = db.scalar(
        select(UserPaymentMethod)
        .where(UserPaymentMethod.id == authorized_payment_method_local_id)
        .with_for_update()
    )
    if (
        buyer_user is None
        or not buyer_user.stripe_customer_id
        or authorized_payment_method is None
        or authorized_payment_method.user_id != buyer_user.id
        or authorized_payment_method.method_status != "active"
        or authorized_payment_method.stripe_customer_id != buyer_user.stripe_customer_id
        or authorized_payment_method.stripe_payment_method_id
        != authorized_provider_payment_method_id
    ):
        mark_paid_waitlist_auto_promotion_failed(
            db,
            db_game,
            waitlist_entry,
            booking,
            booking_participants,
            payment,
            now,
            payment_status="failed",
            failure_code="waitlist_auto_charge_payment_method_stale",
            failure_message="Saved card authorization is no longer valid.",
        )
        commit_paid_waitlist_auto_promotion_state(
            db,
            detail=WAITLIST_AUTO_PROMOTION_PROVIDER_RESULT_RECORDING_FAILED_DETAIL,
        )
        return "failed", 0

    try:
        apply_provider_verified_saved_payment_method(
            db,
            authorized_payment_method,
            buyer_user,
            stripe_payment_method,
            now,
        )
    except HTTPException as exc:
        mark_paid_waitlist_auto_promotion_failed(
            db,
            db_game,
            waitlist_entry,
            booking,
            booking_participants,
            payment,
            now,
            payment_status="failed",
            failure_code="waitlist_auto_charge_payment_method_stale",
            failure_message=str(exc.detail),
        )
        commit_paid_waitlist_auto_promotion_state(
            db,
            detail=WAITLIST_AUTO_PROMOTION_PROVIDER_RESULT_RECORDING_FAILED_DETAIL,
        )
        return "failed", 0

    waitlist_entry.authorized_payment_method_brand = (
        authorized_payment_method.card_brand
    )
    waitlist_entry.authorized_payment_method_last4 = (
        authorized_payment_method.card_last4
    )
    waitlist_entry.updated_at = now
    db.add(waitlist_entry)
    commit_paid_waitlist_auto_promotion_state(
        db,
        detail=WAITLIST_AUTO_PROMOTION_PROVIDER_RESULT_RECORDING_FAILED_DETAIL,
    )

    authorized_payment_method_id = stripe_payment_method.id

    try:
        payment_intent = create_payment_intent(
            amount_cents=payment_amount_cents,
            currency=payment_currency,
            idempotency_key=payment_idempotency_key,
            metadata={
                "source": "waitlist_auto_promote",
                "user_id": str(buyer_user_id),
                "game_id": str(game_id),
                "booking_id": str(booking_id),
                "payment_id": str(payment_id),
                "waitlist_entry_id": str(waitlist_entry_id),
                "authorized_amount_cents": str(authorized_amount_cents),
            },
            customer_id=buyer_user.stripe_customer_id,
        )
        create_now = get_database_now(db)
        (
            db_game,
            waitlist_entry,
            booking,
            booking_participants,
            payment,
        ) = get_locked_paid_waitlist_auto_promotion_state(
            db,
            game_id=game_id,
            waitlist_entry_id=waitlist_entry_id,
            booking_id=booking_id,
            payment_id=payment_id,
        )
        payment.provider_payment_intent_id = payment_intent.id
        payment.provider_status = payment_intent.status
        payment.payment_status = map_payment_intent_status(payment_intent.status)
        payment.updated_at = create_now
        db.add(payment)
        enqueue_payment_reconcile_job(
            db,
            payment.id,
            reason="waitlist_payment_intent_creation",
        )
        if booking.expires_at is not None and booking.expires_at <= create_now:
            from backend.services.checkout_service import expire_stale_pending_checkouts

            expire_stale_pending_checkouts(
                db,
                db_game,
                create_now,
                enqueue_reconciliation=False,
            )
            commit_paid_waitlist_auto_promotion_state(
                db,
                detail=WAITLIST_AUTO_PROMOTION_PROVIDER_RESULT_RECORDING_FAILED_DETAIL,
            )
            return "failed", 0
        commit_paid_waitlist_auto_promotion_state(
            db,
            detail=WAITLIST_AUTO_PROMOTION_PROVIDER_RESULT_RECORDING_FAILED_DETAIL,
        )

        confirmation_fingerprint = canonical_fingerprint(
            {
                "payment_id": str(payment_id),
                "booking_id": str(booking_id),
                "payer_user_id": str(buyer_user_id),
                "provider_customer_id": payment.provider_customer_id,
                "provider_payment_method_id": authorized_payment_method_id,
                "provider_payment_intent_id": payment_intent.id,
                "amount_cents": payment_amount_cents,
                "currency": payment_currency,
                "game_id": str(game_id),
                "participant_count": len(booking_participants),
            }
        )
        confirmation_attempt = PaymentConfirmationAttempt(
            id=uuid.uuid4(),
            payment_id=payment_id,
            booking_id=booking_id,
            user_id=buyer_user_id,
            provider_customer_id=payment.provider_customer_id,
            provider_payment_method_id=authorized_payment_method_id,
            confirmation_fingerprint=confirmation_fingerprint,
            confirmation_idempotency_key=(
                f"waitlist-confirm:{payment_id}:{confirmation_fingerprint}"
            ),
            outcome="pending",
        )
        db.add(confirmation_attempt)
        commit_paid_waitlist_auto_promotion_state(
            db,
            detail=WAITLIST_AUTO_PROMOTION_PROVIDER_RESULT_RECORDING_FAILED_DETAIL,
        )

        payment_intent = confirm_payment_intent(
            payment_intent.id,
            payment_method_id=authorized_payment_method_id,
            off_session=True,
            idempotency_key=confirmation_attempt.confirmation_idempotency_key,
        )
        observation_now = get_database_now(db)
        (
            db_game,
            waitlist_entry,
            booking,
            booking_participants,
            payment,
        ) = get_locked_paid_waitlist_auto_promotion_state(
            db,
            game_id=game_id,
            waitlist_entry_id=waitlist_entry_id,
            booking_id=booking_id,
            payment_id=payment_id,
        )
        payment.provider_payment_intent_id = payment_intent.id
        payment.provider_charge_id = payment_intent.latest_charge_id
        observed_payment_status = map_payment_intent_status(payment_intent.status)
        payment.updated_at = observation_now
        db.add(payment)
        confirmation_attempt = db.get(
            PaymentConfirmationAttempt, confirmation_attempt.id
        )
        confirmation_attempt.outcome = {
            "succeeded": "succeeded",
            "requires_action": "failed",
            "requires_payment_method": "failed",
            "canceled": "failed",
        }.get(observed_payment_status, "pending")
        confirmation_attempt.resolved_at = (
            observation_now
            if confirmation_attempt.outcome in {"succeeded", "failed"}
            else None
        )
        confirmation_attempt.error_code = (
            f"waitlist_confirmation_{observed_payment_status}"
            if confirmation_attempt.outcome == "failed"
            else None
        )
        confirmation_attempt.updated_at = observation_now
        db.add(confirmation_attempt)
        enqueue_payment_reconcile_job(
            db,
            payment.id,
            reason=f"waitlist_confirmation_{confirmation_attempt.id}",
        )
        if observed_payment_status in {
            "requires_action",
            "requires_payment_method",
        }:
            mark_paid_waitlist_auto_promotion_failed(
                db,
                db_game,
                waitlist_entry,
                booking,
                booking_participants,
                payment,
                observation_now,
                payment_status=observed_payment_status,
                failure_code=f"waitlist_auto_charge_{observed_payment_status}",
                failure_message=(
                    "Saved card auto-charge could not complete off-session."
                ),
            )
            commit_paid_waitlist_auto_promotion_state(
                db,
                detail=WAITLIST_AUTO_PROMOTION_PROVIDER_RESULT_RECORDING_FAILED_DETAIL,
            )
            return "failed", 0
    except HTTPException:
        raise
    except StripeConfigError as exc:
        failure_now = get_database_now(db)
        (
            db_game,
            waitlist_entry,
            booking,
            booking_participants,
            payment,
        ) = get_locked_paid_waitlist_auto_promotion_state(
            db,
            game_id=game_id,
            waitlist_entry_id=waitlist_entry_id,
            booking_id=booking_id,
            payment_id=payment_id,
        )
        mark_paid_waitlist_auto_promotion_failed(
            db,
            db_game,
            waitlist_entry,
            booking,
            booking_participants,
            payment,
            failure_now,
            payment_status="failed",
            failure_code="waitlist_auto_charge_stripe_config_error",
            failure_message=str(exc),
        )
        commit_paid_waitlist_auto_promotion_state(
            db,
            detail=WAITLIST_AUTO_PROMOTION_PROVIDER_RESULT_RECORDING_FAILED_DETAIL,
        )
        return "failed", 0
    except DependencyMutationTimeoutUnknownError:
        timeout_now = get_database_now(db)
        (
            db_game,
            waitlist_entry,
            booking,
            booking_participants,
            payment,
        ) = get_locked_paid_waitlist_auto_promotion_state(
            db,
            game_id=game_id,
            waitlist_entry_id=waitlist_entry_id,
            booking_id=booking_id,
            payment_id=payment_id,
        )
        payment.payment_status = "unknown"
        payment.failure_code = None
        payment.failure_message = None
        payment.updated_at = timeout_now
        db.add(payment)
        enqueue_payment_reconcile_job(
            db,
            payment.id,
            reason="waitlist_payment_intent_creation",
        )
        if booking.expires_at is not None and booking.expires_at <= timeout_now:
            from backend.services.checkout_service import expire_stale_pending_checkouts

            expire_stale_pending_checkouts(
                db,
                db_game,
                timeout_now,
                enqueue_reconciliation=False,
            )
            commit_paid_waitlist_auto_promotion_state(
                db,
                detail=WAITLIST_AUTO_PROMOTION_PROVIDER_RESULT_RECORDING_FAILED_DETAIL,
            )
            return "failed", 0
        commit_paid_waitlist_auto_promotion_state(
            db,
            detail=WAITLIST_AUTO_PROMOTION_PROVIDER_RESULT_RECORDING_FAILED_DETAIL,
        )
        return "processing", held_spots
    except Exception as exc:  # noqa: BLE001 - provider outcome is checkpointed below
        failure_now = get_database_now(db)
        (
            db_game,
            waitlist_entry,
            booking,
            booking_participants,
            payment,
        ) = get_locked_paid_waitlist_auto_promotion_state(
            db,
            game_id=game_id,
            waitlist_entry_id=waitlist_entry_id,
            booking_id=booking_id,
            payment_id=payment_id,
        )
        mark_paid_waitlist_auto_promotion_failed(
            db,
            db_game,
            waitlist_entry,
            booking,
            booking_participants,
            payment,
            failure_now,
            payment_status="failed",
            failure_code="waitlist_auto_charge_stripe_error",
            failure_message=str(exc) or "Stripe could not complete auto-charge.",
        )
        commit_paid_waitlist_auto_promotion_state(
            db,
            detail=WAITLIST_AUTO_PROMOTION_PROVIDER_RESULT_RECORDING_FAILED_DETAIL,
        )
        return "failed", 0

    from backend.services.stripe_webhook_service import (
        apply_authoritative_payment_intent_observation,
    )

    apply_authoritative_payment_intent_observation(
        db,
        payment=payment,
        observation=payment_intent,
        source="waitlist_confirmation",
        now=observation_now,
    )
    commit_paid_waitlist_auto_promotion_state(
        db,
        detail=WAITLIST_AUTO_PROMOTION_PROVIDER_RESULT_RECORDING_FAILED_DETAIL,
    )
    db.refresh(booking)
    if booking.booking_status == "confirmed":
        return "succeeded", held_spots
    if booking.booking_status == "capacity_conflict":
        return "capacity_conflict", 0
    if booking.booking_status == "pending_payment":
        return "processing", held_spots
    return "failed", 0


def promote_waitlist_entries(db: Session, db_game: Game, now: datetime) -> None:
    game_id = db_game.id
    while True:
        db_game = get_locked_game_or_404(db, game_id)
        if not db_game.waitlist_enabled:
            sync_game_capacity_status(db, db_game)
            return

        if is_roster_locked(db_game, now):
            sync_game_capacity_status(db, db_game)
            return

        available_spots = max(
            db_game.total_spots - count_roster_players(db, db_game.id, now=now),
            0,
        )
        if available_spots <= 0:
            sync_game_capacity_status(db, db_game)
            return
        app_payment_required = game_requires_app_player_payment(db_game)
        restart_after_paid_boundary = False

        waitlist_entries = list(
            db.scalars(
                select(WaitlistEntry)
                .where(
                    WaitlistEntry.game_id == db_game.id,
                    WaitlistEntry.waitlist_status.in_(
                        WAITLIST_PROMOTION_CANDIDATE_STATUSES
                    ),
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
                waitlist_entry = db.scalar(
                    select(WaitlistEntry)
                    .where(WaitlistEntry.id == waitlist_entry.id)
                    .with_for_update()
                )
                if waitlist_entry is None:
                    continue
                waitlist_entry.waitlist_status = "removed"
                waitlist_entry.updated_at = now
                db.add(waitlist_entry)
                continue

            booking = (
                db.scalar(
                    select(Booking)
                    .where(Booking.id == participant.booking_id)
                    .with_for_update()
                )
                if participant.booking_id
                else None
            )
            waitlist_entry = db.scalar(
                select(WaitlistEntry)
                .where(
                    WaitlistEntry.id == waitlist_entry.id,
                    WaitlistEntry.waitlist_status.in_(
                        WAITLIST_PROMOTION_CANDIDATE_STATUSES
                    ),
                )
                .with_for_update()
            )
            if waitlist_entry is None:
                continue
            if booking is None:
                waitlist_entry.waitlist_status = "removed"
                waitlist_entry.updated_at = now
                db.add(waitlist_entry)
                continue

            booking_participants = list(
                db.scalars(
                    select(GameParticipant)
                    .where(
                        GameParticipant.game_id == db_game.id,
                        GameParticipant.booking_id == booking.id,
                        GameParticipant.participant_status == "waitlisted",
                    )
                    .order_by(GameParticipant.id.asc())
                    .with_for_update()
                ).all()
            )
            if len(booking_participants) != waitlist_entry.party_size:
                waitlist_entry.party_size = len(booking_participants)

            if not booking_participants or len(booking_participants) > available_spots:
                db.add(waitlist_entry)
                continue

            if app_payment_required:
                attempt_paid_waitlist_auto_promotion(
                    db,
                    db_game,
                    waitlist_entry,
                    booking,
                    booking_participants,
                    now,
                )
                restart_after_paid_boundary = True
                break

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
            booking.reservation_status = "confirmed"
            booking.expires_at = None
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

        if restart_after_paid_boundary:
            db_game = get_locked_game_or_404(db, game_id)
        sync_game_capacity_status(db, db_game)
        if not restart_after_paid_boundary:
            return
