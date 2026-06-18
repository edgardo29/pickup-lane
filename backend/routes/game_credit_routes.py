import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import GameCredit, User
from backend.services.admin_permission_service import (
    PERMISSION_MONEY_CREDIT_MANAGE,
    PERMISSION_MONEY_READ,
)
from backend.services.admin_rejected_attempt_policy import (
    ATTEMPT_TYPE_ISSUE_CREDIT_REJECTED,
    ATTEMPT_TYPE_REVERSE_CREDIT_REJECTED,
    REJECTION_PERMISSION_DENIED_PRELOAD,
)
from backend.services.admin_rejected_attempt_service import (
    build_permission_denied_metadata,
    record_admin_rejected_attempt,
)
from backend.services.auth_service import (
    get_current_app_user,
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


def get_route_path_template(request: Request) -> str:
    route = request.scope.get("route")
    route_path = getattr(route, "path", None)
    return route_path or request.url.path


def require_credit_admin_or_log_rejection(
    db: Session,
    *,
    current_user: User,
    request: Request,
    attempt_type: str,
    attempted_refs: dict[str, object],
) -> None:
    try:
        require_user_admin_permission(current_user, PERMISSION_MONEY_CREDIT_MANAGE)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_403_FORBIDDEN:
            record_admin_rejected_attempt(
                db,
                admin_user_id=current_user.id,
                attempt_type=attempt_type,
                rejection_mode=REJECTION_PERMISSION_DENIED_PRELOAD,
                response_status_code=exc.status_code,
                route_method=request.method,
                route_path=get_route_path_template(request),
                metadata=build_permission_denied_metadata(
                    attempted_refs=attempted_refs,
                    required_permission=PERMISSION_MONEY_CREDIT_MANAGE,
                ),
            )
        raise


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
    request: Request,
    current_user: User = Depends(get_current_app_user),
    db: Session = Depends(get_db),
) -> GameCredit:
    require_credit_admin_or_log_rejection(
        db,
        current_user=current_user,
        request=request,
        attempt_type=ATTEMPT_TYPE_ISSUE_CREDIT_REJECTED,
        attempted_refs={
            "user_id": payload.user_id,
            "source_game_id": payload.source_game_id,
            "source_booking_id": payload.source_booking_id,
            "source_payment_id": payload.source_payment_id,
        },
    )
    return issue_admin_game_credit(db, admin_user=current_user, payload=payload)


@admin_router.post(
    "/{game_credit_id}/reverse",
    response_model=GameCreditRead,
    status_code=status.HTTP_200_OK,
)
def reverse_game_credit(
    game_credit_id: uuid.UUID,
    payload: GameCreditReverseCreate,
    request: Request,
    current_user: User = Depends(get_current_app_user),
    db: Session = Depends(get_db),
) -> GameCredit:
    require_credit_admin_or_log_rejection(
        db,
        current_user=current_user,
        request=request,
        attempt_type=ATTEMPT_TYPE_REVERSE_CREDIT_REJECTED,
        attempted_refs={"game_credit_id": game_credit_id},
    )
    return reverse_admin_game_credit(
        db,
        admin_user=current_user,
        game_credit_id=game_credit_id,
        payload=payload,
    )
