from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


# PolicyAcceptanceCreate defines the fields allowed when recording that a user
# accepted a specific policy document version.
class PolicyAcceptanceCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    user_id: UUID
    policy_document_id: UUID
    accepted_at: datetime | None = None
    ip_address: str | None = None
    user_agent: str | None = None


# PolicyAcceptanceRead defines the policy acceptance payload returned by the API.
class PolicyAcceptanceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    policy_document_id: UUID
    accepted_at: datetime
    ip_address: str | None
    user_agent: str | None
    created_at: datetime


# PolicyAcceptanceUpdate supports partial correction of acceptance metadata.
class PolicyAcceptanceUpdate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    accepted_at: datetime | None = None
    ip_address: str | None = None
    user_agent: str | None = None