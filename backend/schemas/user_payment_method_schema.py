from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# UserPaymentMethodCreate defines the fields the client is allowed to send when
# creating a saved payment-method reference for a user. Server-managed
# timestamps stay out of the request body.
class UserPaymentMethodCreate(BaseModel):
    user_id: UUID
    provider: str = "stripe"
    provider_payment_method_id: str
    card_brand: str | None = None
    card_last4: str | None = None
    exp_month: int | None = None
    exp_year: int | None = None
    is_default: bool = False
    is_active: bool = True


# UserPaymentMethodRead defines the payment-method payload returned by the API.
# from_attributes allows Pydantic to serialize directly from a SQLAlchemy model
# instance.
class UserPaymentMethodRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    provider: str
    provider_payment_method_id: str
    card_brand: str | None
    card_last4: str | None
    exp_month: int | None
    exp_year: int | None
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


# UserPaymentMethodUpdate supports partial updates to saved payment-method
# state only. Stripe-backed identity fields like provider, last4, and the
# provider payment method ID should come from Stripe when the payment method is
# created, not be edited freely through this API.
class UserPaymentMethodUpdate(BaseModel):
    is_default: bool | None = None
    is_active: bool | None = None
