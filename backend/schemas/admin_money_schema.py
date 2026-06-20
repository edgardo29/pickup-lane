from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


class AdminMoneyRefundRetryCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    reason: str = Field(min_length=3, max_length=1000)
    idempotency_key: str = Field(min_length=8, max_length=160)


class AdminMoneyPaymentListRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    payer_user_id: UUID
    booking_id: UUID | None
    game_id: UUID | None
    payment_type: str
    provider: str
    amount_cents: int
    currency: str
    payment_status: str
    paid_at: datetime | None
    failure_code: str | None
    created_at: datetime
    updated_at: datetime


class AdminMoneyPaymentDetailItemRead(AdminMoneyPaymentListRead):
    provider_payment_intent_id: str | None
    provider_charge_id: str | None
    failure_message: str | None
    failure_reason: str | None


class AdminMoneyBookingContextRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    game_id: UUID
    buyer_user_id: UUID
    booking_status: str
    payment_status: str
    participant_count: int
    subtotal_cents: int
    platform_fee_cents: int
    discount_cents: int
    total_cents: int
    currency: str
    booked_at: datetime | None
    cancelled_at: datetime | None
    cancelled_by_user_id: UUID | None
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AdminMoneyGameContextRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    game_type: str
    payment_collection_type: str
    publish_status: str
    game_status: str
    title: str
    venue_name_snapshot: str
    starts_at: datetime
    ends_at: datetime
    timezone: str
    price_per_player_cents: int
    currency: str


class AdminMoneyRefundListRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    payment_id: UUID
    booking_id: UUID | None
    participant_id: UUID | None
    amount_cents: int
    currency: str
    refund_reason: str
    refund_status: str
    requested_by_user_id: UUID | None
    approved_by_user_id: UUID | None
    requested_at: datetime
    approved_at: datetime | None
    refunded_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AdminMoneyRefundDetailItemRead(AdminMoneyRefundListRead):
    provider_refund_id: str | None


class AdminMoneyCreditGrantSummaryRead(BaseModel):
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
    expires_at: datetime | None
    reversed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AdminMoneyCreditUsageSummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    game_credit_id: UUID
    user_id: UUID
    booking_id: UUID | None
    game_id: UUID | None
    payment_id: UUID | None
    amount_cents: int
    currency: str
    usage_type: str
    usage_status: str
    release_reason: str | None
    reserved_at: datetime | None
    redeemed_at: datetime | None
    released_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AdminMoneySupportFlagSummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    flag_type: str
    flag_status: str
    severity: str
    source: str
    title: str
    summary: str
    target_user_id: UUID | None
    target_game_id: UUID | None
    target_booking_id: UUID | None
    target_payment_id: UUID | None
    target_refund_id: UUID | None
    target_game_credit_id: UUID | None
    source_admin_action_id: UUID | None
    resolution_outcome: str | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AdminMoneyAuditActionSummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    admin_user_id: UUID
    action_type: str
    target_user_id: UUID | None
    target_game_id: UUID | None
    target_booking_id: UUID | None
    target_participant_id: UUID | None
    target_payment_id: UUID | None
    target_refund_id: UUID | None
    target_game_credit_id: UUID | None
    target_support_flag_id: UUID | None
    reason: str | None
    metadata: dict[str, Any] | None = Field(
        validation_alias="metadata_",
        serialization_alias="metadata",
    )
    created_at: datetime


class AdminMoneyPaymentMethodRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
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
    role: str
    email: str | None
    first_name: str | None
    last_name: str | None
    account_status: str
    hosting_status: str
    member_since: datetime
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class AdminMoneyPaymentDetailRead(BaseModel):
    payment: AdminMoneyPaymentDetailItemRead
    booking: AdminMoneyBookingContextRead | None = None
    game: AdminMoneyGameContextRead | None = None
    refunds: list[AdminMoneyRefundDetailItemRead] = Field(default_factory=list)
    credit_grants: list[AdminMoneyCreditGrantSummaryRead] = Field(default_factory=list)
    credit_usages: list[AdminMoneyCreditUsageSummaryRead] = Field(default_factory=list)
    support_flags: list[AdminMoneySupportFlagSummaryRead] = Field(default_factory=list)
    audit_actions: list[AdminMoneyAuditActionSummaryRead] = Field(default_factory=list)


class AdminMoneyRefundDetailRead(BaseModel):
    refund: AdminMoneyRefundDetailItemRead
    payment: AdminMoneyPaymentDetailItemRead | None = None
    booking: AdminMoneyBookingContextRead | None = None
    game: AdminMoneyGameContextRead | None = None
    credit_grants: list[AdminMoneyCreditGrantSummaryRead] = Field(default_factory=list)
    credit_usages: list[AdminMoneyCreditUsageSummaryRead] = Field(default_factory=list)
    support_flags: list[AdminMoneySupportFlagSummaryRead] = Field(default_factory=list)
    audit_actions: list[AdminMoneyAuditActionSummaryRead] = Field(default_factory=list)


class AdminMoneySupportFlagDetailRead(BaseModel):
    support_flag: AdminMoneySupportFlagSummaryRead
    payments: list[AdminMoneyPaymentDetailItemRead] = Field(default_factory=list)
    refunds: list[AdminMoneyRefundDetailItemRead] = Field(default_factory=list)
    booking: AdminMoneyBookingContextRead | None = None
    game: AdminMoneyGameContextRead | None = None
    credit_grants: list[AdminMoneyCreditGrantSummaryRead] = Field(default_factory=list)
    credit_usages: list[AdminMoneyCreditUsageSummaryRead] = Field(default_factory=list)
    audit_actions: list[AdminMoneyAuditActionSummaryRead] = Field(default_factory=list)


class AdminMoneyCreditDetailRead(BaseModel):
    credit: AdminMoneyCreditGrantSummaryRead
    credit_usages: list[AdminMoneyCreditUsageSummaryRead] = Field(default_factory=list)
    payments: list[AdminMoneyPaymentDetailItemRead] = Field(default_factory=list)
    refunds: list[AdminMoneyRefundDetailItemRead] = Field(default_factory=list)
    booking: AdminMoneyBookingContextRead | None = None
    game: AdminMoneyGameContextRead | None = None
    support_flags: list[AdminMoneySupportFlagSummaryRead] = Field(default_factory=list)
    audit_actions: list[AdminMoneyAuditActionSummaryRead] = Field(default_factory=list)


class AdminMoneyUserDetailRead(BaseModel):
    user: AdminMoneyUserSummaryRead
    payments: list[AdminMoneyPaymentDetailItemRead] = Field(default_factory=list)
    refunds: list[AdminMoneyRefundDetailItemRead] = Field(default_factory=list)
    credit_grants: list[AdminMoneyCreditGrantSummaryRead] = Field(default_factory=list)
    credit_usages: list[AdminMoneyCreditUsageSummaryRead] = Field(default_factory=list)
    payment_methods: list[AdminMoneyPaymentMethodRead] = Field(default_factory=list)
    support_flags: list[AdminMoneySupportFlagSummaryRead] = Field(default_factory=list)
    audit_actions: list[AdminMoneyAuditActionSummaryRead] = Field(default_factory=list)
