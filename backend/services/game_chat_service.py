import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import (
    ChatMessage,
    Game,
    GameChat,
    GameChatRead,
    GameParticipant,
    User,
)
from backend.schemas.chat_message_schema import ChatMessageCreate, ChatMessageUpdate
from backend.schemas.game_chat_schema import GameChatCreate, GameChatUpdate
from backend.services.admin_action_service import record_admin_action
from backend.services.admin_permission_service import (
    PERMISSION_CONTENT_MODERATE,
    user_has_admin_permission,
)
from backend.services.notification_service import (
    build_game_notification_fields,
    reopen_aggregated_notification,
    resolve_aggregated_notification,
)

CHAT_MEMBER_STATUSES = {"confirmed"}
CHAT_MEMBER_TYPES = {"host", "registered_user", "admin_added"}
VALID_CHAT_STATUSES = {"active", "locked", "archived"}
CHAT_CREATABLE_GAME_STATUSES = {"scheduled", "full"}
TERMINAL_CHAT_STATUSES = {"archived"}
MAX_CHAT_MESSAGE_LENGTH = 300
MAX_CHAT_MESSAGES_PER_PAGE = 50
MESSAGE_COOLDOWN_SECONDS = 2
VALID_MODERATION_STATUSES = {
    "visible",
    "hidden_by_admin",
    "deleted_by_sender",
    "flagged",
}
TERMINAL_MODERATION_STATUSES = {"hidden_by_admin", "deleted_by_sender"}
SENDER_BODY_UPDATE_FIELDS = {"message_body"}
SENDER_DELETE_UPDATE_FIELDS = {"moderation_status"}
MODERATOR_HIDE_UPDATE_FIELDS = {"moderation_status", "reason"}


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


def create_game_chat_record(
    db: Session,
    game_chat: GameChatCreate,
    current_admin: User,
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
        db.flush()
        record_admin_action(
            db,
            admin_user_id=current_admin.id,
            action_type="create_game_chat",
            target_game_id=new_game_chat.game_id,
            metadata={
                "after": {
                    "chat_id": str(new_game_chat.id),
                    "chat_status": new_game_chat.chat_status,
                }
            },
        )
        db.commit()
        db.refresh(new_game_chat)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_game_chat_conflict_detail(exc),
        ) from exc

    return new_game_chat


def list_game_chat_records(
    db: Session,
    *,
    game_id: uuid.UUID | None = None,
    chat_status: str | None = None,
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


def update_game_chat_record(
    db: Session,
    game_chat_id: uuid.UUID,
    game_chat_update: GameChatUpdate,
    current_admin: User,
) -> GameChat:
    db_game_chat = get_game_chat_or_404(db, game_chat_id)
    validate_game_chat_is_editable(db_game_chat)
    update_data = game_chat_update.model_dump(exclude_unset=True)
    before_state = {
        "chat_id": str(db_game_chat.id),
        "chat_status": db_game_chat.chat_status,
        "locked_at": (
            db_game_chat.locked_at.isoformat()
            if db_game_chat.locked_at is not None
            else None
        ),
    }

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
    update_data["locked_at"] = effective_chat_data["locked_at"]

    for field_name, field_value in update_data.items():
        setattr(db_game_chat, field_name, field_value)

    db_game_chat.updated_at = datetime.now(timezone.utc)

    try:
        db.add(db_game_chat)
        db.flush()
        record_admin_action(
            db,
            admin_user_id=current_admin.id,
            action_type="update_game_chat",
            target_game_id=db_game_chat.game_id,
            metadata={
                "before": before_state,
                "after": {
                    "chat_id": str(db_game_chat.id),
                    "chat_status": db_game_chat.chat_status,
                    "locked_at": (
                        db_game_chat.locked_at.isoformat()
                        if db_game_chat.locked_at is not None
                        else None
                    ),
                },
            },
        )
        db.commit()
        db.refresh(db_game_chat)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_game_chat_conflict_detail(exc),
        ) from exc

    return db_game_chat


def get_game_chat_or_404(db: Session, chat_id: uuid.UUID) -> GameChat:
    db_game_chat = db.get(GameChat, chat_id)

    if db_game_chat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game chat not found.",
        )

    return db_game_chat


def get_chat_game_or_404(db: Session, game_chat: GameChat) -> Game:
    db_game = db.get(Game, game_chat.game_id)

    if db_game is None or db_game.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found.",
        )

    return db_game


def get_or_create_active_game_chat(db: Session, db_game: Game) -> GameChat:
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

    existing_chat = db.scalar(
        select(GameChat).where(
            GameChat.game_id == db_game.id,
            GameChat.chat_status == "active",
        )
    )

    if existing_chat is not None:
        return existing_chat

    new_chat = GameChat(
        id=uuid.uuid4(),
        game_id=db_game.id,
        chat_status="active",
    )
    db.add(new_chat)
    db.flush()
    return new_chat


def require_chat_member(db: Session, game_chat: GameChat, user: User) -> Game:
    db_game = get_chat_game_or_404(db, game_chat)

    if not db_game.is_chat_enabled or game_chat.chat_status == "archived":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This game chat is not available.",
        )

    if is_chat_member(db, db_game, user.id):
        return db_game

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Only confirmed players and the host can use game chat.",
    )


def is_chat_member(db: Session, db_game: Game, user_id: uuid.UUID) -> bool:
    if db_game.host_user_id == user_id:
        return True

    participant = db.scalar(
        select(GameParticipant.id).where(
            GameParticipant.game_id == db_game.id,
            GameParticipant.user_id == user_id,
            GameParticipant.participant_type.in_(CHAT_MEMBER_TYPES),
            GameParticipant.participant_status.in_(CHAT_MEMBER_STATUSES),
        )
    )

    return participant is not None


def list_chat_member_user_ids(
    db: Session,
    db_game: Game,
    exclude_user_id: uuid.UUID | None = None,
) -> list[uuid.UUID]:
    user_ids = set()

    if db_game.host_user_id is not None:
        user_ids.add(db_game.host_user_id)

    participant_user_ids = db.scalars(
        select(GameParticipant.user_id).where(
            GameParticipant.game_id == db_game.id,
            GameParticipant.user_id.is_not(None),
            GameParticipant.participant_type.in_(CHAT_MEMBER_TYPES),
            GameParticipant.participant_status.in_(CHAT_MEMBER_STATUSES),
        )
    ).all()
    user_ids.update(user_id for user_id in participant_user_ids if user_id is not None)

    if exclude_user_id is not None:
        user_ids.discard(exclude_user_id)

    return list(user_ids)


def chat_message_aggregation_key(
    game_id: uuid.UUID,
    chat_id: uuid.UUID,
    recipient_user_id: uuid.UUID,
) -> str:
    return f"game:{game_id}:chat:{chat_id}:user:{recipient_user_id}:chat_message"


def normalize_message_body(message_body: str) -> str:
    normalized_body = " ".join(message_body.strip().split())

    if not normalized_body:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="message_body must not be empty.",
        )

    if len(normalized_body) > MAX_CHAT_MESSAGE_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"message_body must be {MAX_CHAT_MESSAGE_LENGTH} characters or fewer.",
        )

    return normalized_body


def validate_sender_cooldown(
    db: Session,
    chat_id: uuid.UUID,
    sender_user_id: uuid.UUID,
    now: datetime,
) -> None:
    latest_sent_at = db.scalar(
        select(ChatMessage.created_at)
        .where(
            ChatMessage.chat_id == chat_id,
            ChatMessage.sender_user_id == sender_user_id,
            ChatMessage.message_type == "text",
        )
        .order_by(ChatMessage.created_at.desc())
        .limit(1)
    )

    if latest_sent_at is None:
        return

    latest_sent_at = ensure_timezone(latest_sent_at)
    if now - latest_sent_at < timedelta(seconds=MESSAGE_COOLDOWN_SECONDS):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Please wait a moment before sending another message.",
        )


def get_latest_visible_messages(
    db: Session,
    chat_id: uuid.UUID,
    limit: int = MAX_CHAT_MESSAGES_PER_PAGE,
) -> list[ChatMessage]:
    page_limit = max(1, min(limit, MAX_CHAT_MESSAGES_PER_PAGE))
    messages = db.scalars(
        select(ChatMessage)
        .where(
            ChatMessage.chat_id == chat_id,
            ChatMessage.moderation_status == "visible",
        )
        .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
        .limit(page_limit)
    ).all()

    return list(reversed(messages))


def get_chat_read_state(
    db: Session,
    game_chat: GameChat,
    user: User,
) -> tuple[GameChatRead | None, int]:
    read_state = db.scalar(
        select(GameChatRead).where(
            GameChatRead.chat_id == game_chat.id,
            GameChatRead.user_id == user.id,
        )
    )

    unread_count = count_unread_messages(db, game_chat.id, user.id, read_state)
    return read_state, unread_count


def count_unread_messages(
    db: Session,
    chat_id: uuid.UUID,
    user_id: uuid.UUID,
    read_state: GameChatRead | None,
) -> int:
    statement = select(func.count(ChatMessage.id)).where(
        ChatMessage.chat_id == chat_id,
        ChatMessage.moderation_status == "visible",
        ChatMessage.sender_user_id != user_id,
    )

    if read_state is not None:
        statement = statement.where(
            ChatMessage.created_at > ensure_timezone(read_state.last_read_at)
        )

    return int(db.scalar(statement) or 0)


def mark_chat_read(
    db: Session,
    game_chat: GameChat,
    user: User,
    now: datetime | None = None,
) -> GameChatRead:
    effective_now = now or datetime.now(timezone.utc)
    last_message_id = db.scalar(
        select(ChatMessage.id)
        .where(
            ChatMessage.chat_id == game_chat.id,
            ChatMessage.moderation_status == "visible",
        )
        .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
        .limit(1)
    )
    read_state = db.scalar(
        select(GameChatRead).where(
            GameChatRead.chat_id == game_chat.id,
            GameChatRead.user_id == user.id,
        )
    )

    if read_state is None:
        read_state = GameChatRead(
            id=uuid.uuid4(),
            chat_id=game_chat.id,
            user_id=user.id,
            last_read_at=effective_now,
            last_read_message_id=last_message_id,
            created_at=effective_now,
            updated_at=effective_now,
        )
    else:
        read_state.last_read_at = effective_now
        read_state.last_read_message_id = last_message_id
        read_state.updated_at = effective_now

    db.add(read_state)
    mark_chat_notifications_read(db, game_chat, user.id, effective_now)
    return read_state


def mark_chat_notifications_read(
    db: Session,
    game_chat: GameChat,
    user_id: uuid.UUID,
    now: datetime,
) -> None:
    resolve_aggregated_notification(
        db,
        user_id=user_id,
        aggregation_key=chat_message_aggregation_key(
            game_chat.game_id,
            game_chat.id,
            user_id,
        ),
        values={"aggregate_count": None},
        read_at=now,
    )


def create_or_update_chat_notifications(
    db: Session,
    db_game: Game,
    game_chat: GameChat,
    chat_message: ChatMessage,
    sender_user: User,
    now: datetime,
) -> None:
    recipient_user_ids = list_chat_member_user_ids(
        db,
        db_game,
        exclude_user_id=sender_user.id,
    )

    for recipient_user_id in recipient_user_ids:
        aggregation_key = chat_message_aggregation_key(
            db_game.id,
            game_chat.id,
            recipient_user_id,
        )
        notification_fields = build_game_notification_fields(
            db_game,
            "chat_message",
            event_at=now,
            aggregation_key=aggregation_key,
        )
        notification_fields.update(
            {
                "actor_user_id": sender_user.id,
                "related_game_id": db_game.id,
                "related_chat_id": game_chat.id,
                "related_message_id": chat_message.id,
            }
        )
        reopen_aggregated_notification(
            db,
            user_id=recipient_user_id,
            notification_type="chat_message",
            notification_category="game_activity",
            notification_domain="game",
            aggregation_key=aggregation_key,
            values=notification_fields,
            aggregate_count_mode="increment",
        )


def ensure_timezone(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value


def build_chat_message_conflict_detail(exc: IntegrityError) -> str:
    return str(exc.orig)


def get_chat_message_or_404(
    db: Session,
    chat_message_id: uuid.UUID,
) -> ChatMessage:
    db_chat_message = db.get(ChatMessage, chat_message_id)

    if db_chat_message is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat message not found.",
        )

    return db_chat_message


def can_moderate_chat_messages(user: User) -> bool:
    return user_has_admin_permission(user, PERMISSION_CONTENT_MODERATE)


def validate_chat_message_is_editable(db_chat_message: ChatMessage) -> None:
    if db_chat_message.moderation_status in TERMINAL_MODERATION_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hidden or sender-deleted chat messages cannot be updated.",
        )


def create_chat_message_record(
    db: Session,
    chat_message: ChatMessageCreate,
    current_user: User,
) -> ChatMessage:
    now = datetime.now(timezone.utc)
    message_data = chat_message.model_dump()
    db_game_chat = get_game_chat_or_404(db, message_data["chat_id"])
    db_game = require_chat_member(db, db_game_chat, current_user)
    if db_game_chat.chat_status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This game chat cannot receive message changes.",
        )

    message_data["message_body"] = normalize_message_body(message_data["message_body"])
    validate_sender_cooldown(db, db_game_chat.id, current_user.id, now)

    new_chat_message = ChatMessage(
        id=uuid.uuid4(),
        sender_user_id=current_user.id,
        message_type="text",
        is_pinned=False,
        moderation_status="visible",
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


def get_chat_message_record(
    db: Session,
    chat_message_id: uuid.UUID,
    current_user: User,
) -> ChatMessage:
    db_chat_message = get_chat_message_or_404(db, chat_message_id)
    db_game_chat = get_game_chat_or_404(db, db_chat_message.chat_id)

    if can_moderate_chat_messages(current_user):
        return db_chat_message

    require_chat_member(db, db_game_chat, current_user)
    if db_chat_message.moderation_status != "visible":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat message not found.",
        )

    return db_chat_message


def list_chat_message_records(
    db: Session,
    current_user: User,
    *,
    chat_id: uuid.UUID | None = None,
    sender_user_id: uuid.UUID | None = None,
    moderation_status: str | None = None,
    is_pinned: bool | None = None,
    after_created_at: datetime | None = None,
    limit: int = MAX_CHAT_MESSAGES_PER_PAGE,
) -> list[ChatMessage]:
    if chat_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="chat_id is required.",
        )

    db_game_chat = get_game_chat_or_404(db, chat_id)
    is_moderator = can_moderate_chat_messages(current_user)
    if not is_moderator:
        require_chat_member(db, db_game_chat, current_user)
        if moderation_status not in {None, "visible"}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Content moderation permission required.",
            )

    if moderation_status is not None and moderation_status not in VALID_MODERATION_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "moderation_status must be 'visible', 'hidden_by_admin', "
                "'deleted_by_sender', or 'flagged'."
            ),
        )

    if (
        not is_moderator
        and sender_user_id is None
        and moderation_status in {None, "visible"}
        and is_pinned is None
        and after_created_at is None
    ):
        return get_latest_visible_messages(db, chat_id, limit)

    statement = select(ChatMessage).where(ChatMessage.chat_id == chat_id)

    if not is_moderator:
        statement = statement.where(ChatMessage.moderation_status == "visible")
    elif moderation_status is not None:
        statement = statement.where(
            ChatMessage.moderation_status == moderation_status
        )

    if after_created_at is not None:
        statement = statement.where(ChatMessage.created_at > after_created_at)

    if sender_user_id is not None:
        statement = statement.where(ChatMessage.sender_user_id == sender_user_id)

    if is_pinned is not None:
        statement = statement.where(ChatMessage.is_pinned == is_pinned)

    page_limit = max(1, min(limit, MAX_CHAT_MESSAGES_PER_PAGE))
    chat_messages = db.scalars(
        statement.order_by(
            ChatMessage.created_at.desc(),
            ChatMessage.id.desc(),
        ).limit(page_limit)
    ).all()
    return list(reversed(chat_messages))


def update_chat_message_record(
    db: Session,
    chat_message_id: uuid.UUID,
    chat_message_update: ChatMessageUpdate,
    current_user: User,
) -> ChatMessage:
    db_chat_message = get_chat_message_or_404(db, chat_message_id)
    validate_chat_message_is_editable(db_chat_message)
    update_data = chat_message_update.model_dump(exclude_unset=True)

    if update_data.get("moderation_status") == "hidden_by_admin":
        return hide_chat_message_record(
            db,
            db_chat_message,
            update_data,
            current_user,
        )

    return update_sender_chat_message_record(
        db,
        db_chat_message,
        update_data,
        current_user,
    )


def hide_chat_message_record(
    db: Session,
    db_chat_message: ChatMessage,
    update_data: dict[str, Any],
    current_user: User,
) -> ChatMessage:
    if not can_moderate_chat_messages(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Content moderation permission required.",
        )

    if set(update_data) - MODERATOR_HIDE_UPDATE_FIELDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Moderators can only hide a message and provide a reason.",
        )

    reason = update_data.get("reason")
    if reason is None or not reason.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="reason is required.",
        )

    db_game_chat = get_game_chat_or_404(db, db_chat_message.chat_id)
    if db_game_chat.chat_status == "archived":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This game chat cannot receive message changes.",
        )
    now = datetime.now(timezone.utc)
    old_status = db_chat_message.moderation_status
    db_chat_message.moderation_status = "hidden_by_admin"
    db_chat_message.deleted_by_user_id = current_user.id
    db_chat_message.deleted_at = now
    db_chat_message.updated_at = now

    try:
        db.add(db_chat_message)
        db.flush()
        record_admin_action(
            db,
            admin_user_id=current_user.id,
            action_type="hide_chat_message",
            target_user_id=db_chat_message.sender_user_id,
            target_game_id=db_game_chat.game_id,
            target_message_id=db_chat_message.id,
            reason=reason,
            metadata={
                "old_status": old_status,
                "new_status": db_chat_message.moderation_status,
                "hidden_by": str(current_user.id),
            },
        )
        db.commit()
        db.refresh(db_chat_message)
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_chat_message_conflict_detail(exc),
        ) from exc

    return db_chat_message


def update_sender_chat_message_record(
    db: Session,
    db_chat_message: ChatMessage,
    update_data: dict[str, Any],
    current_user: User,
) -> ChatMessage:
    db_game_chat = get_game_chat_or_404(db, db_chat_message.chat_id)
    require_chat_member(db, db_game_chat, current_user)

    if db_chat_message.sender_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the sender can update this chat message.",
        )

    update_fields = set(update_data)
    is_body_update = (
        update_fields == SENDER_BODY_UPDATE_FIELDS
        and update_data.get("message_body") is not None
    )
    is_sender_delete = (
        update_fields == SENDER_DELETE_UPDATE_FIELDS
        and update_data.get("moderation_status") == "deleted_by_sender"
    )
    if not is_body_update and not is_sender_delete:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Senders can only edit message_body or delete their own message.",
        )

    now = datetime.now(timezone.utc)
    if is_body_update:
        db_chat_message.message_body = normalize_message_body(
            update_data["message_body"]
        )
        db_chat_message.edited_at = now
    else:
        db_chat_message.moderation_status = "deleted_by_sender"
        db_chat_message.deleted_by_user_id = current_user.id
        db_chat_message.deleted_at = now

    db_chat_message.updated_at = now

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
