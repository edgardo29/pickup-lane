import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import Booking, Game, GameCredit, GameCreditUsage, Payment, User
from backend.schemas.game_credit_schema import (
    GameCreditIssueCreate,
    GameCreditReverseCreate,
)
from backend.services.admin_action_service import record_admin_action
from backend.services.game_credit_service import (
    REVERSED_USAGE_STATUS,
    REVERSE_USAGE_TYPE,
    has_reserved_usage_for_credit,
)
from backend.services.user_service import build_user_conflict_detail

VALID_CREDIT_REASONS = {
    "official_game_cancelled",
    "weather_cancelled",
    "player_cancelled_on_time",
    "admin_credit",
    "support_adjustment",
}


@dataclass(frozen=True)
class CreditSourceContext:
    source_booking: Booking | None
    source_payment: Payment | None
    payment_booking: Booking | None


def get_active_credit_user_or_404(db: Session, user_id: uuid.UUID) -> User:
    user = db.get(User, user_id)

    if user is None or user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if user.account_status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is not active.",
        )

    return user


def validate_official_source_game(db: Session, source_game_id: uuid.UUID | None) -> None:
    if source_game_id is None:
        return

    game = db.get(Game, source_game_id)

    if game is None or game.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source game not found.",
        )

    if game.game_type != "official" or game.payment_collection_type != "in_app":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pickup Lane credits can only be sourced from official in-app games.",
        )


def get_source_booking_or_404(
    db: Session,
    source_booking_id: uuid.UUID | None,
) -> Booking | None:
    if source_booking_id is None:
        return None

    booking = db.get(Booking, source_booking_id)
    if booking is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source booking not found.",
        )

    return booking


def get_source_payment_or_404(
    db: Session,
    source_payment_id: uuid.UUID | None,
) -> Payment | None:
    if source_payment_id is None:
        return None

    payment = db.get(Payment, source_payment_id)
    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source payment not found.",
        )

    return payment


def validate_credit_source_booking(
    *,
    booking: Booking | None,
    user_id: uuid.UUID,
    source_game_id: uuid.UUID | None,
) -> None:
    if booking is None:
        return

    if booking.buyer_user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source booking must belong to the credited user.",
        )

    if source_game_id is not None and booking.game_id != source_game_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source booking must belong to the source game.",
        )


def validate_credit_source_payment(
    *,
    payment: Payment | None,
    user_id: uuid.UUID,
    source_game_id: uuid.UUID | None,
    source_booking_id: uuid.UUID | None,
) -> None:
    if payment is None:
        return

    if payment.payer_user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source payment must belong to the credited user.",
        )

    if source_booking_id is not None and payment.booking_id != source_booking_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source payment must belong to the source booking.",
        )

    if (
        source_game_id is not None
        and payment.game_id is not None
        and payment.game_id != source_game_id
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source payment must belong to the source game.",
        )


def validate_credit_source_payment_booking_game(
    *,
    payment: Payment | None,
    payment_booking: Booking | None,
) -> None:
    if payment is None or payment_booking is None or payment.game_id is None:
        return

    if payment.game_id != payment_booking.game_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source payment must belong to the source booking game.",
        )


def get_payment_booking_or_404(
    db: Session,
    payment: Payment | None,
    source_booking: Booking | None,
) -> Booking | None:
    if payment is None or payment.booking_id is None:
        return None

    if source_booking is not None and source_booking.id == payment.booking_id:
        return source_booking

    booking = db.get(Booking, payment.booking_id)
    if booking is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source payment booking is not valid.",
        )

    return booking


def validate_derived_credit_source_game(
    db: Session,
    *,
    source_game_id: uuid.UUID | None,
    source_booking: Booking | None,
    source_payment: Payment | None,
    payment_booking: Booking | None,
) -> None:
    authoritative_game_ids: set[uuid.UUID] = set()
    if source_booking is not None:
        authoritative_game_ids.add(source_booking.game_id)
    if source_payment is not None:
        if source_payment.game_id is not None:
            authoritative_game_ids.add(source_payment.game_id)
        if payment_booking is not None:
            authoritative_game_ids.add(payment_booking.game_id)
        if source_payment.game_id is None and payment_booking is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Source payment must belong to an official in-app game.",
            )

    if len(authoritative_game_ids) > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source payment, booking, and game references must agree.",
        )

    authoritative_game_id = next(iter(authoritative_game_ids), None)
    if (
        source_game_id is not None
        and authoritative_game_id is not None
        and source_game_id != authoritative_game_id
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source game must agree with the source payment or booking.",
        )

    validate_official_source_game(db, authoritative_game_id or source_game_id)


def validate_credit_source_references(
    db: Session,
    *,
    user_id: uuid.UUID,
    source_game_id: uuid.UUID | None,
    source_booking_id: uuid.UUID | None,
    source_payment_id: uuid.UUID | None,
) -> CreditSourceContext:
    validate_official_source_game(db, source_game_id)
    source_booking = get_source_booking_or_404(db, source_booking_id)
    source_payment = get_source_payment_or_404(db, source_payment_id)
    payment_booking = get_payment_booking_or_404(db, source_payment, source_booking)
    validate_credit_source_booking(
        booking=source_booking,
        user_id=user_id,
        source_game_id=source_game_id,
    )
    validate_credit_source_payment(
        payment=source_payment,
        user_id=user_id,
        source_game_id=source_game_id,
        source_booking_id=source_booking_id,
    )
    validate_credit_source_booking(
        booking=payment_booking,
        user_id=user_id,
        source_game_id=source_game_id,
    )
    validate_credit_source_payment_booking_game(
        payment=source_payment,
        payment_booking=payment_booking,
    )
    validate_derived_credit_source_game(
        db,
        source_game_id=source_game_id,
        source_booking=source_booking,
        source_payment=source_payment,
        payment_booking=payment_booking,
    )
    return CreditSourceContext(
        source_booking=source_booking,
        source_payment=source_payment,
        payment_booking=payment_booking,
    )


def normalize_optional_operation_text(value: str | None) -> str | None:
    normalized = (value or "").strip()
    return normalized or None


def require_credit_issue_idempotency_key_available(
    db: Session,
    idempotency_key: str | None,
) -> None:
    if idempotency_key is None:
        return

    existing_credit_id = db.scalar(
        select(GameCredit.id).where(GameCredit.idempotency_key == idempotency_key)
    )
    if existing_credit_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A game credit with this idempotency key already exists.",
        )


def require_credit_usage_idempotency_key_available(
    db: Session,
    idempotency_key: str | None,
) -> None:
    if idempotency_key is None:
        return

    existing_usage_id = db.scalar(
        select(GameCreditUsage.id).where(
            GameCreditUsage.idempotency_key == idempotency_key
        )
    )
    if existing_usage_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A game credit usage with this idempotency key already exists.",
        )


def source_context_amounts(context: CreditSourceContext) -> list[int]:
    amounts: list[int] = []
    if context.source_payment is not None:
        amounts.append(context.source_payment.amount_cents)
    if context.source_booking is not None:
        amounts.append(context.source_booking.total_cents)
    if context.payment_booking is not None:
        amounts.append(context.payment_booking.total_cents)
    return amounts


def source_context_booking_ids(context: CreditSourceContext) -> set[uuid.UUID]:
    booking_ids: set[uuid.UUID] = set()
    if context.source_booking is not None:
        booking_ids.add(context.source_booking.id)
    if context.payment_booking is not None:
        booking_ids.add(context.payment_booking.id)
    if context.source_payment is not None and context.source_payment.booking_id is not None:
        booking_ids.add(context.source_payment.booking_id)
    return booking_ids


def source_context_payment_ids(
    db: Session,
    context: CreditSourceContext,
) -> set[uuid.UUID]:
    payment_ids: set[uuid.UUID] = set()
    if context.source_payment is not None:
        payment_ids.add(context.source_payment.id)

    booking_ids = source_context_booking_ids(context)
    if booking_ids:
        linked_payment_ids = db.scalars(
            select(Payment.id).where(Payment.booking_id.in_(booking_ids))
        ).all()
        payment_ids.update(linked_payment_ids)

    return payment_ids


def source_context_reference_filter(db: Session, context: CreditSourceContext):
    source_filters = []
    payment_ids = source_context_payment_ids(db, context)
    booking_ids = source_context_booking_ids(context)
    if payment_ids:
        source_filters.append(GameCredit.source_payment_id.in_(payment_ids))
    if booking_ids:
        source_filters.append(GameCredit.source_booking_id.in_(booking_ids))
    return or_(*source_filters) if source_filters else None


def get_existing_credit_total_for_source(
    db: Session,
    *,
    user_id: uuid.UUID,
    context: CreditSourceContext,
) -> int:
    source_filter = source_context_reference_filter(db, context)
    if source_filter is None:
        return 0

    return (
        db.scalar(
            select(func.coalesce(func.sum(GameCredit.amount_cents), 0)).where(
                GameCredit.user_id == user_id,
                GameCredit.credit_status != "reversed",
                source_filter,
            )
        )
        or 0
    )


def get_remaining_eligible_credit_amount(
    db: Session,
    *,
    user_id: uuid.UUID,
    context: CreditSourceContext,
) -> int:
    source_amounts = source_context_amounts(context)
    if not source_amounts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Game credit issue requires a source booking or payment with "
                "server-derived eligible value."
            ),
        )

    source_maximum = min(source_amounts)
    existing_total = get_existing_credit_total_for_source(
        db,
        user_id=user_id,
        context=context,
    )
    return max(source_maximum - existing_total, 0)


def validate_source_eligible_credit_amount(
    db: Session,
    *,
    user_id: uuid.UUID,
    amount_cents: int,
    context: CreditSourceContext,
) -> None:
    remaining_eligible_amount = get_remaining_eligible_credit_amount(
        db,
        user_id=user_id,
        context=context,
    )
    if amount_cents > remaining_eligible_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game credit amount exceeds the source-derived eligible amount.",
        )


def issue_admin_game_credit(
    db: Session,
    *,
    admin_user: User,
    payload: GameCreditIssueCreate,
) -> GameCredit:
    if payload.credit_reason not in VALID_CREDIT_REASONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported game credit reason.",
        )

    get_active_credit_user_or_404(db, payload.user_id)
    source_context = validate_credit_source_references(
        db,
        user_id=payload.user_id,
        source_game_id=payload.source_game_id,
        source_booking_id=payload.source_booking_id,
        source_payment_id=payload.source_payment_id,
    )

    explicit_idempotency_key = normalize_optional_operation_text(payload.idempotency_key)
    note = normalize_optional_operation_text(payload.note)
    require_credit_issue_idempotency_key_available(db, explicit_idempotency_key)
    validate_source_eligible_credit_amount(
        db,
        user_id=payload.user_id,
        amount_cents=payload.amount_cents,
        context=source_context,
    )

    idempotency_key = explicit_idempotency_key or (
        f"admin-credit:{admin_user.id}:{payload.user_id}:{uuid.uuid4()}"
    )
    now = datetime.now(timezone.utc)
    game_credit = GameCredit(
        id=uuid.uuid4(),
        user_id=payload.user_id,
        amount_cents=payload.amount_cents,
        available_cents=payload.amount_cents,
        currency="USD",
        credit_status="active",
        credit_reason=payload.credit_reason,
        source_game_id=payload.source_game_id,
        source_booking_id=payload.source_booking_id,
        source_payment_id=payload.source_payment_id,
        issued_by_user_id=admin_user.id,
        idempotency_key=idempotency_key,
        note=note,
        created_at=now,
        updated_at=now,
    )

    try:
        db.add(game_credit)
        db.flush()
        record_admin_action(
            db,
            admin_user_id=admin_user.id,
            action_type="issue_credit",
            target_user_id=payload.user_id,
            target_game_id=payload.source_game_id,
            target_booking_id=payload.source_booking_id,
            target_payment_id=payload.source_payment_id,
            target_game_credit_id=game_credit.id,
            reason=note,
            metadata={
                "amount_cents": payload.amount_cents,
                "credit_reason": payload.credit_reason,
            },
        )
        db.commit()
        db.refresh(game_credit)
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_user_conflict_detail(exc),
        ) from exc

    return game_credit


def reverse_admin_game_credit(
    db: Session,
    *,
    admin_user: User,
    game_credit_id: uuid.UUID,
    payload: GameCreditReverseCreate,
) -> GameCredit:
    game_credit = db.scalars(
        select(GameCredit)
        .where(GameCredit.id == game_credit_id)
        .with_for_update()
    ).first()

    if game_credit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game credit not found.",
        )

    now = datetime.now(timezone.utc)
    if game_credit.credit_status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only active credit with available value can be reversed.",
        )

    if has_reserved_usage_for_credit(db, game_credit.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Credit with reserved usage cannot be reversed.",
        )

    if game_credit.available_cents <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only active credit with available value can be reversed.",
        )

    explicit_idempotency_key = normalize_optional_operation_text(payload.idempotency_key)
    note = normalize_optional_operation_text(payload.note)
    require_credit_usage_idempotency_key_available(db, explicit_idempotency_key)
    idempotency_key = explicit_idempotency_key or (
        f"reverse-credit:{game_credit.id}:{uuid.uuid4()}"
    )
    usage = GameCreditUsage(
        id=uuid.uuid4(),
        game_credit_id=game_credit.id,
        booking_id=game_credit.source_booking_id,
        game_id=game_credit.source_game_id,
        payment_id=game_credit.source_payment_id,
        amount_cents=game_credit.available_cents,
        currency="USD",
        usage_type=REVERSE_USAGE_TYPE,
        usage_status=REVERSED_USAGE_STATUS,
        idempotency_key=idempotency_key,
        reason_code="admin_credit_reversal",
        created_at=now,
        updated_at=now,
    )
    game_credit.available_cents = 0
    game_credit.credit_status = "reversed"
    game_credit.reversed_by_user_id = admin_user.id
    game_credit.reversed_at = now
    game_credit.updated_at = now

    try:
        record_admin_action(
            db,
            admin_user_id=admin_user.id,
            action_type="reverse_credit",
            target_user_id=game_credit.user_id,
            target_game_id=game_credit.source_game_id,
            target_booking_id=game_credit.source_booking_id,
            target_payment_id=game_credit.source_payment_id,
            target_game_credit_id=game_credit.id,
            reason=note,
            metadata={"game_credit_id": game_credit.id},
        )
        db.add(game_credit)
        db.add(usage)
        db.commit()
        db.refresh(game_credit)
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_user_conflict_detail(exc),
        ) from exc

    return game_credit
