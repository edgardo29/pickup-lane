from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


# PaymentCreate defines the fields the client/server payment flow is allowed to
# send when recording a Stripe-backed payment attempt or payment record.
class PaymentCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    payer_user_id: UUID
    booking_id: UUID | None = None
    game_id: UUID | None = None
    payment_type: str
    provider: str = "stripe"
    provider_payment_intent_id: str | None = None
    provider_charge_id: str | None = None
    idempotency_key: str
    amount_cents: int
    currency: str = "USD"
    payment_status: str
    paid_at: datetime | None = None
    failure_reason: str | None = None
    metadata: dict | None = None


# PaymentRead defines the payment payload returned by the API. The SQLAlchemy
# model uses payment_metadata because metadata is reserved on declarative models.
class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    payer_user_id: UUID
    booking_id: UUID | None
    game_id: UUID | None
    payment_type: str
    provider: str
    provider_payment_intent_id: str | None
    provider_charge_id: str | None
    idempotency_key: str
    amount_cents: int
    currency: str
    payment_status: str
    paid_at: datetime | None
    failure_reason: str | None
    metadata: dict | None = Field(
        validation_alias="payment_metadata",
        serialization_alias="metadata",
    )
    created_at: datetime
    updated_at: datetime


# PaymentUpdate supports partial payment updates, so every field is optional
# and only provided values should be applied by the route.
class PaymentUpdate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    payer_user_id: UUID | None = None
    booking_id: UUID | None = None
    game_id: UUID | None = None
    payment_type: str | None = None
    provider: str | None = None
    provider_payment_intent_id: str | None = None
    provider_charge_id: str | None = None
    idempotency_key: str | None = None
    amount_cents: int | None = None
    currency: str | None = None
    payment_status: str | None = None
    paid_at: datetime | None = None
    failure_reason: str | None = None
    metadata: dict | None = None
