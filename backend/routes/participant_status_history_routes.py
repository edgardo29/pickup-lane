import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import GameParticipant, ParticipantStatusHistory, User
from backend.schemas import (
    ParticipantStatusHistoryCreate,
    ParticipantStatusHistoryRead,
    ParticipantStatusHistoryUpdate,
)

router = APIRouter(
    prefix="/participant-status-history",
    tags=["participant_status_history"],
)

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
VALID_CHANGE_SOURCES = {
    "user",
    "host",
    "admin",
    "system",
    "payment_webhook",
    "scheduled_job",
}
IMMUTABLE_HISTORY_UPDATE_FIELDS = {
    "participant_id",
    "old_participant_status",
    "new_participant_status",
    "old_attendance_status",
    "new_attendance_status",
    "changed_by_user_id",
    "change_source",
}


def build_participant_status_history_conflict_detail(exc: IntegrityError) -> str:
    return str(exc.orig)


def get_participant_or_404(
    db: Session,
    participant_id: uuid.UUID,
) -> GameParticipant:
    db_participant = db.get(GameParticipant, participant_id)

    if db_participant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant not found.",
        )

    return db_participant


def get_active_user_or_404(db: Session, user_id: uuid.UUID) -> User:
    db_user = db.get(User, user_id)

    if db_user is None or db_user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Changed by user not found.",
        )

    return db_user


def validate_participant_status_history_business_rules(
    history_data: dict[str, object],
) -> None:
    for field_name in ("participant_id", "new_participant_status", "change_source"):
        if history_data[field_name] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} cannot be null.",
            )

    if (
        history_data["old_participant_status"] is not None
        and history_data["old_participant_status"] not in VALID_PARTICIPANT_STATUSES
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="old_participant_status is not supported.",
        )

    if history_data["new_participant_status"] not in VALID_PARTICIPANT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="new_participant_status is not supported.",
        )

    if (
        history_data["old_attendance_status"] is not None
        and history_data["old_attendance_status"] not in VALID_ATTENDANCE_STATUSES
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="old_attendance_status is not supported.",
        )

    if (
        history_data["new_attendance_status"] is not None
        and history_data["new_attendance_status"] not in VALID_ATTENDANCE_STATUSES
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="new_attendance_status is not supported.",
        )

    if history_data["change_source"] not in VALID_CHANGE_SOURCES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "change_source must be 'user', 'host', 'admin', 'system', "
                "'payment_webhook', or 'scheduled_job'."
            ),
        )

    if (
        history_data["old_participant_status"] == history_data["new_participant_status"]
        and history_data["old_attendance_status"] == history_data["new_attendance_status"]
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one participant or attendance status must change.",
        )


def validate_participant_status_history_references(
    db: Session,
    history_data: dict[str, object],
) -> None:
    db_participant = get_participant_or_404(db, history_data["participant_id"])

    if history_data["changed_by_user_id"] is not None:
        db_user = get_active_user_or_404(db, history_data["changed_by_user_id"])

        if (
            history_data["change_source"] == "user"
            and db_participant.user_id is not None
            and db_user.id != db_participant.user_id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User-sourced changes must be made by the participant user.",
            )

        if history_data["change_source"] == "host" and db_user.role != "host":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Host-sourced changes require a host user.",
            )

        if history_data["change_source"] == "admin" and db_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Admin-sourced changes require an admin user.",
            )


def validate_participant_status_history_update_fields(
    update_data: dict[str, object],
) -> None:
    immutable_fields = IMMUTABLE_HISTORY_UPDATE_FIELDS & update_data.keys()

    if immutable_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Participant status history lifecycle fields cannot be changed "
                "after creation."
            ),
        )


# This route records one append-only participant lifecycle audit row after
# validating the participant, optional actor, status values, and change source.
@router.post(
    "",
    response_model=ParticipantStatusHistoryRead,
    status_code=status.HTTP_201_CREATED,
)
def create_participant_status_history(
    participant_status_history: ParticipantStatusHistoryCreate,
    db: Session = Depends(get_db),
) -> ParticipantStatusHistory:
    history_data = participant_status_history.model_dump()
    validate_participant_status_history_business_rules(history_data)
    validate_participant_status_history_references(db, history_data)

    new_participant_status_history = ParticipantStatusHistory(
        id=uuid.uuid4(),
        **history_data,
    )

    try:
        db.add(new_participant_status_history)
        db.commit()
        db.refresh(new_participant_status_history)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_participant_status_history_conflict_detail(exc),
        ) from exc

    return new_participant_status_history


# This route fetches a single participant status history row by its internal UUID.
@router.get(
    "/{history_id}",
    response_model=ParticipantStatusHistoryRead,
    status_code=status.HTTP_200_OK,
)
def get_participant_status_history(
    history_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> ParticipantStatusHistory:
    db_history = db.get(ParticipantStatusHistory, history_id)

    if db_history is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant status history not found.",
        )

    return db_history


# This route returns participant status history rows currently stored in the app
# database, ordered from oldest to newest for audit readability.
@router.get(
    "",
    response_model=list[ParticipantStatusHistoryRead],
    status_code=status.HTTP_200_OK,
)
def list_participant_status_history(
    participant_id: uuid.UUID | None = None,
    changed_by_user_id: uuid.UUID | None = None,
    change_source: str | None = None,
    db: Session = Depends(get_db),
) -> list[ParticipantStatusHistory]:
    statement = select(ParticipantStatusHistory)

    if participant_id is not None:
        statement = statement.where(
            ParticipantStatusHistory.participant_id == participant_id
        )

    if changed_by_user_id is not None:
        statement = statement.where(
            ParticipantStatusHistory.changed_by_user_id == changed_by_user_id
        )

    if change_source is not None:
        if change_source not in VALID_CHANGE_SOURCES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "change_source must be 'user', 'host', 'admin', 'system', "
                    "'payment_webhook', or 'scheduled_job'."
                ),
            )
        statement = statement.where(
            ParticipantStatusHistory.change_source == change_source
        )

    history_rows = db.scalars(
        statement.order_by(ParticipantStatusHistory.created_at.asc())
    ).all()
    return list(history_rows)


# This route allows correcting the explanatory reason on an audit row while
# keeping the recorded lifecycle change itself immutable.
@router.patch(
    "/{history_id}",
    response_model=ParticipantStatusHistoryRead,
    status_code=status.HTTP_200_OK,
)
def update_participant_status_history(
    history_id: uuid.UUID,
    history_update: ParticipantStatusHistoryUpdate,
    db: Session = Depends(get_db),
) -> ParticipantStatusHistory:
    db_history = db.get(ParticipantStatusHistory, history_id)

    if db_history is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant status history not found.",
        )

    update_data = history_update.model_dump(exclude_unset=True)
    validate_participant_status_history_update_fields(update_data)

    if "change_reason" in update_data:
        db_history.change_reason = update_data["change_reason"]

    try:
        db.add(db_history)
        db.commit()
        db.refresh(db_history)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_participant_status_history_conflict_detail(exc),
        ) from exc

    return db_history
