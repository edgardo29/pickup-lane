from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


# RefundCreate defines the fields the client/server refund flow is allowed to
# send when recording a Stripe refund request or refund result.
class RefundCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    payment_id: UUID
    booking_id: UUID | None = None
    participant_id: UUID | None = None
    provider_refund_id: str | None = None
    amount_cents: int
    currency: str = "USD"
    refund_reason: str
    refund_status: str = "pending"
    requested_by_user_id: UUID | None = None
    approved_by_user_id: UUID | None = None
    requested_at: datetime | None = None
    approved_at: datetime | None = None
    refunded_at: datetime | None = None


# RefundRead defines the refund payload returned by the API.
class RefundRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    payment_id: UUID
    booking_id: UUID | None
    participant_id: UUID | None
    provider_refund_id: str | None
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


# RefundUpdate supports partial refund updates, so every field is optional and
# only provided values should be applied by the route.
class RefundUpdate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    payment_id: UUID | None = None
    booking_id: UUID | None = None
    participant_id: UUID | None = None
    provider_refund_id: str | None = None
    amount_cents: int | None = None
    currency: str | None = None
    refund_reason: str | None = None
    refund_status: str | None = None
    requested_by_user_id: UUID | None = None
    approved_by_user_id: UUID | None = None
    requested_at: datetime | None = None
    approved_at: datetime | None = None
    refunded_at: datetime | None = None
