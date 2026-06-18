from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


# AdminActionCreate defines the fields allowed when recording an admin/support
# audit action.
class AdminActionCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    action_type: str
    target_user_id: UUID | None = None
    target_game_id: UUID | None = None
    target_booking_id: UUID | None = None
    target_participant_id: UUID | None = None
    target_payment_id: UUID | None = None
    target_refund_id: UUID | None = None
    target_game_credit_id: UUID | None = None
    target_venue_id: UUID | None = None
    target_venue_image_id: UUID | None = None
    target_message_id: UUID | None = None
    target_sub_post_id: UUID | None = None
    target_sub_post_request_id: UUID | None = None
    target_sub_post_position_id: UUID | None = None
    target_sub_chat_message_id: UUID | None = None
    target_notification_id: UUID | None = None
    target_platform_notice_campaign_id: UUID | None = None
    target_admin_action_id: UUID | None = None
    reason: str | None = None
    metadata: dict[str, Any] | None = None
    idempotency_key: str | None = None


# AdminActionRead defines the admin action payload returned by the API.
class AdminActionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    admin_user_id: UUID
    action_type: str
    target_user_id: UUID | None
    target_game_id: UUID | None
    target_booking_id: UUID | None
    target_participant_id: UUID | None
    target_payment_id: UUID | None
    target_refund_id: UUID | None
    target_game_credit_id: UUID | None
    target_venue_id: UUID | None
    target_venue_image_id: UUID | None
    target_message_id: UUID | None
    target_sub_post_id: UUID | None
    target_sub_post_request_id: UUID | None
    target_sub_post_position_id: UUID | None
    target_sub_chat_message_id: UUID | None
    target_notification_id: UUID | None
    target_platform_notice_campaign_id: UUID | None
    target_admin_action_id: UUID | None
    reason: str | None
    metadata: dict[str, Any] | None = Field(
        validation_alias="metadata_",
        serialization_alias="metadata",
    )
    idempotency_key: str | None
    created_at: datetime


class AdminActionNoteCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    note: str
    idempotency_key: str | None = None
