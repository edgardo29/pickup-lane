import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models import (
    ChatMessage,
    Game,
    GameChat,
    GameChatRead,
    GameParticipant,
    Notification,
    User,
)

CHAT_MEMBER_STATUSES = {"confirmed"}
CHAT_MEMBER_TYPES = {"host", "registered_user", "admin_added"}
CHAT_CREATABLE_GAME_STATUSES = {"scheduled", "full"}
MAX_CHAT_MESSAGE_LENGTH = 300
MAX_CHAT_MESSAGES_PER_PAGE = 50
MESSAGE_COOLDOWN_SECONDS = 2


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
    notifications = db.scalars(
        select(Notification).where(
            Notification.user_id == user_id,
            Notification.notification_type == "chat_message",
            Notification.related_game_id == game_chat.game_id,
            Notification.related_chat_id == game_chat.id,
            Notification.is_read.is_(False),
        )
    ).all()

    for notification in notifications:
        notification.is_read = True
        notification.read_at = now
        notification.updated_at = now
        db.add(notification)


def create_or_update_chat_notifications(
    db: Session,
    db_game: Game,
    game_chat: GameChat,
    chat_message: ChatMessage,
    sender_user: User,
    now: datetime,
) -> None:
    game_title = db_game.title or db_game.venue_name_snapshot or "your game"
    recipient_user_ids = list_chat_member_user_ids(db, db_game, exclude_user_id=sender_user.id)

    for recipient_user_id in recipient_user_ids:
        existing_notification = db.scalar(
            select(Notification)
            .where(
                Notification.user_id == recipient_user_id,
                Notification.notification_type == "chat_message",
                Notification.related_game_id == db_game.id,
                Notification.related_chat_id == game_chat.id,
                Notification.is_read.is_(False),
            )
            .order_by(Notification.created_at.desc())
            .limit(1)
        )

        if existing_notification is not None:
            existing_notification.title = "New game chat messages"
            existing_notification.body = f"New messages in {game_title}."
            existing_notification.related_message_id = chat_message.id
            existing_notification.updated_at = now
            db.add(existing_notification)
            continue

        db.add(
            Notification(
                id=uuid.uuid4(),
                user_id=recipient_user_id,
                notification_type="chat_message",
                title="New game chat message",
                body=f"New messages in {game_title}.",
                related_game_id=db_game.id,
                related_chat_id=game_chat.id,
                related_message_id=chat_message.id,
                is_read=False,
                read_at=None,
                created_at=now,
                updated_at=now,
            )
        )


def ensure_timezone(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value
