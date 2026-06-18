import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
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
from backend.services.admin_permission_service import (
    PERMISSION_CHAT_ROOMS_MANAGE,
    PERMISSION_CONTENT_MODERATE,
)
from backend.services.auth_service import require_active_user, require_admin_permission
from backend.services.game_chat_service import (
    build_game_chat_conflict_detail,
    create_game_chat_record,
    get_active_game_or_404,
    get_chat_read_state,
    get_game_chat_or_404,
    get_or_create_active_game_chat,
    list_game_chat_records,
    mark_chat_read,
    require_chat_member,
    update_game_chat_record,
)

router = APIRouter(prefix="/game-chats", tags=["game_chats"])


def get_effective_user(
    db: Session,
    acting_user_id: uuid.UUID | None,
    current_user: User | None,
) -> User:
    if current_user is not None:
        return current_user

    if acting_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sign in to use game chat.",
        )

    db_user = db.get(User, acting_user_id)
    if db_user is None or db_user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    return db_user


def serialize_game_chat(
    db_game_chat: GameChat,
    unread_count: int = 0,
    last_read_at: datetime | None = None,
) -> GameChatRead:
    return GameChatRead(
        id=db_game_chat.id,
        game_id=db_game_chat.game_id,
        chat_status=db_game_chat.chat_status,
        created_at=db_game_chat.created_at,
        updated_at=db_game_chat.updated_at,
        locked_at=db_game_chat.locked_at,
        unread_count=unread_count,
        last_read_at=last_read_at,
    )


# This route creates the room-level chat record for a game after validating the
# game can currently support chat.
@router.post("", response_model=GameChatRead, status_code=status.HTTP_201_CREATED)
def create_game_chat(
    game_chat: GameChatCreate,
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_CHAT_ROOMS_MANAGE)
    ),
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
    db_game = get_active_game_or_404(db, game_id)
    effective_user = get_effective_user(db, payload.acting_user_id, current_user)

    if not db_game.is_chat_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This game does not have chat enabled.",
        )

    db_game_chat = get_or_create_active_game_chat(db, db_game)
    require_chat_member(db, db_game_chat, effective_user)

    try:
        db.commit()
        db.refresh(db_game_chat)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_game_chat_conflict_detail(exc),
        ) from exc

    read_state, unread_count = get_chat_read_state(db, db_game_chat, effective_user)
    return serialize_game_chat(
        db_game_chat,
        unread_count=unread_count,
        last_read_at=read_state.last_read_at if read_state else None,
    )


# This route fetches a single game chat room by its internal UUID.
@router.get("/{game_chat_id}", response_model=GameChatRead, status_code=status.HTTP_200_OK)
def get_game_chat(
    game_chat_id: uuid.UUID,
    current_staff: User = Depends(
        require_admin_permission(PERMISSION_CONTENT_MODERATE)
    ),
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
    db_game_chat = db.get(GameChat, game_chat_id)

    if db_game_chat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game chat not found.",
        )

    effective_user = get_effective_user(db, acting_user_id, current_user)
    require_chat_member(db, db_game_chat, effective_user)
    read_state, unread_count = get_chat_read_state(db, db_game_chat, effective_user)

    return GameChatReadStateRead(
        chat_id=db_game_chat.id,
        user_id=effective_user.id,
        last_read_at=read_state.last_read_at if read_state else None,
        last_read_message_id=read_state.last_read_message_id if read_state else None,
        unread_count=unread_count,
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
    db_game_chat = db.get(GameChat, game_chat_id)

    if db_game_chat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game chat not found.",
        )

    effective_user = get_effective_user(db, payload.acting_user_id, current_user)
    require_chat_member(db, db_game_chat, effective_user)
    read_state = mark_chat_read(db, db_game_chat, effective_user)

    try:
        db.commit()
        db.refresh(read_state)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_game_chat_conflict_detail(exc),
        ) from exc

    return GameChatReadStateRead(
        chat_id=db_game_chat.id,
        user_id=effective_user.id,
        last_read_at=read_state.last_read_at,
        last_read_message_id=read_state.last_read_message_id,
        unread_count=0,
    )


# This route returns game chat room records currently stored in the app database.
@router.get("", response_model=list[GameChatRead], status_code=status.HTTP_200_OK)
def list_game_chats(
    game_id: uuid.UUID | None = None,
    chat_status: str | None = None,
    current_staff: User = Depends(
        require_admin_permission(PERMISSION_CONTENT_MODERATE)
    ),
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
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_CHAT_ROOMS_MANAGE)
    ),
    db: Session = Depends(get_db),
) -> GameChat:
    return update_game_chat_record(
        db,
        game_chat_id,
        game_chat_update,
        current_admin,
    )
