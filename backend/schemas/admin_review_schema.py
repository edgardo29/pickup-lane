from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")
MAX_REVIEW_CASE_NOTE_BODY_LENGTH = 1000
AdminReviewClosureOutcome = Literal[
    "enforcement_applied",
    "no_action_needed",
    "invalid_signal",
]
AdminReviewAssignmentMode = Literal["all", "mine", "unassigned"]
AdminReviewExpectedVersion = Annotated[int, Field(strict=True, ge=1)]


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

    outcome: AdminReviewClosureOutcome
    reason: str = Field(min_length=1, max_length=1000)
    expected_case_version: AdminReviewExpectedVersion
    idempotency_key: str = Field(min_length=8, max_length=160)


class AdminReviewCaseNoteCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    body: str = Field(min_length=1, max_length=MAX_REVIEW_CASE_NOTE_BODY_LENGTH)
    corrects_note_id: UUID | None = None
    expected_case_version: AdminReviewExpectedVersion
    idempotency_key: str = Field(min_length=8, max_length=160)


class AdminReviewCaseAssignment(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    assignee_user_id: UUID | None = None
    reason: str = Field(min_length=1, max_length=1000)
    expected_case_version: AdminReviewExpectedVersion
    idempotency_key: str = Field(min_length=8, max_length=160)


class AdminReviewCaseReopen(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    reason: str = Field(min_length=1, max_length=1000)
    expected_case_version: AdminReviewExpectedVersion
    idempotency_key: str = Field(min_length=8, max_length=160)


class AdminReviewCaseMerge(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    destination_case_id: UUID
    reason: str = Field(min_length=1, max_length=1000)
    expected_source_version: AdminReviewExpectedVersion
    expected_destination_version: AdminReviewExpectedVersion
    idempotency_key: str = Field(min_length=8, max_length=160)


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
    event_sequence: int
    case_version: int
    actor_kind: str
    actor_user_id: UUID | None
    admin_action_id: UUID | None
    signal_id: UUID | None
    content_moderation_finding_id: UUID | None
    note_id: UUID | None
    related_case_id: UUID | None
    related_event_id: UUID | None
    automation_rule_id: str | None
    automation_rule_version: str | None
    trigger_actor_user_id: UUID | None
    event_metadata: dict[str, Any] | None
    created_at: datetime


class AdminReviewCaseNoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    review_case_id: UUID
    author_user_id: UUID
    author_display_name: str | None = None
    body: str
    corrects_note_id: UUID | None
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
    case_version: int
    creation_reason: str
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
    closure_mode: str | None
    closure_rule_id: str | None
    closure_rule_version: str | None
    assigned_to_user_id: UUID | None
    assigned_at: datetime | None
    assignee_display_name: str | None = None
    assignee_is_eligible: bool | None = None
    merged_into_case_id: UUID | None
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
    linked_cases: list["AdminReviewLinkedCaseRead"] = Field(default_factory=list)
    resolution_references: list["AdminReviewResolutionReferenceRead"] = Field(
        default_factory=list
    )
    resolution_history: list["AdminReviewResolutionHistoryRead"] = Field(
        default_factory=list
    )


class AdminReviewLinkedCaseRead(BaseModel):
    id: UUID
    case_status: str
    case_version: int
    priority: str
    relation: Literal["merged_into", "merged_from"]


class AdminReviewResolutionReferenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    closure_event_id: UUID
    reference_type: str
    content_moderation_finding_id: UUID | None
    signal_id: UUID | None
    admin_action_id: UUID | None
    source_case_id: UUID | None
    was_current: bool | None


class AdminReviewResolutionHistoryRead(BaseModel):
    closure_event_id: UUID
    event_sequence: int
    outcome: AdminReviewClosureOutcome
    mode: Literal["manual", "automatic"]
    reason: str
    actor_kind: Literal["admin", "automation"]
    actor_user_id: UUID | None
    automation_rule_id: str | None
    automation_rule_version: str | None
    trigger_actor_user_id: UUID | None
    admin_action_id: UUID | None
    closed_at: datetime
    references: list[AdminReviewResolutionReferenceRead] = Field(default_factory=list)


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
    applied_case_version: int
    resulting_case_version: int


class AdminReviewCaseActionResultRead(BaseModel):
    review_case: AdminReviewCaseDetailRead
    audit_action_id: UUID
    idempotent_replay: bool
    applied_case_version: int
    resulting_case_version: int


class AdminReviewCaseMergeResultRead(BaseModel):
    source_case: AdminReviewCaseDetailRead
    destination_case: AdminReviewCaseDetailRead
    audit_action_id: UUID
    idempotent_replay: bool
    applied_source_version: int
    applied_destination_version: int
    resulting_source_version: int
    resulting_destination_version: int


AdminReviewCaseDetailRead.model_rebuild()
