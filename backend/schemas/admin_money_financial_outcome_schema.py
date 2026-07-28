from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


class AdminMoneyFinancialOutcomeCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    outcome: str
    reason: str = Field(min_length=3, max_length=1000)
    internal_note: str | None = Field(default=None, max_length=1000)
    idempotency_key: str = Field(min_length=8, max_length=160)
    host_publish_fee_id: UUID | None = None
    host_user_id: UUID | None = None
    target_game_id: UUID | None = None
    amount_cents: int | None = None

class AdminMoneyFinancialOutcomeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    target_game_id: UUID | None
    target_sub_post_id: UUID | None
    host_user_id: UUID
    host_publish_fee_id: UUID | None
    payment_id: UUID | None
    refund_id: UUID | None
    host_publish_entitlement_id: UUID | None
    admin_action_id: UUID | None
    review_case_id: UUID | None
    outcome: str
    applied_status: str
    amount_cents: int
    currency: str
    reason: str
    internal_note: str | None
    failure_reason: str | None
    created_by_user_id: UUID
    applied_by_user_id: UUID | None
    applied_at: datetime | None
    created_at: datetime
    updated_at: datetime
