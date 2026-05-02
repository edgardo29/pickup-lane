import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Game, GameChat
from backend.schemas import GameChatCreate, GameChatRead, GameChatUpdate

router = APIRouter(prefix="/game-chats", tags=["game_chats"])

VALID_CHAT_STATUSES = {"active", "locked", "archived"}
CHAT_CREATABLE_GAME_STATUSES = {"scheduled", "full"}
TERMINAL_CHAT_STATUSES = {"archived"}


def build_game_chat_conflict_detail(exc: IntegrityError) -> str:
    error_text = str(exc.orig)

    if "uq_game_chats_game_id" in error_text:
        return "This game already has a chat room."

    return error_text


def get_active_game_or_404(db: Session, game_id: uuid.UUID) -> Game:
    db_game = db.get(Game, game_id)

    if db_game is None or db_game.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found.",
        )

    return db_game


def validate_game_chat_business_rules(chat_data: dict[str, object]) -> None:
    for field_name in ("game_id", "chat_status"):
        if chat_data[field_name] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} cannot be null.",
            )

    if chat_data["chat_status"] not in VALID_CHAT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="chat_status must be 'active', 'locked', or 'archived'.",
        )


def normalize_game_chat_lifecycle_fields(
    chat_data: dict[str, object],
    existing_game_chat: GameChat | None = None,
) -> dict[str, object]:
    normalized_data = dict(chat_data)

    # locked_at is derived from status so newly-created rooms cannot keep stale
    # lock timestamps around while active, and locked rooms keep their original
    # lock timestamp through later archive transitions.
    if normalized_data["chat_status"] == "locked":
        normalized_data["locked_at"] = (
            normalized_data.get("locked_at")
            or (existing_game_chat.locked_at if existing_game_chat is not None else None)
            or datetime.now(timezone.utc)
        )
    elif normalized_data["chat_status"] == "archived":
        normalized_data["locked_at"] = (
            existing_game_chat.locked_at if existing_game_chat is not None else None
        )
    else:
        normalized_data["locked_at"] = None

    return normalized_data


def validate_game_chat_references(db: Session, chat_data: dict[str, object]) -> None:
    db_game = get_active_game_or_404(db, chat_data["game_id"])

    if not db_game.is_chat_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This game does not have chat enabled.",
        )

    if db_game.publish_status == "archived":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Archived games cannot create chat rooms.",
        )

    if db_game.game_status not in CHAT_CREATABLE_GAME_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only scheduled or full games can create chat rooms.",
        )


def validate_game_chat_is_editable(db_game_chat: GameChat) -> None:
    if db_game_chat.chat_status in TERMINAL_CHAT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Archived game chats cannot be updated.",
        )


# This route creates the room-level chat record for a game after validating the
# game can currently support chat.
@router.post("", response_model=GameChatRead, status_code=status.HTTP_201_CREATED)
def create_game_chat(
    game_chat: GameChatCreate,
    db: Session = Depends(get_db),
) -> GameChat:
    chat_data = normalize_game_chat_lifecycle_fields(game_chat.model_dump())
    validate_game_chat_business_rules(chat_data)
    validate_game_chat_references(db, chat_data)

    new_game_chat = GameChat(
        id=uuid.uuid4(),
        **chat_data,
    )

    try:
        db.add(new_game_chat)
        db.commit()
        db.refresh(new_game_chat)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_game_chat_conflict_detail(exc),
        ) from exc

    return new_game_chat


# This route fetches a single game chat room by its internal UUID.
@router.get("/{game_chat_id}", response_model=GameChatRead, status_code=status.HTTP_200_OK)
def get_game_chat(
    game_chat_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> GameChat:
    db_game_chat = db.get(GameChat, game_chat_id)

    if db_game_chat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game chat not found.",
        )

    return db_game_chat


# This route returns game chat room records currently stored in the app database.
@router.get("", response_model=list[GameChatRead], status_code=status.HTTP_200_OK)
def list_game_chats(
    game_id: uuid.UUID | None = None,
    chat_status: str | None = None,
    db: Session = Depends(get_db),
) -> list[GameChat]:
    statement = select(GameChat)

    if game_id is not None:
        statement = statement.where(GameChat.game_id == game_id)

    if chat_status is not None:
        if chat_status not in VALID_CHAT_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="chat_status must be 'active', 'locked', or 'archived'.",
            )
        statement = statement.where(GameChat.chat_status == chat_status)

    game_chats = db.scalars(statement.order_by(GameChat.created_at.desc())).all()
    return list(game_chats)


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
    db: Session = Depends(get_db),
) -> GameChat:
    db_game_chat = db.get(GameChat, game_chat_id)

    if db_game_chat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game chat not found.",
        )

    validate_game_chat_is_editable(db_game_chat)

    update_data = game_chat_update.model_dump(exclude_unset=True)

    if "game_id" in update_data and update_data["game_id"] != db_game_chat.game_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="game_id cannot be changed for an existing game chat.",
        )

    effective_chat_data = {
        "game_id": db_game_chat.game_id,
        "chat_status": update_data.get("chat_status", db_game_chat.chat_status),
        "locked_at": update_data.get("locked_at", db_game_chat.locked_at),
    }
    effective_chat_data = normalize_game_chat_lifecycle_fields(
        effective_chat_data,
        db_game_chat,
    )
    validate_game_chat_business_rules(effective_chat_data)
    get_active_game_or_404(db, db_game_chat.game_id)

    # Lifecycle fields are managed from the fully merged chat state so partial
    # PATCH payloads cannot leave stale lock timestamps behind.
    update_data["locked_at"] = effective_chat_data["locked_at"]

    for field_name, field_value in update_data.items():
        setattr(db_game_chat, field_name, field_value)

    db_game_chat.updated_at = datetime.now(timezone.utc)

    try:
        db.add(db_game_chat)
        db.commit()
        db.refresh(db_game_chat)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_game_chat_conflict_detail(exc),
        ) from exc

    return db_game_chat
