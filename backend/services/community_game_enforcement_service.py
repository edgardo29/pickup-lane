"""Admin enforcement workflows for Community Games."""

import uuid
from datetime import datetime, timezone
from typing import Callable

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import AdminAction, AdminTargetNotice, Game, User
from backend.schemas.admin_community_schema import (
    AdminCommunityGameEnforcementActionCreate,
    AdminCommunityGameEnforcementActionResultRead,
)
from backend.schemas.game_schema import GameCancelCreate
from backend.services.admin_action_service import record_admin_action
from backend.services.admin_community_service import (
    build_enforcement_state,
    get_community_game_or_404,
)
from backend.services.admin_record_rules import (
    normalize_idempotency_key,
    normalize_optional_text,
)
from backend.services.admin_review_service import link_admin_action_to_open_review_case
from backend.services.admin_target_notice_service import create_admin_target_notice
from backend.services.auth_service import require_active_admin_user
from backend.services.game_cancellation_service import (
    OfficialCancellationCreditFailure,
    abort_official_cancellation_for_credit_failure,
    apply_game_cancellation_state,
)

VISIBLE = "visible"
HIDDEN = "hidden"
JOIN_OPEN = "open"
JOIN_PAUSED = "paused"


COMMUNITY_NOTICE_COPY = {
    "community_game_hidden": (
        "Community game hidden",
        "Your community game is hidden from public browsing while an admin review is active.",
    ),
    "community_game_restored": (
        "Community game restored",
        "Your community game is visible again.",
    ),
    "community_game_joining_paused": (
        "Joining paused",
        "New joins and guest changes are paused for your community game.",
    ),
    "community_game_joining_resumed": (
        "Joining resumed",
        "New joins and guest changes are open again for your community game.",
    ),
    "community_game_cancelled": (
        "Community game cancelled",
        "Your community game was cancelled by Pickup Lane admin.",
    ),
}


def normalize_enforcement_request(
    payload: AdminCommunityGameEnforcementActionCreate,
) -> tuple[str, str]:
    reason = normalize_optional_text(payload.reason, "reason")
    if reason is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="reason is required.",
        )

    idempotency_key = normalize_idempotency_key(payload.idempotency_key)
    if idempotency_key is None or len(idempotency_key) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="idempotency_key must be at least 8 characters.",
        )

    return reason, idempotency_key


def get_existing_community_game_action(
    db: Session,
    *,
    action_type: str,
    admin_user_id: uuid.UUID,
    game_id: uuid.UUID,
    idempotency_key: str,
) -> AdminAction | None:
    return db.scalar(
        select(AdminAction)
        .where(
            AdminAction.action_type == action_type,
            AdminAction.admin_user_id == admin_user_id,
            AdminAction.target_game_id == game_id,
            AdminAction.idempotency_key == idempotency_key,
        )
        .order_by(AdminAction.created_at.desc(), AdminAction.id.desc())
        .limit(1)
    )


def validate_existing_action(action: AdminAction, *, expected_reason: str) -> None:
    if action.reason != expected_reason:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="idempotency_key was already used for a different action.",
        )


def get_notice_ids_for_action(db: Session, action_id: uuid.UUID) -> list[uuid.UUID]:
    return list(
        db.scalars(
            select(AdminTargetNotice.id)
            .where(AdminTargetNotice.admin_action_id == action_id)
            .order_by(AdminTargetNotice.created_at.asc(), AdminTargetNotice.id.asc())
        ).all()
    )


def build_result(
    db: Session,
    *,
    game: Game,
    audit_action: AdminAction,
    idempotent_replay: bool,
) -> AdminCommunityGameEnforcementActionResultRead:
    return AdminCommunityGameEnforcementActionResultRead(
        game_id=game.id,
        enforcement_state=build_enforcement_state(game),
        audit_action_id=audit_action.id,
        notice_ids=get_notice_ids_for_action(db, audit_action.id),
        idempotent_replay=idempotent_replay,
    )


def create_host_notice(
    db: Session,
    *,
    game: Game,
    audit_action: AdminAction,
    admin_user: User,
    notice_type: str,
    reason: str,
) -> AdminTargetNotice | None:
    if game.host_user_id is None:
        return None

    title, body = COMMUNITY_NOTICE_COPY[notice_type]
    return create_admin_target_notice(
        db,
        notice_type=notice_type,
        title=title,
        body=body,
        recipient_user_id=game.host_user_id,
        target_user_id=game.host_user_id,
        target_game_id=game.id,
        admin_action=audit_action,
        created_by_user_id=admin_user.id,
        user_safe_reason=reason,
    )


def update_action_notice_metadata(
    audit_action: AdminAction,
    notice_ids: list[uuid.UUID],
) -> None:
    metadata = dict(audit_action.metadata_ or {})
    metadata["notice_ids"] = [str(notice_id) for notice_id in notice_ids]
    audit_action.metadata_ = metadata


def apply_community_game_state_action(
    db: Session,
    *,
    game_id: uuid.UUID,
    admin_user: User,
    payload: AdminCommunityGameEnforcementActionCreate,
    action_type: str,
    before: dict[str, object],
    after: dict[str, object],
    notice_type: str,
    state_validator: Callable[[Game], None] | None = None,
) -> AdminCommunityGameEnforcementActionResultRead:
    require_active_admin_user(admin_user)
    reason, idempotency_key = normalize_enforcement_request(payload)
    game = get_community_game_or_404(db, game_id)

    existing_action = get_existing_community_game_action(
        db,
        action_type=action_type,
        admin_user_id=admin_user.id,
        game_id=game.id,
        idempotency_key=idempotency_key,
    )
    if existing_action is not None:
        validate_existing_action(existing_action, expected_reason=reason)
        return build_result(
            db,
            game=game,
            audit_action=existing_action,
            idempotent_replay=True,
        )

    locked_game = db.scalar(
        select(Game).where(Game.id == game.id).with_for_update()
    )
    if locked_game is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Community game not found.",
        )
    game = locked_game

    existing_action = get_existing_community_game_action(
        db,
        action_type=action_type,
        admin_user_id=admin_user.id,
        game_id=game.id,
        idempotency_key=idempotency_key,
    )
    if existing_action is not None:
        validate_existing_action(existing_action, expected_reason=reason)
        return build_result(
            db,
            game=game,
            audit_action=existing_action,
            idempotent_replay=True,
        )

    if state_validator is not None:
        state_validator(game)

    now = datetime.now(timezone.utc)
    for field_name, field_value in after.items():
        setattr(game, field_name, field_value)
    game.updated_at = now
    audit_action = record_admin_action(
        db,
        admin_user_id=admin_user.id,
        action_type=action_type,
        target_game_id=game.id,
        target_user_id=game.host_user_id,
        reason=reason,
        metadata={
            "source": "admin_community_game_enforcement",
            "before": before,
            "after": after,
        },
        idempotency_key=idempotency_key,
        created_at=now,
    )
    link_admin_action_to_open_review_case(db, audit_action)
    notice = create_host_notice(
        db,
        game=game,
        audit_action=audit_action,
        admin_user=admin_user,
        notice_type=notice_type,
        reason=reason,
    )
    db.flush()
    notice_ids = [notice.id] if notice is not None else []
    update_action_notice_metadata(audit_action, notice_ids)

    try:
        db.add(game)
        db.add(audit_action)
        db.commit()
        db.refresh(game)
        db.refresh(audit_action)
    except IntegrityError as exc:
        db.rollback()
        existing_action = get_existing_community_game_action(
            db,
            action_type=action_type,
            admin_user_id=admin_user.id,
            game_id=game_id,
            idempotency_key=idempotency_key,
        )
        if existing_action is not None:
            validate_existing_action(existing_action, expected_reason=reason)
            game = get_community_game_or_404(db, game_id)
            return build_result(
                db,
                game=game,
                audit_action=existing_action,
                idempotent_replay=True,
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Community game action could not be applied.",
        ) from exc

    return build_result(
        db,
        game=game,
        audit_action=audit_action,
        idempotent_replay=False,
    )


def hide_community_game(
    db: Session,
    *,
    game_id: uuid.UUID,
    admin_user: User,
    payload: AdminCommunityGameEnforcementActionCreate,
) -> AdminCommunityGameEnforcementActionResultRead:
    game = get_community_game_or_404(db, game_id)

    def validate_state(current_game: Game) -> None:
        if current_game.public_visibility_status == HIDDEN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Community game is already hidden.",
            )

    return apply_community_game_state_action(
        db,
        game_id=game_id,
        admin_user=admin_user,
        payload=payload,
        action_type="hide_community_game",
        before={"public_visibility_status": game.public_visibility_status},
        after={"public_visibility_status": HIDDEN},
        notice_type="community_game_hidden",
        state_validator=validate_state,
    )


def restore_community_game(
    db: Session,
    *,
    game_id: uuid.UUID,
    admin_user: User,
    payload: AdminCommunityGameEnforcementActionCreate,
) -> AdminCommunityGameEnforcementActionResultRead:
    game = get_community_game_or_404(db, game_id)

    def validate_state(current_game: Game) -> None:
        if current_game.game_status in {"cancelled", "removed"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cancelled or removed community games cannot be restored.",
            )
        if current_game.public_visibility_status == VISIBLE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Community game is already visible.",
            )

    return apply_community_game_state_action(
        db,
        game_id=game_id,
        admin_user=admin_user,
        payload=payload,
        action_type="restore_community_game",
        before={"public_visibility_status": game.public_visibility_status},
        after={"public_visibility_status": VISIBLE},
        notice_type="community_game_restored",
        state_validator=validate_state,
    )


def pause_community_game_joining(
    db: Session,
    *,
    game_id: uuid.UUID,
    admin_user: User,
    payload: AdminCommunityGameEnforcementActionCreate,
) -> AdminCommunityGameEnforcementActionResultRead:
    game = get_community_game_or_404(db, game_id)

    def validate_state(current_game: Game) -> None:
        if current_game.game_status != "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only active community games can pause joining.",
            )
        if current_game.join_enforcement_status == JOIN_PAUSED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Community game joining is already paused.",
            )

    return apply_community_game_state_action(
        db,
        game_id=game_id,
        admin_user=admin_user,
        payload=payload,
        action_type="pause_community_game_joining",
        before={"join_enforcement_status": game.join_enforcement_status},
        after={"join_enforcement_status": JOIN_PAUSED},
        notice_type="community_game_joining_paused",
        state_validator=validate_state,
    )


def resume_community_game_joining(
    db: Session,
    *,
    game_id: uuid.UUID,
    admin_user: User,
    payload: AdminCommunityGameEnforcementActionCreate,
) -> AdminCommunityGameEnforcementActionResultRead:
    game = get_community_game_or_404(db, game_id)

    def validate_state(current_game: Game) -> None:
        if current_game.game_status in {"cancelled", "removed"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cancelled or removed community games cannot resume joining.",
            )
        if current_game.join_enforcement_status == JOIN_OPEN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Community game joining is already open.",
            )

    return apply_community_game_state_action(
        db,
        game_id=game_id,
        admin_user=admin_user,
        payload=payload,
        action_type="resume_community_game_joining",
        before={"join_enforcement_status": game.join_enforcement_status},
        after={"join_enforcement_status": JOIN_OPEN},
        notice_type="community_game_joining_resumed",
        state_validator=validate_state,
    )


def admin_cancel_community_game(
    db: Session,
    *,
    game_id: uuid.UUID,
    admin_user: User,
    payload: AdminCommunityGameEnforcementActionCreate,
) -> AdminCommunityGameEnforcementActionResultRead:
    require_active_admin_user(admin_user)
    reason, idempotency_key = normalize_enforcement_request(payload)
    game = get_community_game_or_404(db, game_id)
    existing_action = get_existing_community_game_action(
        db,
        action_type="admin_cancel_community_game",
        admin_user_id=admin_user.id,
        game_id=game.id,
        idempotency_key=idempotency_key,
    )
    if existing_action is not None:
        validate_existing_action(existing_action, expected_reason=reason)
        return build_result(
            db,
            game=game,
            audit_action=existing_action,
            idempotent_replay=True,
        )

    locked_game = db.scalar(
        select(Game).where(Game.id == game.id).with_for_update()
    )
    if locked_game is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Community game not found.",
        )
    game = locked_game
    existing_action = get_existing_community_game_action(
        db,
        action_type="admin_cancel_community_game",
        admin_user_id=admin_user.id,
        game_id=game.id,
        idempotency_key=idempotency_key,
    )
    if existing_action is not None:
        validate_existing_action(existing_action, expected_reason=reason)
        return build_result(
            db,
            game=game,
            audit_action=existing_action,
            idempotent_replay=True,
        )

    try:
        game, _payment_summary, _notified_user_ids, audit_action, _support_flags = (
            apply_game_cancellation_state(
                db,
                game,
                GameCancelCreate(cancel_reason=reason),
                admin_user,
                admin_action_idempotency_key=idempotency_key,
                admin_action_type="admin_cancel_community_game",
            )
        )
    except OfficialCancellationCreditFailure as exc:
        abort_official_cancellation_for_credit_failure(
            db,
            admin_user=admin_user,
            failure=exc,
            game_id=game_id,
        )
        raise
    if audit_action is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Community game cancellation audit was not recorded.",
        )
    link_admin_action_to_open_review_case(db, audit_action)

    notice = create_host_notice(
        db,
        game=game,
        audit_action=audit_action,
        admin_user=admin_user,
        notice_type="community_game_cancelled",
        reason=reason,
    )
    db.flush()
    notice_ids = [notice.id] if notice is not None else []
    update_action_notice_metadata(audit_action, notice_ids)

    try:
        db.add(game)
        db.add(audit_action)
        db.commit()
        db.refresh(game)
        db.refresh(audit_action)
    except IntegrityError as exc:
        db.rollback()
        existing_action = get_existing_community_game_action(
            db,
            action_type="admin_cancel_community_game",
            admin_user_id=admin_user.id,
            game_id=game_id,
            idempotency_key=idempotency_key,
        )
        if existing_action is not None:
            validate_existing_action(existing_action, expected_reason=reason)
            game = get_community_game_or_404(db, game_id)
            return build_result(
                db,
                game=game,
                audit_action=existing_action,
                idempotent_replay=True,
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Community game could not be cancelled.",
        ) from exc

    return build_result(
        db,
        game=game,
        audit_action=audit_action,
        idempotent_replay=False,
    )
