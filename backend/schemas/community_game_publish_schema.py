from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.schemas.game_schema import GameRead

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


class CommunityGameVenuePayload(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    name: str
    address_line_1: str
    city: str
    state: str
    postal_code: str
    country_code: str = "US"
    neighborhood: str | None = None


class CommunityGamePublishCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    starts_at: datetime
    ends_at: datetime
    timezone: str = "America/Chicago"
    format_label: str
    game_player_group: str = "coed"
    skill_level: str = "any"
    environment_type: str
    total_spots: int
    price_per_player_cents: int
    venue: CommunityGameVenuePayload
    payment_methods_snapshot: list[dict] = Field(default_factory=list)
    payment_instructions_snapshot: str | None = None
    custom_rules_text: str | None = None
    game_notes: str | None = None
    parking_notes: str | None = None
    payment_method_id: UUID | None = None


class CommunityGamePublishRead(BaseModel):
    status: str
    game: GameRead | None = None
    attempt_id: UUID | None = None
    payment_id: UUID | None = None
    attempt_status: str | None = None
    payment_status: str | None = None
    stripe_status: str | None = None
    client_secret: str | None = None
    created_game_id: UUID | None = None
    error_message: str | None = None
