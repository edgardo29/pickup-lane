from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from backend.schemas.game_schema import GameRead


class CommunityPublishAttemptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    host_user_id: UUID
    payment_id: UUID | None
    created_game_id: UUID | None
    attempt_status: str
    payment_method_id: UUID | None
    starts_on_local: date
    amount_cents: int
    currency: str
    failure_code: str | None
    failure_message: str | None
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CommunityPublishAttemptStatusRead(BaseModel):
    status: str
    attempt_id: UUID
    payment_id: UUID | None = None
    attempt_status: str
    payment_status: str | None = None
    stripe_status: str | None = None
    client_secret: str | None = None
    created_game_id: UUID | None = None
    game: GameRead | None = None
    error_message: str | None = None
