from uuid import UUID

from pydantic import BaseModel, ConfigDict

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


class GameCheckoutPaymentIntentCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    guest_count: int = 0
    payment_method_id: UUID | None = None
    return_url: str | None = None


class GameCheckoutPaymentIntentRead(BaseModel):
    client_secret: str
    booking_id: UUID
    payment_id: UUID
    amount_cents: int
    currency: str
    stripe_status: str


class GameCheckoutStatusRead(BaseModel):
    booking_id: UUID
    booking_status: str
    booking_payment_status: str
    payment_id: UUID | None = None
    payment_status: str | None = None
    amount_cents: int
    currency: str
