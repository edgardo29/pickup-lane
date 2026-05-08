from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


# UserSettingsCreate defines the fields the client is allowed to send when
# creating a settings record for a user. Server-managed timestamps stay out of
# the request body.
class UserSettingsCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    user_id: UUID
    push_notifications_enabled: bool = False
    email_notifications_enabled: bool = False
    sms_notifications_enabled: bool = False
    marketing_opt_in: bool = False
    location_permission_status: str = "unknown"
    selected_city: str | None = None
    selected_state: str | None = None


# UserSettingsRead defines the settings payload returned by the API.
# from_attributes allows Pydantic to serialize directly from a SQLAlchemy model
# instance.
class UserSettingsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    push_notifications_enabled: bool
    email_notifications_enabled: bool
    sms_notifications_enabled: bool
    marketing_opt_in: bool
    location_permission_status: str
    selected_city: str | None
    selected_state: str | None
    created_at: datetime
    updated_at: datetime


# UserSettingsUpdate supports partial preference updates, so every field is
# optional and only provided values should be applied by the route.
class UserSettingsUpdate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    push_notifications_enabled: bool | None = None
    email_notifications_enabled: bool | None = None
    sms_notifications_enabled: bool | None = None
    marketing_opt_in: bool | None = None
    location_permission_status: str | None = None
    selected_city: str | None = None
    selected_state: str | None = None
