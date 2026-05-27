import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import AdminAction, Game, GameCredit, GameCreditUsage, User
from backend.routes.auth_routes import (
    get_current_admin_user,
    get_current_app_user,
    require_admin,
)
from backend.routes.user_routes import build_conflict_detail
from backend.schemas import (
    GameCreditBalanceRead,
    GameCreditIssueCreate,
    GameCreditRead,
    GameCreditReverseCreate,
)
from backend.services.game_credit_service import (
    REVERSED_USAGE_STATUS,
    REVERSE_USAGE_TYPE,
    get_available_game_credit_balance,
)

router = APIRouter(prefix="/game-credits", tags=["game_credits"])
admin_router = APIRouter(prefix="/admin/game-credits", tags=["admin_game_credits"])

VALID_CREDIT_REASONS = {
    "official_game_cancelled",
    "weather_cancelled",
    "player_cancelled_on_time",
    "admin_credit",
    "support_adjustment",
}


def get_active_user_or_404(db: Session, user_id: uuid.UUID) -> User:
    user = db.get(User, user_id)

    if user is None or user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    return user


def validate_official_source_game(db: Session, source_game_id: uuid.UUID | None) -> None:
    if source_game_id is None:
        return

    game = db.get(Game, source_game_id)

    if game is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source game not found.",
        )

    if game.game_type != "official" or game.payment_collection_type != "in_app":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pickup Lane credits can only be sourced from official in-app games.",
        )


@router.get(
    "/balance",
    response_model=GameCreditBalanceRead,
    status_code=status.HTTP_200_OK,
)
def get_game_credit_balance(
    user_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_app_user),
    db: Session = Depends(get_db),
) -> GameCreditBalanceRead:
    effective_user_id = user_id or current_user.id

    if effective_user_id != current_user.id:
        require_admin(current_user)

    balance = get_available_game_credit_balance(
        db,
        effective_user_id,
        now=datetime.now(timezone.utc),
    )

    return GameCreditBalanceRead(
        user_id=effective_user_id,
        available_credit_cents=balance,
    )


@router.get("", response_model=list[GameCreditRead], status_code=status.HTTP_200_OK)
def list_game_credits(
    user_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_app_user),
    db: Session = Depends(get_db),
) -> list[GameCredit]:
    effective_user_id = user_id or current_user.id

    if effective_user_id != current_user.id:
        require_admin(current_user)

    statement = (
        select(GameCredit)
        .where(GameCredit.user_id == effective_user_id)
        .order_by(GameCredit.created_at.desc(), GameCredit.id.desc())
    )
    return list(db.scalars(statement).all())


@admin_router.post(
    "/issue",
    response_model=GameCreditRead,
    status_code=status.HTTP_201_CREATED,
)
def issue_game_credit(
    payload: GameCreditIssueCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> GameCredit:
    if payload.credit_reason not in VALID_CREDIT_REASONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported game credit reason.",
        )

    get_active_user_or_404(db, payload.user_id)
    validate_official_source_game(db, payload.source_game_id)

    idempotency_key = payload.idempotency_key or (
        f"admin-credit:{current_user.id}:{payload.user_id}:{uuid.uuid4()}"
    )
    now = datetime.now(timezone.utc)
    game_credit = GameCredit(
        id=uuid.uuid4(),
        user_id=payload.user_id,
        amount_cents=payload.amount_cents,
        remaining_cents=payload.amount_cents,
        currency="USD",
        credit_status="active",
        credit_reason=payload.credit_reason,
        source_game_id=payload.source_game_id,
        source_booking_id=payload.source_booking_id,
        source_payment_id=payload.source_payment_id,
        issued_by_user_id=current_user.id,
        idempotency_key=idempotency_key,
        note=payload.note,
        expires_at=payload.expires_at,
        created_at=now,
        updated_at=now,
    )
    admin_action = AdminAction(
        id=uuid.uuid4(),
        admin_user_id=current_user.id,
        action_type="issue_credit",
        target_user_id=payload.user_id,
        target_game_id=payload.source_game_id,
        target_booking_id=payload.source_booking_id,
        target_payment_id=payload.source_payment_id,
        reason=payload.note,
        metadata_={
            "amount_cents": payload.amount_cents,
            "credit_reason": payload.credit_reason,
        },
    )

    try:
        db.add(game_credit)
        db.add(admin_action)
        db.commit()
        db.refresh(game_credit)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_conflict_detail(exc),
        ) from exc

    return game_credit


@admin_router.post(
    "/{game_credit_id}/reverse",
    response_model=GameCreditRead,
    status_code=status.HTTP_200_OK,
)
def reverse_game_credit(
    game_credit_id: uuid.UUID,
    payload: GameCreditReverseCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
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
    is_expired = game_credit.expires_at is not None and game_credit.expires_at <= now
    if (
        game_credit.credit_status != "active"
        or game_credit.remaining_cents <= 0
        or game_credit.remaining_cents != game_credit.amount_cents
        or is_expired
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only active unused credit can be reversed.",
        )

    idempotency_key = payload.idempotency_key or (
        f"reverse-credit:{game_credit.id}:{uuid.uuid4()}"
    )
    usage = GameCreditUsage(
        id=uuid.uuid4(),
        game_credit_id=game_credit.id,
        user_id=game_credit.user_id,
        booking_id=game_credit.source_booking_id,
        game_id=game_credit.source_game_id,
        payment_id=game_credit.source_payment_id,
        amount_cents=game_credit.remaining_cents,
        currency="USD",
        usage_type=REVERSE_USAGE_TYPE,
        usage_status=REVERSED_USAGE_STATUS,
        idempotency_key=idempotency_key,
        created_at=now,
        updated_at=now,
    )
    game_credit.remaining_cents = 0
    game_credit.credit_status = "reversed"
    game_credit.reversed_by_user_id = current_user.id
    game_credit.reversed_at = now
    game_credit.updated_at = now
    admin_action = AdminAction(
        id=uuid.uuid4(),
        admin_user_id=current_user.id,
        action_type="reverse_credit",
        target_user_id=game_credit.user_id,
        target_game_id=game_credit.source_game_id,
        target_booking_id=game_credit.source_booking_id,
        target_payment_id=game_credit.source_payment_id,
        reason=payload.note,
        metadata_={"game_credit_id": str(game_credit.id)},
    )

    try:
        db.add(game_credit)
        db.add(usage)
        db.add(admin_action)
        db.commit()
        db.refresh(game_credit)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_conflict_detail(exc),
        ) from exc

    return game_credit
