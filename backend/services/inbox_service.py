"""User Inbox workflows for App Updates and Game Activity."""

import base64
import hashlib
import hmac
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import HTTPException, status
from sqlalchemy import and_, func, literal, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from backend.database import DATABASE_URL
from backend.models import (
    Notification,
    PlatformNotice,
    PlatformNoticeGlobalSeenState,
    PlatformNoticeRecipient,
    PlatformNoticeSelectedRead,
    User,
)
from backend.schemas.inbox_schema import InboxCountsRead, InboxItemRead, InboxListRead
from backend.services.account_eligibility_service import user_is_account_eligible
from backend.services.notification_display_service import serialize_notification
from backend.services.platform_notice_service import (
    AUDIENCE_TYPE_ALL_ELIGIBLE,
    AUDIENCE_TYPE_SELECTED,
)

APP_UPDATE_SOURCE_GLOBAL = "platform_notice_global"
APP_UPDATE_SOURCE_SELECTED = "platform_notice_selected"
APP_UPDATE_SOURCE_NOTIFICATION = "notification"
GAME_ACTIVITY_SOURCE_NOTIFICATION = "notification"
READ_BEHAVIOR_GLOBAL_SEEN = "global_seen_marker"
READ_BEHAVIOR_ITEM_READ = "item_read"
APP_UPDATE_SOURCE_RANKS = {
    APP_UPDATE_SOURCE_GLOBAL: 3,
    APP_UPDATE_SOURCE_SELECTED: 2,
    APP_UPDATE_SOURCE_NOTIFICATION: 1,
}
GAME_ACTIVITY_SOURCE_RANKS = {GAME_ACTIVITY_SOURCE_NOTIFICATION: 1}
MAX_INBOX_LIMIT = 50
GLOBAL_SEEN_TOKEN_VERSION = 1


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def token_secret() -> bytes:
    configured_secret = os.getenv("INBOX_TOKEN_SECRET") or DATABASE_URL
    return configured_secret.encode("utf-8")


def encode_payload(payload: dict[str, Any]) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    signature = hmac.new(token_secret(), body, hashlib.sha256).hexdigest()
    envelope = {"payload": payload, "signature": signature}
    return base64.urlsafe_b64encode(
        json.dumps(envelope, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")


def decode_signed_payload(token: str, *, expected_kind: str) -> dict[str, Any]:
    normalized = str(token or "").strip()
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="token is required.",
        )

    try:
        envelope = json.loads(base64.urlsafe_b64decode(normalized.encode("ascii")))
        payload = envelope["payload"]
        signature = envelope["signature"]
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="token is invalid.",
        ) from exc

    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    expected_signature = hmac.new(token_secret(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(str(signature), expected_signature):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="token is invalid.",
        )

    if payload.get("kind") != expected_kind:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="token is invalid.",
        )

    return payload


def encode_cursor(
    *,
    feed_as_of: datetime,
    feed_name: str,
    item: InboxItemRead,
    source_rank: int,
) -> str:
    return encode_payload(
        {
            "kind": "inbox_cursor",
            "feed_name": feed_name,
            "occurred_at": item.occurred_at.isoformat(),
            "source_id": str(item.source_id),
            "source_rank": source_rank,
            "source_type": item.source_type,
            "feed_as_of": feed_as_of.isoformat(),
        }
    )


def decode_cursor(cursor: str | None, *, expected_feed_name: str) -> dict[str, Any] | None:
    normalized = str(cursor or "").strip()
    if not normalized:
        return None

    payload = decode_signed_payload(normalized, expected_kind="inbox_cursor")
    if payload.get("feed_name") != expected_feed_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cursor is invalid.",
        )

    try:
        return {
            "occurred_at": datetime.fromisoformat(payload["occurred_at"]),
            "source_id": uuid.UUID(payload["source_id"]),
            "source_rank": int(payload["source_rank"]),
            "source_type": str(payload["source_type"]),
            "feed_as_of": datetime.fromisoformat(payload["feed_as_of"]),
        }
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cursor is invalid.",
        ) from exc


def cursor_filter(
    *,
    cursor_data: dict[str, Any] | None,
    id_column,
    occurred_at_column,
    source_rank: int,
):
    if cursor_data is None:
        return None

    return or_(
        occurred_at_column < cursor_data["occurred_at"],
        and_(
            occurred_at_column == cursor_data["occurred_at"],
            literal(source_rank) < cursor_data["source_rank"],
        ),
        and_(
            occurred_at_column == cursor_data["occurred_at"],
            literal(source_rank) == cursor_data["source_rank"],
            id_column < cursor_data["source_id"],
        ),
    )


def effective_limit(limit: int) -> int:
    return max(1, min(limit, MAX_INBOX_LIMIT))


def get_global_seen_sequence(db: Session, *, user_id: uuid.UUID) -> int:
    state = db.get(PlatformNoticeGlobalSeenState, user_id)
    return state.last_seen_global_sequence if state else 0


def encode_global_seen_token(
    *,
    highest_global_sequence: int,
    user_id: uuid.UUID,
) -> str:
    return encode_payload(
        {
            "kind": "global_seen",
            "version": GLOBAL_SEEN_TOKEN_VERSION,
            "user_id": str(user_id),
            "highest_global_sequence": highest_global_sequence,
        }
    )


def global_seen_sequence_for_page(
    db: Session,
    *,
    page_global_notice_ids: list[uuid.UUID],
    user: User,
) -> int | None:
    if not page_global_notice_ids:
        return None

    page_global_notice_id_set = set(page_global_notice_ids)
    page_sequences = db.scalars(
        select(PlatformNotice.global_sequence).where(
            PlatformNotice.id.in_(page_global_notice_id_set),
            PlatformNotice.global_sequence.is_not(None),
        )
    ).all()
    if not page_sequences:
        return None

    highest_global_sequence = max(page_sequences)
    seen_sequence = get_global_seen_sequence(db, user_id=user.id)
    if highest_global_sequence <= seen_sequence:
        return None

    return highest_global_sequence


def platform_notice_item(
    *,
    is_new: bool,
    notice: PlatformNotice,
    read_at: datetime | None,
    source_type: str,
) -> InboxItemRead:
    return InboxItemRead(
        source_type=source_type,
        source_id=notice.id,
        item_kind="platform_notice",
        title=notice.title,
        message=notice.message,
        source_label="Pickup Lane",
        subject_label="Pickup Lane",
        row_subject="",
        summary=notice.message,
        occurred_at=notice.published_at,
        is_new=is_new,
        read_behavior=(
            READ_BEHAVIOR_GLOBAL_SEEN
            if source_type == APP_UPDATE_SOURCE_GLOBAL
            else READ_BEHAVIOR_ITEM_READ
        ),
        read_at=read_at,
        action=None,
        icon="Megaphone",
        severity="default",
        notification_type=None,
        notification_category="app",
        notification_domain="app",
        original_notification_id=None,
    )


def notification_item(
    db: Session,
    *,
    notification: Notification,
    source_type: str,
) -> InboxItemRead:
    serialized = serialize_notification(db, notification)
    return InboxItemRead(
        source_type=source_type,
        source_id=notification.id,
        item_kind=notification.notification_type,
        title=serialized["title"],
        message=serialized["body"],
        source_label=serialized["source_label"],
        subject_label=serialized["subject_label"],
        row_subject=serialized["row_subject"],
        summary=serialized["summary"],
        occurred_at=serialized["event_at"],
        is_new=not notification.is_read,
        read_behavior=READ_BEHAVIOR_ITEM_READ,
        read_at=notification.read_at,
        action=serialized["action"],
        icon=serialized["icon"],
        severity=serialized["severity"],
        notification_type=notification.notification_type,
        notification_category=notification.notification_category,
        notification_domain=notification.notification_domain,
        original_notification_id=notification.id,
    )


def sort_inbox_items(
    items: list[InboxItemRead],
    *,
    source_ranks: dict[str, int],
) -> list[InboxItemRead]:
    return sorted(
        items,
        key=lambda item: (
            item.occurred_at,
            source_ranks[item.source_type],
            str(item.source_id),
        ),
        reverse=True,
    )


def list_global_platform_notice_items(
    db: Session,
    *,
    cursor_data: dict[str, Any] | None,
    feed_as_of: datetime,
    filter_mode: str,
    limit: int,
    user: User,
) -> list[InboxItemRead]:
    if not user_is_account_eligible(user):
        return []

    seen_sequence = get_global_seen_sequence(db, user_id=user.id)
    source_rank = APP_UPDATE_SOURCE_RANKS[APP_UPDATE_SOURCE_GLOBAL]
    filters = [
        PlatformNotice.audience_type == AUDIENCE_TYPE_ALL_ELIGIBLE,
        PlatformNotice.cancelled_at.is_(None),
        PlatformNotice.published_at <= feed_as_of,
    ]
    if filter_mode == "new":
        filters.append(PlatformNotice.global_sequence > seen_sequence)

    page_filter = cursor_filter(
        cursor_data=cursor_data,
        id_column=PlatformNotice.id,
        occurred_at_column=PlatformNotice.published_at,
        source_rank=source_rank,
    )
    if page_filter is not None:
        filters.append(page_filter)

    notices = db.scalars(
        select(PlatformNotice)
        .where(*filters)
        .order_by(
            PlatformNotice.published_at.desc(),
            PlatformNotice.id.desc(),
        )
        .limit(limit + 1)
    ).all()
    return [
        platform_notice_item(
            is_new=bool(notice.global_sequence and notice.global_sequence > seen_sequence),
            notice=notice,
            read_at=None,
            source_type=APP_UPDATE_SOURCE_GLOBAL,
        )
        for notice in notices
    ]


def list_selected_platform_notice_items(
    db: Session,
    *,
    cursor_data: dict[str, Any] | None,
    feed_as_of: datetime,
    filter_mode: str,
    limit: int,
    user: User,
) -> list[InboxItemRead]:
    if not user_is_account_eligible(user):
        return []

    source_rank = APP_UPDATE_SOURCE_RANKS[APP_UPDATE_SOURCE_SELECTED]
    filters = [
        PlatformNoticeRecipient.user_id == user.id,
        PlatformNotice.audience_type == AUDIENCE_TYPE_SELECTED,
        PlatformNotice.cancelled_at.is_(None),
        PlatformNotice.published_at <= feed_as_of,
    ]
    if filter_mode == "new":
        filters.append(PlatformNoticeSelectedRead.user_id.is_(None))

    page_filter = cursor_filter(
        cursor_data=cursor_data,
        id_column=PlatformNotice.id,
        occurred_at_column=PlatformNotice.published_at,
        source_rank=source_rank,
    )
    if page_filter is not None:
        filters.append(page_filter)

    rows = db.execute(
        select(PlatformNotice, PlatformNoticeSelectedRead)
        .join(
            PlatformNoticeRecipient,
            PlatformNoticeRecipient.notice_id == PlatformNotice.id,
        )
        .outerjoin(
            PlatformNoticeSelectedRead,
            and_(
                PlatformNoticeSelectedRead.notice_id == PlatformNotice.id,
                PlatformNoticeSelectedRead.user_id == user.id,
            ),
        )
        .where(*filters)
        .order_by(PlatformNotice.published_at.desc(), PlatformNotice.id.desc())
        .limit(limit + 1)
    ).all()
    return [
        platform_notice_item(
            is_new=read is None,
            notice=notice,
            read_at=read.read_at if read else None,
            source_type=APP_UPDATE_SOURCE_SELECTED,
        )
        for notice, read in rows
    ]


def list_notification_items(
    db: Session,
    *,
    category: Literal["app", "game_activity"],
    cursor_data: dict[str, Any] | None,
    feed_as_of: datetime,
    filter_mode: str,
    limit: int,
    user: User,
) -> list[InboxItemRead]:
    source_rank = (
        APP_UPDATE_SOURCE_RANKS[APP_UPDATE_SOURCE_NOTIFICATION]
        if category == "app"
        else GAME_ACTIVITY_SOURCE_RANKS[GAME_ACTIVITY_SOURCE_NOTIFICATION]
    )
    filters = [
        Notification.user_id == user.id,
        Notification.notification_category == category,
        Notification.event_at <= feed_as_of,
    ]
    if filter_mode in {"new", "unread"}:
        filters.append(Notification.is_read.is_(False))
    elif filter_mode == "read":
        filters.append(Notification.is_read.is_(True))

    page_filter = cursor_filter(
        cursor_data=cursor_data,
        id_column=Notification.id,
        occurred_at_column=Notification.event_at,
        source_rank=source_rank,
    )
    if page_filter is not None:
        filters.append(page_filter)

    notifications = db.scalars(
        select(Notification)
        .where(*filters)
        .order_by(
            Notification.event_at.desc(),
            Notification.id.desc(),
        )
        .limit(limit + 1)
    ).all()
    return [
        notification_item(
            db,
            notification=notification,
            source_type=(
                APP_UPDATE_SOURCE_NOTIFICATION
                if category == "app"
                else GAME_ACTIVITY_SOURCE_NOTIFICATION
            ),
        )
        for notification in notifications
    ]


def validate_app_updates_filter(filter_mode: str) -> str:
    normalized = str(filter_mode or "all").strip().lower()
    if normalized not in {"all", "new"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="filter is not supported.",
        )
    return normalized


def validate_game_activity_filter(filter_mode: str) -> str:
    normalized = str(filter_mode or "all").strip().lower()
    if normalized not in {"all", "unread", "read"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="filter is not supported.",
        )
    return normalized


def list_app_updates(
    db: Session,
    *,
    cursor: str | None = None,
    filter_mode: str = "all",
    limit: int = 30,
    user: User,
) -> InboxListRead:
    normalized_filter = validate_app_updates_filter(filter_mode)
    page_limit = effective_limit(limit)
    cursor_data = decode_cursor(cursor, expected_feed_name="app_updates")
    feed_as_of = cursor_data["feed_as_of"] if cursor_data else now_utc()

    items = []
    items.extend(
        list_global_platform_notice_items(
            db,
            cursor_data=cursor_data,
            feed_as_of=feed_as_of,
            filter_mode=normalized_filter,
            limit=page_limit,
            user=user,
        )
    )
    items.extend(
        list_selected_platform_notice_items(
            db,
            cursor_data=cursor_data,
            feed_as_of=feed_as_of,
            filter_mode=normalized_filter,
            limit=page_limit,
            user=user,
        )
    )
    items.extend(
        list_notification_items(
            db,
            category="app",
            cursor_data=cursor_data,
            feed_as_of=feed_as_of,
            filter_mode=normalized_filter,
            limit=page_limit,
            user=user,
        )
    )

    sorted_items = sort_inbox_items(items, source_ranks=APP_UPDATE_SOURCE_RANKS)
    page_items = sorted_items[:page_limit]
    has_more = len(sorted_items) > page_limit
    page_global_notice_ids = [
        item.source_id
        for item in page_items
        if item.source_type == APP_UPDATE_SOURCE_GLOBAL
    ]
    page_global_seen_sequence = global_seen_sequence_for_page(
        db,
        page_global_notice_ids=page_global_notice_ids,
        user=user,
    )

    return InboxListRead(
        items=page_items,
        limit=page_limit,
        next_cursor=encode_cursor(
            feed_as_of=feed_as_of,
            feed_name="app_updates",
            item=page_items[-1],
            source_rank=APP_UPDATE_SOURCE_RANKS[page_items[-1].source_type],
        )
        if has_more and page_items
        else None,
        has_more=has_more,
        global_seen_token=encode_global_seen_token(
            highest_global_sequence=page_global_seen_sequence,
            user_id=user.id,
        )
        if page_global_seen_sequence is not None
        else None,
    )


def list_game_activity(
    db: Session,
    *,
    cursor: str | None = None,
    filter_mode: str = "all",
    limit: int = 30,
    user: User,
) -> InboxListRead:
    normalized_filter = validate_game_activity_filter(filter_mode)
    page_limit = effective_limit(limit)
    cursor_data = decode_cursor(cursor, expected_feed_name="game_activity")
    feed_as_of = cursor_data["feed_as_of"] if cursor_data else now_utc()
    items = list_notification_items(
        db,
        category="game_activity",
        cursor_data=cursor_data,
        feed_as_of=feed_as_of,
        filter_mode=normalized_filter,
        limit=page_limit,
        user=user,
    )
    sorted_items = sort_inbox_items(
        items,
        source_ranks=GAME_ACTIVITY_SOURCE_RANKS,
    )
    page_items = sorted_items[:page_limit]
    has_more = len(sorted_items) > page_limit

    return InboxListRead(
        items=page_items,
        limit=page_limit,
        next_cursor=encode_cursor(
            feed_as_of=feed_as_of,
            feed_name="game_activity",
            item=page_items[-1],
            source_rank=GAME_ACTIVITY_SOURCE_RANKS[page_items[-1].source_type],
        )
        if has_more and page_items
        else None,
        has_more=has_more,
        global_seen_token=None,
    )


def mark_global_platform_notices_seen(
    db: Session,
    *,
    seen_token: str,
    user: User,
) -> InboxCountsRead:
    payload = decode_signed_payload(seen_token, expected_kind="global_seen")
    try:
        version = int(payload["version"])
        token_user_id = uuid.UUID(payload["user_id"])
        sequence = int(payload["highest_global_sequence"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="seen_token is invalid.",
        ) from exc

    if version != GLOBAL_SEEN_TOKEN_VERSION or token_user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="seen_token is invalid.",
        )

    timestamp = now_utc()
    statement = (
        insert(PlatformNoticeGlobalSeenState)
        .values(
            user_id=user.id,
            last_seen_global_sequence=sequence,
            created_at=timestamp,
            updated_at=timestamp,
        )
        .on_conflict_do_update(
            index_elements=[PlatformNoticeGlobalSeenState.user_id],
            set_={
                "last_seen_global_sequence": func.greatest(
                    PlatformNoticeGlobalSeenState.last_seen_global_sequence,
                    sequence,
                ),
                "updated_at": timestamp,
            },
        )
    )
    db.execute(statement)
    db.commit()
    return get_inbox_counts(db, user=user)


def mark_selected_platform_notice_read(
    db: Session,
    *,
    notice_id: uuid.UUID,
    user: User,
) -> InboxItemRead:
    if not user_is_account_eligible(user):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Platform notice not found.",
        )

    notice = db.scalar(
        select(PlatformNotice)
        .join(PlatformNoticeRecipient, PlatformNoticeRecipient.notice_id == PlatformNotice.id)
        .where(
            PlatformNotice.id == notice_id,
            PlatformNoticeRecipient.user_id == user.id,
            PlatformNotice.audience_type == AUDIENCE_TYPE_SELECTED,
            PlatformNotice.cancelled_at.is_(None),
            PlatformNotice.published_at <= now_utc(),
        )
    )
    if notice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Platform notice not found.",
        )

    timestamp = now_utc()
    statement = (
        insert(PlatformNoticeSelectedRead)
        .values(
            notice_id=notice.id,
            user_id=user.id,
            read_at=timestamp,
            created_at=timestamp,
            updated_at=timestamp,
        )
        .on_conflict_do_nothing(
            index_elements=[
                PlatformNoticeSelectedRead.notice_id,
                PlatformNoticeSelectedRead.user_id,
            ],
        )
    )
    db.execute(statement)
    db.commit()
    read = db.get(PlatformNoticeSelectedRead, {"notice_id": notice.id, "user_id": user.id})
    return platform_notice_item(
        is_new=False,
        notice=notice,
        read_at=read.read_at if read else timestamp,
        source_type=APP_UPDATE_SOURCE_SELECTED,
    )


def get_inbox_counts(db: Session, *, user: User) -> InboxCountsRead:
    seen_sequence = get_global_seen_sequence(db, user_id=user.id)
    timestamp = now_utc()
    global_new_count = 0
    if user_is_account_eligible(user):
        global_new_count = db.scalar(
            select(func.count())
            .select_from(PlatformNotice)
            .where(
                PlatformNotice.audience_type == AUDIENCE_TYPE_ALL_ELIGIBLE,
                PlatformNotice.cancelled_at.is_(None),
                PlatformNotice.published_at <= timestamp,
                PlatformNotice.global_sequence > seen_sequence,
            )
        ) or 0

    selected_new_count = 0
    if user_is_account_eligible(user):
        selected_new_count = db.scalar(
            select(func.count())
            .select_from(PlatformNotice)
            .join(PlatformNoticeRecipient, PlatformNoticeRecipient.notice_id == PlatformNotice.id)
            .outerjoin(
                PlatformNoticeSelectedRead,
                and_(
                    PlatformNoticeSelectedRead.notice_id == PlatformNotice.id,
                    PlatformNoticeSelectedRead.user_id == user.id,
                ),
            )
            .where(
                PlatformNoticeRecipient.user_id == user.id,
                PlatformNotice.audience_type == AUDIENCE_TYPE_SELECTED,
                PlatformNotice.cancelled_at.is_(None),
                PlatformNotice.published_at <= timestamp,
                PlatformNoticeSelectedRead.user_id.is_(None),
            )
        ) or 0

    app_notification_new_count = db.scalar(
        select(func.count())
        .select_from(Notification)
        .where(
            Notification.user_id == user.id,
            Notification.notification_category == "app",
            Notification.event_at <= timestamp,
            Notification.is_read.is_(False),
        )
    ) or 0

    game_activity_unread_count = db.scalar(
        select(func.count())
        .select_from(Notification)
        .where(
            Notification.user_id == user.id,
            Notification.notification_category == "game_activity",
            Notification.event_at <= timestamp,
            Notification.is_read.is_(False),
        )
    ) or 0

    return InboxCountsRead(
        app_updates_new_count=(
            int(global_new_count)
            + int(selected_new_count)
            + int(app_notification_new_count)
        ),
        game_activity_unread_count=int(game_activity_unread_count),
    )
