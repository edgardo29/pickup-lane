from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


# NotificationCreate defines the fields allowed when creating a user inbox
# notification and optional links back to the related domain record.
class NotificationCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    user_id: UUID
    notification_type: str
    title: str
    body: str
    related_game_id: UUID | None = None
    related_chat_id: UUID | None = None
    related_booking_id: UUID | None = None
    related_participant_id: UUID | None = None
    related_message_id: UUID | None = None
    is_read: bool = False
    read_at: datetime | None = None


# NotificationRead defines the notification payload returned by the API.
class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    notification_type: str
    title: str
    body: str
    related_game_id: UUID | None
    related_chat_id: UUID | None
    related_booking_id: UUID | None
    related_participant_id: UUID | None
    related_message_id: UUID | None
    is_read: bool
    read_at: datetime | None
    created_at: datetime
    updated_at: datetime


# NotificationUpdate supports partial notification updates, so every field is
# optional and only provided values should be applied by the route.
class NotificationUpdate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    user_id: UUID | None = None
    notification_type: str | None = None
    title: str | None = None
    body: str | None = None
    related_game_id: UUID | None = None
    related_chat_id: UUID | None = None
    related_booking_id: UUID | None = None
    related_participant_id: UUID | None = None
    related_message_id: UUID | None = None
    is_read: bool | None = None
    read_at: datetime | None = None
