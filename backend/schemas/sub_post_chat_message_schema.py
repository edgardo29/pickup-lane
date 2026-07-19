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
    visibility_status: str
    review_status: str
    created_at: datetime
    updated_at: datetime
    reviewed_at: datetime | None = None
    reviewed_by_user_id: UUID | None = None
    removed_at: datetime | None = None
    removed_by_user_id: UUID | None = None
    removed_source: str | None = None
    restored_at: datetime | None = None
    restored_by_user_id: UUID | None = None
