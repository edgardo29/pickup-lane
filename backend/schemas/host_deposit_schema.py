from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


# HostDepositCreate defines the fields allowed when creating the deposit record
# for one community-hosted game.
class HostDepositCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    game_id: UUID
    host_user_id: UUID
    required_amount_cents: int
    currency: str = "USD"
    deposit_status: str = "required"
    payment_id: UUID | None = None
    refund_id: UUID | None = None
    paid_at: datetime | None = None
    released_at: datetime | None = None
    forfeited_at: datetime | None = None
    refunded_at: datetime | None = None
    decision_by_user_id: UUID | None = None
    decision_reason: str | None = None


# HostDepositRead defines the host deposit payload returned by the API.
class HostDepositRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    game_id: UUID
    host_user_id: UUID
    required_amount_cents: int
    currency: str
    deposit_status: str
    payment_id: UUID | None
    refund_id: UUID | None
    paid_at: datetime | None
    released_at: datetime | None
    forfeited_at: datetime | None
    refunded_at: datetime | None
    decision_by_user_id: UUID | None
    decision_reason: str | None
    created_at: datetime
    updated_at: datetime


# HostDepositUpdate supports partial deposit updates, so every field is optional
# and only provided values should be applied by the route.
class HostDepositUpdate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    game_id: UUID | None = None
    host_user_id: UUID | None = None
    required_amount_cents: int | None = None
    currency: str | None = None
    deposit_status: str | None = None
    payment_id: UUID | None = None
    refund_id: UUID | None = None
    paid_at: datetime | None = None
    released_at: datetime | None = None
    forfeited_at: datetime | None = None
    refunded_at: datetime | None = None
    decision_by_user_id: UUID | None = None
    decision_reason: str | None = None
