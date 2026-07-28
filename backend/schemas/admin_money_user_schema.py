from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AdminMoneyPaymentMethodRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    card_brand: str
    card_last4: str
    exp_month: int
    exp_year: int
    method_status: str
    is_default: bool
    created_at: datetime
    updated_at: datetime
    detached_at: datetime | None

class AdminMoneyUserSummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    email: str | None
    account_status: str
    created_at: datetime

class AdminMoneyUserSnapshotRead(BaseModel):
    available_credit_cents: int
    currency: str = "USD"
    open_money_issue_count: int

class AdminMoneyPreviewSectionRead(BaseModel):
    items: list[Any] = Field(default_factory=list)
    has_more: bool = False

class AdminMoneySavedCardsSectionRead(BaseModel):
    items: list[AdminMoneyPaymentMethodRead] = Field(default_factory=list)
    active_count: int = 0
    has_more: bool = False
    includes_inactive: bool = False
    next_cursor: str | None = None

class AdminMoneyUserIssuePreviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    issue_type: str
    origin_workflow: str
    value_kind: str
    amount_cents: int | None
    currency: str
    target_payment_id: UUID | None
    target_refund_id: UUID | None
    target_game_credit_id: UUID | None
    target_credit_usage_id: UUID | None
    latest_reason_code: str | None
    latest_summary: str | None
    recommended_action_code: str
    first_detected_at: datetime
    last_detected_at: datetime

class AdminMoneyUserPaymentPreviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    booking_id: UUID | None
    game_id: UUID | None
    payment_type: str
    amount_cents: int
    currency: str
    payment_status: str
    paid_at: datetime | None
    is_fully_refunded: bool = False
    context_label: str | None = None
    created_at: datetime

class AdminMoneyUserRefundPreviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    payment_id: UUID
    booking_id: UUID | None
    participant_id: UUID | None
    host_publish_fee_id: UUID | None
    amount_cents: int
    currency: str
    refund_reason: str
    refund_status: str
    refunded_at: datetime | None
    context_label: str | None = None
    created_at: datetime

class AdminMoneyUserCreditPreviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    amount_cents: int
    available_cents: int
    currency: str
    credit_status: str
    credit_reason: str
    source_game_id: UUID | None
    source_booking_id: UUID | None
    source_payment_id: UUID | None
    context_label: str | None = None
    created_at: datetime

class AdminMoneyPaymentPreviewSectionRead(BaseModel):
    items: list[AdminMoneyUserPaymentPreviewRead] = Field(default_factory=list)
    has_more: bool = False

class AdminMoneyRefundPreviewSectionRead(BaseModel):
    items: list[AdminMoneyUserRefundPreviewRead] = Field(default_factory=list)
    has_more: bool = False

class AdminMoneyCreditPreviewSectionRead(BaseModel):
    items: list[AdminMoneyUserCreditPreviewRead] = Field(default_factory=list)
    has_more: bool = False

class AdminMoneyIssuePreviewSectionRead(BaseModel):
    items: list[AdminMoneyUserIssuePreviewRead] = Field(default_factory=list)
    count: int
    has_more: bool = False

class AdminMoneyUserDetailRead(BaseModel):
    user: AdminMoneyUserSummaryRead
    snapshot: AdminMoneyUserSnapshotRead
    open_money_issues: AdminMoneyIssuePreviewSectionRead
    saved_cards: AdminMoneySavedCardsSectionRead
    recent_payments: AdminMoneyPaymentPreviewSectionRead
    recent_refunds: AdminMoneyRefundPreviewSectionRead
    recent_credits: AdminMoneyCreditPreviewSectionRead
