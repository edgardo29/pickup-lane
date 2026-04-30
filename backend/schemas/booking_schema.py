from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


# BookingCreate defines the fields the client is allowed to send when creating
# a booking record. Server-managed timestamps remain outside the request body.
class BookingCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    game_id: UUID
    buyer_user_id: UUID
    booking_status: str = "pending_payment"
    payment_status: str = "unpaid"
    participant_count: int
    subtotal_cents: int
    platform_fee_cents: int = 0
    discount_cents: int = 0
    total_cents: int
    currency: str = "USD"
    price_per_player_snapshot_cents: int
    platform_fee_snapshot_cents: int = 0
    booked_at: datetime | None = None
    cancelled_at: datetime | None = None
    cancelled_by_user_id: UUID | None = None
    cancel_reason: str | None = None
    expires_at: datetime | None = None


# BookingRead defines the booking payload returned by the API.
# from_attributes lets Pydantic serialize directly from a SQLAlchemy model
# instance.
class BookingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    game_id: UUID
    buyer_user_id: UUID
    booking_status: str
    payment_status: str
    participant_count: int
    subtotal_cents: int
    platform_fee_cents: int
    discount_cents: int
    total_cents: int
    currency: str
    price_per_player_snapshot_cents: int
    platform_fee_snapshot_cents: int
    booked_at: datetime | None
    cancelled_at: datetime | None
    cancelled_by_user_id: UUID | None
    cancel_reason: str | None
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime


# BookingUpdate supports partial booking updates, so every field is optional
# and only provided values should be applied by the route.
class BookingUpdate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    game_id: UUID | None = None
    buyer_user_id: UUID | None = None
    booking_status: str | None = None
    payment_status: str | None = None
    participant_count: int | None = None
    subtotal_cents: int | None = None
    platform_fee_cents: int | None = None
    discount_cents: int | None = None
    total_cents: int | None = None
    currency: str | None = None
    price_per_player_snapshot_cents: int | None = None
    platform_fee_snapshot_cents: int | None = None
    booked_at: datetime | None = None
    cancelled_at: datetime | None = None
    cancelled_by_user_id: UUID | None = None
    cancel_reason: str | None = None
    expires_at: datetime | None = None
