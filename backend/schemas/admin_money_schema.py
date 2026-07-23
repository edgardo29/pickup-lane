from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


class AdminMoneyRefundRetryCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    reason: str = Field(min_length=3, max_length=1000)
    idempotency_key: str = Field(min_length=8, max_length=160)


class AdminMoneyRefundReconcileCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    reason: str = Field(min_length=3, max_length=1000)
    idempotency_key: str = Field(min_length=8, max_length=160)


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


class AdminMoneyDisplayRead(BaseModel):
    user_name: str | None = None
    user_email: str | None = None
    game_label: str | None = None
    context_label: str | None = None
    payment_short_label: str | None = None
    refund_short_label: str | None = None
    credit_short_label: str | None = None


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


class AdminMoneyParticipantContextRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    game_id: UUID
    booking_id: UUID | None
    participant_type: str
    participant_status: str
    user_id: UUID | None
    guest_of_user_id: UUID | None
    guest_name: str | None
    display_name_snapshot: str
    price_cents: int
    currency: str
    cancelled_at: datetime | None
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


class AdminMoneyPaymentUserContextRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str | None
    first_name: str | None
    last_name: str | None
    account_status: str


class AdminMoneyHostPublishFeeContextRead(BaseModel):
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


class AdminMoneyCommunityPublishAttemptContextRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    host_user_id: UUID
    payment_id: UUID | None
    created_game_id: UUID | None
    attempt_status: str
    starts_on_local: date
    amount_cents: int
    currency: str
    failure_code: str | None
    failure_message: str | None
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime


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
    target_credit_usage_id: UUID | None
    target_financial_outcome_id: UUID | None
    target_host_publish_fee_id: UUID | None
    target_host_publish_entitlement_id: UUID | None
    target_money_issue_id: UUID | None
    reason: str | None
    metadata: dict[str, Any] | None = Field(
        validation_alias="metadata_",
        serialization_alias="metadata",
    )
    created_at: datetime


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


class AdminMoneyIssueListResponseRead(BaseModel):
    items: list[AdminMoneyIssueSummaryRead] = Field(default_factory=list)
    has_more: bool = False
    next_cursor: str | None = None


class AdminMoneyPaymentListResponseRead(BaseModel):
    items: list[AdminMoneyPaymentListRead] = Field(default_factory=list)
    has_more: bool = False
    next_cursor: str | None = None


class AdminMoneyPaymentDetailRead(BaseModel):
    payment: AdminMoneyPaymentDetailItemRead
    payer: AdminMoneyPaymentUserContextRead | None = None
    booking: AdminMoneyBookingContextRead | None = None
    game: AdminMoneyGameContextRead | None = None
    host_publish_fee: AdminMoneyHostPublishFeeContextRead | None = None
    community_publish_attempt: AdminMoneyCommunityPublishAttemptContextRead | None = None
    publish_host: AdminMoneyPaymentUserContextRead | None = None
    refunds: list[AdminMoneyRefundDetailItemRead] = Field(default_factory=list)
    credit_grants: list[AdminMoneyCreditGrantSummaryRead] = Field(default_factory=list)
    credit_usages: list[AdminMoneyCreditUsageSummaryRead] = Field(default_factory=list)
    linked_money_issues: list[AdminMoneyIssueSummaryRead] = Field(default_factory=list)
    admin_actions: list[AdminMoneyAuditActionSummaryRead] = Field(default_factory=list)


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


class AdminMoneyIssueDetailRead(BaseModel):
    money_issue: AdminMoneyIssueSummaryRead
    events: list[AdminMoneyIssueEventRead] = Field(default_factory=list)
    recent_refund_events: list[AdminMoneyRefundEventRead] = Field(default_factory=list)
    refund: AdminMoneyRefundDetailItemRead | None = None
    payment: AdminMoneyPaymentDetailItemRead | None = None
    booking: AdminMoneyBookingContextRead | None = None
    game: AdminMoneyGameContextRead | None = None
    credit: AdminMoneyCreditGrantSummaryRead | None = None
    credit_usages: list[AdminMoneyCreditUsageSummaryRead] = Field(default_factory=list)


class AdminMoneyCreditDetailRead(BaseModel):
    credit: AdminMoneyCreditGrantSummaryRead
    credit_usages: list[AdminMoneyCreditUsageSummaryRead] = Field(default_factory=list)
    credit_usage_count: int = 0
    credit_usages_truncated: bool = False
    payments: list[AdminMoneyPaymentDetailItemRead] = Field(default_factory=list)
    refunds: list[AdminMoneyRefundDetailItemRead] = Field(default_factory=list)
    booking: AdminMoneyBookingContextRead | None = None
    game: AdminMoneyGameContextRead | None = None
    linked_money_issues: list[AdminMoneyIssueSummaryRead] = Field(default_factory=list)
    admin_actions: list[AdminMoneyAuditActionSummaryRead] = Field(default_factory=list)


class AdminMoneyUserDetailRead(BaseModel):
    user: AdminMoneyUserSummaryRead
    snapshot: AdminMoneyUserSnapshotRead
    open_money_issues: AdminMoneyIssuePreviewSectionRead
    saved_cards: AdminMoneySavedCardsSectionRead
    recent_payments: AdminMoneyPaymentPreviewSectionRead
    recent_refunds: AdminMoneyRefundPreviewSectionRead
    recent_credits: AdminMoneyCreditPreviewSectionRead
