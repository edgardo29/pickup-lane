from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


class CommunityGameDetailCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    game_id: UUID
    payment_methods_snapshot: list[dict] = Field(default_factory=list)
    payment_instructions_snapshot: str | None = None


class CommunityGameDetailRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    game_id: UUID
    payment_methods_snapshot: list[dict]
    payment_instructions_snapshot: str | None
    created_at: datetime
    updated_at: datetime


class CommunityGameDetailUpdate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    game_id: UUID | None = None
    payment_methods_snapshot: list[dict] | None = None
    payment_instructions_snapshot: str | None = None
