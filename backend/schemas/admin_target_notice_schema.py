from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AdminTargetNoticeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    recipient_user_id: UUID | None = None
    target_user_id: UUID | None = None
    target_game_id: UUID | None = None
    target_sub_post_id: UUID | None = None
    target_sub_post_request_id: UUID | None = None
    admin_action_id: UUID | None = None
    notice_type: str
    notice_status: str
    title: str
    body: str
    user_safe_reason: str | None = None
    notice_metadata: dict | None = None
    created_by_user_id: UUID | None = None
    read_at: datetime | None = None
    dismissed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
