from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


class SubPostChatCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    sub_post_id: UUID
    chat_status: str = "active"
    closed_at: datetime | None = None


class SubPostChatEnsureCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    acting_user_id: UUID | None = None


class SubPostChatRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sub_post_id: UUID
    chat_status: str
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None
    unread_count: int = 0
    last_read_at: datetime | None = None


class SubPostChatUpdate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    sub_post_id: UUID | None = None
    chat_status: str | None = None
    closed_at: datetime | None = None
