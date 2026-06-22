"""Admin hosting-status impact previews and mutation workflows."""

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import AdminAction, Game, Notification, User
from backend.schemas.admin_user_schema import (
    AdminUserHostingRestrictionGameImpactRead,
    AdminUserHostingRestrictionPreviewRead,
    AdminUserRestrictHostingCreate,
    AdminUserRestrictHostingResultRead,
    AdminUserRestoreHostingCreate,
    AdminUserRestoreHostingResultRead,
)
from backend.services.admin_action_service import record_admin_action
from backend.services.admin_user_service import get_admin_user_or_404
from backend.services.hosting_access_service import (
    HOSTING_STATUS_BANNED,
    HOSTING_STATUS_ELIGIBLE,
    HOSTING_STATUS_NOT_ELIGIBLE,
    HOSTING_STATUS_PENDING_REVIEW,
    HOSTING_STATUS_RESTRICTED,
    HOSTING_STATUS_SUSPENDED,
)
from backend.services.notification_service import build_app_notification_fields
from backend.services.user_service import build_user_conflict_detail

FUTURE_COMMUNITY_HOST_GAME_STATUSES = ("scheduled", "full")
HOSTING_RESTRICTION_PREVIEW_GAME_LIMIT = 100
HOSTING_RESTRICTION_BLOCKING_MESSAGES = {
    "deleted": "Deleted accounts cannot have hosting restricted.",
    "pending_deletion": "Accounts pending deletion cannot have hosting restricted.",
    "already_restricted": "This user's hosting access is already restricted.",
    "not_eligible": "This user is not currently eligible to host.",
    "pending_review": "Hosting access pending review cannot be restricted.",
    "hosting_suspended": "Suspended hosting access cannot be restricted.",
    "banned_from_hosting": "Banned hosting access cannot be restricted.",
}
HOSTING_RESTORATION_BLOCKING_MESSAGES = {
    "deleted": "Deleted accounts cannot have hosting restored.",
    "pending_deletion": "Accounts pending deletion cannot have hosting restored.",
    "already_eligible": "This user's hosting access is already eligible.",
    "not_eligible": "Only restricted hosting access can be restored.",
    "pending_review": "Hosting access pending review cannot be restored by this workflow.",
    "hosting_suspended": "Suspended hosting access cannot be restored by this workflow.",
    "banned_from_hosting": "Banned hosting access cannot be restored by this workflow.",
}


@dataclass(frozen=True)
class FutureCommunityHostedGame:
    id: uuid.UUID
    title: str
    game_status: str
    publish_status: str
    starts_at: datetime
    city: str
    state: str
    host_user_id: uuid.UUID | None
    deleted_at: datetime | None
    updated_at: datetime


def list_future_community_hosted_games(
    db: Session,
    *,
    user_id: uuid.UUID,
    now: datetime,
) -> list[FutureCommunityHostedGame]:
    rows = db.execute(
        select(
            Game.id,
            Game.title,
            Game.game_status,
            Game.publish_status,
            Game.starts_at,
            Game.city_snapshot,
            Game.state_snapshot,
            Game.host_user_id,
            Game.deleted_at,
            Game.updated_at,
        )
        .where(
            Game.host_user_id == user_id,
            Game.game_type == "community",
            Game.publish_status == "published",
            Game.game_status.in_(FUTURE_COMMUNITY_HOST_GAME_STATUSES),
            Game.starts_at > now,
            Game.deleted_at.is_(None),
        )
        .order_by(Game.starts_at.asc(), Game.id.asc())
    ).all()
    return [
        FutureCommunityHostedGame(
            id=row.id,
            title=row.title,
            game_status=row.game_status,
            publish_status=row.publish_status,
            starts_at=row.starts_at,
            city=row.city_snapshot,
            state=row.state_snapshot,
            host_user_id=row.host_user_id,
            deleted_at=row.deleted_at,
            updated_at=row.updated_at,
        )
        for row in rows
    ]


def hosting_restriction_blocking_reason_codes(user: User) -> list[str]:
    if user.deleted_at is not None or user.account_status == "deleted":
        return ["deleted"]
    if user.account_status == "pending_deletion":
        return ["pending_deletion"]
    if user.hosting_status == HOSTING_STATUS_ELIGIBLE:
        return []

    return [
        {
            HOSTING_STATUS_RESTRICTED: "already_restricted",
            HOSTING_STATUS_NOT_ELIGIBLE: "not_eligible",
            HOSTING_STATUS_PENDING_REVIEW: "pending_review",
            HOSTING_STATUS_SUSPENDED: "hosting_suspended",
            HOSTING_STATUS_BANNED: "banned_from_hosting",
        }.get(user.hosting_status, "not_eligible")
    ]


def hosting_restriction_preview_snapshot_token(
    *,
    user: User,
    future_games: list[FutureCommunityHostedGame],
) -> str:
    snapshot = {
        "user": {
            "id": str(user.id),
            "account_status": user.account_status,
            "hosting_status": user.hosting_status,
            "hosting_suspended_until": (
                user.hosting_suspended_until.isoformat()
                if user.hosting_suspended_until
                else None
            ),
            "deleted_at": user.deleted_at.isoformat() if user.deleted_at else None,
            "updated_at": user.updated_at.isoformat(),
        },
        "future_community_game_count": len(future_games),
        "future_community_games": [
            {
                "id": str(game.id),
                "publish_status": game.publish_status,
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
            for game in future_games
        ],
    }
    encoded_snapshot = json.dumps(
        snapshot,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded_snapshot).hexdigest()


def build_admin_user_hosting_restriction_preview(
    *,
    user: User,
    future_games: list[FutureCommunityHostedGame],
) -> AdminUserHostingRestrictionPreviewRead:
    displayed_future_games = future_games[:HOSTING_RESTRICTION_PREVIEW_GAME_LIMIT]
    blocking_reason_codes = hosting_restriction_blocking_reason_codes(user)

    return AdminUserHostingRestrictionPreviewRead(
        user_id=user.id,
        account_status=user.account_status,
        hosting_status=user.hosting_status,
        can_restrict=not blocking_reason_codes,
        preview_token=hosting_restriction_preview_snapshot_token(
            user=user,
            future_games=future_games,
        ),
        blocking_reasons=[
            HOSTING_RESTRICTION_BLOCKING_MESSAGES[reason_code]
            for reason_code in blocking_reason_codes
        ],
        future_community_game_count=len(future_games),
        future_community_games=[
            AdminUserHostingRestrictionGameImpactRead(
                id=game.id,
                title=game.title,
                game_status=game.game_status,
                starts_at=game.starts_at,
                city=game.city,
                state=game.state,
            )
            for game in displayed_future_games
        ],
    )


def preview_admin_user_hosting_restriction(
    db: Session,
    *,
    user_id: uuid.UUID,
) -> AdminUserHostingRestrictionPreviewRead:
    user = get_admin_user_or_404(db, user_id)
    future_games = list_future_community_hosted_games(
        db,
        user_id=user.id,
        now=datetime.now(timezone.utc),
    )
    return build_admin_user_hosting_restriction_preview(
        user=user,
        future_games=future_games,
    )


def normalize_hosting_action_request(
    *,
    reason_value: str,
    idempotency_key_value: str,
) -> tuple[str, str]:
    reason = " ".join(reason_value.strip().split())
    if not reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="reason is required.",
        )

    idempotency_key = idempotency_key_value.strip()
    if len(idempotency_key) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="idempotency_key must be at least 8 characters.",
        )

    return reason, idempotency_key


def normalize_restrict_hosting_request(
    payload: AdminUserRestrictHostingCreate,
) -> tuple[str, str]:
    return normalize_hosting_action_request(
        reason_value=payload.reason,
        idempotency_key_value=payload.idempotency_key,
    )


def normalize_restore_hosting_request(
    payload: AdminUserRestoreHostingCreate,
) -> tuple[str, str]:
    return normalize_hosting_action_request(
        reason_value=payload.reason,
        idempotency_key_value=payload.idempotency_key,
    )


def get_existing_restrict_hosting_action(
    db: Session,
    *,
    admin_user_id: uuid.UUID,
    user_id: uuid.UUID,
    idempotency_key: str,
) -> AdminAction | None:
    return db.scalar(
        select(AdminAction).where(
            AdminAction.admin_user_id == admin_user_id,
            AdminAction.action_type == "restrict_hosting",
            AdminAction.target_user_id == user_id,
            AdminAction.idempotency_key == idempotency_key,
        )
    )


def get_existing_restore_hosting_action(
    db: Session,
    *,
    admin_user_id: uuid.UUID,
    user_id: uuid.UUID,
    idempotency_key: str,
) -> AdminAction | None:
    return db.scalar(
        select(AdminAction).where(
            AdminAction.admin_user_id == admin_user_id,
            AdminAction.action_type == "restore_hosting",
            AdminAction.target_user_id == user_id,
            AdminAction.idempotency_key == idempotency_key,
        )
    )


def build_restrict_hosting_result(
    db: Session,
    *,
    action: AdminAction,
    expected_preview_snapshot_hash: str,
    expected_reason: str,
) -> AdminUserRestrictHostingResultRead:
    user = db.get(User, action.target_user_id)
    notification = db.get(Notification, action.target_notification_id)
    metadata = action.metadata_ or {}
    reviewed = metadata.get("reviewed") or {}
    preview_snapshot_hash = reviewed.get("preview_snapshot_hash")
    if user is None or notification is None or not preview_snapshot_hash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The prior hosting restriction result is incomplete.",
        )
    if (
        action.reason != expected_reason
        or preview_snapshot_hash != expected_preview_snapshot_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "idempotency_key was already used for a different "
                "hosting restriction request."
            ),
        )

    return AdminUserRestrictHostingResultRead(
        user_id=user.id,
        hosting_status="restricted",
        restricted_at=action.created_at,
        admin_action_id=action.id,
        notification_id=notification.id,
    )


def build_restore_hosting_result(
    db: Session,
    *,
    action: AdminAction,
    expected_reason: str,
) -> AdminUserRestoreHostingResultRead:
    user = db.get(User, action.target_user_id)
    notification = db.get(Notification, action.target_notification_id)
    if user is None or notification is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The prior hosting restoration result is incomplete.",
        )
    if action.reason != expected_reason:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "idempotency_key was already used for a different "
                "hosting restoration request."
            ),
        )

    return AdminUserRestoreHostingResultRead(
        user_id=user.id,
        hosting_status="eligible",
        restored_at=action.created_at,
        admin_action_id=action.id,
        notification_id=notification.id,
    )


def get_locked_admin_user_or_404(
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


def hosting_restoration_blocking_reason_codes(user: User) -> list[str]:
    if user.deleted_at is not None or user.account_status == "deleted":
        return ["deleted"]
    if user.account_status == "pending_deletion":
        return ["pending_deletion"]
    if user.hosting_status == HOSTING_STATUS_RESTRICTED:
        return []

    return [
        {
            HOSTING_STATUS_ELIGIBLE: "already_eligible",
            HOSTING_STATUS_NOT_ELIGIBLE: "not_eligible",
            HOSTING_STATUS_PENDING_REVIEW: "pending_review",
            HOSTING_STATUS_SUSPENDED: "hosting_suspended",
            HOSTING_STATUS_BANNED: "banned_from_hosting",
        }.get(user.hosting_status, "not_eligible")
    ]


def restrict_admin_user_hosting(
    db: Session,
    *,
    admin_user: User,
    user_id: uuid.UUID,
    payload: AdminUserRestrictHostingCreate,
) -> AdminUserRestrictHostingResultRead:
    reason, idempotency_key = normalize_restrict_hosting_request(payload)
    existing_action = get_existing_restrict_hosting_action(
        db,
        admin_user_id=admin_user.id,
        user_id=user_id,
        idempotency_key=idempotency_key,
    )
    if existing_action is not None:
        return build_restrict_hosting_result(
            db,
            action=existing_action,
            expected_preview_snapshot_hash=payload.preview_token,
            expected_reason=reason,
        )

    target_user = get_locked_admin_user_or_404(db, user_id=user_id)
    existing_action = get_existing_restrict_hosting_action(
        db,
        admin_user_id=admin_user.id,
        user_id=user_id,
        idempotency_key=idempotency_key,
    )
    if existing_action is not None:
        return build_restrict_hosting_result(
            db,
            action=existing_action,
            expected_preview_snapshot_hash=payload.preview_token,
            expected_reason=reason,
        )

    now = datetime.now(timezone.utc)
    future_games = list_future_community_hosted_games(
        db,
        user_id=target_user.id,
        now=now,
    )
    preview = build_admin_user_hosting_restriction_preview(
        user=target_user,
        future_games=future_games,
    )
    if not preview.can_restrict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=preview.blocking_reasons[0],
        )
    if payload.preview_token != preview.preview_token:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Hosting restriction preview is stale. "
                "Refresh the impact before continuing."
            ),
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
            title="Hosting restricted",
            summary="Pickup Lane restricted your hosting access.",
            body=(
                "Your Pickup Lane account cannot publish new community games "
                "right now. Existing hosted games remain available to manage. "
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
        action_type="restrict_hosting",
        target_user_id=target_user.id,
        target_notification_id=notification.id,
        reason=reason,
        metadata={
            "before": {
                "hosting_status": target_user.hosting_status,
                "hosting_suspended_until": (
                    target_user.hosting_suspended_until.isoformat()
                    if target_user.hosting_suspended_until
                    else None
                ),
            },
            "after": {
                "hosting_status": HOSTING_STATUS_RESTRICTED,
                "hosting_suspended_until": None,
            },
            "reviewed": {
                "future_community_game_count": len(future_games),
                "preview_snapshot_hash": preview.preview_token,
            },
        },
        idempotency_key=idempotency_key,
        created_at=now,
    )
    target_user.hosting_status = HOSTING_STATUS_RESTRICTED
    target_user.hosting_suspended_until = None
    target_user.updated_at = now
    db.add(target_user)

    try:
        db.commit()
        db.refresh(target_user)
        return AdminUserRestrictHostingResultRead(
            user_id=target_user.id,
            hosting_status=target_user.hosting_status,
            restricted_at=audit_action.created_at,
            admin_action_id=audit_action.id,
            notification_id=notification.id,
        )
    except IntegrityError as exc:
        db.rollback()
        existing_action = get_existing_restrict_hosting_action(
            db,
            admin_user_id=admin_user.id,
            user_id=user_id,
            idempotency_key=idempotency_key,
        )
        if existing_action is not None:
            return build_restrict_hosting_result(
                db,
                action=existing_action,
                expected_preview_snapshot_hash=payload.preview_token,
                expected_reason=reason,
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_user_conflict_detail(exc),
        ) from exc


def restore_admin_user_hosting(
    db: Session,
    *,
    admin_user: User,
    user_id: uuid.UUID,
    payload: AdminUserRestoreHostingCreate,
) -> AdminUserRestoreHostingResultRead:
    reason, idempotency_key = normalize_restore_hosting_request(payload)
    existing_action = get_existing_restore_hosting_action(
        db,
        admin_user_id=admin_user.id,
        user_id=user_id,
        idempotency_key=idempotency_key,
    )
    if existing_action is not None:
        return build_restore_hosting_result(
            db,
            action=existing_action,
            expected_reason=reason,
        )

    target_user = get_locked_admin_user_or_404(db, user_id=user_id)
    existing_action = get_existing_restore_hosting_action(
        db,
        admin_user_id=admin_user.id,
        user_id=user_id,
        idempotency_key=idempotency_key,
    )
    if existing_action is not None:
        return build_restore_hosting_result(
            db,
            action=existing_action,
            expected_reason=reason,
        )

    blocking_reason_codes = hosting_restoration_blocking_reason_codes(target_user)
    if blocking_reason_codes:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=HOSTING_RESTORATION_BLOCKING_MESSAGES[
                blocking_reason_codes[0]
            ],
        )

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
            title="Hosting restored",
            summary="Pickup Lane restored your hosting access.",
            body=(
                "Your Pickup Lane hosting access was restored. "
                "You can publish community games when your account also meets "
                "normal account and verification requirements."
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
        action_type="restore_hosting",
        target_user_id=target_user.id,
        target_notification_id=notification.id,
        reason=reason,
        metadata={
            "before": {
                "hosting_status": target_user.hosting_status,
                "hosting_suspended_until": (
                    target_user.hosting_suspended_until.isoformat()
                    if target_user.hosting_suspended_until
                    else None
                ),
            },
            "after": {
                "hosting_status": HOSTING_STATUS_ELIGIBLE,
                "hosting_suspended_until": None,
            },
        },
        idempotency_key=idempotency_key,
        created_at=now,
    )
    target_user.hosting_status = HOSTING_STATUS_ELIGIBLE
    target_user.hosting_suspended_until = None
    target_user.updated_at = now
    db.add(target_user)

    try:
        db.commit()
        db.refresh(target_user)
        return AdminUserRestoreHostingResultRead(
            user_id=target_user.id,
            hosting_status=target_user.hosting_status,
            restored_at=audit_action.created_at,
            admin_action_id=audit_action.id,
            notification_id=notification.id,
        )
    except IntegrityError as exc:
        db.rollback()
        existing_action = get_existing_restore_hosting_action(
            db,
            admin_user_id=admin_user.id,
            user_id=user_id,
            idempotency_key=idempotency_key,
        )
        if existing_action is not None:
            return build_restore_hosting_result(
                db,
                action=existing_action,
                expected_reason=reason,
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_user_conflict_detail(exc),
        ) from exc
