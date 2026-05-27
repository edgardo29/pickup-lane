from uuid import UUID

from pydantic import BaseModel, ConfigDict

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


class GameCheckoutPaymentIntentCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    guest_count: int = 0
    payment_method_id: UUID | None = None
    return_url: str | None = None


class GameCheckoutPaymentIntentRead(BaseModel):
    client_secret: str | None
    booking_id: UUID
    payment_id: UUID | None
    amount_cents: int
    currency: str
    stripe_status: str | None
    subtotal_cents: int
    platform_fee_cents: int
    checkout_total_cents: int
    available_credit_cents: int
    credit_applied_cents: int
    minimum_charge_adjustment_cents: int
    final_amount_due_cents: int
    stripe_amount_cents: int
    payment_required: bool
    booking_status: str
    booking_payment_status: str
    payment_status: str | None = None


class GameCheckoutStatusRead(BaseModel):
    booking_id: UUID
    booking_status: str
    booking_payment_status: str
    payment_id: UUID | None = None
    payment_status: str | None = None
    amount_cents: int
    currency: str
    subtotal_cents: int
    platform_fee_cents: int
    checkout_total_cents: int
    available_credit_cents: int
    credit_applied_cents: int
    minimum_charge_adjustment_cents: int
    final_amount_due_cents: int
    stripe_amount_cents: int
    payment_required: bool
