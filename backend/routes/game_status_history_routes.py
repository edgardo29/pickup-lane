import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import GameStatusHistory, User
from backend.routes.retired_route_helpers import raise_retired_mutation_route
from backend.schemas import (
    GameStatusHistoryRead,
)
from backend.services.auth_service import require_active_admin
from backend.services.status_history_service import (
    get_game_status_history_record,
    list_game_status_history_records,
)
from backend.services.query_pagination import (
    DEFAULT_ADMIN_COLLECTION_LIMIT,
    MAX_ADMIN_COLLECTION_LIMIT,
)

router = APIRouter(prefix="/game-status-history", tags=["game_status_history"])


@router.post(
    "",
    status_code=status.HTTP_410_GONE,
)
def create_game_status_history(
    current_admin: User = Depends(require_active_admin),
) -> None:
    del current_admin
    raise_retired_mutation_route(
        code="game_status_history_scaffold_removed",
        message=(
            "Direct game status history creation is no longer supported. "
            "History is recorded by product-owned workflows."
        ),
    )


@router.get(
    "/{history_id}",
    response_model=GameStatusHistoryRead,
    status_code=status.HTTP_200_OK,
)
def get_game_status_history(
    history_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
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
    offset: int = Query(default=0, ge=0),
    limit: int = Query(
        default=DEFAULT_ADMIN_COLLECTION_LIMIT,
        ge=1,
        le=MAX_ADMIN_COLLECTION_LIMIT,
    ),
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> list[GameStatusHistory]:
    del current_admin
    return list_game_status_history_records(
        db,
        game_id=game_id,
        changed_by_user_id=changed_by_user_id,
        change_source=change_source,
        limit=limit,
        offset=offset,
    )


@router.patch(
    "/{history_id}",
    status_code=status.HTTP_410_GONE,
)
def update_game_status_history(
    history_id: uuid.UUID,
    current_admin: User = Depends(require_active_admin),
) -> None:
    del history_id, current_admin
    raise_retired_mutation_route(
        code="game_status_history_scaffold_removed",
        message=(
            "Direct game status history updates are no longer supported. "
            "History is recorded by product-owned workflows."
        ),
    )
