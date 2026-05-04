from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


# PolicyDocumentCreate defines the fields allowed when creating a versioned
# legal/policy document for the app.
class PolicyDocumentCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    policy_type: str
    version: str
    title: str
    content_url: str | None = None
    content_text: str | None = None
    effective_at: datetime
    retired_at: datetime | None = None
    is_active: bool = True


# PolicyDocumentRead defines the policy document payload returned by the API.
class PolicyDocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    policy_type: str
    version: str
    title: str
    content_url: str | None
    content_text: str | None
    effective_at: datetime
    retired_at: datetime | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


# PolicyDocumentUpdate supports partial policy document updates, so every field
# is optional and only provided values should be applied by the route.
class PolicyDocumentUpdate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    policy_type: str | None = None
    version: str | None = None
    title: str | None = None
    content_url: str | None = None
    content_text: str | None = None
    effective_at: datetime | None = None
    retired_at: datetime | None = None
    is_active: bool | None = None