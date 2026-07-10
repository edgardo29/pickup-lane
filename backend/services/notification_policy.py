from dataclasses import dataclass


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
        title="Post cancelled",
        summary="This Need a Sub post was cancelled.",
        body="This Need a Sub post was cancelled by the host.",
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
