from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from backend.models import Game, Notification, SubPost

VALID_NOTIFICATION_TYPES = {
    "booking_confirmed",
    "booking_cancelled",
    "booking_refunded",
    "payment_failed",
    "game_cancelled",
    "game_updated",
    "game_reminder",
    "waitlist_joined",
    "waitlist_promoted",
    "waitlist_expired",
    "host_update",
    "chat_message",
    "deposit_paid",
    "deposit_released",
    "deposit_forfeited",
    "admin_notice",
    "support_reply",
    "account_security",
    "policy_update",
    "game_player_added_by_admin",
    "game_player_removed_by_admin",
    "game_host_assigned",
    "game_host_removed",
    "game_roster_update",
    "sub_request_received",
    "sub_request_confirmed",
    "sub_request_declined",
    "sub_waitlist_promoted_to_pending",
    "sub_request_canceled_by_player",
    "sub_request_canceled_by_owner",
    "sub_post_canceled",
    "sub_post_removed",
}
VALID_NOTIFICATION_CATEGORIES = {"app", "game_activity"}
APP_NOTIFICATION_DOMAINS = {"app", "account", "admin", "support"}
GAME_ACTIVITY_DOMAINS = {"game", "need_a_sub"}
VALID_NOTIFICATION_DOMAINS = APP_NOTIFICATION_DOMAINS | GAME_ACTIVITY_DOMAINS
VALID_SOURCE_TYPES = {
    "need_a_sub",
    "official_game",
    "community_game",
    "game",
    "pickup_lane",
    "policy",
    "support",
    "account",
    "payment",
}
VALID_ACTION_KEYS = {
    "view_game",
    "view_sub_post",
    "view_policy",
    "payment_methods",
    "view_profile",
}
APP_NOTIFICATION_TYPE_DOMAINS = {
    "admin_notice": {"app", "admin"},
    "policy_update": {"app", "admin"},
    "support_reply": {"support"},
    "account_security": {"account"},
}
NEED_A_SUB_NOTIFICATION_TYPES = {
    "sub_request_received",
    "sub_request_confirmed",
    "sub_request_declined",
    "sub_waitlist_promoted_to_pending",
    "sub_request_canceled_by_player",
    "sub_request_canceled_by_owner",
    "sub_post_canceled",
    "sub_post_removed",
}
GAME_NOTIFICATION_TYPES = (
    VALID_NOTIFICATION_TYPES
    - set(APP_NOTIFICATION_TYPE_DOMAINS.keys())
    - NEED_A_SUB_NOTIFICATION_TYPES
)

SOURCE_LABEL_BY_TYPE = {
    "need_a_sub": "Need a Sub",
    "official_game": "Official Game",
    "community_game": "Community Game",
    "game": "Game",
    "pickup_lane": "Pickup Lane",
    "policy": "Policy",
    "support": "Support",
    "account": "Account",
    "payment": "Payment",
}
ACTION_LABEL_BY_KEY = {
    "view_game": "View game",
    "view_sub_post": "View post",
    "view_policy": "View policy",
    "payment_methods": "Payment methods",
    "view_profile": "View profile",
}
ICON_BY_NOTIFICATION_TYPE = {
    "account_security": "ShieldCheck",
    "admin_notice": "Megaphone",
    "booking_cancelled": "CalendarX",
    "booking_confirmed": "CalendarDays",
    "booking_refunded": "CircleDollarSign",
    "chat_message": "MessageSquareText",
    "deposit_forfeited": "CircleDollarSign",
    "deposit_paid": "CircleDollarSign",
    "deposit_released": "CircleDollarSign",
    "game_cancelled": "CalendarX",
    "game_host_assigned": "ShieldCheck",
    "game_host_removed": "ShieldCheck",
    "game_player_added_by_admin": "UsersRound",
    "game_player_removed_by_admin": "UsersRound",
    "game_reminder": "Clock3",
    "game_roster_update": "UsersRound",
    "game_updated": "CalendarDays",
    "host_update": "ShieldCheck",
    "payment_failed": "WalletCards",
    "policy_update": "Megaphone",
    "sub_post_canceled": "MapPin",
    "sub_post_removed": "MapPin",
    "sub_request_canceled_by_owner": "ClipboardList",
    "sub_request_canceled_by_player": "ClipboardList",
    "sub_request_confirmed": "ClipboardList",
    "sub_request_declined": "ClipboardList",
    "sub_request_received": "UserPlus",
    "sub_waitlist_promoted_to_pending": "Clock3",
    "support_reply": "Headphones",
    "waitlist_expired": "Clock3",
    "waitlist_joined": "Clock3",
    "waitlist_promoted": "Clock3",
}
SEVERITY_BY_NOTIFICATION_TYPE = {
    "account_security": "warning",
    "booking_cancelled": "danger",
    "booking_confirmed": "success",
    "booking_refunded": "success",
    "deposit_forfeited": "danger",
    "deposit_paid": "success",
    "deposit_released": "success",
    "game_cancelled": "danger",
    "game_host_assigned": "success",
    "game_host_removed": "warning",
    "game_player_removed_by_admin": "danger",
    "payment_failed": "warning",
    "sub_post_canceled": "danger",
    "sub_post_removed": "danger",
    "sub_request_canceled_by_owner": "danger",
    "sub_request_canceled_by_player": "warning",
    "sub_request_confirmed": "success",
    "sub_request_declined": "danger",
    "sub_waitlist_promoted_to_pending": "success",
    "waitlist_expired": "warning",
    "waitlist_promoted": "success",
}
NOTIFICATION_TEMPLATE_BY_TYPE = {
    "admin_notice": {
        "title": "Pickup Lane update",
        "summary": "Pickup Lane posted an update.",
        "body": "Pickup Lane posted an update.",
        "action_key": None,
    },
    "policy_update": {
        "title": "Policy update",
        "summary": "A Pickup Lane policy was updated.",
        "body": "A Pickup Lane policy was updated.",
        "action_key": "view_policy",
    },
    "support_reply": {
        "title": "Support reply",
        "summary": "Support replied to your request.",
        "body": "Support replied to your request.",
        "action_key": None,
    },
    "account_security": {
        "title": "Security alert",
        "summary": "Account security activity was detected.",
        "body": "Account security activity was detected.",
        "action_key": "view_profile",
    },
    "booking_confirmed": {
        "title": "Booking confirmed",
        "summary": "Your booking was confirmed.",
        "body": "Your booking for this game was confirmed.",
        "action_key": "view_game",
    },
    "booking_cancelled": {
        "title": "Booking canceled",
        "summary": "Your booking was canceled.",
        "body": "Your booking for this game was canceled.",
        "action_key": "view_game",
    },
    "booking_refunded": {
        "title": "Refund processed",
        "summary": "Your refund was processed.",
        "body": "Your refund for this game was processed.",
        "action_key": "view_game",
    },
    "payment_failed": {
        "title": "Payment issue",
        "summary": "Your payment needs attention.",
        "body": "Your payment for this game needs attention.",
        "action_key": "payment_methods",
    },
    "game_cancelled": {
        "title": "Game canceled",
        "summary": "This game was canceled.",
        "body": "This game was canceled.",
        "action_key": "view_game",
    },
    "game_updated": {
        "title": "Game update",
        "summary": "Game details were updated.",
        "body": "Game details were updated.",
        "action_key": "view_game",
    },
    "game_reminder": {
        "title": "Game reminder",
        "summary": "This game is coming up.",
        "body": "This game is coming up.",
        "action_key": "view_game",
    },
    "waitlist_joined": {
        "title": "Waitlist update",
        "summary": "You joined the waitlist.",
        "body": "You are on the waitlist for this game.",
        "action_key": "view_game",
    },
    "waitlist_promoted": {
        "title": "Moved into game",
        "summary": "You were moved into the game.",
        "body": "A spot opened and you were moved into this game.",
        "action_key": "view_game",
    },
    "waitlist_expired": {
        "title": "Waitlist expired",
        "summary": "Your waitlist spot expired.",
        "body": "Your waitlist spot for this game expired.",
        "action_key": "view_game",
    },
    "host_update": {
        "title": "Host update",
        "summary": "Host information changed.",
        "body": "Host information for this game changed.",
        "action_key": "view_game",
    },
    "chat_message": {
        "title": "New chat activity",
        "summary": "New messages were posted.",
        "body": "New messages were posted for this game.",
        "action_key": "view_game",
    },
    "deposit_paid": {
        "title": "Deposit paid",
        "summary": "The host deposit was paid.",
        "body": "The host deposit for this game was paid.",
        "action_key": "view_game",
    },
    "deposit_released": {
        "title": "Deposit released",
        "summary": "The host deposit was released.",
        "body": "The host deposit for this game was released.",
        "action_key": "view_game",
    },
    "deposit_forfeited": {
        "title": "Deposit forfeited",
        "summary": "The host deposit was forfeited.",
        "body": "The host deposit for this game was forfeited.",
        "action_key": "view_game",
    },
    "game_player_added_by_admin": {
        "title": "Player added",
        "summary": "A player was added.",
        "body": "A player was added to this game.",
        "action_key": "view_game",
    },
    "game_player_removed_by_admin": {
        "title": "Player removed",
        "summary": "A player was removed.",
        "body": "A player was removed from this game.",
        "action_key": "view_game",
    },
    "game_host_assigned": {
        "title": "Host assigned",
        "summary": "You were assigned as host.",
        "body": "You were assigned as a host for this game.",
        "action_key": "view_game",
    },
    "game_host_removed": {
        "title": "Host removed",
        "summary": "You were removed as host.",
        "body": "You are no longer listed as host for this game.",
        "action_key": "view_game",
    },
    "game_roster_update": {
        "title": "Roster update",
        "summary": "The roster changed.",
        "body": "The roster for this game changed.",
        "action_key": "view_game",
    },
    "sub_request_received": {
        "title": "New request",
        "summary": "A player requested a sub spot.",
        "body": "A player requested a sub spot for this post.",
        "action_key": "view_sub_post",
    },
    "sub_request_confirmed": {
        "title": "Request approved",
        "summary": "Your request was approved.",
        "body": "You're confirmed for this sub spot.",
        "action_key": "view_sub_post",
    },
    "sub_request_declined": {
        "title": "Request declined",
        "summary": "Your request was declined.",
        "body": "Your request for this sub spot was declined.",
        "action_key": "view_sub_post",
    },
    "sub_waitlist_promoted_to_pending": {
        "title": "Moved to review",
        "summary": "A spot opened for review.",
        "body": "A spot opened and the host can now review your request.",
        "action_key": "view_sub_post",
    },
    "sub_request_canceled_by_player": {
        "title": "Request canceled",
        "summary": "A player canceled their request.",
        "body": "A player canceled their request for this sub spot.",
        "action_key": "view_sub_post",
    },
    "sub_request_canceled_by_owner": {
        "title": "Sub spot removed",
        "summary": "The host removed you from this sub spot.",
        "body": "The host removed you from this sub spot.",
        "action_key": "view_sub_post",
    },
    "sub_post_canceled": {
        "title": "Post canceled",
        "summary": "This Need a Sub post was canceled.",
        "body": "This Need a Sub post was canceled by the host.",
        "action_key": "view_sub_post",
    },
    "sub_post_removed": {
        "title": "Post removed",
        "summary": "This Need a Sub post was removed.",
        "body": "This Need a Sub post was removed by Pickup Lane.",
        "action_key": None,
    },
}


def ensure_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value


def source_type_for_game(game: Game | None) -> str:
    if game is None:
        return "game"

    if game.game_type == "official":
        return "official_game"

    if game.game_type == "community":
        return "community_game"

    return "game"


def subject_label_for_game(game: Game) -> str:
    return game.title or f"{game.venue_name_snapshot} {game.format_label}".strip()


def subject_label_for_sub_post(sub_post: SubPost) -> str:
    base_label = (
        sub_post.team_name
        or sub_post.location_name
        or "Need a Sub post"
    )

    if sub_post.format_label:
        return f"{base_label} {sub_post.format_label}"

    return base_label


def get_notification_template(notification_type: str) -> dict[str, str | None]:
    return NOTIFICATION_TEMPLATE_BY_TYPE.get(
        notification_type,
        {
            "title": "Inbox update",
            "summary": "There is a new update.",
            "body": "There is a new update.",
            "action_key": None,
        },
    )


def build_game_notification_fields(
    game: Game,
    notification_type: str,
    *,
    event_at: datetime,
    title: str | None = None,
    summary: str | None = None,
    body: str | None = None,
    action_key: str | None = None,
    aggregation_key: str | None = None,
    aggregate_count: int | None = None,
) -> dict[str, object]:
    template = get_notification_template(notification_type)

    return {
        "source_type": source_type_for_game(game),
        "title": title or template["title"],
        "subject_label": subject_label_for_game(game),
        "summary": summary or template["summary"],
        "body": body or template["body"],
        "action_key": action_key if action_key is not None else template["action_key"],
        "subject_starts_at": game.starts_at,
        "subject_ends_at": game.ends_at,
        "subject_timezone": game.timezone or "America/Chicago",
        "event_at": ensure_aware_utc(event_at),
        "aggregation_key": aggregation_key,
        "aggregate_count": aggregate_count,
    }


def build_need_a_sub_notification_fields(
    sub_post: SubPost,
    notification_type: str,
    *,
    event_at: datetime,
    title: str | None = None,
    summary: str | None = None,
    body: str | None = None,
    action_key: str | None = None,
) -> dict[str, object]:
    template = get_notification_template(notification_type)

    return {
        "source_type": "need_a_sub",
        "title": title or template["title"],
        "subject_label": subject_label_for_sub_post(sub_post),
        "summary": summary or template["summary"],
        "body": body or template["body"],
        "action_key": action_key if action_key is not None else template["action_key"],
        "subject_starts_at": sub_post.starts_at,
        "subject_ends_at": sub_post.ends_at,
        "subject_timezone": sub_post.timezone or "America/Chicago",
        "event_at": ensure_aware_utc(event_at),
        "aggregation_key": None,
        "aggregate_count": None,
    }


def build_app_notification_fields(
    notification_type: str,
    *,
    event_at: datetime,
    source_type: str | None = None,
    subject_label: str | None = None,
    title: str | None = None,
    summary: str | None = None,
    body: str | None = None,
    action_key: str | None = None,
) -> dict[str, object]:
    template = get_notification_template(notification_type)
    effective_source_type = source_type or source_type_for_app_notification(
        notification_type
    )

    return {
        "source_type": effective_source_type,
        "title": title or template["title"],
        "subject_label": subject_label
        or subject_label_for_app_notification(notification_type, effective_source_type),
        "summary": summary or template["summary"],
        "body": body or template["body"],
        "action_key": action_key if action_key is not None else template["action_key"],
        "subject_starts_at": None,
        "subject_ends_at": None,
        "subject_timezone": None,
        "event_at": ensure_aware_utc(event_at),
        "aggregation_key": None,
        "aggregate_count": None,
    }


def source_type_for_app_notification(notification_type: str) -> str:
    if notification_type == "policy_update":
        return "policy"
    if notification_type == "support_reply":
        return "support"
    if notification_type == "account_security":
        return "account"

    return "pickup_lane"


def subject_label_for_app_notification(
    notification_type: str,
    source_type: str,
) -> str:
    if notification_type == "account_security":
        return "Your account"
    if notification_type == "support_reply":
        return "Support"
    if notification_type == "policy_update":
        return "Pickup Lane"
    if source_type == "payment":
        return "Payment methods"

    return "Pickup Lane"


def notification_source_domain_matches(
    notification_domain: str,
    source_type: str,
) -> bool:
    if notification_domain == "need_a_sub":
        return source_type == "need_a_sub"
    if notification_domain == "game":
        return source_type in {"official_game", "community_game", "game"}
    if notification_domain == "support":
        return source_type == "support"
    if notification_domain == "account":
        return source_type in {"account", "payment"}
    if notification_domain in {"app", "admin"}:
        return source_type in {"pickup_lane", "policy", "payment"}

    return False


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
        if game is None or game.deleted_at is not None:
            return None

        return build_action_payload(action_key, f"/games/{notification.related_game_id}")

    if action_key == "view_sub_post":
        if notification.related_sub_post_id is None:
            return None

        sub_post = db.get(SubPost, notification.related_sub_post_id)
        if sub_post is None or sub_post.post_status == "removed":
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


def build_action_payload(action_key: str, path: str) -> dict[str, str]:
    return {
        "key": action_key,
        "label": ACTION_LABEL_BY_KEY[action_key],
        "path": path,
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
        "related_participant_id": notification.related_participant_id,
        "related_message_id": notification.related_message_id,
        "related_sub_post_id": notification.related_sub_post_id,
        "related_sub_post_request_id": notification.related_sub_post_request_id,
        "related_sub_post_position_id": notification.related_sub_post_position_id,
        "is_read": notification.is_read,
        "read_at": notification.read_at,
        "created_at": notification.created_at,
        "updated_at": notification.updated_at,
    }
