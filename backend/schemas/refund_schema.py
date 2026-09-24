from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


# RefundRead defines the refund payload returned by the API.
class RefundRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    payment_id: UUID
    booking_id: UUID | None
    participant_id: UUID | None
    host_publish_fee_id: UUID | None
    origin_workflow: str
    provider: str
    provider_refund_id: str | None
    origin_operation_key: str
    current_attempt_number: int
    stripe_request_key: str | None
    provider_attempt_started_at: datetime | None
    automatic_mutation_blocked_reason: str | None
    automatic_mutation_blocked_at: datetime | None
    provider_charge_id: str | None
    provider_status: str | None
    provider_status_observed_at: datetime | None
    last_refund_event_at: datetime | None
    amount_cents: int
    currency: str
    refund_reason: str
    refund_status: str
    requested_by_user_id: UUID | None
    approved_by_user_id: UUID | None
    requested_at: datetime
    approved_at: datetime | None
    refunded_at: datetime | None
    created_at: datetime
    updated_at: datetime


class RefundSummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    payment_id: UUID
    booking_id: UUID | None
    participant_id: UUID | None
    host_publish_fee_id: UUID | None
    amount_cents: int
    currency: str
    refund_reason: str
    refund_status: str
    current_attempt_number: int
    requested_at: datetime
    refunded_at: datetime | None
    created_at: datetime


class AdminRefundRead(RefundRead):
    pass
