from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


class NotificationActionRead(BaseModel):
    key: str
    label: str
    path: str
    state: dict[str, str] | None = None


# NotificationCreate defines the fields allowed when creating a user inbox
# notification and optional links back to the related domain record.
class NotificationCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    user_id: UUID
    notification_type: str
    notification_category: str
    notification_domain: str
    source_type: str | None = None
    title: str
    subject_label: str | None = None
    summary: str | None = None
    body: str
    action_key: str | None = None
    subject_starts_at: datetime | None = None
    subject_ends_at: datetime | None = None
    subject_timezone: str | None = None
    event_at: datetime | None = None
    aggregation_key: str | None = None
    aggregate_count: int | None = None
    actor_user_id: UUID | None = None
    related_game_id: UUID | None = None
    related_chat_id: UUID | None = None
    related_booking_id: UUID | None = None
    related_payment_id: UUID | None = None
    related_refund_id: UUID | None = None
    related_participant_id: UUID | None = None
    related_message_id: UUID | None = None
    related_sub_post_id: UUID | None = None
    related_sub_post_request_id: UUID | None = None
    related_sub_post_position_id: UUID | None = None
    is_read: bool = False
    read_at: datetime | None = None


# NotificationRead defines the notification payload returned by the API.
class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    notification_type: str
    notification_category: str
    notification_domain: str
    source_type: str
    source_label: str
    title: str
    subject_label: str
    subject_starts_at: datetime | None
    subject_ends_at: datetime | None
    subject_timezone: str | None
    row_subject: str
    summary: str
    body: str
    action_key: str | None
    action: NotificationActionRead | None
    icon: str
    severity: str
    event_at: datetime
    aggregation_key: str | None
    aggregate_count: int | None
    actor_user_id: UUID | None
    related_game_id: UUID | None
    related_chat_id: UUID | None
    related_booking_id: UUID | None
    related_payment_id: UUID | None
    related_refund_id: UUID | None
    related_participant_id: UUID | None
    related_message_id: UUID | None
    related_sub_post_id: UUID | None
    related_sub_post_request_id: UUID | None
    related_sub_post_position_id: UUID | None
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
    notification_category: str | None = None
    notification_domain: str | None = None
    source_type: str | None = None
    title: str | None = None
    subject_label: str | None = None
    summary: str | None = None
    body: str | None = None
    action_key: str | None = None
    subject_starts_at: datetime | None = None
    subject_ends_at: datetime | None = None
    subject_timezone: str | None = None
    event_at: datetime | None = None
    aggregation_key: str | None = None
    aggregate_count: int | None = None
    actor_user_id: UUID | None = None
    related_game_id: UUID | None = None
    related_chat_id: UUID | None = None
    related_booking_id: UUID | None = None
    related_payment_id: UUID | None = None
    related_refund_id: UUID | None = None
    related_participant_id: UUID | None = None
    related_message_id: UUID | None = None
    related_sub_post_id: UUID | None = None
    related_sub_post_request_id: UUID | None = None
    related_sub_post_position_id: UUID | None = None
    is_read: bool | None = None
    read_at: datetime | None = None
