"""Admin staff role mutation workflows."""

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import AdminAction, User
from backend.schemas.admin_user_schema import (
    AdminUserStaffRoleChangeCreate,
    AdminUserStaffRoleChangeResultRead,
)
from backend.services.admin_action_service import record_admin_action
from backend.services.auth_service import ADMIN_ROLE
from backend.services.user_service import build_user_conflict_detail

PLAYER_ROLE = "player"
STAFF_ROLE_CHANGE_ROLES = (ADMIN_ROLE, PLAYER_ROLE)


def normalize_staff_role_change_request(
    payload: AdminUserStaffRoleChangeCreate,
) -> tuple[str, str, str]:
    role = payload.role.strip().lower()
    if role not in STAFF_ROLE_CHANGE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="role is not supported.",
        )

    reason = " ".join(payload.reason.strip().split())
    if not reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="reason is required.",
        )

    idempotency_key = payload.idempotency_key.strip()
    if len(idempotency_key) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="idempotency_key must be at least 8 characters.",
        )

    return role, reason, idempotency_key


def get_existing_staff_role_change_action(
    db: Session,
    *,
    admin_user_id: uuid.UUID,
    user_id: uuid.UUID,
    idempotency_key: str,
) -> AdminAction | None:
    return db.scalar(
        select(AdminAction).where(
            AdminAction.admin_user_id == admin_user_id,
            AdminAction.action_type == "change_staff_role",
            AdminAction.target_user_id == user_id,
            AdminAction.idempotency_key == idempotency_key,
        )
    )


def build_staff_role_change_result(
    *,
    action: AdminAction,
    expected_reason: str,
    expected_role: str,
) -> AdminUserStaffRoleChangeResultRead:
    metadata = action.metadata_ or {}
    before = metadata.get("before") or {}
    after = metadata.get("after") or {}
    previous_role = before.get("role")
    role = after.get("role")
    if action.target_user_id is None or not previous_role or not role:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The prior staff role change result is incomplete.",
        )
    if role != expected_role or action.reason != expected_reason:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "idempotency_key was already used for a different "
                "staff role change request."
            ),
        )

    return AdminUserStaffRoleChangeResultRead(
        user_id=action.target_user_id,
        previous_role=previous_role,
        role=role,
        changed_at=action.created_at,
        admin_action_id=action.id,
    )


def lock_staff_role_change_users(
    db: Session,
    *,
    user_id: uuid.UUID,
) -> tuple[User, list[User]]:
    users = list(
        db.scalars(
            select(User)
            .where(
                or_(
                    User.id == user_id,
                    (
                        (User.role == ADMIN_ROLE)
                        & (User.account_status == "active")
                        & User.deleted_at.is_(None)
                    ),
                )
            )
            .order_by(User.id.asc())
            .with_for_update()
        ).all()
    )
    target_user = next((user for user in users if user.id == user_id), None)
    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    active_admin_users = [
        user
        for user in users
        if (
            user.role == ADMIN_ROLE
            and user.account_status == "active"
            and user.deleted_at is None
        )
    ]
    return target_user, active_admin_users


def validate_staff_role_change_target(user: User, *, next_role: str) -> None:
    if user.deleted_at is not None or user.account_status == "deleted":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Deleted accounts cannot have staff roles changed.",
        )
    if user.account_status == "pending_deletion":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Accounts pending deletion cannot have staff roles changed.",
        )
    if user.role == next_role:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This user already has that role.",
        )


def validate_last_active_admin_protection(
    *,
    active_admin_users: list[User],
    target_user: User,
    next_role: str,
) -> None:
    if target_user.role != ADMIN_ROLE or next_role == ADMIN_ROLE:
        return

    target_is_active_admin = (
        target_user.account_status == "active"
        and target_user.deleted_at is None
    )
    if target_is_active_admin and len(active_admin_users) <= 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The last active admin cannot be demoted.",
        )


def change_admin_user_staff_role(
    db: Session,
    *,
    admin_user: User,
    user_id: uuid.UUID,
    payload: AdminUserStaffRoleChangeCreate,
) -> AdminUserStaffRoleChangeResultRead:
    next_role, reason, idempotency_key = normalize_staff_role_change_request(payload)
    existing_action = get_existing_staff_role_change_action(
        db,
        admin_user_id=admin_user.id,
        user_id=user_id,
        idempotency_key=idempotency_key,
    )
    if existing_action is not None:
        return build_staff_role_change_result(
            action=existing_action,
            expected_reason=reason,
            expected_role=next_role,
        )

    target_user, active_admin_users = lock_staff_role_change_users(
        db,
        user_id=user_id,
    )
    existing_action = get_existing_staff_role_change_action(
        db,
        admin_user_id=admin_user.id,
        user_id=user_id,
        idempotency_key=idempotency_key,
    )
    if existing_action is not None:
        return build_staff_role_change_result(
            action=existing_action,
            expected_reason=reason,
            expected_role=next_role,
        )

    validate_staff_role_change_target(target_user, next_role=next_role)
    validate_last_active_admin_protection(
        active_admin_users=active_admin_users,
        target_user=target_user,
        next_role=next_role,
    )

    now = datetime.now(timezone.utc)
    previous_role = target_user.role
    audit_action = record_admin_action(
        db,
        admin_user_id=admin_user.id,
        action_type="change_staff_role",
        target_user_id=target_user.id,
        reason=reason,
        metadata={
            "before": {"role": previous_role},
            "after": {"role": next_role},
        },
        idempotency_key=idempotency_key,
        created_at=now,
    )
    target_user.role = next_role
    target_user.updated_at = now
    db.add(target_user)

    try:
        db.commit()
        db.refresh(target_user)
        return AdminUserStaffRoleChangeResultRead(
            user_id=target_user.id,
            previous_role=previous_role,
            role=target_user.role,
            changed_at=audit_action.created_at,
            admin_action_id=audit_action.id,
        )
    except IntegrityError as exc:
        db.rollback()
        existing_action = get_existing_staff_role_change_action(
            db,
            admin_user_id=admin_user.id,
            user_id=user_id,
            idempotency_key=idempotency_key,
        )
        if existing_action is not None:
            return build_staff_role_change_result(
                action=existing_action,
                expected_reason=reason,
                expected_role=next_role,
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_user_conflict_detail(exc),
        ) from exc
