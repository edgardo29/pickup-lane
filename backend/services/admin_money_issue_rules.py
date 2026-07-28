"""Pure rules for admin money issue classification and identity."""

import uuid


ADMIN_MONEY_ISSUE_STATUSES = {"open", "resolved", "all"}
MONEY_ISSUE_EVENT_LIMIT = 100
MONEY_ISSUE_REFUND_EVENT_LIMIT = 100
MONEY_ISSUE_SEARCH_USER_LIMIT = 25
MONEY_ISSUE_OPERATION_KEY_PREFIXES = (
    "refund:",
    "credit-restore:",
    "credit-release:",
)
MONEY_ISSUE_OPERATION_KEY_MIN_PREFIX_CHARS = 8
ISSUE_RESOLUTION_REASONS = {
    "retried_successfully",
    "provider_completed_no_action_required",
    "handled_externally",
    "invalid_issue",
    "unable_to_complete_documented",
}
ISSUE_DEFAULTS = {
    "refund_missing_provider_reference": (
        "cash_refund",
        "recover_provider_reference",
    ),
    "refund_processing_overdue": (
        "cash_refund",
        "verify_provider_refund",
    ),
    "refund_failed": (
        "cash_refund",
        "retry_refund",
    ),
    "refund_cancelled": (
        "cash_refund",
        "retry_refund",
    ),
    "refund_outcome_unknown": (
        "cash_refund",
        "review_unknown_outcome",
    ),
    "credit_restore_failed": (
        "game_credit_restore",
        "retry_credit_restore",
    ),
    "credit_release_failed": (
        "game_credit_release",
        "retry_credit_release",
    ),
}


def build_refund_issue_operation_key(refund_id: uuid.UUID) -> str:
    return f"refund:{refund_id}"


def build_credit_restore_issue_operation_key(usage_id: uuid.UUID) -> str:
    return f"credit-restore:{usage_id}"


def build_credit_release_issue_operation_key(usage_id: uuid.UUID) -> str:
    return f"credit-release:{usage_id}"


def detection_event_type(
    *,
    previous_status: str,
    previous_issue_type: str,
    issue_type: str,
    previous_action: str,
    recommended_action_code: str,
    fallback_event_type: str,
) -> str:
    if previous_status == "resolved":
        return "issue_reopened"
    if previous_issue_type != issue_type:
        return "classification_changed"
    if previous_action != recommended_action_code:
        return "recommended_action_changed"
    return fallback_event_type
