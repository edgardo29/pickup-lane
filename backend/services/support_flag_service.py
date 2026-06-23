"""Support flag workflows for durable admin follow-up state."""

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import (
    AdminAction,
    Booking,
    Game,
    GameCredit,
    Notification,
    Payment,
    Refund,
    SupportFlag,
    User,
    Venue,
    VenueImage,
)
from backend.schemas.support_flag_schema import SupportFlagResolve
from backend.services.admin_action_service import (
    describe_fields,
    normalize_idempotency_key,
    normalize_metadata_value,
    record_admin_action,
)
from backend.services.admin_permission_service import (
    get_admin_data_scopes_for_user,
    require_user_admin_permission,
    user_has_admin_permission,
)
from backend.services.support_flag_policy import (
    SUPPORT_FLAG_POLICIES,
    SUPPORT_FLAG_TARGET_FIELDS,
    TARGET_BOOKING_ID,
    TARGET_GAME_CREDIT_ID,
    TARGET_GAME_ID,
    TARGET_NOTIFICATION_ID,
    TARGET_PAYMENT_ID,
    TARGET_REFUND_ID,
    TARGET_USER_ID,
    TARGET_VENUE_ID,
    TARGET_VENUE_IMAGE_ID,
    SupportFlagPolicy,
    SupportFlagTargetRule,
    get_support_flag_policy,
)
from backend.services.user_service import build_user_conflict_detail

MAX_SUPPORT_FLAG_TITLE_LENGTH = 180
MAX_SUPPORT_FLAG_SUMMARY_LENGTH = 2000
SUPPORT_FLAG_STATUSES = ("open", "resolved")

TARGET_MODEL_BY_FIELD = {
    TARGET_USER_ID: User,
    TARGET_GAME_ID: Game,
    TARGET_BOOKING_ID: Booking,
    TARGET_PAYMENT_ID: Payment,
    TARGET_REFUND_ID: Refund,
    TARGET_GAME_CREDIT_ID: GameCredit,
    TARGET_VENUE_ID: Venue,
    TARGET_VENUE_IMAGE_ID: VenueImage,
    TARGET_NOTIFICATION_ID: Notification,
}

TARGET_NOT_FOUND_DETAIL = {
    TARGET_USER_ID: "Target user not found.",
    TARGET_GAME_ID: "Target game not found.",
    TARGET_BOOKING_ID: "Target booking not found.",
    TARGET_PAYMENT_ID: "Target payment not found.",
    TARGET_REFUND_ID: "Target refund not found.",
    TARGET_GAME_CREDIT_ID: "Target game credit not found.",
    TARGET_VENUE_ID: "Target venue not found.",
    TARGET_VENUE_IMAGE_ID: "Target venue image not found.",
    TARGET_NOTIFICATION_ID: "Target notification not found.",
}


def support_flag_conflict_detail(exc: IntegrityError) -> str:
    error_text = str(exc.orig)

    if "ck_support_flags_flag_type" in error_text:
        return "flag_type is not supported."

    if "ck_support_flags_target_required" in error_text:
        return "At least one target field must be provided."

    if "uq_support_flags_flag_type_idempotency_key" in error_text:
        return "Support flag with this idempotency key already exists."

    return build_user_conflict_detail(exc)


def unsupported_flag_type_response() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="flag_type is not supported.",
    )


def get_policy_or_400(flag_type: str) -> SupportFlagPolicy:
    policy = get_support_flag_policy(flag_type)
    if policy is None:
        raise unsupported_flag_type_response()
    return policy


def validate_required_rule(
    flag_type: str,
    rule: SupportFlagTargetRule,
    data: dict[str, Any],
) -> None:
    if rule.all_of:
        missing_fields = [
            field_name for field_name in rule.all_of if data.get(field_name) is None
        ]
        if missing_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"{flag_type} requires target field(s): "
                    f"{describe_fields(missing_fields)}."
                ),
            )

    if rule.one_of and not any(data.get(field_name) is not None for field_name in rule.one_of):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"{flag_type} requires one of target field(s): "
                f"{describe_fields(rule.one_of)}."
            ),
        )


def validate_target_policy(policy: SupportFlagPolicy, data: dict[str, Any]) -> None:
    provided_targets = {
        field_name
        for field_name in SUPPORT_FLAG_TARGET_FIELDS
        if data.get(field_name) is not None
    }
    unexpected_targets = provided_targets - policy.allowed_target_fields
    if unexpected_targets:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"{policy.flag_type} does not allow target field(s): "
                f"{describe_fields(unexpected_targets)}."
            ),
        )

    for rule in policy.required_target_rules:
        validate_required_rule(policy.flag_type, rule, data)


def validate_reference_exists(
    db: Session,
    field_name: str,
    record_id: uuid.UUID,
) -> None:
    model = TARGET_MODEL_BY_FIELD.get(field_name)
    if model is None:
        return

    record = db.get(model, record_id)
    if record is None or getattr(record, "deleted_at", None) is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=TARGET_NOT_FOUND_DETAIL[field_name],
        )


def validate_target_references(db: Session, data: dict[str, Any]) -> None:
    for field_name in SUPPORT_FLAG_TARGET_FIELDS:
        target_id = data.get(field_name)
        if target_id is not None:
            validate_reference_exists(db, field_name, target_id)


def normalize_limited_text(
    value: str,
    field_name: str,
    max_length: int,
) -> str:
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


def normalize_support_flag_metadata(metadata: dict[str, Any] | None) -> dict[str, Any] | None:
    if metadata is None:
        return None

    if not isinstance(metadata, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="metadata must be an object.",
        )

    return normalize_metadata_value(metadata)


def user_can_read_support_flag(user: User, support_flag: SupportFlag) -> bool:
    policy = get_support_flag_policy(support_flag.flag_type)
    if policy is None:
        return False

    return (
        policy.sensitivity_scope in get_admin_data_scopes_for_user(user)
        and user_has_admin_permission(user, policy.read_permission)
    )


def readable_support_flag_types(user: User) -> tuple[str, ...]:
    data_scopes = get_admin_data_scopes_for_user(user)
    return tuple(
        flag_type
        for flag_type, policy in SUPPORT_FLAG_POLICIES.items()
        if policy.sensitivity_scope in data_scopes
        and user_has_admin_permission(user, policy.read_permission)
    )


def get_support_flag_or_404(db: Session, support_flag_id: uuid.UUID) -> SupportFlag:
    support_flag = db.get(SupportFlag, support_flag_id)

    if support_flag is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Support flag not found.",
        )

    return support_flag


def get_support_flag_for_viewer_or_404(
    db: Session,
    support_flag_id: uuid.UUID,
    viewer_user: User,
) -> SupportFlag:
    support_flag = get_support_flag_or_404(db, support_flag_id)

    if not user_can_read_support_flag(viewer_user, support_flag):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Support flag not found.",
        )

    return support_flag


def list_support_flags(
    db: Session,
    *,
    viewer_user: User,
    flag_status: str = "open",
    flag_type: str | None = None,
    limit: int = 100,
) -> list[SupportFlag]:
    if flag_status not in (*SUPPORT_FLAG_STATUSES, "all"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="flag_status is not supported.",
        )

    if flag_type is not None:
        get_policy_or_400(flag_type)

    readable_flag_types = readable_support_flag_types(viewer_user)
    if not readable_flag_types:
        return []

    query = select(SupportFlag).where(
        SupportFlag.flag_type.in_(readable_flag_types)
    )
    if flag_status != "all":
        query = query.where(SupportFlag.flag_status == flag_status)
    if flag_type:
        query = query.where(SupportFlag.flag_type == flag_type)

    support_flags = db.scalars(
        query.order_by(SupportFlag.created_at.desc(), SupportFlag.id.asc()).limit(limit)
    ).all()

    return list(support_flags)


def get_existing_support_flag_by_idempotency_key(
    db: Session,
    *,
    flag_type: str,
    idempotency_key: str,
) -> SupportFlag | None:
    return db.scalar(
        select(SupportFlag).where(
            SupportFlag.flag_type == flag_type,
            SupportFlag.idempotency_key == idempotency_key,
        )
    )


def reopen_resolved_support_flag(
    support_flag: SupportFlag,
    *,
    source: str,
    title: str,
    summary: str,
    severity: str,
    metadata: dict[str, Any] | None,
    source_admin_action_id: uuid.UUID | None,
) -> SupportFlag:
    reopened_at = datetime.now(timezone.utc)
    support_flag.flag_status = "open"
    support_flag.severity = severity
    support_flag.source = source
    support_flag.title = normalize_limited_text(
        title,
        "title",
        MAX_SUPPORT_FLAG_TITLE_LENGTH,
    )
    support_flag.summary = normalize_limited_text(
        summary,
        "summary",
        MAX_SUPPORT_FLAG_SUMMARY_LENGTH,
    )
    support_flag.metadata_ = normalize_support_flag_metadata(metadata)
    support_flag.source_admin_action_id = source_admin_action_id
    support_flag.resolved_by_user_id = None
    support_flag.resolution_outcome = None
    support_flag.resolution_reason = None
    support_flag.resolution_admin_action_id = None
    support_flag.resolved_at = None
    support_flag.updated_at = reopened_at
    return support_flag


def stage_support_flag(
    db: Session,
    *,
    flag_type: str,
    source: str,
    title: str,
    summary: str,
    severity: str = "attention",
    metadata: dict[str, Any] | None = None,
    idempotency_key: str | None = None,
    source_admin_action_id: uuid.UUID | None = None,
    created_by_user_id: uuid.UUID | None = None,
    reopen_resolved: bool = False,
    **targets: uuid.UUID | None,
) -> SupportFlag:
    policy = get_policy_or_400(flag_type)
    unknown_targets = set(targets) - set(SUPPORT_FLAG_TARGET_FIELDS)
    if unknown_targets:
        raise ValueError(f"Unknown support flag target(s): {describe_fields(unknown_targets)}")

    normalized_idempotency_key = normalize_idempotency_key(idempotency_key)
    if normalized_idempotency_key is not None:
        existing_flag = get_existing_support_flag_by_idempotency_key(
            db,
            flag_type=flag_type,
            idempotency_key=normalized_idempotency_key,
        )
        if existing_flag is not None:
            if reopen_resolved and existing_flag.flag_status == "resolved":
                reopen_resolved_support_flag(
                    existing_flag,
                    source=source,
                    title=title,
                    summary=summary,
                    severity=severity,
                    metadata=metadata,
                    source_admin_action_id=source_admin_action_id,
                )
                db.add(existing_flag)
            return existing_flag

    flag_data = {
        "flag_type": flag_type,
        **{
            field_name: targets.get(field_name)
            for field_name in SUPPORT_FLAG_TARGET_FIELDS
        },
    }
    validate_target_policy(policy, flag_data)
    validate_target_references(db, flag_data)

    support_flag = SupportFlag(
        id=uuid.uuid4(),
        flag_type=flag_type,
        flag_status="open",
        severity=severity,
        source=source,
        title=normalize_limited_text(title, "title", MAX_SUPPORT_FLAG_TITLE_LENGTH),
        summary=normalize_limited_text(summary, "summary", MAX_SUPPORT_FLAG_SUMMARY_LENGTH),
        metadata_=normalize_support_flag_metadata(metadata),
        idempotency_key=normalized_idempotency_key,
        source_admin_action_id=source_admin_action_id,
        created_by_user_id=created_by_user_id,
        **{
            field_name: targets.get(field_name)
            for field_name in SUPPORT_FLAG_TARGET_FIELDS
        },
    )

    db.add(support_flag)
    return support_flag


def create_support_flag(
    db: Session,
    *,
    flag_type: str,
    source: str,
    title: str,
    summary: str,
    severity: str = "attention",
    metadata: dict[str, Any] | None = None,
    idempotency_key: str | None = None,
    source_admin_action_id: uuid.UUID | None = None,
    created_by_user_id: uuid.UUID | None = None,
    reopen_resolved: bool = False,
    **targets: uuid.UUID | None,
) -> SupportFlag:
    try:
        support_flag = stage_support_flag(
            db,
            flag_type=flag_type,
            source=source,
            title=title,
            summary=summary,
            severity=severity,
            metadata=metadata,
            idempotency_key=idempotency_key,
            source_admin_action_id=source_admin_action_id,
            created_by_user_id=created_by_user_id,
            reopen_resolved=reopen_resolved,
            **targets,
        )
        db.commit()
        db.refresh(support_flag)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=support_flag_conflict_detail(exc),
        ) from exc

    return support_flag


def build_support_flag_audit_targets(support_flag: SupportFlag) -> dict[str, uuid.UUID | None]:
    return {
        field_name: getattr(support_flag, field_name)
        for field_name in SUPPORT_FLAG_TARGET_FIELDS
    }


def get_existing_support_flag_resolution_action(
    db: Session,
    *,
    resolver_user_id: uuid.UUID,
    support_flag_id: uuid.UUID,
    idempotency_key: str,
) -> AdminAction | None:
    return db.scalar(
        select(AdminAction)
        .where(
            AdminAction.action_type == "resolve_support_flag",
            AdminAction.admin_user_id == resolver_user_id,
            AdminAction.target_support_flag_id == support_flag_id,
            AdminAction.idempotency_key == idempotency_key,
        )
        .order_by(AdminAction.created_at.desc(), AdminAction.id.desc())
        .limit(1)
    )


def validate_existing_support_flag_resolution_action(
    action: AdminAction,
    *,
    expected_outcome: str,
    expected_reason: str,
) -> None:
    after_metadata = (
        action.metadata_.get("after")
        if isinstance(action.metadata_, dict)
        else None
    )
    recorded_outcome = (
        after_metadata.get("resolution_outcome")
        if isinstance(after_metadata, dict)
        else None
    )
    if action.reason != expected_reason or recorded_outcome != expected_outcome:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "idempotency_key was already used for a different "
                "support flag resolution request."
            ),
        )


def resolve_support_flag(
    db: Session,
    *,
    support_flag_id: uuid.UUID,
    resolver_user: User,
    payload: SupportFlagResolve,
) -> SupportFlag:
    visible_flag = get_support_flag_for_viewer_or_404(
        db,
        support_flag_id,
        resolver_user,
    )
    policy = get_policy_or_400(visible_flag.flag_type)
    require_user_admin_permission(resolver_user, policy.resolve_permission)

    resolution_reason = normalize_limited_text(payload.reason, "reason", 1000)
    idempotency_key = normalize_idempotency_key(payload.idempotency_key)
    if policy.resolution_requires_idempotency and (
        idempotency_key is None or len(idempotency_key) < 8
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="idempotency_key must be at least 8 characters.",
        )

    support_flag = db.scalar(
        select(SupportFlag)
        .where(SupportFlag.id == support_flag_id)
        .with_for_update()
    )
    if support_flag is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Support flag not found.",
        )
    policy = get_policy_or_400(support_flag.flag_type)

    if idempotency_key is not None:
        existing_action = get_existing_support_flag_resolution_action(
            db,
            resolver_user_id=resolver_user.id,
            support_flag_id=support_flag.id,
            idempotency_key=idempotency_key,
        )
        if existing_action is not None:
            validate_existing_support_flag_resolution_action(
                existing_action,
                expected_outcome=payload.outcome,
                expected_reason=resolution_reason,
            )
            return support_flag

    if support_flag.flag_status != "open":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Support flag is already resolved.",
        )

    if payload.outcome not in policy.allowed_resolution_outcomes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="resolution outcome is not supported for this support flag.",
        )

    resolved_at = datetime.now(timezone.utc)
    audit_action = record_admin_action(
        db,
        admin_user_id=resolver_user.id,
        action_type="resolve_support_flag",
        reason=resolution_reason,
        metadata={
            "before": {
                "flag_status": support_flag.flag_status,
                "resolution_outcome": support_flag.resolution_outcome,
            },
            "after": {
                "flag_status": "resolved",
                "resolution_outcome": payload.outcome,
                "flag_type": support_flag.flag_type,
            },
        },
        idempotency_key=idempotency_key,
        target_support_flag_id=support_flag.id,
        **build_support_flag_audit_targets(support_flag),
    )
    support_flag.flag_status = "resolved"
    support_flag.resolved_by_user_id = resolver_user.id
    support_flag.resolution_outcome = payload.outcome
    support_flag.resolution_reason = resolution_reason
    support_flag.resolution_admin_action_id = audit_action.id
    support_flag.resolved_at = resolved_at
    support_flag.updated_at = resolved_at

    try:
        db.add(support_flag)
        db.commit()
        db.refresh(support_flag)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=support_flag_conflict_detail(exc),
        ) from exc

    return support_flag
