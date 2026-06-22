"""Admin account-status impact previews and mutation workflows."""

import hashlib
import json
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import AdminAction, Game, Notification, User
from backend.schemas.admin_user_schema import (
    AdminUserSuspendCreate,
    AdminUserSuspendResultRead,
    AdminUserSuspensionOfficialHostImpactRead,
    AdminUserSuspensionPreviewRead,
    AdminUserUnsuspendCreate,
    AdminUserUnsuspendResultRead,
)
from backend.services.admin_action_service import record_admin_action
from backend.services.admin_rejected_attempt_policy import (
    ATTEMPT_TYPE_SUSPEND_USER_REJECTED,
    REJECTION_DOMAIN_REJECTED_POSTLOAD,
)
from backend.services.admin_rejected_attempt_service import (
    record_admin_rejected_attempt,
)
from backend.services.admin_user_service import (
    count_active_admins,
    get_admin_user_or_404,
)
from backend.services.notification_service import build_app_notification_fields
from backend.services.user_service import build_user_conflict_detail

FUTURE_OFFICIAL_HOST_GAME_STATUSES = ("scheduled", "full")
SUSPENSION_PREVIEW_HOST_ASSIGNMENT_LIMIT = 100
SUSPEND_USER_ROUTE_PATH = "/admin/users/{user_id}/suspend"
SUSPENSION_BLOCKING_MESSAGES = {
    "deleted": "Deleted accounts cannot be suspended.",
    "pending_deletion": "Accounts pending deletion cannot be suspended.",
    "already_suspended": "This account is already suspended.",
    "not_active": "Only active accounts can be suspended.",
    "last_active_admin": "The last active admin cannot be suspended.",
    "future_official_host": (
        "Remove the user from all future official host assignments before suspension."
    ),
}


def list_future_official_host_assignments(
    db: Session,
    *,
    user_id: uuid.UUID,
    now: datetime,
) -> tuple[list[Game], int]:
    rows = db.execute(
        select(Game, func.count().over())
        .where(
            Game.host_user_id == user_id,
            Game.game_type == "official",
            Game.game_status.in_(FUTURE_OFFICIAL_HOST_GAME_STATUSES),
            Game.starts_at > now,
            Game.deleted_at.is_(None),
        )
        .order_by(Game.starts_at.asc(), Game.id.asc())
        .limit(SUSPENSION_PREVIEW_HOST_ASSIGNMENT_LIMIT)
    ).all()
    return (
        [game for game, _assignment_count in rows],
        int(rows[0][1]) if rows else 0,
    )


def suspension_preview_snapshot_token(
    *,
    user: User,
    active_admin_count: int,
    official_host_assignment_count: int,
    official_host_assignments: list[Game],
) -> str:
    snapshot = {
        "user": {
            "id": str(user.id),
            "role": user.role,
            "account_status": user.account_status,
            "deleted_at": user.deleted_at.isoformat() if user.deleted_at else None,
            "updated_at": user.updated_at.isoformat(),
        },
        "active_admin_count": active_admin_count,
        "future_official_host_assignment_count": official_host_assignment_count,
        "future_official_host_assignments": [
            {
                "id": str(game.id),
                "game_status": game.game_status,
                "starts_at": game.starts_at.isoformat(),
                "host_user_id": (
                    str(game.host_user_id) if game.host_user_id is not None else None
                ),
                "deleted_at": (
                    game.deleted_at.isoformat() if game.deleted_at else None
                ),
                "updated_at": game.updated_at.isoformat(),
            }
            for game in official_host_assignments
        ],
    }
    encoded_snapshot = json.dumps(
        snapshot,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded_snapshot).hexdigest()


def suspension_blocking_reason_codes(
    *,
    user: User,
    active_admin_count: int,
    official_host_assignment_count: int,
) -> list[str]:
    reason_codes: list[str] = []

    if user.deleted_at is not None or user.account_status == "deleted":
        reason_codes.append("deleted")
    elif user.account_status == "pending_deletion":
        reason_codes.append("pending_deletion")
    elif user.account_status == "suspended":
        reason_codes.append("already_suspended")
    elif user.account_status != "active":
        reason_codes.append("not_active")

    if (
        user.role == "admin"
        and user.account_status == "active"
        and user.deleted_at is None
        and active_admin_count <= 1
    ):
        reason_codes.append("last_active_admin")

    if official_host_assignment_count:
        reason_codes.append("future_official_host")

    return reason_codes


def build_admin_user_suspension_preview(
    *,
    user: User,
    active_admin_count: int,
    official_host_assignments: list[Game],
    official_host_assignment_count: int,
) -> AdminUserSuspensionPreviewRead:
    blocking_reason_codes = suspension_blocking_reason_codes(
        user=user,
        active_admin_count=active_admin_count,
        official_host_assignment_count=official_host_assignment_count,
    )
    return AdminUserSuspensionPreviewRead(
        user_id=user.id,
        account_status=user.account_status,
        role=user.role,
        can_suspend=not blocking_reason_codes,
        preview_token=suspension_preview_snapshot_token(
            user=user,
            active_admin_count=active_admin_count,
            official_host_assignment_count=official_host_assignment_count,
            official_host_assignments=official_host_assignments,
        ),
        blocking_reasons=[
            SUSPENSION_BLOCKING_MESSAGES[reason_code]
            for reason_code in blocking_reason_codes
        ],
        future_official_host_assignment_count=official_host_assignment_count,
        future_official_host_assignments=[
            AdminUserSuspensionOfficialHostImpactRead(
                id=game.id,
                title=game.title,
                game_status=game.game_status,
                starts_at=game.starts_at,
                city=game.city_snapshot,
                state=game.state_snapshot,
            )
            for game in official_host_assignments
        ],
    )


def preview_admin_user_suspension(
    db: Session,
    *,
    user_id: uuid.UUID,
) -> AdminUserSuspensionPreviewRead:
    user = get_admin_user_or_404(db, user_id)
    now = datetime.now(timezone.utc)
    (
        official_host_assignments,
        official_host_assignment_count,
    ) = list_future_official_host_assignments(
        db,
        user_id=user.id,
        now=now,
    )
    active_admin_count = count_active_admins(db)
    return build_admin_user_suspension_preview(
        user=user,
        active_admin_count=active_admin_count,
        official_host_assignments=official_host_assignments,
        official_host_assignment_count=official_host_assignment_count,
    )


def normalize_suspend_request(
    payload: AdminUserSuspendCreate,
) -> tuple[str, str]:
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

    return reason, idempotency_key


def get_existing_suspend_action(
    db: Session,
    *,
    admin_user_id: uuid.UUID,
    user_id: uuid.UUID,
    idempotency_key: str,
) -> AdminAction | None:
    return db.scalar(
        select(AdminAction).where(
            AdminAction.admin_user_id == admin_user_id,
            AdminAction.action_type == "suspend_user",
            AdminAction.target_user_id == user_id,
            AdminAction.idempotency_key == idempotency_key,
        )
    )


def build_suspend_result(
    db: Session,
    *,
    action: AdminAction,
    expected_preview_snapshot_hash: str,
    expected_reason: str,
) -> AdminUserSuspendResultRead:
    user = db.get(User, action.target_user_id)
    notification = db.get(Notification, action.target_notification_id)
    metadata = action.metadata_ or {}
    reviewed = metadata.get("reviewed") or {}
    preview_snapshot_hash = reviewed.get("preview_snapshot_hash")
    if user is None or notification is None or not preview_snapshot_hash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The prior suspension result is incomplete.",
        )
    if (
        action.reason != expected_reason
        or preview_snapshot_hash != expected_preview_snapshot_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "idempotency_key was already used for a different "
                "suspension request."
            ),
        )

    return AdminUserSuspendResultRead(
        user_id=user.id,
        account_status="suspended",
        suspended_at=action.created_at,
        admin_action_id=action.id,
        notification_id=notification.id,
    )


def lock_suspension_users(
    db: Session,
    *,
    user_id: uuid.UUID,
) -> tuple[User, int]:
    users = list(
        db.scalars(
            select(User)
            .where(
                or_(
                    User.id == user_id,
                    (
                        (User.role == "admin")
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

    active_admin_count = sum(
        1
        for user in users
        if (
            user.role == "admin"
            and user.account_status == "active"
            and user.deleted_at is None
        )
    )
    return target_user, active_admin_count


def reject_guarded_suspension(
    db: Session,
    *,
    admin_user: User,
    target_user: User,
    reason_codes: list[str],
    official_host_assignment_count: int,
    route_method: str,
    route_path: str,
) -> None:
    record_admin_rejected_attempt(
        db,
        admin_user_id=admin_user.id,
        attempt_type=ATTEMPT_TYPE_SUSPEND_USER_REJECTED,
        rejection_mode=REJECTION_DOMAIN_REJECTED_POSTLOAD,
        response_status_code=status.HTTP_409_CONFLICT,
        route_method=route_method,
        route_path=route_path,
        target_user_id=target_user.id,
        metadata={
            "reason_codes": reason_codes,
            "role": target_user.role,
            "account_status": target_user.account_status,
            "future_official_host_assignment_count": (
                official_host_assignment_count
            ),
        },
    )
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=SUSPENSION_BLOCKING_MESSAGES[reason_codes[0]],
    )


def suspend_admin_user(
    db: Session,
    *,
    admin_user: User,
    user_id: uuid.UUID,
    payload: AdminUserSuspendCreate,
    route_method: str = "POST",
    route_path: str = SUSPEND_USER_ROUTE_PATH,
) -> AdminUserSuspendResultRead:
    reason, idempotency_key = normalize_suspend_request(payload)
    existing_action = get_existing_suspend_action(
        db,
        admin_user_id=admin_user.id,
        user_id=user_id,
        idempotency_key=idempotency_key,
    )
    if existing_action is not None:
        return build_suspend_result(
            db,
            action=existing_action,
            expected_preview_snapshot_hash=payload.preview_token,
            expected_reason=reason,
        )

    target_user, active_admin_count = lock_suspension_users(db, user_id=user_id)
    existing_action = get_existing_suspend_action(
        db,
        admin_user_id=admin_user.id,
        user_id=user_id,
        idempotency_key=idempotency_key,
    )
    if existing_action is not None:
        return build_suspend_result(
            db,
            action=existing_action,
            expected_preview_snapshot_hash=payload.preview_token,
            expected_reason=reason,
        )

    now = datetime.now(timezone.utc)
    (
        official_host_assignments,
        official_host_assignment_count,
    ) = list_future_official_host_assignments(
        db,
        user_id=target_user.id,
        now=now,
    )
    preview = build_admin_user_suspension_preview(
        user=target_user,
        active_admin_count=active_admin_count,
        official_host_assignments=official_host_assignments,
        official_host_assignment_count=official_host_assignment_count,
    )
    reason_codes = suspension_blocking_reason_codes(
        user=target_user,
        active_admin_count=active_admin_count,
        official_host_assignment_count=official_host_assignment_count,
    )
    guarded_reason_codes = [
        reason_code
        for reason_code in reason_codes
        if reason_code in {"last_active_admin", "future_official_host"}
    ]
    if target_user.account_status != "active" or target_user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=preview.blocking_reasons[0],
        )
    if guarded_reason_codes:
        reject_guarded_suspension(
            db,
            admin_user=admin_user,
            target_user=target_user,
            reason_codes=guarded_reason_codes,
            official_host_assignment_count=official_host_assignment_count,
            route_method=route_method,
            route_path=route_path,
        )
    if payload.preview_token != preview.preview_token:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Suspension preview is stale. Refresh the impact before continuing.",
        )

    notification = Notification(
        id=uuid.uuid4(),
        user_id=target_user.id,
        notification_type="account_security",
        notification_category="app",
        notification_domain="account",
        **build_app_notification_fields(
            "account_security",
            event_at=now,
            title="Account suspended",
            summary="Pickup Lane suspended your account.",
            body=(
                "Your Pickup Lane account was suspended. Product and staff "
                "actions are unavailable while the suspension is active. "
                "Contact support if you need help."
            ),
            action_key="view_profile",
        ),
        actor_user_id=(
            None if admin_user.id == target_user.id else admin_user.id
        ),
        is_read=False,
        read_at=None,
        created_at=now,
        updated_at=now,
    )
    db.add(notification)
    db.flush()
    audit_action = record_admin_action(
        db,
        admin_user_id=admin_user.id,
        action_type="suspend_user",
        target_user_id=target_user.id,
        target_notification_id=notification.id,
        reason=reason,
        metadata={
            "before": {"account_status": target_user.account_status},
            "after": {"account_status": "suspended"},
            "reviewed": {"preview_snapshot_hash": preview.preview_token},
        },
        idempotency_key=idempotency_key,
        created_at=now,
    )
    target_user.account_status = "suspended"
    target_user.updated_at = now
    db.add(target_user)

    try:
        db.commit()
        db.refresh(target_user)
        return AdminUserSuspendResultRead(
            user_id=target_user.id,
            account_status=target_user.account_status,
            suspended_at=audit_action.created_at,
            admin_action_id=audit_action.id,
            notification_id=notification.id,
        )
    except IntegrityError as exc:
        db.rollback()
        existing_action = get_existing_suspend_action(
            db,
            admin_user_id=admin_user.id,
            user_id=user_id,
            idempotency_key=idempotency_key,
        )
        if existing_action is not None:
            return build_suspend_result(
                db,
                action=existing_action,
                expected_preview_snapshot_hash=payload.preview_token,
                expected_reason=reason,
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_user_conflict_detail(exc),
        ) from exc


def normalize_unsuspend_request(
    payload: AdminUserUnsuspendCreate,
) -> tuple[str, str]:
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

    return reason, idempotency_key


def get_existing_unsuspend_action(
    db: Session,
    *,
    admin_user_id: uuid.UUID,
    user_id: uuid.UUID,
    idempotency_key: str,
) -> AdminAction | None:
    return db.scalar(
        select(AdminAction).where(
            AdminAction.admin_user_id == admin_user_id,
            AdminAction.action_type == "unsuspend_user",
            AdminAction.target_user_id == user_id,
            AdminAction.idempotency_key == idempotency_key,
        )
    )


def build_unsuspend_result(
    db: Session,
    *,
    action: AdminAction,
    expected_reason: str,
) -> AdminUserUnsuspendResultRead:
    user = db.get(User, action.target_user_id)
    notification = db.get(Notification, action.target_notification_id)
    if user is None or notification is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The prior unsuspension result is incomplete.",
        )
    if action.reason != expected_reason:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "idempotency_key was already used for a different "
                "unsuspension request."
            ),
        )

    return AdminUserUnsuspendResultRead(
        user_id=user.id,
        account_status="active",
        unsuspended_at=action.created_at,
        admin_action_id=action.id,
        notification_id=notification.id,
    )


def get_user_for_unsuspend_or_404(
    db: Session,
    *,
    user_id: uuid.UUID,
) -> User:
    user = db.scalar(
        select(User).where(User.id == user_id).with_for_update()
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )
    return user


def validate_user_can_be_unsuspended(user: User) -> None:
    if user.deleted_at is not None or user.account_status == "deleted":
        detail = "Deleted accounts cannot be unsuspended."
    elif user.account_status == "pending_deletion":
        detail = "Accounts pending deletion cannot be unsuspended."
    elif user.account_status == "active":
        detail = "This account is already active."
    else:
        detail = "Only suspended accounts can be unsuspended."

    if user.account_status != "suspended" or user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        )


def unsuspend_admin_user(
    db: Session,
    *,
    admin_user: User,
    user_id: uuid.UUID,
    payload: AdminUserUnsuspendCreate,
) -> AdminUserUnsuspendResultRead:
    reason, idempotency_key = normalize_unsuspend_request(payload)
    existing_action = get_existing_unsuspend_action(
        db,
        admin_user_id=admin_user.id,
        user_id=user_id,
        idempotency_key=idempotency_key,
    )
    if existing_action is not None:
        return build_unsuspend_result(
            db,
            action=existing_action,
            expected_reason=reason,
        )

    target_user = get_user_for_unsuspend_or_404(db, user_id=user_id)
    existing_action = get_existing_unsuspend_action(
        db,
        admin_user_id=admin_user.id,
        user_id=user_id,
        idempotency_key=idempotency_key,
    )
    if existing_action is not None:
        return build_unsuspend_result(
            db,
            action=existing_action,
            expected_reason=reason,
        )

    validate_user_can_be_unsuspended(target_user)
    now = datetime.now(timezone.utc)
    notification = Notification(
        id=uuid.uuid4(),
        user_id=target_user.id,
        notification_type="account_security",
        notification_category="app",
        notification_domain="account",
        **build_app_notification_fields(
            "account_security",
            event_at=now,
            title="Account access restored",
            summary="Pickup Lane restored your account access.",
            body=(
                "Your Pickup Lane account suspension was removed. You can use "
                "available product features again. Hosting access remains "
                "subject to your current hosting status."
            ),
            action_key="view_profile",
        ),
        actor_user_id=admin_user.id,
        is_read=False,
        read_at=None,
        created_at=now,
        updated_at=now,
    )
    db.add(notification)
    db.flush()
    audit_action = record_admin_action(
        db,
        admin_user_id=admin_user.id,
        action_type="unsuspend_user",
        target_user_id=target_user.id,
        target_notification_id=notification.id,
        reason=reason,
        metadata={
            "before": {"account_status": target_user.account_status},
            "after": {"account_status": "active"},
        },
        idempotency_key=idempotency_key,
        created_at=now,
    )
    target_user.account_status = "active"
    target_user.updated_at = now
    db.add(target_user)

    try:
        db.commit()
        db.refresh(target_user)
        return AdminUserUnsuspendResultRead(
            user_id=target_user.id,
            account_status=target_user.account_status,
            unsuspended_at=audit_action.created_at,
            admin_action_id=audit_action.id,
            notification_id=notification.id,
        )
    except IntegrityError as exc:
        db.rollback()
        existing_action = get_existing_unsuspend_action(
            db,
            admin_user_id=admin_user.id,
            user_id=user_id,
            idempotency_key=idempotency_key,
        )
        if existing_action is not None:
            return build_unsuspend_result(
                db,
                action=existing_action,
                expected_reason=reason,
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_user_conflict_detail(exc),
        ) from exc
