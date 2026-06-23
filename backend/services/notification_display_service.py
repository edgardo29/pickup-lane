from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from backend.models import Game, Notification, SubPost, SubPostRequest
from backend.services.notification_policy import (
    ACTION_LABEL_BY_KEY,
    ICON_BY_NOTIFICATION_TYPE,
    SEVERITY_BY_NOTIFICATION_TYPE,
    SOURCE_LABEL_BY_TYPE,
)

GAME_STATUSES_WITH_DISABLED_INBOX_ACTIONS = {"cancelled", "abandoned"}
SUB_POST_STATUSES_WITH_INBOX_ACTIONS = {"active", "filled"}
SUB_CHAT_MESSAGE_ACTION_POST_STATUSES = {"active", "filled", "expired"}
SUB_CHAT_MESSAGE_ACTION_GRACE_HOURS = 24


def ensure_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value


def format_row_subject(notification: Notification) -> str:
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
) -> dict[str, object] | None:
    action_key = notification.action_key
    if action_key != "view_sub_post":
        return None

    if notification.related_sub_post_chat_id is None:
        return None

    if sub_post.post_status in {"canceled", "removed"}:
        return build_disabled_action_payload(
            action_key,
            "This Need a Sub post is no longer available.",
        )

    if sub_post.post_status not in SUB_CHAT_MESSAGE_ACTION_POST_STATUSES:
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

    if not user_has_current_sub_chat_access(db, notification, sub_post):
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
) -> dict[str, object] | None:
    action_key = notification.action_key

    if action_key is None:
        return None

    if action_key == "view_game":
        if notification.related_game_id is None:
            return None

        game = db.get(Game, notification.related_game_id)
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

        sub_post = db.get(SubPost, notification.related_sub_post_id)
        if sub_post is None:
            return None

        if notification.notification_type == "sub_chat_message":
            return build_sub_chat_message_action(db, notification, sub_post)

        starts_at = ensure_aware_utc(sub_post.starts_at)
        if (
            sub_post.post_status not in SUB_POST_STATUSES_WITH_INBOX_ACTIONS
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
        "action": build_notification_action(db, notification),
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
