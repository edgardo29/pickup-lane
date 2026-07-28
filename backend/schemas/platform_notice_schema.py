from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


class PlatformNoticeCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    idempotency_key: str = Field(min_length=8, max_length=160)
    title: str = Field(min_length=1, max_length=150)
    message: str = Field(min_length=1, max_length=4000)
    audience_type: str
    selected_user_ids: list[UUID] = Field(default_factory=list)


class PlatformNoticeCancel(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    cancellation_reason: str = Field(min_length=1, max_length=1000)


class PlatformNoticeAdminSummaryRead(BaseModel):
    id: UUID
    display_name: str
    email: str | None = None


class PlatformNoticeRead(BaseModel):
    id: UUID
    title: str
    message: str
    audience_type: str
    status: str
    selected_recipient_count: int = 0
    global_sequence: int | None = None
    published_at: datetime
    created_at: datetime
    updated_at: datetime
    created_by_admin_id: UUID | None = None
    created_by_admin: PlatformNoticeAdminSummaryRead | None = None
    cancelled_at: datetime | None = None
    cancelled_by_admin_id: UUID | None = None
    cancelled_by_admin: PlatformNoticeAdminSummaryRead | None = None
    cancellation_reason: str | None = None


class PlatformNoticeCreateResultRead(BaseModel):
    notice: PlatformNoticeRead
    idempotent_replay: bool = False


class PlatformNoticeListRead(BaseModel):
    notices: list[PlatformNoticeRead]
    limit: int = 30
    next_cursor: str | None = None
    has_more: bool = False


class PlatformNoticeRecipientRead(BaseModel):
    user_id: UUID
    display_name: str
    email: str | None = None
    account_status: str
    currently_eligible: bool
    read_at: datetime | None = None
    created_at: datetime


class PlatformNoticeRecipientListRead(BaseModel):
    recipients: list[PlatformNoticeRecipientRead]
    limit: int = 50
    next_cursor: str | None = None
    has_more: bool = False
