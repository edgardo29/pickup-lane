from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AdminMoneyDisplayRead(BaseModel):
    user_name: str | None = None
    user_email: str | None = None
    game_label: str | None = None
    context_label: str | None = None
    payment_short_label: str | None = None
    refund_short_label: str | None = None
    credit_short_label: str | None = None

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
