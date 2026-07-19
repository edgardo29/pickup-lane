import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import (
    Notification,
    SubPost,
    SubPostChat,
    SubPostChatMessageDetection,
    SubPostChatMessage,
    SubPostChatRead,
    SubPostRequest,
    User,
)
from backend.schemas.sub_post_chat_message_schema import (
    SubPostChatMessageCreate,
)
from backend.schemas.sub_post_chat_read_schema import (
    SubPostChatReadStateRead as SubPostChatReadStateReadSchema,
)
from backend.schemas.sub_post_chat_schema import (
    SubPostChatEnsureCreate,
    SubPostChatRead as SubPostChatReadSchema,
)
from backend.services.notification_event_service import (
    build_need_a_sub_notification_fields,
    reopen_aggregated_notification,
    resolve_aggregated_notification,
)
from backend.services.chat_moderation_service import (
    build_safe_message_preview,
    detect_chat_message,
)
from backend.services.moderation_surfacing_service import (
    surface_need_a_sub_chat_message_text,
)
from backend.services.need_a_sub_rules import CHAT_ALLOWED_POST_STATUSES

logger = logging.getLogger(__name__)

MAX_SUB_CHAT_MESSAGE_LENGTH = 300
MAX_SUB_CHAT_MESSAGES_PER_PAGE = 50
MAX_SUB_CHAT_MESSAGES_TOTAL = 200
MAX_SUB_CHAT_MESSAGES_PER_MINUTE = 5
SUB_CHAT_ACCESS_GRACE_HOURS = 24
VISIBLE_MESSAGE_STATUS = "visible"
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


def get_sub_post_or_404(
    db: Session,
    sub_post_id: uuid.UUID,
    *,
    lock_for_update: bool = False,
) -> SubPost:
    if lock_for_update:
        sub_post = db.scalar(
            select(SubPost)
            .where(SubPost.id == sub_post_id)
            .with_for_update()
        )
    else:
        sub_post = db.get(SubPost, sub_post_id)

    if sub_post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Need a Sub post not found.",
        )

    return sub_post


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


def close_sub_post_chat_for_post(
    db: Session,
    *,
    sub_post_id: uuid.UUID,
    closed_at: datetime,
) -> None:
    db_chat = get_sub_post_chat_for_post(db, sub_post_id)
    if db_chat is None:
        return

    db_chat.chat_status = "closed"
    db_chat.closed_at = db_chat.closed_at or closed_at
    db_chat.updated_at = closed_at
    db.add(db_chat)


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


def is_current_or_former_confirmed_sub_post_requester(
    db: Session,
    sub_post_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    return (
        db.scalar(
            select(SubPostRequest.id).where(
                SubPostRequest.sub_post_id == sub_post_id,
                SubPostRequest.requester_user_id == user_id,
                SubPostRequest.confirmed_at.is_not(None),
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


def is_sub_post_chat_write_participant(
    db: Session,
    sub_post: SubPost,
    user_id: uuid.UUID,
) -> bool:
    if sub_post.owner_user_id == user_id:
        return True

    return is_current_or_former_confirmed_sub_post_requester(
        db,
        sub_post.id,
        user_id,
    )


def validate_sub_post_chat_access(
    db: Session,
    sub_post: SubPost,
    user: User,
) -> None:
    if sub_post.post_status not in CHAT_ALLOWED_POST_STATUSES:
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
    sub_post = get_sub_post_for_chat(db, db_chat)
    if not is_sub_post_chat_write_participant(db, sub_post, user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the post owner and confirmed players can use this chat.",
        )

    if db_chat.chat_status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This Need a Sub chat cannot receive messages.",
        )

    validate_sub_post_chat_access(db, sub_post, user)
    return sub_post


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
    name_parts = [
        value.strip()
        for value in [user.first_name or "", user.last_name or ""]
        if value and value.strip()
    ]
    display_name = " ".join(name_parts) if name_parts else "Pickup Lane Player"
    initials_source = name_parts if name_parts else ["Pickup", "Lane"]
    initials = "".join(part[:1].upper() for part in initials_source if part)[:2]

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


def sender_repeated_sub_chat_message(
    db: Session,
    chat_id: uuid.UUID,
    sender_user_id: uuid.UUID,
    message_body: str,
    *,
    exclude_message_id: uuid.UUID | None = None,
) -> bool:
    statement = select(SubPostChatMessage.message_body).where(
        SubPostChatMessage.chat_id == chat_id,
        SubPostChatMessage.sender_user_id == sender_user_id,
        SubPostChatMessage.message_type == "text",
        SubPostChatMessage.visibility_status == VISIBLE_MESSAGE_STATUS,
    )
    if exclude_message_id is not None:
        statement = statement.where(SubPostChatMessage.id != exclude_message_id)

    latest_body = db.scalar(
        statement.order_by(
            SubPostChatMessage.created_at.desc(),
            SubPostChatMessage.id.desc(),
        ).limit(1)
    )
    return (
        latest_body is not None
        and latest_body.strip().casefold() == message_body.strip().casefold()
    )


def replace_sub_chat_message_detections(
    db: Session,
    message: SubPostChatMessage,
    *,
    is_repeated_message: bool,
) -> None:
    db.execute(
        delete(SubPostChatMessageDetection).where(
            SubPostChatMessageDetection.message_id == message.id
        )
    )
    try:
        detections = detect_chat_message(
            message.message_body,
            is_repeated_message=is_repeated_message,
        )
    except Exception:
        logger.exception(
            "Need a Sub chat moderation detector failed for message %s.",
            message.id,
        )
        detections = []
    message.review_status = "needs_review" if detections else "clear"
    message.reviewed_at = None
    message.reviewed_by_user_id = None
    for detection in detections:
        db.add(
            SubPostChatMessageDetection(
                id=uuid.uuid4(),
                message_id=message.id,
                category=detection.category,
                severity=detection.severity,
                rule_key=detection.rule_key,
                matched_preview=detection.matched_preview,
            )
        )


def refresh_sub_post_chat_summary(db: Session, db_chat: SubPostChat) -> None:
    db_chat.message_count = (
        db.scalar(
            select(func.count())
            .select_from(SubPostChatMessage)
            .where(
                SubPostChatMessage.chat_id == db_chat.id,
                SubPostChatMessage.visibility_status == VISIBLE_MESSAGE_STATUS,
            )
        )
        or 0
    )
    db_chat.needs_review_count = (
        db.scalar(
            select(func.count())
            .select_from(SubPostChatMessage)
            .where(
                SubPostChatMessage.chat_id == db_chat.id,
                SubPostChatMessage.review_status == "needs_review",
            )
        )
        or 0
    )
    db_chat.removed_count = (
        db.scalar(
            select(func.count())
            .select_from(SubPostChatMessage)
            .where(
                SubPostChatMessage.chat_id == db_chat.id,
                SubPostChatMessage.visibility_status == "removed",
            )
        )
        or 0
    )
    latest_visible_message = db.scalar(
        select(SubPostChatMessage)
        .where(
            SubPostChatMessage.chat_id == db_chat.id,
            SubPostChatMessage.visibility_status == VISIBLE_MESSAGE_STATUS,
        )
        .order_by(SubPostChatMessage.created_at.desc(), SubPostChatMessage.id.desc())
        .limit(1)
    )
    if latest_visible_message is None:
        db_chat.latest_message_id = None
        db_chat.latest_message_preview = None
        db_chat.latest_message_at = None
    else:
        db_chat.latest_message_id = latest_visible_message.id
        db_chat.latest_message_preview = build_safe_message_preview(
            latest_visible_message.message_body
        )
        db_chat.latest_message_at = latest_visible_message.created_at
    db_chat.updated_at = now_utc()
    db.add(db_chat)


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
            SubPostChatMessage.visibility_status == VISIBLE_MESSAGE_STATUS,
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
            SubPostChatMessage.visibility_status == VISIBLE_MESSAGE_STATUS,
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
        SubPostChatMessage.visibility_status == VISIBLE_MESSAGE_STATUS,
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
            SubPostChatMessage.visibility_status == VISIBLE_MESSAGE_STATUS,
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
            SubPostChatMessage.visibility_status == VISIBLE_MESSAGE_STATUS,
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


def reconcile_sub_chat_notifications_after_moderation(
    db: Session,
    *,
    db_chat: SubPostChat,
    moderated_at: datetime,
) -> None:
    notifications = db.scalars(
        select(Notification).where(
            Notification.related_sub_post_chat_id == db_chat.id,
            Notification.notification_type == "sub_chat_message",
        )
    ).all()

    for notification in notifications:
        read_state = db.scalar(
            select(SubPostChatRead).where(
                SubPostChatRead.chat_id == db_chat.id,
                SubPostChatRead.user_id == notification.user_id,
            )
        )
        unread_filters = [
            SubPostChatMessage.chat_id == db_chat.id,
            SubPostChatMessage.visibility_status == VISIBLE_MESSAGE_STATUS,
            SubPostChatMessage.sender_user_id != notification.user_id,
        ]
        if read_state is not None:
            unread_filters.append(
                SubPostChatMessage.created_at
                > ensure_aware(read_state.last_read_at)
            )

        unread_count = (
            db.scalar(
                select(func.count())
                .select_from(SubPostChatMessage)
                .where(*unread_filters)
            )
            or 0
        )
        latest_unread_message = db.scalar(
            select(SubPostChatMessage)
            .where(*unread_filters)
            .order_by(
                SubPostChatMessage.created_at.desc(),
                SubPostChatMessage.id.desc(),
            )
            .limit(1)
        )

        if unread_count == 0 or latest_unread_message is None:
            notification.is_read = True
            if notification.read_at is None:
                notification.read_at = moderated_at
            notification.aggregate_count = None
        else:
            notification.is_read = False
            notification.read_at = None
            notification.aggregate_count = unread_count
            notification.actor_user_id = latest_unread_message.sender_user_id
            notification.related_sub_post_chat_message_id = (
                latest_unread_message.id
            )
            notification.event_at = latest_unread_message.created_at

        notification.updated_at = moderated_at
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
        "visibility_status": message.visibility_status,
        "review_status": message.review_status,
        "created_at": message.created_at,
        "updated_at": message.updated_at,
        "reviewed_at": message.reviewed_at,
        "reviewed_by_user_id": message.reviewed_by_user_id,
        "removed_at": message.removed_at,
        "removed_by_user_id": message.removed_by_user_id,
        "removed_source": message.removed_source,
        "restored_at": message.restored_at,
        "restored_by_user_id": message.restored_by_user_id,
    }


def serialize_sub_post_chat(
    db_chat: SubPostChat,
    unread_count: int = 0,
    last_read_at: datetime | None = None,
) -> SubPostChatReadSchema:
    return SubPostChatReadSchema(
        id=db_chat.id,
        sub_post_id=db_chat.sub_post_id,
        chat_status=db_chat.chat_status,
        created_at=db_chat.created_at,
        updated_at=db_chat.updated_at,
        closed_at=db_chat.closed_at,
        message_count=db_chat.message_count,
        needs_review_count=db_chat.needs_review_count,
        removed_count=db_chat.removed_count,
        latest_message_id=db_chat.latest_message_id,
        latest_message_preview=db_chat.latest_message_preview,
        latest_message_at=db_chat.latest_message_at,
        unread_count=unread_count,
        last_read_at=last_read_at,
    )


def get_accessible_sub_post_chat_or_404(
    db: Session,
    sub_post_id: uuid.UUID,
    current_user: User,
    *,
    lock_post_for_update: bool = False,
) -> tuple[SubPost, SubPostChat]:
    sub_post = get_sub_post_or_404(
        db,
        sub_post_id,
        lock_for_update=lock_post_for_update,
    )
    validate_sub_post_chat_access(db, sub_post, current_user)
    db_chat = get_sub_post_chat_for_post(db, sub_post.id)
    if db_chat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Need a Sub chat not found.",
        )

    return sub_post, db_chat


def ensure_sub_post_chat_workflow(
    db: Session,
    sub_post_id: uuid.UUID,
    _payload: SubPostChatEnsureCreate,
    current_user: User,
) -> SubPostChatReadSchema:
    sub_post = get_sub_post_or_404(db, sub_post_id, lock_for_update=True)
    validate_sub_post_chat_access(db, sub_post, current_user)
    db_chat = get_or_create_active_sub_post_chat(db, sub_post)

    try:
        db.commit()
        db.refresh(db_chat)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc.orig),
        ) from exc

    read_state, unread_count = get_sub_chat_read_state(db, db_chat, current_user)
    return serialize_sub_post_chat(
        db_chat,
        unread_count=unread_count,
        last_read_at=read_state.last_read_at if read_state else None,
    )


def get_sub_post_chat_workflow(
    db: Session,
    sub_post_id: uuid.UUID,
    current_user: User,
) -> SubPostChatReadSchema:
    _, db_chat = get_accessible_sub_post_chat_or_404(db, sub_post_id, current_user)
    read_state, unread_count = get_sub_chat_read_state(db, db_chat, current_user)
    return serialize_sub_post_chat(
        db_chat,
        unread_count=unread_count,
        last_read_at=read_state.last_read_at if read_state else None,
    )


def get_sub_post_chat_read_state_workflow(
    db: Session,
    sub_post_id: uuid.UUID,
    current_user: User,
) -> SubPostChatReadStateReadSchema:
    _, db_chat = get_accessible_sub_post_chat_or_404(db, sub_post_id, current_user)
    read_state, unread_count = get_sub_chat_read_state(db, db_chat, current_user)
    return SubPostChatReadStateReadSchema(
        chat_id=db_chat.id,
        user_id=current_user.id,
        last_read_at=read_state.last_read_at if read_state else None,
        last_read_message_id=read_state.last_read_message_id if read_state else None,
        unread_count=unread_count,
    )


def mark_sub_post_chat_read_workflow(
    db: Session,
    sub_post_id: uuid.UUID,
    _payload: SubPostChatEnsureCreate,
    current_user: User,
) -> SubPostChatReadStateReadSchema:
    _, db_chat = get_accessible_sub_post_chat_or_404(db, sub_post_id, current_user)
    read_state = mark_sub_chat_read(db, db_chat, current_user)

    try:
        db.commit()
        db.refresh(read_state)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc.orig),
        ) from exc

    return SubPostChatReadStateReadSchema(
        chat_id=db_chat.id,
        user_id=current_user.id,
        last_read_at=read_state.last_read_at,
        last_read_message_id=read_state.last_read_message_id,
        unread_count=0,
    )


def list_sub_post_chat_messages_workflow(
    db: Session,
    sub_post_id: uuid.UUID,
    current_user: User,
    *,
    before_created_at: datetime | None = None,
    limit: int = 50,
) -> list[dict]:
    sub_post, db_chat = get_accessible_sub_post_chat_or_404(
        db,
        sub_post_id,
        current_user,
    )
    messages = get_latest_visible_sub_chat_messages(
        db,
        db_chat.id,
        limit=limit,
        before_created_at=before_created_at,
    )
    if before_created_at is None:
        mark_sub_chat_read(db, db_chat, current_user)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(exc.orig),
            ) from exc
    return [serialize_sub_chat_message(db, message, sub_post) for message in messages]


def create_sub_post_chat_message_workflow(
    db: Session,
    sub_post_id: uuid.UUID,
    payload: SubPostChatMessageCreate,
    current_user: User,
) -> dict:
    current_time = now_utc()
    sub_post = get_sub_post_or_404(db, sub_post_id, lock_for_update=True)
    db_chat = get_sub_post_chat_for_post(db, sub_post.id)
    if db_chat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Need a Sub chat not found.",
        )
    sub_post = require_sub_post_chat_can_write(db, db_chat, current_user)

    if payload.chat_id != db_chat.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="chat_id must match this post's Need a Sub chat.",
        )

    message_body = normalize_message_body(payload.message_body)
    validate_sender_rate_limit(db, db_chat.id, current_user.id, current_time)
    validate_total_message_limit(db, db_chat.id)
    is_repeated_message = sender_repeated_sub_chat_message(
        db,
        db_chat.id,
        current_user.id,
        message_body,
    )
    sender_display_name, sender_initials = build_sender_snapshot(current_user)
    new_message = SubPostChatMessage(
        id=uuid.uuid4(),
        chat_id=db_chat.id,
        sender_user_id=current_user.id,
        sender_display_name_snapshot=sender_display_name,
        sender_initials_snapshot=sender_initials,
        message_type="text",
        message_body=message_body,
        visibility_status=VISIBLE_MESSAGE_STATUS,
    )

    try:
        db.add(new_message)
        db.flush()
        replace_sub_chat_message_detections(
            db,
            new_message,
            is_repeated_message=is_repeated_message,
        )
        db.add(new_message)
        db.flush()
        refresh_sub_post_chat_summary(db, db_chat)
        create_or_update_sub_chat_notifications(
            db,
            sub_post=sub_post,
            db_chat=db_chat,
            message=new_message,
            sender=current_user,
            event_at=current_time,
        )
        mark_sub_chat_read(db, db_chat, current_user, current_time)
        db.commit()
        db.refresh(new_message)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc.orig),
        ) from exc

    surface_need_a_sub_chat_message_text(db, message_id=new_message.id)
    return serialize_sub_chat_message(db, new_message, sub_post)
