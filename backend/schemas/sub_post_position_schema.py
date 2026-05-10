from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


class SubPostPositionCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    position_label: str
    player_group: str = "open"
    spots_needed: int = 1
    sort_order: int = 0


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
