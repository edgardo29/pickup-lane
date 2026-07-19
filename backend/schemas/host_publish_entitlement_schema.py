from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class HostPublishEntitlementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    host_user_id: UUID
    entitlement_type: str
    status: str
    source: str
    source_admin_action_id: UUID | None
    source_financial_outcome_id: UUID | None
    reserved_by_attempt_id: UUID | None
    used_by_game_id: UUID | None
    used_by_host_publish_fee_id: UUID | None
    used_at: datetime | None
    revoked_at: datetime | None
    revoked_by_user_id: UUID | None
    revoke_reason: str | None
    created_at: datetime
    updated_at: datetime
