from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class GameChangeRemovalRequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    relief_choice: Literal["original_payment_method", "game_credit"]


class GameChangeRemovalRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    booking_id: UUID
    relief_choice: str
    request_status: str
    submitted_at: datetime


class GameDetailChangeRead(BaseModel):
    """One game detail that staff changed after the player booked."""

    field: str
    before: Any
    after: Any
    changed_at: datetime


class GameChangeReviewRead(BaseModel):
    """What changed since the player booked, and their request to leave, if any."""

    changes: list[GameDetailChangeRead]
    active_request: GameChangeRemovalRequestRead | None
    can_request_removal: bool
