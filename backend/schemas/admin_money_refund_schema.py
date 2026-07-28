from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.schemas.admin_money_context_schema import (
    AdminMoneyAuditActionSummaryRead,
    AdminMoneyBookingContextRead,
    AdminMoneyDisplayRead,
    AdminMoneyGameContextRead,
    AdminMoneyHostPublishFeeContextRead,
    AdminMoneyParticipantContextRead,
    AdminMoneyPaymentUserContextRead,
)
from backend.schemas.admin_money_credit_schema import (
    AdminMoneyCreditGrantSummaryRead,
    AdminMoneyCreditUsageSummaryRead,
)
from backend.schemas.admin_money_issue_schema import AdminMoneyIssueSummaryRead
from backend.schemas.admin_money_payment_schema import AdminMoneyPaymentDetailItemRead


REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


class AdminMoneyRefundRetryCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    reason: str = Field(min_length=3, max_length=1000)
    idempotency_key: str = Field(min_length=8, max_length=160)

class AdminMoneyRefundReconcileCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    reason: str = Field(min_length=3, max_length=1000)
    idempotency_key: str = Field(min_length=8, max_length=160)

class AdminMoneyRefundEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    refund_id: UUID
    event_type: str
    event_source: str
    actor_user_id: UUID | None
    admin_action_id: UUID | None
    idempotency_key: str | None
    provider: str | None
    provider_event_id: str | None
    provider_refund_id: str | None
    provider_charge_id: str | None
    provider_status: str | None
    previous_refund_status: str | None
    new_refund_status: str | None
    reason_code: str | None
    summary: str | None
    metadata: dict[str, Any] | None = Field(
        validation_alias="event_metadata",
        serialization_alias="metadata",
    )
    occurred_at: datetime
    created_at: datetime

class AdminMoneyRefundEventListResponseRead(BaseModel):
    items: list[AdminMoneyRefundEventRead] = Field(default_factory=list)
    has_more: bool = False
    next_cursor: str | None = None

class AdminMoneyRefundListRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    payment_id: UUID
    booking_id: UUID | None
    participant_id: UUID | None
    host_publish_fee_id: UUID | None
    game_id: UUID | None
    target_user_id: UUID | None
    origin_workflow: str
    provider: str
    provider_refund_id: str | None
    provider_charge_id: str | None
    provider_status: str | None
    provider_status_observed_at: datetime | None
    amount_cents: int
    currency: str
    refund_reason: str
    refund_status: str
    requested_by_user_id: UUID | None
    approved_by_user_id: UUID | None
    requested_at: datetime
    approved_at: datetime | None
    refunded_at: datetime | None
    last_refund_event_at: datetime | None
    linked_issue: AdminMoneyIssueSummaryRead | None = None
    display: AdminMoneyDisplayRead | None = None
    created_at: datetime
    updated_at: datetime

class AdminMoneyRefundListResponseRead(BaseModel):
    items: list[AdminMoneyRefundListRead] = Field(default_factory=list)
    has_more: bool = False
    next_cursor: str | None = None

class AdminMoneyRefundDetailItemRead(AdminMoneyRefundListRead):
    pass

class AdminMoneyRefundActionRead(BaseModel):
    action_code: str
    enabled: bool
    blockers: list[str] = Field(default_factory=list)
    confirmation_text: str | None = None

class AdminMoneyRefundProviderSnapshotRead(BaseModel):
    provider: str
    provider_status: str | None
    provider_status_observed_at: datetime | None
    provider_refund_id: str | None
    provider_charge_id: str | None

class AdminMoneyRefundCreditContextRead(BaseModel):
    credit_grants: list[AdminMoneyCreditGrantSummaryRead] = Field(default_factory=list)
    credit_usages: list[AdminMoneyCreditUsageSummaryRead] = Field(default_factory=list)

class AdminMoneyRefundDetailRead(BaseModel):
    refund: AdminMoneyRefundDetailItemRead
    current_provider_snapshot: AdminMoneyRefundProviderSnapshotRead
    payment_summary: AdminMoneyPaymentDetailItemRead | None = None
    user_summary: AdminMoneyPaymentUserContextRead | None = None
    booking_summary: AdminMoneyBookingContextRead | None = None
    participant_summary: AdminMoneyParticipantContextRead | None = None
    game_summary: AdminMoneyGameContextRead | None = None
    publish_fee_summary: AdminMoneyHostPublishFeeContextRead | None = None
    credit_context: AdminMoneyRefundCreditContextRead = Field(
        default_factory=AdminMoneyRefundCreditContextRead
    )
    recent_refund_events: list[AdminMoneyRefundEventRead] = Field(default_factory=list)
    admin_activity: list[AdminMoneyAuditActionSummaryRead] = Field(default_factory=list)
    linked_money_issue: AdminMoneyIssueSummaryRead | None = None
    available_actions: list[AdminMoneyRefundActionRead] = Field(default_factory=list)
