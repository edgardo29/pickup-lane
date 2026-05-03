import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import HostDeposit, HostDepositEvent, User
from backend.schemas import (
    HostDepositEventCreate,
    HostDepositEventRead,
    HostDepositEventUpdate,
)

router = APIRouter(prefix="/host-deposit-events", tags=["host_deposit_events"])

VALID_DEPOSIT_STATUSES = {
    "required",
    "payment_pending",
    "paid",
    "held",
    "released",
    "refunded",
    "forfeited",
    "waived",
}
VALID_CHANGE_SOURCES = {
    "user",
    "host",
    "admin",
    "system",
    "payment_webhook",
    "scheduled_job",
}
IMMUTABLE_HOST_DEPOSIT_EVENT_UPDATE_FIELDS = {
    "host_deposit_id",
    "old_status",
    "new_status",
    "changed_by_user_id",
    "change_source",
}


def build_host_deposit_event_conflict_detail(exc: IntegrityError) -> str:
    return str(exc.orig)


def get_host_deposit_or_404(
    db: Session,
    host_deposit_id: uuid.UUID,
) -> HostDeposit:
    db_host_deposit = db.get(HostDeposit, host_deposit_id)

    if db_host_deposit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Host deposit not found.",
        )

    return db_host_deposit


def get_active_user_or_404(db: Session, user_id: uuid.UUID) -> User:
    db_user = db.get(User, user_id)

    if db_user is None or db_user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Changed by user not found.",
        )

    return db_user


def validate_host_deposit_event_business_rules(
    event_data: dict[str, object],
) -> None:
    for field_name in ("host_deposit_id", "new_status", "change_source"):
        if event_data[field_name] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} cannot be null.",
            )

    if (
        event_data["old_status"] is not None
        and event_data["old_status"] not in VALID_DEPOSIT_STATUSES
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="old_status is not supported.",
        )

    if event_data["new_status"] not in VALID_DEPOSIT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="new_status is not supported.",
        )

    if event_data["change_source"] not in VALID_CHANGE_SOURCES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "change_source must be 'user', 'host', 'admin', 'system', "
                "'payment_webhook', or 'scheduled_job'."
            ),
        )

    if event_data["old_status"] == event_data["new_status"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Host deposit event must change status.",
        )

    if event_data["new_status"] in {"forfeited", "waived"} and event_data["reason"] is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Forfeited and waived host deposit events require reason.",
        )


def validate_host_deposit_event_references(
    db: Session,
    event_data: dict[str, object],
) -> None:
    db_host_deposit = get_host_deposit_or_404(db, event_data["host_deposit_id"])

    if event_data["changed_by_user_id"] is not None:
        db_user = get_active_user_or_404(db, event_data["changed_by_user_id"])

        if (
            event_data["change_source"] in {"user", "host"}
            and db_user.id != db_host_deposit.host_user_id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "User and host sourced changes must be made by the host user."
                ),
            )

        if event_data["change_source"] == "admin" and db_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Admin-sourced changes require an admin user.",
            )


def validate_host_deposit_event_update_fields(
    update_data: dict[str, object],
) -> None:
    immutable_fields = IMMUTABLE_HOST_DEPOSIT_EVENT_UPDATE_FIELDS & update_data.keys()

    if immutable_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Host deposit event lifecycle fields cannot be changed "
                "after creation."
            ),
        )


# This route records one append-only host deposit lifecycle audit row after
# validating the host deposit, optional actor, status values, and change source.
@router.post(
    "",
    response_model=HostDepositEventRead,
    status_code=status.HTTP_201_CREATED,
)
def create_host_deposit_event(
    host_deposit_event: HostDepositEventCreate,
    db: Session = Depends(get_db),
) -> HostDepositEvent:
    event_data = host_deposit_event.model_dump()
    validate_host_deposit_event_business_rules(event_data)
    validate_host_deposit_event_references(db, event_data)

    new_host_deposit_event = HostDepositEvent(
        id=uuid.uuid4(),
        **event_data,
    )

    try:
        db.add(new_host_deposit_event)
        db.commit()
        db.refresh(new_host_deposit_event)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_host_deposit_event_conflict_detail(exc),
        ) from exc

    return new_host_deposit_event


# This route fetches a single host deposit event audit row by its internal UUID.
@router.get(
    "/{event_id}",
    response_model=HostDepositEventRead,
    status_code=status.HTTP_200_OK,
)
def get_host_deposit_event(
    event_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> HostDepositEvent:
    db_event = db.get(HostDepositEvent, event_id)

    if db_event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Host deposit event not found.",
        )

    return db_event


# This route returns host deposit event rows currently stored in the app
# database, ordered from oldest to newest for audit readability.
@router.get(
    "",
    response_model=list[HostDepositEventRead],
    status_code=status.HTTP_200_OK,
)
def list_host_deposit_events(
    host_deposit_id: uuid.UUID | None = None,
    changed_by_user_id: uuid.UUID | None = None,
    change_source: str | None = None,
    db: Session = Depends(get_db),
) -> list[HostDepositEvent]:
    statement = select(HostDepositEvent)

    if host_deposit_id is not None:
        statement = statement.where(HostDepositEvent.host_deposit_id == host_deposit_id)

    if changed_by_user_id is not None:
        statement = statement.where(
            HostDepositEvent.changed_by_user_id == changed_by_user_id
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
        statement = statement.where(HostDepositEvent.change_source == change_source)

    event_rows = db.scalars(
        statement.order_by(HostDepositEvent.created_at.asc())
    ).all()
    return list(event_rows)


# This route allows correcting the explanatory reason on an audit row while
# keeping the recorded lifecycle change itself immutable.
@router.patch(
    "/{event_id}",
    response_model=HostDepositEventRead,
    status_code=status.HTTP_200_OK,
)
def update_host_deposit_event(
    event_id: uuid.UUID,
    host_deposit_event_update: HostDepositEventUpdate,
    db: Session = Depends(get_db),
) -> HostDepositEvent:
    db_event = db.get(HostDepositEvent, event_id)

    if db_event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Host deposit event not found.",
        )

    update_data = host_deposit_event_update.model_dump(exclude_unset=True)
    validate_host_deposit_event_update_fields(update_data)

    if "reason" in update_data:
        db_event.reason = update_data["reason"]

    try:
        db.add(db_event)
        db.commit()
        db.refresh(db_event)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_host_deposit_event_conflict_detail(exc),
        ) from exc

    return db_event
