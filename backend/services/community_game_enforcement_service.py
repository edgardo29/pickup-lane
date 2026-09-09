"""Admin enforcement workflows for Community Games."""

import uuid
from collections.abc import Callable
from datetime import datetime, timezone

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
from backend.services.admin_action_service import (
    integrity_error_matches_constraint,
    record_admin_action,
)
from backend.services.admin_community_service import (
    build_enforcement_state,
    get_community_game_or_404,
    lock_community_game_for_enforcement,
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
COMMUNITY_GAME_ADMIN_CANCELLATION_PUBLIC_REASON = (
    "Cancelled by Pickup Lane for safety or policy reasons."
)


COMMUNITY_NOTICE_COPY = {
    "community_game_hidden": (
        "Community game hidden",
        (
            "Your community game was hidden from public browsing for safety "
            "or policy reasons. Contact support if you believe this was a mistake."
        ),
    ),
    "community_game_restored": (
        "Community game restored",
        "Your community game is visible again.",
    ),
    "community_game_joining_paused": (
        "Joining paused",
        (
            "New joins and guest changes are paused for your community game for "
            "safety or policy reasons. Contact support if you believe this was a "
            "mistake."
        ),
    ),
    "community_game_joining_resumed": (
        "Joining resumed",
        "New joins and guest changes are open again for your community game.",
    ),
    "community_game_cancelled": (
        "Community game cancelled",
        (
            "Your community game was cancelled by Pickup Lane for safety or policy "
            "reasons. Contact support if you believe this was a mistake."
        ),
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
    notice_ids = get_notice_ids_for_action(db, audit_action.id)
    if len(notice_ids) != 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The prior Community Game action result is incomplete.",
        )
    return AdminCommunityGameEnforcementActionResultRead(
        game_id=game.id,
        enforcement_state=build_enforcement_state(game),
        audit_action_id=audit_action.id,
        notice_ids=notice_ids,
        idempotent_replay=idempotent_replay,
    )


def create_host_notice(
    db: Session,
    *,
    game: Game,
    audit_action: AdminAction,
    admin_user: User,
    notice_type: str,
) -> AdminTargetNotice:
    if game.host_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Community game host is unavailable.",
        )

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
    )


def apply_community_game_state_action(
    db: Session,
    *,
    game_id: uuid.UUID,
    admin_user: User,
    payload: AdminCommunityGameEnforcementActionCreate,
    action_type: str,
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

    game = lock_community_game_for_enforcement(db, game.id)

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
    if game.host_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Community game host is unavailable.",
        )

    now = datetime.now(timezone.utc)
    before = {field_name: getattr(game, field_name) for field_name in after}
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
    try:
        link_admin_action_to_open_review_case(db, audit_action)
        create_host_notice(
            db,
            game=game,
            audit_action=audit_action,
            admin_user=admin_user,
            notice_type=notice_type,
        )
        db.add(game)
        db.add(audit_action)
        db.flush()
        db.commit()
        db.refresh(game)
        db.refresh(audit_action)
    except IntegrityError as exc:
        db.rollback()
        if integrity_error_matches_constraint(
            exc,
            "uq_admin_actions_community_game_enforcement_idempotency",
        ):
            existing_action = get_existing_community_game_action(
                db,
                action_type=action_type,
                admin_user_id=admin_user.id,
                game_id=game_id,
                idempotency_key=idempotency_key,
            )
        else:
            existing_action = None
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
    except Exception:
        db.rollback()
        raise

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
    def validate_state(current_game: Game) -> None:
        if (
            current_game.game_status in {"cancelled", "removed"}
            or current_game.public_visibility_status != VISIBLE
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only visible, nonterminal community games can be hidden.",
            )

    return apply_community_game_state_action(
        db,
        game_id=game_id,
        admin_user=admin_user,
        payload=payload,
        action_type="hide_community_game",
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
    def validate_state(current_game: Game) -> None:
        if current_game.game_status in {"cancelled", "removed"}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cancelled or removed community games cannot be restored.",
            )
        if current_game.public_visibility_status != HIDDEN:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only hidden community games can be restored.",
            )

    return apply_community_game_state_action(
        db,
        game_id=game_id,
        admin_user=admin_user,
        payload=payload,
        action_type="restore_community_game",
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
    def validate_state(current_game: Game) -> None:
        if current_game.game_status != "active":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only active community games can pause joining.",
            )
        if current_game.join_enforcement_status != JOIN_OPEN:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only open Community Game joining can be paused.",
            )

    return apply_community_game_state_action(
        db,
        game_id=game_id,
        admin_user=admin_user,
        payload=payload,
        action_type="pause_community_game_joining",
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
    def validate_state(current_game: Game) -> None:
        if current_game.game_status != "active":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only active community games can resume joining.",
            )
        if current_game.join_enforcement_status != JOIN_PAUSED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only paused Community Game joining can be resumed.",
            )

    return apply_community_game_state_action(
        db,
        game_id=game_id,
        admin_user=admin_user,
        payload=payload,
        action_type="resume_community_game_joining",
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

    game = lock_community_game_for_enforcement(db, game.id)
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

    if game.host_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Community game host is unavailable.",
        )

    try:
        game, _payment_summary, _notified_user_ids, audit_action, _money_issue_ids = (
            apply_game_cancellation_state(
                db,
                game,
                GameCancelCreate(
                    cancel_reason=COMMUNITY_GAME_ADMIN_CANCELLATION_PUBLIC_REASON
                ),
                admin_user,
                admin_action_idempotency_key=idempotency_key,
                admin_action_type="admin_cancel_community_game",
                admin_action_reason=reason,
                include_admin_host_notification=False,
            )
        )
        if audit_action is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Community game cancellation audit was not recorded.",
            )
        link_admin_action_to_open_review_case(db, audit_action)
        create_host_notice(
            db,
            game=game,
            audit_action=audit_action,
            admin_user=admin_user,
            notice_type="community_game_cancelled",
        )
        db.add(game)
        db.add(audit_action)
        db.flush()
        db.commit()
        db.refresh(game)
        db.refresh(audit_action)
    except IntegrityError as exc:
        db.rollback()
        existing_action = None
        if integrity_error_matches_constraint(
            exc,
            "uq_admin_actions_community_game_enforcement_idempotency",
        ):
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
    except HTTPException as exc:
        db.rollback()
        if exc.status_code == status.HTTP_400_BAD_REQUEST:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=exc.detail,
            ) from exc
        raise
    except OfficialCancellationCreditFailure as exc:
        abort_official_cancellation_for_credit_failure(
            db,
            admin_user=admin_user,
            failure=exc,
            game_id=game_id,
        )
        raise
    except Exception:
        db.rollback()
        raise

    return build_result(
        db,
        game=game,
        audit_action=audit_action,
        idempotent_replay=False,
    )
