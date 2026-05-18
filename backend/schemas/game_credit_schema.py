from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


class GameCreditIssueCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    user_id: UUID
    amount_cents: int = Field(gt=0)
    credit_reason: str = "admin_credit"
    source_game_id: UUID | None = None
    source_booking_id: UUID | None = None
    source_payment_id: UUID | None = None
    idempotency_key: str | None = None
    note: str | None = None
    expires_at: datetime | None = None


class GameCreditReverseCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    idempotency_key: str | None = None
    note: str | None = None


class GameCreditRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    amount_cents: int
    remaining_cents: int
    currency: str
    credit_status: str
    credit_reason: str
    source_game_id: UUID | None
    source_booking_id: UUID | None
    source_payment_id: UUID | None
    issued_by_user_id: UUID | None
    reversed_by_user_id: UUID | None
    idempotency_key: str
    note: str | None
    expires_at: datetime | None
    reversed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class GameCreditUsageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    game_credit_id: UUID
    user_id: UUID
    booking_id: UUID | None
    amount_cents: int
    currency: str
    usage_type: str
    idempotency_key: str
    created_at: datetime


class GameCreditBalanceRead(BaseModel):
    user_id: UUID
    available_credit_cents: int
    currency: str = "USD"
