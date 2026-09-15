"""Audit game-scoped administrative financial reads before protected loading."""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Game, GameParticipant, User
from backend.services.admin_action_service import record_financial_sensitive_read
from backend.services.admin_community_service import get_admin_community_game_detail
from backend.services.game_cancellation_service import (
    build_official_game_cancellation_preview,
)
from backend.services.official_game_player_removal_service import (
    preview_official_game_player_removal,
)
from backend.services.official_game_query_service import (
    get_official_game_money,
    list_official_game_bookings,
    list_official_game_waitlist_entries,
)


def _precheck_game(db: Session, *, game_id: uuid.UUID, game_type: str) -> None:
    game_ref = db.execute(
        select(Game.id, Game.game_type, Game.deleted_at).where(Game.id == game_id)
    ).one_or_none()
    if (
        game_ref is None
        or game_ref.deleted_at is not None
        or game_ref.game_type != game_type
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Official game not found."
                if game_type == "official"
                else "Community game not found."
            ),
        )


def read_official_game_bookings(
    db: Session, *, admin: User, game_id: uuid.UUID, limit: int, offset: int
):
    _precheck_game(db, game_id=game_id, game_type="official")
    record_financial_sensitive_read(
        authenticated_admin_id=admin.id,
        action_type="read_admin_official_game_bookings",
        target_id=game_id,
    )
    return list_official_game_bookings(db, game_id, limit=limit, offset=offset)


def read_official_game_waitlist(
    db: Session, *, admin: User, game_id: uuid.UUID, limit: int, offset: int
):
    _precheck_game(db, game_id=game_id, game_type="official")
    record_financial_sensitive_read(
        authenticated_admin_id=admin.id,
        action_type="read_admin_official_game_waitlist",
        target_id=game_id,
    )
    return list_official_game_waitlist_entries(db, game_id, limit=limit, offset=offset)


def read_official_game_money(db: Session, *, admin: User, game_id: uuid.UUID):
    _precheck_game(db, game_id=game_id, game_type="official")
    record_financial_sensitive_read(
        authenticated_admin_id=admin.id,
        action_type="read_admin_official_game_money",
        target_id=game_id,
    )
    return get_official_game_money(db, game_id)


def read_official_game_cancellation_preview(
    db: Session, *, admin: User, game_id: uuid.UUID
):
    _precheck_game(db, game_id=game_id, game_type="official")
    record_financial_sensitive_read(
        authenticated_admin_id=admin.id,
        action_type="read_admin_official_game_cancel_preview",
        target_id=game_id,
    )
    return build_official_game_cancellation_preview(
        db, game_id=game_id, admin_user=admin
    )


def read_official_game_removal_preview(
    db: Session, *, admin: User, game_id: uuid.UUID, participant_id: uuid.UUID
):
    _precheck_game(db, game_id=game_id, game_type="official")
    participant_ref = db.execute(
        select(GameParticipant.id, GameParticipant.game_id).where(
            GameParticipant.id == participant_id
        )
    ).one_or_none()
    if participant_ref is None or participant_ref.game_id != game_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Official game participant not found.",
        )
    record_financial_sensitive_read(
        authenticated_admin_id=admin.id,
        action_type="read_admin_official_game_remove_preview",
        target_id=participant_id,
    )
    return preview_official_game_player_removal(
        db, game_id=game_id, participant_id=participant_id
    )


def read_admin_community_game_detail(
    db: Session,
    *,
    admin: User,
    game_id: uuid.UUID,
    support_flag_offset: int,
    support_flag_limit: int,
    audit_offset: int,
    audit_limit: int,
):
    _precheck_game(db, game_id=game_id, game_type="community")
    record_financial_sensitive_read(
        authenticated_admin_id=admin.id,
        action_type="read_admin_community_game_payment_detail",
        target_id=game_id,
    )
    return get_admin_community_game_detail(
        db,
        game_id=game_id,
        viewer_user=admin,
        support_flag_offset=support_flag_offset,
        support_flag_limit=support_flag_limit,
        audit_offset=audit_offset,
        audit_limit=audit_limit,
    )
