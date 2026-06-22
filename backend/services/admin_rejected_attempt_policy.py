"""Policy for high-risk admin attempts that were rejected."""

from dataclasses import dataclass

from backend.services.admin_permission_service import PERMISSION_AUDIT_READ

ATTEMPT_TYPE_ISSUE_CREDIT_REJECTED = "issue_credit_rejected"
ATTEMPT_TYPE_REVERSE_CREDIT_REJECTED = "reverse_credit_rejected"
ATTEMPT_TYPE_SUSPEND_USER_REJECTED = "suspend_user_rejected"
ATTEMPT_TYPE_DELETE_USER_REJECTED = "delete_user_rejected"

REJECTION_PERMISSION_DENIED_PRELOAD = "permission_denied_preload"
REJECTION_DOMAIN_REJECTED_POSTLOAD = "domain_rejected_postload"

TARGET_USER_ID = "target_user_id"
TARGET_GAME_CREDIT_ID = "target_game_credit_id"

ADMIN_REJECTED_ATTEMPT_TARGET_FIELDS = (
    TARGET_USER_ID,
    TARGET_GAME_CREDIT_ID,
)

REJECTION_MODES = frozenset(
    {
        REJECTION_PERMISSION_DENIED_PRELOAD,
        REJECTION_DOMAIN_REJECTED_POSTLOAD,
    }
)

PERMISSION_DENIED_ATTEMPTED_REF_FIELDS = frozenset(
    {
        "user_id",
        "source_game_id",
        "source_booking_id",
        "source_payment_id",
        "game_credit_id",
    }
)


@dataclass(frozen=True)
class AdminRejectedAttemptPolicy:
    attempt_type: str
    read_permission: str
    allowed_target_fields: frozenset[str]


def target_set(*fields: str) -> frozenset[str]:
    return frozenset(fields)


ADMIN_REJECTED_ATTEMPT_POLICIES: dict[str, AdminRejectedAttemptPolicy] = {
    ATTEMPT_TYPE_ISSUE_CREDIT_REJECTED: AdminRejectedAttemptPolicy(
        attempt_type=ATTEMPT_TYPE_ISSUE_CREDIT_REJECTED,
        read_permission=PERMISSION_AUDIT_READ,
        allowed_target_fields=target_set(TARGET_USER_ID),
    ),
    ATTEMPT_TYPE_REVERSE_CREDIT_REJECTED: AdminRejectedAttemptPolicy(
        attempt_type=ATTEMPT_TYPE_REVERSE_CREDIT_REJECTED,
        read_permission=PERMISSION_AUDIT_READ,
        allowed_target_fields=target_set(TARGET_GAME_CREDIT_ID),
    ),
    ATTEMPT_TYPE_SUSPEND_USER_REJECTED: AdminRejectedAttemptPolicy(
        attempt_type=ATTEMPT_TYPE_SUSPEND_USER_REJECTED,
        read_permission=PERMISSION_AUDIT_READ,
        allowed_target_fields=target_set(TARGET_USER_ID),
    ),
    ATTEMPT_TYPE_DELETE_USER_REJECTED: AdminRejectedAttemptPolicy(
        attempt_type=ATTEMPT_TYPE_DELETE_USER_REJECTED,
        read_permission=PERMISSION_AUDIT_READ,
        allowed_target_fields=target_set(TARGET_USER_ID),
    ),
}


def get_admin_rejected_attempt_policy(
    attempt_type: str,
) -> AdminRejectedAttemptPolicy | None:
    return ADMIN_REJECTED_ATTEMPT_POLICIES.get(attempt_type)
