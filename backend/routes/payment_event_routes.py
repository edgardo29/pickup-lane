import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Payment, PaymentEvent
from backend.schemas import PaymentEventCreate, PaymentEventRead, PaymentEventUpdate

router = APIRouter(prefix="/payment-events", tags=["payment_events"])

VALID_PROVIDERS = {"stripe"}
VALID_PROCESSING_STATUSES = {
    "pending",
    "processed",
    "failed",
    "ignored",
}
IMMUTABLE_PAYMENT_EVENT_UPDATE_FIELDS = {
    "provider",
    "provider_event_id",
    "event_type",
    "raw_payload",
}


def build_payment_event_conflict_detail(exc: IntegrityError) -> str:
    error_text = str(exc.orig)

    if "uq_payment_events_provider_event_id" in error_text:
        return "This provider event has already been recorded."

    if "ck_payment_events_provider" in error_text:
        return "provider must be 'stripe'."

    if "ck_payment_events_processing_status" in error_text:
        return "processing_status must be 'pending', 'processed', 'failed', or 'ignored'."

    if "ck_payment_events_event_type_not_empty" in error_text:
        return "event_type must not be empty."

    return error_text


def get_payment_or_404(db: Session, payment_id: uuid.UUID) -> Payment:
    db_payment = db.get(Payment, payment_id)

    if db_payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found.",
        )

    return db_payment


def validate_payment_event_business_rules(event_data: dict[str, Any]) -> None:
    for field_name in (
        "provider",
        "provider_event_id",
        "event_type",
        "raw_payload",
        "processing_status",
    ):
        if event_data[field_name] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} cannot be null.",
            )

    if event_data["provider"] not in VALID_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="provider must be 'stripe'.",
        )

    if event_data["processing_status"] not in VALID_PROCESSING_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "processing_status must be 'pending', 'processed', 'failed', "
                "or 'ignored'."
            ),
        )

    if not event_data["provider_event_id"].strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="provider_event_id must not be empty.",
        )

    if not event_data["event_type"].strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="event_type must not be empty.",
        )

    if event_data["processing_status"] == "failed" and not event_data["processing_error"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed payment events require processing_error.",
        )


def normalize_payment_event_lifecycle_fields(
    event_data: dict[str, Any],
) -> dict[str, Any]:
    normalized_data = dict(event_data)

    # processed_at is derived when an event is marked processed so clients do
    # not have to keep processing_status and timestamp fields aligned.
    if normalized_data["processing_status"] == "processed":
        normalized_data["processed_at"] = (
            normalized_data.get("processed_at") or datetime.now(timezone.utc)
        )
    elif normalized_data["processing_status"] != "processed":
        normalized_data["processed_at"] = None

    if normalized_data["processing_status"] != "failed":
        normalized_data["processing_error"] = None

    return normalized_data


def validate_payment_event_references(
    db: Session,
    event_data: dict[str, Any],
) -> None:
    if event_data["payment_id"] is not None:
        get_payment_or_404(db, event_data["payment_id"])


def validate_payment_event_update_fields(update_data: dict[str, Any]) -> None:
    immutable_fields = IMMUTABLE_PAYMENT_EVENT_UPDATE_FIELDS & update_data.keys()

    if immutable_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment event provider fields cannot be changed after creation.",
        )


# This route records one durable provider webhook/event row. The current payment
# status remains on the payments table; this is the event audit record.
@router.post("", response_model=PaymentEventRead, status_code=status.HTTP_201_CREATED)
def create_payment_event(
    payment_event: PaymentEventCreate,
    db: Session = Depends(get_db),
) -> PaymentEvent:
    event_data = normalize_payment_event_lifecycle_fields(payment_event.model_dump())
    validate_payment_event_business_rules(event_data)
    validate_payment_event_references(db, event_data)

    new_payment_event = PaymentEvent(
        id=uuid.uuid4(),
        **event_data,
    )

    try:
        db.add(new_payment_event)
        db.commit()
        db.refresh(new_payment_event)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_payment_event_conflict_detail(exc),
        ) from exc

    return new_payment_event


# This route fetches a single payment provider event by its internal UUID.
@router.get(
    "/{payment_event_id}",
    response_model=PaymentEventRead,
    status_code=status.HTTP_200_OK,
)
def get_payment_event(
    payment_event_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> PaymentEvent:
    db_payment_event = db.get(PaymentEvent, payment_event_id)

    if db_payment_event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment event not found.",
        )

    return db_payment_event


# This route returns payment provider event rows currently stored in the app
# database, newest first for webhook/debug review.
@router.get("", response_model=list[PaymentEventRead], status_code=status.HTTP_200_OK)
def list_payment_events(
    payment_id: uuid.UUID | None = None,
    provider_event_id: str | None = None,
    event_type: str | None = None,
    processing_status: str | None = None,
    db: Session = Depends(get_db),
) -> list[PaymentEvent]:
    statement = select(PaymentEvent)

    if payment_id is not None:
        statement = statement.where(PaymentEvent.payment_id == payment_id)

    if provider_event_id is not None:
        statement = statement.where(PaymentEvent.provider_event_id == provider_event_id)

    if event_type is not None:
        statement = statement.where(PaymentEvent.event_type == event_type)

    if processing_status is not None:
        if processing_status not in VALID_PROCESSING_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "processing_status must be 'pending', 'processed', 'failed', "
                    "or 'ignored'."
                ),
            )
        statement = statement.where(PaymentEvent.processing_status == processing_status)

    payment_events = db.scalars(
        statement.order_by(PaymentEvent.created_at.desc())
    ).all()
    return list(payment_events)


# This route allows linking a previously unmatched event to a payment and
# updating its processing result, while keeping the provider event payload fixed.
@router.patch(
    "/{payment_event_id}",
    response_model=PaymentEventRead,
    status_code=status.HTTP_200_OK,
)
def update_payment_event(
    payment_event_id: uuid.UUID,
    payment_event_update: PaymentEventUpdate,
    db: Session = Depends(get_db),
) -> PaymentEvent:
    db_payment_event = db.get(PaymentEvent, payment_event_id)

    if db_payment_event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment event not found.",
        )

    update_data = payment_event_update.model_dump(exclude_unset=True)
    validate_payment_event_update_fields(update_data)

    effective_event_data = {
        "payment_id": update_data.get("payment_id", db_payment_event.payment_id),
        "provider": db_payment_event.provider,
        "provider_event_id": db_payment_event.provider_event_id,
        "event_type": db_payment_event.event_type,
        "raw_payload": db_payment_event.raw_payload,
        "processing_status": update_data.get(
            "processing_status",
            db_payment_event.processing_status,
        ),
        "processed_at": update_data.get("processed_at", db_payment_event.processed_at),
        "processing_error": update_data.get(
            "processing_error",
            db_payment_event.processing_error,
        ),
    }
    effective_event_data = normalize_payment_event_lifecycle_fields(effective_event_data)
    validate_payment_event_business_rules(effective_event_data)
    validate_payment_event_references(db, effective_event_data)

    update_data["processed_at"] = effective_event_data["processed_at"]
    update_data["processing_error"] = effective_event_data["processing_error"]

    for field_name, field_value in update_data.items():
        setattr(db_payment_event, field_name, field_value)

    try:
        db.add(db_payment_event)
        db.commit()
        db.refresh(db_payment_event)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_payment_event_conflict_detail(exc),
        ) from exc

    return db_payment_event