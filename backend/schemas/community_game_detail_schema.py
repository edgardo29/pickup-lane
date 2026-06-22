from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


class CommunityGameDetailCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    game_id: UUID
    payment_methods_snapshot: list[dict] = Field(default_factory=list)
    payment_instructions_snapshot: str | None = None


class CommunityGameDetailPublicRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    game_id: UUID
    payment_methods_snapshot: list[dict]
    payment_instructions_snapshot: str | None
    payment_text_moderation_status: str
    created_at: datetime
    updated_at: datetime


class CommunityGameDetailHostRead(CommunityGameDetailPublicRead):
    pass


class CommunityGameDetailStaffRead(CommunityGameDetailHostRead):
    payment_text_hidden_at: datetime | None
    payment_text_hidden_by_user_id: UUID | None
    payment_text_hidden_reason: str | None


class CommunityGameDetailUpdate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    game_id: UUID | None = None
    payment_methods_snapshot: list[dict] | None = None
    payment_instructions_snapshot: str | None = None


class CommunityGameDetailHostUpsert(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    payment_methods_snapshot: list[dict] = Field(default_factory=list)
    payment_instructions_snapshot: str | None = None
