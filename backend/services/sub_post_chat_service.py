import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models import (
    Notification,
    SubPost,
    SubPostChat,
    SubPostChatMessage,
    SubPostChatRead,
    SubPostRequest,
    User,
)
from backend.services.need_a_sub_service import (
    build_requester_display,
    get_sub_post_or_404,
)
from backend.services.notification_service import (
    build_need_a_sub_notification_fields,
    reopen_aggregated_notification,
    resolve_aggregated_notification,
)

MAX_SUB_CHAT_MESSAGE_LENGTH = 300
MAX_SUB_CHAT_MESSAGES_PER_PAGE = 50
MAX_SUB_CHAT_MESSAGES_TOTAL = 200
MAX_SUB_CHAT_MESSAGES_PER_MINUTE = 5
SUB_CHAT_ACCESS_GRACE_HOURS = 24
SUB_CHAT_ALLOWED_POST_STATUSES = {"active", "filled", "expired"}
VISIBLE_MESSAGE_STATUSES = {"visible", "flagged"}
NO_LONGER_IN_GAME_LABEL = "No longer in game"


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value


def sub_chat_closes_at(sub_post: SubPost) -> datetime:
    return ensure_aware(sub_post.ends_at) + timedelta(hours=SUB_CHAT_ACCESS_GRACE_HOURS)


def get_sub_post_chat_or_404(db: Session, chat_id: uuid.UUID) -> SubPostChat:
    db_chat = db.get(SubPostChat, chat_id)
    if db_chat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Need a Sub chat not found.",
        )

    return db_chat


def get_sub_post_chat_for_post(
    db: Session,
    sub_post_id: uuid.UUID,
) -> SubPostChat | None:
    return db.scalar(
        select(SubPostChat).where(SubPostChat.sub_post_id == sub_post_id)
    )


def get_or_create_active_sub_post_chat(
    db: Session,
    sub_post: SubPost,
) -> SubPostChat:
    db_chat = get_sub_post_chat_for_post(db, sub_post.id)
    if db_chat is not None:
        return db_chat

    db_chat = SubPostChat(
        id=uuid.uuid4(),
        sub_post_id=sub_post.id,
        chat_status="active",
    )
    db.add(db_chat)
    db.flush()
    return db_chat


def get_sub_post_for_chat(db: Session, db_chat: SubPostChat) -> SubPost:
    return get_sub_post_or_404(db, db_chat.sub_post_id)


def is_confirmed_sub_post_requester(
    db: Session,
    sub_post_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    return (
        db.scalar(
            select(SubPostRequest.id).where(
                SubPostRequest.sub_post_id == sub_post_id,
                SubPostRequest.requester_user_id == user_id,
                SubPostRequest.request_status == "confirmed",
            )
        )
        is not None
    )


def is_sub_post_chat_member(
    db: Session,
    sub_post: SubPost,
    user_id: uuid.UUID,
) -> bool:
    if sub_post.owner_user_id == user_id:
        return True

    return is_confirmed_sub_post_requester(db, sub_post.id, user_id)


def validate_sub_post_chat_access(
    db: Session,
    sub_post: SubPost,
    user: User,
) -> None:
    if sub_post.post_status not in SUB_CHAT_ALLOWED_POST_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This Need a Sub chat is not available.",
        )

    if now_utc() > sub_chat_closes_at(sub_post):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This Need a Sub chat is closed.",
        )

    if not is_sub_post_chat_member(db, sub_post, user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the post owner and confirmed players can use this chat.",
        )


def require_sub_post_chat_member(
    db: Session,
    db_chat: SubPostChat,
    user: User,
) -> SubPost:
    sub_post = get_sub_post_for_chat(db, db_chat)
    validate_sub_post_chat_access(db, sub_post, user)
    return sub_post


def require_sub_post_chat_can_write(
    db: Session,
    db_chat: SubPostChat,
    user: User,
) -> SubPost:
    if db_chat.chat_status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This Need a Sub chat cannot receive messages.",
        )

    return require_sub_post_chat_member(db, db_chat, user)


def list_sub_post_chat_member_user_ids(
    db: Session,
    sub_post: SubPost,
    exclude_user_id: uuid.UUID | None = None,
) -> list[uuid.UUID]:
    member_user_ids = [sub_post.owner_user_id]
    confirmed_user_ids = db.scalars(
        select(SubPostRequest.requester_user_id).where(
            SubPostRequest.sub_post_id == sub_post.id,
            SubPostRequest.request_status == "confirmed",
        )
    ).all()
    member_user_ids.extend(confirmed_user_ids)

    unique_user_ids: list[uuid.UUID] = []
    seen_user_ids: set[uuid.UUID] = set()
    for user_id in member_user_ids:
        if user_id == exclude_user_id or user_id in seen_user_ids:
            continue
        seen_user_ids.add(user_id)
        unique_user_ids.append(user_id)

    return unique_user_ids


def build_sender_snapshot(user: User) -> tuple[str, str]:
    display_name, initials = build_requester_display(user)
    return display_name or "Pickup Lane Player", initials or "PL"


def normalize_message_body(message_body: str) -> str:
    normalized = " ".join(message_body.strip().split())
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="message_body must not be empty.",
        )

    if len(normalized) > MAX_SUB_CHAT_MESSAGE_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Need a Sub chat messages must be "
                f"{MAX_SUB_CHAT_MESSAGE_LENGTH} characters or fewer."
            ),
        )

    return normalized


def validate_sender_rate_limit(
    db: Session,
    chat_id: uuid.UUID,
    sender_user_id: uuid.UUID,
    current_time: datetime,
) -> None:
    window_start = ensure_aware(current_time) - timedelta(minutes=1)
    message_count = db.scalar(
        select(func.count())
        .select_from(SubPostChatMessage)
        .where(
            SubPostChatMessage.chat_id == chat_id,
            SubPostChatMessage.sender_user_id == sender_user_id,
            SubPostChatMessage.message_type == "text",
            SubPostChatMessage.moderation_status.in_(VISIBLE_MESSAGE_STATUSES),
            SubPostChatMessage.created_at >= window_start,
        )
    ) or 0

    if message_count >= MAX_SUB_CHAT_MESSAGES_PER_MINUTE:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Slow down before sending another Need a Sub chat message.",
        )


def validate_total_message_limit(db: Session, chat_id: uuid.UUID) -> None:
    message_count = db.scalar(
        select(func.count())
        .select_from(SubPostChatMessage)
        .where(
            SubPostChatMessage.chat_id == chat_id,
            SubPostChatMessage.message_type == "text",
            SubPostChatMessage.moderation_status.in_(VISIBLE_MESSAGE_STATUSES),
        )
    ) or 0

    if message_count >= MAX_SUB_CHAT_MESSAGES_TOTAL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This Need a Sub chat has reached its message limit.",
        )


def get_latest_visible_sub_chat_messages(
    db: Session,
    chat_id: uuid.UUID,
    *,
    limit: int = MAX_SUB_CHAT_MESSAGES_PER_PAGE,
    before_created_at: datetime | None = None,
) -> list[SubPostChatMessage]:
    page_limit = max(1, min(limit, MAX_SUB_CHAT_MESSAGES_PER_PAGE))
    statement = select(SubPostChatMessage).where(
        SubPostChatMessage.chat_id == chat_id,
        SubPostChatMessage.moderation_status.in_(VISIBLE_MESSAGE_STATUSES),
    )

    if before_created_at is not None:
        statement = statement.where(
            SubPostChatMessage.created_at < ensure_aware(before_created_at)
        )

    messages = db.scalars(
        statement.order_by(
            SubPostChatMessage.created_at.desc(),
            SubPostChatMessage.id.desc(),
        ).limit(page_limit)
    ).all()

    return list(reversed(messages))


def get_latest_visible_sub_chat_message(
    db: Session,
    chat_id: uuid.UUID,
) -> SubPostChatMessage | None:
    return db.scalar(
        select(SubPostChatMessage)
        .where(
            SubPostChatMessage.chat_id == chat_id,
            SubPostChatMessage.moderation_status.in_(VISIBLE_MESSAGE_STATUSES),
        )
        .order_by(SubPostChatMessage.created_at.desc(), SubPostChatMessage.id.desc())
        .limit(1)
    )


def count_unread_sub_chat_messages(
    db: Session,
    chat_id: uuid.UUID,
    user: User,
    read_state: SubPostChatRead | None,
) -> int:
    statement = (
        select(func.count())
        .select_from(SubPostChatMessage)
        .where(
            SubPostChatMessage.chat_id == chat_id,
            SubPostChatMessage.moderation_status.in_(VISIBLE_MESSAGE_STATUSES),
            SubPostChatMessage.sender_user_id != user.id,
        )
    )

    if read_state is not None:
        statement = statement.where(
            SubPostChatMessage.created_at > ensure_aware(read_state.last_read_at)
        )

    return db.scalar(statement) or 0


def get_sub_chat_read_state(
    db: Session,
    db_chat: SubPostChat,
    user: User,
) -> tuple[SubPostChatRead | None, int]:
    read_state = db.scalar(
        select(SubPostChatRead).where(
            SubPostChatRead.chat_id == db_chat.id,
            SubPostChatRead.user_id == user.id,
        )
    )
    unread_count = count_unread_sub_chat_messages(db, db_chat.id, user, read_state)
    return read_state, unread_count


def sub_chat_message_aggregation_key(
    sub_post_id: uuid.UUID,
    chat_id: uuid.UUID,
    recipient_user_id: uuid.UUID,
) -> str:
    return (
        f"need_a_sub:post:{sub_post_id}:chat:{chat_id}:"
        f"user:{recipient_user_id}:sub_chat_message"
    )


def mark_sub_chat_notifications_read(
    db: Session,
    *,
    sub_post_id: uuid.UUID,
    chat_id: uuid.UUID,
    user_id: uuid.UUID,
    read_at: datetime,
) -> None:
    resolve_aggregated_notification(
        db,
        user_id=user_id,
        aggregation_key=sub_chat_message_aggregation_key(
            sub_post_id,
            chat_id,
            user_id,
        ),
        values={"aggregate_count": None},
        read_at=read_at,
    )


def mark_sub_chat_read(
    db: Session,
    db_chat: SubPostChat,
    user: User,
    read_at: datetime | None = None,
) -> SubPostChatRead:
    effective_read_at = read_at or now_utc()
    latest_message = get_latest_visible_sub_chat_message(db, db_chat.id)
    read_state = db.scalar(
        select(SubPostChatRead).where(
            SubPostChatRead.chat_id == db_chat.id,
            SubPostChatRead.user_id == user.id,
        )
    )

    if read_state is None:
        read_state = SubPostChatRead(
            id=uuid.uuid4(),
            chat_id=db_chat.id,
            user_id=user.id,
            last_read_at=effective_read_at,
            last_read_message_id=latest_message.id if latest_message else None,
        )
        db.add(read_state)
    else:
        read_state.last_read_at = effective_read_at
        read_state.last_read_message_id = latest_message.id if latest_message else None
        read_state.updated_at = effective_read_at
        db.add(read_state)

    mark_sub_chat_notifications_read(
        db,
        sub_post_id=db_chat.sub_post_id,
        chat_id=db_chat.id,
        user_id=user.id,
        read_at=effective_read_at,
    )
    return read_state


def create_or_update_sub_chat_notifications(
    db: Session,
    *,
    sub_post: SubPost,
    db_chat: SubPostChat,
    message: SubPostChatMessage,
    sender: User,
    event_at: datetime,
) -> None:
    recipient_user_ids = list_sub_post_chat_member_user_ids(
        db,
        sub_post,
        exclude_user_id=sender.id,
    )

    for recipient_user_id in recipient_user_ids:
        aggregation_key = sub_chat_message_aggregation_key(
            sub_post.id,
            db_chat.id,
            recipient_user_id,
        )
        notification_fields = build_need_a_sub_notification_fields(
            sub_post,
            "sub_chat_message",
            event_at=event_at,
            aggregation_key=aggregation_key,
        )
        notification_fields.update(
            {
                "actor_user_id": sender.id,
                "related_sub_post_id": sub_post.id,
                "related_sub_post_chat_id": db_chat.id,
                "related_sub_post_chat_message_id": message.id,
            }
        )
        reopen_aggregated_notification(
            db,
            user_id=recipient_user_id,
            notification_type="sub_chat_message",
            notification_category="game_activity",
            notification_domain="need_a_sub",
            aggregation_key=aggregation_key,
            values=notification_fields,
            aggregate_count_mode="increment",
        )


def resolve_sub_chat_notifications_for_user(
    db: Session,
    *,
    sub_post_id: uuid.UUID,
    user_id: uuid.UUID,
    read_at: datetime | None = None,
) -> None:
    db_chat = get_sub_post_chat_for_post(db, sub_post_id)
    if db_chat is None:
        return

    mark_sub_chat_notifications_read(
        db,
        sub_post_id=sub_post_id,
        chat_id=db_chat.id,
        user_id=user_id,
        read_at=read_at or now_utc(),
    )


def resolve_sub_chat_notifications_for_post(
    db: Session,
    *,
    sub_post_id: uuid.UUID,
    read_at: datetime | None = None,
) -> None:
    effective_read_at = read_at or now_utc()
    db_chat = get_sub_post_chat_for_post(db, sub_post_id)
    if db_chat is None:
        return

    notifications = db.scalars(
        select(Notification).where(
            Notification.related_sub_post_chat_id == db_chat.id,
            Notification.notification_type == "sub_chat_message",
        )
    ).all()
    for notification in notifications:
        notification.is_read = True
        if notification.read_at is None:
            notification.read_at = effective_read_at
        notification.aggregate_count = None
        notification.updated_at = effective_read_at
        db.add(notification)


def sender_is_current_sub_chat_member(
    db: Session,
    sub_post: SubPost,
    sender_user_id: uuid.UUID | None,
) -> bool:
    if sender_user_id is None:
        return False

    return is_sub_post_chat_member(db, sub_post, sender_user_id)


def serialize_sub_chat_message(
    db: Session,
    message: SubPostChatMessage,
    sub_post: SubPost,
) -> dict[str, object]:
    is_current_member = sender_is_current_sub_chat_member(
        db,
        sub_post,
        message.sender_user_id,
    )
    return {
        "id": message.id,
        "chat_id": message.chat_id,
        "sender_user_id": message.sender_user_id,
        "sender_display_name_snapshot": message.sender_display_name_snapshot,
        "sender_initials_snapshot": message.sender_initials_snapshot,
        "sender_is_current_chat_member": is_current_member,
        "sender_status_label": None if is_current_member else NO_LONGER_IN_GAME_LABEL,
        "message_type": message.message_type,
        "message_body": message.message_body,
        "moderation_status": message.moderation_status,
        "created_at": message.created_at,
        "updated_at": message.updated_at,
        "edited_at": message.edited_at,
        "deleted_at": message.deleted_at,
        "deleted_by_user_id": message.deleted_by_user_id,
    }
