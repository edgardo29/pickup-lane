"""Requests to leave an official game whose details changed after booking.

A player with a confirmed booking may ask to be removed when staff changed the
game after they booked, choosing a refund to the original payment method or
game credit. Submitting a request changes no booking, roster, refund, or
credit; staff processing does that. See Edit Official Game §4.7 and the
database architecture's changed-official-game removal requests.
"""

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import AdminAction, Booking, Game, GameChangeRemovalRequest, User
from backend.schemas.game_change_removal_schema import (
    GameChangeRemovalRequestRead,
    GameChangeReviewRead,
    GameDetailChangeRead,
)
from backend.services.game_rules import is_roster_locked, require_roster_window_open
from backend.services.game_service import get_public_game_or_404

ACTIVE_REQUEST_STATUSES = ("pending", "processing", "failed")
OFFICIAL_GAME_EDIT_ACTION = "update_official_game"


def get_game_change_review(
    db: Session,
    game_id: uuid.UUID,
    current_user: User,
    *,
    now: datetime | None = None,
) -> GameChangeReviewRead:
    captured_now = now or datetime.now(UTC)
    game = get_public_game_or_404(db, game_id, current_user)
    booking = get_confirmed_official_booking(db, game, current_user)
    if booking is None:
        return GameChangeReviewRead(
            changes=[], active_request=None, can_request_removal=False
        )

    changes = list_changes_since_booking(db, game, booking)
    active_request = get_active_removal_request(db, booking.id)
    return GameChangeReviewRead(
        changes=changes,
        active_request=(
            GameChangeRemovalRequestRead.model_validate(active_request)
            if active_request is not None
            else None
        ),
        can_request_removal=(
            bool(changes)
            and active_request is None
            and not is_roster_locked(game, captured_now)
        ),
    )


def submit_game_change_removal_request(
    db: Session,
    game_id: uuid.UUID,
    relief_choice: str,
    current_user: User,
    *,
    now: datetime | None = None,
) -> GameChangeRemovalRequest:
    captured_now = now or datetime.now(UTC)
    game = get_public_game_or_404(db, game_id, current_user)
    if game.game_type != "official":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only official games accept change-related removal requests.",
        )

    booking = get_confirmed_official_booking(db, game, current_user)
    if booking is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You do not have a confirmed booking for this game.",
        )

    require_roster_window_open(
        game, captured_now, "Requests to leave are closed for this game."
    )
    if not list_changes_since_booking(db, game, booking):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This game has not changed since you booked.",
        )
    if get_active_removal_request(db, booking.id) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have a request to leave this game.",
        )

    removal_request = GameChangeRemovalRequest(
        id=uuid.uuid4(),
        booking_id=booking.id,
        requester_user_id=current_user.id,
        relief_choice=relief_choice,
        request_status="pending",
        submitted_at=captured_now,
        created_at=captured_now,
        updated_at=captured_now,
    )
    db.add(removal_request)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have a request to leave this game.",
        ) from exc
    db.refresh(removal_request)
    return removal_request


def get_confirmed_official_booking(
    db: Session,
    game: Game,
    current_user: User,
) -> Booking | None:
    if game.game_type != "official":
        return None

    return db.scalar(
        select(Booking)
        .where(
            Booking.game_id == game.id,
            Booking.buyer_user_id == current_user.id,
            Booking.booking_status.in_(("confirmed", "partially_cancelled")),
        )
        .order_by(Booking.created_at.asc(), Booking.id.asc())
        .limit(1)
    )


def list_changes_since_booking(
    db: Session,
    game: Game,
    booking: Booking,
) -> list[GameDetailChangeRead]:
    """Each detail staff changed after the booking, from first value to latest."""
    booked_at = booking.booked_at or booking.created_at
    edits = db.scalars(
        select(AdminAction)
        .where(
            AdminAction.action_type == OFFICIAL_GAME_EDIT_ACTION,
            AdminAction.outcome == "succeeded",
            AdminAction.target_game_id == game.id,
            AdminAction.created_at > booked_at,
        )
        .order_by(AdminAction.created_at.asc(), AdminAction.id.asc())
    ).all()

    changes: dict[str, GameDetailChangeRead] = {}
    for edit in edits:
        metadata = edit.metadata_ or {}
        before = metadata.get("before") or {}
        after = metadata.get("after") or {}
        for field in metadata.get("changed_fields") or []:
            if field.endswith("_id"):
                continue
            if field in changes:
                changes[field].after = after.get(field)
                changes[field].changed_at = edit.created_at
            else:
                changes[field] = GameDetailChangeRead(
                    field=field,
                    before=before.get(field),
                    after=after.get(field),
                    changed_at=edit.created_at,
                )

    return [change for change in changes.values() if change.before != change.after]


def get_active_removal_request(
    db: Session,
    booking_id: uuid.UUID,
) -> GameChangeRemovalRequest | None:
    return db.scalar(
        select(GameChangeRemovalRequest).where(
            GameChangeRemovalRequest.booking_id == booking_id,
            GameChangeRemovalRequest.request_status.in_(ACTIVE_REQUEST_STATUSES),
        )
    )
