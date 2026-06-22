"""Central policy for durable admin support flag types."""

from dataclasses import dataclass

from backend.services.admin_permission_service import (
    DATA_SCOPE_ADMIN_ONLY,
    DATA_SCOPE_MONEY_SENSITIVE,
    DATA_SCOPE_STAFF_SENSITIVE,
    DATA_SCOPE_SUPPORT_SAFE,
    PERMISSION_COMMUNITY_GAMES_READ,
    PERMISSION_COMMUNITY_GAMES_WRITE,
    PERMISSION_MONEY_CREDIT_MANAGE,
    PERMISSION_MONEY_PAYMENT_MANAGE,
    PERMISSION_MONEY_READ,
    PERMISSION_MONEY_REFUND,
    PERMISSION_OFFICIAL_GAMES_CANCEL,
    PERMISSION_USERS_DELETE,
    PERMISSION_VENUE_IMAGES_MANAGE,
)

TARGET_USER_ID = "target_user_id"
TARGET_GAME_ID = "target_game_id"
TARGET_BOOKING_ID = "target_booking_id"
TARGET_PAYMENT_ID = "target_payment_id"
TARGET_REFUND_ID = "target_refund_id"
TARGET_GAME_CREDIT_ID = "target_game_credit_id"
TARGET_VENUE_ID = "target_venue_id"
TARGET_VENUE_IMAGE_ID = "target_venue_image_id"
TARGET_NOTIFICATION_ID = "target_notification_id"

SUPPORT_FLAG_TARGET_FIELDS = (
    TARGET_USER_ID,
    TARGET_GAME_ID,
    TARGET_BOOKING_ID,
    TARGET_PAYMENT_ID,
    TARGET_REFUND_ID,
    TARGET_GAME_CREDIT_ID,
    TARGET_VENUE_ID,
    TARGET_VENUE_IMAGE_ID,
    TARGET_NOTIFICATION_ID,
)

BASELINE_RESOLUTION_OUTCOMES = (
    "handled_externally",
    "retried_successfully",
    "no_action_needed",
    "duplicate",
    "invalid_flag",
)


@dataclass(frozen=True)
class SupportFlagTargetRule:
    all_of: tuple[str, ...] = ()
    one_of: tuple[str, ...] = ()


@dataclass(frozen=True)
class SupportFlagPolicy:
    flag_type: str
    sensitivity_scope: str
    read_permission: str
    resolve_permission: str
    required_target_rules: tuple[SupportFlagTargetRule, ...]
    allowed_target_fields: frozenset[str]
    allowed_resolution_outcomes: tuple[str, ...] = BASELINE_RESOLUTION_OUTCOMES
    resolution_requires_idempotency: bool = False


def target_set(*fields: str) -> frozenset[str]:
    return frozenset(fields)


SUPPORT_FLAG_POLICIES: dict[str, SupportFlagPolicy] = {
    "refund_follow_up_required": SupportFlagPolicy(
        flag_type="refund_follow_up_required",
        sensitivity_scope=DATA_SCOPE_MONEY_SENSITIVE,
        read_permission=PERMISSION_MONEY_READ,
        resolve_permission=PERMISSION_MONEY_REFUND,
        required_target_rules=(
            SupportFlagTargetRule(one_of=(TARGET_BOOKING_ID, TARGET_PAYMENT_ID, TARGET_REFUND_ID)),
        ),
        allowed_target_fields=target_set(
            TARGET_USER_ID,
            TARGET_GAME_ID,
            TARGET_BOOKING_ID,
            TARGET_PAYMENT_ID,
            TARGET_REFUND_ID,
        ),
    ),
    "stripe_refund_failed": SupportFlagPolicy(
        flag_type="stripe_refund_failed",
        sensitivity_scope=DATA_SCOPE_MONEY_SENSITIVE,
        read_permission=PERMISSION_MONEY_READ,
        resolve_permission=PERMISSION_MONEY_REFUND,
        required_target_rules=(SupportFlagTargetRule(all_of=(TARGET_REFUND_ID,)),),
        allowed_target_fields=target_set(
            TARGET_USER_ID,
            TARGET_GAME_ID,
            TARGET_BOOKING_ID,
            TARGET_PAYMENT_ID,
            TARGET_REFUND_ID,
        ),
    ),
    "missing_stripe_charge_id": SupportFlagPolicy(
        flag_type="missing_stripe_charge_id",
        sensitivity_scope=DATA_SCOPE_MONEY_SENSITIVE,
        read_permission=PERMISSION_MONEY_READ,
        resolve_permission=PERMISSION_MONEY_PAYMENT_MANAGE,
        required_target_rules=(
            SupportFlagTargetRule(one_of=(TARGET_BOOKING_ID, TARGET_PAYMENT_ID)),
        ),
        allowed_target_fields=target_set(
            TARGET_USER_ID,
            TARGET_GAME_ID,
            TARGET_BOOKING_ID,
            TARGET_PAYMENT_ID,
            TARGET_REFUND_ID,
        ),
    ),
    "credit_restore_failed": SupportFlagPolicy(
        flag_type="credit_restore_failed",
        sensitivity_scope=DATA_SCOPE_MONEY_SENSITIVE,
        read_permission=PERMISSION_MONEY_READ,
        resolve_permission=PERMISSION_MONEY_CREDIT_MANAGE,
        required_target_rules=(
            SupportFlagTargetRule(one_of=(TARGET_BOOKING_ID, TARGET_GAME_CREDIT_ID)),
        ),
        allowed_target_fields=target_set(
            TARGET_USER_ID,
            TARGET_GAME_ID,
            TARGET_BOOKING_ID,
            TARGET_PAYMENT_ID,
            TARGET_GAME_CREDIT_ID,
        ),
    ),
    "credit_release_failed": SupportFlagPolicy(
        flag_type="credit_release_failed",
        sensitivity_scope=DATA_SCOPE_MONEY_SENSITIVE,
        read_permission=PERMISSION_MONEY_READ,
        resolve_permission=PERMISSION_MONEY_CREDIT_MANAGE,
        required_target_rules=(
            SupportFlagTargetRule(one_of=(TARGET_BOOKING_ID, TARGET_GAME_CREDIT_ID)),
        ),
        allowed_target_fields=target_set(
            TARGET_USER_ID,
            TARGET_GAME_ID,
            TARGET_BOOKING_ID,
            TARGET_PAYMENT_ID,
            TARGET_GAME_CREDIT_ID,
        ),
    ),
    "venue_image_upload_failed": SupportFlagPolicy(
        flag_type="venue_image_upload_failed",
        sensitivity_scope=DATA_SCOPE_ADMIN_ONLY,
        read_permission=PERMISSION_VENUE_IMAGES_MANAGE,
        resolve_permission=PERMISSION_VENUE_IMAGES_MANAGE,
        required_target_rules=(
            SupportFlagTargetRule(one_of=(TARGET_VENUE_ID, TARGET_VENUE_IMAGE_ID)),
        ),
        allowed_target_fields=target_set(TARGET_VENUE_ID, TARGET_VENUE_IMAGE_ID),
    ),
    "venue_image_readiness_failed": SupportFlagPolicy(
        flag_type="venue_image_readiness_failed",
        sensitivity_scope=DATA_SCOPE_ADMIN_ONLY,
        read_permission=PERMISSION_VENUE_IMAGES_MANAGE,
        resolve_permission=PERMISSION_VENUE_IMAGES_MANAGE,
        required_target_rules=(
            SupportFlagTargetRule(one_of=(TARGET_VENUE_ID, TARGET_VENUE_IMAGE_ID)),
        ),
        allowed_target_fields=target_set(TARGET_VENUE_ID, TARGET_VENUE_IMAGE_ID),
    ),
    "account_delete_partial_failure": SupportFlagPolicy(
        flag_type="account_delete_partial_failure",
        sensitivity_scope=DATA_SCOPE_STAFF_SENSITIVE,
        read_permission=PERMISSION_USERS_DELETE,
        resolve_permission=PERMISSION_USERS_DELETE,
        required_target_rules=(SupportFlagTargetRule(all_of=(TARGET_USER_ID,)),),
        allowed_target_fields=target_set(TARGET_USER_ID),
    ),
    "official_cancel_partial_failure": SupportFlagPolicy(
        flag_type="official_cancel_partial_failure",
        sensitivity_scope=DATA_SCOPE_MONEY_SENSITIVE,
        read_permission=PERMISSION_OFFICIAL_GAMES_CANCEL,
        resolve_permission=PERMISSION_OFFICIAL_GAMES_CANCEL,
        required_target_rules=(SupportFlagTargetRule(all_of=(TARGET_GAME_ID,)),),
        allowed_target_fields=target_set(
            TARGET_USER_ID,
            TARGET_GAME_ID,
            TARGET_BOOKING_ID,
            TARGET_PAYMENT_ID,
            TARGET_REFUND_ID,
            TARGET_GAME_CREDIT_ID,
        ),
    ),
    "community_game_review_required": SupportFlagPolicy(
        flag_type="community_game_review_required",
        sensitivity_scope=DATA_SCOPE_SUPPORT_SAFE,
        read_permission=PERMISSION_COMMUNITY_GAMES_READ,
        resolve_permission=PERMISSION_COMMUNITY_GAMES_WRITE,
        required_target_rules=(SupportFlagTargetRule(all_of=(TARGET_GAME_ID,)),),
        allowed_target_fields=target_set(TARGET_GAME_ID),
        allowed_resolution_outcomes=(
            "handled_externally",
            "no_action_needed",
            "duplicate",
            "invalid_flag",
        ),
        resolution_requires_idempotency=True,
    ),
}

SUPPORT_FLAG_TYPES = tuple(SUPPORT_FLAG_POLICIES)


def get_support_flag_policy(flag_type: str) -> SupportFlagPolicy | None:
    return SUPPORT_FLAG_POLICIES.get(flag_type)
