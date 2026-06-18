from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


class SubPostChatMessageCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    chat_id: UUID
    message_body: str


class SubPostChatMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    chat_id: UUID
    sender_user_id: UUID | None
    sender_display_name_snapshot: str
    sender_initials_snapshot: str
    sender_is_current_chat_member: bool = True
    sender_status_label: str | None = None
    message_type: str
    message_body: str
    moderation_status: str
    created_at: datetime
    updated_at: datetime
    edited_at: datetime | None
    deleted_at: datetime | None
    deleted_by_user_id: UUID | None


class SubPostChatMessageUpdate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    message_body: str | None = None
    moderation_status: str | None = None
