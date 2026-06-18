from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


class SupportFlagRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    flag_type: str
    flag_status: str
    severity: str
    source: str
    title: str
    summary: str
    target_user_id: UUID | None
    target_game_id: UUID | None
    target_booking_id: UUID | None
    target_payment_id: UUID | None
    target_refund_id: UUID | None
    target_game_credit_id: UUID | None
    target_venue_id: UUID | None
    target_venue_image_id: UUID | None
    target_notification_id: UUID | None
    metadata: dict[str, Any] | None = Field(
        validation_alias="metadata_",
        serialization_alias="metadata",
    )
    idempotency_key: str | None
    source_admin_action_id: UUID | None
    created_by_user_id: UUID | None
    resolved_by_user_id: UUID | None
    resolution_outcome: str | None
    resolution_reason: str | None
    resolution_admin_action_id: UUID | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class SupportFlagResolve(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    outcome: str
    reason: str
