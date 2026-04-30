from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


# UserCreate defines the fields the client is allowed to send when creating a
# user record. Server-managed fields like timestamps and defaults stay out of
# the request body.
class UserCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    auth_user_id: str
    email: str
    phone: str
    first_name: str
    last_name: str
    date_of_birth: date
    profile_photo_url: str | None = None
    home_city: str | None = None
    home_state: str | None = None
    stripe_customer_id: str | None = None


# UserRead defines the user shape returned by the API after reading or creating
# a record. from_attributes allows Pydantic to serialize directly from a
# SQLAlchemy model instance.
class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    auth_user_id: str
    role: str
    email: str
    phone: str
    first_name: str
    last_name: str
    date_of_birth: date
    profile_photo_url: str | None
    home_city: str | None
    home_state: str | None
    account_status: str
    hosting_status: str
    hosting_suspended_until: datetime | None
    stripe_customer_id: str | None
    member_since: datetime
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


# UserUpdate supports partial profile updates, so every field is optional and
# only provided values should be applied by the route.
class UserUpdate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    email: str | None = None
    phone: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    date_of_birth: date | None = None
    profile_photo_url: str | None = None
    home_city: str | None = None
    home_state: str | None = None
    stripe_customer_id: str | None = None
