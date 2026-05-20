from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


class SubPostPositionCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    position_label: Literal["field_player", "goalkeeper"]
    player_group: Literal["open", "men", "women"] = "open"
    spots_needed: int = Field(default=1, ge=1, le=11)
    sort_order: int = Field(default=0, ge=0)


class SubPostPositionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sub_post_id: UUID
    position_label: str
    player_group: str
    spots_needed: int
    sort_order: int
    pending_count: int = 0
    confirmed_count: int = 0
    sub_waitlist_count: int = 0
    created_at: datetime
    updated_at: datetime
