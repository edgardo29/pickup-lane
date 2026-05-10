from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.schemas.sub_post_position_schema import (
    SubPostPositionCreate,
    SubPostPositionRead,
)

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


class SubPostCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    sport_type: str = "soccer"
    format_label: str
    skill_level: str
    game_player_group: str
    team_name: str | None = None
    starts_at: datetime
    ends_at: datetime
    timezone: str = "America/Chicago"
    location_name: str
    address_line_1: str
    city: str
    state: str
    postal_code: str
    country_code: str = "US"
    neighborhood: str | None = None
    subs_needed: int
    price_due_at_venue_cents: int = 0
    currency: str = "USD"
    payment_note: str | None = None
    notes: str | None = None
    positions: list[SubPostPositionCreate]


class SubPostUpdate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    sport_type: str | None = None
    format_label: str | None = None
    skill_level: str | None = None
    game_player_group: str | None = None
    team_name: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    timezone: str | None = None
    location_name: str | None = None
    address_line_1: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country_code: str | None = None
    neighborhood: str | None = None
    subs_needed: int | None = None
    price_due_at_venue_cents: int | None = None
    currency: str | None = None
    payment_note: str | None = None
    notes: str | None = None
    positions: list[SubPostPositionCreate] | None = None


class SubPostCancel(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    cancel_reason: str | None = None


class SubPostRemove(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    remove_reason: str | None = None


class SubPostRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_user_id: UUID
    post_status: str
    sport_type: str
    format_label: str
    skill_level: str
    game_player_group: str
    team_name: str | None
    starts_at: datetime
    ends_at: datetime
    timezone: str
    location_name: str
    address_line_1: str
    city: str
    state: str
    postal_code: str
    country_code: str
    neighborhood: str | None
    subs_needed: int
    price_due_at_venue_cents: int
    currency: str
    payment_note: str | None
    notes: str | None
    expires_at: datetime
    filled_at: datetime | None
    canceled_at: datetime | None
    canceled_by_user_id: UUID | None
    cancel_reason: str | None
    removed_at: datetime | None
    removed_by_user_id: UUID | None
    remove_reason: str | None
    created_at: datetime
    updated_at: datetime
    positions: list[SubPostPositionRead] = Field(default_factory=list)
    pending_count: int = 0
    confirmed_count: int = 0
    sub_waitlist_count: int = 0
