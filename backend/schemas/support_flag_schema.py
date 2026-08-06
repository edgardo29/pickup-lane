from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")
SupportResolutionOutcome = Literal[
    "handled_externally",
    "retried_successfully",
    "no_action_needed",
    "duplicate",
    "invalid_flag",
]


class SupportFlagRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
    resolution_outcome: str | None
    resolution_reason: str | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class SupportFlagResolve(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    outcome: SupportResolutionOutcome
    reason: str = Field(min_length=1, max_length=1000)
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=160)
