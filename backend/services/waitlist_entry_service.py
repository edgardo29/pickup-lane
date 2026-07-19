"""Waitlist entry reads and protected create/update workflows."""

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import Booking, Game, User, WaitlistEntry
from backend.schemas.waitlist_entry_schema import (
    WaitlistEntryCreate,
    WaitlistEntryUpdate,
)
from backend.services.auth_service import require_active_admin_user
from backend.services.waitlist_rules import (
    build_waitlist_entry_conflict_detail,
    normalize_waitlist_entry_lifecycle_fields,
    validate_game_accepts_waitlist_status,
    validate_waitlist_entry_business_rules,
    validate_waitlist_status,
)


def get_active_game_or_404(db: Session, game_id: uuid.UUID) -> Game:
    db_game = db.get(Game, game_id)

    if db_game is None or db_game.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found.",
        )

    return db_game


def get_active_user_or_404(db: Session, user_id: uuid.UUID) -> User:
    db_user = db.get(User, user_id)

    if db_user is None or db_user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    return db_user


def get_booking_or_404(db: Session, booking_id: uuid.UUID) -> Booking:
    db_booking = db.get(Booking, booking_id)

    if db_booking is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Promoted booking not found.",
        )

    return db_booking


def validate_waitlist_entry_references(
    db: Session,
    waitlist_entry_data: dict[str, object],
) -> Game | None:
    db_game = None
    if waitlist_entry_data["game_id"] is not None:
        db_game = get_active_game_or_404(db, waitlist_entry_data["game_id"])

    if waitlist_entry_data["user_id"] is not None:
        get_active_user_or_404(db, waitlist_entry_data["user_id"])

    if waitlist_entry_data["promoted_booking_id"] is not None:
        db_booking = get_booking_or_404(db, waitlist_entry_data["promoted_booking_id"])

        if db_booking.game_id != waitlist_entry_data["game_id"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="promoted_booking_id must belong to the same game_id.",
            )

    return db_game


def create_waitlist_entry_workflow(
    db: Session,
    waitlist_entry: WaitlistEntryCreate,
) -> WaitlistEntry:
    waitlist_entry_data = waitlist_entry.model_dump()
    db_game = validate_waitlist_entry_references(db, waitlist_entry_data)

    normalized_waitlist_entry_data = normalize_waitlist_entry_lifecycle_fields(
        waitlist_entry_data
    )
    if db_game is not None:
        validate_game_accepts_waitlist_status(
            db_game, normalized_waitlist_entry_data["waitlist_status"]
        )
    validate_waitlist_entry_business_rules(normalized_waitlist_entry_data)

    new_waitlist_entry = WaitlistEntry(
        id=uuid.uuid4(),
        **normalized_waitlist_entry_data,
    )

    try:
        db.add(new_waitlist_entry)
        db.commit()
        db.refresh(new_waitlist_entry)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_waitlist_entry_conflict_detail(exc),
        ) from exc

    return new_waitlist_entry


def list_current_user_waitlist_entries(
    db: Session,
    current_user: User,
) -> list[WaitlistEntry]:
    return list(
        db.scalars(
            select(WaitlistEntry)
            .where(WaitlistEntry.user_id == current_user.id)
            .order_by(
                WaitlistEntry.created_at.desc(),
                WaitlistEntry.joined_at.desc(),
            )
        ).all()
    )


def get_waitlist_entry_for_user_or_404(
    db: Session,
    waitlist_entry_id: uuid.UUID,
    current_user: User,
) -> WaitlistEntry:
    db_waitlist_entry = db.get(WaitlistEntry, waitlist_entry_id)

    if db_waitlist_entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Waitlist entry not found.",
        )

    if db_waitlist_entry.user_id != current_user.id:
        require_active_admin_user(current_user)

    return db_waitlist_entry


def list_waitlist_entries(
    db: Session,
    *,
    game_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    waitlist_status: str | None = None,
) -> list[WaitlistEntry]:
    statement = select(WaitlistEntry)

    if game_id is not None:
        statement = statement.where(WaitlistEntry.game_id == game_id)

    if user_id is not None:
        statement = statement.where(WaitlistEntry.user_id == user_id)

    if waitlist_status is not None:
        validate_waitlist_status(waitlist_status)
        statement = statement.where(WaitlistEntry.waitlist_status == waitlist_status)

    waitlist_entries = db.scalars(
        statement.order_by(
            WaitlistEntry.position.asc(),
            WaitlistEntry.joined_at.asc(),
        )
    ).all()
    return list(waitlist_entries)


def update_waitlist_entry_workflow(
    db: Session,
    waitlist_entry_id: uuid.UUID,
    waitlist_entry_update: WaitlistEntryUpdate,
) -> WaitlistEntry:
    db_waitlist_entry = db.get(WaitlistEntry, waitlist_entry_id)

    if db_waitlist_entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Waitlist entry not found.",
        )

    update_data = waitlist_entry_update.model_dump(exclude_unset=True)
    effective_waitlist_entry_data = {
        "game_id": update_data.get("game_id", db_waitlist_entry.game_id),
        "user_id": update_data.get("user_id", db_waitlist_entry.user_id),
        "party_size": update_data.get("party_size", db_waitlist_entry.party_size),
        "position": update_data.get("position", db_waitlist_entry.position),
        "waitlist_status": update_data.get(
            "waitlist_status", db_waitlist_entry.waitlist_status
        ),
        "promoted_booking_id": update_data.get(
            "promoted_booking_id", db_waitlist_entry.promoted_booking_id
        ),
        "promotion_expires_at": update_data.get(
            "promotion_expires_at", db_waitlist_entry.promotion_expires_at
        ),
        "joined_at": update_data.get("joined_at", db_waitlist_entry.joined_at),
        "promoted_at": update_data.get("promoted_at", db_waitlist_entry.promoted_at),
        "cancelled_at": update_data.get(
            "cancelled_at", db_waitlist_entry.cancelled_at
        ),
        "expired_at": update_data.get("expired_at", db_waitlist_entry.expired_at),
    }

    db_game = validate_waitlist_entry_references(db, effective_waitlist_entry_data)

    effective_waitlist_entry_data = normalize_waitlist_entry_lifecycle_fields(
        effective_waitlist_entry_data,
        db_waitlist_entry,
    )
    if db_game is not None and (
        "game_id" in update_data or "waitlist_status" in update_data
    ):
        validate_game_accepts_waitlist_status(
            db_game, effective_waitlist_entry_data["waitlist_status"]
        )
    validate_waitlist_entry_business_rules(effective_waitlist_entry_data)

    # Lifecycle fields are managed from the fully merged waitlist state so
    # partial PATCH payloads cannot leave stale status timestamps behind.
    for lifecycle_field in (
        "joined_at",
        "promotion_expires_at",
        "promoted_at",
        "cancelled_at",
        "expired_at",
    ):
        update_data[lifecycle_field] = effective_waitlist_entry_data[lifecycle_field]

    for field_name, field_value in update_data.items():
        setattr(db_waitlist_entry, field_name, field_value)

    db_waitlist_entry.updated_at = datetime.now(timezone.utc)

    try:
        db.add(db_waitlist_entry)
        db.commit()
        db.refresh(db_waitlist_entry)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_waitlist_entry_conflict_detail(exc),
        ) from exc

    return db_waitlist_entry
