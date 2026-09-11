from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


class AdminChatDetectionRead(BaseModel):
    category: str
    severity: str


class AdminChatSummaryRead(BaseModel):
    chat_status: str
    message_count: int = 0
    needs_review_count: int = 0
    removed_count: int = 0


class AdminChatMessageRead(BaseModel):
    id: UUID
    sender_display_name: str
    message_excerpt: str
    visibility_status: str
    review_status: str
    created_at: datetime
    removed_source: str | None = None
    detections: list[AdminChatDetectionRead] = Field(default_factory=list)


class AdminChatMessageContentRead(BaseModel):
    id: UUID
    message_body: str


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
    message_id: UUID
    audit_action_id: UUID
    idempotent_replay: bool = False
