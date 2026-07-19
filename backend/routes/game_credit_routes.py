import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import GameCredit, User
from backend.services.auth_service import get_current_app_user, require_active_admin
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
    get_game_credit_balance_for_user,
    list_game_credits_for_user,
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
    return get_game_credit_balance_for_user(db, current_user, user_id=user_id)


@router.get("", response_model=list[GameCreditRead], status_code=status.HTTP_200_OK)
def list_game_credits(
    user_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_app_user),
    db: Session = Depends(get_db),
) -> list[GameCredit]:
    return list_game_credits_for_user(db, current_user, user_id=user_id)


@admin_router.post(
    "/issue",
    response_model=GameCreditRead,
    status_code=status.HTTP_201_CREATED,
)
def issue_game_credit(
    payload: GameCreditIssueCreate,
    current_user: User = Depends(require_active_admin),
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
    current_user: User = Depends(require_active_admin),
    db: Session = Depends(get_db),
) -> GameCredit:
    return reverse_admin_game_credit(
        db,
        admin_user=current_user,
        game_credit_id=game_credit_id,
        payload=payload,
    )
