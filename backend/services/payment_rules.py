"""Pure payment-record constants shared by payment workflows."""

VALID_PAYMENT_TYPES = {
    "booking",
    "community_publish_fee",
    "admin_charge",
}
VALID_PROVIDERS = {"stripe"}
VALID_PAYMENT_STATUSES = {
    "requires_payment_method",
    "processing",
    "requires_action",
    "succeeded",
    "failed",
    "canceled",
}
VALID_CURRENCY = "USD"
PENDING_PAYMENT_STATUSES = {
    "requires_payment_method",
    "requires_action",
    "processing",
}
COLLECTED_PAYMENT_STATUSES = {
    "succeeded",
}
SUCCEEDED_PAYMENT_STATUSES = {"succeeded"}
FAILED_PAYMENT_STATUSES = {"failed", "canceled"}
