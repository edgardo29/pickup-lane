from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.schemas.game_schema import GameRead
from backend.schemas.game_credit_schema import GameCreditRead, GameCreditUsageRead
from backend.schemas.game_participant_schema import GameParticipantRead
from backend.schemas.payment_schema import PaymentRead
from backend.schemas.refund_schema import RefundRead

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


class AdminOfficialGameVenuePayload(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    name: str
    address_line_1: str
    city: str
    state: str
    postal_code: str
    country_code: str = "US"
    neighborhood: str | None = None


class AdminOfficialGameCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    title: str | None = None
    venue_id: UUID | None = None
    venue: AdminOfficialGameVenuePayload | None = None
    starts_at: datetime
    ends_at: datetime
    timezone: str = "America/Chicago"
    format_label: str
    game_player_group: str = "coed"
    skill_level: str = "any"
    environment_type: str
    total_spots: int
    price_per_player_cents: int
    allow_guests: bool = True
    max_guests_per_booking: int = 2
    waitlist_enabled: bool = True
    is_chat_enabled: bool = True
    game_notes: str | None = None
    parking_notes: str | None = None
    reason: str | None = None
    replacement_for_game_id: UUID | None = None


class AdminOfficialGameUpdate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    title: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    timezone: str | None = None
    format_label: str | None = None
    game_player_group: str | None = None
    skill_level: str | None = None
    environment_type: str | None = None
    total_spots: int | None = None
    price_per_player_cents: int | None = None
    allow_guests: bool | None = None
    max_guests_per_booking: int | None = None
    waitlist_enabled: bool | None = None
    is_chat_enabled: bool | None = None
    game_notes: str | None = None
    parking_notes: str | None = None
    reason: str | None = None


class AdminOfficialGameHostAssign(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    host_user_id: UUID
    reason: str | None = None


class AdminOfficialGameHostRemove(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    reason: str | None = None


class AdminOfficialGamePlayerAdd(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    user_id: UUID
    reason: str | None = None


class AdminOfficialGamePlayerRemove(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    reason: str | None = None


class AdminOfficialGameUserSearchEligibilityRead(BaseModel):
    can_add: bool
    reason: str | None = None


class AdminOfficialGameUserSearchResultRead(BaseModel):
    user_id: UUID
    display_name: str
    email: str | None = None
    status: str
    eligibility: AdminOfficialGameUserSearchEligibilityRead


class AdminOfficialGameUserSearchRead(BaseModel):
    results: list[AdminOfficialGameUserSearchResultRead] = Field(default_factory=list)


class AdminOfficialGameParticipantRead(GameParticipantRead):
    user_email: str | None = None


class AdminOfficialGamePlayerRemovalExecute(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    preview_token: str = Field(min_length=64, max_length=64)
    outcome: str
    reason: str = Field(min_length=1, max_length=1000)


class AdminOfficialGameCancelExecute(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    preview_token: str = Field(min_length=64, max_length=64)
    reason: str = Field(min_length=1, max_length=500)


class AdminOfficialGameRemovalParticipantRead(BaseModel):
    id: UUID
    display_name: str
    participant_type: str
    participant_status: str
    price_cents: int
    is_selected: bool


class AdminOfficialGamePlayerRemovalPreviewRead(BaseModel):
    game_id: UUID
    selected_participant_id: UUID
    selected_participant_name: str
    booking_id: UUID | None = None
    buyer_user_id: UUID | None = None
    removal_scope: str
    classification: str
    automatic_outcome_available: bool
    preview_token: str
    blocking_reasons: list[str] = Field(default_factory=list)
    allowed_outcomes: list[str] = Field(default_factory=list)
    affected_participants: list[AdminOfficialGameRemovalParticipantRead] = Field(
        default_factory=list
    )
    booking_status: str | None = None
    booking_payment_status: str | None = None
    booking_total_cents: int = 0
    currency: str = "USD"
    payment_statuses: list[str] = Field(default_factory=list)
    refund_statuses: list[str] = Field(default_factory=list)
    cash_collected_cents: int = 0
    cash_refunded_cents: int = 0
    cash_refund_pending_cents: int = 0
    cash_refundable_cents: int = 0
    credit_reserved_cents: int = 0
    credit_redeemed_cents: int = 0
    credit_released_cents: int = 0
    credit_restored_cents: int = 0
    credit_reversed_cents: int = 0
    credit_restorable_cents: int = 0
    spots_opened: int = 0
    available_spots_after_removal: int = 0
    active_waitlist_entry_count: int = 0
    active_waitlist_player_count: int = 0
    next_waitlist_party_size: int | None = None
    waitlist_promotion_possible: bool = False


class AdminOfficialGameRemovalRefundRead(BaseModel):
    id: UUID
    payment_id: UUID
    amount_cents: int
    currency: str
    refund_status: str


class AdminOfficialGamePlayerRemovalResultRead(BaseModel):
    game_id: UUID
    selected_participant_id: UUID
    booking_id: UUID
    outcome: str
    removed_participant_ids: list[UUID] = Field(default_factory=list)
    booking_status: str
    booking_payment_status: str
    refunds: list[AdminOfficialGameRemovalRefundRead] = Field(default_factory=list)
    credit_restored_count: int = 0
    credit_restored_cents: int = 0
    refund_follow_up_required: bool = False
    money_issue_ids: list[UUID] = Field(default_factory=list)
    waitlist_advanced_entry_ids: list[UUID] = Field(default_factory=list)


class AdminOfficialGameCancellationBookingImpactRead(BaseModel):
    booking_id: UUID
    buyer_user_id: UUID
    booking_status: str
    booking_payment_status: str
    participant_count: int = 0
    payment_statuses: list[str] = Field(default_factory=list)
    refund_statuses: list[str] = Field(default_factory=list)
    result_category: str
    cash_refundable_cents: int = 0
    credit_restorable_cents: int = 0
    credit_releasable_cents: int = 0
    follow_up_required: bool = False
    follow_up_reason: str | None = None


class AdminOfficialGameCancellationPreviewRead(BaseModel):
    game_id: UUID
    game_status: str
    preview_token: str
    booking_count: int = 0
    participant_count: int = 0
    waitlist_entry_count: int = 0
    cash_refundable_cents: int = 0
    credit_restorable_cents: int = 0
    credit_releasable_cents: int = 0
    refund_follow_up_required: bool = False
    payment_follow_up_required: bool = False
    booking_impacts: list[AdminOfficialGameCancellationBookingImpactRead] = Field(
        default_factory=list
    )


class AdminOfficialGameCancellationRefundRead(BaseModel):
    id: UUID
    payment_id: UUID
    amount_cents: int
    currency: str
    refund_status: str


class AdminOfficialGameCancellationBookingResultRead(BaseModel):
    booking_id: UUID
    buyer_user_id: UUID
    booking_status: str
    booking_payment_status: str
    result_category: str
    refunds: list[AdminOfficialGameCancellationRefundRead] = Field(
        default_factory=list
    )
    cash_refunded_cents: int = 0
    credit_restored_cents: int = 0
    credit_released_cents: int = 0
    follow_up_required: bool = False
    follow_up_reason: str | None = None


class AdminOfficialGameCancellationResultRead(BaseModel):
    game: GameRead
    preview_token: str
    cancelled_booking_count: int = 0
    cancelled_participant_count: int = 0
    cancelled_waitlist_entry_count: int = 0
    notified_user_count: int = 0
    refund_created_count: int = 0
    refund_failed_count: int = 0
    refund_processing_count: int = 0
    refund_missing_charge_count: int = 0
    credit_restored_count: int = 0
    credit_restored_cents: int = 0
    credit_released_count: int = 0
    credit_released_cents: int = 0
    refund_follow_up_required: bool = False
    payment_follow_up_required: bool = False
    money_issue_ids: list[UUID] = Field(default_factory=list)
    booking_results: list[AdminOfficialGameCancellationBookingResultRead] = Field(
        default_factory=list
    )


class AdminOfficialGameMoneyRead(BaseModel):
    payments: list[PaymentRead] = Field(default_factory=list)
    refunds: list[RefundRead] = Field(default_factory=list)
    credits: list[GameCreditRead] = Field(default_factory=list)
    credit_usages: list[GameCreditUsageRead] = Field(default_factory=list)


class AdminOfficialGameRead(BaseModel):
    game: GameRead


class AdminOfficialGameCardRead(BaseModel):
    id: UUID
    title: str
    venue_name_snapshot: str
    starts_at: datetime
    ends_at: datetime
    starts_on_local: date
    timezone: str
    city_snapshot: str
    state_snapshot: str
    format_label: str
    game_player_group: str
    environment_type: str
    price_per_player_cents: int
    currency: str
    total_spots: int
    booked_spots: int
    host_user_id: UUID | None = None
    primary_venue_image_url: str | None = None
    issues: list[str] = Field(default_factory=list)


class AdminOfficialGameListRead(BaseModel):
    games: list[AdminOfficialGameCardRead] = Field(default_factory=list)
    next_cursor: str | None = None
    has_more: bool = False
    limit: int = 24
