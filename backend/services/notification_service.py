from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from backend.models import Game, Notification, SubPost

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
        "related_payment_id": notification.related_payment_id,
        "related_refund_id": notification.related_refund_id,
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
