from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


# AdminActionCreate defines the fields allowed when recording an admin/support
# audit action.
class AdminActionCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    admin_user_id: UUID
    action_type: str
    target_user_id: UUID | None = None
    target_game_id: UUID | None = None
    target_booking_id: UUID | None = None
    target_participant_id: UUID | None = None
    target_payment_id: UUID | None = None
    target_venue_id: UUID | None = None
    target_message_id: UUID | None = None
    target_host_deposit_id: UUID | None = None
    reason: str | None = None
    metadata: dict[str, Any] | None = None


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
    target_venue_id: UUID | None
    target_message_id: UUID | None
    target_host_deposit_id: UUID | None
    reason: str | None
    metadata: dict[str, Any] | None = Field(
        validation_alias="metadata_",
        serialization_alias="metadata",
    )
    created_at: datetime


# AdminActionUpdate supports partial audit-row updates, so every field is
# optional and only provided values should be applied by the route.
class AdminActionUpdate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    admin_user_id: UUID | None = None
    action_type: str | None = None
    target_user_id: UUID | None = None
    target_game_id: UUID | None = None
    target_booking_id: UUID | None = None
    target_participant_id: UUID | None = None
    target_payment_id: UUID | None = None
    target_venue_id: UUID | None = None
    target_message_id: UUID | None = None
    target_host_deposit_id: UUID | None = None
    reason: str | None = None
    metadata: dict[str, Any] | None = None