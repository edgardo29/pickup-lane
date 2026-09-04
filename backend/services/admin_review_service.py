"""Admin review signal and case workflow services."""

import hashlib
import uuid
from base64 import urlsafe_b64decode, urlsafe_b64encode
from binascii import Error as BinasciiError
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from json import JSONDecodeError, dumps, loads
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import (
    AdminAction,
    AdminContentModerationFinding,
    AdminFinancialOutcome,
    AdminReviewCase,
    AdminReviewCaseEvent,
    AdminReviewCaseNote,
    AdminReviewCaseResolutionReference,
    AdminReviewSignal,
    Game,
    Payment,
    SubPost,
    SubPostRequest,
    User,
)
from backend.schemas.admin_review_schema import (
    MAX_REVIEW_CASE_NOTE_BODY_LENGTH,
    AdminContentModerationFindingRead,
    AdminReviewCaseActionResultRead,
    AdminReviewCaseAssignment,
    AdminReviewCaseClose,
    AdminReviewCaseDetailRead,
    AdminReviewCaseEventRead,
    AdminReviewCaseFindingSummaryRead,
    AdminReviewCaseListRead,
    AdminReviewCaseMerge,
    AdminReviewCaseMergeResultRead,
    AdminReviewCaseNoteCreate,
    AdminReviewCaseNoteRead,
    AdminReviewCaseNoteResultRead,
    AdminReviewCaseRead,
    AdminReviewCaseReopen,
    AdminReviewCaseTargetSummaryRead,
    AdminReviewLinkedCaseRead,
    AdminReviewResolutionHistoryRead,
    AdminReviewResolutionReferenceRead,
    AdminReviewSignalRead,
)
from backend.services.admin_action_service import record_admin_action
from backend.services.admin_record_rules import (
    normalize_idempotency_key,
    normalize_metadata_value,
)
from backend.services.admin_review_actionability_service import (
    build_open_content_review_case_actionable_condition,
    is_game_content_review_actionable,
    is_sub_post_content_review_actionable,
)
from backend.services.auth_service import (
    require_active_admin_user,
    user_is_active_admin,
)
from backend.services.user_service import get_user_display_name

CASE_ACTIVE_STATUSES = ("open",)
VALID_CASE_STATUSES = ("open", "closed")
VALID_CASE_TYPES = ("community_game", "need_a_sub", "money", "user", "system")
CONTENT_MODERATION_CASE_CATEGORY = "content_moderation"
CHAT_MODERATION_CASE_CATEGORY = "chat_moderation"
REVIEW_CASE_LIST_CURSOR_SORT = "updated_at_desc"
REVIEW_CASE_LIST_CONTENT_TARGETS = "content_targets"
MAX_REVIEW_CASE_NOTES = 100
VALID_REVIEW_CASE_LIST_TARGET_TYPES = {
    REVIEW_CASE_LIST_CONTENT_TARGETS,
    "community_game",
    "need_a_sub",
}
VALID_CASE_CATEGORIES = {
    CONTENT_MODERATION_CASE_CATEGORY,
    "chat_moderation",
}
VALID_SIGNAL_CATEGORIES = {
    "chat_moderation",
}
VALID_SOURCES = {
    "chat_moderation",
}
VALID_PRIORITIES = ("attention", "urgent", "critical")
PRIORITY_RANK = {priority: index for index, priority in enumerate(VALID_PRIORITIES)}
VALID_CLOSURE_OUTCOMES = {
    "enforcement_applied",
    "no_action_needed",
    "invalid_signal",
}
VALID_RESOLUTION_MODES = {"manual", "automatic"}
VALID_EVENT_TYPES = {
    "case_created",
    "finding_attached",
    "finding_cleared",
    "signal_attached",
    "signal_superseded",
    "signal_reactivated",
    "note_added",
    "assignment_changed",
    "enforcement_action_linked",
    "closed",
    "reopened",
    "merged_into",
    "merged_from",
}
VALID_EVENT_ACTOR_KINDS = {"admin", "automation"}
SOURCE_STATE_EVENT_TYPES = {
    "finding_attached",
    "finding_cleared",
    "signal_attached",
    "signal_superseded",
    "signal_reactivated",
}
SOURCE_RECONCILIATION_RULE_ID = "moderation_review_case.source_reconciliation"
SOURCE_RECONCILIATION_RULE_VERSION = "1"
TARGET_LIFECYCLE_RULE_ID = "moderation_review_case.target_lifecycle_resolution"
TARGET_LIFECYCLE_RULE_VERSION = "1"
REVIEW_WORKFLOW_ACTION_TYPES = {
    "create_review_case",
    "close_review_case",
    "add_review_case_note",
    "assign_review_case",
    "reopen_review_case",
    "merge_review_case",
}


@dataclass(frozen=True)
class AutomaticContentLifecycleTransition:
    previous_state: str
    new_state: str
    trigger_actor_types: frozenset[str]
    closure_outcome: str
    linked_action_type: str | None = None


AUTOMATIC_CONTENT_LIFECYCLE_TRANSITIONS = {
    ("community_game", "host_cancelled"): AutomaticContentLifecycleTransition(
        "active", "cancelled", frozenset({"host"}), "no_action_needed"
    ),
    (
        "community_game",
        "admin_operational_cancelled",
    ): AutomaticContentLifecycleTransition(
        "active",
        "cancelled",
        frozenset({"admin"}),
        "no_action_needed",
        "cancel_game",
    ),
    (
        "community_game",
        "admin_moderation_cancelled",
    ): AutomaticContentLifecycleTransition(
        "active",
        "cancelled",
        frozenset({"admin"}),
        "enforcement_applied",
        "admin_cancel_community_game",
    ),
    (
        "community_game",
        "host_account_deleted",
    ): AutomaticContentLifecycleTransition(
        "active", "cancelled", frozenset({"owner"}), "no_action_needed"
    ),
    ("community_game", "game_completed"): AutomaticContentLifecycleTransition(
        "active",
        "completed",
        frozenset({"admin", "system"}),
        "no_action_needed",
    ),
    ("community_game", "game_expired"): AutomaticContentLifecycleTransition(
        "active", "expired", frozenset({"admin", "system"}), "no_action_needed"
    ),
    (
        "community_game",
        "admin_soft_deleted",
    ): AutomaticContentLifecycleTransition(
        "active", "soft_deleted", frozenset({"admin"}), "no_action_needed"
    ),
    ("need_a_sub", "owner_cancelled"): AutomaticContentLifecycleTransition(
        "active", "cancelled", frozenset({"owner"}), "no_action_needed"
    ),
    (
        "need_a_sub",
        "owner_account_deleted",
    ): AutomaticContentLifecycleTransition(
        "active", "cancelled", frozenset({"owner"}), "no_action_needed"
    ),
    ("need_a_sub", "admin_removed"): AutomaticContentLifecycleTransition(
        "active",
        "removed",
        frozenset({"admin"}),
        "enforcement_applied",
        "remove_sub_post",
    ),
    ("need_a_sub", "post_completed"): AutomaticContentLifecycleTransition(
        "active", "completed", frozenset({"scheduled_job"}), "no_action_needed"
    ),
    ("need_a_sub", "post_expired"): AutomaticContentLifecycleTransition(
        "active", "expired", frozenset({"scheduled_job"}), "no_action_needed"
    ),
}
EVENT_ADMIN_ACTION_TYPES = {
    "note_added": "add_review_case_note",
    "assignment_changed": "assign_review_case",
    "closed": "close_review_case",
    "reopened": "reopen_review_case",
    "merged_into": "merge_review_case",
    "merged_from": "merge_review_case",
}
EVENT_METADATA_FIELDS = {
    "case_created": {"source"},
    "finding_attached": {
        "finding_type",
        "risk_area",
        "source_field",
        "priority_before",
        "priority_after",
    },
    "finding_cleared": {
        "finding_type",
        "risk_area",
        "source_field",
        "priority_before",
        "priority_after",
    },
    "signal_attached": {
        "created_case",
        "source",
        "priority_before",
        "priority_after",
    },
    "signal_superseded": {"priority_before", "priority_after"},
    "signal_reactivated": {"priority_before", "priority_after"},
    "note_added": {"corrects_note_id"},
    "assignment_changed": {"previous_assignee_id", "next_assignee_id"},
    "enforcement_action_linked": {"action_type"},
    "reopened": {"prior_resolution_mode", "prior_resolution_outcome"},
    "merged_into": {"source_resolution_mode", "source_resolution_outcome"},
    "merged_from": {"source_resolution_mode", "source_resolution_outcome"},
}
CHAT_REVIEW_CASE_CREATION_RACE_CONSTRAINTS = {
    "uq_admin_review_cases_open_community_game_moderation",
    "uq_admin_review_cases_open_need_sub_moderation",
    "uq_admin_review_signals_source_idempotency_key",
}
REVIEW_TARGET_FIELDS = (
    "target_user_id",
    "target_game_id",
    "target_sub_post_id",
    "target_sub_post_request_id",
    "target_payment_id",
    "target_financial_outcome_id",
)
PRIMARY_TARGET_FIELDS = (
    "target_game_id",
    "target_sub_post_id",
    "target_sub_post_request_id",
    "target_payment_id",
    "target_financial_outcome_id",
    "target_user_id",
)
TARGET_MODEL_BY_FIELD = {
    "target_user_id": User,
    "target_game_id": Game,
    "target_sub_post_id": SubPost,
    "target_sub_post_request_id": SubPostRequest,
    "target_payment_id": Payment,
    "target_financial_outcome_id": AdminFinancialOutcome,
}
TARGET_NOT_FOUND_DETAIL = {
    "target_user_id": "Target user not found.",
    "target_game_id": "Target game not found.",
    "target_sub_post_id": "Target Need a Sub post not found.",
    "target_sub_post_request_id": "Target Need a Sub request not found.",
    "target_payment_id": "Target payment not found.",
    "target_financial_outcome_id": "Target financial outcome not found.",
}


def append_unique(values: list[str], value: str) -> None:
    if value and value not in values:
        values.append(value)


def review_integrity_constraint_name(error: IntegrityError) -> str | None:
    diagnostic = getattr(getattr(error, "orig", None), "diag", None)
    constraint_name = getattr(diagnostic, "constraint_name", None)
    return constraint_name if isinstance(constraint_name, str) else None


def is_retryable_chat_review_case_creation_race(error: IntegrityError) -> bool:
    return (
        review_integrity_constraint_name(error)
        in CHAT_REVIEW_CASE_CREATION_RACE_CONSTRAINTS
    )


def encode_admin_review_case_list_cursor(
    *,
    review_case: AdminReviewCase,
    case_status: str | None,
    case_category: str | None,
    target_type: str | None,
    assignment: str,
    viewer_user_id: uuid.UUID,
) -> str:
    payload = {
        "case_status": case_status,
        "case_category": case_category,
        "target_type": target_type,
        "assignment": assignment,
        "viewer_user_id": str(viewer_user_id) if assignment == "mine" else None,
        "sort": REVIEW_CASE_LIST_CURSOR_SORT,
        "updated_at": review_case.updated_at.isoformat(),
        "id": str(review_case.id),
    }
    serialized = dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return urlsafe_b64encode(serialized).decode("ascii")


def decode_admin_review_case_list_cursor(
    cursor: str | None,
) -> dict[str, object] | None:
    if cursor is None:
        return None

    try:
        decoded = urlsafe_b64decode(cursor.encode("ascii"))
        payload = loads(decoded.decode("utf-8"))
    except (BinasciiError, UnicodeDecodeError, ValueError, JSONDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cursor is invalid.",
        ) from exc

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cursor is invalid.",
        )

    required_keys = {
        "case_status",
        "case_category",
        "target_type",
        "assignment",
        "viewer_user_id",
        "sort",
        "updated_at",
        "id",
    }
    if not required_keys.issubset(payload):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cursor is invalid.",
        )
    return payload


def validate_admin_review_case_list_cursor_context(
    cursor_payload: dict[str, object] | None,
    *,
    case_status: str | None,
    case_category: str | None,
    target_type: str | None,
    assignment: str,
    viewer_user_id: uuid.UUID,
) -> None:
    if cursor_payload is None:
        return

    if (
        cursor_payload["case_status"] != case_status
        or cursor_payload["case_category"] != case_category
        or cursor_payload["target_type"] != target_type
        or cursor_payload["assignment"] != assignment
        or cursor_payload["viewer_user_id"]
        != (str(viewer_user_id) if assignment == "mine" else None)
        or cursor_payload["sort"] != REVIEW_CASE_LIST_CURSOR_SORT
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cursor does not match the current query.",
        )


def parse_admin_review_case_list_cursor_datetime(
    cursor_payload: dict[str, object],
) -> datetime:
    value = cursor_payload["updated_at"]
    if not isinstance(value, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cursor is invalid.",
        )
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cursor is invalid.",
        ) from exc


def parse_admin_review_case_list_cursor_uuid(
    cursor_payload: dict[str, object],
) -> uuid.UUID:
    value = cursor_payload["id"]
    if not isinstance(value, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cursor is invalid.",
        )
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cursor is invalid.",
        ) from exc


def build_admin_review_case_list_cursor_filter(
    cursor_payload: dict[str, object],
):
    updated_at = parse_admin_review_case_list_cursor_datetime(cursor_payload)
    review_case_id = parse_admin_review_case_list_cursor_uuid(cursor_payload)
    return or_(
        AdminReviewCase.updated_at < updated_at,
        and_(
            AdminReviewCase.updated_at == updated_at,
            AdminReviewCase.id < review_case_id,
        ),
    )


def require_review_read_access(user: User) -> None:
    require_active_admin_user(user)


def require_review_manage_access(user: User) -> None:
    require_active_admin_user(user)


def normalize_limited_text(value: str, field_name: str, max_length: int) -> str:
    normalized = " ".join(str(value or "").strip().split())
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} is required.",
        )
    if len(normalized) > max_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must be {max_length} characters or fewer.",
        )
    return normalized


def normalize_required_idempotency_key(value: str | None) -> str:
    idempotency_key = normalize_idempotency_key(value)
    if idempotency_key is None or len(idempotency_key) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="idempotency_key must be at least 8 characters.",
        )
    return idempotency_key


def normalize_metadata(metadata: dict[str, Any] | None) -> dict[str, Any] | None:
    if metadata is None:
        return None
    if not isinstance(metadata, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="metadata must be an object.",
        )
    return normalize_metadata_value(metadata)


def normalize_case_category(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized not in VALID_CASE_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="case_category is not supported.",
        )
    return normalized


def normalize_review_case_list_target_type(value: str | None) -> str | None:
    normalized = str(value or "").strip().lower()
    if not normalized or normalized == "all":
        return None
    if normalized not in VALID_REVIEW_CASE_LIST_TARGET_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="target_type is not supported.",
        )
    return normalized


def normalize_signal_category(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized not in VALID_SIGNAL_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="signal_category is not supported.",
        )
    return normalized


def normalize_source(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized not in VALID_SOURCES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="source is not supported.",
        )
    return normalized


def normalize_priority(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized not in VALID_PRIORITIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="priority is not supported.",
        )
    return normalized


def target_data_from_object(source: object) -> dict[str, uuid.UUID | None]:
    return {
        field_name: getattr(source, field_name, None)
        for field_name in REVIEW_TARGET_FIELDS
    }


def provided_target_fields(target_data: dict[str, uuid.UUID | None]) -> set[str]:
    return {
        field_name for field_name, value in target_data.items() if value is not None
    }


def primary_target(
    target_data: dict[str, uuid.UUID | None],
) -> tuple[str, uuid.UUID] | None:
    for field_name in PRIMARY_TARGET_FIELDS:
        value = target_data.get(field_name)
        if value is not None:
            return field_name, value
    return None


def validate_target_references(
    db: Session,
    target_data: dict[str, uuid.UUID | None],
) -> None:
    if not provided_target_fields(target_data):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one target field must be provided.",
        )

    for field_name, model in TARGET_MODEL_BY_FIELD.items():
        target_id = target_data.get(field_name)
        if target_id is None:
            continue
        record = db.get(model, target_id)
        if record is None or getattr(record, "deleted_at", None) is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=TARGET_NOT_FOUND_DETAIL[field_name],
            )


def infer_case_type(db: Session, target_data: dict[str, uuid.UUID | None]) -> str:
    if target_data.get("target_game_id") is not None:
        game = db.get(Game, target_data["target_game_id"])
        return "community_game" if game and game.game_type == "community" else "system"
    if (
        target_data.get("target_sub_post_id") is not None
        or target_data.get("target_sub_post_request_id") is not None
    ):
        return "need_a_sub"
    if (
        target_data.get("target_payment_id") is not None
        or target_data.get("target_financial_outcome_id") is not None
    ):
        return "money"
    if target_data.get("target_user_id") is not None:
        return "user"
    return "system"


def copy_targets(
    target_data: dict[str, uuid.UUID | None],
) -> dict[str, uuid.UUID | None]:
    return {
        field_name: target_data.get(field_name) for field_name in REVIEW_TARGET_FIELDS
    }


def require_event_metadata_fields(
    event_type: str,
    metadata: dict[str, Any] | None,
    expected_fields: set[str],
) -> dict[str, Any]:
    if not isinstance(metadata, dict) or set(metadata) != expected_fields:
        raise ValueError(f"{event_type} metadata does not match its exact schema.")
    return metadata


def require_event_metadata_string(
    event_type: str,
    metadata: dict[str, Any],
    field_name: str,
) -> str:
    value = metadata.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{event_type} metadata {field_name} must be a string.")
    return value


def require_event_metadata_uuid(
    event_type: str,
    metadata: dict[str, Any],
    field_name: str,
    *,
    optional: bool = True,
) -> uuid.UUID | None:
    value = metadata.get(field_name)
    if value is None and optional:
        return None
    if isinstance(value, uuid.UUID):
        return value
    if not isinstance(value, str):
        raise TypeError(f"{event_type} metadata {field_name} must be a UUID.")
    try:
        parsed = uuid.UUID(value)
    except ValueError as exc:
        raise ValueError(f"{event_type} metadata {field_name} must be a UUID.") from exc
    if str(parsed) != value:
        raise ValueError(f"{event_type} metadata {field_name} must be canonical.")
    return parsed


def require_case_projection_metadata(
    event_type: str,
    value: Any,
    *,
    expected_status: str,
) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {
        "case_status",
        "closure_outcome",
    }:
        raise ValueError(f"{event_type} case projection metadata is invalid.")
    if value.get("case_status") != expected_status:
        raise ValueError(f"{event_type} case projection status is invalid.")
    outcome = value.get("closure_outcome")
    if expected_status == "open" and outcome is not None:
        raise ValueError(f"{event_type} open projection cannot have an outcome.")
    if expected_status == "closed" and outcome not in VALID_CLOSURE_OUTCOMES:
        raise ValueError(f"{event_type} closed projection outcome is invalid.")
    return value


def validate_case_event_metadata(
    *,
    event_type: str,
    actor_kind: str,
    event_metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    if event_type == "closed":
        if not isinstance(event_metadata, dict):
            raise ValueError("closed metadata does not match its exact schema.")
        closure_mode = event_metadata.get("closure_mode")
        if actor_kind == "admin":
            metadata = require_event_metadata_fields(
                event_type,
                event_metadata,
                {
                    "closure_mode",
                    "reason",
                    "target_type",
                    "target_id",
                    "closed_by_user_id",
                    "previous_assignee_id",
                    "before",
                    "after",
                },
            )
            if closure_mode != "manual":
                raise ValueError("An administrator closure must be manual.")
            require_event_metadata_string(event_type, metadata, "reason")
            require_event_metadata_string(event_type, metadata, "target_type")
            if metadata.get("target_type") not in VALID_CASE_TYPES:
                raise ValueError("A closure target type is invalid.")
            require_event_metadata_uuid(
                event_type, metadata, "target_id", optional=False
            )
            require_event_metadata_uuid(
                event_type, metadata, "closed_by_user_id", optional=False
            )
        else:
            metadata = require_event_metadata_fields(
                event_type,
                event_metadata,
                {
                    "closure_mode",
                    "closure_source",
                    "lifecycle_action",
                    "target_type",
                    "previous_target_state",
                    "new_target_state",
                    "trigger_actor_type",
                    "trigger_actor_user_id",
                    "closed_by_user_id",
                    "previous_assignee_id",
                    "linked_admin_action_id",
                    "before",
                    "after",
                    "reason",
                    "target_id",
                },
            )
            if closure_mode != "automatic":
                raise ValueError("An automation closure must be automatic.")
            if metadata.get("closure_source") != "target_lifecycle":
                raise ValueError("An automation closure source is invalid.")
            for field_name in (
                "lifecycle_action",
                "target_type",
                "previous_target_state",
                "new_target_state",
                "trigger_actor_type",
                "reason",
            ):
                require_event_metadata_string(event_type, metadata, field_name)
            if metadata.get("target_type") not in VALID_CASE_TYPES:
                raise ValueError("A closure target type is invalid.")
            require_event_metadata_uuid(
                event_type, metadata, "target_id", optional=False
            )
            for field_name in (
                "trigger_actor_user_id",
                "closed_by_user_id",
                "linked_admin_action_id",
            ):
                require_event_metadata_uuid(event_type, metadata, field_name)
        require_event_metadata_uuid(event_type, metadata, "previous_assignee_id")
        require_case_projection_metadata(
            event_type, metadata.get("before"), expected_status="open"
        )
        require_case_projection_metadata(
            event_type, metadata.get("after"), expected_status="closed"
        )
        return metadata

    metadata = require_event_metadata_fields(
        event_type,
        event_metadata,
        EVENT_METADATA_FIELDS[event_type],
    )
    if event_type == "case_created":
        require_event_metadata_string(event_type, metadata, "source")
    elif event_type in {"finding_attached", "finding_cleared"}:
        for field_name in ("finding_type", "risk_area", "source_field"):
            require_event_metadata_string(event_type, metadata, field_name)
        for field_name in ("priority_before", "priority_after"):
            if metadata.get(field_name) not in VALID_PRIORITIES:
                raise ValueError(f"{event_type} requires valid priority attribution.")
    elif event_type == "signal_attached":
        if not isinstance(metadata.get("created_case"), bool):
            raise ValueError("signal_attached metadata created_case must be boolean.")
        require_event_metadata_string(event_type, metadata, "source")
        for field_name in ("priority_before", "priority_after"):
            if metadata.get(field_name) not in VALID_PRIORITIES:
                raise ValueError(f"{event_type} requires valid priority attribution.")
    elif event_type in {"signal_superseded", "signal_reactivated"}:
        for field_name in ("priority_before", "priority_after"):
            if metadata.get(field_name) not in VALID_PRIORITIES:
                raise ValueError(f"{event_type} requires valid priority attribution.")
    elif event_type == "note_added":
        require_event_metadata_uuid(event_type, metadata, "corrects_note_id")
    elif event_type == "assignment_changed":
        previous_id = require_event_metadata_uuid(
            event_type, metadata, "previous_assignee_id"
        )
        next_id = require_event_metadata_uuid(event_type, metadata, "next_assignee_id")
        if previous_id is None and next_id is None:
            raise ValueError("assignment_changed requires a prior or next assignee.")
    elif event_type == "enforcement_action_linked":
        require_event_metadata_string(event_type, metadata, "action_type")
    elif event_type == "reopened":
        if metadata.get("prior_resolution_mode") not in VALID_RESOLUTION_MODES:
            raise ValueError("reopened metadata resolution mode is invalid.")
        if metadata.get("prior_resolution_outcome") not in VALID_CLOSURE_OUTCOMES:
            raise ValueError("reopened metadata resolution outcome is invalid.")
    elif event_type in {"merged_into", "merged_from"}:
        if metadata.get("source_resolution_mode") not in VALID_RESOLUTION_MODES:
            raise ValueError(f"{event_type} source resolution mode is invalid.")
        if metadata.get("source_resolution_outcome") not in VALID_CLOSURE_OUTCOMES:
            raise ValueError(f"{event_type} source resolution outcome is invalid.")
    return metadata


def validate_case_event_payload(
    *,
    event_type: str,
    actor_kind: str,
    admin_action_id: uuid.UUID | None,
    signal_id: uuid.UUID | None,
    content_moderation_finding_id: uuid.UUID | None,
    note_id: uuid.UUID | None,
    related_case_id: uuid.UUID | None,
    related_event_id: uuid.UUID | None,
    trigger_actor_user_id: uuid.UUID | None,
    event_metadata: dict[str, Any] | None,
) -> None:
    references = {
        "signal": signal_id,
        "finding": content_moderation_finding_id,
        "note": note_id,
        "related_case": related_case_id,
        "related_event": related_event_id,
    }
    required_references = {
        "finding_attached": {"finding"},
        "finding_cleared": {"finding"},
        "signal_attached": {"signal"},
        "signal_superseded": {"signal"},
        "signal_reactivated": {"signal"},
        "note_added": {"note"},
        "reopened": {"related_event"},
        "merged_into": {"related_case", "related_event"},
        "merged_from": {"related_case", "related_event"},
    }.get(event_type, set())
    allowed_references = {
        "case_created": {"signal", "finding"},
        "finding_attached": {"finding"},
        "finding_cleared": {"finding"},
        "signal_attached": {"signal"},
        "signal_superseded": {"signal"},
        "signal_reactivated": {"signal"},
        "note_added": {"note"},
        "assignment_changed": set(),
        "enforcement_action_linked": set(),
        "closed": set(),
        "reopened": {"related_event"},
        "merged_into": {"related_case", "related_event"},
        "merged_from": {"related_case", "related_event"},
    }[event_type]
    present_references = {
        name for name, value in references.items() if value is not None
    }
    if not required_references.issubset(present_references):
        raise ValueError(f"{event_type} is missing its required reference.")
    if not present_references.issubset(allowed_references):
        raise ValueError(f"{event_type} contains an unsupported reference.")
    if event_type == "case_created" and len(present_references) > 1:
        raise ValueError("case_created accepts at most one source reference.")

    admin_event_types = {
        "note_added",
        "assignment_changed",
        "enforcement_action_linked",
        "reopened",
        "merged_into",
        "merged_from",
    }
    automation_event_types = {
        "case_created",
        "finding_attached",
        "finding_cleared",
        "signal_attached",
        "signal_superseded",
        "signal_reactivated",
    }
    if event_type in admin_event_types and actor_kind != "admin":
        raise ValueError(f"{event_type} requires an administrator actor.")
    if event_type in automation_event_types and actor_kind != "automation":
        raise ValueError(f"{event_type} requires an automation actor.")
    if event_type in admin_event_types and admin_action_id is None:
        raise ValueError(f"{event_type} requires an admin action.")
    if event_type == "closed" and actor_kind == "admin" and admin_action_id is None:
        raise ValueError("An administrator closure requires an admin action.")
    if actor_kind == "admin" and trigger_actor_user_id is not None:
        raise ValueError("Administrator events do not accept a triggering user.")
    if event_type != "closed" and trigger_actor_user_id is not None:
        raise ValueError(f"{event_type} does not accept a triggering user.")
    if event_type in automation_event_types and admin_action_id is not None:
        raise ValueError(f"{event_type} does not accept an admin action.")
    validate_case_event_metadata(
        event_type=event_type,
        actor_kind=actor_kind,
        event_metadata=event_metadata,
    )


def validate_case_event_relationships(
    db: Session,
    *,
    review_case: AdminReviewCase,
    event_type: str,
    actor_kind: str,
    actor_user_id: uuid.UUID | None,
    admin_action_id: uuid.UUID | None,
    signal_id: uuid.UUID | None,
    content_moderation_finding_id: uuid.UUID | None,
    note_id: uuid.UUID | None,
    related_case_id: uuid.UUID | None,
    related_event_id: uuid.UUID | None,
    automation_rule_id: str | None,
    automation_rule_version: str | None,
    trigger_actor_user_id: uuid.UUID | None,
    event_metadata: dict[str, Any],
) -> None:
    def referenced(model: type[Any], object_id: uuid.UUID | None) -> Any | None:
        if object_id is None:
            return None
        for candidate in db.new:
            if isinstance(candidate, model) and candidate.id == object_id:
                return candidate
        return db.get(model, object_id)

    def latest_event(
        event_types: set[str],
        *,
        finding_id: uuid.UUID | None = None,
        review_signal_id: uuid.UUID | None = None,
    ) -> AdminReviewCaseEvent | None:
        statement = select(AdminReviewCaseEvent).where(
            AdminReviewCaseEvent.review_case_id == review_case.id,
            AdminReviewCaseEvent.event_type.in_(event_types),
        )
        if finding_id is not None:
            statement = statement.where(
                AdminReviewCaseEvent.content_moderation_finding_id == finding_id
            )
        if review_signal_id is not None:
            statement = statement.where(
                AdminReviewCaseEvent.signal_id == review_signal_id
            )
        return db.scalar(
            statement.order_by(AdminReviewCaseEvent.event_sequence.desc()).limit(1)
        )

    def derived_case_priority() -> str:
        if review_case.case_category == CONTENT_MODERATION_CASE_CATEGORY:
            priorities = list(
                db.scalars(
                    select(AdminContentModerationFinding.priority).where(
                        AdminContentModerationFinding.review_case_id == review_case.id,
                        AdminContentModerationFinding.current_match.is_(True),
                    )
                ).all()
            )
        elif review_case.case_category == CHAT_MODERATION_CASE_CATEGORY:
            signals = list(
                db.scalars(
                    select(AdminReviewSignal).where(
                        AdminReviewSignal.review_case_id == review_case.id
                    )
                ).all()
            )
            priorities = [
                candidate.priority
                for candidate in signals
                if is_current_signal(candidate)
            ]
        else:
            raise ValueError("Source events require a moderation case category.")
        if not priorities:
            return "attention"
        return max(priorities, key=lambda priority: PRIORITY_RANK[priority])

    def prior_effective_assignee_id() -> uuid.UUID | None:
        prior_assignment_event = latest_event(
            {"assignment_changed", "closed", "reopened", "merged_into"}
        )
        if (
            prior_assignment_event is None
            or prior_assignment_event.event_type != "assignment_changed"
        ):
            return None
        return require_event_metadata_uuid(
            "assignment_changed",
            prior_assignment_event.event_metadata or {},
            "next_assignee_id",
        )

    finding = (
        referenced(AdminContentModerationFinding, content_moderation_finding_id)
        if content_moderation_finding_id is not None
        else None
    )
    if content_moderation_finding_id is not None and (
        finding is None or finding.review_case_id != review_case.id
    ):
        raise ValueError("Event finding must belong to the review case.")
    if finding is not None:
        if event_metadata.get("finding_type") != finding.finding_type:
            raise ValueError("Event finding type does not match the finding.")
        if event_metadata.get("risk_area") != finding.risk_area:
            raise ValueError("Event risk area does not match the finding.")
        if event_metadata.get("source_field") != finding.source_field:
            raise ValueError("Event source field does not match the finding.")

    signal = referenced(AdminReviewSignal, signal_id)
    if signal_id is not None and (
        signal is None or signal.review_case_id != review_case.id
    ):
        raise ValueError("Event signal must belong to the review case.")
    if signal is not None and event_metadata.get("source") not in {
        None,
        signal.source,
    }:
        raise ValueError("Event signal source does not match the signal.")

    note = referenced(AdminReviewCaseNote, note_id)
    if note_id is not None and (note is None or note.review_case_id != review_case.id):
        raise ValueError("Event note must belong to the review case.")
    if note is not None:
        metadata_correction_id = require_event_metadata_uuid(
            event_type, event_metadata, "corrects_note_id"
        )
        if metadata_correction_id != note.corrects_note_id:
            raise ValueError("Event note correction does not match the note.")

    related_case = (
        referenced(AdminReviewCase, related_case_id)
        if related_case_id is not None
        else None
    )
    if related_case_id is not None and related_case is None:
        raise ValueError("Related review case does not exist.")
    if related_case is not None:
        if related_case.id == review_case.id:
            raise ValueError("A case event cannot reference its own case.")
        if not review_cases_have_same_identity(review_case, related_case):
            raise ValueError("Merge event cases must have the same identity.")

    related_event = (
        referenced(AdminReviewCaseEvent, related_event_id)
        if related_event_id is not None
        else None
    )
    if related_event_id is not None and related_event is None:
        raise ValueError("Related review event does not exist.")

    action = referenced(AdminAction, admin_action_id)
    if admin_action_id is not None and action is None:
        raise ValueError("Event admin action does not exist.")
    if action is not None:
        expected_target_case_id = (
            related_case_id if event_type == "merged_from" else review_case.id
        )
        if action.target_review_case_id != expected_target_case_id:
            raise ValueError("Event admin action targets another review case.")
        if actor_kind == "admin" and action.admin_user_id != actor_user_id:
            raise ValueError("Event actor does not match the admin action actor.")
        if actor_kind == "automation" and (
            trigger_actor_user_id is None
            or action.admin_user_id != trigger_actor_user_id
        ):
            raise ValueError(
                "Automation event trigger does not match its action actor."
            )
        expected_action_type = (
            EVENT_ADMIN_ACTION_TYPES.get(event_type) if actor_kind == "admin" else None
        )
        if (
            expected_action_type is not None
            and action.action_type != expected_action_type
        ):
            raise ValueError("Event admin action type is invalid for the event.")
        if event_type == "enforcement_action_linked" and (
            action.action_type in REVIEW_WORKFLOW_ACTION_TYPES
            or event_metadata.get("action_type") != action.action_type
        ):
            raise ValueError("Linked enforcement action attribution is invalid.")
        if event_type == "closed" and actor_kind == "automation":
            if action.action_type in REVIEW_WORKFLOW_ACTION_TYPES:
                raise ValueError(
                    "Automatic closure cannot use a review workflow action."
                )
            linked_action_id = require_event_metadata_uuid(
                event_type, event_metadata, "linked_admin_action_id"
            )
            if linked_action_id != action.id:
                raise ValueError("Automatic closure action metadata is invalid.")
    elif event_type == "closed" and actor_kind == "automation":
        if event_metadata.get("linked_admin_action_id") is not None:
            raise ValueError("Automatic closure metadata references a missing action.")

    if event_type == "closed":
        after = event_metadata["after"]
        target_field_name, target_id = discover_case_primary_target(review_case)
        metadata_target_id = require_event_metadata_uuid(
            event_type, event_metadata, "target_id", optional=False
        )
        if (
            review_case.case_status != "closed"
            or after["case_status"] != review_case.case_status
            or after["closure_outcome"] != review_case.closure_outcome
            or event_metadata.get("reason") != review_case.closure_reason
            or event_metadata.get("target_type") != review_case.case_type
            or metadata_target_id != target_id
        ):
            raise ValueError("Closure event does not match the case resolution.")
        if action is not None and getattr(action, target_field_name) != target_id:
            raise ValueError("Closure action does not match the case transition.")
        if (
            actor_kind == "admin"
            and action is not None
            and (action.reason != review_case.closure_reason)
        ):
            raise ValueError("Manual closure action reason does not match the case.")
        if actor_kind == "admin":
            metadata_closed_by_id = require_event_metadata_uuid(
                event_type, event_metadata, "closed_by_user_id", optional=False
            )
            if (
                review_case.closure_mode != "manual"
                or review_case.closed_by_user_id != actor_user_id
                or metadata_closed_by_id != actor_user_id
                or review_case.closure_rule_id is not None
                or review_case.closure_rule_version is not None
                or trigger_actor_user_id is not None
            ):
                raise ValueError("Manual closure attribution does not match the case.")
        else:
            metadata_trigger_actor_id = require_event_metadata_uuid(
                event_type, event_metadata, "trigger_actor_user_id"
            )
            metadata_closed_by_id = require_event_metadata_uuid(
                event_type, event_metadata, "closed_by_user_id"
            )
            metadata_action_id = require_event_metadata_uuid(
                event_type, event_metadata, "linked_admin_action_id"
            )
            if (
                review_case.closure_mode != "automatic"
                or review_case.closure_rule_id != automation_rule_id
                or review_case.closure_rule_version != automation_rule_version
                or review_case.closed_by_user_id != metadata_closed_by_id
                or trigger_actor_user_id != metadata_trigger_actor_id
                or admin_action_id != metadata_action_id
            ):
                raise ValueError(
                    "Automatic closure attribution does not match the case."
                )
            if (
                review_case.closure_outcome == "enforcement_applied"
                and admin_action_id is None
            ):
                raise ValueError(
                    "Automatic enforcement closure requires a linked action."
                )
            target = (
                db.get(Game, target_id)
                if review_case.case_type == "community_game"
                else db.get(SubPost, target_id)
            )
            if target is None:
                raise ValueError("Automatic closure target does not exist.")
            validate_automatic_content_lifecycle_transition(
                target_type=review_case.case_type,
                lifecycle_action=event_metadata["lifecycle_action"],
                previous_target_state=event_metadata["previous_target_state"],
                new_target_state=event_metadata["new_target_state"],
                trigger_actor_type=event_metadata["trigger_actor_type"],
                trigger_actor_user_id=trigger_actor_user_id,
                closed_by_user_id=metadata_closed_by_id,
                closure_outcome=review_case.closure_outcome,
                admin_action=action,
            )
            validate_automatic_content_lifecycle_target_state(
                target=target,
                target_type=review_case.case_type,
                new_target_state=event_metadata["new_target_state"],
            )

    if event_type == "reopened":
        if (
            related_event is None
            or related_event.review_case_id != review_case.id
            or related_event.event_type != "closed"
        ):
            raise ValueError("Reopen must reference the same case's prior closure.")
        if event_metadata.get(
            "prior_resolution_mode"
        ) != related_event.event_metadata.get("closure_mode") or event_metadata.get(
            "prior_resolution_outcome"
        ) != related_event.event_metadata.get("after", {}).get("closure_outcome"):
            raise ValueError("Reopen metadata does not match the prior closure.")
    elif event_type == "merged_into":
        if (
            related_case is None
            or review_case.merged_into_case_id != related_case.id
            or review_case.case_status != "closed"
            or review_case.closure_mode not in VALID_RESOLUTION_MODES
            or review_case.closure_outcome not in VALID_CLOSURE_OUTCOMES
            or not review_case.closure_reason
            or review_case.closed_at is None
            or review_case.assigned_to_user_id is not None
        ):
            raise ValueError("Outgoing merge event does not match the case link.")
        if (
            related_event is None
            or related_event.review_case_id != review_case.id
            or related_event.event_type != "closed"
            or related_event.event_sequence != review_case.case_version
        ):
            raise ValueError("A merge source must reference its retained closure.")
        if (
            event_metadata.get("source_resolution_mode") != review_case.closure_mode
            or event_metadata.get("source_resolution_outcome")
            != review_case.closure_outcome
        ):
            raise ValueError("Outgoing merge metadata does not match the source.")
    elif event_type == "merged_from":
        if (
            related_case is None
            or related_case.merged_into_case_id != review_case.id
            or related_event is None
            or related_event.review_case_id != related_case.id
            or related_event.event_type != "merged_into"
            or related_event.related_case_id != review_case.id
            or related_event.admin_action_id != admin_action_id
        ):
            raise ValueError(
                "Incoming merge event does not match its reciprocal event."
            )
        if event_metadata != related_event.event_metadata:
            raise ValueError("Reciprocal merge event metadata does not match.")

    if event_type == "case_created":
        expected_source = {
            "content_moderation_finding": (
                CONTENT_MODERATION_CASE_CATEGORY,
                "content_moderation_scanner",
            ),
            "chat_moderation_detection": (
                CHAT_MODERATION_CASE_CATEGORY,
                "chat_moderation",
            ),
        }.get(review_case.creation_reason)
        if (
            review_case.case_status != "open"
            or review_case.case_version != 1
            or review_case.assigned_to_user_id is not None
            or review_case.merged_into_case_id is not None
            or review_case.closure_mode is not None
            or review_case.closure_outcome is not None
        ):
            raise ValueError("Case-created event does not match the new case state.")
        if expected_source is None:
            if (
                event_metadata.get("source") != review_case.creation_reason
                or signal_id is not None
                or content_moderation_finding_id is not None
            ):
                raise ValueError(
                    "Case-created event does not match the new case state."
                )
            return
        if (
            review_case.case_category != expected_source[0]
            or event_metadata.get("source") != expected_source[1]
        ):
            raise ValueError("Case-created event does not match the new case state.")
        if review_case.case_category == CONTENT_MODERATION_CASE_CATEGORY and (
            signal_id is not None or content_moderation_finding_id is not None
        ):
            raise ValueError("Content case creation precedes finding attachment.")
        if review_case.case_category == CHAT_MODERATION_CASE_CATEGORY and (
            signal is None
            or not is_current_signal(signal)
            or signal.signal_status != "attached"
            or target_data_from_object(signal) != target_data_from_object(review_case)
        ):
            raise ValueError("Chat case creation requires its current attached signal.")

    if event_type in SOURCE_STATE_EVENT_TYPES:
        if review_case.case_status != "open":
            raise ValueError("Source state events require an open review case.")
        prior_source_event = latest_event(SOURCE_STATE_EVENT_TYPES)
        expected_priority_before = (
            (prior_source_event.event_metadata or {}).get("priority_after")
            if prior_source_event is not None
            else review_case.priority
        )
        if (
            event_metadata.get("priority_before") != expected_priority_before
            or event_metadata.get("priority_after") != review_case.priority
            or review_case.priority != derived_case_priority()
        ):
            raise ValueError("Source event priority does not match the case state.")

    if event_type in {"finding_attached", "finding_cleared"}:
        prior_finding_event = latest_event(
            {"finding_attached", "finding_cleared"},
            finding_id=content_moderation_finding_id,
        )
        expected_current = event_type == "finding_attached"
        if (
            review_case.case_category != CONTENT_MODERATION_CASE_CATEGORY
            or finding is None
            or finding.current_match is not expected_current
            or (event_type == "finding_attached" and prior_finding_event is not None)
            or (
                event_type == "finding_cleared"
                and (
                    prior_finding_event is None
                    or prior_finding_event.event_type != "finding_attached"
                )
            )
        ):
            raise ValueError("Finding event does not match the finding state.")

    if event_type in {
        "signal_attached",
        "signal_superseded",
        "signal_reactivated",
    }:
        prior_signal_event = latest_event(
            {"signal_attached", "signal_superseded", "signal_reactivated"},
            review_signal_id=signal_id,
        )
        expected_current = event_type != "signal_superseded"
        if (
            review_case.case_category != CHAT_MODERATION_CASE_CATEGORY
            or signal is None
            or signal.signal_status != "attached"
            or is_current_signal(signal) is not expected_current
            or target_data_from_object(signal) != target_data_from_object(review_case)
            or (event_type == "signal_attached" and prior_signal_event is not None)
            or (
                event_type == "signal_superseded"
                and (
                    prior_signal_event is None
                    or prior_signal_event.event_type
                    not in {"signal_attached", "signal_reactivated"}
                )
            )
            or (
                event_type == "signal_reactivated"
                and (
                    prior_signal_event is None
                    or prior_signal_event.event_type != "signal_superseded"
                )
            )
        ):
            raise ValueError("Signal event does not match the signal state.")
        if event_type == "signal_attached":
            creation_event = db.scalar(
                select(AdminReviewCaseEvent).where(
                    AdminReviewCaseEvent.review_case_id == review_case.id,
                    AdminReviewCaseEvent.event_type == "case_created",
                )
            )
            created_case = bool(event_metadata.get("created_case"))
            if created_case is not (
                creation_event is not None and creation_event.signal_id == signal.id
            ):
                raise ValueError("Signal attachment creation attribution is invalid.")

    if event_type == "note_added":
        action_metadata = (action.metadata_ or {}) if action is not None else {}
        if (
            review_case.case_status != "open"
            or note is None
            or note.author_user_id != actor_user_id
            or note.note_status != "active"
            or note.edited_at is not None
            or note.deleted_at is not None
            or str(note.id) != action_metadata.get("note_id")
            or action_metadata.get("corrects_note_id")
            != event_metadata.get("corrects_note_id")
            or db.scalar(
                select(AdminReviewCaseEvent.id).where(
                    AdminReviewCaseEvent.review_case_id == review_case.id,
                    AdminReviewCaseEvent.event_type == "note_added",
                    AdminReviewCaseEvent.note_id == note.id,
                )
            )
            is not None
        ):
            raise ValueError("Note event does not match an eligible new note.")

    if event_type == "assignment_changed":
        previous_id = require_event_metadata_uuid(
            event_type, event_metadata, "previous_assignee_id"
        )
        next_id = require_event_metadata_uuid(
            event_type, event_metadata, "next_assignee_id"
        )
        action_metadata = (action.metadata_ or {}) if action is not None else {}
        if (
            review_case.case_status != "open"
            or previous_id == next_id
            or previous_id != prior_effective_assignee_id()
            or next_id != review_case.assigned_to_user_id
            or (next_id is None) is not (review_case.assigned_at is None)
            or action_metadata.get("previous_assignee_id")
            != event_metadata.get("previous_assignee_id")
            or action_metadata.get("next_assignee_id")
            != event_metadata.get("next_assignee_id")
        ):
            raise ValueError("Assignment event does not match the case assignment.")

    if event_type == "enforcement_action_linked":
        target_field_name, target_id = discover_case_primary_target(review_case)
        if (
            review_case.case_status != "open"
            or action is None
            or getattr(action, target_field_name) != target_id
            or db.scalar(
                select(AdminReviewCaseEvent.id).where(
                    AdminReviewCaseEvent.review_case_id == review_case.id,
                    AdminReviewCaseEvent.event_type == "enforcement_action_linked",
                    AdminReviewCaseEvent.admin_action_id == action.id,
                )
            )
            is not None
        ):
            raise ValueError("Enforcement-link event does not match the open case.")

    if event_type == "reopened":
        latest_lifecycle_event = latest_event({"closed", "reopened", "merged_into"})
        action_metadata = (action.metadata_ or {}) if action is not None else {}
        if (
            review_case.case_status != "open"
            or review_case.closed_by_user_id is not None
            or review_case.closure_outcome is not None
            or review_case.closure_reason is not None
            or review_case.closure_mode is not None
            or review_case.closure_rule_id is not None
            or review_case.closure_rule_version is not None
            or review_case.closed_at is not None
            or review_case.assigned_to_user_id is not None
            or review_case.merged_into_case_id is not None
            or latest_lifecycle_event is None
            or latest_lifecycle_event.id != related_event_id
            or action_metadata.get("prior_closure_event_id") != str(related_event_id)
            or action_metadata.get("prior_resolution_mode")
            != event_metadata.get("prior_resolution_mode")
            or action_metadata.get("prior_resolution_outcome")
            != event_metadata.get("prior_resolution_outcome")
        ):
            raise ValueError("Reopen event does not match the resulting open case.")

    if event_type == "merged_into" and (
        related_case is None
        or related_case.case_status != "open"
        or related_case.merged_into_case_id is not None
        or db.scalar(
            select(AdminReviewCaseEvent.id).where(
                AdminReviewCaseEvent.review_case_id == review_case.id,
                AdminReviewCaseEvent.event_type == "merged_into",
            )
        )
        is not None
    ):
        raise ValueError("Outgoing merge event does not match the destination state.")

    if event_type == "merged_from" and (
        review_case.case_status != "open"
        or review_case.merged_into_case_id is not None
        or db.scalar(
            select(AdminReviewCaseEvent.id).where(
                AdminReviewCaseEvent.review_case_id == review_case.id,
                AdminReviewCaseEvent.event_type == "merged_from",
                AdminReviewCaseEvent.related_case_id == related_case_id,
            )
        )
        is not None
    ):
        raise ValueError("Incoming merge event does not match the destination state.")


def create_case_event(
    db: Session,
    *,
    review_case_id: uuid.UUID,
    event_type: str,
    actor_user_id: uuid.UUID | None = None,
    admin_action_id: uuid.UUID | None = None,
    signal_id: uuid.UUID | None = None,
    content_moderation_finding_id: uuid.UUID | None = None,
    note_id: uuid.UUID | None = None,
    related_case_id: uuid.UUID | None = None,
    related_event_id: uuid.UUID | None = None,
    actor_kind: str | None = None,
    automation_rule_id: str | None = None,
    automation_rule_version: str | None = None,
    trigger_actor_user_id: uuid.UUID | None = None,
    event_metadata: dict[str, Any] | None = None,
    created_at: datetime | None = None,
) -> AdminReviewCaseEvent:
    if event_type not in VALID_EVENT_TYPES:
        raise ValueError("event_type is not supported.")
    normalized_actor_kind = actor_kind or (
        "admin" if actor_user_id is not None else "automation"
    )
    if normalized_actor_kind not in VALID_EVENT_ACTOR_KINDS:
        raise ValueError("actor_kind is not supported.")
    if normalized_actor_kind == "admin":
        if actor_user_id is None:
            raise ValueError("Admin events require actor_user_id.")
        if automation_rule_id is not None or automation_rule_version is not None:
            raise ValueError("Admin events do not accept automation rule identity.")
    else:
        if actor_user_id is not None:
            raise ValueError("Automation events do not accept actor_user_id.")
        if not isinstance(automation_rule_id, str) or not automation_rule_id.strip():
            raise ValueError("Automation events require automation_rule_id.")
        if (
            not isinstance(automation_rule_version, str)
            or not automation_rule_version.strip()
        ):
            raise ValueError("Automation events require automation_rule_version.")
        automation_rule_id = automation_rule_id.strip()
        automation_rule_version = automation_rule_version.strip()
        if len(automation_rule_id) > 120 or len(automation_rule_version) > 40:
            raise ValueError("Automation rule identity exceeds its storage bound.")

    review_case = db.get(AdminReviewCase, review_case_id)
    if review_case is None:
        raise ValueError("Review case is required before creating an event.")

    validate_case_event_payload(
        event_type=event_type,
        actor_kind=normalized_actor_kind,
        admin_action_id=admin_action_id,
        signal_id=signal_id,
        content_moderation_finding_id=content_moderation_finding_id,
        note_id=note_id,
        related_case_id=related_case_id,
        related_event_id=related_event_id,
        trigger_actor_user_id=trigger_actor_user_id,
        event_metadata=event_metadata,
    )
    if not isinstance(event_metadata, dict):
        raise TypeError(f"{event_type} metadata must be an object.")
    validate_case_event_relationships(
        db,
        review_case=review_case,
        event_type=event_type,
        actor_kind=normalized_actor_kind,
        actor_user_id=actor_user_id,
        admin_action_id=admin_action_id,
        signal_id=signal_id,
        content_moderation_finding_id=content_moderation_finding_id,
        note_id=note_id,
        related_case_id=related_case_id,
        related_event_id=related_event_id,
        automation_rule_id=automation_rule_id,
        automation_rule_version=automation_rule_version,
        trigger_actor_user_id=trigger_actor_user_id,
        event_metadata=event_metadata,
    )
    if event_type == "case_created":
        event_sequence = review_case.case_version
        if event_sequence != 1:
            raise ValueError("Case creation must initialize version 1.")
    else:
        review_case.case_version += 1
        event_sequence = review_case.case_version
    event_time = created_at or datetime.now(timezone.utc)
    review_case.updated_at = event_time
    db.add(review_case)
    db.flush()
    event = AdminReviewCaseEvent(
        id=uuid.uuid4(),
        review_case_id=review_case_id,
        event_type=event_type,
        event_sequence=event_sequence,
        case_version=event_sequence,
        actor_kind=normalized_actor_kind,
        actor_user_id=actor_user_id,
        admin_action_id=admin_action_id,
        signal_id=signal_id,
        content_moderation_finding_id=content_moderation_finding_id,
        note_id=note_id,
        related_case_id=related_case_id,
        related_event_id=related_event_id,
        automation_rule_id=automation_rule_id,
        automation_rule_version=automation_rule_version,
        trigger_actor_user_id=trigger_actor_user_id,
        event_metadata=normalize_metadata(event_metadata),
        created_at=event_time,
    )
    db.add(event)
    db.flush([event])
    return event


def get_review_case_or_404(
    db: Session,
    review_case_id: uuid.UUID,
) -> AdminReviewCase:
    review_case = db.get(AdminReviewCase, review_case_id)
    if review_case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review case not found.",
        )
    return review_case


def get_review_case_for_update_or_404(
    db: Session,
    review_case_id: uuid.UUID,
) -> AdminReviewCase:
    review_case = db.scalar(
        select(AdminReviewCase)
        .where(AdminReviewCase.id == review_case_id)
        .execution_options(populate_existing=True)
        .with_for_update()
    )
    if review_case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review case not found.",
        )
    return review_case


def review_case_request_fingerprint(payload: dict[str, object]) -> str:
    serialized = dumps(payload, separators=(",", ":"), sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def review_case_safe_snapshot(review_case: AdminReviewCase) -> dict[str, object]:
    return {
        "id": str(review_case.id),
        "case_status": review_case.case_status,
        "case_version": review_case.case_version,
        "priority": review_case.priority,
        "assigned_to_user_id": (
            str(review_case.assigned_to_user_id)
            if review_case.assigned_to_user_id is not None
            else None
        ),
        "closure_outcome": review_case.closure_outcome,
        "merged_into_case_id": (
            str(review_case.merged_into_case_id)
            if review_case.merged_into_case_id is not None
            else None
        ),
        "updated_at": review_case.updated_at.isoformat(),
    }


def review_case_conflict(
    code: str,
    review_case: AdminReviewCase,
    *,
    existing_open_case_id: uuid.UUID | None = None,
) -> HTTPException:
    detail: dict[str, object] = {
        "code": code,
        "current": review_case_safe_snapshot(review_case),
    }
    if existing_open_case_id is not None:
        detail["existing_open_case_id"] = str(existing_open_case_id)
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def lock_primary_target(
    db: Session,
    *,
    target_field_name: str,
    target_id: uuid.UUID,
) -> object | None:
    target_model = TARGET_MODEL_BY_FIELD.get(target_field_name)
    if target_model is None:
        raise ValueError("Review case primary target is not lockable.")
    tracked_target = db.identity_map.get(db.identity_key(target_model, target_id))
    if tracked_target is not None and db.is_modified(
        tracked_target, include_collections=False
    ):
        db.flush([tracked_target])
    return db.scalar(
        select(target_model)
        .where(target_model.id == target_id)
        .execution_options(populate_existing=True)
        .with_for_update()
    )


def discover_case_primary_target(
    review_case: AdminReviewCase,
) -> tuple[str, uuid.UUID]:
    target = primary_target(target_data_from_object(review_case))
    if target is None:
        raise review_case_conflict("review_case_transition_conflict", review_case)
    return target


def lock_review_case_with_target(
    db: Session,
    review_case_id: uuid.UUID,
) -> tuple[AdminReviewCase, object]:
    discovered_case = get_review_case_or_404(db, review_case_id)
    target_field_name, target_id = discover_case_primary_target(discovered_case)
    target = lock_primary_target(
        db,
        target_field_name=target_field_name,
        target_id=target_id,
    )
    locked_case = get_review_case_for_update_or_404(db, review_case_id)
    if discover_case_primary_target(locked_case) != (target_field_name, target_id):
        raise review_case_conflict("review_case_transition_conflict", locked_case)
    if target is None:
        raise review_case_conflict("review_case_transition_conflict", locked_case)
    return locked_case, target


def require_expected_case_version(
    review_case: AdminReviewCase,
    expected_case_version: int,
) -> None:
    if review_case.case_version != expected_case_version:
        raise review_case_conflict("review_case_version_conflict", review_case)


def get_latest_closure_event(
    db: Session,
    review_case_id: uuid.UUID,
) -> AdminReviewCaseEvent | None:
    return db.scalar(
        select(AdminReviewCaseEvent)
        .where(
            AdminReviewCaseEvent.review_case_id == review_case_id,
            AdminReviewCaseEvent.event_type == "closed",
        )
        .order_by(AdminReviewCaseEvent.event_sequence.desc())
        .limit(1)
    )


def merged_source_case_ids(
    db: Session,
    review_case_id: uuid.UUID,
) -> list[uuid.UUID]:
    discovered: list[uuid.UUID] = []
    frontier = [review_case_id]
    while frontier:
        parent_ids = list(frontier)
        frontier = []
        child_ids = list(
            db.scalars(
                select(AdminReviewCase.id)
                .where(AdminReviewCase.merged_into_case_id.in_(parent_ids))
                .order_by(AdminReviewCase.id.asc())
            ).all()
        )
        for child_id in child_ids:
            if child_id not in discovered:
                discovered.append(child_id)
                frontier.append(child_id)
    return discovered


def review_case_aggregate_ids(
    db: Session,
    review_case_id: uuid.UUID,
) -> list[uuid.UUID]:
    return [review_case_id, *merged_source_case_ids(db, review_case_id)]


def append_resolution_references(
    db: Session,
    *,
    review_case: AdminReviewCase,
    closure_event: AdminReviewCaseEvent,
) -> None:
    db.flush()
    source_case_ids = merged_source_case_ids(db, review_case.id)
    included_case_ids = [review_case.id, *source_case_ids]

    findings = list(
        db.scalars(
            select(AdminContentModerationFinding)
            .where(AdminContentModerationFinding.review_case_id.in_(included_case_ids))
            .order_by(AdminContentModerationFinding.id.asc())
            .execution_options(populate_existing=True)
            .with_for_update()
        ).all()
    )
    signals = list(
        db.scalars(
            select(AdminReviewSignal)
            .where(AdminReviewSignal.review_case_id.in_(included_case_ids))
            .order_by(AdminReviewSignal.id.asc())
            .execution_options(populate_existing=True)
            .with_for_update()
        ).all()
    )
    enforcement_actions = list(
        db.scalars(
            select(AdminAction)
            .where(
                AdminAction.target_review_case_id.in_(included_case_ids),
                ~AdminAction.action_type.in_(REVIEW_WORKFLOW_ACTION_TYPES),
                or_(
                    AdminAction.id == closure_event.admin_action_id,
                    exists(
                        select(AdminReviewCaseEvent.id).where(
                            AdminReviewCaseEvent.admin_action_id == AdminAction.id,
                            AdminReviewCaseEvent.review_case_id.in_(included_case_ids),
                            AdminReviewCaseEvent.event_type
                            == "enforcement_action_linked",
                        )
                    ),
                ),
            )
            .order_by(AdminAction.id.asc())
            .execution_options(populate_existing=True)
            .with_for_update()
        ).all()
    )

    for finding in findings:
        db.add(
            AdminReviewCaseResolutionReference(
                id=uuid.uuid4(),
                closure_event_id=closure_event.id,
                reference_type="finding",
                content_moderation_finding_id=finding.id,
                was_current=finding.current_match,
            )
        )
    for signal in signals:
        db.add(
            AdminReviewCaseResolutionReference(
                id=uuid.uuid4(),
                closure_event_id=closure_event.id,
                reference_type="signal",
                signal_id=signal.id,
                was_current=is_current_signal(signal),
            )
        )
    for action in enforcement_actions:
        db.add(
            AdminReviewCaseResolutionReference(
                id=uuid.uuid4(),
                closure_event_id=closure_event.id,
                reference_type="enforcement_action",
                admin_action_id=action.id,
            )
        )
    for source_case_id in source_case_ids:
        db.add(
            AdminReviewCaseResolutionReference(
                id=uuid.uuid4(),
                closure_event_id=closure_event.id,
                reference_type="source_case",
                source_case_id=source_case_id,
            )
        )


def eligible_admin_by_id(
    db: Session,
    user_id: uuid.UUID | None,
    *,
    lock: bool = False,
) -> User | None:
    if user_id is None:
        return None
    statement = select(User).where(User.id == user_id)
    if lock:
        statement = statement.execution_options(
            populate_existing=True
        ).with_for_update()
    user = db.scalar(statement)
    return user if user is not None and user_is_active_admin(user) else None


def lock_eligible_admin_ids(
    db: Session,
    user_ids: set[uuid.UUID],
) -> set[uuid.UUID]:
    if not user_ids:
        return set()
    users = db.scalars(
        select(User)
        .where(User.id.in_(user_ids))
        .order_by(User.id.asc())
        .execution_options(populate_existing=True)
        .with_for_update()
    ).all()
    return {user.id for user in users if user_is_active_admin(user)}


def signal_issue_labels(signal: AdminReviewSignal) -> list[str]:
    metadata = signal.metadata_ or {}
    labels: list[str] = []
    detected_categories = metadata.get("detected_categories")
    if isinstance(detected_categories, list):
        for category in detected_categories:
            append_unique(labels, str(category or "").strip())
    if not labels:
        append_unique(labels, str(signal.signal_category or "").strip())
    return labels


def is_current_signal(signal: AdminReviewSignal) -> bool:
    if signal.signal_status == "dismissed":
        return False
    metadata = signal.metadata_ or {}
    return metadata.get("current_match") is not False


def priority_for_current_signals(
    db: Session,
    review_case_id: uuid.UUID,
) -> str:
    signals = list(
        db.scalars(
            select(AdminReviewSignal)
            .where(AdminReviewSignal.review_case_id == review_case_id)
            .order_by(AdminReviewSignal.id.asc())
        ).all()
    )
    priorities = [signal.priority for signal in signals if is_current_signal(signal)]
    if not priorities:
        return "attention"
    return max(priorities, key=lambda priority: PRIORITY_RANK[priority])


def apply_review_signal_current_state(
    db: Session,
    *,
    signal_id: uuid.UUID,
    metadata: dict[str, Any],
    changed_at: datetime,
) -> bool:
    discovered_signal = db.get(AdminReviewSignal, signal_id)
    if discovered_signal is None or discovered_signal.review_case_id is None:
        return False
    discovered_case = get_review_case_or_404(db, discovered_signal.review_case_id)
    target_field_name, target_id = discover_case_primary_target(discovered_case)
    if (
        lock_primary_target(
            db, target_field_name=target_field_name, target_id=target_id
        )
        is None
    ):
        return False
    review_case = get_review_case_for_update_or_404(db, discovered_case.id)
    if review_case.case_status != "open":
        return False
    signal = db.scalar(
        select(AdminReviewSignal)
        .where(AdminReviewSignal.id == signal_id)
        .execution_options(populate_existing=True)
        .with_for_update()
    )
    if signal is None or signal.review_case_id != review_case.id:
        return False
    was_current = is_current_signal(signal)
    signal.metadata_ = normalize_metadata(metadata)
    signal.updated_at = changed_at
    is_current = is_current_signal(signal)
    if was_current == is_current:
        db.add(signal)
        return False

    priority_before = review_case.priority
    db.add(signal)
    db.flush()
    priority_after = priority_for_current_signals(db, review_case.id)
    review_case.priority = priority_after
    create_case_event(
        db,
        review_case_id=review_case.id,
        event_type="signal_reactivated" if is_current else "signal_superseded",
        signal_id=signal.id,
        automation_rule_id=SOURCE_RECONCILIATION_RULE_ID,
        automation_rule_version=SOURCE_RECONCILIATION_RULE_VERSION,
        event_metadata={
            "priority_before": priority_before,
            "priority_after": priority_after,
        },
        created_at=changed_at,
    )
    return True


def content_finding_issue_labels(
    finding: AdminContentModerationFinding,
) -> list[str]:
    labels: list[str] = []
    append_unique(labels, str(finding.finding_type or "").strip())
    return labels


def build_review_case_finding_summary(
    signals: list[AdminReviewSignal],
    findings: list[AdminContentModerationFinding],
) -> AdminReviewCaseFindingSummaryRead:
    active_signals = [
        signal for signal in signals if signal.signal_status != "dismissed"
    ]
    current_labels: list[str] = []
    previous_labels: list[str] = []
    current_finding_count = 0

    for finding in findings:
        labels = content_finding_issue_labels(finding)
        if finding.current_match:
            current_finding_count += 1
            for label in labels:
                append_unique(current_labels, label)
            continue
        for label in labels:
            append_unique(previous_labels, label)

    for signal in active_signals:
        labels = signal_issue_labels(signal)
        if is_current_signal(signal):
            current_finding_count += 1
            for label in labels:
                append_unique(current_labels, label)
            continue
        for label in labels:
            append_unique(previous_labels, label)

    return AdminReviewCaseFindingSummaryRead(
        total_finding_count=len(findings) + len(active_signals),
        current_finding_count=current_finding_count,
        current_issue_type_count=len(current_labels),
        current_issue_labels=current_labels,
        previous_issue_labels=previous_labels,
    )


def format_review_target_location(city: str | None, state: str | None) -> str | None:
    parts = [part for part in (city, state) if part]
    return ", ".join(parts) if parts else None


def build_game_review_target_summary(
    game: Game,
) -> AdminReviewCaseTargetSummaryRead:
    if game.deleted_at is not None:
        status = "deleted"
    elif game.game_status != "active":
        status = game.game_status
    elif game.public_visibility_status == "hidden":
        status = "hidden"
    else:
        status = game.game_status

    return AdminReviewCaseTargetSummaryRead(
        label="Community Game" if game.game_type == "community" else "Game",
        title=game.title,
        subtitle=game.venue_name_snapshot,
        status=status,
        starts_at=game.starts_at,
        location=format_review_target_location(
            game.city_snapshot,
            game.state_snapshot,
        ),
    )


def build_sub_post_review_target_summary(
    post: SubPost,
) -> AdminReviewCaseTargetSummaryRead:
    status = (
        post.post_status
        if post.post_status != "active" or post.public_visibility_status != "hidden"
        else "hidden"
    )

    return AdminReviewCaseTargetSummaryRead(
        label="Need a Sub Post",
        title=post.team_name or "Need a Sub post",
        subtitle=post.location_name,
        status=status,
        starts_at=post.starts_at,
        location=format_review_target_location(post.city, post.state),
    )


def build_unavailable_review_target_summary(
    review_case: AdminReviewCase,
) -> AdminReviewCaseTargetSummaryRead | None:
    if (
        review_case.case_type == "community_game"
        or review_case.target_game_id is not None
    ):
        return AdminReviewCaseTargetSummaryRead(
            label="Community Game",
            title="Game unavailable",
            status="unavailable",
        )
    if (
        review_case.case_type == "need_a_sub"
        or review_case.target_sub_post_id is not None
        or review_case.target_sub_post_request_id is not None
    ):
        return AdminReviewCaseTargetSummaryRead(
            label="Need a Sub Post",
            title="Post unavailable",
            status="unavailable",
        )
    return None


def build_review_case_target_summaries(
    db: Session,
    cases: list[AdminReviewCase],
) -> dict[uuid.UUID, AdminReviewCaseTargetSummaryRead]:
    summaries: dict[uuid.UUID, AdminReviewCaseTargetSummaryRead] = {}
    game_case_ids: dict[uuid.UUID, list[uuid.UUID]] = {}
    sub_post_case_ids: dict[uuid.UUID, list[uuid.UUID]] = {}
    for review_case in cases:
        if review_case.target_game_id is not None:
            game_case_ids.setdefault(review_case.target_game_id, []).append(
                review_case.id
            )
        if review_case.target_sub_post_id is not None:
            sub_post_case_ids.setdefault(review_case.target_sub_post_id, []).append(
                review_case.id
            )

    if game_case_ids:
        games = db.scalars(
            select(Game).where(Game.id.in_(list(game_case_ids.keys())))
        ).all()
        loaded_game_ids = {game.id for game in games}
        for game in games:
            for case_id in game_case_ids.get(game.id, []):
                summaries[case_id] = build_game_review_target_summary(game)
        for game_id, case_ids in game_case_ids.items():
            if game_id in loaded_game_ids:
                continue
            for case_id in case_ids:
                review_case = next(
                    (item for item in cases if item.id == case_id),
                    None,
                )
                if review_case is not None:
                    summary = build_unavailable_review_target_summary(review_case)
                    if summary is not None:
                        summaries[case_id] = summary

    if sub_post_case_ids:
        posts = db.scalars(
            select(SubPost).where(SubPost.id.in_(list(sub_post_case_ids.keys())))
        ).all()
        loaded_post_ids = {post.id for post in posts}
        for post in posts:
            for case_id in sub_post_case_ids.get(post.id, []):
                summaries[case_id] = build_sub_post_review_target_summary(post)
        for post_id, case_ids in sub_post_case_ids.items():
            if post_id in loaded_post_ids:
                continue
            for case_id in case_ids:
                review_case = next(
                    (item for item in cases if item.id == case_id),
                    None,
                )
                if review_case is not None:
                    summary = build_unavailable_review_target_summary(review_case)
                    if summary is not None:
                        summaries[case_id] = summary

    for review_case in cases:
        if review_case.id in summaries:
            continue
        summary = build_unavailable_review_target_summary(review_case)
        if summary is not None:
            summaries[review_case.id] = summary

    return summaries


def get_review_case_target_summary(
    db: Session,
    review_case: AdminReviewCase,
) -> AdminReviewCaseTargetSummaryRead | None:
    summaries = build_review_case_target_summaries(db, [review_case])
    return summaries.get(review_case.id)


def serialize_review_case_read(
    review_case: AdminReviewCase,
    signals: list[AdminReviewSignal] | None = None,
    findings: list[AdminContentModerationFinding] | None = None,
    target_summary: AdminReviewCaseTargetSummaryRead | None = None,
    assignee: User | None = None,
) -> AdminReviewCaseRead:
    return AdminReviewCaseRead.model_validate(review_case).model_copy(
        update={
            "finding_summary": build_review_case_finding_summary(
                signals or [],
                findings or [],
            ),
            "target_summary": target_summary,
            "assignee_display_name": (
                get_user_display_name(assignee, fallback="Admin")
                if assignee is not None
                else None
            ),
            "assignee_is_eligible": (
                user_is_active_admin(assignee)
                if review_case.assigned_to_user_id is not None
                else None
            ),
        }
    )


def serialize_review_case_note_read(
    note: AdminReviewCaseNote,
    author_by_id: dict[uuid.UUID, User],
) -> AdminReviewCaseNoteRead:
    author = author_by_id.get(note.author_user_id)
    author_display_name = (
        get_user_display_name(author, fallback="Admin") if author else None
    )
    return AdminReviewCaseNoteRead.model_validate(note).model_copy(
        update={"author_display_name": author_display_name}
    )


def serialize_review_case_detail(
    db: Session,
    review_case: AdminReviewCase,
) -> AdminReviewCaseDetailRead:
    findings = list(
        db.scalars(
            select(AdminContentModerationFinding)
            .where(AdminContentModerationFinding.review_case_id == review_case.id)
            .order_by(
                AdminContentModerationFinding.created_at.asc(),
                AdminContentModerationFinding.id.asc(),
            )
        ).all()
    )
    signals = list(
        db.scalars(
            select(AdminReviewSignal)
            .where(AdminReviewSignal.review_case_id == review_case.id)
            .order_by(AdminReviewSignal.created_at.asc(), AdminReviewSignal.id.asc())
        ).all()
    )
    events = list(
        db.scalars(
            select(AdminReviewCaseEvent)
            .where(AdminReviewCaseEvent.review_case_id == review_case.id)
            .order_by(
                AdminReviewCaseEvent.event_sequence.asc(),
            )
        ).all()
    )
    notes = list(
        db.scalars(
            select(AdminReviewCaseNote)
            .where(AdminReviewCaseNote.review_case_id == review_case.id)
            .order_by(
                AdminReviewCaseNote.created_at.asc(),
                AdminReviewCaseNote.id.asc(),
            )
        ).all()
    )
    author_ids = {note.author_user_id for note in notes}
    author_by_id: dict[uuid.UUID, User] = {}
    if author_ids:
        authors = db.scalars(select(User).where(User.id.in_(author_ids))).all()
        author_by_id = {author.id: author for author in authors}
    assignee = (
        db.get(User, review_case.assigned_to_user_id)
        if review_case.assigned_to_user_id is not None
        else None
    )
    linked_cases = list(
        db.scalars(
            select(AdminReviewCase)
            .where(
                or_(
                    AdminReviewCase.id == review_case.merged_into_case_id,
                    AdminReviewCase.merged_into_case_id == review_case.id,
                )
            )
            .order_by(AdminReviewCase.created_at.asc(), AdminReviewCase.id.asc())
        ).all()
    )
    resolution_references = list(
        db.scalars(
            select(AdminReviewCaseResolutionReference)
            .join(
                AdminReviewCaseEvent,
                AdminReviewCaseEvent.id
                == AdminReviewCaseResolutionReference.closure_event_id,
            )
            .where(AdminReviewCaseEvent.review_case_id == review_case.id)
            .order_by(
                AdminReviewCaseEvent.event_sequence.asc(),
                AdminReviewCaseResolutionReference.reference_type.asc(),
                AdminReviewCaseResolutionReference.id.asc(),
            )
        ).all()
    )
    references_by_event_id: dict[
        uuid.UUID, list[AdminReviewResolutionReferenceRead]
    ] = {}
    for reference in resolution_references:
        references_by_event_id.setdefault(reference.closure_event_id, []).append(
            AdminReviewResolutionReferenceRead.model_validate(reference)
        )
    resolution_history = []
    for event in events:
        if event.event_type != "closed":
            continue
        metadata = event.event_metadata or {}
        resolution_history.append(
            AdminReviewResolutionHistoryRead(
                closure_event_id=event.id,
                event_sequence=event.event_sequence,
                outcome=metadata["after"]["closure_outcome"],
                mode=metadata["closure_mode"],
                reason=metadata["reason"],
                actor_kind=event.actor_kind,
                actor_user_id=event.actor_user_id,
                automation_rule_id=event.automation_rule_id,
                automation_rule_version=event.automation_rule_version,
                trigger_actor_user_id=event.trigger_actor_user_id,
                admin_action_id=event.admin_action_id,
                closed_at=event.created_at,
                references=references_by_event_id.get(event.id, []),
            )
        )

    return AdminReviewCaseDetailRead.model_validate(review_case).model_copy(
        update={
            "finding_summary": build_review_case_finding_summary(signals, findings),
            "target_summary": get_review_case_target_summary(db, review_case),
            "assignee_display_name": (
                get_user_display_name(assignee, fallback="Admin")
                if assignee is not None
                else None
            ),
            "assignee_is_eligible": (
                user_is_active_admin(assignee)
                if review_case.assigned_to_user_id is not None
                else None
            ),
            "findings": [
                AdminContentModerationFindingRead.model_validate(finding)
                for finding in findings
            ],
            "signals": [
                AdminReviewSignalRead.model_validate(signal) for signal in signals
            ],
            "events": [
                AdminReviewCaseEventRead.model_validate(event) for event in events
            ],
            "notes": [
                serialize_review_case_note_read(note, author_by_id) for note in notes
            ],
            "linked_cases": [
                AdminReviewLinkedCaseRead(
                    id=linked.id,
                    case_status=linked.case_status,
                    case_version=linked.case_version,
                    priority=linked.priority,
                    relation=(
                        "merged_into"
                        if linked.id == review_case.merged_into_case_id
                        else "merged_from"
                    ),
                )
                for linked in linked_cases
            ],
            "resolution_references": [
                AdminReviewResolutionReferenceRead.model_validate(reference)
                for reference in resolution_references
            ],
            "resolution_history": resolution_history,
        }
    )


def build_case_list_response(
    db: Session,
    *,
    cases: list[AdminReviewCase],
    offset: int,
    limit: int,
    next_cursor: str | None,
    has_more: bool,
) -> AdminReviewCaseListRead:
    case_ids = [review_case.id for review_case in cases]
    signals_by_case_id: dict[uuid.UUID, list[AdminReviewSignal]] = {
        case_id: [] for case_id in case_ids
    }
    findings_by_case_id: dict[uuid.UUID, list[AdminContentModerationFinding]] = {
        case_id: [] for case_id in case_ids
    }
    if case_ids:
        findings = db.scalars(
            select(AdminContentModerationFinding)
            .where(AdminContentModerationFinding.review_case_id.in_(case_ids))
            .order_by(
                AdminContentModerationFinding.created_at.asc(),
                AdminContentModerationFinding.id.asc(),
            )
        ).all()
        for finding in findings:
            if finding.review_case_id in findings_by_case_id:
                findings_by_case_id[finding.review_case_id].append(finding)
        signals = db.scalars(
            select(AdminReviewSignal)
            .where(AdminReviewSignal.review_case_id.in_(case_ids))
            .order_by(AdminReviewSignal.created_at.asc(), AdminReviewSignal.id.asc())
        ).all()
        for signal in signals:
            if signal.review_case_id in signals_by_case_id:
                signals_by_case_id[signal.review_case_id].append(signal)
    target_summaries = build_review_case_target_summaries(db, cases)
    assignee_ids = {
        review_case.assigned_to_user_id
        for review_case in cases
        if review_case.assigned_to_user_id is not None
    }
    assignees_by_id = (
        {
            user.id: user
            for user in db.scalars(select(User).where(User.id.in_(assignee_ids))).all()
        }
        if assignee_ids
        else {}
    )

    return AdminReviewCaseListRead(
        cases=[
            serialize_review_case_read(
                review_case,
                signals_by_case_id.get(review_case.id, []),
                findings_by_case_id.get(review_case.id, []),
                target_summaries.get(review_case.id),
                assignees_by_id.get(review_case.assigned_to_user_id),
            )
            for review_case in cases
        ],
        total_count=None,
        offset=offset,
        limit=limit,
        next_cursor=next_cursor,
        has_more=has_more,
    )


def list_review_cases(
    db: Session,
    *,
    viewer_user: User,
    case_status: str | None = None,
    case_category: str | None = None,
    target_type: str | None = None,
    offset: int = 0,
    limit: int = 24,
    cursor: str | None = None,
    assignment: str = "all",
) -> AdminReviewCaseListRead:
    require_review_read_access(viewer_user)
    normalized_status: str | None = None
    normalized_category: str | None = None
    normalized_target_type = normalize_review_case_list_target_type(target_type)
    normalized_assignment = str(assignment or "").strip().lower()
    if normalized_assignment not in {"all", "mine", "unassigned"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="assignment is not supported.",
        )
    cursor_payload = decode_admin_review_case_list_cursor(cursor)

    statement = select(AdminReviewCase)
    if case_status is not None:
        normalized_status = case_status.strip().lower()
        if normalized_status not in VALID_CASE_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="case_status is not supported.",
            )
        statement = statement.where(AdminReviewCase.case_status == normalized_status)
    if case_category is not None:
        normalized_category = normalize_case_category(case_category)
        statement = statement.where(
            AdminReviewCase.case_category == normalized_category
        )
    if normalized_target_type == REVIEW_CASE_LIST_CONTENT_TARGETS:
        statement = statement.where(
            AdminReviewCase.case_type.in_(("community_game", "need_a_sub"))
        )
    elif normalized_target_type == "need_a_sub":
        statement = statement.where(AdminReviewCase.case_type == "need_a_sub")
    elif normalized_target_type == "community_game":
        statement = statement.where(AdminReviewCase.case_type == "community_game")
    if normalized_assignment == "mine":
        statement = statement.where(
            AdminReviewCase.assigned_to_user_id == viewer_user.id
        )
    elif normalized_assignment == "unassigned":
        statement = statement.where(AdminReviewCase.assigned_to_user_id.is_(None))

    actionable_open_condition = build_open_content_review_case_actionable_condition()
    if normalized_status in CASE_ACTIVE_STATUSES:
        statement = statement.where(actionable_open_condition)
    elif normalized_status is None:
        statement = statement.where(
            or_(
                ~AdminReviewCase.case_status.in_(CASE_ACTIVE_STATUSES),
                actionable_open_condition,
            )
        )

    validate_admin_review_case_list_cursor_context(
        cursor_payload,
        case_status=normalized_status,
        case_category=normalized_category,
        target_type=normalized_target_type,
        assignment=normalized_assignment,
        viewer_user_id=viewer_user.id,
    )
    if cursor_payload is not None:
        statement = statement.where(
            build_admin_review_case_list_cursor_filter(cursor_payload)
        )

    statement = statement.order_by(
        AdminReviewCase.updated_at.desc(),
        AdminReviewCase.id.desc(),
    )
    if cursor_payload is None:
        statement = statement.offset(offset)

    rows = list(db.scalars(statement.limit(limit + 1)).all())
    cases = rows[:limit]
    has_more = len(rows) > limit
    next_cursor = None
    if has_more and cases:
        next_cursor = encode_admin_review_case_list_cursor(
            review_case=cases[-1],
            case_status=normalized_status,
            case_category=normalized_category,
            target_type=normalized_target_type,
            assignment=normalized_assignment,
            viewer_user_id=viewer_user.id,
        )

    return build_case_list_response(
        db,
        cases=cases,
        offset=offset,
        limit=limit,
        next_cursor=next_cursor,
        has_more=has_more,
    )


def get_review_case_detail(
    db: Session,
    *,
    review_case_id: uuid.UUID,
    viewer_user: User,
) -> AdminReviewCaseDetailRead:
    require_review_read_access(viewer_user)
    return serialize_review_case_detail(db, get_review_case_or_404(db, review_case_id))


def find_open_case_for_signal(
    db: Session,
    *,
    target_data: dict[str, uuid.UUID | None],
    case_category: str,
    allow_reference_inserts: bool = False,
) -> AdminReviewCase | None:
    primary = primary_target(target_data)
    if primary is None:
        return None
    field_name, target_id = primary
    case_type = infer_case_type(db, target_data)
    statement = (
        select(AdminReviewCase)
        .where(
            AdminReviewCase.case_status.in_(CASE_ACTIVE_STATUSES),
            AdminReviewCase.case_type == case_type,
            AdminReviewCase.case_category == case_category,
            getattr(AdminReviewCase, field_name) == target_id,
        )
        .order_by(AdminReviewCase.created_at.asc(), AdminReviewCase.id.asc())
        .limit(1)
    )
    active_case = db.scalar(
        statement.execution_options(populate_existing=True).with_for_update(
            key_share=allow_reference_inserts
        )
    )
    if active_case is not None:
        return active_case

    return None


def find_open_case_for_admin_action(
    db: Session,
    admin_action: AdminAction,
    *,
    case_category: str,
) -> AdminReviewCase | None:
    target_data = target_data_from_object(admin_action)
    primary = primary_target(target_data)
    if primary is None:
        return None
    field_name, target_id = primary
    case_type_by_target = {
        "target_game_id": "community_game",
        "target_sub_post_id": "need_a_sub",
    }
    case_type = case_type_by_target.get(field_name)
    if case_type is None:
        return None
    if (
        lock_primary_target(
            db,
            target_field_name=field_name,
            target_id=target_id,
        )
        is None
    ):
        return None
    return db.scalar(
        select(AdminReviewCase)
        .where(
            AdminReviewCase.case_status.in_(CASE_ACTIVE_STATUSES),
            AdminReviewCase.case_type == case_type,
            AdminReviewCase.case_category == normalize_case_category(case_category),
            getattr(AdminReviewCase, field_name) == target_id,
        )
        .order_by(AdminReviewCase.created_at.asc(), AdminReviewCase.id.asc())
        .execution_options(populate_existing=True)
        .with_for_update()
        .limit(1)
    )


def validate_automatic_content_lifecycle_transition(
    *,
    target_type: str,
    lifecycle_action: str,
    previous_target_state: str | None,
    new_target_state: str | None,
    trigger_actor_type: str,
    trigger_actor_user_id: uuid.UUID | None,
    closed_by_user_id: uuid.UUID | None,
    closure_outcome: str,
    admin_action: AdminAction | None,
) -> None:
    transition = AUTOMATIC_CONTENT_LIFECYCLE_TRANSITIONS.get(
        (target_type, lifecycle_action)
    )
    if transition is None:
        raise ValueError("Automatic closure lifecycle action is not supported.")
    if (
        previous_target_state != transition.previous_state
        or new_target_state != transition.new_state
        or trigger_actor_type not in transition.trigger_actor_types
        or closure_outcome != transition.closure_outcome
    ):
        raise ValueError("Automatic closure lifecycle transition is invalid.")

    actor_requires_user = trigger_actor_type in {"admin", "host", "owner"}
    if actor_requires_user != (trigger_actor_user_id is not None):
        raise ValueError("Automatic closure trigger actor attribution is invalid.")
    expected_closed_by_user_id = (
        trigger_actor_user_id if trigger_actor_type == "admin" else None
    )
    if closed_by_user_id != expected_closed_by_user_id:
        raise ValueError("Automatic closure resolver attribution is invalid.")

    if transition.linked_action_type is None:
        if admin_action is not None:
            raise ValueError("Automatic closure does not accept a linked action.")
        return
    if (
        admin_action is None
        or admin_action.action_type != transition.linked_action_type
    ):
        raise ValueError("Automatic closure linked action is invalid.")
    if admin_action.admin_user_id != trigger_actor_user_id:
        raise ValueError("Automatic closure action actor is invalid.")


def validate_automatic_content_lifecycle_target_state(
    *,
    target: Game | SubPost,
    target_type: str,
    new_target_state: str | None,
) -> None:
    if target_type == "community_game":
        if not isinstance(target, Game) or target.game_type != "community":
            raise ValueError("Automatic closure requires a Community Game target.")
        if new_target_state == "soft_deleted":
            if target.deleted_at is None:
                raise ValueError("Automatic closure target state is not applied.")
        elif target.game_status != new_target_state:
            raise ValueError("Automatic closure target state is not applied.")
        return
    if not isinstance(target, SubPost) or target.post_status != new_target_state:
        raise ValueError("Automatic closure target state is not applied.")


def close_open_content_moderation_case_for_lifecycle(
    db: Session,
    *,
    target_field_name: str,
    target_id: uuid.UUID,
    closure_outcome: str,
    closure_reason: str,
    lifecycle_action: str,
    target_type: str,
    trigger_actor_type: str,
    trigger_actor_user_id: uuid.UUID | None = None,
    closed_by_user_id: uuid.UUID | None = None,
    admin_action: AdminAction | None = None,
    previous_target_state: str | None = None,
    new_target_state: str | None = None,
    closed_at: datetime | None = None,
) -> AdminReviewCase | None:
    if target_field_name not in REVIEW_TARGET_FIELDS:
        raise ValueError("target_field_name is not a review target field.")
    case_type_by_target = {
        "target_game_id": "community_game",
        "target_sub_post_id": "need_a_sub",
    }
    case_type = case_type_by_target.get(target_field_name)
    if case_type is None:
        raise ValueError("Automatic review-case closure requires a content target.")
    if target_type != case_type:
        raise ValueError("Automatic closure target type does not match its target.")
    validate_automatic_content_lifecycle_transition(
        target_type=target_type,
        lifecycle_action=lifecycle_action,
        previous_target_state=previous_target_state,
        new_target_state=new_target_state,
        trigger_actor_type=trigger_actor_type,
        trigger_actor_user_id=trigger_actor_user_id,
        closed_by_user_id=closed_by_user_id,
        closure_outcome=closure_outcome,
        admin_action=admin_action,
    )
    reason = normalize_limited_text(closure_reason, "closure_reason", 2000)

    target = lock_primary_target(
        db,
        target_field_name=target_field_name,
        target_id=target_id,
    )
    if target is None:
        return None
    validate_automatic_content_lifecycle_target_state(
        target=target,
        target_type=target_type,
        new_target_state=new_target_state,
    )
    if isinstance(target, Game):
        if is_game_content_review_actionable(target):
            return None
    elif isinstance(target, SubPost):
        if is_sub_post_content_review_actionable(target):
            return None
    else:
        raise TypeError("Automatic review-case closure requires a content target.")

    review_case = db.scalar(
        select(AdminReviewCase)
        .where(
            AdminReviewCase.case_status.in_(CASE_ACTIVE_STATUSES),
            AdminReviewCase.case_type == case_type,
            AdminReviewCase.case_category == CONTENT_MODERATION_CASE_CATEGORY,
            getattr(AdminReviewCase, target_field_name) == target_id,
        )
        .order_by(AdminReviewCase.created_at.asc(), AdminReviewCase.id.asc())
        .limit(1)
        .execution_options(populate_existing=True)
        .with_for_update()
    )
    if review_case is None:
        return None

    now = closed_at or datetime.now(timezone.utc)
    before = {
        "case_status": review_case.case_status,
        "closure_outcome": review_case.closure_outcome,
    }
    review_case.case_status = "closed"
    review_case.closure_outcome = closure_outcome
    review_case.closure_reason = reason
    review_case.closure_mode = "automatic"
    review_case.closure_rule_id = TARGET_LIFECYCLE_RULE_ID
    review_case.closure_rule_version = TARGET_LIFECYCLE_RULE_VERSION
    review_case.closed_by_user_id = closed_by_user_id
    review_case.closed_at = now
    previous_assignee_id = review_case.assigned_to_user_id
    review_case.assigned_to_user_id = None
    review_case.assigned_at = None
    db.add(review_case)

    if admin_action is not None and admin_action.target_review_case_id is None:
        admin_action.target_review_case_id = review_case.id
        db.add(admin_action)

    closure_event = create_case_event(
        db,
        review_case_id=review_case.id,
        event_type="closed",
        actor_kind="automation",
        automation_rule_id=TARGET_LIFECYCLE_RULE_ID,
        automation_rule_version=TARGET_LIFECYCLE_RULE_VERSION,
        trigger_actor_user_id=trigger_actor_user_id,
        admin_action_id=admin_action.id if admin_action is not None else None,
        event_metadata={
            "closure_mode": "automatic",
            "reason": reason,
            "closure_source": "target_lifecycle",
            "lifecycle_action": lifecycle_action,
            "target_type": target_type,
            "target_id": target_id,
            "previous_target_state": previous_target_state,
            "new_target_state": new_target_state,
            "trigger_actor_type": trigger_actor_type,
            "trigger_actor_user_id": trigger_actor_user_id,
            "closed_by_user_id": closed_by_user_id,
            "previous_assignee_id": previous_assignee_id,
            "linked_admin_action_id": (
                admin_action.id if admin_action is not None else None
            ),
            "before": before,
            "after": {
                "case_status": "closed",
                "closure_outcome": closure_outcome,
            },
        },
        created_at=now,
    )
    append_resolution_references(
        db,
        review_case=review_case,
        closure_event=closure_event,
    )
    return review_case


def close_open_content_moderation_case_for_sub_post_lifecycle(
    db: Session,
    *,
    sub_post_id: uuid.UUID,
    closure_outcome: str,
    closure_reason: str,
    lifecycle_action: str,
    trigger_actor_type: str,
    trigger_actor_user_id: uuid.UUID | None = None,
    closed_by_user_id: uuid.UUID | None = None,
    admin_action: AdminAction | None = None,
    previous_post_status: str | None = None,
    new_post_status: str | None = None,
    closed_at: datetime | None = None,
) -> AdminReviewCase | None:
    return close_open_content_moderation_case_for_lifecycle(
        db,
        target_field_name="target_sub_post_id",
        target_id=sub_post_id,
        closure_outcome=closure_outcome,
        closure_reason=closure_reason,
        lifecycle_action=lifecycle_action,
        target_type="need_a_sub",
        trigger_actor_type=trigger_actor_type,
        trigger_actor_user_id=trigger_actor_user_id,
        closed_by_user_id=closed_by_user_id,
        admin_action=admin_action,
        previous_target_state=previous_post_status,
        new_target_state=new_post_status,
        closed_at=closed_at,
    )


def close_open_content_moderation_case_for_game_lifecycle(
    db: Session,
    *,
    game_id: uuid.UUID,
    closure_outcome: str,
    closure_reason: str,
    lifecycle_action: str,
    trigger_actor_type: str,
    trigger_actor_user_id: uuid.UUID | None = None,
    closed_by_user_id: uuid.UUID | None = None,
    admin_action: AdminAction | None = None,
    previous_game_status: str | None = None,
    new_game_status: str | None = None,
    closed_at: datetime | None = None,
) -> AdminReviewCase | None:
    return close_open_content_moderation_case_for_lifecycle(
        db,
        target_field_name="target_game_id",
        target_id=game_id,
        closure_outcome=closure_outcome,
        closure_reason=closure_reason,
        lifecycle_action=lifecycle_action,
        target_type="community_game",
        trigger_actor_type=trigger_actor_type,
        trigger_actor_user_id=trigger_actor_user_id,
        closed_by_user_id=closed_by_user_id,
        admin_action=admin_action,
        previous_target_state=previous_game_status,
        new_target_state=new_game_status,
        closed_at=closed_at,
    )


def get_existing_signal_by_idempotency_key(
    db: Session,
    *,
    source: str,
    idempotency_key: str,
) -> AdminReviewSignal | None:
    return db.scalar(
        select(AdminReviewSignal)
        .where(
            AdminReviewSignal.source == source,
            AdminReviewSignal.idempotency_key == idempotency_key,
        )
        .order_by(AdminReviewSignal.created_at.desc(), AdminReviewSignal.id.desc())
        .limit(1)
    )


def build_case_scoped_signal_idempotency_key(
    base_key: str,
    review_case_id: uuid.UUID,
) -> str:
    return f"{base_key}:case:{review_case_id}"


def build_content_moderation_case_title(case_type: str) -> str:
    if case_type == "community_game":
        return "Community Game needs review"
    if case_type == "need_a_sub":
        return "Need a Sub post needs review"
    return "Content needs review"


def build_content_moderation_case_summary(case_type: str) -> str:
    if case_type == "community_game":
        return "Review moderation findings attached to this Community Game."
    if case_type == "need_a_sub":
        return "Review moderation findings attached to this Need a Sub post."
    return "Review moderation findings attached to this target."


def case_category_for_internal_signal(category: str, source: str) -> str:
    if category == "chat_moderation" or source == "chat_moderation":
        return "chat_moderation"
    return CONTENT_MODERATION_CASE_CATEGORY


def build_internal_signal_case_title(case_category: str, case_type: str) -> str:
    if case_category == "chat_moderation":
        if case_type == "community_game":
            return "Community Game chat needs review"
        if case_type == "need_a_sub":
            return "Need a Sub chat needs review"
        return "Chat needs review"
    return build_content_moderation_case_title(case_type)


def build_internal_signal_case_summary(case_category: str, case_type: str) -> str:
    if case_category == "chat_moderation":
        if case_type == "community_game":
            return "Review chat moderation signals attached to this Community Game."
        if case_type == "need_a_sub":
            return "Review chat moderation signals attached to this Need a Sub post."
        return "Review chat moderation signals attached to this case."
    return build_content_moderation_case_summary(case_type)


def create_internal_review_signal(
    db: Session,
    *,
    signal_category: str,
    source: str,
    priority: str,
    title: str,
    summary: str,
    target_data: dict[str, uuid.UUID | None],
    metadata: dict[str, Any] | None,
    idempotency_key: str,
    _retrying_after_conflict: bool = False,
) -> tuple[AdminReviewCase, AdminReviewSignal, bool, bool]:
    category = normalize_signal_category(signal_category)
    normalized_source = normalize_source(source)
    case_category = case_category_for_internal_signal(category, normalized_source)
    normalized_priority = normalize_priority(priority)
    normalized_title = normalize_limited_text(title, "title", 180)
    normalized_summary = normalize_limited_text(summary, "summary", 2000)
    normalized_metadata = normalize_metadata(metadata)
    base_idempotency_key = normalize_required_idempotency_key(idempotency_key)
    normalized_targets = copy_targets(target_data)
    validate_target_references(db, normalized_targets)
    primary = primary_target(normalized_targets)
    if primary is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Review signals require a primary target.",
        )
    if (
        lock_primary_target(
            db,
            target_field_name=primary[0],
            target_id=primary[1],
        )
        is None
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=TARGET_NOT_FOUND_DETAIL[primary[0]],
        )

    now = datetime.now(timezone.utc)
    review_case = find_open_case_for_signal(
        db,
        target_data=normalized_targets,
        case_category=case_category,
    )
    created_case = review_case is None

    try:
        if review_case is None:
            case_type = infer_case_type(db, normalized_targets)
            review_case = AdminReviewCase(
                id=uuid.uuid4(),
                case_type=case_type,
                case_status="open",
                case_category=case_category,
                priority=normalized_priority,
                title=build_internal_signal_case_title(case_category, case_type),
                summary=build_internal_signal_case_summary(case_category, case_type),
                case_version=1,
                creation_reason="chat_moderation_detection",
                opened_by_user_id=None,
                created_at=now,
                updated_at=now,
                **copy_targets(normalized_targets),
            )
            db.add(review_case)
            db.flush()

        scoped_idempotency_key = build_case_scoped_signal_idempotency_key(
            base_idempotency_key,
            review_case.id,
        )
        existing_signal = get_existing_signal_by_idempotency_key(
            db,
            source=normalized_source,
            idempotency_key=scoped_idempotency_key,
        )
        if existing_signal is not None:
            existing_targets = target_data_from_object(existing_signal)
            if (
                existing_signal.signal_category != category
                or existing_signal.source != normalized_source
                or existing_targets != normalized_targets
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="idempotency_key was already used for a different signal.",
                )
            previous_metadata = dict(existing_signal.metadata_ or {})
            was_current_match = previous_metadata.get("current_match") is True
            becomes_current_match = (
                normalized_metadata is not None
                and normalized_metadata.get("current_match") is True
            )
            if normalized_metadata is not None:
                if was_current_match != becomes_current_match:
                    apply_review_signal_current_state(
                        db,
                        signal_id=existing_signal.id,
                        metadata=normalized_metadata,
                        changed_at=now,
                    )
                else:
                    existing_signal.metadata_ = normalized_metadata
                    existing_signal.updated_at = now
                    db.add(existing_signal)
            db.commit()
            db.refresh(review_case)
            db.refresh(existing_signal)
            return review_case, existing_signal, False, True

        if not created_case:
            priority_before = review_case.priority
            if PRIORITY_RANK[normalized_priority] > PRIORITY_RANK[priority_before]:
                review_case.priority = normalized_priority
            db.add(review_case)
        else:
            priority_before = review_case.priority

        signal = AdminReviewSignal(
            id=uuid.uuid4(),
            review_case_id=review_case.id,
            signal_category=category,
            source=normalized_source,
            signal_status="attached",
            priority=normalized_priority,
            title=normalized_title,
            summary=normalized_summary,
            metadata_=normalized_metadata,
            idempotency_key=scoped_idempotency_key,
            created_by_user_id=None,
            created_at=now,
            updated_at=now,
            **copy_targets(normalized_targets),
        )
        db.add(signal)
        db.flush()

        if created_case:
            create_case_event(
                db,
                review_case_id=review_case.id,
                event_type="case_created",
                actor_user_id=None,
                signal_id=signal.id,
                automation_rule_id=SOURCE_RECONCILIATION_RULE_ID,
                automation_rule_version=SOURCE_RECONCILIATION_RULE_VERSION,
                event_metadata={"source": normalized_source},
                created_at=now,
            )

        create_case_event(
            db,
            review_case_id=review_case.id,
            event_type="signal_attached",
            actor_user_id=None,
            signal_id=signal.id,
            automation_rule_id=SOURCE_RECONCILIATION_RULE_ID,
            automation_rule_version=SOURCE_RECONCILIATION_RULE_VERSION,
            event_metadata={
                "created_case": created_case,
                "source": normalized_source,
                "priority_before": priority_before,
                "priority_after": review_case.priority,
            },
            created_at=now + timedelta(microseconds=1) if created_case else now,
        )

        db.commit()
        db.refresh(review_case)
        db.refresh(signal)
    except IntegrityError as exc:
        db.rollback()
        if not _retrying_after_conflict and is_retryable_chat_review_case_creation_race(
            exc
        ):
            return create_internal_review_signal(
                db,
                signal_category=signal_category,
                source=source,
                priority=priority,
                title=title,
                summary=summary,
                target_data=target_data,
                metadata=metadata,
                idempotency_key=idempotency_key,
                _retrying_after_conflict=True,
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Review signal could not be created.",
        ) from exc

    return review_case, signal, created_case, False


def get_existing_review_action(
    db: Session,
    *,
    action_type: str,
    admin_user_id: uuid.UUID,
    review_case_id: uuid.UUID,
    idempotency_key: str,
) -> AdminAction | None:
    return db.scalar(
        select(AdminAction)
        .where(
            AdminAction.action_type == action_type,
            AdminAction.admin_user_id == admin_user_id,
            AdminAction.target_review_case_id == review_case_id,
            AdminAction.idempotency_key == idempotency_key,
        )
        .order_by(AdminAction.created_at.desc(), AdminAction.id.desc())
        .limit(1)
    )


def note_hash(body: str) -> str:
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def add_review_case_note(
    db: Session,
    *,
    review_case_id: uuid.UUID,
    admin_user: User,
    payload: AdminReviewCaseNoteCreate,
    _replaying_after_conflict: bool = False,
) -> AdminReviewCaseNoteResultRead:
    require_review_manage_access(admin_user)
    body = normalize_limited_text(
        payload.body,
        "body",
        MAX_REVIEW_CASE_NOTE_BODY_LENGTH,
    )
    idempotency_key = normalize_required_idempotency_key(payload.idempotency_key)
    body_hash = note_hash(body)
    request_fingerprint = review_case_request_fingerprint(
        {
            "body_hash": body_hash,
            "corrects_note_id": payload.corrects_note_id,
            "expected_case_version": payload.expected_case_version,
        }
    )

    existing_action = get_existing_review_action(
        db,
        action_type="add_review_case_note",
        admin_user_id=admin_user.id,
        review_case_id=review_case_id,
        idempotency_key=idempotency_key,
    )
    if existing_action is not None:
        metadata = existing_action.metadata_ or {}
        if metadata.get("request_fingerprint") != request_fingerprint:
            review_case = get_review_case_or_404(db, review_case_id)
            raise review_case_conflict("review_case_idempotency_conflict", review_case)
        note = db.get(AdminReviewCaseNote, uuid.UUID(metadata["note_id"]))
        if note is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Review note audit exists but note is missing.",
            )
        review_case = get_review_case_or_404(db, review_case_id)
        return AdminReviewCaseNoteResultRead(
            review_case=serialize_review_case_detail(db, review_case),
            note=serialize_review_case_note_read(note, {admin_user.id: admin_user}),
            audit_action_id=existing_action.id,
            idempotent_replay=True,
            applied_case_version=int(metadata["applied_case_version"]),
            resulting_case_version=int(metadata["resulting_case_version"]),
        )

    review_case, _target = lock_review_case_with_target(db, review_case_id)
    existing_action = get_existing_review_action(
        db,
        action_type="add_review_case_note",
        admin_user_id=admin_user.id,
        review_case_id=review_case_id,
        idempotency_key=idempotency_key,
    )
    if existing_action is not None:
        db.rollback()
        return add_review_case_note(
            db,
            review_case_id=review_case_id,
            admin_user=admin_user,
            payload=payload,
            _replaying_after_conflict=True,
        )
    require_expected_case_version(review_case, payload.expected_case_version)
    if review_case.case_status == "closed":
        raise review_case_conflict("review_case_transition_conflict", review_case)
    note_count = db.scalar(
        select(func.count(AdminReviewCaseNote.id)).where(
            AdminReviewCaseNote.review_case_id == review_case.id
        )
    )
    if (note_count or 0) >= MAX_REVIEW_CASE_NOTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Review cases can have at most {MAX_REVIEW_CASE_NOTES} notes.",
        )

    corrected_note = None
    if payload.corrects_note_id is not None:
        corrected_note = db.scalar(
            select(AdminReviewCaseNote)
            .where(AdminReviewCaseNote.id == payload.corrects_note_id)
            .execution_options(populate_existing=True)
            .with_for_update()
        )
        if corrected_note is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="corrects_note_id does not identify a review-case note.",
            )
        if corrected_note.review_case_id != review_case.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A correction must reference a note from the same case.",
            )

    now = datetime.now(timezone.utc)
    note = AdminReviewCaseNote(
        id=uuid.uuid4(),
        review_case_id=review_case.id,
        author_user_id=admin_user.id,
        body=body,
        corrects_note_id=(corrected_note.id if corrected_note is not None else None),
        created_at=now,
        updated_at=now,
    )
    db.add(note)
    db.flush()
    admin_action = record_admin_action(
        db,
        admin_user_id=admin_user.id,
        action_type="add_review_case_note",
        target_review_case_id=review_case.id,
        reason="Internal review note added.",
        metadata={
            "source": "review_case",
            "note_id": str(note.id),
            "note_hash": body_hash,
            "note_length": len(body),
            "corrects_note_id": (
                str(corrected_note.id) if corrected_note is not None else None
            ),
            "request_fingerprint": request_fingerprint,
            "applied_case_version": payload.expected_case_version,
            "resulting_case_version": payload.expected_case_version + 1,
        },
        idempotency_key=idempotency_key,
        created_at=now,
        **copy_targets(target_data_from_object(review_case)),
    )
    event = create_case_event(
        db,
        review_case_id=review_case.id,
        event_type="note_added",
        actor_user_id=admin_user.id,
        admin_action_id=admin_action.id,
        note_id=note.id,
        event_metadata={
            "corrects_note_id": (
                str(corrected_note.id) if corrected_note is not None else None
            )
        },
        created_at=now,
    )
    metadata = dict(admin_action.metadata_ or {})
    metadata["event_id"] = str(event.id)
    admin_action.metadata_ = metadata

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if (
            not _replaying_after_conflict
            and review_integrity_constraint_name(exc)
            == "uq_admin_actions_review_case_idempotency"
        ):
            return add_review_case_note(
                db,
                review_case_id=review_case_id,
                admin_user=admin_user,
                payload=payload,
                _replaying_after_conflict=True,
            )
        raise
    db.refresh(review_case)
    db.refresh(note)
    db.refresh(admin_action)
    return AdminReviewCaseNoteResultRead(
        review_case=serialize_review_case_detail(db, review_case),
        note=serialize_review_case_note_read(note, {admin_user.id: admin_user}),
        audit_action_id=admin_action.id,
        idempotent_replay=False,
        applied_case_version=payload.expected_case_version,
        resulting_case_version=review_case.case_version,
    )


def build_review_case_action_replay(
    db: Session,
    *,
    review_case_id: uuid.UUID,
    action: AdminAction,
) -> AdminReviewCaseActionResultRead:
    review_case = get_review_case_or_404(db, review_case_id)
    metadata = action.metadata_ or {}
    return AdminReviewCaseActionResultRead(
        review_case=serialize_review_case_detail(db, review_case),
        audit_action_id=action.id,
        idempotent_replay=True,
        applied_case_version=int(metadata["applied_case_version"]),
        resulting_case_version=int(metadata["resulting_case_version"]),
    )


def close_review_case(
    db: Session,
    *,
    review_case_id: uuid.UUID,
    admin_user: User,
    payload: AdminReviewCaseClose,
    _replaying_after_conflict: bool = False,
) -> AdminReviewCaseActionResultRead:
    require_review_manage_access(admin_user)
    outcome = str(payload.outcome or "").strip().lower()
    if outcome not in VALID_CLOSURE_OUTCOMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="outcome is not supported.",
        )
    reason = normalize_limited_text(payload.reason, "reason", 1000)
    idempotency_key = normalize_required_idempotency_key(payload.idempotency_key)
    request_fingerprint = review_case_request_fingerprint(
        {
            "outcome": outcome,
            "reason": reason,
            "expected_case_version": payload.expected_case_version,
        }
    )

    existing_action = get_existing_review_action(
        db,
        action_type="close_review_case",
        admin_user_id=admin_user.id,
        review_case_id=review_case_id,
        idempotency_key=idempotency_key,
    )
    if existing_action is not None:
        metadata = existing_action.metadata_ or {}
        if metadata.get("request_fingerprint") != request_fingerprint:
            review_case = get_review_case_or_404(db, review_case_id)
            raise review_case_conflict("review_case_idempotency_conflict", review_case)
        return build_review_case_action_replay(
            db,
            review_case_id=review_case_id,
            action=existing_action,
        )

    review_case, _target = lock_review_case_with_target(db, review_case_id)
    existing_action = get_existing_review_action(
        db,
        action_type="close_review_case",
        admin_user_id=admin_user.id,
        review_case_id=review_case_id,
        idempotency_key=idempotency_key,
    )
    if existing_action is not None:
        db.rollback()
        return close_review_case(
            db,
            review_case_id=review_case_id,
            admin_user=admin_user,
            payload=payload,
            _replaying_after_conflict=True,
        )
    require_expected_case_version(review_case, payload.expected_case_version)
    if review_case.case_status == "closed":
        raise review_case_conflict("review_case_transition_conflict", review_case)
    current_assignee = eligible_admin_by_id(
        db, review_case.assigned_to_user_id, lock=True
    )
    if current_assignee is not None and current_assignee.id != admin_user.id:
        raise review_case_conflict("review_case_assignment_conflict", review_case)
    if outcome == "enforcement_applied":
        aggregate_case_ids = review_case_aggregate_ids(db, review_case.id)
        enforcement_action_id = db.scalar(
            select(AdminAction.id)
            .where(
                AdminAction.target_review_case_id.in_(aggregate_case_ids),
                ~AdminAction.action_type.in_(REVIEW_WORKFLOW_ACTION_TYPES),
                exists(
                    select(AdminReviewCaseEvent.id).where(
                        AdminReviewCaseEvent.admin_action_id == AdminAction.id,
                        AdminReviewCaseEvent.review_case_id.in_(aggregate_case_ids),
                        AdminReviewCaseEvent.event_type == "enforcement_action_linked",
                    )
                ),
            )
            .order_by(AdminAction.created_at.desc(), AdminAction.id.desc())
            .limit(1)
        )
        if enforcement_action_id is None:
            raise review_case_conflict("review_case_transition_conflict", review_case)

    now = datetime.now(timezone.utc)
    before = {
        "case_status": review_case.case_status,
        "closure_outcome": review_case.closure_outcome,
    }
    review_case.case_status = "closed"
    review_case.closure_outcome = outcome
    review_case.closure_reason = reason
    review_case.closure_mode = "manual"
    review_case.closure_rule_id = None
    review_case.closure_rule_version = None
    review_case.closed_by_user_id = admin_user.id
    review_case.closed_at = now
    previous_assignee_id = review_case.assigned_to_user_id
    review_case.assigned_to_user_id = None
    review_case.assigned_at = None
    after = {
        "case_status": review_case.case_status,
        "closure_outcome": outcome,
    }
    admin_action = record_admin_action(
        db,
        admin_user_id=admin_user.id,
        action_type="close_review_case",
        target_review_case_id=review_case.id,
        reason=reason,
        metadata={
            "source": "review_case_closure",
            "before": before,
            "after": after,
            "closure_outcome": outcome,
            "request_fingerprint": request_fingerprint,
            "applied_case_version": payload.expected_case_version,
            "resulting_case_version": payload.expected_case_version + 1,
            "previous_assignee_id": (
                str(previous_assignee_id) if previous_assignee_id is not None else None
            ),
        },
        idempotency_key=idempotency_key,
        created_at=now,
        **copy_targets(target_data_from_object(review_case)),
    )
    event = create_case_event(
        db,
        review_case_id=review_case.id,
        event_type="closed",
        actor_user_id=admin_user.id,
        admin_action_id=admin_action.id,
        event_metadata={
            "closure_mode": "manual",
            "reason": reason,
            "target_type": review_case.case_type,
            "target_id": discover_case_primary_target(review_case)[1],
            "closed_by_user_id": admin_user.id,
            "previous_assignee_id": previous_assignee_id,
            "before": before,
            "after": after,
        },
        created_at=now,
    )
    append_resolution_references(
        db,
        review_case=review_case,
        closure_event=event,
    )
    metadata = dict(admin_action.metadata_ or {})
    metadata["event_id"] = str(event.id)
    admin_action.metadata_ = metadata

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if (
            not _replaying_after_conflict
            and review_integrity_constraint_name(exc)
            == "uq_admin_actions_review_case_idempotency"
        ):
            return close_review_case(
                db,
                review_case_id=review_case_id,
                admin_user=admin_user,
                payload=payload,
                _replaying_after_conflict=True,
            )
        raise
    db.refresh(review_case)
    db.refresh(admin_action)
    return AdminReviewCaseActionResultRead(
        review_case=serialize_review_case_detail(db, review_case),
        audit_action_id=admin_action.id,
        idempotent_replay=False,
        applied_case_version=payload.expected_case_version,
        resulting_case_version=review_case.case_version,
    )


def assign_review_case(
    db: Session,
    *,
    review_case_id: uuid.UUID,
    admin_user: User,
    payload: AdminReviewCaseAssignment,
) -> AdminReviewCaseActionResultRead:
    require_review_manage_access(admin_user)
    reason = normalize_limited_text(payload.reason, "reason", 1000)
    idempotency_key = normalize_required_idempotency_key(payload.idempotency_key)
    request_fingerprint = review_case_request_fingerprint(
        {
            "assignee_user_id": payload.assignee_user_id,
            "reason": reason,
            "expected_case_version": payload.expected_case_version,
        }
    )
    existing_action = get_existing_review_action(
        db,
        action_type="assign_review_case",
        admin_user_id=admin_user.id,
        review_case_id=review_case_id,
        idempotency_key=idempotency_key,
    )
    if existing_action is not None:
        if (existing_action.metadata_ or {}).get(
            "request_fingerprint"
        ) != request_fingerprint:
            raise review_case_conflict(
                "review_case_idempotency_conflict",
                get_review_case_or_404(db, review_case_id),
            )
        return build_review_case_action_replay(
            db, review_case_id=review_case_id, action=existing_action
        )

    review_case, _target = lock_review_case_with_target(db, review_case_id)
    existing_action = get_existing_review_action(
        db,
        action_type="assign_review_case",
        admin_user_id=admin_user.id,
        review_case_id=review_case_id,
        idempotency_key=idempotency_key,
    )
    if existing_action is not None:
        db.rollback()
        return assign_review_case(
            db,
            review_case_id=review_case_id,
            admin_user=admin_user,
            payload=payload,
        )
    require_expected_case_version(review_case, payload.expected_case_version)
    if review_case.case_status != "open":
        raise review_case_conflict("review_case_transition_conflict", review_case)

    next_assignee = None
    if payload.assignee_user_id is not None:
        next_assignee = eligible_admin_by_id(db, payload.assignee_user_id, lock=True)
        if next_assignee is None:
            raise review_case_conflict("review_case_assignment_conflict", review_case)
    if review_case.assigned_to_user_id == payload.assignee_user_id:
        raise review_case_conflict("review_case_transition_conflict", review_case)

    now = datetime.now(timezone.utc)
    previous_assignee_id = review_case.assigned_to_user_id
    review_case.assigned_to_user_id = (
        next_assignee.id if next_assignee is not None else None
    )
    review_case.assigned_at = now if next_assignee is not None else None
    admin_action = record_admin_action(
        db,
        admin_user_id=admin_user.id,
        action_type="assign_review_case",
        target_review_case_id=review_case.id,
        reason=reason,
        metadata={
            "source": "review_case_assignment",
            "request_fingerprint": request_fingerprint,
            "previous_assignee_id": (
                str(previous_assignee_id) if previous_assignee_id is not None else None
            ),
            "next_assignee_id": (
                str(next_assignee.id) if next_assignee is not None else None
            ),
            "applied_case_version": payload.expected_case_version,
            "resulting_case_version": payload.expected_case_version + 1,
        },
        idempotency_key=idempotency_key,
        created_at=now,
        **copy_targets(target_data_from_object(review_case)),
    )
    event = create_case_event(
        db,
        review_case_id=review_case.id,
        event_type="assignment_changed",
        actor_user_id=admin_user.id,
        admin_action_id=admin_action.id,
        event_metadata={
            "previous_assignee_id": (
                str(previous_assignee_id) if previous_assignee_id is not None else None
            ),
            "next_assignee_id": (
                str(next_assignee.id) if next_assignee is not None else None
            ),
        },
        created_at=now,
    )
    metadata = dict(admin_action.metadata_ or {})
    metadata["event_id"] = str(event.id)
    admin_action.metadata_ = metadata
    db.commit()
    db.refresh(review_case)
    return AdminReviewCaseActionResultRead(
        review_case=serialize_review_case_detail(db, review_case),
        audit_action_id=admin_action.id,
        idempotent_replay=False,
        applied_case_version=payload.expected_case_version,
        resulting_case_version=review_case.case_version,
    )


def case_target_is_actionable_for_reopen(
    review_case: AdminReviewCase,
    target: object,
) -> bool:
    if review_case.case_category == CONTENT_MODERATION_CASE_CATEGORY:
        if review_case.case_type == "community_game":
            return isinstance(target, Game) and is_game_content_review_actionable(
                target
            )
        if review_case.case_type == "need_a_sub":
            return isinstance(
                target, SubPost
            ) and is_sub_post_content_review_actionable(target)
        return False
    if review_case.case_category == CHAT_MODERATION_CASE_CATEGORY:
        if isinstance(target, Game):
            return target.deleted_at is None
        return isinstance(target, SubPost)
    return False


def find_other_open_case_for_identity(
    db: Session,
    review_case: AdminReviewCase,
) -> AdminReviewCase | None:
    target_field_name, target_id = discover_case_primary_target(review_case)
    return db.scalar(
        select(AdminReviewCase)
        .where(
            AdminReviewCase.id != review_case.id,
            AdminReviewCase.case_type == review_case.case_type,
            AdminReviewCase.case_category == review_case.case_category,
            AdminReviewCase.case_status == "open",
            getattr(AdminReviewCase, target_field_name) == target_id,
        )
        .order_by(AdminReviewCase.id.asc())
        .execution_options(populate_existing=True)
        .with_for_update()
        .limit(1)
    )


def reopen_review_case(
    db: Session,
    *,
    review_case_id: uuid.UUID,
    admin_user: User,
    payload: AdminReviewCaseReopen,
) -> AdminReviewCaseActionResultRead:
    require_review_manage_access(admin_user)
    reason = normalize_limited_text(payload.reason, "reason", 1000)
    idempotency_key = normalize_required_idempotency_key(payload.idempotency_key)
    request_fingerprint = review_case_request_fingerprint(
        {
            "reason": reason,
            "expected_case_version": payload.expected_case_version,
        }
    )
    existing_action = get_existing_review_action(
        db,
        action_type="reopen_review_case",
        admin_user_id=admin_user.id,
        review_case_id=review_case_id,
        idempotency_key=idempotency_key,
    )
    if existing_action is not None:
        if (existing_action.metadata_ or {}).get(
            "request_fingerprint"
        ) != request_fingerprint:
            raise review_case_conflict(
                "review_case_idempotency_conflict",
                get_review_case_or_404(db, review_case_id),
            )
        return build_review_case_action_replay(
            db, review_case_id=review_case_id, action=existing_action
        )

    review_case, target = lock_review_case_with_target(db, review_case_id)
    existing_action = get_existing_review_action(
        db,
        action_type="reopen_review_case",
        admin_user_id=admin_user.id,
        review_case_id=review_case_id,
        idempotency_key=idempotency_key,
    )
    if existing_action is not None:
        db.rollback()
        return reopen_review_case(
            db,
            review_case_id=review_case_id,
            admin_user=admin_user,
            payload=payload,
        )
    require_expected_case_version(review_case, payload.expected_case_version)
    if (
        review_case.case_status != "closed"
        or review_case.merged_into_case_id is not None
    ):
        raise review_case_conflict("review_case_transition_conflict", review_case)
    if not case_target_is_actionable_for_reopen(review_case, target):
        raise review_case_conflict("review_case_transition_conflict", review_case)
    existing_open = find_other_open_case_for_identity(db, review_case)
    if existing_open is not None:
        raise review_case_conflict(
            "review_case_open_identity_conflict",
            review_case,
            existing_open_case_id=existing_open.id,
        )
    prior_closure = get_latest_closure_event(db, review_case.id)
    if prior_closure is None:
        raise review_case_conflict("review_case_transition_conflict", review_case)

    now = datetime.now(timezone.utc)
    prior_resolution_mode = review_case.closure_mode
    prior_resolution_outcome = review_case.closure_outcome
    review_case.case_status = "open"
    review_case.closed_by_user_id = None
    review_case.closure_outcome = None
    review_case.closure_reason = None
    review_case.closure_mode = None
    review_case.closure_rule_id = None
    review_case.closure_rule_version = None
    review_case.closed_at = None
    review_case.assigned_to_user_id = None
    review_case.assigned_at = None
    admin_action = record_admin_action(
        db,
        admin_user_id=admin_user.id,
        action_type="reopen_review_case",
        target_review_case_id=review_case.id,
        reason=reason,
        metadata={
            "source": "review_case_reopen",
            "request_fingerprint": request_fingerprint,
            "prior_closure_event_id": str(prior_closure.id),
            "prior_resolution_mode": prior_resolution_mode,
            "prior_resolution_outcome": prior_resolution_outcome,
            "applied_case_version": payload.expected_case_version,
            "resulting_case_version": payload.expected_case_version + 1,
        },
        idempotency_key=idempotency_key,
        created_at=now,
        **copy_targets(target_data_from_object(review_case)),
    )
    event = create_case_event(
        db,
        review_case_id=review_case.id,
        event_type="reopened",
        actor_user_id=admin_user.id,
        admin_action_id=admin_action.id,
        related_event_id=prior_closure.id,
        event_metadata={
            "prior_resolution_mode": prior_resolution_mode,
            "prior_resolution_outcome": prior_resolution_outcome,
        },
        created_at=now,
    )
    metadata = dict(admin_action.metadata_ or {})
    metadata["event_id"] = str(event.id)
    admin_action.metadata_ = metadata
    db.commit()
    db.refresh(review_case)
    return AdminReviewCaseActionResultRead(
        review_case=serialize_review_case_detail(db, review_case),
        audit_action_id=admin_action.id,
        idempotent_replay=False,
        applied_case_version=payload.expected_case_version,
        resulting_case_version=review_case.case_version,
    )


def review_cases_have_same_identity(
    source_case: AdminReviewCase,
    destination_case: AdminReviewCase,
) -> bool:
    return (
        source_case.case_type == destination_case.case_type
        and source_case.case_category == destination_case.case_category
        and discover_case_primary_target(source_case)
        == discover_case_primary_target(destination_case)
    )


def build_review_case_merge_replay(
    db: Session,
    *,
    source_case_id: uuid.UUID,
    action: AdminAction,
) -> AdminReviewCaseMergeResultRead:
    metadata = action.metadata_ or {}
    destination_case_id = uuid.UUID(str(metadata["destination_case_id"]))
    source_case = get_review_case_or_404(db, source_case_id)
    destination_case = get_review_case_or_404(db, destination_case_id)
    return AdminReviewCaseMergeResultRead(
        source_case=serialize_review_case_detail(db, source_case),
        destination_case=serialize_review_case_detail(db, destination_case),
        audit_action_id=action.id,
        idempotent_replay=True,
        applied_source_version=int(metadata["applied_source_version"]),
        applied_destination_version=int(metadata["applied_destination_version"]),
        resulting_source_version=int(metadata["resulting_source_version"]),
        resulting_destination_version=int(metadata["resulting_destination_version"]),
    )


def merge_review_case(
    db: Session,
    *,
    source_case_id: uuid.UUID,
    admin_user: User,
    payload: AdminReviewCaseMerge,
) -> AdminReviewCaseMergeResultRead:
    require_review_manage_access(admin_user)
    reason = normalize_limited_text(payload.reason, "reason", 1000)
    idempotency_key = normalize_required_idempotency_key(payload.idempotency_key)
    request_fingerprint = review_case_request_fingerprint(
        {
            "destination_case_id": payload.destination_case_id,
            "reason": reason,
            "expected_source_version": payload.expected_source_version,
            "expected_destination_version": payload.expected_destination_version,
        }
    )
    existing_action = get_existing_review_action(
        db,
        action_type="merge_review_case",
        admin_user_id=admin_user.id,
        review_case_id=source_case_id,
        idempotency_key=idempotency_key,
    )
    if existing_action is not None:
        if (existing_action.metadata_ or {}).get(
            "request_fingerprint"
        ) != request_fingerprint:
            raise review_case_conflict(
                "review_case_idempotency_conflict",
                get_review_case_or_404(db, source_case_id),
            )
        return build_review_case_merge_replay(
            db, source_case_id=source_case_id, action=existing_action
        )
    if source_case_id == payload.destination_case_id:
        raise review_case_conflict(
            "review_case_transition_conflict",
            get_review_case_or_404(db, source_case_id),
        )

    discovered_source = get_review_case_or_404(db, source_case_id)
    discovered_destination = get_review_case_or_404(db, payload.destination_case_id)
    target_field_name, target_id = discover_case_primary_target(discovered_source)
    target = lock_primary_target(
        db, target_field_name=target_field_name, target_id=target_id
    )
    if target is None:
        raise review_case_conflict("review_case_transition_conflict", discovered_source)
    locked_cases = list(
        db.scalars(
            select(AdminReviewCase)
            .where(
                AdminReviewCase.id.in_((source_case_id, payload.destination_case_id))
            )
            .order_by(AdminReviewCase.id.asc())
            .execution_options(populate_existing=True)
            .with_for_update()
        ).all()
    )
    if len(locked_cases) != 2:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review case not found.",
        )
    by_id = {case.id: case for case in locked_cases}
    source_case = by_id[source_case_id]
    destination_case = by_id[payload.destination_case_id]
    if not review_cases_have_same_identity(source_case, destination_case):
        raise review_case_conflict("review_case_transition_conflict", source_case)
    if discovered_destination.id != destination_case.id:
        raise review_case_conflict("review_case_transition_conflict", source_case)

    existing_action = get_existing_review_action(
        db,
        action_type="merge_review_case",
        admin_user_id=admin_user.id,
        review_case_id=source_case_id,
        idempotency_key=idempotency_key,
    )
    if existing_action is not None:
        db.rollback()
        return merge_review_case(
            db,
            source_case_id=source_case_id,
            admin_user=admin_user,
            payload=payload,
        )
    require_expected_case_version(source_case, payload.expected_source_version)
    require_expected_case_version(
        destination_case, payload.expected_destination_version
    )
    if source_case.merged_into_case_id is not None:
        raise review_case_conflict("review_case_transition_conflict", source_case)
    incoming_source_case_id = db.scalar(
        select(AdminReviewCase.id)
        .where(AdminReviewCase.merged_into_case_id == source_case.id)
        .order_by(AdminReviewCase.id.asc())
        .limit(1)
    )
    if incoming_source_case_id is not None:
        raise review_case_conflict("review_case_transition_conflict", source_case)
    if (
        source_case.case_status != "closed"
        or source_case.closure_mode not in VALID_RESOLUTION_MODES
        or source_case.closure_outcome not in VALID_CLOSURE_OUTCOMES
        or not source_case.closure_reason
        or source_case.closed_at is None
        or source_case.assigned_to_user_id is not None
    ):
        raise review_case_conflict("review_case_transition_conflict", source_case)
    if (
        destination_case.case_status != "open"
        or destination_case.merged_into_case_id is not None
    ):
        raise review_case_conflict("review_case_transition_conflict", destination_case)

    eligible_assignee_ids = lock_eligible_admin_ids(
        db,
        (
            {destination_case.assigned_to_user_id}
            if destination_case.assigned_to_user_id is not None
            else set()
        ),
    )
    if (
        destination_case.assigned_to_user_id in eligible_assignee_ids
        and destination_case.assigned_to_user_id != admin_user.id
    ):
        raise review_case_conflict("review_case_assignment_conflict", source_case)

    now = datetime.now(timezone.utc)
    prior_closure = get_latest_closure_event(db, source_case.id)
    if prior_closure is None:
        raise review_case_conflict("review_case_transition_conflict", source_case)
    prior_metadata = prior_closure.event_metadata or {}
    if (
        prior_metadata.get("closure_mode") != source_case.closure_mode
        or prior_metadata.get("reason") != source_case.closure_reason
        or prior_metadata.get("after", {}).get("closure_outcome")
        != source_case.closure_outcome
        or prior_closure.created_at != source_case.closed_at
        or (
            source_case.closure_mode == "manual"
            and (
                prior_closure.actor_kind != "admin"
                or prior_closure.actor_user_id != source_case.closed_by_user_id
            )
        )
        or (
            source_case.closure_mode == "automatic"
            and (
                prior_closure.actor_kind != "automation"
                or prior_closure.automation_rule_id != source_case.closure_rule_id
                or prior_closure.automation_rule_version
                != source_case.closure_rule_version
            )
        )
    ):
        raise review_case_conflict("review_case_transition_conflict", source_case)
    source_case.merged_into_case_id = destination_case.id

    admin_action = record_admin_action(
        db,
        admin_user_id=admin_user.id,
        action_type="merge_review_case",
        target_review_case_id=source_case.id,
        reason=reason,
        metadata={
            "source": "review_case_merge",
            "destination_case_id": str(destination_case.id),
            "request_fingerprint": request_fingerprint,
            "applied_source_version": payload.expected_source_version,
            "applied_destination_version": payload.expected_destination_version,
            "resulting_source_version": payload.expected_source_version + 1,
            "resulting_destination_version": payload.expected_destination_version + 1,
            "retained_closure_event_id": str(prior_closure.id),
        },
        idempotency_key=idempotency_key,
        created_at=now,
        **copy_targets(target_data_from_object(source_case)),
    )
    source_event = create_case_event(
        db,
        review_case_id=source_case.id,
        event_type="merged_into",
        actor_user_id=admin_user.id,
        admin_action_id=admin_action.id,
        related_case_id=destination_case.id,
        related_event_id=prior_closure.id,
        event_metadata={
            "source_resolution_mode": source_case.closure_mode,
            "source_resolution_outcome": source_case.closure_outcome,
        },
        created_at=now,
    )
    destination_event = create_case_event(
        db,
        review_case_id=destination_case.id,
        event_type="merged_from",
        actor_user_id=admin_user.id,
        admin_action_id=admin_action.id,
        related_case_id=source_case.id,
        related_event_id=source_event.id,
        event_metadata={
            "source_resolution_mode": source_case.closure_mode,
            "source_resolution_outcome": source_case.closure_outcome,
        },
        created_at=now,
    )
    metadata = dict(admin_action.metadata_ or {})
    metadata["source_event_id"] = str(source_event.id)
    metadata["destination_event_id"] = str(destination_event.id)
    admin_action.metadata_ = metadata
    db.commit()
    db.refresh(source_case)
    db.refresh(destination_case)
    return AdminReviewCaseMergeResultRead(
        source_case=serialize_review_case_detail(db, source_case),
        destination_case=serialize_review_case_detail(db, destination_case),
        audit_action_id=admin_action.id,
        idempotent_replay=False,
        applied_source_version=payload.expected_source_version,
        applied_destination_version=payload.expected_destination_version,
        resulting_source_version=source_case.case_version,
        resulting_destination_version=destination_case.case_version,
    )


def link_admin_action_to_open_review_case(
    db: Session,
    admin_action: AdminAction,
    *,
    case_category: str,
) -> AdminReviewCase | None:
    if admin_action.target_review_case_id is not None:
        return None
    review_case = find_open_case_for_admin_action(
        db,
        admin_action,
        case_category=case_category,
    )
    if review_case is None:
        return None
    admin_action.target_review_case_id = review_case.id
    create_case_event(
        db,
        review_case_id=review_case.id,
        event_type="enforcement_action_linked",
        actor_user_id=admin_action.admin_user_id,
        admin_action_id=admin_action.id,
        event_metadata={"action_type": admin_action.action_type},
    )
    return review_case
