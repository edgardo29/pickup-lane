from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


# BookingStatusHistoryCreate defines the fields allowed when recording booking
# or payment lifecycle audit rows.
class BookingStatusHistoryCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    booking_id: UUID
    old_booking_status: str | None = None
    new_booking_status: str
    old_payment_status: str | None = None
    new_payment_status: str | None = None
    changed_by_user_id: UUID | None = None
    change_source: str = "system"
    change_reason: str | None = None


# BookingStatusHistoryRead defines the booking status history payload returned
# by the API.
class BookingStatusHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    booking_id: UUID
    old_booking_status: str | None
    new_booking_status: str
    old_payment_status: str | None
    new_payment_status: str | None
    changed_by_user_id: UUID | None
    change_source: str
    change_reason: str | None
    created_at: datetime


# BookingStatusHistoryUpdate supports partial audit-row updates, so every field
# is optional and only provided values should be applied by the route.
class BookingStatusHistoryUpdate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    booking_id: UUID | None = None
    old_booking_status: str | None = None
    new_booking_status: str | None = None
    old_payment_status: str | None = None
    new_payment_status: str | None = None
    changed_by_user_id: UUID | None = None
    change_source: str | None = None
    change_reason: str | None = None
