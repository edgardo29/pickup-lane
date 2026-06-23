from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import uuid
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import (
    Booking,
    ChatMessage,
    Game,
    GameChat,
    GameParticipant,
    Notification,
    Payment,
    Refund,
    SubPost,
    SubPostChat,
    SubPostChatMessage,
    SubPostPosition,
    SubPostRequest,
    User,
)
from backend.schemas.notification_schema import NotificationCreate, NotificationUpdate
from backend.services.admin_action_service import record_admin_action
from backend.services.admin_permission_service import (
    PERMISSION_NOTIFICATIONS_MANAGE,
    PERMISSION_NOTIFICATIONS_READ,
    require_user_admin_permission,
    user_has_admin_permission,
)

VALID_NOTIFICATION_PREFERENCE_CLASSES = {
    "mandatory",
    "preference_controlled",
    "conditional",
}


@dataclass(frozen=True)
class NotificationTypeConfig:
    notification_category: str
    notification_domains: frozenset[str]
    title: str
    summary: str
    body: str
    action_key: str | None
    icon: str
    severity: str = "default"
    preference_class: str = "mandatory"
    implementation_status: str = "planned"


NOTIFICATION_TYPE_CONFIG = {
    "admin_notice": NotificationTypeConfig(
        notification_category="app",
        notification_domains=frozenset({"app", "admin"}),
        title="Pickup Lane update",
        summary="Pickup Lane posted an update.",
        body="Pickup Lane posted an update.",
        action_key=None,
        icon="Megaphone",
        preference_class="conditional",
        implementation_status="planned_if_tooling",
    ),
    "policy_update": NotificationTypeConfig(
        notification_category="app",
        notification_domains=frozenset({"app", "admin"}),
        title="Policy update",
        summary="A Pickup Lane policy was updated.",
        body="A Pickup Lane policy was updated.",
        action_key="view_policy",
        icon="Megaphone",
        preference_class="conditional",
        implementation_status="planned_if_tooling",
    ),
    "support_reply": NotificationTypeConfig(
        notification_category="app",
        notification_domains=frozenset({"support"}),
        title="Support reply",
        summary="Support replied to your request.",
        body="Support replied to your request.",
        action_key=None,
        icon="Headphones",
        preference_class="preference_controlled",
        implementation_status="blocked",
    ),
    "account_security": NotificationTypeConfig(
        notification_category="app",
        notification_domains=frozenset({"account"}),
        title="Security alert",
        summary="Account security activity was detected.",
        body="Account security activity was detected.",
        action_key="view_profile",
        icon="ShieldCheck",
        severity="warning",
        preference_class="mandatory",
        implementation_status="blocked",
    ),
    "booking_confirmed": NotificationTypeConfig(
        notification_category="game_activity",
        notification_domains=frozenset({"game"}),
        title="Booking confirmed",
        summary="Your booking was confirmed.",
        body="Your booking for this game was confirmed.",
        action_key="view_game",
        icon="CalendarDays",
        severity="success",
    ),
    "booking_cancelled": NotificationTypeConfig(
        notification_category="game_activity",
        notification_domains=frozenset({"game"}),
        title="Booking canceled",
        summary="Your booking was canceled.",
        body="Your booking for this game was canceled.",
        action_key="view_game",
        icon="CalendarX",
        severity="danger",
        preference_class="conditional",
        implementation_status="valid_only",
    ),
    "booking_refunded": NotificationTypeConfig(
        notification_category="game_activity",
        notification_domains=frozenset({"game"}),
        title="Refund processed",
        summary="Your refund was processed.",
        body="Your refund for this game was processed.",
        action_key="view_game",
        icon="CircleDollarSign",
        severity="success",
    ),
    "payment_failed": NotificationTypeConfig(
        notification_category="game_activity",
        notification_domains=frozenset({"game"}),
        title="Payment failed",
        summary="Your payment could not be completed.",
        body="Your payment for this game could not be completed.",
        action_key="view_game",
        icon="WalletCards",
        severity="warning",
    ),
    "game_cancelled": NotificationTypeConfig(
        notification_category="game_activity",
        notification_domains=frozenset({"game"}),
        title="Game canceled",
        summary="This game was canceled.",
        body="This game was canceled.",
        action_key="view_game",
        icon="CalendarX",
        severity="danger",
    ),
    "game_updated": NotificationTypeConfig(
        notification_category="game_activity",
        notification_domains=frozenset({"game"}),
        title="Game updated",
        summary="Important game details were updated.",
        body="Review the latest game details before heading out.",
        action_key="view_game",
        icon="CalendarDays",
    ),
    "game_reminder": NotificationTypeConfig(
        notification_category="game_activity",
        notification_domains=frozenset({"game"}),
        title="Game reminder",
        summary="This game is coming up.",
        body="This game is coming up.",
        action_key="view_game",
        icon="Clock3",
        implementation_status="valid_only",
    ),
    "waitlist_joined": NotificationTypeConfig(
        notification_category="game_activity",
        notification_domains=frozenset({"game"}),
        title="Waitlist update",
        summary="You joined the waitlist.",
        body="You are on the waitlist for this game.",
        action_key="view_game",
        icon="Clock3",
        implementation_status="valid_only",
    ),
    "waitlist_promoted": NotificationTypeConfig(
        notification_category="game_activity",
        notification_domains=frozenset({"game"}),
        title="Moved into game",
        summary="You were moved into the game.",
        body="A spot opened and you were moved into this game.",
        action_key="view_game",
        icon="Clock3",
        severity="success",
    ),
    "waitlist_expired": NotificationTypeConfig(
        notification_category="game_activity",
        notification_domains=frozenset({"game"}),
        title="Waitlist expired",
        summary="Your waitlist spot expired.",
        body="Your waitlist spot for this game expired.",
        action_key="view_game",
        icon="Clock3",
        severity="warning",
        preference_class="conditional",
        implementation_status="valid_only",
    ),
    "host_update": NotificationTypeConfig(
        notification_category="game_activity",
        notification_domains=frozenset({"game"}),
        title="Host update",
        summary="Host information changed.",
        body="Host information for this game changed.",
        action_key="view_game",
        icon="ShieldCheck",
        implementation_status="valid_only",
    ),
    "chat_message": NotificationTypeConfig(
        notification_category="game_activity",
        notification_domains=frozenset({"game"}),
        title="New chat activity",
        summary="New messages were posted.",
        body="New messages were posted for this game.",
        action_key="view_game",
        icon="MessageSquareText",
    ),
    "deposit_paid": NotificationTypeConfig(
        notification_category="game_activity",
        notification_domains=frozenset({"game"}),
        title="Deposit paid",
        summary="The host deposit was paid.",
        body="The host deposit for this game was paid.",
        action_key="view_game",
        icon="CircleDollarSign",
        severity="success",
        implementation_status="valid_only",
    ),
    "deposit_released": NotificationTypeConfig(
        notification_category="game_activity",
        notification_domains=frozenset({"game"}),
        title="Deposit released",
        summary="The host deposit was released.",
        body="The host deposit for this game was released.",
        action_key="view_game",
        icon="CircleDollarSign",
        severity="success",
        implementation_status="valid_only",
    ),
    "deposit_forfeited": NotificationTypeConfig(
        notification_category="game_activity",
        notification_domains=frozenset({"game"}),
        title="Deposit forfeited",
        summary="The host deposit was forfeited.",
        body="The host deposit for this game was forfeited.",
        action_key="view_game",
        icon="CircleDollarSign",
        severity="danger",
        implementation_status="valid_only",
    ),
    "game_player_added_by_admin": NotificationTypeConfig(
        notification_category="game_activity",
        notification_domains=frozenset({"game"}),
        title="Player added",
        summary="You were added to this official game.",
        body="Pickup Lane added you to this official game.",
        action_key="view_game",
        icon="UsersRound",
        severity="success",
    ),
    "game_player_removed_by_admin": NotificationTypeConfig(
        notification_category="game_activity",
        notification_domains=frozenset({"game"}),
        title="Player removed",
        summary="You were removed from this official game.",
        body="Pickup Lane removed you from this official game.",
        action_key="view_game",
        icon="UsersRound",
        severity="danger",
    ),
    "game_host_assigned": NotificationTypeConfig(
        notification_category="game_activity",
        notification_domains=frozenset({"game"}),
        title="Host assigned",
        summary="You were assigned as host.",
        body="You were assigned as a host for this game.",
        action_key="view_game",
        icon="ShieldCheck",
        severity="success",
    ),
    "game_host_removed": NotificationTypeConfig(
        notification_category="game_activity",
        notification_domains=frozenset({"game"}),
        title="Host removed",
        summary="You were removed as host.",
        body="You are no longer listed as host for this game.",
        action_key="view_game",
        icon="ShieldCheck",
        severity="warning",
    ),
    "game_roster_update": NotificationTypeConfig(
        notification_category="game_activity",
        notification_domains=frozenset({"game"}),
        title="Roster update",
        summary="The roster changed.",
        body="The roster for this game changed.",
        action_key="view_game",
        icon="UsersRound",
        preference_class="conditional",
        implementation_status="valid_only",
    ),
    "sub_request_received": NotificationTypeConfig(
        notification_category="game_activity",
        notification_domains=frozenset({"need_a_sub"}),
        title="New request",
        summary="A player requested a sub spot.",
        body="A player requested a sub spot for this post.",
        action_key="view_sub_post",
        icon="UserPlus",
    ),
    "sub_request_confirmed": NotificationTypeConfig(
        notification_category="game_activity",
        notification_domains=frozenset({"need_a_sub"}),
        title="Request approved",
        summary="Your request was approved.",
        body="You're confirmed for this sub spot.",
        action_key="view_sub_post",
        icon="ClipboardList",
        severity="success",
    ),
    "sub_request_declined": NotificationTypeConfig(
        notification_category="game_activity",
        notification_domains=frozenset({"need_a_sub"}),
        title="Request declined",
        summary="Your request was declined.",
        body="Your request for this sub spot was declined.",
        action_key="view_sub_post",
        icon="ClipboardList",
        severity="danger",
    ),
    "sub_waitlist_promoted_to_pending": NotificationTypeConfig(
        notification_category="game_activity",
        notification_domains=frozenset({"need_a_sub"}),
        title="Moved to review",
        summary="A spot opened for review.",
        body="A spot opened and the host can now review your request.",
        action_key="view_sub_post",
        icon="Clock3",
        severity="success",
    ),
    "sub_request_canceled_by_player": NotificationTypeConfig(
        notification_category="game_activity",
        notification_domains=frozenset({"need_a_sub"}),
        title="Request canceled",
        summary="A player canceled their request.",
        body="A player canceled their request for this sub spot.",
        action_key="view_sub_post",
        icon="ClipboardList",
        severity="warning",
    ),
    "sub_request_canceled_by_owner": NotificationTypeConfig(
        notification_category="game_activity",
        notification_domains=frozenset({"need_a_sub"}),
        title="Sub spot removed",
        summary="The host removed you from this sub spot.",
        body="The host removed you from this sub spot.",
        action_key="view_sub_post",
        icon="ClipboardList",
        severity="danger",
    ),
    "sub_post_canceled": NotificationTypeConfig(
        notification_category="game_activity",
        notification_domains=frozenset({"need_a_sub"}),
        title="Post canceled",
        summary="This Need a Sub post was canceled.",
        body="This Need a Sub post was canceled by the host.",
        action_key=None,
        icon="MapPin",
        severity="danger",
    ),
    "sub_post_removed": NotificationTypeConfig(
        notification_category="game_activity",
        notification_domains=frozenset({"need_a_sub"}),
        title="Post removed",
        summary="This Need a Sub post was removed.",
        body="This Need a Sub post was removed by Pickup Lane.",
        action_key=None,
        icon="MapPin",
        severity="danger",
    ),
    "sub_post_updated": NotificationTypeConfig(
        notification_category="game_activity",
        notification_domains=frozenset({"need_a_sub"}),
        title="Post updated",
        summary="Important details were updated.",
        body="Review the latest details before the game.",
        action_key="view_sub_post",
        icon="CalendarDays",
    ),
    "sub_chat_message": NotificationTypeConfig(
        notification_category="game_activity",
        notification_domains=frozenset({"need_a_sub"}),
        title="New chat message",
        summary="New messages were posted.",
        body="New messages were posted in the Need a Sub chat.",
        action_key="view_sub_post",
        icon="MessageSquareText",
        preference_class="preference_controlled",
    ),
}
VALID_NOTIFICATION_TYPES = set(NOTIFICATION_TYPE_CONFIG)
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
GAME_STATUSES_WITH_DISABLED_INBOX_ACTIONS = {"cancelled", "abandoned"}
SUB_POST_STATUSES_WITH_INBOX_ACTIONS = {"active", "filled"}
SUB_CHAT_MESSAGE_ACTION_POST_STATUSES = {"active", "filled", "expired"}
SUB_CHAT_MESSAGE_ACTION_GRACE_HOURS = 24
AGGREGATE_COUNT_MODES = {"replace", "increment", "clear", "preserve"}
AGGREGATED_NOTIFICATION_ASSIGNABLE_FIELDS = {
    "source_type",
    "title",
    "subject_label",
    "summary",
    "body",
    "action_key",
    "subject_starts_at",
    "subject_ends_at",
    "subject_timezone",
    "event_at",
    "aggregation_key",
    "aggregate_count",
    "related_game_id",
    "related_booking_id",
    "related_participant_id",
    "related_chat_id",
    "related_message_id",
    "related_sub_post_id",
    "related_sub_post_chat_id",
    "related_sub_post_chat_message_id",
    "related_sub_post_request_id",
    "related_sub_post_position_id",
    "related_payment_id",
    "related_refund_id",
    "actor_user_id",
}
RESOLVED_NOTIFICATION_ASSIGNABLE_FIELDS = (
    AGGREGATED_NOTIFICATION_ASSIGNABLE_FIELDS - {"event_at", "aggregation_key"}
)
APP_NOTIFICATION_TYPE_DOMAINS = {
    notification_type: set(config.notification_domains)
    for notification_type, config in NOTIFICATION_TYPE_CONFIG.items()
    if config.notification_category == "app"
}
NEED_A_SUB_NOTIFICATION_TYPES = {
    notification_type
    for notification_type, config in NOTIFICATION_TYPE_CONFIG.items()
    if config.notification_domains == frozenset({"need_a_sub"})
}
GAME_NOTIFICATION_TYPES = {
    notification_type
    for notification_type, config in NOTIFICATION_TYPE_CONFIG.items()
    if config.notification_domains == frozenset({"game"})
}

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
    notification_type: config.icon
    for notification_type, config in NOTIFICATION_TYPE_CONFIG.items()
}
SEVERITY_BY_NOTIFICATION_TYPE = {
    notification_type: config.severity
    for notification_type, config in NOTIFICATION_TYPE_CONFIG.items()
}
NOTIFICATION_PREFERENCE_CLASS_BY_TYPE = {
    notification_type: config.preference_class
    for notification_type, config in NOTIFICATION_TYPE_CONFIG.items()
}
NOTIFICATION_IMPLEMENTATION_STATUS_BY_TYPE = {
    notification_type: config.implementation_status
    for notification_type, config in NOTIFICATION_TYPE_CONFIG.items()
}
NOTIFICATION_TEMPLATE_BY_TYPE = {
    notification_type: {
        "title": config.title,
        "summary": config.summary,
        "body": config.body,
        "action_key": config.action_key,
    }
    for notification_type, config in NOTIFICATION_TYPE_CONFIG.items()
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


def resolve_template_action_key(
    template_action_key: str | None,
    action_key: str | None,
    force_action_null: bool,
) -> str | None:
    if force_action_null:
        return None

    return action_key if action_key is not None else template_action_key


def build_game_notification_fields(
    game: Game,
    notification_type: str,
    *,
    event_at: datetime,
    title: str | None = None,
    summary: str | None = None,
    body: str | None = None,
    action_key: str | None = None,
    force_action_null: bool = False,
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
        "action_key": resolve_template_action_key(
            template["action_key"],
            action_key,
            force_action_null,
        ),
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
    force_action_null: bool = False,
    aggregation_key: str | None = None,
    aggregate_count: int | None = None,
) -> dict[str, object]:
    template = get_notification_template(notification_type)

    return {
        "source_type": "need_a_sub",
        "title": title or template["title"],
        "subject_label": subject_label_for_sub_post(sub_post),
        "summary": summary or template["summary"],
        "body": body or template["body"],
        "action_key": resolve_template_action_key(
            template["action_key"],
            action_key,
            force_action_null,
        ),
        "subject_starts_at": sub_post.starts_at,
        "subject_ends_at": sub_post.ends_at,
        "subject_timezone": sub_post.timezone or "America/Chicago",
        "event_at": ensure_aware_utc(event_at),
        "aggregation_key": aggregation_key,
        "aggregate_count": aggregate_count,
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
    force_action_null: bool = False,
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
        "action_key": resolve_template_action_key(
            template["action_key"],
            action_key,
            force_action_null,
        ),
        "subject_starts_at": None,
        "subject_ends_at": None,
        "subject_timezone": None,
        "event_at": ensure_aware_utc(event_at),
        "aggregation_key": None,
        "aggregate_count": None,
    }


def validate_notification_assignment_fields(
    values: dict[str, object],
    *,
    allowed_fields: set[str],
) -> None:
    unknown_fields = set(values) - allowed_fields
    if unknown_fields:
        unknown_list = ", ".join(sorted(unknown_fields))
        raise ValueError(f"Unsupported notification assignment fields: {unknown_list}")


def assign_notification_values(
    notification: Notification,
    values: dict[str, object],
    *,
    allowed_fields: set[str],
) -> None:
    validate_notification_assignment_fields(values, allowed_fields=allowed_fields)

    for field_name, field_value in values.items():
        if field_name == "event_at" and isinstance(field_value, datetime):
            field_value = ensure_aware_utc(field_value)
        setattr(notification, field_name, field_value)


def apply_aggregate_count_mode(
    notification: Notification,
    *,
    aggregate_count_mode: str,
    was_read: bool,
    is_new: bool,
) -> None:
    if aggregate_count_mode not in AGGREGATE_COUNT_MODES:
        raise ValueError(f"Unsupported aggregate_count_mode: {aggregate_count_mode}")

    if aggregate_count_mode == "clear":
        notification.aggregate_count = None
        return

    if aggregate_count_mode == "preserve":
        return

    if aggregate_count_mode == "increment":
        if is_new or was_read:
            notification.aggregate_count = 1
            return

        current_count = notification.aggregate_count
        notification.aggregate_count = (
            current_count if current_count is not None else 1
        ) + 1


def reopen_aggregated_notification(
    db: Session,
    *,
    user_id: UUID,
    notification_type: str,
    notification_category: str,
    notification_domain: str,
    aggregation_key: str,
    values: dict[str, object],
    aggregate_count_mode: str = "replace",
) -> Notification:
    if not aggregation_key.strip():
        raise ValueError("aggregation_key is required")

    notification = (
        db.query(Notification)
        .filter(
            Notification.user_id == user_id,
            Notification.aggregation_key == aggregation_key,
        )
        .one_or_none()
    )
    is_new = notification is None
    was_read = False if is_new else bool(notification.is_read)

    if notification is None:
        notification = Notification(
            id=uuid4(),
            user_id=user_id,
            notification_type=notification_type,
            notification_category=notification_category,
            notification_domain=notification_domain,
            aggregation_key=aggregation_key,
            is_read=False,
            read_at=None,
        )
        db.add(notification)
    else:
        notification.notification_type = notification_type
        notification.notification_category = notification_category
        notification.notification_domain = notification_domain

    assign_notification_values(
        notification,
        values,
        allowed_fields=AGGREGATED_NOTIFICATION_ASSIGNABLE_FIELDS,
    )
    now_value = values.get("event_at")
    effective_now = (
        ensure_aware_utc(now_value)
        if isinstance(now_value, datetime)
        else datetime.now(timezone.utc)
    )
    if is_new:
        notification.created_at = effective_now
    notification.updated_at = effective_now
    notification.aggregation_key = aggregation_key
    notification.is_read = False
    notification.read_at = None
    apply_aggregate_count_mode(
        notification,
        aggregate_count_mode=aggregate_count_mode,
        was_read=was_read,
        is_new=is_new,
    )

    return notification


def resolve_aggregated_notification(
    db: Session,
    *,
    user_id: UUID,
    aggregation_key: str,
    values: dict[str, object] | None = None,
    read_at: datetime | None = None,
) -> Notification | None:
    notification = (
        db.query(Notification)
        .filter(
            Notification.user_id == user_id,
            Notification.aggregation_key == aggregation_key,
        )
        .one_or_none()
    )
    if notification is None:
        return None

    if values:
        assign_notification_values(
            notification,
            values,
            allowed_fields=RESOLVED_NOTIFICATION_ASSIGNABLE_FIELDS,
        )

    effective_read_at = ensure_aware_utc(read_at or datetime.now(timezone.utc))
    notification.is_read = True
    if notification.read_at is None:
        notification.read_at = effective_read_at
    notification.updated_at = effective_read_at

    return notification


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


GAME_RELATED_FIELDS = {
    "related_game_id",
    "related_chat_id",
    "related_booking_id",
    "related_payment_id",
    "related_refund_id",
    "related_participant_id",
    "related_message_id",
}
SUB_RELATED_FIELDS = {
    "related_sub_post_id",
    "related_sub_post_chat_id",
    "related_sub_post_chat_message_id",
    "related_sub_post_request_id",
    "related_sub_post_position_id",
}
IMMUTABLE_NOTIFICATION_UPDATE_FIELDS = {
    "notification_type",
    "notification_category",
    "notification_domain",
    "source_type",
    "title",
    "subject_label",
    "summary",
    "body",
    "action_key",
    "subject_starts_at",
    "subject_ends_at",
    "subject_timezone",
    "event_at",
    "aggregation_key",
    "aggregate_count",
    "actor_user_id",
    "related_game_id",
    "related_chat_id",
    "related_booking_id",
    "related_payment_id",
    "related_refund_id",
    "related_participant_id",
    "related_message_id",
    "related_sub_post_id",
    "related_sub_post_chat_id",
    "related_sub_post_chat_message_id",
    "related_sub_post_request_id",
    "related_sub_post_position_id",
}


def build_notification_conflict_detail(exc: IntegrityError) -> str:
    return str(exc.orig)


def get_active_user_or_404(
    db: Session,
    user_id: uuid.UUID,
    detail: str = "User not found.",
) -> User:
    db_user = db.get(User, user_id)

    if db_user is None or db_user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )

    return db_user


def get_visible_notification_or_404(
    db: Session,
    notification_id: uuid.UUID,
    current_user: User,
    *,
    allow_admin_read: bool,
) -> Notification:
    db_notification = db.get(Notification, notification_id)

    if db_notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found.",
        )

    if db_notification.user_id == current_user.id:
        return db_notification

    if allow_admin_read and user_has_admin_permission(
        current_user,
        PERMISSION_NOTIFICATIONS_READ,
    ):
        require_user_admin_permission(current_user, PERMISSION_NOTIFICATIONS_READ)
        return db_notification

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Notification not found.",
    )


def validate_notification_business_rules(
    notification_data: dict[str, object],
) -> None:
    for field_name in (
        "user_id",
        "notification_type",
        "notification_category",
        "notification_domain",
        "source_type",
        "title",
        "subject_label",
        "summary",
        "body",
        "event_at",
        "is_read",
    ):
        if notification_data[field_name] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} cannot be null.",
            )

    notification_type = notification_data["notification_type"]
    if notification_type not in VALID_NOTIFICATION_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="notification_type is not supported.",
        )

    notification_category = notification_data["notification_category"]
    if notification_category not in VALID_NOTIFICATION_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="notification_category is not supported.",
        )

    notification_domain = notification_data["notification_domain"]
    if notification_domain not in VALID_NOTIFICATION_DOMAINS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="notification_domain is not supported.",
        )

    source_type = notification_data["source_type"]
    if source_type not in VALID_SOURCE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="source_type is not supported.",
        )

    if not notification_source_domain_matches(notification_domain, source_type):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="source_type does not match notification_domain.",
        )

    action_key = notification_data.get("action_key")
    if action_key is not None and action_key not in VALID_ACTION_KEYS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="action_key is not supported.",
        )

    if (
        notification_category == "app"
        and notification_domain not in APP_NOTIFICATION_DOMAINS
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="App notifications must use an app notification domain.",
        )

    if (
        notification_category == "game_activity"
        and notification_domain not in GAME_ACTIVITY_DOMAINS
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game activity notifications must use a game activity domain.",
        )

    app_type_domains = APP_NOTIFICATION_TYPE_DOMAINS.get(notification_type)
    if app_type_domains is not None:
        if (
            notification_category != "app"
            or notification_domain not in app_type_domains
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "notification_type does not match notification_category "
                    "and notification_domain."
                ),
            )
    elif notification_type in NEED_A_SUB_NOTIFICATION_TYPES:
        if (
            notification_category != "game_activity"
            or notification_domain != "need_a_sub"
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Need a Sub notification types must use the Need a Sub "
                    "game activity domain."
                ),
            )
    elif notification_type in GAME_NOTIFICATION_TYPES:
        if notification_category != "game_activity" or notification_domain != "game":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Game notification types must use the game activity domain.",
            )

    if not str(notification_data["title"]).strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="title must not be empty.",
        )

    if not str(notification_data["subject_label"]).strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="subject_label must not be empty.",
        )

    if not str(notification_data["summary"]).strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="summary must not be empty.",
        )

    if not str(notification_data["body"]).strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="body must not be empty.",
        )

    subject_timezone = notification_data.get("subject_timezone")
    if subject_timezone is not None and not str(subject_timezone).strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="subject_timezone must not be empty.",
        )

    if (
        notification_data.get("subject_starts_at") is not None
        and subject_timezone is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="subject_timezone is required when subject_starts_at is set.",
        )

    subject_ends_at = notification_data.get("subject_ends_at")
    subject_starts_at = notification_data.get("subject_starts_at")
    if (
        subject_ends_at is not None
        and subject_starts_at is not None
        and subject_ends_at < subject_starts_at
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="subject_ends_at cannot be before subject_starts_at.",
        )

    aggregation_key = notification_data.get("aggregation_key")
    aggregate_count = notification_data.get("aggregate_count")
    if aggregation_key is not None and not str(aggregation_key).strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="aggregation_key must not be empty.",
        )

    if aggregate_count is not None and aggregate_count < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="aggregate_count must be at least 1.",
        )

    if aggregate_count is not None and aggregation_key is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="aggregation_key is required when aggregate_count is set.",
        )

    if action_key == "view_game" and notification_data.get("related_game_id") is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="view_game notifications require related_game_id.",
        )

    if (
        action_key == "view_sub_post"
        and notification_data.get("related_sub_post_id") is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="view_sub_post notifications require related_sub_post_id.",
        )

    if (
        notification_data.get("actor_user_id") is not None
        and notification_data["actor_user_id"] == notification_data["user_id"]
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="actor_user_id cannot match user_id.",
        )

    has_game_relation = any(
        notification_data[field_name] is not None
        for field_name in GAME_RELATED_FIELDS
    )
    has_sub_relation = any(
        notification_data[field_name] is not None
        for field_name in SUB_RELATED_FIELDS
    )

    if has_game_relation and has_sub_relation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Notifications cannot mix game and Need a Sub related records.",
        )

    if has_game_relation and notification_domain != "game":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game related records require notification_domain 'game'.",
        )

    if has_sub_relation and notification_domain != "need_a_sub":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Need a Sub related records require notification_domain 'need_a_sub'.",
        )


def normalize_notification_lifecycle_fields(
    notification_data: dict[str, object],
    existing_notification: Notification | None = None,
) -> dict[str, object]:
    normalized_data = dict(notification_data)

    for field_name in (
        "event_at",
        "subject_starts_at",
        "subject_ends_at",
        "read_at",
    ):
        field_value = normalized_data.get(field_name)
        if isinstance(field_value, datetime):
            normalized_data[field_name] = ensure_aware_utc(field_value)

    if normalized_data["is_read"]:
        normalized_data["read_at"] = (
            normalized_data.get("read_at")
            or (
                existing_notification.read_at
                if existing_notification is not None
                else None
            )
            or datetime.now(timezone.utc)
        )
    else:
        normalized_data["read_at"] = None

    return normalized_data


def validate_notification_references(
    db: Session,
    notification_data: dict[str, object],
) -> None:
    get_active_user_or_404(db, notification_data["user_id"])

    if notification_data["actor_user_id"] is not None:
        get_active_user_or_404(
            db,
            notification_data["actor_user_id"],
            "Actor user not found.",
        )

    db_game = None
    if notification_data["related_game_id"] is not None:
        db_game = db.get(Game, notification_data["related_game_id"])

        if db_game is None or db_game.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Related game not found.",
            )

        expected_source_type = source_type_for_game(db_game)
        if notification_data["source_type"] != expected_source_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="source_type must match the related game's game_type.",
            )

    db_chat = None
    if notification_data["related_chat_id"] is not None:
        db_chat = db.get(GameChat, notification_data["related_chat_id"])

        if db_chat is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Related game chat not found.",
            )

        if (
            notification_data["related_game_id"] is not None
            and db_chat.game_id != notification_data["related_game_id"]
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="related_chat_id must belong to related_game_id.",
            )

    db_booking = None
    if notification_data["related_booking_id"] is not None:
        db_booking = db.get(Booking, notification_data["related_booking_id"])

        if db_booking is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Related booking not found.",
            )

        if (
            notification_data["related_game_id"] is not None
            and db_booking.game_id != notification_data["related_game_id"]
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="related_booking_id must belong to related_game_id.",
            )

    db_payment = None
    if notification_data["related_payment_id"] is not None:
        db_payment = db.get(Payment, notification_data["related_payment_id"])

        if db_payment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Related payment not found.",
            )

        if (
            notification_data["related_booking_id"] is not None
            and db_payment.booking_id != notification_data["related_booking_id"]
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="related_payment_id must belong to related_booking_id.",
            )

        if notification_data["related_game_id"] is not None:
            payment_game_matches = db_payment.game_id == notification_data["related_game_id"]
            payment_booking_game_matches = (
                db_booking is not None
                and db_payment.booking_id == db_booking.id
                and db_booking.game_id == notification_data["related_game_id"]
            )

            if not payment_game_matches and not payment_booking_game_matches:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="related_payment_id must belong to related_game_id.",
                )

    if notification_data["related_refund_id"] is not None:
        db_refund = db.get(Refund, notification_data["related_refund_id"])

        if db_refund is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Related refund not found.",
            )

        if (
            notification_data["related_payment_id"] is not None
            and db_refund.payment_id != notification_data["related_payment_id"]
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="related_refund_id must belong to related_payment_id.",
            )

        if (
            notification_data["related_booking_id"] is not None
            and db_refund.booking_id is not None
            and db_refund.booking_id != notification_data["related_booking_id"]
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="related_refund_id must belong to related_booking_id.",
            )

        if (
            notification_data["related_game_id"] is not None
            and db_refund.booking_id is not None
        ):
            refund_booking = db_booking
            if refund_booking is None or refund_booking.id != db_refund.booking_id:
                refund_booking = db.get(Booking, db_refund.booking_id)

            if (
                refund_booking is None
                or refund_booking.game_id != notification_data["related_game_id"]
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="related_refund_id must belong to related_game_id.",
                )

    if notification_data["related_participant_id"] is not None:
        db_participant = db.get(
            GameParticipant,
            notification_data["related_participant_id"],
        )

        if db_participant is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Related participant not found.",
            )

        if (
            notification_data["related_game_id"] is not None
            and db_participant.game_id != notification_data["related_game_id"]
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="related_participant_id must belong to related_game_id.",
            )

        if (
            notification_data["related_booking_id"] is not None
            and db_participant.booking_id != notification_data["related_booking_id"]
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="related_participant_id must belong to related_booking_id.",
            )

    if notification_data["related_message_id"] is not None:
        db_message = db.get(ChatMessage, notification_data["related_message_id"])

        if db_message is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Related chat message not found.",
            )

        if (
            notification_data["related_chat_id"] is not None
            and db_message.chat_id != notification_data["related_chat_id"]
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="related_message_id must belong to related_chat_id.",
            )

        if (
            notification_data["related_chat_id"] is None
            and notification_data["related_game_id"] is not None
        ):
            db_message_chat = db.get(GameChat, db_message.chat_id)

            if (
                db_message_chat is None
                or db_message_chat.game_id != notification_data["related_game_id"]
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="related_message_id must belong to related_game_id.",
                )

    db_sub_post = None
    if notification_data["related_sub_post_id"] is not None:
        db_sub_post = db.get(SubPost, notification_data["related_sub_post_id"])

        if db_sub_post is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Related Need a Sub post not found.",
            )

    db_sub_post_chat = None
    if notification_data["related_sub_post_chat_id"] is not None:
        db_sub_post_chat = db.get(
            SubPostChat,
            notification_data["related_sub_post_chat_id"],
        )

        if db_sub_post_chat is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Related Need a Sub chat not found.",
            )

        if (
            db_sub_post is not None
            and db_sub_post_chat.sub_post_id != db_sub_post.id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="related_sub_post_chat_id must belong to related_sub_post_id.",
            )

    if notification_data["related_sub_post_chat_message_id"] is not None:
        db_sub_chat_message = db.get(
            SubPostChatMessage,
            notification_data["related_sub_post_chat_message_id"],
        )

        if db_sub_chat_message is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Related Need a Sub chat message not found.",
            )

        if (
            db_sub_post_chat is not None
            and db_sub_chat_message.chat_id != db_sub_post_chat.id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "related_sub_post_chat_message_id must belong to "
                    "related_sub_post_chat_id."
                ),
            )

        if db_sub_post_chat is None and db_sub_post is not None:
            db_sub_message_chat = db.get(SubPostChat, db_sub_chat_message.chat_id)

            if (
                db_sub_message_chat is None
                or db_sub_message_chat.sub_post_id != db_sub_post.id
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "related_sub_post_chat_message_id must belong to "
                        "related_sub_post_id."
                    ),
                )

    db_sub_position = None
    if notification_data["related_sub_post_position_id"] is not None:
        db_sub_position = db.get(
            SubPostPosition,
            notification_data["related_sub_post_position_id"],
        )

        if db_sub_position is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Related Need a Sub position not found.",
            )

        if (
            db_sub_post is not None
            and db_sub_position.sub_post_id != db_sub_post.id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="related_sub_post_position_id must belong to related_sub_post_id.",
            )

    if notification_data["related_sub_post_request_id"] is not None:
        db_sub_request = db.get(
            SubPostRequest,
            notification_data["related_sub_post_request_id"],
        )

        if db_sub_request is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Related Need a Sub request not found.",
            )

        if db_sub_post is not None and db_sub_request.sub_post_id != db_sub_post.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="related_sub_post_request_id must belong to related_sub_post_id.",
            )

        if (
            db_sub_position is not None
            and db_sub_request.sub_post_position_id != db_sub_position.id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "related_sub_post_request_id must belong to "
                    "related_sub_post_position_id."
                ),
            )


def require_notification_create_access(current_user: User) -> None:
    require_user_admin_permission(current_user, PERMISSION_NOTIFICATIONS_MANAGE)


def validate_notification_update_fields(update_data: dict[str, object]) -> None:
    immutable_fields = IMMUTABLE_NOTIFICATION_UPDATE_FIELDS & update_data.keys()

    if immutable_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Notification content and related records cannot be changed "
                "after creation."
            ),
        )


def query_notifications(
    db: Session,
    *,
    user_id: uuid.UUID,
    notification_type: str | None = None,
    notification_category: str | None = None,
    notification_domain: str | None = None,
    is_read: bool | None = None,
    related_game_id: uuid.UUID | None = None,
    related_chat_id: uuid.UUID | None = None,
    related_booking_id: uuid.UUID | None = None,
    related_payment_id: uuid.UUID | None = None,
    related_refund_id: uuid.UUID | None = None,
    related_participant_id: uuid.UUID | None = None,
    related_message_id: uuid.UUID | None = None,
    related_sub_post_id: uuid.UUID | None = None,
    related_sub_post_chat_id: uuid.UUID | None = None,
    related_sub_post_chat_message_id: uuid.UUID | None = None,
    related_sub_post_request_id: uuid.UUID | None = None,
    related_sub_post_position_id: uuid.UUID | None = None,
) -> list[Notification]:
    statement = select(Notification).where(Notification.user_id == user_id)

    if notification_type is not None:
        if notification_type not in VALID_NOTIFICATION_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="notification_type is not supported.",
            )
        statement = statement.where(Notification.notification_type == notification_type)

    if notification_category is not None:
        if notification_category not in VALID_NOTIFICATION_CATEGORIES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="notification_category is not supported.",
            )
        statement = statement.where(
            Notification.notification_category == notification_category
        )

    if notification_domain is not None:
        if notification_domain not in VALID_NOTIFICATION_DOMAINS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="notification_domain is not supported.",
            )
        statement = statement.where(
            Notification.notification_domain == notification_domain
        )

    if is_read is not None:
        statement = statement.where(Notification.is_read == is_read)

    if related_game_id is not None:
        statement = statement.where(Notification.related_game_id == related_game_id)

    if related_chat_id is not None:
        statement = statement.where(Notification.related_chat_id == related_chat_id)

    if related_booking_id is not None:
        statement = statement.where(
            Notification.related_booking_id == related_booking_id
        )

    if related_payment_id is not None:
        statement = statement.where(
            Notification.related_payment_id == related_payment_id
        )

    if related_refund_id is not None:
        statement = statement.where(
            Notification.related_refund_id == related_refund_id
        )

    if related_participant_id is not None:
        statement = statement.where(
            Notification.related_participant_id == related_participant_id
        )

    if related_message_id is not None:
        statement = statement.where(
            Notification.related_message_id == related_message_id
        )

    if related_sub_post_id is not None:
        statement = statement.where(
            Notification.related_sub_post_id == related_sub_post_id
        )

    if related_sub_post_chat_id is not None:
        statement = statement.where(
            Notification.related_sub_post_chat_id == related_sub_post_chat_id
        )

    if related_sub_post_chat_message_id is not None:
        statement = statement.where(
            Notification.related_sub_post_chat_message_id
            == related_sub_post_chat_message_id
        )

    if related_sub_post_request_id is not None:
        statement = statement.where(
            Notification.related_sub_post_request_id == related_sub_post_request_id
        )

    if related_sub_post_position_id is not None:
        statement = statement.where(
            Notification.related_sub_post_position_id == related_sub_post_position_id
        )

    notifications = db.scalars(statement.order_by(Notification.event_at.desc())).all()
    return list(notifications)


def create_notification_workflow(
    db: Session,
    notification: NotificationCreate,
    current_user: User,
) -> dict[str, object]:
    notification_data = normalize_notification_lifecycle_fields(
        notification.model_dump()
    )
    validate_notification_business_rules(notification_data)
    require_notification_create_access(current_user)
    validate_notification_references(db, notification_data)

    new_notification = Notification(
        id=uuid4(),
        **notification_data,
    )

    try:
        db.add(new_notification)
        db.flush()
        record_admin_action(
            db,
            admin_user_id=current_user.id,
            action_type="create_notification",
            target_notification_id=new_notification.id,
            target_user_id=new_notification.user_id,
            metadata={
                "after": {
                    "notification_type": new_notification.notification_type,
                    "notification_category": new_notification.notification_category,
                    "notification_domain": new_notification.notification_domain,
                    "is_read": new_notification.is_read,
                }
            },
        )
        db.commit()
        db.refresh(new_notification)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_notification_conflict_detail(exc),
        ) from exc

    return serialize_notification(db, new_notification)


def list_user_notifications_workflow(
    db: Session,
    *,
    user_id: uuid.UUID,
    notification_type: str | None = None,
    notification_category: str | None = None,
    notification_domain: str | None = None,
    is_read: bool | None = None,
    related_game_id: uuid.UUID | None = None,
    related_chat_id: uuid.UUID | None = None,
    related_booking_id: uuid.UUID | None = None,
    related_payment_id: uuid.UUID | None = None,
    related_refund_id: uuid.UUID | None = None,
    related_participant_id: uuid.UUID | None = None,
    related_message_id: uuid.UUID | None = None,
    related_sub_post_id: uuid.UUID | None = None,
    related_sub_post_chat_id: uuid.UUID | None = None,
    related_sub_post_chat_message_id: uuid.UUID | None = None,
    related_sub_post_request_id: uuid.UUID | None = None,
    related_sub_post_position_id: uuid.UUID | None = None,
) -> list[dict[str, object]]:
    notifications = query_notifications(
        db,
        user_id=user_id,
        notification_type=notification_type,
        notification_category=notification_category,
        notification_domain=notification_domain,
        is_read=is_read,
        related_game_id=related_game_id,
        related_chat_id=related_chat_id,
        related_booking_id=related_booking_id,
        related_payment_id=related_payment_id,
        related_refund_id=related_refund_id,
        related_participant_id=related_participant_id,
        related_message_id=related_message_id,
        related_sub_post_id=related_sub_post_id,
        related_sub_post_chat_id=related_sub_post_chat_id,
        related_sub_post_chat_message_id=related_sub_post_chat_message_id,
        related_sub_post_request_id=related_sub_post_request_id,
        related_sub_post_position_id=related_sub_post_position_id,
    )
    return [
        serialize_notification(db, notification)
        for notification in notifications
    ]


def list_notifications_workflow(
    db: Session,
    current_user: User,
    *,
    user_id: uuid.UUID | None = None,
    notification_type: str | None = None,
    notification_category: str | None = None,
    notification_domain: str | None = None,
    is_read: bool | None = None,
    related_game_id: uuid.UUID | None = None,
    related_chat_id: uuid.UUID | None = None,
    related_booking_id: uuid.UUID | None = None,
    related_payment_id: uuid.UUID | None = None,
    related_refund_id: uuid.UUID | None = None,
    related_participant_id: uuid.UUID | None = None,
    related_message_id: uuid.UUID | None = None,
    related_sub_post_id: uuid.UUID | None = None,
    related_sub_post_chat_id: uuid.UUID | None = None,
    related_sub_post_chat_message_id: uuid.UUID | None = None,
    related_sub_post_request_id: uuid.UUID | None = None,
    related_sub_post_position_id: uuid.UUID | None = None,
) -> list[dict[str, object]]:
    require_user_admin_permission(current_user, PERMISSION_NOTIFICATIONS_READ)
    effective_user_id = current_user.id
    if user_id is not None:
        effective_user_id = user_id

    return list_user_notifications_workflow(
        db,
        user_id=effective_user_id,
        notification_type=notification_type,
        notification_category=notification_category,
        notification_domain=notification_domain,
        is_read=is_read,
        related_game_id=related_game_id,
        related_chat_id=related_chat_id,
        related_booking_id=related_booking_id,
        related_payment_id=related_payment_id,
        related_refund_id=related_refund_id,
        related_participant_id=related_participant_id,
        related_message_id=related_message_id,
        related_sub_post_id=related_sub_post_id,
        related_sub_post_chat_id=related_sub_post_chat_id,
        related_sub_post_chat_message_id=related_sub_post_chat_message_id,
        related_sub_post_request_id=related_sub_post_request_id,
        related_sub_post_position_id=related_sub_post_position_id,
    )


def get_notification_workflow(
    db: Session,
    notification_id: uuid.UUID,
    current_user: User,
) -> dict[str, object]:
    notification = get_visible_notification_or_404(
        db,
        notification_id,
        current_user,
        allow_admin_read=True,
    )
    return serialize_notification(db, notification)


def mark_notification_read_workflow(
    db: Session,
    notification_id: uuid.UUID,
    current_user: User,
) -> dict[str, object]:
    db_notification = get_visible_notification_or_404(
        db,
        notification_id,
        current_user,
        allow_admin_read=False,
    )
    return apply_notification_update(
        db,
        db_notification,
        NotificationUpdate(is_read=True),
    )


def apply_notification_update(
    db: Session,
    db_notification: Notification,
    notification_update: NotificationUpdate,
    *,
    admin_user_id: uuid.UUID | None = None,
) -> dict[str, object]:
    update_data = notification_update.model_dump(exclude_unset=True)

    if "user_id" in update_data and update_data["user_id"] != db_notification.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id cannot be changed for an existing notification.",
        )

    validate_notification_update_fields(update_data)

    effective_notification_data = {
        "user_id": db_notification.user_id,
        "notification_type": db_notification.notification_type,
        "notification_category": db_notification.notification_category,
        "notification_domain": db_notification.notification_domain,
        "source_type": db_notification.source_type,
        "title": db_notification.title,
        "subject_label": db_notification.subject_label,
        "summary": db_notification.summary,
        "body": db_notification.body,
        "action_key": db_notification.action_key,
        "subject_starts_at": db_notification.subject_starts_at,
        "subject_ends_at": db_notification.subject_ends_at,
        "subject_timezone": db_notification.subject_timezone,
        "event_at": db_notification.event_at,
        "aggregation_key": db_notification.aggregation_key,
        "aggregate_count": db_notification.aggregate_count,
        "actor_user_id": db_notification.actor_user_id,
        "related_game_id": db_notification.related_game_id,
        "related_chat_id": db_notification.related_chat_id,
        "related_booking_id": db_notification.related_booking_id,
        "related_payment_id": db_notification.related_payment_id,
        "related_refund_id": db_notification.related_refund_id,
        "related_participant_id": db_notification.related_participant_id,
        "related_message_id": db_notification.related_message_id,
        "related_sub_post_id": db_notification.related_sub_post_id,
        "related_sub_post_chat_id": db_notification.related_sub_post_chat_id,
        "related_sub_post_chat_message_id": (
            db_notification.related_sub_post_chat_message_id
        ),
        "related_sub_post_request_id": db_notification.related_sub_post_request_id,
        "related_sub_post_position_id": db_notification.related_sub_post_position_id,
        "is_read": update_data.get("is_read", db_notification.is_read),
        "read_at": update_data.get("read_at", db_notification.read_at),
    }
    effective_notification_data = normalize_notification_lifecycle_fields(
        effective_notification_data,
        db_notification,
    )
    validate_notification_business_rules(effective_notification_data)
    validate_notification_references(db, effective_notification_data)

    update_data["read_at"] = effective_notification_data["read_at"]

    before_read_state = {
        "is_read": db_notification.is_read,
        "read_at": (
            db_notification.read_at.isoformat()
            if db_notification.read_at is not None
            else None
        ),
    }

    for field_name, field_value in update_data.items():
        setattr(db_notification, field_name, field_value)

    db_notification.updated_at = datetime.now(timezone.utc)

    try:
        db.add(db_notification)
        if admin_user_id is not None:
            record_admin_action(
                db,
                admin_user_id=admin_user_id,
                action_type="update_notification",
                target_notification_id=db_notification.id,
                target_user_id=db_notification.user_id,
                metadata={
                    "before": before_read_state,
                    "after": {
                        "is_read": db_notification.is_read,
                        "read_at": (
                            db_notification.read_at.isoformat()
                            if db_notification.read_at is not None
                            else None
                        ),
                    },
                },
            )
        db.commit()
        db.refresh(db_notification)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_notification_conflict_detail(exc),
        ) from exc

    return serialize_notification(db, db_notification)


def update_notification_workflow(
    db: Session,
    notification_id: uuid.UUID,
    notification_update: NotificationUpdate,
    current_user: User,
) -> dict[str, object]:
    require_user_admin_permission(current_user, PERMISSION_NOTIFICATIONS_MANAGE)
    db_notification = get_visible_notification_or_404(
        db,
        notification_id,
        current_user,
        allow_admin_read=True,
    )
    return apply_notification_update(
        db,
        db_notification,
        notification_update,
        admin_user_id=current_user.id,
    )


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
