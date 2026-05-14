from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


# GameCreate defines the fields the client is allowed to send when creating a
# game record. Server-managed timestamps remain outside the request body.
class GameCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    game_type: str
    payment_collection_type: str
    publish_status: str = "draft"
    game_status: str = "scheduled"
    title: str
    description: str | None = None
    venue_id: UUID
    venue_name_snapshot: str
    address_snapshot: str
    city_snapshot: str
    state_snapshot: str
    neighborhood_snapshot: str | None = None
    host_user_id: UUID | None = None
    created_by_user_id: UUID
    starts_at: datetime
    ends_at: datetime
    timezone: str = "America/Chicago"
    sport_type: str = "soccer"
    format_label: str
    environment_type: str
    total_spots: int
    price_per_player_cents: int
    currency: str = "USD"
    minimum_age: int | None = None
    allow_guests: bool = True
    max_guests_per_booking: int = 2
    waitlist_enabled: bool = True
    is_chat_enabled: bool = True
    policy_mode: str
    custom_rules_text: str | None = None
    custom_cancellation_text: str | None = None
    game_notes: str | None = None
    parking_notes: str | None = None
    published_at: datetime | None = None
    cancelled_at: datetime | None = None
    cancelled_by_user_id: UUID | None = None
    cancel_reason: str | None = None
    completed_at: datetime | None = None
    completed_by_user_id: UUID | None = None


# GameRead defines the game payload returned by the API. from_attributes lets
# Pydantic serialize directly from a SQLAlchemy model instance.
class GameRead(BaseModel):
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
    host_user_id: UUID | None
    created_by_user_id: UUID
    starts_at: datetime
    ends_at: datetime
    timezone: str
    sport_type: str
    format_label: str
    environment_type: str
    total_spots: int
    price_per_player_cents: int
    currency: str
    minimum_age: int | None
    allow_guests: bool
    max_guests_per_booking: int
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
    cancel_reason: str | None
    completed_at: datetime | None
    completed_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


# GameUpdate supports partial game updates, so every field is optional and only
# provided values should be applied by the route.
class GameUpdate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    game_type: str | None = None
    payment_collection_type: str | None = None
    publish_status: str | None = None
    game_status: str | None = None
    title: str | None = None
    description: str | None = None
    venue_id: UUID | None = None
    venue_name_snapshot: str | None = None
    address_snapshot: str | None = None
    city_snapshot: str | None = None
    state_snapshot: str | None = None
    neighborhood_snapshot: str | None = None
    host_user_id: UUID | None = None
    created_by_user_id: UUID | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    timezone: str | None = None
    sport_type: str | None = None
    format_label: str | None = None
    environment_type: str | None = None
    total_spots: int | None = None
    price_per_player_cents: int | None = None
    currency: str | None = None
    minimum_age: int | None = None
    allow_guests: bool | None = None
    max_guests_per_booking: int | None = None
    waitlist_enabled: bool | None = None
    is_chat_enabled: bool | None = None
    policy_mode: str | None = None
    custom_rules_text: str | None = None
    custom_cancellation_text: str | None = None
    game_notes: str | None = None
    parking_notes: str | None = None
    published_at: datetime | None = None
    cancelled_at: datetime | None = None
    cancelled_by_user_id: UUID | None = None
    cancel_reason: str | None = None
    completed_at: datetime | None = None
    completed_by_user_id: UUID | None = None


# GameHostEdit is the safer host-facing edit contract. It intentionally exposes
# only fields a community host should be able to change from the app flow.
class GameHostEdit(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    acting_user_id: UUID
    venue_name: str | None = None
    address_line_1: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    neighborhood: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    format_label: str | None = None
    environment_type: str | None = None
    total_spots: int | None = None
    price_per_player_cents: int | None = None
    game_notes: str | None = None
    parking_notes: str | None = None


class GameJoinCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    acting_user_id: UUID
    guest_count: int = 0


class GameJoinRead(BaseModel):
    status: str
    message: str
    participant_id: UUID | None = None
    booking_id: UUID | None = None
    waitlist_entry_id: UUID | None = None


class GameLeaveCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    acting_user_id: UUID


class GameLeaveRead(BaseModel):
    status: str
    message: str
    refund_eligible: bool
    participant_id: UUID
    booking_id: UUID | None = None


class GameGuestAddCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    acting_user_id: UUID
    guest_count: int = 1


class GameGuestAddRead(BaseModel):
    status: str
    message: str
    added_count: int


class GameGuestRemoveCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    acting_user_id: UUID
    remove_count: int


class GameGuestRemoveRead(BaseModel):
    status: str
    message: str
    removed_count: int
    booking_id: UUID | None = None
