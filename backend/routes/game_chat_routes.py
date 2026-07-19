import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import GameChat, User
from backend.schemas import (
    GameChatCreate,
    GameChatEnsureCreate,
    GameChatRead,
    GameChatReadStateRead,
    GameChatUpdate,
)
from backend.services.auth_service import require_active_user, require_active_admin
from backend.services.game_chat_service import (
    create_game_chat_record,
    get_game_chat_or_404,
    get_game_chat_read_state_record,
    list_game_chat_records,
    mark_game_chat_read_workflow,
    ensure_game_chat_for_game_workflow,
    update_game_chat_record,
)

router = APIRouter(prefix="/game-chats", tags=["game_chats"])


# This route creates the room-level chat record for a game after validating the
# game can currently support chat.
@router.post("", response_model=GameChatRead, status_code=status.HTTP_201_CREATED)
def create_game_chat(
    game_chat: GameChatCreate,
    current_admin: User = Depends(require_active_admin),
    db: Session = Depends(get_db),
) -> GameChat:
    return create_game_chat_record(db, game_chat, current_admin)


@router.post(
    "/for-game/{game_id}",
    response_model=GameChatRead,
    status_code=status.HTTP_200_OK,
)
def ensure_game_chat_for_game(
    game_id: uuid.UUID,
    payload: GameChatEnsureCreate,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> GameChatRead:
    return ensure_game_chat_for_game_workflow(db, game_id, payload, current_user)


# This route fetches a single game chat room by its internal UUID.
@router.get("/{game_chat_id}", response_model=GameChatRead, status_code=status.HTTP_200_OK)
def get_game_chat(
    game_chat_id: uuid.UUID,
    current_staff: User = Depends(require_active_admin),
    db: Session = Depends(get_db),
) -> GameChat:
    del current_staff
    return get_game_chat_or_404(db, game_chat_id)


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


# This route returns game chat room records currently stored in the app database.
@router.get("", response_model=list[GameChatRead], status_code=status.HTTP_200_OK)
def list_game_chats(
    game_id: uuid.UUID | None = None,
    chat_status: str | None = None,
    current_staff: User = Depends(require_active_admin),
    db: Session = Depends(get_db),
) -> list[GameChat]:
    del current_staff
    return list_game_chat_records(
        db,
        game_id=game_id,
        chat_status=chat_status,
    )


# This route applies partial updates to an existing game chat while keeping the
# lock lifecycle timestamp aligned with chat_status.
@router.patch(
    "/{game_chat_id}",
    response_model=GameChatRead,
    status_code=status.HTTP_200_OK,
)
def update_game_chat(
    game_chat_id: uuid.UUID,
    game_chat_update: GameChatUpdate,
    current_admin: User = Depends(require_active_admin),
    db: Session = Depends(get_db),
) -> GameChat:
    return update_game_chat_record(
        db,
        game_chat_id,
        game_chat_update,
        current_admin,
    )
