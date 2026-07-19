from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")
MAX_REVIEW_CASE_NOTE_BODY_LENGTH = 1000


class AdminReviewTargetFields(BaseModel):
    target_user_id: UUID | None = None
    target_game_id: UUID | None = None
    target_sub_post_id: UUID | None = None
    target_sub_post_request_id: UUID | None = None
    target_payment_id: UUID | None = None
    target_financial_outcome_id: UUID | None = None


class AdminReviewEvidenceMatchRead(BaseModel):
    rule_id: str
    evidence_type: str
    matched_text: str
    start: int
    end: int


class AdminReviewEvidenceItemRead(BaseModel):
    evidence_type: str
    display_text: str
    start: int
    end: int
    matches: list[AdminReviewEvidenceMatchRead] = Field(default_factory=list)
    truncated_before: bool = False
    truncated_after: bool = False
    additional_match_count: int = 0


class AdminContentModerationFindingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    review_case_id: UUID
    risk_area: str
    finding_type: str
    priority: str
    source_field: str
    source_content_hash: str
    evidence_fingerprint: str
    evidence: list[AdminReviewEvidenceItemRead]
    current_match: bool
    first_detected_at: datetime
    last_detected_at: datetime
    cleared_at: datetime | None
    scanner_version: str
    metadata: dict[str, Any] | None = Field(
        validation_alias="metadata_",
        serialization_alias="metadata",
    )
    created_at: datetime
    updated_at: datetime


class AdminReviewCaseClose(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    outcome: str
    reason: str
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=160)


class AdminReviewCaseNoteCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    body: str = Field(max_length=MAX_REVIEW_CASE_NOTE_BODY_LENGTH)
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=160)


class AdminReviewSignalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    review_case_id: UUID | None
    signal_category: str
    source: str
    signal_status: str
    priority: str
    title: str
    summary: str
    target_user_id: UUID | None
    target_game_id: UUID | None
    target_sub_post_id: UUID | None
    target_sub_post_request_id: UUID | None
    target_payment_id: UUID | None
    target_financial_outcome_id: UUID | None
    metadata: dict[str, Any] | None = Field(
        validation_alias="metadata_",
        serialization_alias="metadata",
    )
    idempotency_key: str | None
    created_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime


class AdminReviewCaseEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    review_case_id: UUID
    event_type: str
    actor_user_id: UUID | None
    admin_action_id: UUID | None
    signal_id: UUID | None
    content_moderation_finding_id: UUID | None
    note_id: UUID | None
    event_metadata: dict[str, Any] | None
    created_at: datetime


class AdminReviewCaseNoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    review_case_id: UUID
    author_user_id: UUID
    author_display_name: str | None = None
    body: str
    note_status: str
    edited_at: datetime | None
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AdminReviewCaseFindingSummaryRead(BaseModel):
    total_finding_count: int = 0
    current_finding_count: int = 0
    current_issue_type_count: int = 0
    current_issue_labels: list[str] = Field(default_factory=list)
    previous_issue_labels: list[str] = Field(default_factory=list)


class AdminReviewCaseTargetSummaryRead(BaseModel):
    label: str
    title: str
    subtitle: str | None = None
    status: str | None = None
    starts_at: datetime | None = None
    location: str | None = None


class AdminReviewCaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    case_type: str
    case_status: str
    case_category: str
    priority: str
    title: str
    summary: str
    target_user_id: UUID | None
    target_game_id: UUID | None
    target_sub_post_id: UUID | None
    target_sub_post_request_id: UUID | None
    target_payment_id: UUID | None
    target_financial_outcome_id: UUID | None
    opened_by_user_id: UUID | None
    closed_by_user_id: UUID | None
    closure_outcome: str | None
    closure_reason: str | None
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    finding_summary: AdminReviewCaseFindingSummaryRead = Field(
        default_factory=AdminReviewCaseFindingSummaryRead
    )
    target_summary: AdminReviewCaseTargetSummaryRead | None = None


class AdminReviewCaseDetailRead(AdminReviewCaseRead):
    signals: list[AdminReviewSignalRead] = Field(default_factory=list)
    findings: list[AdminContentModerationFindingRead] = Field(default_factory=list)
    events: list[AdminReviewCaseEventRead] = Field(default_factory=list)
    notes: list[AdminReviewCaseNoteRead] = Field(default_factory=list)


class AdminReviewCaseListRead(BaseModel):
    cases: list[AdminReviewCaseRead]
    total_count: int | None = None
    offset: int = 0
    limit: int
    next_cursor: str | None = None
    has_more: bool


class AdminReviewCaseNoteResultRead(BaseModel):
    review_case: AdminReviewCaseDetailRead
    note: AdminReviewCaseNoteRead
    audit_action_id: UUID
    idempotent_replay: bool


class AdminReviewCaseActionResultRead(BaseModel):
    review_case: AdminReviewCaseDetailRead
    audit_action_id: UUID
    idempotent_replay: bool
