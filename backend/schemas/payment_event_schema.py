from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


# PaymentEventCreate defines the fields allowed when recording a provider
# webhook/event audit row.
class PaymentEventCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    payment_id: UUID | None = None
    provider: str = "stripe"
    provider_event_id: str
    event_type: str
    event_envelope: dict[str, Any]
    provider_created_at: datetime
    processing_status: str = "pending"
    processed_at: datetime | None = None
    processing_error_code: str | None = None


# PaymentEventRead defines the payment event payload returned by the API.
class PaymentEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    payment_id: UUID | None
    provider: str
    provider_event_id: str
    event_type: str
    provider_created_at: datetime
    processing_status: str
    processed_at: datetime | None
    processing_error_code: str | None
    created_at: datetime


# PaymentEventUpdate supports the retained admin repair route. Provider-owned
# identity, event type, and normalized envelope remain immutable provider state.
class PaymentEventUpdate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    payment_id: UUID | None = None
    reprocess: bool = False

    @field_validator("payment_id", mode="before")
    @classmethod
    def normalize_payment_id(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value
