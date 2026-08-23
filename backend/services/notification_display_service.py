import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from backend.models import Game, Notification, SubPost, SubPostRequest
from backend.services.game_rules import GAME_STATUSES_WITH_DISABLED_INBOX_ACTIONS
from backend.services.need_a_sub_rules import (
    ACTIVE_VISIBLE_POST_STATUSES,
    CHAT_ALLOWED_POST_STATUSES,
)
from backend.services.notification_policy import (
    ACTION_LABEL_BY_KEY,
    ICON_BY_NOTIFICATION_TYPE,
    SEVERITY_BY_NOTIFICATION_TYPE,
    SOURCE_LABEL_BY_TYPE,
)

SUB_CHAT_MESSAGE_ACTION_GRACE_HOURS = 24
_MISSING = object()


def ensure_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value


def format_row_subject(notification: Notification) -> str:
    if notification.notification_type == "admin_enforcement_notice":
        return notification.summary

    if notification.subject_starts_at is None:
        return notification.subject_label

    if not notification.subject_timezone:
        return notification.subject_label

    return (
        f"{notification.subject_label} · "
        f"{format_short_datetime(notification.subject_starts_at, notification.subject_timezone)}"
    )


def format_short_datetime(value: datetime, timezone_name: str) -> str:
    local_value = to_local_datetime(value, timezone_name)
    hour = local_value.hour % 12 or 12
    minute = f":{local_value.minute:02d}" if local_value.minute else ""
    meridiem = "AM" if local_value.hour < 12 else "PM"

    return (
        f"{local_value:%a}, {local_value:%b} {local_value.day}, "
        f"{local_value.year} at {hour}{minute} {meridiem}"
    )


def to_local_datetime(value: datetime, timezone_name: str) -> datetime:
    aware_value = ensure_aware_utc(value)

    try:
        local_timezone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        local_timezone = timezone.utc

    return aware_value.astimezone(local_timezone)


def user_has_current_sub_chat_access(
    db: Session,
    notification: Notification,
    sub_post: SubPost,
) -> bool:
    if notification.user_id == sub_post.owner_user_id:
        return True

    return (
        db.query(SubPostRequest.id)
        .filter(
            SubPostRequest.sub_post_id == sub_post.id,
            SubPostRequest.requester_user_id == notification.user_id,
            SubPostRequest.request_status == "confirmed",
        )
        .one_or_none()
        is not None
    )


def build_sub_chat_message_action(
    db: Session,
    notification: Notification,
    sub_post: SubPost,
    *,
    has_chat_access: bool | None = None,
) -> dict[str, object] | None:
    action_key = notification.action_key
    if action_key != "view_sub_post":
        return None

    if notification.related_sub_post_chat_id is None:
        return None

    if sub_post.post_status in {"cancelled", "removed"}:
        return build_disabled_action_payload(
            action_key,
            "This Need a Sub post is no longer available.",
        )

    if sub_post.post_status not in CHAT_ALLOWED_POST_STATUSES:
        return build_disabled_action_payload(
            action_key,
            "This Need a Sub chat is no longer available.",
        )

    closes_at = ensure_aware_utc(sub_post.ends_at) + timedelta(
        hours=SUB_CHAT_MESSAGE_ACTION_GRACE_HOURS
    )
    if datetime.now(timezone.utc) > closes_at:
        return build_disabled_action_payload(
            action_key,
            "This Need a Sub chat is closed.",
        )

    if has_chat_access is None:
        has_chat_access = user_has_current_sub_chat_access(db, notification, sub_post)

    if not has_chat_access:
        return build_disabled_action_payload(
            action_key,
            "You no longer have access to this chat.",
        )

    return build_action_payload(
        action_key,
        f"/need-a-sub/posts/{notification.related_sub_post_id}",
    )


def build_notification_action(
    db: Session,
    notification: Notification,
    *,
    related_game: Game | None | object = _MISSING,
    related_sub_post: SubPost | None | object = _MISSING,
    sub_chat_access: bool | None = None,
) -> dict[str, object] | None:
    action_key = notification.action_key

    if action_key is None:
        return None

    if action_key == "view_game":
        if notification.related_game_id is None:
            return None

        game = (
            db.get(Game, notification.related_game_id)
            if related_game is _MISSING
            else related_game
        )
        if (
            game is None
            or game.deleted_at is not None
            or game.publish_status != "published"
            or game.game_status in GAME_STATUSES_WITH_DISABLED_INBOX_ACTIONS
        ):
            return None

        return build_action_payload(action_key, f"/games/{notification.related_game_id}")

    if action_key == "view_sub_post":
        if notification.related_sub_post_id is None:
            return None

        sub_post = (
            db.get(SubPost, notification.related_sub_post_id)
            if related_sub_post is _MISSING
            else related_sub_post
        )
        if sub_post is None:
            return None

        if notification.notification_type == "sub_chat_message":
            return build_sub_chat_message_action(
                db,
                notification,
                sub_post,
                has_chat_access=sub_chat_access,
            )

        starts_at = ensure_aware_utc(sub_post.starts_at)
        if (
            sub_post.post_status not in ACTIVE_VISIBLE_POST_STATUSES
            or starts_at < datetime.now(timezone.utc)
        ):
            return None

        return build_action_payload(
            action_key,
            f"/need-a-sub/posts/{notification.related_sub_post_id}",
        )

    if action_key == "view_policy":
        return {
            **build_action_payload(action_key, policy_path_for_notification(notification)),
            "state": {
                "from": "/inbox",
                "fromLabel": "Back to Inbox",
            },
        }

    if action_key == "payment_methods":
        return build_action_payload(action_key, "/profile/payment-methods")

    if action_key == "view_profile":
        return build_action_payload(action_key, "/profile")

    return None


def build_action_payload(action_key: str, path: str) -> dict[str, object]:
    return {
        "key": action_key,
        "label": ACTION_LABEL_BY_KEY[action_key],
        "path": path,
        "disabled": False,
        "disabled_reason": None,
    }


def build_disabled_action_payload(
    action_key: str,
    disabled_reason: str,
) -> dict[str, object]:
    return {
        "key": action_key,
        "label": ACTION_LABEL_BY_KEY[action_key],
        "path": None,
        "disabled": True,
        "disabled_reason": disabled_reason,
    }


def policy_path_for_notification(notification: Notification) -> str:
    notification_text = (
        f"{notification.title} {notification.summary} {notification.body}"
    ).lower()

    if "privacy" in notification_text:
        return "/privacy"

    if "refund" in notification_text or "cancel" in notification_text:
        return "/policies/cancellation-refunds"

    return "/terms"


def serialize_notification(
    db: Session,
    notification: Notification,
    *,
    related_game: Game | None | object = _MISSING,
    related_sub_post: SubPost | None | object = _MISSING,
    sub_chat_access: bool | None = None,
) -> dict[str, object]:
    return {
        "id": notification.id,
        "user_id": notification.user_id,
        "notification_type": notification.notification_type,
        "notification_category": notification.notification_category,
        "notification_domain": notification.notification_domain,
        "source_type": notification.source_type,
        "source_label": SOURCE_LABEL_BY_TYPE.get(notification.source_type, "Pickup Lane"),
        "title": notification.title,
        "subject_label": notification.subject_label,
        "subject_starts_at": notification.subject_starts_at,
        "subject_ends_at": notification.subject_ends_at,
        "subject_timezone": notification.subject_timezone,
        "row_subject": format_row_subject(notification),
        "summary": notification.summary,
        "body": notification.body,
        "action_key": notification.action_key,
        "action": build_notification_action(
            db,
            notification,
            related_game=related_game,
            related_sub_post=related_sub_post,
            sub_chat_access=sub_chat_access,
        ),
        "icon": ICON_BY_NOTIFICATION_TYPE.get(notification.notification_type, "Bell"),
        "severity": SEVERITY_BY_NOTIFICATION_TYPE.get(
            notification.notification_type,
            "default",
        ),
        "event_at": notification.event_at,
        "aggregation_key": notification.aggregation_key,
        "aggregate_count": notification.aggregate_count,
        "actor_user_id": notification.actor_user_id,
        "related_game_id": notification.related_game_id,
        "related_chat_id": notification.related_chat_id,
        "related_booking_id": notification.related_booking_id,
        "related_payment_id": notification.related_payment_id,
        "related_refund_id": notification.related_refund_id,
        "related_participant_id": notification.related_participant_id,
        "related_message_id": notification.related_message_id,
        "related_sub_post_id": notification.related_sub_post_id,
        "related_sub_post_chat_id": notification.related_sub_post_chat_id,
        "related_sub_post_chat_message_id": (
            notification.related_sub_post_chat_message_id
        ),
        "related_sub_post_request_id": notification.related_sub_post_request_id,
        "related_sub_post_position_id": notification.related_sub_post_position_id,
        "is_read": notification.is_read,
        "read_at": notification.read_at,
        "created_at": notification.created_at,
        "updated_at": notification.updated_at,
    }


def load_notification_games(
    db: Session,
    notifications: list[Notification],
) -> dict[uuid.UUID, Game]:
    game_ids = {
        notification.related_game_id
        for notification in notifications
        if notification.action_key == "view_game"
        and notification.related_game_id is not None
    }
    if not game_ids:
        return {}

    return dict(db.execute(select(Game.id, Game).where(Game.id.in_(game_ids))).all())


def load_notification_sub_posts(
    db: Session,
    notifications: list[Notification],
) -> dict[uuid.UUID, SubPost]:
    sub_post_ids = {
        notification.related_sub_post_id
        for notification in notifications
        if notification.action_key == "view_sub_post"
        and notification.related_sub_post_id is not None
    }
    if not sub_post_ids:
        return {}

    return dict(
        db.execute(select(SubPost.id, SubPost).where(SubPost.id.in_(sub_post_ids))).all()
    )


def load_sub_chat_access_by_notification_id(
    db: Session,
    notifications: list[Notification],
    sub_posts_by_id: dict[uuid.UUID, SubPost],
) -> dict[uuid.UUID, bool]:
    access_by_notification_id: dict[uuid.UUID, bool] = {}
    requester_pairs: set[tuple[uuid.UUID, uuid.UUID]] = set()

    for notification in notifications:
        if (
            notification.action_key != "view_sub_post"
            or notification.notification_type != "sub_chat_message"
            or notification.related_sub_post_id is None
        ):
            continue

        sub_post = sub_posts_by_id.get(notification.related_sub_post_id)
        if sub_post is None:
            access_by_notification_id[notification.id] = False
            continue

        if notification.user_id == sub_post.owner_user_id:
            access_by_notification_id[notification.id] = True
            continue

        requester_pairs.add((sub_post.id, notification.user_id))

    if requester_pairs:
        conditions = [
            and_(
                SubPostRequest.sub_post_id == sub_post_id,
                SubPostRequest.requester_user_id == user_id,
            )
            for sub_post_id, user_id in requester_pairs
        ]
        confirmed_pairs = set(
            db.execute(
                select(
                    SubPostRequest.sub_post_id,
                    SubPostRequest.requester_user_id,
                ).where(
                    SubPostRequest.request_status == "confirmed",
                    or_(*conditions),
                )
            ).all()
        )
    else:
        confirmed_pairs = set()

    for notification in notifications:
        if notification.id in access_by_notification_id:
            continue
        if (
            notification.action_key == "view_sub_post"
            and notification.notification_type == "sub_chat_message"
            and notification.related_sub_post_id is not None
        ):
            access_by_notification_id[notification.id] = (
                notification.related_sub_post_id,
                notification.user_id,
            ) in confirmed_pairs

    return access_by_notification_id


def serialize_notifications_for_list(
    db: Session,
    notifications: list[Notification],
) -> list[dict[str, object]]:
    games_by_id = load_notification_games(db, notifications)
    sub_posts_by_id = load_notification_sub_posts(db, notifications)
    sub_chat_access_by_notification_id = load_sub_chat_access_by_notification_id(
        db,
        notifications,
        sub_posts_by_id,
    )

    return [
        serialize_notification(
            db,
            notification,
            related_game=(
                games_by_id.get(notification.related_game_id)
                if notification.related_game_id is not None
                else None
            ),
            related_sub_post=(
                sub_posts_by_id.get(notification.related_sub_post_id)
                if notification.related_sub_post_id is not None
                else None
            ),
            sub_chat_access=sub_chat_access_by_notification_id.get(notification.id),
        )
        for notification in notifications
    ]
