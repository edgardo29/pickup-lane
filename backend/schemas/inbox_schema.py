from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from backend.schemas.notification_schema import NotificationActionRead


REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


class InboxItemRead(BaseModel):
    source_type: str
    source_id: UUID
    item_kind: str
    title: str
    message: str
    source_label: str
    subject_label: str
    row_subject: str
    summary: str
    occurred_at: datetime
    is_new: bool
    read_behavior: str
    read_at: datetime | None = None
    action: NotificationActionRead | None = None
    icon: str = "Bell"
    severity: str = "default"
    notification_type: str | None = None
    notification_category: str | None = None
    notification_domain: str | None = None
    original_notification_id: UUID | None = None


class InboxListRead(BaseModel):
    items: list[InboxItemRead]
    limit: int = 50
    next_cursor: str | None = None
    has_more: bool = False
    global_seen_token: str | None = None


class InboxCountsRead(BaseModel):
    app_updates_new_count: int = 0
    game_activity_unread_count: int = 0


class InboxGlobalSeenUpdate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    seen_token: str
