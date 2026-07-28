from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from backend.schemas.notification_schema import NotificationRead


class AdminNotificationAuditActionRead(BaseModel):
    id: UUID
    action_type: str
    admin_user_id: UUID
    created_at: datetime


class AdminNotificationRecipientRead(BaseModel):
    user_id: UUID
    display_name: str
    email: str | None = None
    account_status: str | None = None


class AdminNotificationRelatedRecordRead(BaseModel):
    type: str
    id: UUID
    display_label: str
    exists: bool | None = None


class AdminNotificationCompactRelatedRecordRead(BaseModel):
    type: str
    id: UUID
    display_label: str


class AdminNotificationActionStateRead(BaseModel):
    action_key: str | None
    status: str
    path: str | None = None
    disabled_reason: str | None = None
    reason_code: str | None = None
    explanation: str | None = None
    evaluated_at: datetime | None = None
    target_record: AdminNotificationRelatedRecordRead | None = None


class AdminNotificationLookupItemRead(BaseModel):
    id: UUID
    user_id: UUID
    recipient: AdminNotificationRecipientRead | None = None
    title: str
    subject_label: str | None = None
    row_subject: str | None = None
    notification_type: str
    notification_category: str
    notification_domain: str
    source_type: str
    source_label: str
    icon: str
    severity: str
    event_at: datetime
    created_at: datetime
    is_read: bool
    read_at: datetime | None
    primary_related_record: AdminNotificationCompactRelatedRecordRead | None = None


class AdminNotificationLookupDetailRead(NotificationRead):
    action_state: AdminNotificationActionStateRead
    related_records: list[AdminNotificationRelatedRecordRead] = Field(
        default_factory=list
    )
    audit_actions: list[AdminNotificationAuditActionRead] = Field(default_factory=list)
    audit_action_count: int = 0


class AdminNotificationLookupListRead(BaseModel):
    notifications: list[AdminNotificationLookupItemRead]
    limit: int = 50
    next_cursor: str | None = None
    has_more: bool = False
