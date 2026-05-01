from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


# GameParticipantCreate defines the fields the client is allowed to send when
# creating a participant roster row. Server-managed timestamps remain outside
# the request body unless explicitly modeled here.
class GameParticipantCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    game_id: UUID
    booking_id: UUID | None = None
    participant_type: str
    user_id: UUID | None = None
    guest_name: str | None = None
    guest_email: str | None = None
    guest_phone: str | None = None
    display_name_snapshot: str
    participant_status: str = "pending_payment"
    attendance_status: str = "unknown"
    cancellation_type: str = "none"
    price_cents: int
    currency: str = "USD"
    roster_order: int | None = None
    joined_at: datetime | None = None
    confirmed_at: datetime | None = None
    cancelled_at: datetime | None = None
    checked_in_at: datetime | None = None
    marked_attendance_by_user_id: UUID | None = None
    attendance_decided_at: datetime | None = None
    attendance_notes: str | None = None


# GameParticipantRead defines the participant payload returned by the API.
# from_attributes lets Pydantic serialize directly from a SQLAlchemy model
# instance.
class GameParticipantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    game_id: UUID
    booking_id: UUID | None
    participant_type: str
    user_id: UUID | None
    guest_name: str | None
    guest_email: str | None
    guest_phone: str | None
    display_name_snapshot: str
    participant_status: str
    attendance_status: str
    cancellation_type: str
    price_cents: int
    currency: str
    roster_order: int | None
    joined_at: datetime
    confirmed_at: datetime | None
    cancelled_at: datetime | None
    checked_in_at: datetime | None
    marked_attendance_by_user_id: UUID | None
    attendance_decided_at: datetime | None
    attendance_notes: str | None
    created_at: datetime
    updated_at: datetime


# GameParticipantUpdate supports partial participant updates, so every field is
# optional and only provided values should be applied by the route.
class GameParticipantUpdate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    game_id: UUID | None = None
    booking_id: UUID | None = None
    participant_type: str | None = None
    user_id: UUID | None = None
    guest_name: str | None = None
    guest_email: str | None = None
    guest_phone: str | None = None
    display_name_snapshot: str | None = None
    participant_status: str | None = None
    attendance_status: str | None = None
    cancellation_type: str | None = None
    price_cents: int | None = None
    currency: str | None = None
    roster_order: int | None = None
    joined_at: datetime | None = None
    confirmed_at: datetime | None = None
    cancelled_at: datetime | None = None
    checked_in_at: datetime | None = None
    marked_attendance_by_user_id: UUID | None = None
    attendance_decided_at: datetime | None = None
    attendance_notes: str | None = None
