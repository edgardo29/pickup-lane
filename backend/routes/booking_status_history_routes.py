import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Booking, BookingStatusHistory, User
from backend.schemas import (
    BookingStatusHistoryCreate,
    BookingStatusHistoryRead,
    BookingStatusHistoryUpdate,
)

router = APIRouter(prefix="/booking-status-history", tags=["booking_status_history"])

VALID_BOOKING_STATUSES = {
    "pending_payment",
    "confirmed",
    "partially_cancelled",
    "cancelled",
    "expired",
    "failed",
}
VALID_PAYMENT_STATUSES = {
    "unpaid",
    "requires_action",
    "processing",
    "paid",
    "failed",
    "partially_refunded",
    "refunded",
    "disputed",
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
    "booking_id",
    "old_booking_status",
    "new_booking_status",
    "old_payment_status",
    "new_payment_status",
    "changed_by_user_id",
    "change_source",
}


def build_booking_status_history_conflict_detail(exc: IntegrityError) -> str:
    return str(exc.orig)


def get_booking_or_404(db: Session, booking_id: uuid.UUID) -> Booking:
    db_booking = db.get(Booking, booking_id)

    if db_booking is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found.",
        )

    return db_booking


def get_active_user_or_404(db: Session, user_id: uuid.UUID) -> User:
    db_user = db.get(User, user_id)

    if db_user is None or db_user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Changed by user not found.",
        )

    return db_user


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

    if history_data["change_source"] not in VALID_CHANGE_SOURCES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "change_source must be 'user', 'host', 'admin', 'system', "
                "'payment_webhook', or 'scheduled_job'."
            ),
        )

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
        get_active_user_or_404(db, history_data["changed_by_user_id"])


def validate_booking_status_history_update_fields(update_data: dict[str, object]) -> None:
    immutable_fields = IMMUTABLE_HISTORY_UPDATE_FIELDS & update_data.keys()

    if immutable_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Booking status history lifecycle fields cannot be changed "
                "after creation."
            ),
        )


# This route records one append-only booking lifecycle audit row after
# validating the booking, optional actor, status values, and change source.
@router.post(
    "",
    response_model=BookingStatusHistoryRead,
    status_code=status.HTTP_201_CREATED,
)
def create_booking_status_history(
    booking_status_history: BookingStatusHistoryCreate,
    db: Session = Depends(get_db),
) -> BookingStatusHistory:
    history_data = booking_status_history.model_dump()
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
            detail=build_booking_status_history_conflict_detail(exc),
        ) from exc

    return new_booking_status_history


# This route fetches a single booking status history row by its internal UUID.
@router.get(
    "/{history_id}",
    response_model=BookingStatusHistoryRead,
    status_code=status.HTTP_200_OK,
)
def get_booking_status_history(
    history_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> BookingStatusHistory:
    db_history = db.get(BookingStatusHistory, history_id)

    if db_history is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking status history not found.",
        )

    return db_history


# This route returns booking status history rows currently stored in the app
# database, ordered from oldest to newest for audit readability.
@router.get(
    "",
    response_model=list[BookingStatusHistoryRead],
    status_code=status.HTTP_200_OK,
)
def list_booking_status_history(
    booking_id: uuid.UUID | None = None,
    changed_by_user_id: uuid.UUID | None = None,
    change_source: str | None = None,
    db: Session = Depends(get_db),
) -> list[BookingStatusHistory]:
    statement = select(BookingStatusHistory)

    if booking_id is not None:
        statement = statement.where(BookingStatusHistory.booking_id == booking_id)

    if changed_by_user_id is not None:
        statement = statement.where(
            BookingStatusHistory.changed_by_user_id == changed_by_user_id
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
        statement = statement.where(BookingStatusHistory.change_source == change_source)

    history_rows = db.scalars(
        statement.order_by(BookingStatusHistory.created_at.asc())
    ).all()
    return list(history_rows)


# This route allows correcting the explanatory reason on an audit row while
# keeping the recorded lifecycle change itself immutable.
@router.patch(
    "/{history_id}",
    response_model=BookingStatusHistoryRead,
    status_code=status.HTTP_200_OK,
)
def update_booking_status_history(
    history_id: uuid.UUID,
    history_update: BookingStatusHistoryUpdate,
    db: Session = Depends(get_db),
) -> BookingStatusHistory:
    db_history = db.get(BookingStatusHistory, history_id)

    if db_history is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking status history not found.",
        )

    update_data = history_update.model_dump(exclude_unset=True)
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
            detail=build_booking_status_history_conflict_detail(exc),
        ) from exc

    return db_history
