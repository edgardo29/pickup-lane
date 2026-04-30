from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# VenueCreate defines the fields the client is allowed to send when creating a
# venue record. Server-managed timestamps and moderation fields remain outside
# the request body unless explicitly supplied here.
class VenueCreate(BaseModel):
    name: str
    address_line_1: str
    city: str
    state: str
    postal_code: str
    country_code: str = "US"
    neighborhood: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    external_place_id: str | None = None
    venue_status: str = "pending_review"
    created_by_user_id: UUID | None = None
    approved_by_user_id: UUID | None = None
    approved_at: datetime | None = None
    is_active: bool = True


# VenueRead defines the venue payload returned by the API. from_attributes lets
# Pydantic serialize directly from a SQLAlchemy model instance.
class VenueRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    address_line_1: str
    city: str
    state: str
    postal_code: str
    country_code: str
    neighborhood: str | None
    latitude: Decimal | None
    longitude: Decimal | None
    external_place_id: str | None
    venue_status: str
    created_by_user_id: UUID | None
    approved_by_user_id: UUID | None
    approved_at: datetime | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


# VenueUpdate supports partial venue updates, so every field is optional and
# only provided values should be applied by the route.
class VenueUpdate(BaseModel):
    name: str | None = None
    address_line_1: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country_code: str | None = None
    neighborhood: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    external_place_id: str | None = None
    venue_status: str | None = None
    created_by_user_id: UUID | None = None
    approved_by_user_id: UUID | None = None
    approved_at: datetime | None = None
    is_active: bool | None = None
