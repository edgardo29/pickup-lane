from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


class HostPublishFeeCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    game_id: UUID
    host_user_id: UUID
    payment_id: UUID | None = None
    amount_cents: int
    currency: str = "USD"
    fee_status: str
    waiver_reason: str = "none"
    paid_at: datetime | None = None


class HostPublishFeeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    game_id: UUID
    host_user_id: UUID
    payment_id: UUID | None
    amount_cents: int
    currency: str
    fee_status: str
    waiver_reason: str
    paid_at: datetime | None
    created_at: datetime
    updated_at: datetime


class HostPublishFeeUpdate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    game_id: UUID | None = None
    host_user_id: UUID | None = None
    payment_id: UUID | None = None
    amount_cents: int | None = None
    currency: str | None = None
    fee_status: str | None = None
    waiver_reason: str | None = None
    paid_at: datetime | None = None
