import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import ChatMessage, GameChat, User
from backend.routes.auth_routes import get_current_app_user
from backend.schemas import ChatMessageCreate, ChatMessageRead, ChatMessageUpdate
from backend.services.game_chat_service import (
    create_or_update_chat_notifications,
    get_latest_visible_messages,
    mark_chat_read,
    normalize_message_body,
    require_chat_member,
    validate_sender_cooldown,
)

router = APIRouter(prefix="/chat-messages", tags=["chat_messages"])

VALID_MESSAGE_TYPES = {"text", "system", "pinned_update"}
VALID_MODERATION_STATUSES = {
    "visible",
    "hidden_by_admin",
    "deleted_by_sender",
    "flagged",
}
SENDER_REQUIRED_MESSAGE_TYPES = {"text", "pinned_update"}
DELETED_MODERATION_STATUSES = {"hidden_by_admin", "deleted_by_sender"}
TERMINAL_MODERATION_STATUSES = {"hidden_by_admin", "deleted_by_sender"}


def build_chat_message_conflict_detail(exc: IntegrityError) -> str:
    return str(exc.orig)


def get_game_chat_or_404(db: Session, chat_id: uuid.UUID) -> GameChat:
    db_game_chat = db.get(GameChat, chat_id)

    if db_game_chat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game chat not found.",
        )

    return db_game_chat


def get_active_user_or_404(
    db: Session,
    user_id: uuid.UUID,
    detail: str,
) -> User:
    db_user = db.get(User, user_id)

    if db_user is None or db_user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )

    return db_user


def validate_chat_message_business_rules(message_data: dict[str, object]) -> None:
    for field_name in ("chat_id", "message_type", "message_body", "moderation_status"):
        if message_data[field_name] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} cannot be null.",
            )

    if message_data["message_type"] not in VALID_MESSAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="message_type must be 'text', 'system', or 'pinned_update'.",
        )

    if message_data["moderation_status"] not in VALID_MODERATION_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "moderation_status must be 'visible', 'hidden_by_admin', "
                "'deleted_by_sender', or 'flagged'."
            ),
        )

    if not message_data["message_body"].strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="message_body must not be empty.",
        )

    if (
        message_data["message_type"] in SENDER_REQUIRED_MESSAGE_TYPES
        and message_data["sender_user_id"] is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="text and pinned_update messages require sender_user_id.",
        )

    if message_data["message_type"] == "pinned_update" and not message_data["is_pinned"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="pinned_update messages must be pinned.",
        )

    if message_data["is_pinned"] and message_data["pinned_by_user_id"] is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pinned messages require pinned_by_user_id.",
        )

    if (
        message_data["moderation_status"] in DELETED_MODERATION_STATUSES
        and message_data["deleted_by_user_id"] is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hidden or deleted messages require deleted_by_user_id.",
        )

    if message_data["moderation_status"] == "deleted_by_sender":
        if message_data["sender_user_id"] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sender-deleted messages require sender_user_id.",
            )

        if message_data["deleted_by_user_id"] != message_data["sender_user_id"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="deleted_by_user_id must match sender_user_id.",
            )


def normalize_chat_message_lifecycle_fields(
    message_data: dict[str, object],
    existing_chat_message: ChatMessage | None = None,
) -> dict[str, object]:
    normalized_data = dict(message_data)
    now = datetime.now(timezone.utc)

    # Pin and deletion timestamps are derived from state so create payloads
    # cannot store stale lifecycle fields that contradict the message status.
    if normalized_data["is_pinned"]:
        normalized_data["pinned_at"] = (
            normalized_data.get("pinned_at")
            or (
                existing_chat_message.pinned_at
                if existing_chat_message is not None
                else None
            )
            or now
        )
    else:
        normalized_data["pinned_at"] = None
        normalized_data["pinned_by_user_id"] = None

    if normalized_data["moderation_status"] in DELETED_MODERATION_STATUSES:
        normalized_data["deleted_at"] = (
            normalized_data.get("deleted_at")
            or (
                existing_chat_message.deleted_at
                if existing_chat_message is not None
                else None
            )
            or now
        )
    else:
        normalized_data["deleted_at"] = None
        normalized_data["deleted_by_user_id"] = None

    if existing_chat_message is None:
        normalized_data["edited_at"] = None
    elif normalized_data["message_body"] != existing_chat_message.message_body:
        normalized_data["edited_at"] = normalized_data.get("edited_at") or now
    else:
        normalized_data["edited_at"] = existing_chat_message.edited_at

    return normalized_data


def validate_chat_message_references(
    db: Session,
    message_data: dict[str, object],
    allow_locked_chat: bool = False,
) -> None:
    db_game_chat = get_game_chat_or_404(db, message_data["chat_id"])

    allowed_chat_statuses = {"active", "locked"} if allow_locked_chat else {"active"}
    if db_game_chat.chat_status not in allowed_chat_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This game chat cannot receive message changes.",
        )

    if message_data["sender_user_id"] is not None:
        get_active_user_or_404(db, message_data["sender_user_id"], "Sender not found.")

    if message_data["pinned_by_user_id"] is not None:
        get_active_user_or_404(
            db,
            message_data["pinned_by_user_id"],
            "Pinned by user not found.",
        )

    if message_data["deleted_by_user_id"] is not None:
        deleted_by_user = get_active_user_or_404(
            db,
            message_data["deleted_by_user_id"],
            "Deleted by user not found.",
        )

        if (
            message_data["moderation_status"] == "hidden_by_admin"
            and deleted_by_user.role != "admin"
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="hidden_by_admin messages require an admin deleted_by_user_id.",
            )


def validate_chat_message_is_editable(db_chat_message: ChatMessage) -> None:
    if db_chat_message.moderation_status in TERMINAL_MODERATION_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hidden or sender-deleted chat messages cannot be updated.",
        )


# This route creates a message inside an active game chat after validating the
# chat and user references plus pinned/moderation lifecycle fields.
@router.post("", response_model=ChatMessageRead, status_code=status.HTTP_201_CREATED)
def create_chat_message(
    chat_message: ChatMessageCreate,
    current_user: User = Depends(get_current_app_user),
    db: Session = Depends(get_db),
) -> ChatMessage:
    now = datetime.now(timezone.utc)
    message_data = chat_message.model_dump()
    db_game_chat = get_game_chat_or_404(db, message_data["chat_id"])
    db_game = require_chat_member(db, db_game_chat, current_user)

    if message_data["sender_user_id"] not in {None, current_user.id}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="sender_user_id must match the authenticated user.",
        )

    message_data["sender_user_id"] = current_user.id
    message_data["message_body"] = normalize_message_body(message_data["message_body"])
    validate_sender_cooldown(db, db_game_chat.id, current_user.id, now)
    message_data = normalize_chat_message_lifecycle_fields(message_data)
    validate_chat_message_business_rules(message_data)
    validate_chat_message_references(db, message_data)

    new_chat_message = ChatMessage(
        id=uuid.uuid4(),
        **message_data,
    )

    try:
        db.add(new_chat_message)
        db.flush()
        create_or_update_chat_notifications(
            db,
            db_game,
            db_game_chat,
            new_chat_message,
            current_user,
            now,
        )
        mark_chat_read(db, db_game_chat, current_user, now)
        db.commit()
        db.refresh(new_chat_message)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_chat_message_conflict_detail(exc),
        ) from exc

    return new_chat_message


# This route fetches a single chat message by its internal UUID.
@router.get(
    "/{chat_message_id}",
    response_model=ChatMessageRead,
    status_code=status.HTTP_200_OK,
)
def get_chat_message(
    chat_message_id: uuid.UUID,
    current_user: User = Depends(get_current_app_user),
    db: Session = Depends(get_db),
) -> ChatMessage:
    db_chat_message = db.get(ChatMessage, chat_message_id)

    if db_chat_message is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat message not found.",
        )

    db_game_chat = get_game_chat_or_404(db, db_chat_message.chat_id)
    require_chat_member(db, db_game_chat, current_user)

    return db_chat_message


# This route returns chat message records currently stored in the app database.
@router.get("", response_model=list[ChatMessageRead], status_code=status.HTTP_200_OK)
def list_chat_messages(
    chat_id: uuid.UUID | None = None,
    sender_user_id: uuid.UUID | None = None,
    moderation_status: str | None = None,
    is_pinned: bool | None = None,
    limit: int = 50,
    current_user: User = Depends(get_current_app_user),
    db: Session = Depends(get_db),
) -> list[ChatMessage]:
    if chat_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="chat_id is required.",
        )

    db_game_chat = get_game_chat_or_404(db, chat_id)
    require_chat_member(db, db_game_chat, current_user)

    if sender_user_id is None and moderation_status in {None, "visible"} and is_pinned is None:
        return get_latest_visible_messages(db, chat_id, limit)

    statement = select(ChatMessage)

    statement = statement.where(ChatMessage.chat_id == chat_id)

    if sender_user_id is not None:
        statement = statement.where(ChatMessage.sender_user_id == sender_user_id)

    if moderation_status is not None:
        if moderation_status not in VALID_MODERATION_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "moderation_status must be 'visible', 'hidden_by_admin', "
                    "'deleted_by_sender', or 'flagged'."
                ),
            )
        statement = statement.where(ChatMessage.moderation_status == moderation_status)

    if is_pinned is not None:
        statement = statement.where(ChatMessage.is_pinned == is_pinned)

    page_limit = max(1, min(limit, 50))
    chat_messages = db.scalars(
        statement.order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc()).limit(page_limit)
    ).all()
    chat_messages = list(reversed(chat_messages))
    return list(chat_messages)


# This route applies partial updates to an existing chat message while keeping
# edit, pin, and deletion lifecycle timestamps aligned with message state.
@router.patch(
    "/{chat_message_id}",
    response_model=ChatMessageRead,
    status_code=status.HTTP_200_OK,
)
def update_chat_message(
    chat_message_id: uuid.UUID,
    chat_message_update: ChatMessageUpdate,
    current_user: User = Depends(get_current_app_user),
    db: Session = Depends(get_db),
) -> ChatMessage:
    db_chat_message = db.get(ChatMessage, chat_message_id)

    if db_chat_message is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat message not found.",
        )

    validate_chat_message_is_editable(db_chat_message)
    db_game_chat = get_game_chat_or_404(db, db_chat_message.chat_id)
    if current_user.role != "admin":
        require_chat_member(db, db_game_chat, current_user)

        if db_chat_message.sender_user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the sender can update this chat message.",
            )

    update_data = chat_message_update.model_dump(exclude_unset=True)

    if "chat_id" in update_data and update_data["chat_id"] != db_chat_message.chat_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="chat_id cannot be changed for an existing chat message.",
        )

    effective_message_data = {
        "chat_id": db_chat_message.chat_id,
        "sender_user_id": update_data.get(
            "sender_user_id",
            db_chat_message.sender_user_id,
        ),
        "message_type": update_data.get("message_type", db_chat_message.message_type),
        "message_body": update_data.get("message_body", db_chat_message.message_body),
        "is_pinned": update_data.get("is_pinned", db_chat_message.is_pinned),
        "pinned_at": update_data.get("pinned_at", db_chat_message.pinned_at),
        "pinned_by_user_id": update_data.get(
            "pinned_by_user_id",
            db_chat_message.pinned_by_user_id,
        ),
        "moderation_status": update_data.get(
            "moderation_status",
            db_chat_message.moderation_status,
        ),
        "edited_at": update_data.get("edited_at", db_chat_message.edited_at),
        "deleted_at": update_data.get("deleted_at", db_chat_message.deleted_at),
        "deleted_by_user_id": update_data.get(
            "deleted_by_user_id",
            db_chat_message.deleted_by_user_id,
        ),
    }
    effective_message_data = normalize_chat_message_lifecycle_fields(
        effective_message_data,
        db_chat_message,
    )
    validate_chat_message_business_rules(effective_message_data)
    if (
        effective_message_data["moderation_status"] == "hidden_by_admin"
        and current_user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="hidden_by_admin messages require an admin deleted_by_user_id.",
        )

    if (
        effective_message_data["moderation_status"] == "deleted_by_sender"
        and current_user.id != db_chat_message.sender_user_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the sender can delete this chat message.",
        )

    validate_chat_message_references(
        db,
        effective_message_data,
        allow_locked_chat=True,
    )

    # Lifecycle timestamps are derived from the fully merged message state so
    # partial PATCH payloads cannot leave stale timestamps behind.
    update_data["pinned_at"] = effective_message_data["pinned_at"]
    update_data["pinned_by_user_id"] = effective_message_data["pinned_by_user_id"]
    update_data["edited_at"] = effective_message_data["edited_at"]
    update_data["deleted_at"] = effective_message_data["deleted_at"]
    update_data["deleted_by_user_id"] = effective_message_data["deleted_by_user_id"]

    for field_name, field_value in update_data.items():
        setattr(db_chat_message, field_name, field_value)

    db_chat_message.updated_at = datetime.now(timezone.utc)

    try:
        db.add(db_chat_message)
        db.commit()
        db.refresh(db_chat_message)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_chat_message_conflict_detail(exc),
        ) from exc

    return db_chat_message
