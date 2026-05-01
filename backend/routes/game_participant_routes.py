import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Booking, Game, GameParticipant, User
from backend.schemas import (
    GameParticipantCreate,
    GameParticipantRead,
    GameParticipantUpdate,
)

router = APIRouter(prefix="/game-participants", tags=["game_participants"])

VALID_PARTICIPANT_TYPES = {"registered_user", "guest", "host", "admin_added"}
VALID_PARTICIPANT_STATUSES = {
    "pending_payment",
    "confirmed",
    "waitlisted",
    "cancelled",
    "late_cancelled",
    "removed",
    "refunded",
}
VALID_ATTENDANCE_STATUSES = {
    "unknown",
    "attended",
    "no_show",
    "excused_absence",
    "not_applicable",
}
VALID_CANCELLATION_TYPES = {
    "none",
    "on_time",
    "late",
    "host_cancelled",
    "admin_cancelled",
    "payment_failed",
}
VALID_CURRENCY = "USD"
CANCELLED_PARTICIPANT_STATUSES = {"cancelled", "late_cancelled", "removed", "refunded"}
DECIDED_ATTENDANCE_STATUSES = {"attended", "no_show", "excused_absence"}
CONFIRMED_HISTORY_PARTICIPANT_STATUSES = {"confirmed"} | CANCELLED_PARTICIPANT_STATUSES


def build_game_participant_conflict_detail(exc: IntegrityError) -> str:
    error_text = str(exc.orig)

    if "ux_game_participants_active_registered_user_per_game" in error_text:
        return "This user already has an active participant row for this game."

    return error_text


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


def validate_game_participant_business_rules(
    participant_data: dict[str, object],
) -> None:
    if participant_data["participant_type"] not in VALID_PARTICIPANT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "participant_type must be 'registered_user', 'guest', "
                "'host', or 'admin_added'."
            ),
        )

    if participant_data["participant_status"] not in VALID_PARTICIPANT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "participant_status must be 'pending_payment', 'confirmed', "
                "'waitlisted', 'cancelled', 'late_cancelled', 'removed', "
                "or 'refunded'."
            ),
        )

    if participant_data["attendance_status"] not in VALID_ATTENDANCE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "attendance_status must be 'unknown', 'attended', "
                "'no_show', 'excused_absence', or 'not_applicable'."
            ),
        )

    if participant_data["cancellation_type"] not in VALID_CANCELLATION_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "cancellation_type must be 'none', 'on_time', 'late', "
                "'host_cancelled', 'admin_cancelled', or 'payment_failed'."
            ),
        )

    if participant_data["currency"] != VALID_CURRENCY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="currency must be 'USD'.",
        )

    if participant_data["price_cents"] < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="price_cents must be greater than or equal to 0.",
        )

    if (
        participant_data["roster_order"] is not None
        and participant_data["roster_order"] <= 0
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="roster_order must be null or greater than 0.",
        )

    if (
        participant_data["participant_type"] == "guest"
        and participant_data["guest_name"] is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Guest participants require guest_name.",
        )

    if (
        participant_data["participant_type"] == "guest"
        and participant_data["user_id"] is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Guest participants cannot include user_id.",
        )

    if (
        participant_data["participant_type"] in {"registered_user", "host", "admin_added"}
        and participant_data["user_id"] is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registered_user, host, and admin_added participants require user_id.",
        )

    if (
        participant_data["participant_type"] != "guest"
        and any(
            participant_data[field_name] is not None
            for field_name in ("guest_name", "guest_email", "guest_phone")
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Only guest participants may include guest_name, guest_email, "
                "or guest_phone."
            ),
        )

    if (
        participant_data["participant_status"] in CANCELLED_PARTICIPANT_STATUSES
        and participant_data["cancellation_type"] == "none"
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Cancelled, late_cancelled, removed, and refunded participants "
                "require a non-'none' cancellation_type."
            ),
        )

    if (
        participant_data["participant_status"] not in CANCELLED_PARTICIPANT_STATUSES
        and participant_data["cancellation_type"] != "none"
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Only cancelled, late_cancelled, removed, and refunded "
                "participants may use a non-'none' cancellation_type."
            ),
        )

    if (
        participant_data["attendance_status"] in DECIDED_ATTENDANCE_STATUSES
        and participant_data["marked_attendance_by_user_id"] is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Attended, no_show, and excused_absence participants require "
                "marked_attendance_by_user_id."
            ),
        )

    if (
        participant_data["checked_in_at"] is not None
        and participant_data["attendance_status"] != "attended"
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="checked_in_at can only be set when attendance_status is 'attended'.",
        )


def normalize_game_participant_lifecycle_fields(
    participant_data: dict[str, object],
    existing_participant: GameParticipant | None = None,
) -> dict[str, object]:
    normalized_data = dict(participant_data)
    now = datetime.now(timezone.utc)

    normalized_data["joined_at"] = (
        normalized_data.get("joined_at")
        or (existing_participant.joined_at if existing_participant is not None else None)
        or now
    )

    # Preserve the original confirmed_at timestamp for participants who were
    # once confirmed, even if they later cancel or get refunded.
    if normalized_data["participant_status"] in CONFIRMED_HISTORY_PARTICIPANT_STATUSES:
        normalized_data["confirmed_at"] = (
            normalized_data.get("confirmed_at")
            or (
                existing_participant.confirmed_at
                if existing_participant is not None
                else None
            )
            or now
        )
    else:
        normalized_data["confirmed_at"] = None

    if normalized_data["participant_status"] in CANCELLED_PARTICIPANT_STATUSES:
        normalized_data["cancelled_at"] = (
            normalized_data.get("cancelled_at")
            or (
                existing_participant.cancelled_at
                if existing_participant is not None
                else None
            )
            or now
        )
    else:
        normalized_data["cancelled_at"] = None

    if normalized_data["attendance_status"] in DECIDED_ATTENDANCE_STATUSES:
        normalized_data["attendance_decided_at"] = (
            normalized_data.get("attendance_decided_at")
            or (
                existing_participant.attendance_decided_at
                if existing_participant is not None
                else None
            )
            or now
        )
    else:
        normalized_data["attendance_decided_at"] = None
        normalized_data["marked_attendance_by_user_id"] = None
        normalized_data["attendance_notes"] = None

    return normalized_data


# This route creates one roster row for a real participant slot after
# validating the linked game, optional booking, and optional user references.
@router.post(
    "", response_model=GameParticipantRead, status_code=status.HTTP_201_CREATED
)
def create_game_participant(
    participant: GameParticipantCreate, db: Session = Depends(get_db)
) -> GameParticipant:
    get_active_game_or_404(db, participant.game_id)

    if participant.booking_id is not None:
        db_booking = get_booking_or_404(db, participant.booking_id)

        if db_booking.game_id != participant.game_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="booking_id must belong to the same game_id.",
            )

    if participant.user_id is not None:
        get_active_user_or_404(db, participant.user_id, "User not found.")

    if participant.marked_attendance_by_user_id is not None:
        get_active_user_or_404(
            db,
            participant.marked_attendance_by_user_id,
            "Marked-attendance-by user not found.",
        )

    normalized_participant_data = normalize_game_participant_lifecycle_fields(
        participant.model_dump()
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


# This route fetches a single participant roster row by its internal UUID.
@router.get(
    "/{participant_id}",
    response_model=GameParticipantRead,
    status_code=status.HTTP_200_OK,
)
def get_game_participant(
    participant_id: uuid.UUID, db: Session = Depends(get_db)
) -> GameParticipant:
    db_participant = db.get(GameParticipant, participant_id)

    if db_participant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game participant not found.",
        )

    return db_participant


# This route returns participant roster rows currently stored in the app
# database.
@router.get("", response_model=list[GameParticipantRead], status_code=status.HTTP_200_OK)
def list_game_participants(
    game_id: uuid.UUID | None = None,
    booking_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    participant_status: str | None = None,
    attendance_status: str | None = None,
    db: Session = Depends(get_db),
) -> list[GameParticipant]:
    statement = select(GameParticipant)

    if game_id is not None:
        statement = statement.where(GameParticipant.game_id == game_id)

    if booking_id is not None:
        statement = statement.where(GameParticipant.booking_id == booking_id)

    if user_id is not None:
        statement = statement.where(GameParticipant.user_id == user_id)

    if participant_status is not None:
        if participant_status not in VALID_PARTICIPANT_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "participant_status must be 'pending_payment', 'confirmed', "
                    "'waitlisted', 'cancelled', 'late_cancelled', 'removed', "
                    "or 'refunded'."
                ),
            )
        statement = statement.where(
            GameParticipant.participant_status == participant_status
        )

    if attendance_status is not None:
        if attendance_status not in VALID_ATTENDANCE_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "attendance_status must be 'unknown', 'attended', "
                    "'no_show', 'excused_absence', or 'not_applicable'."
                ),
            )
        statement = statement.where(GameParticipant.attendance_status == attendance_status)

    participants = db.scalars(
        statement.order_by(
            GameParticipant.roster_order.asc().nulls_last(),
            GameParticipant.created_at.asc(),
        )
    ).all()
    return list(participants)


# This route applies partial updates to an existing participant roster row
# while keeping participant identity, lifecycle, and attendance state aligned.
@router.patch(
    "/{participant_id}",
    response_model=GameParticipantRead,
    status_code=status.HTTP_200_OK,
)
def update_game_participant(
    participant_id: uuid.UUID,
    participant_update: GameParticipantUpdate,
    db: Session = Depends(get_db),
) -> GameParticipant:
    db_participant = db.get(GameParticipant, participant_id)

    if db_participant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game participant not found.",
        )

    if participant_update.game_id is not None:
        get_active_game_or_404(db, participant_update.game_id)

    if participant_update.booking_id is not None:
        db_booking = get_booking_or_404(db, participant_update.booking_id)

        effective_game_id = participant_update.game_id or db_participant.game_id
        if db_booking.game_id != effective_game_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="booking_id must belong to the same game_id.",
            )

    if participant_update.user_id is not None:
        get_active_user_or_404(db, participant_update.user_id, "User not found.")

    if participant_update.marked_attendance_by_user_id is not None:
        get_active_user_or_404(
            db,
            participant_update.marked_attendance_by_user_id,
            "Marked-attendance-by user not found.",
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
