"""Shared helpers for recording and querying lifecycle status changes."""

import uuid
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import (
    Booking,
    BookingStatusHistory,
    Game,
    GameParticipant,
    GameStatusHistory,
    ParticipantStatusHistory,
    User,
)
from backend.schemas.booking_status_history_schema import (
    BookingStatusHistoryCreate,
    BookingStatusHistoryUpdate,
)
from backend.schemas.game_status_history_schema import (
    GameStatusHistoryCreate,
    GameStatusHistoryUpdate,
)
from backend.schemas.participant_status_history_schema import (
    ParticipantStatusHistoryCreate,
    ParticipantStatusHistoryUpdate,
)
from backend.services.admin_permission_service import ADMIN_ROLE
from backend.services.booking_rules import VALID_BOOKING_STATUSES, VALID_PAYMENT_STATUSES
from backend.services.game_participant_rules import (
    VALID_ATTENDANCE_STATUSES,
    VALID_PARTICIPANT_STATUSES,
)
from backend.services.game_rules import VALID_GAME_STATUSES, VALID_PUBLISH_STATUSES

VALID_CHANGE_SOURCES = {
    "user",
    "host",
    "admin",
    "system",
    "payment_webhook",
    "scheduled_job",
}
GAME_IMMUTABLE_HISTORY_UPDATE_FIELDS = {
    "game_id",
    "old_publish_status",
    "new_publish_status",
    "old_game_status",
    "new_game_status",
    "changed_by_user_id",
    "change_source",
}
BOOKING_IMMUTABLE_HISTORY_UPDATE_FIELDS = {
    "booking_id",
    "old_booking_status",
    "new_booking_status",
    "old_payment_status",
    "new_payment_status",
    "changed_by_user_id",
    "change_source",
}
PARTICIPANT_IMMUTABLE_HISTORY_UPDATE_FIELDS = {
    "participant_id",
    "old_participant_status",
    "new_participant_status",
    "old_attendance_status",
    "new_attendance_status",
    "changed_by_user_id",
    "change_source",
}


def add_game_status_history_if_changed(
    db: Session,
    game: Game,
    *,
    old_publish_status: str,
    old_game_status: str,
    new_publish_status: str | None = None,
    new_game_status: str | None = None,
    reason: str | None,
    changed_by_user_id: uuid.UUID | None = None,
    change_source: str = "system",
    changed_at: datetime | None = None,
) -> None:
    resolved_new_publish_status = (
        game.publish_status if new_publish_status is None else new_publish_status
    )
    resolved_new_game_status = (
        game.game_status if new_game_status is None else new_game_status
    )
    if (
        old_publish_status == resolved_new_publish_status
        and old_game_status == resolved_new_game_status
    ):
        return

    history = GameStatusHistory(
        id=uuid.uuid4(),
        game_id=game.id,
        old_publish_status=old_publish_status,
        new_publish_status=resolved_new_publish_status,
        old_game_status=old_game_status,
        new_game_status=resolved_new_game_status,
        changed_by_user_id=changed_by_user_id,
        change_source=change_source,
        change_reason=reason,
    )
    if changed_at is not None:
        history.created_at = changed_at
    db.add(history)


def add_booking_status_history_if_changed(
    db: Session,
    booking: Booking,
    *,
    old_booking_status: str,
    old_payment_status: str,
    reason: str,
    changed_by_user_id: uuid.UUID | None = None,
    change_source: str = "system",
) -> None:
    if (
        old_booking_status == booking.booking_status
        and old_payment_status == booking.payment_status
    ):
        return

    db.add(
        BookingStatusHistory(
            id=uuid.uuid4(),
            booking_id=booking.id,
            old_booking_status=old_booking_status,
            new_booking_status=booking.booking_status,
            old_payment_status=old_payment_status,
            new_payment_status=booking.payment_status,
            changed_by_user_id=changed_by_user_id,
            change_source=change_source,
            change_reason=reason,
        )
    )


def add_participant_status_history_if_changed(
    db: Session,
    participant: GameParticipant,
    *,
    old_participant_status: str,
    old_attendance_status: str,
    reason: str,
    changed_by_user_id: uuid.UUID | None = None,
    change_source: str = "system",
) -> None:
    if (
        old_participant_status == participant.participant_status
        and old_attendance_status == participant.attendance_status
    ):
        return

    db.add(
        ParticipantStatusHistory(
            id=uuid.uuid4(),
            participant_id=participant.id,
            old_participant_status=old_participant_status,
            new_participant_status=participant.participant_status,
            old_attendance_status=old_attendance_status,
            new_attendance_status=participant.attendance_status,
            changed_by_user_id=changed_by_user_id,
            change_source=change_source,
            change_reason=reason,
        )
    )


def build_status_history_conflict_detail(exc: IntegrityError) -> str:
    return str(exc.orig)


def get_game_or_404(db: Session, game_id: uuid.UUID) -> Game:
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


def get_changed_by_user_or_404(db: Session, user_id: uuid.UUID) -> User:
    db_user = db.get(User, user_id)

    if db_user is None or db_user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Changed by user not found.",
        )

    return db_user


def validate_change_source(change_source: str) -> None:
    if change_source not in VALID_CHANGE_SOURCES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "change_source must be 'user', 'host', 'admin', 'system', "
                "'payment_webhook', or 'scheduled_job'."
            ),
        )


def get_game_status_history_or_404(
    db: Session,
    history_id: uuid.UUID,
) -> GameStatusHistory:
    db_history = db.get(GameStatusHistory, history_id)

    if db_history is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game status history not found.",
        )

    return db_history


def get_booking_status_history_or_404(
    db: Session,
    history_id: uuid.UUID,
) -> BookingStatusHistory:
    db_history = db.get(BookingStatusHistory, history_id)

    if db_history is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking status history not found.",
        )

    return db_history


def get_participant_status_history_or_404(
    db: Session,
    history_id: uuid.UUID,
) -> ParticipantStatusHistory:
    db_history = db.get(ParticipantStatusHistory, history_id)

    if db_history is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant status history not found.",
        )

    return db_history


def validate_game_status_history_business_rules(
    history_data: dict[str, object],
) -> None:
    for field_name in (
        "game_id",
        "new_publish_status",
        "new_game_status",
        "change_source",
    ):
        if history_data[field_name] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} cannot be null.",
            )

    if (
        history_data["old_publish_status"] is not None
        and history_data["old_publish_status"] not in VALID_PUBLISH_STATUSES
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="old_publish_status must be 'draft', 'published', or 'archived'.",
        )

    if history_data["new_publish_status"] not in VALID_PUBLISH_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="new_publish_status must be 'draft', 'published', or 'archived'.",
        )

    if (
        history_data["old_game_status"] is not None
        and history_data["old_game_status"] not in VALID_GAME_STATUSES
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "old_game_status must be 'active', 'completed', 'cancelled', "
                "'expired', or 'removed'."
            ),
        )

    if history_data["new_game_status"] not in VALID_GAME_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "new_game_status must be 'active', 'completed', 'cancelled', "
                "'expired', or 'removed'."
            ),
        )

    validate_change_source(str(history_data["change_source"]))

    if (
        history_data["old_publish_status"] == history_data["new_publish_status"]
        and history_data["old_game_status"] == history_data["new_game_status"]
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one publish or game status must change.",
        )


def validate_game_status_history_references(
    db: Session,
    history_data: dict[str, object],
) -> None:
    get_game_or_404(db, history_data["game_id"])

    if history_data["changed_by_user_id"] is not None:
        get_changed_by_user_or_404(db, history_data["changed_by_user_id"])


def validate_game_status_history_update_fields(update_data: dict[str, object]) -> None:
    immutable_fields = GAME_IMMUTABLE_HISTORY_UPDATE_FIELDS & update_data.keys()

    if immutable_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Game status history lifecycle fields cannot be changed "
                "after creation."
            ),
        )


def create_game_status_history_record(
    db: Session,
    payload: GameStatusHistoryCreate,
) -> GameStatusHistory:
    history_data = payload.model_dump()
    validate_game_status_history_business_rules(history_data)
    validate_game_status_history_references(db, history_data)

    new_game_status_history = GameStatusHistory(
        id=uuid.uuid4(),
        **history_data,
    )

    try:
        db.add(new_game_status_history)
        db.commit()
        db.refresh(new_game_status_history)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_status_history_conflict_detail(exc),
        ) from exc

    return new_game_status_history


def get_game_status_history_record(
    db: Session,
    history_id: uuid.UUID,
) -> GameStatusHistory:
    return get_game_status_history_or_404(db, history_id)


def list_game_status_history_records(
    db: Session,
    *,
    game_id: uuid.UUID | None = None,
    changed_by_user_id: uuid.UUID | None = None,
    change_source: str | None = None,
) -> list[GameStatusHistory]:
    statement = select(GameStatusHistory)

    if game_id is not None:
        statement = statement.where(GameStatusHistory.game_id == game_id)

    if changed_by_user_id is not None:
        statement = statement.where(
            GameStatusHistory.changed_by_user_id == changed_by_user_id
        )

    if change_source is not None:
        validate_change_source(change_source)
        statement = statement.where(GameStatusHistory.change_source == change_source)

    history_rows = db.scalars(
        statement.order_by(GameStatusHistory.created_at.asc())
    ).all()
    return list(history_rows)


def update_game_status_history_record(
    db: Session,
    history_id: uuid.UUID,
    payload: GameStatusHistoryUpdate,
) -> GameStatusHistory:
    db_history = get_game_status_history_or_404(db, history_id)
    update_data = payload.model_dump(exclude_unset=True)
    validate_game_status_history_update_fields(update_data)

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
            detail=build_status_history_conflict_detail(exc),
        ) from exc

    return db_history


def validate_booking_status_history_business_rules(
    history_data: dict[str, object],
) -> None:
    for field_name in ("booking_id", "new_booking_status", "change_source"):
        if history_data[field_name] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} cannot be null.",
            )

    if (
        history_data["old_booking_status"] is not None
        and history_data["old_booking_status"] not in VALID_BOOKING_STATUSES
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="old_booking_status is not supported.",
        )

    if history_data["new_booking_status"] not in VALID_BOOKING_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="new_booking_status is not supported.",
        )

    if (
        history_data["old_payment_status"] is not None
        and history_data["old_payment_status"] not in VALID_PAYMENT_STATUSES
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="old_payment_status is not supported.",
        )

    if (
        history_data["new_payment_status"] is not None
        and history_data["new_payment_status"] not in VALID_PAYMENT_STATUSES
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="new_payment_status is not supported.",
        )

    validate_change_source(str(history_data["change_source"]))

    if (
        history_data["old_booking_status"] == history_data["new_booking_status"]
        and history_data["old_payment_status"] == history_data["new_payment_status"]
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one booking or payment status must change.",
        )


def validate_booking_status_history_references(
    db: Session,
    history_data: dict[str, object],
) -> None:
    get_booking_or_404(db, history_data["booking_id"])

    if history_data["changed_by_user_id"] is not None:
        get_changed_by_user_or_404(db, history_data["changed_by_user_id"])


def validate_booking_status_history_update_fields(update_data: dict[str, object]) -> None:
    immutable_fields = BOOKING_IMMUTABLE_HISTORY_UPDATE_FIELDS & update_data.keys()

    if immutable_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Booking status history lifecycle fields cannot be changed "
                "after creation."
            ),
        )


def create_booking_status_history_record(
    db: Session,
    payload: BookingStatusHistoryCreate,
) -> BookingStatusHistory:
    history_data = payload.model_dump()
    validate_booking_status_history_business_rules(history_data)
    validate_booking_status_history_references(db, history_data)

    new_booking_status_history = BookingStatusHistory(
        id=uuid.uuid4(),
        **history_data,
    )

    try:
        db.add(new_booking_status_history)
        db.commit()
        db.refresh(new_booking_status_history)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_status_history_conflict_detail(exc),
        ) from exc

    return new_booking_status_history


def get_booking_status_history_record(
    db: Session,
    history_id: uuid.UUID,
) -> BookingStatusHistory:
    return get_booking_status_history_or_404(db, history_id)


def list_booking_status_history_records(
    db: Session,
    *,
    booking_id: uuid.UUID | None = None,
    changed_by_user_id: uuid.UUID | None = None,
    change_source: str | None = None,
) -> list[BookingStatusHistory]:
    statement = select(BookingStatusHistory)

    if booking_id is not None:
        statement = statement.where(BookingStatusHistory.booking_id == booking_id)

    if changed_by_user_id is not None:
        statement = statement.where(
            BookingStatusHistory.changed_by_user_id == changed_by_user_id
        )

    if change_source is not None:
        validate_change_source(change_source)
        statement = statement.where(BookingStatusHistory.change_source == change_source)

    history_rows = db.scalars(
        statement.order_by(BookingStatusHistory.created_at.asc())
    ).all()
    return list(history_rows)


def update_booking_status_history_record(
    db: Session,
    history_id: uuid.UUID,
    payload: BookingStatusHistoryUpdate,
) -> BookingStatusHistory:
    db_history = get_booking_status_history_or_404(db, history_id)
    update_data = payload.model_dump(exclude_unset=True)
    validate_booking_status_history_update_fields(update_data)

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
            detail=build_status_history_conflict_detail(exc),
        ) from exc

    return db_history


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

    validate_change_source(str(history_data["change_source"]))

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
        db_user = get_changed_by_user_or_404(db, history_data["changed_by_user_id"])

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

        if history_data["change_source"] == "admin" and db_user.role != ADMIN_ROLE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Admin-sourced changes require an admin user.",
            )


def validate_participant_status_history_update_fields(
    update_data: dict[str, object],
) -> None:
    immutable_fields = PARTICIPANT_IMMUTABLE_HISTORY_UPDATE_FIELDS & update_data.keys()

    if immutable_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Participant status history lifecycle fields cannot be changed "
                "after creation."
            ),
        )


def create_participant_status_history_record(
    db: Session,
    payload: ParticipantStatusHistoryCreate,
) -> ParticipantStatusHistory:
    history_data = payload.model_dump()
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
            detail=build_status_history_conflict_detail(exc),
        ) from exc

    return new_participant_status_history


def get_participant_status_history_record(
    db: Session,
    history_id: uuid.UUID,
) -> ParticipantStatusHistory:
    return get_participant_status_history_or_404(db, history_id)


def list_participant_status_history_records(
    db: Session,
    *,
    participant_id: uuid.UUID | None = None,
    changed_by_user_id: uuid.UUID | None = None,
    change_source: str | None = None,
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
        validate_change_source(change_source)
        statement = statement.where(
            ParticipantStatusHistory.change_source == change_source
        )

    history_rows = db.scalars(
        statement.order_by(ParticipantStatusHistory.created_at.asc())
    ).all()
    return list(history_rows)


def update_participant_status_history_record(
    db: Session,
    history_id: uuid.UUID,
    payload: ParticipantStatusHistoryUpdate,
) -> ParticipantStatusHistory:
    db_history = get_participant_status_history_or_404(db, history_id)
    update_data = payload.model_dump(exclude_unset=True)
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
            detail=build_status_history_conflict_detail(exc),
        ) from exc

    return db_history
