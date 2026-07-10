from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


class AdminChatDetectionRead(BaseModel):
    id: UUID
    category: str
    severity: str
    rule_key: str
    matched_preview: str | None = None
    created_at: datetime


class AdminChatSummaryRead(BaseModel):
    chat_id: UUID | None = None
    chat_status: str
    message_count: int = 0
    needs_review_count: int = 0
    removed_count: int = 0
    latest_message_id: UUID | None = None
    latest_message_preview: str | None = None
    latest_message_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    closed_at: datetime | None = None


class AdminChatMessageRead(BaseModel):
    id: UUID
    chat_id: UUID
    sender_user_id: UUID | None = None
    sender_display_name: str
    sender_initials: str
    message_type: str
    message_body: str
    visibility_status: str
    review_status: str
    created_at: datetime
    updated_at: datetime
    edited_at: datetime | None = None
    reviewed_at: datetime | None = None
    reviewed_by_user_id: UUID | None = None
    removed_at: datetime | None = None
    removed_by_user_id: UUID | None = None
    removed_source: str | None = None
    restored_at: datetime | None = None
    restored_by_user_id: UUID | None = None
    detections: list[AdminChatDetectionRead] = Field(default_factory=list)


class AdminChatMessageListRead(BaseModel):
    messages: list[AdminChatMessageRead] = Field(default_factory=list)
    total_count: int = 0
    offset: int = 0
    limit: int = 20


class AdminChatModerationActionCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    idempotency_key: str = Field(min_length=8, max_length=160)
    reason: str | None = Field(default=None, min_length=1, max_length=1000)


class AdminChatModerationActionResultRead(BaseModel):
    message: AdminChatMessageRead
    audit_action_id: UUID
    idempotent_replay: bool = False
