from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SubPostStatusHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sub_post_id: UUID
    old_status: str | None
    new_status: str
    changed_by_user_id: UUID | None
    change_source: str
    change_reason: str | None
    created_at: datetime
