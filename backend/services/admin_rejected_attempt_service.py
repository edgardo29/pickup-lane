"""Rejected high-risk admin attempt workflows."""

import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import AdminRejectedAttempt, User
from backend.services.admin_record_rules import (
    describe_fields,
    normalize_metadata_value,
)
from backend.services.admin_rejected_attempt_policy import (
    ADMIN_REJECTED_ATTEMPT_TARGET_FIELDS,
    PERMISSION_DENIED_ATTEMPTED_REF_FIELDS,
    REJECTION_MODES,
    REJECTION_PERMISSION_DENIED_PRELOAD,
    AdminRejectedAttemptPolicy,
    get_admin_rejected_attempt_policy,
)
from backend.services.admin_permission_service import require_user_admin_permission
from backend.services.user_service import build_user_conflict_detail

MAX_ROUTE_METHOD_LENGTH = 10
MAX_ROUTE_PATH_LENGTH = 240
MAX_UNVERIFIED_REF_VALUE_LENGTH = 160


def admin_rejected_attempt_conflict_detail(exc: IntegrityError) -> str:
    error_text = str(exc.orig)

    if "ck_admin_rejected_attempts_attempt_type" in error_text:
        return "attempt_type is not supported."

    if "ck_admin_rejected_attempts_rejection_mode" in error_text:
        return "rejection_mode is not supported."

    if "ck_admin_rejected_attempts_response_status_code" in error_text:
        return "response_status_code must be a 4xx or 5xx status."

    return build_user_conflict_detail(exc)


def unsupported_attempt_type_response() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="attempt_type is not supported.",
    )


def get_policy_or_400(attempt_type: str) -> AdminRejectedAttemptPolicy:
    policy = get_admin_rejected_attempt_policy(attempt_type)
    if policy is None:
        raise unsupported_attempt_type_response()
    return policy


def validate_rejection_mode(rejection_mode: str) -> None:
    if rejection_mode not in REJECTION_MODES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="rejection_mode is not supported.",
        )


def normalize_route_method(route_method: str) -> str:
    normalized = route_method.strip().upper()
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="route_method is required.",
        )

    if len(normalized) > MAX_ROUTE_METHOD_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"route_method must be {MAX_ROUTE_METHOD_LENGTH} characters or fewer."
            ),
        )

    return normalized


def normalize_route_path(route_path: str) -> str:
    normalized = route_path.strip()
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="route_path is required.",
        )

    if "?" in normalized:
        normalized = normalized.split("?", maxsplit=1)[0]

    if len(normalized) > MAX_ROUTE_PATH_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"route_path must be {MAX_ROUTE_PATH_LENGTH} characters or fewer.",
        )

    return normalized


def normalize_response_status_code(response_status_code: int) -> int:
    if response_status_code < 400 or response_status_code > 599:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="response_status_code must be a 4xx or 5xx status.",
        )

    return response_status_code


def normalize_unverified_ref_value(value: Any) -> str | int | bool:
    if isinstance(value, uuid.UUID):
        return str(value)

    if isinstance(value, bool):
        return value

    if isinstance(value, int):
        return value

    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="attempted reference values cannot be blank.",
            )

        if len(normalized) > MAX_UNVERIFIED_REF_VALUE_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "attempted reference values must be "
                    f"{MAX_UNVERIFIED_REF_VALUE_LENGTH} characters or fewer."
                ),
            )

        return normalized

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="attempted reference values must be primitive identifiers.",
    )


def build_permission_denied_metadata(
    *,
    attempted_refs: dict[str, Any],
    required_permission: str,
) -> dict[str, Any]:
    unknown_ref_fields = set(attempted_refs) - PERMISSION_DENIED_ATTEMPTED_REF_FIELDS
    if unknown_ref_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "attempted_refs does not allow field(s): "
                f"{describe_fields(unknown_ref_fields)}."
            ),
        )

    normalized_refs = {
        field_name: normalize_unverified_ref_value(value)
        for field_name, value in attempted_refs.items()
        if value is not None
    }

    return normalize_metadata_value(
        {
            "required_permission": required_permission,
            "attempted_refs_unverified": normalized_refs,
        }
    )


def normalize_rejected_attempt_metadata(
    metadata: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if metadata is None:
        return None

    if not isinstance(metadata, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="metadata must be an object.",
        )

    return normalize_metadata_value(metadata)


def provided_target_fields(attempt_data: dict[str, Any]) -> set[str]:
    return {
        field_name
        for field_name in ADMIN_REJECTED_ATTEMPT_TARGET_FIELDS
        if attempt_data.get(field_name) is not None
    }


def validate_target_policy(
    policy: AdminRejectedAttemptPolicy,
    attempt_data: dict[str, Any],
    *,
    rejection_mode: str,
) -> None:
    targets = provided_target_fields(attempt_data)
    unexpected_targets = targets - policy.allowed_target_fields
    if unexpected_targets:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"{policy.attempt_type} does not allow target field(s): "
                f"{describe_fields(unexpected_targets)}."
            ),
        )

    if rejection_mode == REJECTION_PERMISSION_DENIED_PRELOAD and targets:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="permission_denied_preload attempts cannot store target refs.",
        )


def record_admin_rejected_attempt(
    db: Session,
    *,
    admin_user_id: uuid.UUID | None,
    attempt_type: str,
    rejection_mode: str,
    response_status_code: int,
    route_method: str,
    route_path: str,
    metadata: dict[str, Any] | None = None,
    target_user_id: uuid.UUID | None = None,
    target_game_credit_id: uuid.UUID | None = None,
) -> AdminRejectedAttempt:
    policy = get_policy_or_400(attempt_type)
    validate_rejection_mode(rejection_mode)
    attempt_data = {
        "target_user_id": target_user_id,
        "target_game_credit_id": target_game_credit_id,
    }
    validate_target_policy(policy, attempt_data, rejection_mode=rejection_mode)

    rejected_attempt = AdminRejectedAttempt(
        id=uuid.uuid4(),
        admin_user_id=admin_user_id,
        attempt_type=policy.attempt_type,
        rejection_mode=rejection_mode,
        response_status_code=normalize_response_status_code(response_status_code),
        route_method=normalize_route_method(route_method),
        route_path=normalize_route_path(route_path),
        target_user_id=target_user_id,
        target_game_credit_id=target_game_credit_id,
        metadata_=normalize_rejected_attempt_metadata(metadata),
    )

    try:
        db.add(rejected_attempt)
        db.commit()
        db.refresh(rejected_attempt)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=admin_rejected_attempt_conflict_detail(exc),
        ) from exc

    return rejected_attempt


def user_can_read_rejected_attempt(
    user: User,
    rejected_attempt: AdminRejectedAttempt,
) -> bool:
    policy = get_admin_rejected_attempt_policy(rejected_attempt.attempt_type)
    if policy is None:
        return False

    try:
        require_user_admin_permission(user, policy.read_permission)
    except HTTPException:
        return False

    return True


def list_admin_rejected_attempts(
    db: Session,
    *,
    viewer_user: User,
    attempt_type: str | None = None,
    rejection_mode: str | None = None,
    limit: int = 100,
) -> list[AdminRejectedAttempt]:
    if attempt_type is not None:
        get_policy_or_400(attempt_type)

    if rejection_mode is not None:
        validate_rejection_mode(rejection_mode)

    query = select(AdminRejectedAttempt)
    if attempt_type:
        query = query.where(AdminRejectedAttempt.attempt_type == attempt_type)
    if rejection_mode:
        query = query.where(AdminRejectedAttempt.rejection_mode == rejection_mode)

    rejected_attempts = db.scalars(
        query.order_by(
            AdminRejectedAttempt.created_at.desc(),
            AdminRejectedAttempt.id.asc(),
        ).limit(limit)
    ).all()

    return [
        rejected_attempt
        for rejected_attempt in rejected_attempts
        if user_can_read_rejected_attempt(viewer_user, rejected_attempt)
    ]


def get_admin_rejected_attempt_for_viewer_or_404(
    db: Session,
    admin_rejected_attempt_id: uuid.UUID,
    viewer_user: User,
) -> AdminRejectedAttempt:
    rejected_attempt = db.get(AdminRejectedAttempt, admin_rejected_attempt_id)

    if rejected_attempt is None or not user_can_read_rejected_attempt(
        viewer_user,
        rejected_attempt,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rejected admin attempt not found.",
        )

    return rejected_attempt
