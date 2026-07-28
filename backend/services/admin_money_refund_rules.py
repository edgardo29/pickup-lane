"""Pure rules for admin money refund retry and provider state."""

from datetime import timedelta


RETRYABLE_REFUND_STATUSES = {"failed", "cancelled"}
RETRYABLE_PAYMENT_STATUSES = {"succeeded"}
UNCERTAIN_PROVIDER_REFUND_STATUSES = {"processing", "unknown"}
REFUND_PROCESSING_OVERDUE_AFTER = timedelta(hours=24)


def map_admin_money_retry_refund_status(provider_status: str) -> str:
    normalized_status = provider_status.strip().lower()
    if normalized_status == "succeeded":
        return "succeeded"
    if normalized_status == "failed":
        return "failed"
    if normalized_status in {"canceled", "cancelled"}:
        return "cancelled"
    return "processing"
