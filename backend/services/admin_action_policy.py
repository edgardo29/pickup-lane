"""Central policy for admin audit action types and target requirements."""

from dataclasses import dataclass

from backend.services.admin_permission_service import (
    DATA_SCOPE_ADMIN_ONLY,
    DATA_SCOPE_MONEY_SENSITIVE,
    DATA_SCOPE_STAFF_SENSITIVE,
    DATA_SCOPE_SUPPORT_SAFE,
    PERMISSION_AUDIT_READ,
    PERMISSION_CHAT_ROOMS_MANAGE,
    PERMISSION_COMMUNITY_GAMES_HIDE_UNSAFE_CONTENT,
    PERMISSION_CONTENT_MODERATE,
    PERMISSION_MONEY_CREDIT_MANAGE,
    PERMISSION_MONEY_PAYMENT_MANAGE,
    PERMISSION_MONEY_REFUND,
    PERMISSION_NEED_A_SUB_MODERATE,
    PERMISSION_NOTIFICATIONS_MANAGE,
    PERMISSION_OFFICIAL_GAMES_CANCEL,
    PERMISSION_OFFICIAL_GAMES_ROSTER_MANAGE,
    PERMISSION_OFFICIAL_GAMES_WRITE,
    PERMISSION_STAFF_MANAGE,
    PERMISSION_USERS_DELETE,
    PERMISSION_USERS_HOSTING_MANAGE,
    PERMISSION_USERS_SUSPEND,
    PERMISSION_VENUES_MANAGE,
    PERMISSION_VENUE_IMAGES_MANAGE,
)

TARGET_USER_ID = "target_user_id"
TARGET_GAME_ID = "target_game_id"
TARGET_BOOKING_ID = "target_booking_id"
TARGET_PARTICIPANT_ID = "target_participant_id"
TARGET_PAYMENT_ID = "target_payment_id"
TARGET_REFUND_ID = "target_refund_id"
TARGET_GAME_CREDIT_ID = "target_game_credit_id"
TARGET_VENUE_ID = "target_venue_id"
TARGET_VENUE_IMAGE_ID = "target_venue_image_id"
TARGET_MESSAGE_ID = "target_message_id"
TARGET_SUB_POST_ID = "target_sub_post_id"
TARGET_SUB_POST_REQUEST_ID = "target_sub_post_request_id"
TARGET_SUB_POST_POSITION_ID = "target_sub_post_position_id"
TARGET_SUB_CHAT_MESSAGE_ID = "target_sub_chat_message_id"
TARGET_NOTIFICATION_ID = "target_notification_id"
TARGET_PLATFORM_NOTICE_CAMPAIGN_ID = "target_platform_notice_campaign_id"
TARGET_ADMIN_ACTION_ID = "target_admin_action_id"
TARGET_SUPPORT_FLAG_ID = "target_support_flag_id"

ADMIN_ACTION_TARGET_FIELDS = (
    TARGET_USER_ID,
    TARGET_GAME_ID,
    TARGET_BOOKING_ID,
    TARGET_PARTICIPANT_ID,
    TARGET_PAYMENT_ID,
    TARGET_REFUND_ID,
    TARGET_GAME_CREDIT_ID,
    TARGET_VENUE_ID,
    TARGET_VENUE_IMAGE_ID,
    TARGET_MESSAGE_ID,
    TARGET_SUB_POST_ID,
    TARGET_SUB_POST_REQUEST_ID,
    TARGET_SUB_POST_POSITION_ID,
    TARGET_SUB_CHAT_MESSAGE_ID,
    TARGET_NOTIFICATION_ID,
    TARGET_PLATFORM_NOTICE_CAMPAIGN_ID,
    TARGET_ADMIN_ACTION_ID,
    TARGET_SUPPORT_FLAG_ID,
)

@dataclass(frozen=True)
class TargetRule:
    all_of: tuple[str, ...] = ()
    one_of: tuple[str, ...] = ()


@dataclass(frozen=True)
class AdminActionPolicy:
    action_type: str
    sensitivity_scope: str
    read_permission: str
    mutation_permission: str
    required_target_rules: tuple[TargetRule, ...]
    allowed_target_fields: frozenset[str]
    metadata_builder_key: str
    note_permission: str | None = None
    client_allowed_target_fields: frozenset[str] | None = None
    server_copied_target_fields: frozenset[str] = frozenset()
    allows_audit_note: bool = True
    requires_reason: bool = False

    @property
    def effective_note_permission(self) -> str:
        return self.note_permission or self.read_permission


def target_set(*fields: str) -> frozenset[str]:
    return frozenset(fields)


ADMIN_ACTION_POLICIES: dict[str, AdminActionPolicy] = {
    "cancel_game": AdminActionPolicy(
        action_type="cancel_game",
        sensitivity_scope=DATA_SCOPE_MONEY_SENSITIVE,
        read_permission=PERMISSION_AUDIT_READ,
        mutation_permission=PERMISSION_OFFICIAL_GAMES_CANCEL,
        required_target_rules=(TargetRule(all_of=(TARGET_GAME_ID,)),),
        allowed_target_fields=target_set(TARGET_GAME_ID, TARGET_USER_ID),
        metadata_builder_key="game_cancellation",
    ),
    "refund_booking": AdminActionPolicy(
        action_type="refund_booking",
        sensitivity_scope=DATA_SCOPE_MONEY_SENSITIVE,
        read_permission=PERMISSION_AUDIT_READ,
        mutation_permission=PERMISSION_MONEY_REFUND,
        required_target_rules=(
            TargetRule(one_of=(TARGET_BOOKING_ID, TARGET_PAYMENT_ID, TARGET_REFUND_ID)),
        ),
        allowed_target_fields=target_set(
            TARGET_USER_ID,
            TARGET_GAME_ID,
            TARGET_BOOKING_ID,
            TARGET_PARTICIPANT_ID,
            TARGET_PAYMENT_ID,
            TARGET_REFUND_ID,
        ),
        metadata_builder_key="money",
    ),
    "create_refund": AdminActionPolicy(
        action_type="create_refund",
        sensitivity_scope=DATA_SCOPE_MONEY_SENSITIVE,
        read_permission=PERMISSION_AUDIT_READ,
        mutation_permission=PERMISSION_MONEY_REFUND,
        required_target_rules=(TargetRule(all_of=(TARGET_REFUND_ID,)),),
        allowed_target_fields=target_set(
            TARGET_USER_ID,
            TARGET_BOOKING_ID,
            TARGET_PARTICIPANT_ID,
            TARGET_PAYMENT_ID,
            TARGET_REFUND_ID,
        ),
        metadata_builder_key="money",
    ),
    "update_refund": AdminActionPolicy(
        action_type="update_refund",
        sensitivity_scope=DATA_SCOPE_MONEY_SENSITIVE,
        read_permission=PERMISSION_AUDIT_READ,
        mutation_permission=PERMISSION_MONEY_REFUND,
        required_target_rules=(TargetRule(all_of=(TARGET_REFUND_ID,)),),
        allowed_target_fields=target_set(
            TARGET_USER_ID,
            TARGET_BOOKING_ID,
            TARGET_PARTICIPANT_ID,
            TARGET_PAYMENT_ID,
            TARGET_REFUND_ID,
        ),
        metadata_builder_key="money",
    ),
    "create_payment": AdminActionPolicy(
        action_type="create_payment",
        sensitivity_scope=DATA_SCOPE_MONEY_SENSITIVE,
        read_permission=PERMISSION_AUDIT_READ,
        mutation_permission=PERMISSION_MONEY_PAYMENT_MANAGE,
        required_target_rules=(TargetRule(all_of=(TARGET_PAYMENT_ID,)),),
        allowed_target_fields=target_set(
            TARGET_USER_ID,
            TARGET_GAME_ID,
            TARGET_BOOKING_ID,
            TARGET_PAYMENT_ID,
        ),
        metadata_builder_key="money",
    ),
    "update_payment": AdminActionPolicy(
        action_type="update_payment",
        sensitivity_scope=DATA_SCOPE_MONEY_SENSITIVE,
        read_permission=PERMISSION_AUDIT_READ,
        mutation_permission=PERMISSION_MONEY_PAYMENT_MANAGE,
        required_target_rules=(TargetRule(all_of=(TARGET_PAYMENT_ID,)),),
        allowed_target_fields=target_set(
            TARGET_USER_ID,
            TARGET_GAME_ID,
            TARGET_BOOKING_ID,
            TARGET_PAYMENT_ID,
        ),
        metadata_builder_key="money",
    ),
    "mark_no_show": AdminActionPolicy(
        action_type="mark_no_show",
        sensitivity_scope=DATA_SCOPE_ADMIN_ONLY,
        read_permission=PERMISSION_AUDIT_READ,
        mutation_permission=PERMISSION_OFFICIAL_GAMES_ROSTER_MANAGE,
        required_target_rules=(TargetRule(all_of=(TARGET_PARTICIPANT_ID,)),),
        allowed_target_fields=target_set(
            TARGET_USER_ID,
            TARGET_GAME_ID,
            TARGET_BOOKING_ID,
            TARGET_PARTICIPANT_ID,
        ),
        metadata_builder_key="support",
    ),
    "reverse_no_show": AdminActionPolicy(
        action_type="reverse_no_show",
        sensitivity_scope=DATA_SCOPE_ADMIN_ONLY,
        read_permission=PERMISSION_AUDIT_READ,
        mutation_permission=PERMISSION_OFFICIAL_GAMES_ROSTER_MANAGE,
        required_target_rules=(TargetRule(all_of=(TARGET_PARTICIPANT_ID,)),),
        allowed_target_fields=target_set(
            TARGET_USER_ID,
            TARGET_GAME_ID,
            TARGET_BOOKING_ID,
            TARGET_PARTICIPANT_ID,
        ),
        metadata_builder_key="support",
    ),
    "suspend_user": AdminActionPolicy(
        action_type="suspend_user",
        sensitivity_scope=DATA_SCOPE_STAFF_SENSITIVE,
        read_permission=PERMISSION_AUDIT_READ,
        mutation_permission=PERMISSION_USERS_SUSPEND,
        required_target_rules=(TargetRule(all_of=(TARGET_USER_ID,)),),
        allowed_target_fields=target_set(TARGET_USER_ID, TARGET_NOTIFICATION_ID),
        client_allowed_target_fields=target_set(TARGET_USER_ID),
        metadata_builder_key="support",
        requires_reason=True,
    ),
    "unsuspend_user": AdminActionPolicy(
        action_type="unsuspend_user",
        sensitivity_scope=DATA_SCOPE_STAFF_SENSITIVE,
        read_permission=PERMISSION_AUDIT_READ,
        mutation_permission=PERMISSION_USERS_SUSPEND,
        required_target_rules=(TargetRule(all_of=(TARGET_USER_ID,)),),
        allowed_target_fields=target_set(TARGET_USER_ID, TARGET_NOTIFICATION_ID),
        client_allowed_target_fields=target_set(TARGET_USER_ID),
        metadata_builder_key="support",
        requires_reason=True,
    ),
    "restrict_hosting": AdminActionPolicy(
        action_type="restrict_hosting",
        sensitivity_scope=DATA_SCOPE_STAFF_SENSITIVE,
        read_permission=PERMISSION_AUDIT_READ,
        mutation_permission=PERMISSION_USERS_HOSTING_MANAGE,
        required_target_rules=(TargetRule(all_of=(TARGET_USER_ID,)),),
        allowed_target_fields=target_set(TARGET_USER_ID, TARGET_NOTIFICATION_ID),
        client_allowed_target_fields=target_set(TARGET_USER_ID),
        metadata_builder_key="support",
        requires_reason=True,
    ),
    "restore_hosting": AdminActionPolicy(
        action_type="restore_hosting",
        sensitivity_scope=DATA_SCOPE_STAFF_SENSITIVE,
        read_permission=PERMISSION_AUDIT_READ,
        mutation_permission=PERMISSION_USERS_HOSTING_MANAGE,
        required_target_rules=(TargetRule(all_of=(TARGET_USER_ID,)),),
        allowed_target_fields=target_set(TARGET_USER_ID, TARGET_NOTIFICATION_ID),
        client_allowed_target_fields=target_set(TARGET_USER_ID),
        metadata_builder_key="support",
        requires_reason=True,
    ),
    "delete_user": AdminActionPolicy(
        action_type="delete_user",
        sensitivity_scope=DATA_SCOPE_STAFF_SENSITIVE,
        read_permission=PERMISSION_AUDIT_READ,
        mutation_permission=PERMISSION_USERS_DELETE,
        required_target_rules=(TargetRule(all_of=(TARGET_USER_ID,)),),
        allowed_target_fields=target_set(TARGET_USER_ID),
        client_allowed_target_fields=target_set(TARGET_USER_ID),
        metadata_builder_key="support",
        requires_reason=True,
    ),
    "approve_venue": AdminActionPolicy(
        action_type="approve_venue",
        sensitivity_scope=DATA_SCOPE_ADMIN_ONLY,
        read_permission=PERMISSION_AUDIT_READ,
        mutation_permission=PERMISSION_VENUES_MANAGE,
        required_target_rules=(TargetRule(all_of=(TARGET_VENUE_ID,)),),
        allowed_target_fields=target_set(TARGET_VENUE_ID, TARGET_USER_ID),
        metadata_builder_key="support",
    ),
    "reject_venue": AdminActionPolicy(
        action_type="reject_venue",
        sensitivity_scope=DATA_SCOPE_ADMIN_ONLY,
        read_permission=PERMISSION_AUDIT_READ,
        mutation_permission=PERMISSION_VENUES_MANAGE,
        required_target_rules=(TargetRule(all_of=(TARGET_VENUE_ID,)),),
        allowed_target_fields=target_set(TARGET_VENUE_ID, TARGET_USER_ID),
        metadata_builder_key="support",
        requires_reason=True,
    ),
    "create_venue_image": AdminActionPolicy(
        action_type="create_venue_image",
        sensitivity_scope=DATA_SCOPE_ADMIN_ONLY,
        read_permission=PERMISSION_AUDIT_READ,
        mutation_permission=PERMISSION_VENUE_IMAGES_MANAGE,
        required_target_rules=(TargetRule(all_of=(TARGET_VENUE_IMAGE_ID,)),),
        allowed_target_fields=target_set(TARGET_VENUE_ID, TARGET_VENUE_IMAGE_ID),
        metadata_builder_key="support",
    ),
    "update_venue_image": AdminActionPolicy(
        action_type="update_venue_image",
        sensitivity_scope=DATA_SCOPE_ADMIN_ONLY,
        read_permission=PERMISSION_AUDIT_READ,
        mutation_permission=PERMISSION_VENUE_IMAGES_MANAGE,
        required_target_rules=(TargetRule(all_of=(TARGET_VENUE_IMAGE_ID,)),),
        allowed_target_fields=target_set(TARGET_VENUE_ID, TARGET_VENUE_IMAGE_ID),
        metadata_builder_key="support",
    ),
    "remove_venue_image": AdminActionPolicy(
        action_type="remove_venue_image",
        sensitivity_scope=DATA_SCOPE_ADMIN_ONLY,
        read_permission=PERMISSION_AUDIT_READ,
        mutation_permission=PERMISSION_VENUE_IMAGES_MANAGE,
        required_target_rules=(TargetRule(all_of=(TARGET_VENUE_IMAGE_ID,)),),
        allowed_target_fields=target_set(TARGET_VENUE_ID, TARGET_VENUE_IMAGE_ID),
        metadata_builder_key="support",
        requires_reason=True,
    ),
    "remove_chat_message": AdminActionPolicy(
        action_type="remove_chat_message",
        sensitivity_scope=DATA_SCOPE_SUPPORT_SAFE,
        read_permission=PERMISSION_AUDIT_READ,
        mutation_permission=PERMISSION_CONTENT_MODERATE,
        required_target_rules=(
            TargetRule(one_of=(TARGET_MESSAGE_ID, TARGET_SUB_CHAT_MESSAGE_ID)),
        ),
        allowed_target_fields=target_set(
            TARGET_USER_ID,
            TARGET_GAME_ID,
            TARGET_MESSAGE_ID,
            TARGET_SUB_POST_ID,
            TARGET_SUB_CHAT_MESSAGE_ID,
        ),
        metadata_builder_key="moderation",
        requires_reason=True,
    ),
    "hide_chat_message": AdminActionPolicy(
        action_type="hide_chat_message",
        sensitivity_scope=DATA_SCOPE_SUPPORT_SAFE,
        read_permission=PERMISSION_AUDIT_READ,
        mutation_permission=PERMISSION_CONTENT_MODERATE,
        required_target_rules=(
            TargetRule(one_of=(TARGET_MESSAGE_ID, TARGET_SUB_CHAT_MESSAGE_ID)),
        ),
        allowed_target_fields=target_set(
            TARGET_USER_ID,
            TARGET_GAME_ID,
            TARGET_MESSAGE_ID,
            TARGET_SUB_POST_ID,
            TARGET_SUB_CHAT_MESSAGE_ID,
        ),
        metadata_builder_key="moderation",
        requires_reason=True,
    ),
    "update_game": AdminActionPolicy(
        action_type="update_game",
        sensitivity_scope=DATA_SCOPE_ADMIN_ONLY,
        read_permission=PERMISSION_AUDIT_READ,
        mutation_permission=PERMISSION_OFFICIAL_GAMES_WRITE,
        required_target_rules=(TargetRule(all_of=(TARGET_GAME_ID,)),),
        allowed_target_fields=target_set(TARGET_GAME_ID),
        metadata_builder_key="official_game",
    ),
    "create_game_chat": AdminActionPolicy(
        action_type="create_game_chat",
        sensitivity_scope=DATA_SCOPE_ADMIN_ONLY,
        read_permission=PERMISSION_AUDIT_READ,
        mutation_permission=PERMISSION_CHAT_ROOMS_MANAGE,
        required_target_rules=(TargetRule(all_of=(TARGET_GAME_ID,)),),
        allowed_target_fields=target_set(TARGET_GAME_ID),
        metadata_builder_key="support",
    ),
    "update_game_chat": AdminActionPolicy(
        action_type="update_game_chat",
        sensitivity_scope=DATA_SCOPE_ADMIN_ONLY,
        read_permission=PERMISSION_AUDIT_READ,
        mutation_permission=PERMISSION_CHAT_ROOMS_MANAGE,
        required_target_rules=(TargetRule(all_of=(TARGET_GAME_ID,)),),
        allowed_target_fields=target_set(TARGET_GAME_ID),
        metadata_builder_key="support",
    ),
    "update_booking": AdminActionPolicy(
        action_type="update_booking",
        sensitivity_scope=DATA_SCOPE_MONEY_SENSITIVE,
        read_permission=PERMISSION_AUDIT_READ,
        mutation_permission=PERMISSION_OFFICIAL_GAMES_ROSTER_MANAGE,
        required_target_rules=(TargetRule(all_of=(TARGET_BOOKING_ID,)),),
        allowed_target_fields=target_set(
            TARGET_USER_ID,
            TARGET_GAME_ID,
            TARGET_BOOKING_ID,
            TARGET_PAYMENT_ID,
        ),
        metadata_builder_key="support",
    ),
    "update_participant": AdminActionPolicy(
        action_type="update_participant",
        sensitivity_scope=DATA_SCOPE_ADMIN_ONLY,
        read_permission=PERMISSION_AUDIT_READ,
        mutation_permission=PERMISSION_OFFICIAL_GAMES_ROSTER_MANAGE,
        required_target_rules=(TargetRule(all_of=(TARGET_PARTICIPANT_ID,)),),
        allowed_target_fields=target_set(
            TARGET_USER_ID,
            TARGET_GAME_ID,
            TARGET_BOOKING_ID,
            TARGET_PARTICIPANT_ID,
        ),
        metadata_builder_key="support",
    ),
    "issue_credit": AdminActionPolicy(
        action_type="issue_credit",
        sensitivity_scope=DATA_SCOPE_MONEY_SENSITIVE,
        read_permission=PERMISSION_AUDIT_READ,
        mutation_permission=PERMISSION_MONEY_CREDIT_MANAGE,
        required_target_rules=(TargetRule(all_of=(TARGET_USER_ID,)),),
        allowed_target_fields=target_set(
            TARGET_USER_ID,
            TARGET_GAME_ID,
            TARGET_BOOKING_ID,
            TARGET_PAYMENT_ID,
            TARGET_GAME_CREDIT_ID,
        ),
        metadata_builder_key="credit",
        requires_reason=True,
    ),
    "reverse_credit": AdminActionPolicy(
        action_type="reverse_credit",
        sensitivity_scope=DATA_SCOPE_MONEY_SENSITIVE,
        read_permission=PERMISSION_AUDIT_READ,
        mutation_permission=PERMISSION_MONEY_CREDIT_MANAGE,
        required_target_rules=(
            TargetRule(one_of=(TARGET_USER_ID, TARGET_GAME_CREDIT_ID)),
        ),
        allowed_target_fields=target_set(
            TARGET_USER_ID,
            TARGET_GAME_ID,
            TARGET_BOOKING_ID,
            TARGET_PAYMENT_ID,
            TARGET_GAME_CREDIT_ID,
        ),
        metadata_builder_key="credit",
        requires_reason=True,
    ),
    "create_official_game": AdminActionPolicy(
        action_type="create_official_game",
        sensitivity_scope=DATA_SCOPE_ADMIN_ONLY,
        read_permission=PERMISSION_AUDIT_READ,
        mutation_permission=PERMISSION_OFFICIAL_GAMES_WRITE,
        required_target_rules=(TargetRule(all_of=(TARGET_GAME_ID,)),),
        allowed_target_fields=target_set(TARGET_GAME_ID, TARGET_VENUE_ID),
        metadata_builder_key="official_game",
    ),
    "update_official_game": AdminActionPolicy(
        action_type="update_official_game",
        sensitivity_scope=DATA_SCOPE_ADMIN_ONLY,
        read_permission=PERMISSION_AUDIT_READ,
        mutation_permission=PERMISSION_OFFICIAL_GAMES_WRITE,
        required_target_rules=(TargetRule(all_of=(TARGET_GAME_ID,)),),
        allowed_target_fields=target_set(TARGET_GAME_ID, TARGET_VENUE_ID),
        metadata_builder_key="official_game",
    ),
    "assign_official_host": AdminActionPolicy(
        action_type="assign_official_host",
        sensitivity_scope=DATA_SCOPE_ADMIN_ONLY,
        read_permission=PERMISSION_AUDIT_READ,
        mutation_permission=PERMISSION_OFFICIAL_GAMES_ROSTER_MANAGE,
        required_target_rules=(TargetRule(all_of=(TARGET_GAME_ID, TARGET_USER_ID)),),
        allowed_target_fields=target_set(
            TARGET_GAME_ID,
            TARGET_USER_ID,
            TARGET_PARTICIPANT_ID,
        ),
        metadata_builder_key="official_game",
    ),
    "remove_official_host": AdminActionPolicy(
        action_type="remove_official_host",
        sensitivity_scope=DATA_SCOPE_ADMIN_ONLY,
        read_permission=PERMISSION_AUDIT_READ,
        mutation_permission=PERMISSION_OFFICIAL_GAMES_ROSTER_MANAGE,
        required_target_rules=(TargetRule(all_of=(TARGET_GAME_ID, TARGET_USER_ID)),),
        allowed_target_fields=target_set(
            TARGET_GAME_ID,
            TARGET_USER_ID,
            TARGET_PARTICIPANT_ID,
        ),
        metadata_builder_key="official_game",
    ),
    "admin_add_player": AdminActionPolicy(
        action_type="admin_add_player",
        sensitivity_scope=DATA_SCOPE_MONEY_SENSITIVE,
        read_permission=PERMISSION_AUDIT_READ,
        mutation_permission=PERMISSION_OFFICIAL_GAMES_ROSTER_MANAGE,
        required_target_rules=(TargetRule(all_of=(TARGET_GAME_ID, TARGET_PARTICIPANT_ID)),),
        allowed_target_fields=target_set(
            TARGET_GAME_ID,
            TARGET_USER_ID,
            TARGET_BOOKING_ID,
            TARGET_PARTICIPANT_ID,
            TARGET_PAYMENT_ID,
        ),
        metadata_builder_key="official_game",
    ),
    "admin_remove_player": AdminActionPolicy(
        action_type="admin_remove_player",
        sensitivity_scope=DATA_SCOPE_MONEY_SENSITIVE,
        read_permission=PERMISSION_AUDIT_READ,
        mutation_permission=PERMISSION_OFFICIAL_GAMES_ROSTER_MANAGE,
        required_target_rules=(TargetRule(all_of=(TARGET_GAME_ID, TARGET_PARTICIPANT_ID)),),
        allowed_target_fields=target_set(
            TARGET_GAME_ID,
            TARGET_USER_ID,
            TARGET_BOOKING_ID,
            TARGET_PARTICIPANT_ID,
            TARGET_PAYMENT_ID,
            TARGET_REFUND_ID,
        ),
        metadata_builder_key="official_game",
    ),
    "waive_payment": AdminActionPolicy(
        action_type="waive_payment",
        sensitivity_scope=DATA_SCOPE_MONEY_SENSITIVE,
        read_permission=PERMISSION_AUDIT_READ,
        mutation_permission=PERMISSION_MONEY_CREDIT_MANAGE,
        required_target_rules=(TargetRule(one_of=(TARGET_BOOKING_ID, TARGET_PAYMENT_ID)),),
        allowed_target_fields=target_set(
            TARGET_USER_ID,
            TARGET_GAME_ID,
            TARGET_BOOKING_ID,
            TARGET_PARTICIPANT_ID,
            TARGET_PAYMENT_ID,
        ),
        metadata_builder_key="money",
        requires_reason=True,
    ),
    "remove_sub_post": AdminActionPolicy(
        action_type="remove_sub_post",
        sensitivity_scope=DATA_SCOPE_SUPPORT_SAFE,
        read_permission=PERMISSION_AUDIT_READ,
        mutation_permission=PERMISSION_NEED_A_SUB_MODERATE,
        required_target_rules=(TargetRule(all_of=(TARGET_SUB_POST_ID,)),),
        allowed_target_fields=target_set(TARGET_USER_ID, TARGET_SUB_POST_ID),
        metadata_builder_key="moderation",
        requires_reason=True,
    ),
    "hide_unsafe_community_payment_text": AdminActionPolicy(
        action_type="hide_unsafe_community_payment_text",
        sensitivity_scope=DATA_SCOPE_SUPPORT_SAFE,
        read_permission=PERMISSION_AUDIT_READ,
        mutation_permission=PERMISSION_COMMUNITY_GAMES_HIDE_UNSAFE_CONTENT,
        required_target_rules=(TargetRule(all_of=(TARGET_GAME_ID,)),),
        allowed_target_fields=target_set(TARGET_GAME_ID, TARGET_USER_ID),
        metadata_builder_key="moderation",
        requires_reason=True,
    ),
    "update_notification": AdminActionPolicy(
        action_type="update_notification",
        sensitivity_scope=DATA_SCOPE_ADMIN_ONLY,
        read_permission=PERMISSION_AUDIT_READ,
        mutation_permission=PERMISSION_NOTIFICATIONS_MANAGE,
        required_target_rules=(TargetRule(all_of=(TARGET_NOTIFICATION_ID,)),),
        allowed_target_fields=target_set(TARGET_NOTIFICATION_ID, TARGET_USER_ID),
        metadata_builder_key="support",
    ),
    "create_notification": AdminActionPolicy(
        action_type="create_notification",
        sensitivity_scope=DATA_SCOPE_ADMIN_ONLY,
        read_permission=PERMISSION_AUDIT_READ,
        mutation_permission=PERMISSION_NOTIFICATIONS_MANAGE,
        required_target_rules=(TargetRule(all_of=(TARGET_NOTIFICATION_ID,)),),
        allowed_target_fields=target_set(TARGET_NOTIFICATION_ID, TARGET_USER_ID),
        metadata_builder_key="support",
    ),
    "change_staff_role": AdminActionPolicy(
        action_type="change_staff_role",
        sensitivity_scope=DATA_SCOPE_STAFF_SENSITIVE,
        read_permission=PERMISSION_AUDIT_READ,
        mutation_permission=PERMISSION_STAFF_MANAGE,
        required_target_rules=(TargetRule(all_of=(TARGET_USER_ID,)),),
        allowed_target_fields=target_set(TARGET_USER_ID),
        metadata_builder_key="support",
        requires_reason=True,
    ),
    "append_audit_note": AdminActionPolicy(
        action_type="append_audit_note",
        sensitivity_scope=DATA_SCOPE_ADMIN_ONLY,
        read_permission=PERMISSION_AUDIT_READ,
        mutation_permission=PERMISSION_AUDIT_READ,
        required_target_rules=(TargetRule(all_of=(TARGET_ADMIN_ACTION_ID,)),),
        allowed_target_fields=target_set(TARGET_ADMIN_ACTION_ID, *ADMIN_ACTION_TARGET_FIELDS),
        client_allowed_target_fields=target_set(TARGET_ADMIN_ACTION_ID),
        server_copied_target_fields=target_set(*ADMIN_ACTION_TARGET_FIELDS),
        metadata_builder_key="audit_note",
        allows_audit_note=False,
        requires_reason=True,
    ),
    "resolve_support_flag": AdminActionPolicy(
        action_type="resolve_support_flag",
        sensitivity_scope=DATA_SCOPE_ADMIN_ONLY,
        read_permission=PERMISSION_AUDIT_READ,
        mutation_permission=PERMISSION_AUDIT_READ,
        required_target_rules=(TargetRule(all_of=(TARGET_SUPPORT_FLAG_ID,)),),
        allowed_target_fields=target_set(
            TARGET_SUPPORT_FLAG_ID,
            TARGET_USER_ID,
            TARGET_GAME_ID,
            TARGET_BOOKING_ID,
            TARGET_PAYMENT_ID,
            TARGET_REFUND_ID,
            TARGET_GAME_CREDIT_ID,
            TARGET_VENUE_ID,
            TARGET_VENUE_IMAGE_ID,
            TARGET_NOTIFICATION_ID,
        ),
        client_allowed_target_fields=target_set(),
        metadata_builder_key="support",
        requires_reason=True,
    ),
}

ADMIN_ACTION_TYPES = tuple(ADMIN_ACTION_POLICIES)


def get_admin_action_policy(action_type: str) -> AdminActionPolicy | None:
    return ADMIN_ACTION_POLICIES.get(action_type)
