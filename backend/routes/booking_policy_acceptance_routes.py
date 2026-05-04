import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Booking, BookingPolicyAcceptance, PolicyDocument
from backend.schemas import (
    BookingPolicyAcceptanceCreate,
    BookingPolicyAcceptanceRead,
    BookingPolicyAcceptanceUpdate,
)

router = APIRouter(
    prefix="/booking-policy-acceptances",
    tags=["booking_policy_acceptances"],
)


def build_booking_policy_acceptance_conflict_detail(exc: IntegrityError) -> str:
    error_text = str(exc.orig)

    if "uq_booking_policy_acceptances_booking_id_policy_document_id" in error_text:
        return "This booking has already accepted this policy document."

    return error_text


def get_booking_or_404(db: Session, booking_id: uuid.UUID) -> Booking:
    db_booking = db.get(Booking, booking_id)

    if db_booking is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found.",
        )

    return db_booking


def get_policy_document_or_404(
    db: Session,
    policy_document_id: uuid.UUID,
) -> PolicyDocument:
    db_policy_document = db.get(PolicyDocument, policy_document_id)

    if db_policy_document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy document not found.",
        )

    return db_policy_document


def validate_booking_policy_acceptance_business_rules(
    acceptance_data: dict[str, Any],
) -> None:
    for field_name in ("booking_id", "policy_document_id", "accepted_at"):
        if acceptance_data[field_name] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} cannot be null.",
            )


def normalize_booking_policy_acceptance_fields(
    acceptance_data: dict[str, Any],
) -> dict[str, Any]:
    normalized_data = dict(acceptance_data)

    if normalized_data["accepted_at"] is None:
        normalized_data["accepted_at"] = datetime.now(timezone.utc)

    return normalized_data


def validate_booking_policy_acceptance_references(
    db: Session,
    acceptance_data: dict[str, Any],
) -> None:
    get_booking_or_404(db, acceptance_data["booking_id"])
    db_policy_document = get_policy_document_or_404(
        db,
        acceptance_data["policy_document_id"],
    )

    now = datetime.now(timezone.utc)
    if (
        not db_policy_document.is_active
        or db_policy_document.retired_at is not None
        or db_policy_document.effective_at > now
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Booking policy acceptances require an active, non-retired "
                "policy document that is already effective."
            ),
        )


def validate_booking_policy_acceptance_update_rules(update_data: dict[str, Any]) -> None:
    if "accepted_at" in update_data and update_data["accepted_at"] is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="accepted_at cannot be null.",
        )


# This route records that one booking accepted one specific policy document
# version at confirmation/payment time.
@router.post(
    "",
    response_model=BookingPolicyAcceptanceRead,
    status_code=status.HTTP_201_CREATED,
)
def create_booking_policy_acceptance(
    booking_policy_acceptance: BookingPolicyAcceptanceCreate,
    db: Session = Depends(get_db),
) -> BookingPolicyAcceptance:
    acceptance_data = normalize_booking_policy_acceptance_fields(
        booking_policy_acceptance.model_dump()
    )
    validate_booking_policy_acceptance_business_rules(acceptance_data)
    validate_booking_policy_acceptance_references(db, acceptance_data)

    new_booking_policy_acceptance = BookingPolicyAcceptance(
        id=uuid.uuid4(),
        **acceptance_data,
    )

    try:
        db.add(new_booking_policy_acceptance)
        db.commit()
        db.refresh(new_booking_policy_acceptance)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_booking_policy_acceptance_conflict_detail(exc),
        ) from exc

    return new_booking_policy_acceptance


# This route fetches a single booking policy acceptance row by its internal UUID.
@router.get(
    "/{booking_policy_acceptance_id}",
    response_model=BookingPolicyAcceptanceRead,
    status_code=status.HTTP_200_OK,
)
def get_booking_policy_acceptance(
    booking_policy_acceptance_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> BookingPolicyAcceptance:
    db_booking_policy_acceptance = db.get(
        BookingPolicyAcceptance,
        booking_policy_acceptance_id,
    )

    if db_booking_policy_acceptance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking policy acceptance not found.",
        )

    return db_booking_policy_acceptance


# This route returns booking policy acceptance rows currently stored in the app
# database.
@router.get(
    "",
    response_model=list[BookingPolicyAcceptanceRead],
    status_code=status.HTTP_200_OK,
)
def list_booking_policy_acceptances(
    booking_id: uuid.UUID | None = None,
    policy_document_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
) -> list[BookingPolicyAcceptance]:
    statement = select(BookingPolicyAcceptance)

    if booking_id is not None:
        statement = statement.where(BookingPolicyAcceptance.booking_id == booking_id)

    if policy_document_id is not None:
        statement = statement.where(
            BookingPolicyAcceptance.policy_document_id == policy_document_id
        )

    booking_policy_acceptances = db.scalars(
        statement.order_by(BookingPolicyAcceptance.accepted_at.desc())
    ).all()
    return list(booking_policy_acceptances)


# This route allows correcting the acceptance timestamp without changing the
# booking or policy document.
@router.patch(
    "/{booking_policy_acceptance_id}",
    response_model=BookingPolicyAcceptanceRead,
    status_code=status.HTTP_200_OK,
)
def update_booking_policy_acceptance(
    booking_policy_acceptance_id: uuid.UUID,
    booking_policy_acceptance_update: BookingPolicyAcceptanceUpdate,
    db: Session = Depends(get_db),
) -> BookingPolicyAcceptance:
    db_booking_policy_acceptance = db.get(
        BookingPolicyAcceptance,
        booking_policy_acceptance_id,
    )

    if db_booking_policy_acceptance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking policy acceptance not found.",
        )

    update_data = booking_policy_acceptance_update.model_dump(exclude_unset=True)
    validate_booking_policy_acceptance_update_rules(update_data)

    for field_name, field_value in update_data.items():
        setattr(db_booking_policy_acceptance, field_name, field_value)

    try:
        db.add(db_booking_policy_acceptance)
        db.commit()
        db.refresh(db_booking_policy_acceptance)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_booking_policy_acceptance_conflict_detail(exc),
        ) from exc

    return db_booking_policy_acceptance
