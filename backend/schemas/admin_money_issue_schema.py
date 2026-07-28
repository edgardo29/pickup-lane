from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.schemas.admin_money_context_schema import AdminMoneyDisplayRead


REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


class AdminMoneyIssueResolveCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    resolution_reason_code: str = Field(min_length=3, max_length=80)
    resolution_note: str | None = Field(default=None, max_length=1000)
    resolution_external_reference: str | None = Field(default=None, max_length=255)
    idempotency_key: str = Field(min_length=8, max_length=160)

class AdminMoneyIssueCreditRetryCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    reason: str = Field(min_length=3, max_length=1000)
    idempotency_key: str = Field(min_length=8, max_length=160)

class AdminMoneyIssueSummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    operation_key: str
    status: str
    issue_type: str
    origin_workflow: str
    value_kind: str
    amount_cents: int | None
    currency: str
    target_user_id: UUID | None
    target_game_id: UUID | None
    target_booking_id: UUID | None
    target_payment_id: UUID | None
    target_refund_id: UUID | None
    target_game_credit_id: UUID | None
    target_credit_usage_id: UUID | None
    latest_reason_code: str | None
    latest_summary: str | None
    recommended_action_code: str
    display: AdminMoneyDisplayRead | None = None
    occurrence_count: int
    reopen_count: int
    first_detected_at: datetime
    last_detected_at: datetime
    last_activity_at: datetime
    resolved_at: datetime | None
    resolved_by_user_id: UUID | None
    resolution_reason_code: str | None
    resolution_note: str | None
    resolution_external_reference: str | None
    created_at: datetime
    updated_at: datetime

class AdminMoneyIssueEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    money_issue_id: UUID
    event_type: str
    event_source: str
    actor_user_id: UUID | None
    admin_action_id: UUID | None
    refund_event_id: UUID | None
    result_credit_usage_id: UUID | None
    previous_status: str | None
    new_status: str | None
    previous_issue_type: str | None
    new_issue_type: str | None
    previous_recommended_action_code: str | None
    new_recommended_action_code: str | None
    reason_code: str | None
    summary: str | None
    metadata: dict[str, Any] | None = Field(
        validation_alias="event_metadata",
        serialization_alias="metadata",
    )
    occurred_at: datetime
    created_at: datetime

class AdminMoneyIssueListResponseRead(BaseModel):
    items: list[AdminMoneyIssueSummaryRead] = Field(default_factory=list)
    has_more: bool = False
    next_cursor: str | None = None
