from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


# WaitlistEntryCreate defines the fields the client is allowed to send when
# creating a waitlist entry. Server-managed timestamps stay out of the request.
class WaitlistEntryCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    game_id: UUID
    user_id: UUID
    party_size: int = 1
    position: int
    waitlist_status: str = "active"
    promoted_booking_id: UUID | None = None
    promotion_expires_at: datetime | None = None
    joined_at: datetime | None = None
    promoted_at: datetime | None = None
    cancelled_at: datetime | None = None
    expired_at: datetime | None = None


# WaitlistEntryRead defines the waitlist entry payload returned by the API.
# from_attributes lets Pydantic serialize directly from a SQLAlchemy model
# instance.
class WaitlistEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    game_id: UUID
    user_id: UUID
    party_size: int
    position: int
    waitlist_status: str
    promoted_booking_id: UUID | None
    promotion_expires_at: datetime | None
    joined_at: datetime
    promoted_at: datetime | None
    cancelled_at: datetime | None
    expired_at: datetime | None
    created_at: datetime
    updated_at: datetime


# WaitlistEntryUpdate supports partial waitlist updates, so every field is
# optional and only provided values should be applied by the route.
class WaitlistEntryUpdate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    game_id: UUID | None = None
    user_id: UUID | None = None
    party_size: int | None = None
    position: int | None = None
    waitlist_status: str | None = None
    promoted_booking_id: UUID | None = None
    promotion_expires_at: datetime | None = None
    joined_at: datetime | None = None
    promoted_at: datetime | None = None
    cancelled_at: datetime | None = None
    expired_at: datetime | None = None
