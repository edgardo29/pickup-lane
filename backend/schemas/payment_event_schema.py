from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


# PaymentEventCreate defines the fields allowed when recording a provider
# webhook/event audit row.
class PaymentEventCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    payment_id: UUID | None = None
    provider: str = "stripe"
    provider_event_id: str
    event_type: str
    raw_payload: dict[str, Any]
    processing_status: str = "pending"
    processed_at: datetime | None = None
    processing_error: str | None = None


# PaymentEventRead defines the payment event payload returned by the API.
class PaymentEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    payment_id: UUID | None
    provider: str
    provider_event_id: str
    event_type: str
    raw_payload: dict[str, Any]
    processing_status: str
    processed_at: datetime | None
    processing_error: str | None
    created_at: datetime


# PaymentEventUpdate supports partial processing updates, so every field is
# optional and only provided values should be applied by the route.
class PaymentEventUpdate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    payment_id: UUID | None = None
    provider: str | None = None
    provider_event_id: str | None = None
    event_type: str | None = None
    raw_payload: dict[str, Any] | None = None
    processing_status: str | None = None
    processed_at: datetime | None = None
    processing_error: str | None = None