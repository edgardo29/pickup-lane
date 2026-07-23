"""Central policy for admin audit action types and target requirements."""

from dataclasses import dataclass

TARGET_USER_ID = "target_user_id"
TARGET_GAME_ID = "target_game_id"
TARGET_BOOKING_ID = "target_booking_id"
TARGET_PARTICIPANT_ID = "target_participant_id"
TARGET_PAYMENT_ID = "target_payment_id"
TARGET_REFUND_ID = "target_refund_id"
TARGET_GAME_CREDIT_ID = "target_game_credit_id"
TARGET_CREDIT_USAGE_ID = "target_credit_usage_id"
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
TARGET_MONEY_ISSUE_ID = "target_money_issue_id"
TARGET_REVIEW_CASE_ID = "target_review_case_id"
TARGET_FINANCIAL_OUTCOME_ID = "target_financial_outcome_id"
TARGET_HOST_PUBLISH_FEE_ID = "target_host_publish_fee_id"
TARGET_HOST_PUBLISH_ENTITLEMENT_ID = "target_host_publish_entitlement_id"

ADMIN_ACTION_TARGET_FIELDS = (
    TARGET_USER_ID,
    TARGET_GAME_ID,
    TARGET_BOOKING_ID,
    TARGET_PARTICIPANT_ID,
    TARGET_PAYMENT_ID,
    TARGET_REFUND_ID,
    TARGET_GAME_CREDIT_ID,
    TARGET_CREDIT_USAGE_ID,
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
    TARGET_MONEY_ISSUE_ID,
    TARGET_REVIEW_CASE_ID,
    TARGET_FINANCIAL_OUTCOME_ID,
    TARGET_HOST_PUBLISH_FEE_ID,
    TARGET_HOST_PUBLISH_ENTITLEMENT_ID,
)

@dataclass(frozen=True)
class TargetRule:
    all_of: tuple[str, ...] = ()
    one_of: tuple[str, ...] = ()


@dataclass(frozen=True)
class AdminActionPolicy:
    action_type: str
    required_target_rules: tuple[TargetRule, ...]
    allowed_target_fields: frozenset[str]
    metadata_builder_key: str
    client_allowed_target_fields: frozenset[str] | None = None
    server_copied_target_fields: frozenset[str] = frozenset()
    allows_audit_note: bool = True
    requires_reason: bool = False



def target_set(*fields: str) -> frozenset[str]:
    return frozenset(fields)


ADMIN_ACTION_POLICIES: dict[str, AdminActionPolicy] = {
    "cancel_game": AdminActionPolicy(
        action_type="cancel_game",
        required_target_rules=(TargetRule(all_of=(TARGET_GAME_ID,)),),
        allowed_target_fields=target_set(TARGET_GAME_ID, TARGET_USER_ID),
        metadata_builder_key="game_cancellation",
    ),
    "refund_booking": AdminActionPolicy(
        action_type="refund_booking",
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
        required_target_rules=(TargetRule(all_of=(TARGET_REFUND_ID,)),),
        allowed_target_fields=target_set(
            TARGET_USER_ID,
            TARGET_BOOKING_ID,
            TARGET_PARTICIPANT_ID,
            TARGET_PAYMENT_ID,
            TARGET_REFUND_ID,
            TARGET_HOST_PUBLISH_FEE_ID,
        ),
        metadata_builder_key="money",
    ),
    "update_refund": AdminActionPolicy(
        action_type="update_refund",
        required_target_rules=(TargetRule(all_of=(TARGET_REFUND_ID,)),),
        allowed_target_fields=target_set(
            TARGET_USER_ID,
            TARGET_BOOKING_ID,
            TARGET_PARTICIPANT_ID,
            TARGET_PAYMENT_ID,
            TARGET_REFUND_ID,
            TARGET_HOST_PUBLISH_FEE_ID,
        ),
        metadata_builder_key="money",
    ),
    "create_financial_outcome": AdminActionPolicy(
        action_type="create_financial_outcome",
        required_target_rules=(
            TargetRule(all_of=(TARGET_FINANCIAL_OUTCOME_ID,)),
        ),
        allowed_target_fields=target_set(
            TARGET_USER_ID,
            TARGET_GAME_ID,
            TARGET_PAYMENT_ID,
            TARGET_REFUND_ID,
            TARGET_FINANCIAL_OUTCOME_ID,
            TARGET_HOST_PUBLISH_FEE_ID,
            TARGET_HOST_PUBLISH_ENTITLEMENT_ID,
        ),
        metadata_builder_key="money",
    ),
    "apply_financial_outcome": AdminActionPolicy(
        action_type="apply_financial_outcome",
        required_target_rules=(
            TargetRule(all_of=(TARGET_FINANCIAL_OUTCOME_ID,)),
        ),
        allowed_target_fields=target_set(
            TARGET_USER_ID,
            TARGET_GAME_ID,
            TARGET_PAYMENT_ID,
            TARGET_REFUND_ID,
            TARGET_FINANCIAL_OUTCOME_ID,
            TARGET_HOST_PUBLISH_FEE_ID,
            TARGET_HOST_PUBLISH_ENTITLEMENT_ID,
        ),
        metadata_builder_key="money",
    ),
    "create_payment": AdminActionPolicy(
        action_type="create_payment",
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
        required_target_rules=(TargetRule(all_of=(TARGET_USER_ID,)),),
        allowed_target_fields=target_set(TARGET_USER_ID, TARGET_NOTIFICATION_ID),
        client_allowed_target_fields=target_set(TARGET_USER_ID),
        metadata_builder_key="support",
        requires_reason=True,
    ),
    "unsuspend_user": AdminActionPolicy(
        action_type="unsuspend_user",
        required_target_rules=(TargetRule(all_of=(TARGET_USER_ID,)),),
        allowed_target_fields=target_set(TARGET_USER_ID, TARGET_NOTIFICATION_ID),
        client_allowed_target_fields=target_set(TARGET_USER_ID),
        metadata_builder_key="support",
        requires_reason=True,
    ),
    "restrict_hosting": AdminActionPolicy(
        action_type="restrict_hosting",
        required_target_rules=(TargetRule(all_of=(TARGET_USER_ID,)),),
        allowed_target_fields=target_set(TARGET_USER_ID, TARGET_NOTIFICATION_ID),
        client_allowed_target_fields=target_set(TARGET_USER_ID),
        metadata_builder_key="support",
        requires_reason=True,
    ),
    "restore_hosting": AdminActionPolicy(
        action_type="restore_hosting",
        required_target_rules=(TargetRule(all_of=(TARGET_USER_ID,)),),
        allowed_target_fields=target_set(TARGET_USER_ID, TARGET_NOTIFICATION_ID),
        client_allowed_target_fields=target_set(TARGET_USER_ID),
        metadata_builder_key="support",
        requires_reason=True,
    ),
    "delete_user": AdminActionPolicy(
        action_type="delete_user",
        required_target_rules=(TargetRule(all_of=(TARGET_USER_ID,)),),
        allowed_target_fields=target_set(TARGET_USER_ID),
        client_allowed_target_fields=target_set(TARGET_USER_ID),
        metadata_builder_key="support",
        requires_reason=True,
    ),
    "approve_venue": AdminActionPolicy(
        action_type="approve_venue",
        required_target_rules=(TargetRule(all_of=(TARGET_VENUE_ID,)),),
        allowed_target_fields=target_set(TARGET_VENUE_ID, TARGET_USER_ID),
        metadata_builder_key="support",
    ),
    "reject_venue": AdminActionPolicy(
        action_type="reject_venue",
        required_target_rules=(TargetRule(all_of=(TARGET_VENUE_ID,)),),
        allowed_target_fields=target_set(TARGET_VENUE_ID, TARGET_USER_ID),
        metadata_builder_key="support",
        requires_reason=True,
    ),
    "create_venue_image": AdminActionPolicy(
        action_type="create_venue_image",
        required_target_rules=(TargetRule(all_of=(TARGET_VENUE_IMAGE_ID,)),),
        allowed_target_fields=target_set(TARGET_VENUE_ID, TARGET_VENUE_IMAGE_ID),
        metadata_builder_key="support",
    ),
    "update_venue_image": AdminActionPolicy(
        action_type="update_venue_image",
        required_target_rules=(TargetRule(all_of=(TARGET_VENUE_IMAGE_ID,)),),
        allowed_target_fields=target_set(TARGET_VENUE_ID, TARGET_VENUE_IMAGE_ID),
        metadata_builder_key="support",
    ),
    "remove_venue_image": AdminActionPolicy(
        action_type="remove_venue_image",
        required_target_rules=(TargetRule(all_of=(TARGET_VENUE_IMAGE_ID,)),),
        allowed_target_fields=target_set(TARGET_VENUE_ID, TARGET_VENUE_IMAGE_ID),
        metadata_builder_key="support",
        requires_reason=True,
    ),
    "mark_chat_message_reviewed": AdminActionPolicy(
        action_type="mark_chat_message_reviewed",
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
    ),
    "remove_chat_message": AdminActionPolicy(
        action_type="remove_chat_message",
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
    "restore_chat_message": AdminActionPolicy(
        action_type="restore_chat_message",
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
        required_target_rules=(TargetRule(all_of=(TARGET_GAME_ID,)),),
        allowed_target_fields=target_set(TARGET_GAME_ID),
        metadata_builder_key="official_game",
    ),
    "create_game_chat": AdminActionPolicy(
        action_type="create_game_chat",
        required_target_rules=(TargetRule(all_of=(TARGET_GAME_ID,)),),
        allowed_target_fields=target_set(TARGET_GAME_ID),
        metadata_builder_key="support",
    ),
    "update_game_chat": AdminActionPolicy(
        action_type="update_game_chat",
        required_target_rules=(TargetRule(all_of=(TARGET_GAME_ID,)),),
        allowed_target_fields=target_set(TARGET_GAME_ID),
        metadata_builder_key="support",
    ),
    "update_booking": AdminActionPolicy(
        action_type="update_booking",
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
        required_target_rules=(TargetRule(all_of=(TARGET_GAME_ID,)),),
        allowed_target_fields=target_set(TARGET_GAME_ID, TARGET_VENUE_ID),
        metadata_builder_key="official_game",
    ),
    "update_official_game": AdminActionPolicy(
        action_type="update_official_game",
        required_target_rules=(TargetRule(all_of=(TARGET_GAME_ID,)),),
        allowed_target_fields=target_set(TARGET_GAME_ID, TARGET_VENUE_ID),
        metadata_builder_key="official_game",
    ),
    "assign_official_host": AdminActionPolicy(
        action_type="assign_official_host",
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
        required_target_rules=(TargetRule(all_of=(TARGET_SUB_POST_ID,)),),
        allowed_target_fields=target_set(TARGET_USER_ID, TARGET_SUB_POST_ID),
        metadata_builder_key="moderation",
        requires_reason=True,
    ),
    "hide_need_sub_post": AdminActionPolicy(
        action_type="hide_need_sub_post",
        required_target_rules=(TargetRule(all_of=(TARGET_SUB_POST_ID,)),),
        allowed_target_fields=target_set(TARGET_USER_ID, TARGET_SUB_POST_ID),
        metadata_builder_key="moderation",
        requires_reason=True,
    ),
    "restore_need_sub_post": AdminActionPolicy(
        action_type="restore_need_sub_post",
        required_target_rules=(TargetRule(all_of=(TARGET_SUB_POST_ID,)),),
        allowed_target_fields=target_set(TARGET_USER_ID, TARGET_SUB_POST_ID),
        metadata_builder_key="moderation",
        requires_reason=True,
    ),
    "hide_community_game": AdminActionPolicy(
        action_type="hide_community_game",
        required_target_rules=(TargetRule(all_of=(TARGET_GAME_ID,)),),
        allowed_target_fields=target_set(TARGET_GAME_ID, TARGET_USER_ID),
        metadata_builder_key="moderation",
        requires_reason=True,
    ),
    "restore_community_game": AdminActionPolicy(
        action_type="restore_community_game",
        required_target_rules=(TargetRule(all_of=(TARGET_GAME_ID,)),),
        allowed_target_fields=target_set(TARGET_GAME_ID, TARGET_USER_ID),
        metadata_builder_key="moderation",
        requires_reason=True,
    ),
    "pause_community_game_joining": AdminActionPolicy(
        action_type="pause_community_game_joining",
        required_target_rules=(TargetRule(all_of=(TARGET_GAME_ID,)),),
        allowed_target_fields=target_set(TARGET_GAME_ID, TARGET_USER_ID),
        metadata_builder_key="moderation",
        requires_reason=True,
    ),
    "resume_community_game_joining": AdminActionPolicy(
        action_type="resume_community_game_joining",
        required_target_rules=(TargetRule(all_of=(TARGET_GAME_ID,)),),
        allowed_target_fields=target_set(TARGET_GAME_ID, TARGET_USER_ID),
        metadata_builder_key="moderation",
        requires_reason=True,
    ),
    "admin_cancel_community_game": AdminActionPolicy(
        action_type="admin_cancel_community_game",
        required_target_rules=(TargetRule(all_of=(TARGET_GAME_ID,)),),
        allowed_target_fields=target_set(TARGET_GAME_ID, TARGET_USER_ID),
        metadata_builder_key="game_cancellation",
        requires_reason=True,
    ),
    "hide_unsafe_community_payment_text": AdminActionPolicy(
        action_type="hide_unsafe_community_payment_text",
        required_target_rules=(TargetRule(all_of=(TARGET_GAME_ID,)),),
        allowed_target_fields=target_set(TARGET_GAME_ID, TARGET_USER_ID),
        metadata_builder_key="moderation",
        requires_reason=True,
    ),
    "restore_community_payment_text": AdminActionPolicy(
        action_type="restore_community_payment_text",
        required_target_rules=(TargetRule(all_of=(TARGET_GAME_ID,)),),
        allowed_target_fields=target_set(TARGET_GAME_ID, TARGET_USER_ID),
        metadata_builder_key="moderation",
        requires_reason=True,
    ),
    "create_review_case": AdminActionPolicy(
        action_type="create_review_case",
        required_target_rules=(TargetRule(all_of=(TARGET_REVIEW_CASE_ID,)),),
        allowed_target_fields=target_set(
            TARGET_REVIEW_CASE_ID,
            TARGET_USER_ID,
            TARGET_GAME_ID,
            TARGET_SUB_POST_ID,
            TARGET_SUB_POST_REQUEST_ID,
            TARGET_PAYMENT_ID,
            TARGET_FINANCIAL_OUTCOME_ID,
        ),
        metadata_builder_key="review_workflow",
    ),
    "close_review_case": AdminActionPolicy(
        action_type="close_review_case",
        required_target_rules=(TargetRule(all_of=(TARGET_REVIEW_CASE_ID,)),),
        allowed_target_fields=target_set(
            TARGET_REVIEW_CASE_ID,
            TARGET_USER_ID,
            TARGET_GAME_ID,
            TARGET_SUB_POST_ID,
            TARGET_SUB_POST_REQUEST_ID,
            TARGET_PAYMENT_ID,
            TARGET_FINANCIAL_OUTCOME_ID,
        ),
        metadata_builder_key="review_workflow",
        requires_reason=True,
    ),
    "add_review_case_note": AdminActionPolicy(
        action_type="add_review_case_note",
        required_target_rules=(TargetRule(all_of=(TARGET_REVIEW_CASE_ID,)),),
        allowed_target_fields=target_set(
            TARGET_REVIEW_CASE_ID,
            TARGET_USER_ID,
            TARGET_GAME_ID,
            TARGET_SUB_POST_ID,
            TARGET_SUB_POST_REQUEST_ID,
            TARGET_PAYMENT_ID,
            TARGET_FINANCIAL_OUTCOME_ID,
        ),
        metadata_builder_key="review_workflow",
        requires_reason=True,
    ),
    "update_notification": AdminActionPolicy(
        action_type="update_notification",
        required_target_rules=(TargetRule(all_of=(TARGET_NOTIFICATION_ID,)),),
        allowed_target_fields=target_set(TARGET_NOTIFICATION_ID, TARGET_USER_ID),
        metadata_builder_key="support",
    ),
    "create_notification": AdminActionPolicy(
        action_type="create_notification",
        required_target_rules=(TargetRule(all_of=(TARGET_NOTIFICATION_ID,)),),
        allowed_target_fields=target_set(TARGET_NOTIFICATION_ID, TARGET_USER_ID),
        metadata_builder_key="support",
    ),
    "create_platform_notice_campaign": AdminActionPolicy(
        action_type="create_platform_notice_campaign",
        required_target_rules=(
            TargetRule(all_of=(TARGET_PLATFORM_NOTICE_CAMPAIGN_ID,)),
        ),
        allowed_target_fields=target_set(TARGET_PLATFORM_NOTICE_CAMPAIGN_ID),
        metadata_builder_key="platform_notice",
    ),
    "update_platform_notice_campaign": AdminActionPolicy(
        action_type="update_platform_notice_campaign",
        required_target_rules=(
            TargetRule(all_of=(TARGET_PLATFORM_NOTICE_CAMPAIGN_ID,)),
        ),
        allowed_target_fields=target_set(TARGET_PLATFORM_NOTICE_CAMPAIGN_ID),
        metadata_builder_key="platform_notice",
    ),
    "send_platform_notice_campaign": AdminActionPolicy(
        action_type="send_platform_notice_campaign",
        required_target_rules=(
            TargetRule(all_of=(TARGET_PLATFORM_NOTICE_CAMPAIGN_ID,)),
        ),
        allowed_target_fields=target_set(TARGET_PLATFORM_NOTICE_CAMPAIGN_ID),
        metadata_builder_key="platform_notice",
    ),
    "retry_platform_notice_campaign": AdminActionPolicy(
        action_type="retry_platform_notice_campaign",
        required_target_rules=(
            TargetRule(all_of=(TARGET_PLATFORM_NOTICE_CAMPAIGN_ID,)),
        ),
        allowed_target_fields=target_set(TARGET_PLATFORM_NOTICE_CAMPAIGN_ID),
        metadata_builder_key="platform_notice",
    ),
    "user_role_changed": AdminActionPolicy(
        action_type="user_role_changed",
        required_target_rules=(TargetRule(all_of=(TARGET_USER_ID,)),),
        allowed_target_fields=target_set(TARGET_USER_ID),
        metadata_builder_key="support",
        requires_reason=True,
    ),
    "append_audit_note": AdminActionPolicy(
        action_type="append_audit_note",
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
    "resolve_money_issue": AdminActionPolicy(
        action_type="resolve_money_issue",
        required_target_rules=(TargetRule(all_of=(TARGET_MONEY_ISSUE_ID,)),),
        allowed_target_fields=target_set(
            TARGET_MONEY_ISSUE_ID,
            TARGET_USER_ID,
            TARGET_GAME_ID,
            TARGET_BOOKING_ID,
            TARGET_PAYMENT_ID,
            TARGET_REFUND_ID,
            TARGET_GAME_CREDIT_ID,
            TARGET_CREDIT_USAGE_ID,
        ),
        client_allowed_target_fields=target_set(),
        metadata_builder_key="money_issue",
        requires_reason=True,
    ),
    "retry_money_issue_credit": AdminActionPolicy(
        action_type="retry_money_issue_credit",
        required_target_rules=(TargetRule(all_of=(TARGET_MONEY_ISSUE_ID,)),),
        allowed_target_fields=target_set(
            TARGET_MONEY_ISSUE_ID,
            TARGET_USER_ID,
            TARGET_GAME_ID,
            TARGET_BOOKING_ID,
            TARGET_PAYMENT_ID,
            TARGET_GAME_CREDIT_ID,
            TARGET_CREDIT_USAGE_ID,
        ),
        client_allowed_target_fields=target_set(),
        metadata_builder_key="money_issue",
        requires_reason=True,
    ),
    "reconcile_refund": AdminActionPolicy(
        action_type="reconcile_refund",
        required_target_rules=(TargetRule(all_of=(TARGET_REFUND_ID,)),),
        allowed_target_fields=target_set(
            TARGET_MONEY_ISSUE_ID,
            TARGET_USER_ID,
            TARGET_GAME_ID,
            TARGET_BOOKING_ID,
            TARGET_PAYMENT_ID,
            TARGET_REFUND_ID,
            TARGET_HOST_PUBLISH_FEE_ID,
        ),
        client_allowed_target_fields=target_set(),
        metadata_builder_key="money_issue",
        requires_reason=True,
    ),
}

ADMIN_ACTION_TYPES = tuple(ADMIN_ACTION_POLICIES)


def get_admin_action_policy(action_type: str) -> AdminActionPolicy | None:
    return ADMIN_ACTION_POLICIES.get(action_type)
