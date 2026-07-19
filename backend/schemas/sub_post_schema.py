from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.schemas.sub_post_position_schema import (
    SubPostPositionCreate,
    SubPostPositionRead,
)

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")
MAX_SUB_POST_TOTAL_SUBS = 11
MAX_SUB_POST_POSITION_ROWS = 6

FormatLabel = Literal[
    "3v3",
    "4v4",
    "5v5",
    "6v6",
    "7v7",
    "8v8",
    "9v9",
    "10v10",
    "11v11",
]
SkillLevel = Literal[
    "any",
    "beginner",
    "recreational",
    "intermediate",
    "advanced",
    "competitive",
]
GamePlayerGroup = Literal["men", "women", "coed"]
EnvironmentType = Literal["indoor", "outdoor"]
SportType = Literal["soccer"]
Currency = Literal["USD"]
CountryCode = Literal["US"]


class SubPostCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    sport_type: SportType = "soccer"
    format_label: FormatLabel
    environment_type: EnvironmentType
    skill_level: SkillLevel
    game_player_group: GamePlayerGroup
    team_name: str | None = Field(default=None, max_length=120)
    starts_at: datetime
    ends_at: datetime
    timezone: str = Field(default="America/Chicago", min_length=1, max_length=60)
    location_name: str = Field(min_length=1, max_length=150)
    address_line_1: str = Field(min_length=1, max_length=200)
    city: str = Field(min_length=1, max_length=100)
    state: str = Field(min_length=1, max_length=100)
    postal_code: str = Field(min_length=1, max_length=20)
    country_code: CountryCode = "US"
    neighborhood: str | None = Field(default=None, max_length=120)
    subs_needed: int = Field(ge=1, le=MAX_SUB_POST_TOTAL_SUBS)
    price_due_at_venue_cents: int = Field(default=0, ge=0)
    currency: Currency = "USD"
    payment_note: str | None = Field(default=None, max_length=500)
    notes: str | None = Field(default=None, max_length=500)
    positions: list[SubPostPositionCreate] = Field(
        min_length=1,
        max_length=MAX_SUB_POST_POSITION_ROWS,
    )

    @field_validator(
        "timezone",
        "location_name",
        "address_line_1",
        "city",
        "state",
        "postal_code",
        mode="before",
    )
    @classmethod
    def strip_required_strings(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator(
        "team_name",
        "neighborhood",
        "payment_note",
        "notes",
        mode="before",
    )
    @classmethod
    def strip_string_values(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class SubPostUpdate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    sport_type: SportType | None = None
    format_label: FormatLabel | None = None
    environment_type: EnvironmentType | None = None
    skill_level: SkillLevel | None = None
    game_player_group: GamePlayerGroup | None = None
    team_name: str | None = Field(default=None, max_length=120)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    timezone: str | None = Field(default=None, min_length=1, max_length=60)
    location_name: str | None = Field(default=None, min_length=1, max_length=150)
    address_line_1: str | None = Field(default=None, min_length=1, max_length=200)
    city: str | None = Field(default=None, min_length=1, max_length=100)
    state: str | None = Field(default=None, min_length=1, max_length=100)
    postal_code: str | None = Field(default=None, min_length=1, max_length=20)
    country_code: CountryCode | None = None
    neighborhood: str | None = Field(default=None, max_length=120)
    subs_needed: int | None = Field(default=None, ge=1, le=MAX_SUB_POST_TOTAL_SUBS)
    price_due_at_venue_cents: int | None = Field(default=None, ge=0)
    currency: Currency | None = None
    payment_note: str | None = Field(default=None, max_length=500)
    notes: str | None = Field(default=None, max_length=500)
    positions: list[SubPostPositionCreate] | None = Field(
        default=None,
        min_length=1,
        max_length=MAX_SUB_POST_POSITION_ROWS,
    )

    @field_validator(
        "timezone",
        "location_name",
        "address_line_1",
        "city",
        "state",
        "postal_code",
        mode="before",
    )
    @classmethod
    def strip_required_update_strings(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator(
        "team_name",
        "neighborhood",
        "payment_note",
        "notes",
        mode="before",
    )
    @classmethod
    def strip_string_values(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class SubPostCancel(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    cancel_reason: str | None = Field(default=None, max_length=500)

    @field_validator("cancel_reason", mode="before")
    @classmethod
    def strip_cancel_reason(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class SubPostRemove(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    remove_reason: str | None = Field(default=None, max_length=500)
    idempotency_key: str = Field(min_length=8, max_length=160)

    @field_validator("remove_reason", mode="before")
    @classmethod
    def strip_remove_reason(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class SubPostRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_user_id: UUID
    post_status: str
    public_visibility_status: str
    sport_type: str
    format_label: str
    environment_type: str
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


class SubPostPublicRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    post_status: str
    public_visibility_status: str
    sport_type: str
    format_label: str
    environment_type: str
    skill_level: str
    game_player_group: str
    starts_at: datetime
    ends_at: datetime
    timezone: str
    location_name: str
    city: str
    state: str
    neighborhood: str | None
    subs_needed: int
    price_due_at_venue_cents: int
    currency: str
    expires_at: datetime
    created_at: datetime
    updated_at: datetime
    positions: list[SubPostPositionRead] = Field(default_factory=list)
    pending_count: int = 0
    confirmed_count: int = 0
    sub_waitlist_count: int = 0


class SubPostListRead(BaseModel):
    posts: list[SubPostPublicRead] = Field(default_factory=list)
    next_cursor: str | None = None
    has_more: bool = False
    limit: int = 40
