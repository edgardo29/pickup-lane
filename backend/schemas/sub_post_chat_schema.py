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


class SubPostChatRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sub_post_id: UUID
    chat_status: str
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None
    message_count: int = 0
    needs_review_count: int = 0
    removed_count: int = 0
    latest_message_id: UUID | None = None
    latest_message_preview: str | None = None
    latest_message_at: datetime | None = None
    unread_count: int = 0
    last_read_at: datetime | None = None


class SubPostChatUpdate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    sub_post_id: UUID | None = None
    chat_status: str | None = None
    closed_at: datetime | None = None
