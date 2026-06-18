import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import GameCredit, User
from backend.services.admin_permission_service import (
    PERMISSION_MONEY_CREDIT_MANAGE,
    PERMISSION_MONEY_READ,
)
from backend.services.auth_service import (
    get_current_app_user,
    require_admin_permission,
    require_user_admin_permission,
)
from backend.schemas import (
    GameCreditBalanceRead,
    GameCreditIssueCreate,
    GameCreditRead,
    GameCreditReverseCreate,
)
from backend.services.game_credit_admin_service import (
    issue_admin_game_credit,
    reverse_admin_game_credit,
)
from backend.services.game_credit_service import (
    get_available_game_credit_balance,
)

router = APIRouter(prefix="/game-credits", tags=["game_credits"])
admin_router = APIRouter(prefix="/admin/game-credits", tags=["admin_game_credits"])


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
        require_user_admin_permission(current_user, PERMISSION_MONEY_READ)

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
        require_user_admin_permission(current_user, PERMISSION_MONEY_READ)

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
    current_user: User = Depends(
        require_admin_permission(PERMISSION_MONEY_CREDIT_MANAGE)
    ),
    db: Session = Depends(get_db),
) -> GameCredit:
    return issue_admin_game_credit(db, admin_user=current_user, payload=payload)


@admin_router.post(
    "/{game_credit_id}/reverse",
    response_model=GameCreditRead,
    status_code=status.HTTP_200_OK,
)
def reverse_game_credit(
    game_credit_id: uuid.UUID,
    payload: GameCreditReverseCreate,
    current_user: User = Depends(
        require_admin_permission(PERMISSION_MONEY_CREDIT_MANAGE)
    ),
    db: Session = Depends(get_db),
) -> GameCredit:
    return reverse_admin_game_credit(
        db,
        admin_user=current_user,
        game_credit_id=game_credit_id,
        payload=payload,
    )
