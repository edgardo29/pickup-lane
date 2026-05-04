from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


# BookingPolicyAcceptanceCreate defines the fields allowed when recording that
# a booking accepted a specific policy document version.
class BookingPolicyAcceptanceCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    booking_id: UUID
    policy_document_id: UUID
    accepted_at: datetime | None = None


# BookingPolicyAcceptanceRead defines the booking policy acceptance payload
# returned by the API.
class BookingPolicyAcceptanceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    booking_id: UUID
    policy_document_id: UUID
    accepted_at: datetime
    created_at: datetime


# BookingPolicyAcceptanceUpdate supports partial correction of acceptance time.
class BookingPolicyAcceptanceUpdate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    accepted_at: datetime | None = None