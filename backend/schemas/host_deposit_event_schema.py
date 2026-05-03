from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


# HostDepositEventCreate defines the fields allowed when recording host deposit
# status lifecycle audit rows.
class HostDepositEventCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    host_deposit_id: UUID
    old_status: str | None = None
    new_status: str
    changed_by_user_id: UUID | None = None
    change_source: str = "system"
    reason: str | None = None


# HostDepositEventRead defines the host deposit event payload returned by the API.
class HostDepositEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    host_deposit_id: UUID
    old_status: str | None
    new_status: str
    changed_by_user_id: UUID | None
    change_source: str
    reason: str | None
    created_at: datetime


# HostDepositEventUpdate supports partial audit-row updates, so every field is
# optional and only provided values should be applied by the route.
class HostDepositEventUpdate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    host_deposit_id: UUID | None = None
    old_status: str | None = None
    new_status: str | None = None
    changed_by_user_id: UUID | None = None
    change_source: str | None = None
    reason: str | None = None
