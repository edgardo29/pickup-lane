from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


# ChatMessageCreate defines the fields allowed when creating a message inside
# a game chat room.
class ChatMessageCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    chat_id: UUID
    sender_user_id: UUID | None = None
    message_type: str = "text"
    message_body: str
    is_pinned: bool = False
    pinned_at: datetime | None = None
    pinned_by_user_id: UUID | None = None
    moderation_status: str = "visible"
    edited_at: datetime | None = None
    deleted_at: datetime | None = None
    deleted_by_user_id: UUID | None = None


# ChatMessageRead defines the chat message payload returned by the API.
class ChatMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    chat_id: UUID
    sender_user_id: UUID | None
    message_type: str
    message_body: str
    is_pinned: bool
    pinned_at: datetime | None
    pinned_by_user_id: UUID | None
    moderation_status: str
    created_at: datetime
    updated_at: datetime
    edited_at: datetime | None
    deleted_at: datetime | None
    deleted_by_user_id: UUID | None


# ChatMessageUpdate supports partial message updates, so every field is optional
# and only provided values should be applied by the route.
class ChatMessageUpdate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    chat_id: UUID | None = None
    sender_user_id: UUID | None = None
    message_type: str | None = None
    message_body: str | None = None
    is_pinned: bool | None = None
    pinned_at: datetime | None = None
    pinned_by_user_id: UUID | None = None
    moderation_status: str | None = None
    edited_at: datetime | None = None
    deleted_at: datetime | None = None
    deleted_by_user_id: UUID | None = None
