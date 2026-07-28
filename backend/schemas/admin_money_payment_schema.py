from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.schemas.admin_money_context_schema import AdminMoneyDisplayRead


class AdminMoneyPaymentListRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    payer_user_id: UUID
    booking_id: UUID | None
    game_id: UUID | None
    payment_type: str
    provider: str
    provider_payment_intent_id: str | None = None
    provider_charge_id: str | None = None
    amount_cents: int
    currency: str
    payment_status: str
    paid_at: datetime | None
    failure_code: str | None
    is_fully_refunded: bool = False
    reserved_credit_cents: int = 0
    redeemed_credit_cents: int = 0
    open_money_issue_count: int = 0
    display: AdminMoneyDisplayRead | None = None
    created_at: datetime

class AdminMoneyPaymentDetailItemRead(AdminMoneyPaymentListRead):
    failure_message: str | None = None
    idempotency_key: str
    updated_at: datetime

class AdminMoneyPaymentListResponseRead(BaseModel):
    items: list[AdminMoneyPaymentListRead] = Field(default_factory=list)
    has_more: bool = False
    next_cursor: str | None = None
