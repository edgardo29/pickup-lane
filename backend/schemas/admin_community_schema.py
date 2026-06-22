from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


class AdminCommunityGameHostRead(BaseModel):
    id: UUID
    display_name: str
    account_status: str
    hosting_status: str


class AdminCommunityGameSupportSafeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    game_type: str
    payment_collection_type: str
    publish_status: str
    game_status: str
    title: str
    description: str | None
    venue_id: UUID
    venue_name_snapshot: str
    address_snapshot: str
    city_snapshot: str
    state_snapshot: str
    neighborhood_snapshot: str | None
    starts_at: datetime
    ends_at: datetime
    starts_on_local: date
    timezone: str
    sport_type: str
    format_label: str
    game_player_group: str
    skill_level: str
    environment_type: str
    total_spots: int
    price_per_player_cents: int
    currency: str
    minimum_age: int | None
    allow_guests: bool
    max_guests_per_booking: int
    host_guest_max: int
    waitlist_enabled: bool
    is_chat_enabled: bool
    policy_mode: str
    custom_rules_text: str | None
    custom_cancellation_text: str | None
    game_notes: str | None
    parking_notes: str | None
    published_at: datetime | None
    cancelled_at: datetime | None
    cancel_reason: str | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AdminCommunityGameParticipantSummaryRead(BaseModel):
    total_count: int = 0
    confirmed_count: int = 0
    waitlisted_count: int = 0
    pending_payment_count: int = 0
    inactive_count: int = 0
    registered_user_count: int = 0
    guest_count: int = 0


class AdminCommunityGamePaymentSnapshotRead(BaseModel):
    id: UUID
    payment_methods_snapshot: list[dict[str, Any]] = Field(default_factory=list)
    payment_instructions_snapshot: str | None = None
    payment_text_moderation_status: str
    payment_text_hidden_at: datetime | None = None
    payment_text_hidden_by_user_id: UUID | None = None
    payment_text_hidden_reason: str | None = None
    created_at: datetime
    updated_at: datetime


class AdminCommunityGamePublishFeeRead(BaseModel):
    id: UUID
    amount_cents: int
    currency: str
    fee_status: str
    waiver_reason: str
    paid_at: datetime | None = None
    payment_status: str | None = None
    created_at: datetime
    updated_at: datetime


class AdminCommunityGameSupportFlagSummaryRead(BaseModel):
    id: UUID
    flag_type: str
    flag_status: str
    severity: str
    source: str
    title: str
    summary: str
    resolution_outcome: str | None = None
    resolution_reason: str | None = None
    resolved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AdminCommunityGameAuditActionSummaryRead(BaseModel):
    id: UUID
    admin_user_id: UUID
    action_type: str
    reason: str | None = None
    created_at: datetime


class AdminCommunityGameModerationStateRead(BaseModel):
    host_payment_snapshot_present: bool = False
    unsafe_payment_text_hidden: bool = False
    payment_text_hidden_at: datetime | None = None
    payment_text_hidden_by_user_id: UUID | None = None
    payment_text_hidden_reason: str | None = None
    review_flag_status: str = "not_flagged"


class AdminCommunityGameCapabilitiesRead(BaseModel):
    can_read_audit: bool = False
    can_read_publish_fee: bool = False
    can_flag_game: bool = False
    can_resolve_review_flags: bool = False
    can_hide_unsafe_payment_text: bool = False
    can_cancel_game: bool = False


class AdminCommunityGameListItemRead(BaseModel):
    id: UUID
    title: str
    publish_status: str
    game_status: str
    payment_collection_type: str
    starts_at: datetime
    ends_at: datetime
    timezone: str
    city: str
    state: str
    price_per_player_cents: int
    total_spots: int
    host: AdminCommunityGameHostRead | None = None
    participant_summary: AdminCommunityGameParticipantSummaryRead
    moderation_state: AdminCommunityGameModerationStateRead
    created_at: datetime
    updated_at: datetime


class AdminCommunityGameListRead(BaseModel):
    games: list[AdminCommunityGameListItemRead] = Field(default_factory=list)
    total_count: int = 0
    offset: int = 0
    limit: int = 50


class AdminCommunityGameDetailRead(BaseModel):
    game: AdminCommunityGameSupportSafeRead
    host: AdminCommunityGameHostRead | None = None
    participant_summary: AdminCommunityGameParticipantSummaryRead
    payment_snapshot: AdminCommunityGamePaymentSnapshotRead | None = None
    publish_fee: AdminCommunityGamePublishFeeRead | None = None
    support_flags: list[AdminCommunityGameSupportFlagSummaryRead] = Field(
        default_factory=list
    )
    support_flag_total_count: int = 0
    support_flag_offset: int = 0
    support_flag_limit: int = 50
    audit_actions: list[AdminCommunityGameAuditActionSummaryRead] = Field(
        default_factory=list
    )
    audit_total_count: int = 0
    audit_offset: int = 0
    audit_limit: int = 50
    moderation_state: AdminCommunityGameModerationStateRead
    capabilities: AdminCommunityGameCapabilitiesRead


class AdminCommunityGameHidePaymentTextCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    reason: str = Field(min_length=1, max_length=1000)
    idempotency_key: str = Field(min_length=8, max_length=160)


class AdminCommunityGameHidePaymentTextResultRead(BaseModel):
    game_id: UUID
    payment_snapshot: AdminCommunityGamePaymentSnapshotRead
    moderation_state: AdminCommunityGameModerationStateRead
    audit_action_id: UUID
    idempotent_replay: bool = False


class AdminCommunityGameReviewFlagCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    reason: str = Field(min_length=1, max_length=1000)
    idempotency_key: str = Field(min_length=8, max_length=160)


class AdminCommunityGameReviewFlagResultRead(BaseModel):
    game_id: UUID
    support_flag: AdminCommunityGameSupportFlagSummaryRead
    moderation_state: AdminCommunityGameModerationStateRead
    idempotent_replay: bool = False
