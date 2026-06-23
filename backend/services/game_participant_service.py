"""Game participant reads and protected create/update workflows."""

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import Booking, Game, GameParticipant, User
from backend.schemas.game_participant_schema import (
    GameParticipantCreate,
    GameParticipantUpdate,
)
from backend.services.admin_permission_service import (
    PERMISSION_OFFICIAL_GAMES_ROSTER_MANAGE,
    require_user_admin_permission,
)
from backend.services.game_participant_rules import (
    build_game_participant_conflict_detail,
    normalize_game_participant_lifecycle_fields,
    validate_game_participant_attendance_status,
    validate_game_participant_business_rules,
    validate_game_participant_status,
)


def get_active_game_or_404(db: Session, game_id: uuid.UUID) -> Game:
    db_game = db.get(Game, game_id)

    if db_game is None or db_game.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found.",
        )

    return db_game


def get_booking_or_404(db: Session, booking_id: uuid.UUID) -> Booking:
    db_booking = db.get(Booking, booking_id)

    if db_booking is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found.",
        )

    return db_booking


def get_active_user_or_404(db: Session, user_id: uuid.UUID, detail: str) -> User:
    db_user = db.get(User, user_id)

    if db_user is None or db_user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )

    return db_user


def validate_participant_references(
    db: Session,
    participant_data: dict[str, object],
) -> None:
    get_active_game_or_404(db, participant_data["game_id"])

    if participant_data["booking_id"] is not None:
        db_booking = get_booking_or_404(db, participant_data["booking_id"])

        if db_booking.game_id != participant_data["game_id"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="booking_id must belong to the same game_id.",
            )

    if participant_data["user_id"] is not None:
        get_active_user_or_404(db, participant_data["user_id"], "User not found.")

    if participant_data["marked_attendance_by_user_id"] is not None:
        get_active_user_or_404(
            db,
            participant_data["marked_attendance_by_user_id"],
            "Marked-attendance-by user not found.",
        )


def validate_participant_update_references(
    db: Session,
    db_participant: GameParticipant,
    update_data: dict[str, object],
) -> None:
    if update_data.get("game_id") is not None:
        get_active_game_or_404(db, update_data["game_id"])

    if update_data.get("booking_id") is not None:
        db_booking = get_booking_or_404(db, update_data["booking_id"])

        effective_game_id = update_data.get("game_id") or db_participant.game_id
        if db_booking.game_id != effective_game_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="booking_id must belong to the same game_id.",
            )

    if update_data.get("user_id") is not None:
        get_active_user_or_404(db, update_data["user_id"], "User not found.")

    if update_data.get("marked_attendance_by_user_id") is not None:
        get_active_user_or_404(
            db,
            update_data["marked_attendance_by_user_id"],
            "Marked-attendance-by user not found.",
        )


def create_game_participant_workflow(
    db: Session,
    participant: GameParticipantCreate,
) -> GameParticipant:
    participant_data = participant.model_dump()
    validate_participant_references(db, participant_data)

    normalized_participant_data = normalize_game_participant_lifecycle_fields(
        participant_data
    )
    validate_game_participant_business_rules(normalized_participant_data)

    new_participant = GameParticipant(
        id=uuid.uuid4(),
        **normalized_participant_data,
    )

    try:
        db.add(new_participant)
        db.commit()
        db.refresh(new_participant)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_game_participant_conflict_detail(exc),
        ) from exc

    return new_participant


def get_game_participant_for_user_or_404(
    db: Session,
    participant_id: uuid.UUID,
    current_user: User,
) -> GameParticipant:
    db_participant = db.get(GameParticipant, participant_id)

    if db_participant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game participant not found.",
        )

    can_read_participant = db_participant.user_id == current_user.id
    can_read_participant = (
        can_read_participant or db_participant.guest_of_user_id == current_user.id
    )
    if db_participant.booking_id is not None:
        db_booking = db.get(Booking, db_participant.booking_id)
        can_read_participant = (
            can_read_participant
            or (
                db_booking is not None
                and db_booking.buyer_user_id == current_user.id
            )
        )

    if not can_read_participant:
        require_user_admin_permission(
            current_user,
            PERMISSION_OFFICIAL_GAMES_ROSTER_MANAGE,
        )

    return db_participant


def list_game_participants(
    db: Session,
    *,
    game_id: uuid.UUID | None = None,
    booking_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    participant_status: str | None = None,
    attendance_status: str | None = None,
) -> list[GameParticipant]:
    statement = select(GameParticipant)

    if game_id is not None:
        statement = statement.where(GameParticipant.game_id == game_id)

    if booking_id is not None:
        statement = statement.where(GameParticipant.booking_id == booking_id)

    if user_id is not None:
        statement = statement.where(GameParticipant.user_id == user_id)

    if participant_status is not None:
        validate_game_participant_status(participant_status)
        statement = statement.where(
            GameParticipant.participant_status == participant_status
        )

    if attendance_status is not None:
        validate_game_participant_attendance_status(attendance_status)
        statement = statement.where(GameParticipant.attendance_status == attendance_status)

    participants = db.scalars(
        statement.order_by(
            GameParticipant.roster_order.asc().nulls_last(),
            GameParticipant.created_at.asc(),
        )
    ).all()
    return list(participants)


def update_game_participant_workflow(
    db: Session,
    participant_id: uuid.UUID,
    participant_update: GameParticipantUpdate,
) -> GameParticipant:
    db_participant = db.get(GameParticipant, participant_id)

    if db_participant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game participant not found.",
        )

    update_data = participant_update.model_dump(exclude_unset=True)
    effective_participant_data = {
        "game_id": update_data.get("game_id", db_participant.game_id),
        "booking_id": update_data.get("booking_id", db_participant.booking_id),
        "participant_type": update_data.get(
            "participant_type", db_participant.participant_type
        ),
        "user_id": update_data.get("user_id", db_participant.user_id),
        "guest_name": update_data.get("guest_name", db_participant.guest_name),
        "guest_email": update_data.get("guest_email", db_participant.guest_email),
        "guest_phone": update_data.get("guest_phone", db_participant.guest_phone),
        "display_name_snapshot": update_data.get(
            "display_name_snapshot", db_participant.display_name_snapshot
        ),
        "participant_status": update_data.get(
            "participant_status", db_participant.participant_status
        ),
        "attendance_status": update_data.get(
            "attendance_status", db_participant.attendance_status
        ),
        "cancellation_type": update_data.get(
            "cancellation_type", db_participant.cancellation_type
        ),
        "price_cents": update_data.get("price_cents", db_participant.price_cents),
        "currency": update_data.get("currency", db_participant.currency),
        "roster_order": update_data.get("roster_order", db_participant.roster_order),
        "joined_at": update_data.get("joined_at", db_participant.joined_at),
        "confirmed_at": update_data.get("confirmed_at", db_participant.confirmed_at),
        "cancelled_at": update_data.get("cancelled_at", db_participant.cancelled_at),
        "checked_in_at": update_data.get("checked_in_at", db_participant.checked_in_at),
        "marked_attendance_by_user_id": update_data.get(
            "marked_attendance_by_user_id",
            db_participant.marked_attendance_by_user_id,
        ),
        "attendance_decided_at": update_data.get(
            "attendance_decided_at", db_participant.attendance_decided_at
        ),
        "attendance_notes": update_data.get(
            "attendance_notes", db_participant.attendance_notes
        ),
    }
    validate_participant_update_references(db, db_participant, update_data)

    effective_participant_data = normalize_game_participant_lifecycle_fields(
        effective_participant_data, db_participant
    )
    validate_game_participant_business_rules(effective_participant_data)

    # Lifecycle fields are managed from the fully merged participant state so
    # partial PATCH payloads cannot keep stale timestamps or attendance notes.
    for lifecycle_field in (
        "joined_at",
        "confirmed_at",
        "cancelled_at",
        "attendance_decided_at",
        "marked_attendance_by_user_id",
        "attendance_notes",
    ):
        update_data[lifecycle_field] = effective_participant_data[lifecycle_field]

    for field_name, field_value in update_data.items():
        setattr(db_participant, field_name, field_value)

    db_participant.updated_at = datetime.now(timezone.utc)

    try:
        db.add(db_participant)
        db.commit()
        db.refresh(db_participant)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_game_participant_conflict_detail(exc),
        ) from exc

    return db_participant
