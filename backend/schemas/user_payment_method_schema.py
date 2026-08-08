from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


class UserPaymentMethodSetupIntentCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    set_as_default: bool = False


class UserPaymentMethodSetupIntentRead(BaseModel):
    client_secret: str


class UserPaymentMethodSyncCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    setup_intent_id: str = Field(min_length=1, max_length=255)
    set_as_default: bool = False

    @field_validator("setup_intent_id", mode="before")
    @classmethod
    def trim_setup_intent_id(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value


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
