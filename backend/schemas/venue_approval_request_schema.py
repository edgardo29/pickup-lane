from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


# VenueApprovalRequestCreate defines the fields allowed when a user submits a
# venue location for admin review.
class VenueApprovalRequestCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    submitted_by_user_id: UUID
    venue_id: UUID | None = None
    requested_name: str
    requested_address_line_1: str
    requested_city: str
    requested_state: str
    requested_postal_code: str
    requested_country_code: str = "US"
    request_status: str = "pending_review"
    reviewed_by_user_id: UUID | None = None
    reviewed_at: datetime | None = None
    review_notes: str | None = None


# VenueApprovalRequestRead defines the venue approval request payload returned
# by the API.
class VenueApprovalRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    submitted_by_user_id: UUID
    venue_id: UUID | None
    requested_name: str
    requested_address_line_1: str
    requested_city: str
    requested_state: str
    requested_postal_code: str
    requested_country_code: str
    request_status: str
    reviewed_by_user_id: UUID | None
    reviewed_at: datetime | None
    review_notes: str | None
    created_at: datetime
    updated_at: datetime


# VenueApprovalRequestUpdate supports partial admin review updates and metadata
# corrections, so every field is optional.
class VenueApprovalRequestUpdate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    venue_id: UUID | None = None
    requested_name: str | None = None
    requested_address_line_1: str | None = None
    requested_city: str | None = None
    requested_state: str | None = None
    requested_postal_code: str | None = None
    requested_country_code: str | None = None
    request_status: str | None = None
    reviewed_by_user_id: UUID | None = None
    reviewed_at: datetime | None = None
    review_notes: str | None = None