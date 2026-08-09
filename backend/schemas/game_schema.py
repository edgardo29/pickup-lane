from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")
MIN_TOTAL_SPOTS = 6
MAX_TOTAL_SPOTS = 99
MAX_PRICE_PER_PLAYER_CENTS = 99_900
MAX_PLAYER_GUESTS_PER_BOOKING = 2
MAX_CANCEL_REASON_LENGTH = 500
MAX_AUTO_CHARGE_CONSENT_VERSION_LENGTH = 50


# GameCreate defines the fields an admin caller is allowed to send when using
# the generic game creation route. Identity, lifecycle, payment mode, location
# snapshots, and other workflow-owned fields are derived in the service.
class GameCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    game_type: str
    title: str
    description: str | None = None
    venue_id: UUID
    host_user_id: UUID | None = None
    starts_at: datetime
    ends_at: datetime
    timezone: str = "America/Chicago"
    format_label: str
    game_player_group: str = "coed"
    skill_level: str = "any"
    environment_type: str
    total_spots: int = Field(ge=MIN_TOTAL_SPOTS, le=MAX_TOTAL_SPOTS)
    price_per_player_cents: int = Field(ge=0, le=MAX_PRICE_PER_PLAYER_CENTS)
    allow_guests: bool = True
    max_guests_per_booking: int = Field(default=2, ge=0, le=MAX_PLAYER_GUESTS_PER_BOOKING)
    waitlist_enabled: bool = True
    is_chat_enabled: bool = True
    custom_rules_text: str | None = None
    game_notes: str | None = None
    parking_notes: str | None = None


# GameRead defines the game payload returned by the API. from_attributes lets
# Pydantic serialize directly from a SQLAlchemy model instance.
class GameRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    game_type: str
    payment_collection_type: str
    publish_status: str
    game_status: str
    public_visibility_status: str
    join_enforcement_status: str
    title: str
    description: str | None
    venue_id: UUID
    venue_name_snapshot: str
    address_snapshot: str
    city_snapshot: str
    state_snapshot: str
    neighborhood_snapshot: str | None
    host_user_id: UUID | None
    created_by_user_id: UUID
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
    cancelled_by_user_id: UUID | None
    cancellation_source: str | None
    cancel_reason: str | None
    completed_at: datetime | None
    completed_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class GameAvailabilityRead(BaseModel):
    status: str
    occupied_spots: int
    total_spots: int
    spots_remaining: int


class GameTimeGroupRead(BaseModel):
    group_key: str
    total_games: int


class GameCardRead(BaseModel):
    id: UUID
    game_type: str
    game_status: str
    public_visibility_status: str = "visible"
    join_enforcement_status: str = "open"
    title: str
    display_title: str
    venue_name_snapshot: str
    city_snapshot: str
    state_snapshot: str
    location_label: str
    starts_at: datetime
    ends_at: datetime
    starts_on_local: date
    time_group_key: str
    timezone: str
    format_label: str
    game_player_group: str
    environment_type: str
    total_spots: int
    price_per_player_cents: int
    currency: str
    price_label: str
    participant_count: int
    availability: GameAvailabilityRead
    registration_closes_at: datetime
    primary_image_url: str | None = None


class GameCardListRead(BaseModel):
    browse_today: date
    browse_timezone: str
    minimum_browse_date: date
    maximum_browse_date: date
    browse_date: date
    time_groups: list[GameTimeGroupRead]
    games: list[GameCardRead]
    next_cursor: str | None = None
    has_more: bool = False
    limit: int = 40


class MyGameCardRead(BaseModel):
    bucket: str
    game: GameCardRead
    is_host: bool
    participant_id: UUID | None = None
    participant_status: str | None = None
    cancellation_type: str | None = None
    status_label: str
    status_tone: str


class MyGamesListRead(BaseModel):
    items: list[MyGameCardRead]
    next_cursor: str | None = None
    has_more: bool = False
    limit: int = 40


# GameUpdate supports partial generic admin edits. It intentionally excludes
# server-owned lifecycle, identity, provider/payment, and snapshot fields.
class GameUpdate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    title: str | None = None
    description: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    timezone: str | None = None
    format_label: str | None = None
    game_player_group: str | None = None
    skill_level: str | None = None
    environment_type: str | None = None
    total_spots: int | None = Field(default=None, ge=MIN_TOTAL_SPOTS, le=MAX_TOTAL_SPOTS)
    price_per_player_cents: int | None = Field(
        default=None, ge=0, le=MAX_PRICE_PER_PLAYER_CENTS
    )
    allow_guests: bool | None = None
    max_guests_per_booking: int | None = Field(
        default=None, ge=0, le=MAX_PLAYER_GUESTS_PER_BOOKING
    )
    waitlist_enabled: bool | None = None
    is_chat_enabled: bool | None = None
    custom_rules_text: str | None = None
    game_notes: str | None = None
    parking_notes: str | None = None


# GameHostEdit is the safer host-facing edit contract. It intentionally exposes
# only fields a community host should be able to change from the app flow.
class GameHostEdit(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    venue_name: str | None = None
    address_line_1: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    neighborhood: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    format_label: str | None = None
    game_player_group: str | None = None
    skill_level: str | None = None
    environment_type: str | None = None
    total_spots: int | None = Field(default=None, ge=MIN_TOTAL_SPOTS, le=MAX_TOTAL_SPOTS)
    price_per_player_cents: int | None = Field(
        default=None, ge=0, le=MAX_PRICE_PER_PLAYER_CENTS
    )
    custom_rules_text: str | None = None
    game_notes: str | None = None
    parking_notes: str | None = None


class GameJoinCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    guest_count: int = Field(default=0, ge=0, le=MAX_PLAYER_GUESTS_PER_BOOKING)
    payment_method_id: UUID | None = None
    auto_charge_consent_accepted: bool = False
    auto_charge_consent_version: str | None = Field(
        default=None, max_length=MAX_AUTO_CHARGE_CONSENT_VERSION_LENGTH
    )


class GameJoinRead(BaseModel):
    status: str
    message: str
    participant_id: UUID | None = None
    booking_id: UUID | None = None
    waitlist_entry_id: UUID | None = None


class GameLeaveCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG


class GameLeaveRead(BaseModel):
    status: str
    message: str
    refund_eligible: bool
    participant_id: UUID
    booking_id: UUID | None = None


class GameGuestAddCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    guest_count: int = Field(default=1, ge=1)


class GameBookingGuestAddCreate(GameGuestAddCreate):
    guest_count: int = Field(default=1, ge=1, le=MAX_PLAYER_GUESTS_PER_BOOKING)


class GameGuestAddRead(BaseModel):
    status: str
    message: str
    added_count: int
    booking_id: UUID | None = None


class GameGuestRemoveCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    remove_count: int = Field(ge=1)


class GameGuestRemoveRead(BaseModel):
    status: str
    message: str
    removed_count: int
    booking_id: UUID | None = None


class GameCancelCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    cancel_reason: str | None = Field(default=None, max_length=MAX_CANCEL_REASON_LENGTH)
