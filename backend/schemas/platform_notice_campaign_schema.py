from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


class PlatformNoticeCampaignCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    internal_name: str = Field(min_length=1, max_length=160)
    title: str = Field(min_length=1, max_length=150)
    summary: str = Field(min_length=1, max_length=500)
    body: str = Field(min_length=1, max_length=4000)
    audience_type: str
    delivery_class: str
    target_user_ids: list[UUID] = Field(default_factory=list, max_length=500)
    idempotency_key: str = Field(min_length=8, max_length=160)


class PlatformNoticeCampaignUpdate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    internal_name: str | None = Field(default=None, min_length=1, max_length=160)
    title: str | None = Field(default=None, min_length=1, max_length=150)
    summary: str | None = Field(default=None, min_length=1, max_length=500)
    body: str | None = Field(default=None, min_length=1, max_length=4000)
    audience_type: str | None = None
    delivery_class: str | None = None
    target_user_ids: list[UUID] | None = Field(default=None, max_length=500)


class PlatformNoticeCampaignDeliverySummary(BaseModel):
    targeted_count: int = 0
    delivered_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0


class PlatformNoticeCampaignRead(BaseModel):
    id: UUID
    campaign_status: str
    audience_type: str
    delivery_class: str
    internal_name: str
    title: str
    summary: str
    body: str
    target_user_ids: list[UUID] = Field(default_factory=list)
    target_user_count: int = 0
    delivery_summary: PlatformNoticeCampaignDeliverySummary = Field(
        default_factory=PlatformNoticeCampaignDeliverySummary
    )
    created_by_user_id: UUID | None
    updated_by_user_id: UUID | None
    first_sent_at: datetime | None
    completed_at: datetime | None
    last_attempt_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PlatformNoticeCampaignListRead(BaseModel):
    campaigns: list[PlatformNoticeCampaignRead]
    total_count: int = 0
    offset: int = 0
    limit: int = 50


class PlatformNoticeCampaignDeliveryRequest(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    idempotency_key: str = Field(min_length=8, max_length=160)


class PlatformNoticeCampaignDeliveryRead(BaseModel):
    id: UUID
    campaign_id: UUID
    recipient_user_id: UUID | None
    recipient_user_id_snapshot: UUID
    delivery_status: str
    skip_reason: str | None
    failure_code: str | None
    notification_id: UUID | None
    attempt_count: int
    last_attempt_at: datetime | None
    delivered_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PlatformNoticeCampaignDeliveryListRead(BaseModel):
    deliveries: list[PlatformNoticeCampaignDeliveryRead]
    total_count: int = 0
    offset: int = 0
    limit: int = 50


class PlatformNoticeCampaignAttemptRead(BaseModel):
    id: UUID
    campaign_id: UUID
    attempt_type: str
    attempt_status: str
    idempotency_key: str
    targeted_count: int
    delivered_count: int
    skipped_count: int
    failed_count: int
    created_by_user_id: UUID | None
    started_at: datetime
    completed_at: datetime | None
    created_at: datetime


class PlatformNoticeCampaignAttemptListRead(BaseModel):
    attempts: list[PlatformNoticeCampaignAttemptRead]
    total_count: int = 0
    offset: int = 0
    limit: int = 50


class PlatformNoticeCampaignDeliveryResult(BaseModel):
    campaign: PlatformNoticeCampaignRead
    attempt: PlatformNoticeCampaignAttemptRead
