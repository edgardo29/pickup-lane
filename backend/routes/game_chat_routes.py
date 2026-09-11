import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.routes.retired_route_helpers import raise_retired_mutation_route
from backend.schemas import (
    GameChatEnsureCreate,
    GameChatRead,
    GameChatReadStateRead,
)
from backend.services.auth_service import (
    require_active_admin,
    require_active_user,
    require_verified_user,
)
from backend.services.game_chat_service import (
    ensure_game_chat_for_game_workflow,
    get_game_chat_read_state_record,
    mark_game_chat_read_workflow,
)

router = APIRouter(prefix="/game-chats", tags=["game_chats"])


# This route creates the room-level chat record for a game after validating the
# game can currently support chat.
@router.post("", status_code=status.HTTP_410_GONE)
def create_game_chat(
    current_admin: User = Depends(require_active_admin),
) -> None:
    del current_admin
    raise_retired_mutation_route(
        code="game_chat_scaffold_removed",
        message=(
            "Direct game chat creation is no longer supported. Use scoped "
            "game and Need-a-Sub chat workflows."
        ),
    )


@router.post(
    "/for-game/{game_id}",
    response_model=GameChatRead,
    status_code=status.HTTP_200_OK,
)
def ensure_game_chat_for_game(
    game_id: uuid.UUID,
    payload: GameChatEnsureCreate,
    current_user: User = Depends(require_verified_user),
    db: Session = Depends(get_db),
) -> GameChatRead:
    return ensure_game_chat_for_game_workflow(db, game_id, payload, current_user)


@router.get(
    "/{game_chat_id}/read-state",
    response_model=GameChatReadStateRead,
    status_code=status.HTTP_200_OK,
)
def get_game_chat_read_state(
    game_chat_id: uuid.UUID,
    acting_user_id: uuid.UUID | None = None,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> GameChatReadStateRead:
    return get_game_chat_read_state_record(
        db,
        game_chat_id,
        acting_user_id,
        current_user,
    )


@router.post(
    "/{game_chat_id}/read",
    response_model=GameChatReadStateRead,
    status_code=status.HTTP_200_OK,
)
def mark_game_chat_read(
    game_chat_id: uuid.UUID,
    payload: GameChatEnsureCreate,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> GameChatReadStateRead:
    return mark_game_chat_read_workflow(db, game_chat_id, payload, current_user)


# This route applies partial updates to an existing game chat while keeping the
# lock lifecycle timestamp aligned with chat_status.
@router.patch(
    "/{game_chat_id}",
    status_code=status.HTTP_410_GONE,
)
def update_game_chat(
    game_chat_id: uuid.UUID,
    current_admin: User = Depends(require_active_admin),
) -> None:
    del game_chat_id, current_admin
    raise_retired_mutation_route(
        code="game_chat_scaffold_removed",
        message=(
            "Direct game chat updates are no longer supported. Use scoped "
            "game and Need-a-Sub chat workflows."
        ),
    )
