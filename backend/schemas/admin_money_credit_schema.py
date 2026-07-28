from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.schemas.admin_money_context_schema import AdminMoneyDisplayRead


class AdminMoneyCreditGrantListRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    amount_cents: int
    available_cents: int
    reserved_cents: int = 0
    currency: str
    credit_status: str
    credit_reason: str
    source_game_id: UUID | None
    source_booking_id: UUID | None
    source_payment_id: UUID | None
    reversed_at: datetime | None
    open_money_issue_count: int = 0
    display: AdminMoneyDisplayRead | None = None
    created_at: datetime

class AdminMoneyCreditGrantSummaryRead(AdminMoneyCreditGrantListRead):
    issued_by_user_id: UUID | None
    reversed_by_user_id: UUID | None
    idempotency_key: str
    note: str | None
    updated_at: datetime

class AdminMoneyCreditListResponseRead(BaseModel):
    items: list[AdminMoneyCreditGrantListRead] = Field(default_factory=list)
    has_more: bool = False
    next_cursor: str | None = None

class AdminMoneyCreditUsageSummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    game_credit_id: UUID
    booking_id: UUID | None
    game_id: UUID | None
    payment_id: UUID | None
    original_usage_id: UUID | None
    amount_cents: int
    currency: str
    usage_type: str
    usage_status: str
    idempotency_key: str
    reason_code: str | None
    reserved_at: datetime | None
    redeemed_at: datetime | None
    released_at: datetime | None
    created_at: datetime
    updated_at: datetime
