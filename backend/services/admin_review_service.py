"""Admin review signal and case workflow services."""

from base64 import urlsafe_b64decode, urlsafe_b64encode
from binascii import Error as BinasciiError
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from json import JSONDecodeError, dumps, loads
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import (
    AdminAction,
    AdminContentModerationFinding,
    AdminFinancialOutcome,
    AdminReviewCase,
    AdminReviewCaseEvent,
    AdminReviewCaseNote,
    AdminReviewSignal,
    Game,
    Payment,
    SubPost,
    SubPostRequest,
    User,
)
from backend.schemas.admin_review_schema import (
    AdminContentModerationFindingRead,
    AdminReviewCaseActionResultRead,
    AdminReviewCaseDetailRead,
    AdminReviewCaseEventRead,
    AdminReviewCaseFindingSummaryRead,
    AdminReviewCaseListRead,
    AdminReviewCaseNoteCreate,
    AdminReviewCaseNoteRead,
    AdminReviewCaseNoteResultRead,
    AdminReviewCaseRead,
    AdminReviewCaseClose,
    AdminReviewCaseTargetSummaryRead,
    AdminReviewSignalRead,
    MAX_REVIEW_CASE_NOTE_BODY_LENGTH,
)
from backend.services.admin_action_service import record_admin_action
from backend.services.admin_review_actionability_service import (
    build_open_content_review_case_actionable_condition,
)
from backend.services.admin_record_rules import (
    normalize_idempotency_key,
    normalize_metadata_value,
)
from backend.services.auth_service import require_active_admin_user
from backend.services.user_service import get_user_display_name

CASE_ACTIVE_STATUSES = ("open",)
VALID_CASE_STATUSES = ("open", "closed")
CONTENT_MODERATION_CASE_CATEGORY = "content_moderation"
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


def encode_admin_review_case_list_cursor(
    *,
    review_case: AdminReviewCase,
    case_status: str | None,
    case_category: str | None,
    target_type: str | None,
) -> str:
    payload = {
        "case_status": case_status,
        "case_category": case_category,
        "target_type": target_type,
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
) -> None:
    if cursor_payload is None:
        return

    if (
        cursor_payload["case_status"] != case_status
        or cursor_payload["case_category"] != case_category
        or cursor_payload["target_type"] != target_type
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
        field_name
        for field_name, value in target_data.items()
        if value is not None
    }


def primary_target(target_data: dict[str, uuid.UUID | None]) -> tuple[str, uuid.UUID] | None:
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


def copy_targets(target_data: dict[str, uuid.UUID | None]) -> dict[str, uuid.UUID | None]:
    return {
        field_name: target_data.get(field_name)
        for field_name in REVIEW_TARGET_FIELDS
    }


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
    event_metadata: dict[str, Any] | None = None,
    created_at: datetime | None = None,
) -> AdminReviewCaseEvent:
    event = AdminReviewCaseEvent(
        id=uuid.uuid4(),
        review_case_id=review_case_id,
        event_type=event_type,
        actor_user_id=actor_user_id,
        admin_action_id=admin_action_id,
        signal_id=signal_id,
        content_moderation_finding_id=content_moderation_finding_id,
        note_id=note_id,
        event_metadata=normalize_metadata(event_metadata),
        created_at=created_at or datetime.now(timezone.utc),
    )
    db.add(event)
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
        .with_for_update()
    )
    if review_case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review case not found.",
        )
    return review_case


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
    if review_case.case_type == "community_game" or review_case.target_game_id is not None:
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
) -> AdminReviewCaseRead:
    return AdminReviewCaseRead.model_validate(review_case).model_copy(
        update={
            "finding_summary": build_review_case_finding_summary(
                signals or [],
                findings or [],
            ),
            "target_summary": target_summary,
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
                AdminReviewCaseEvent.created_at.asc(),
                AdminReviewCaseEvent.id.asc(),
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

    return AdminReviewCaseDetailRead.model_validate(review_case).model_copy(
        update={
            "finding_summary": build_review_case_finding_summary(signals, findings),
            "target_summary": get_review_case_target_summary(db, review_case),
            "findings": [
                AdminContentModerationFindingRead.model_validate(finding)
                for finding in findings
            ],
            "signals": [
                AdminReviewSignalRead.model_validate(signal)
                for signal in signals
            ],
            "events": [
                AdminReviewCaseEventRead.model_validate(event)
                for event in events
            ],
            "notes": [
                serialize_review_case_note_read(note, author_by_id)
                for note in notes
            ],
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

    return AdminReviewCaseListRead(
        cases=[
            serialize_review_case_read(
                review_case,
                signals_by_case_id.get(review_case.id, []),
                findings_by_case_id.get(review_case.id, []),
                target_summaries.get(review_case.id),
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
) -> AdminReviewCaseListRead:
    require_review_read_access(viewer_user)
    normalized_status: str | None = None
    normalized_category: str | None = None
    normalized_target_type = normalize_review_case_list_target_type(target_type)
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
        statement = statement.where(AdminReviewCase.case_category == normalized_category)
    if normalized_target_type == REVIEW_CASE_LIST_CONTENT_TARGETS:
        statement = statement.where(
            AdminReviewCase.case_type.in_(("community_game", "need_a_sub"))
        )
    elif normalized_target_type == "need_a_sub":
        statement = statement.where(AdminReviewCase.case_type == "need_a_sub")
    elif normalized_target_type == "community_game":
        statement = statement.where(AdminReviewCase.case_type == "community_game")

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
) -> AdminReviewCase | None:
    primary = primary_target(target_data)
    if primary is None:
        return None
    field_name, target_id = primary
    active_case = db.scalar(
        select(AdminReviewCase)
        .where(
            AdminReviewCase.case_status.in_(CASE_ACTIVE_STATUSES),
            AdminReviewCase.case_category == case_category,
            getattr(AdminReviewCase, field_name) == target_id,
        )
        .order_by(AdminReviewCase.created_at.asc(), AdminReviewCase.id.asc())
        .limit(1)
        .with_for_update()
    )
    if active_case is not None:
        return active_case

    return None


def find_open_case_for_admin_action(
    db: Session,
    admin_action: AdminAction,
) -> AdminReviewCase | None:
    target_data = target_data_from_object(admin_action)
    primary = primary_target(target_data)
    if primary is None:
        return None
    field_name, target_id = primary
    return db.scalar(
        select(AdminReviewCase)
        .where(
            AdminReviewCase.case_status.in_(CASE_ACTIVE_STATUSES),
            getattr(AdminReviewCase, field_name) == target_id,
        )
        .order_by(AdminReviewCase.created_at.asc(), AdminReviewCase.id.asc())
        .limit(1)
    )


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
    if closure_outcome not in VALID_CLOSURE_OUTCOMES:
        raise ValueError("closure_outcome is not supported.")

    review_case = db.scalar(
        select(AdminReviewCase)
        .where(
            AdminReviewCase.case_status.in_(CASE_ACTIVE_STATUSES),
            AdminReviewCase.case_category == CONTENT_MODERATION_CASE_CATEGORY,
            getattr(AdminReviewCase, target_field_name) == target_id,
        )
        .order_by(AdminReviewCase.created_at.asc(), AdminReviewCase.id.asc())
        .limit(1)
        .with_for_update()
    )
    if review_case is None:
        return None

    now = closed_at or datetime.now(timezone.utc)
    reason = normalize_limited_text(closure_reason, "closure_reason", 2000)
    before = {
        "case_status": review_case.case_status,
        "closure_outcome": review_case.closure_outcome,
    }
    review_case.case_status = "closed"
    review_case.closure_outcome = closure_outcome
    review_case.closure_reason = reason
    review_case.closed_by_user_id = closed_by_user_id
    review_case.closed_at = now
    review_case.updated_at = now
    db.add(review_case)

    if admin_action is not None and admin_action.target_review_case_id is None:
        admin_action.target_review_case_id = review_case.id
        db.add(admin_action)

    create_case_event(
        db,
        review_case_id=review_case.id,
        event_type="closed",
        actor_user_id=trigger_actor_user_id,
        admin_action_id=admin_action.id if admin_action is not None else None,
        event_metadata={
            "closure_mode": "automatic",
            "closure_source": "target_lifecycle",
            "lifecycle_action": lifecycle_action,
            "target_type": target_type,
            "previous_target_state": previous_target_state,
            "new_target_state": new_target_state,
            "trigger_actor_type": trigger_actor_type,
            "trigger_actor_user_id": trigger_actor_user_id,
            "closed_by_user_id": closed_by_user_id,
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
                existing_signal.metadata_ = normalized_metadata
                existing_signal.updated_at = now
                db.add(existing_signal)
            if (
                not was_current_match
                and becomes_current_match
                and review_case.case_status in CASE_ACTIVE_STATUSES
            ):
                review_case.updated_at = now
                if (
                    PRIORITY_RANK[normalized_priority]
                    > PRIORITY_RANK[review_case.priority]
                ):
                    review_case.priority = normalized_priority
                db.add(review_case)
            db.commit()
            db.refresh(review_case)
            db.refresh(existing_signal)
            return review_case, existing_signal, False, True

        if not created_case:
            review_case.updated_at = now
            if PRIORITY_RANK[normalized_priority] > PRIORITY_RANK[review_case.priority]:
                review_case.priority = normalized_priority
            db.add(review_case)

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
                event_metadata={"source": normalized_source},
                created_at=now,
            )

        create_case_event(
            db,
            review_case_id=review_case.id,
            event_type="signal_attached",
            actor_user_id=None,
            signal_id=signal.id,
            event_metadata={
                "created_case": created_case,
                "source": normalized_source,
            },
            created_at=now + timedelta(microseconds=1) if created_case else now,
        )

        db.commit()
        db.refresh(review_case)
        db.refresh(signal)
    except IntegrityError as exc:
        db.rollback()
        if not _retrying_after_conflict:
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
) -> AdminReviewCaseNoteResultRead:
    require_review_manage_access(admin_user)
    body = normalize_limited_text(
        payload.body,
        "body",
        MAX_REVIEW_CASE_NOTE_BODY_LENGTH,
    )
    idempotency_key = normalize_required_idempotency_key(payload.idempotency_key)
    body_hash = note_hash(body)

    existing_action = get_existing_review_action(
        db,
        action_type="add_review_case_note",
        admin_user_id=admin_user.id,
        review_case_id=review_case_id,
        idempotency_key=idempotency_key,
    )
    if existing_action is not None:
        metadata = existing_action.metadata_ or {}
        if metadata.get("note_hash") != body_hash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="idempotency_key was already used for a different note.",
            )
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
        )

    review_case = get_review_case_for_update_or_404(db, review_case_id)
    if review_case.case_status == "closed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Closed review cases cannot receive notes.",
        )
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

    now = datetime.now(timezone.utc)
    note = AdminReviewCaseNote(
        id=uuid.uuid4(),
        review_case_id=review_case.id,
        author_user_id=admin_user.id,
        body=body,
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
    )
    review_case.updated_at = now
    db.flush()
    metadata = dict(admin_action.metadata_ or {})
    metadata["event_id"] = str(event.id)
    admin_action.metadata_ = metadata

    db.commit()
    db.refresh(review_case)
    db.refresh(note)
    db.refresh(admin_action)
    return AdminReviewCaseNoteResultRead(
        review_case=serialize_review_case_detail(db, review_case),
        note=serialize_review_case_note_read(note, {admin_user.id: admin_user}),
        audit_action_id=admin_action.id,
        idempotent_replay=False,
    )


def build_review_case_action_replay(
    db: Session,
    *,
    review_case_id: uuid.UUID,
    action: AdminAction,
) -> AdminReviewCaseActionResultRead:
    review_case = get_review_case_or_404(db, review_case_id)
    return AdminReviewCaseActionResultRead(
        review_case=serialize_review_case_detail(db, review_case),
        audit_action_id=action.id,
        idempotent_replay=True,
    )


def close_review_case(
    db: Session,
    *,
    review_case_id: uuid.UUID,
    admin_user: User,
    payload: AdminReviewCaseClose,
) -> AdminReviewCaseActionResultRead:
    require_review_manage_access(admin_user)
    outcome = str(payload.outcome or "").strip().lower()
    if outcome not in VALID_CLOSURE_OUTCOMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="outcome is not supported.",
        )
    reason = normalize_limited_text(payload.reason, "reason", 2000)
    idempotency_key = normalize_required_idempotency_key(payload.idempotency_key)

    existing_action = get_existing_review_action(
        db,
        action_type="close_review_case",
        admin_user_id=admin_user.id,
        review_case_id=review_case_id,
        idempotency_key=idempotency_key,
    )
    if existing_action is not None:
        metadata = existing_action.metadata_ or {}
        if (
            metadata.get("closure_outcome") != outcome
            or existing_action.reason != reason
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "idempotency_key was already used for a different "
                    "review closure."
                ),
            )
        return build_review_case_action_replay(
            db,
            review_case_id=review_case_id,
            action=existing_action,
        )

    review_case = get_review_case_for_update_or_404(db, review_case_id)
    if review_case.case_status == "closed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Review case is already closed.",
        )

    now = datetime.now(timezone.utc)
    before = {
        "case_status": review_case.case_status,
        "closure_outcome": review_case.closure_outcome,
    }
    review_case.case_status = "closed"
    review_case.closure_outcome = outcome
    review_case.closure_reason = reason
    review_case.closed_by_user_id = admin_user.id
    review_case.closed_at = now
    review_case.updated_at = now
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
        event_metadata=after,
    )
    db.flush()
    metadata = dict(admin_action.metadata_ or {})
    metadata["event_id"] = str(event.id)
    admin_action.metadata_ = metadata

    db.commit()
    db.refresh(review_case)
    db.refresh(admin_action)
    return AdminReviewCaseActionResultRead(
        review_case=serialize_review_case_detail(db, review_case),
        audit_action_id=admin_action.id,
        idempotent_replay=False,
    )


def link_admin_action_to_open_review_case(
    db: Session,
    admin_action: AdminAction,
) -> AdminReviewCase | None:
    if admin_action.target_review_case_id is not None:
        return None
    review_case = find_open_case_for_admin_action(db, admin_action)
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
    review_case.updated_at = datetime.now(timezone.utc)
    return review_case
