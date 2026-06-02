from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.schemas.game_schema import GameRead

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


class AdminOfficialGameRead(BaseModel):
    game: GameRead


class AdminOfficialGameListRead(BaseModel):
    games: list[GameRead] = Field(default_factory=list)
