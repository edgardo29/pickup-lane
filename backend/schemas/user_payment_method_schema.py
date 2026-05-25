from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


class UserPaymentMethodSetupIntentCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    set_as_default: bool = True


class UserPaymentMethodSetupIntentRead(BaseModel):
    client_secret: str


class UserPaymentMethodSyncCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    setup_intent_id: str
    set_as_default: bool = True


class UserPaymentMethodRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    card_brand: str
    card_last4: str
    exp_month: int
    exp_year: int
    method_status: str
    is_default: bool
    created_at: datetime
    updated_at: datetime
    detached_at: datetime | None
