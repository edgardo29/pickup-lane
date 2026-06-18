import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import GameStatusHistory, User
from backend.schemas import (
    GameStatusHistoryCreate,
    GameStatusHistoryRead,
    GameStatusHistoryUpdate,
)
from backend.services.admin_permission_service import (
    PERMISSION_OFFICIAL_GAMES_READ,
    PERMISSION_OFFICIAL_GAMES_WRITE,
)
from backend.services.auth_service import require_admin_permission
from backend.services.status_history_service import (
    create_game_status_history_record,
    get_game_status_history_record,
    list_game_status_history_records,
    update_game_status_history_record,
)

router = APIRouter(prefix="/game-status-history", tags=["game_status_history"])


@router.post(
    "",
    response_model=GameStatusHistoryRead,
    status_code=status.HTTP_201_CREATED,
)
def create_game_status_history(
    game_status_history: GameStatusHistoryCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_OFFICIAL_GAMES_WRITE)
    ),
) -> GameStatusHistory:
    del current_admin
    return create_game_status_history_record(db, game_status_history)


@router.get(
    "/{history_id}",
    response_model=GameStatusHistoryRead,
    status_code=status.HTTP_200_OK,
)
def get_game_status_history(
    history_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_OFFICIAL_GAMES_READ)
    ),
) -> GameStatusHistory:
    del current_admin
    return get_game_status_history_record(db, history_id)


@router.get(
    "",
    response_model=list[GameStatusHistoryRead],
    status_code=status.HTTP_200_OK,
)
def list_game_status_history(
    game_id: uuid.UUID | None = None,
    changed_by_user_id: uuid.UUID | None = None,
    change_source: str | None = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_OFFICIAL_GAMES_READ)
    ),
) -> list[GameStatusHistory]:
    del current_admin
    return list_game_status_history_records(
        db,
        game_id=game_id,
        changed_by_user_id=changed_by_user_id,
        change_source=change_source,
    )


@router.patch(
    "/{history_id}",
    response_model=GameStatusHistoryRead,
    status_code=status.HTTP_200_OK,
)
def update_game_status_history(
    history_id: uuid.UUID,
    history_update: GameStatusHistoryUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_OFFICIAL_GAMES_WRITE)
    ),
) -> GameStatusHistory:
    del current_admin
    return update_game_status_history_record(db, history_id, history_update)
