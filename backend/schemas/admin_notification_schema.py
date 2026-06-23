from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from backend.schemas.notification_schema import NotificationRead


class AdminNotificationActionStateRead(BaseModel):
    action_key: str | None
    status: str
    path: str | None = None
    disabled_reason: str | None = None


class AdminNotificationAuditActionRead(BaseModel):
    id: UUID
    action_type: str
    admin_user_id: UUID
    created_at: datetime


class AdminNotificationDebugRead(NotificationRead):
    action_state: AdminNotificationActionStateRead
    audit_actions: list[AdminNotificationAuditActionRead] = Field(default_factory=list)
    audit_action_count: int = 0


class AdminNotificationDebugListRead(BaseModel):
    notifications: list[AdminNotificationDebugRead]
    total_count: int = 0
    offset: int = 0
    limit: int = 50
