import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import PaymentEvent, User
from backend.schemas import PaymentEventCreate, PaymentEventRead, PaymentEventUpdate
from backend.services.auth_service import require_active_admin
from backend.services.payment_event_service import (
    create_payment_event_record,
    get_payment_event_record,
    list_payment_event_records,
    update_payment_event_record,
)

router = APIRouter(prefix="/payment-events", tags=["payment_events"])


# This route records one durable provider webhook/event row. The current payment
# status remains on the payments table; this is the event audit record.
@router.post("", response_model=PaymentEventRead, status_code=status.HTTP_201_CREATED)
def create_payment_event(
    payment_event: PaymentEventCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> PaymentEvent:
    del current_admin
    return create_payment_event_record(db, payment_event)


# This route fetches a single payment provider event by its internal UUID.
@router.get(
    "/{payment_event_id}",
    response_model=PaymentEventRead,
    status_code=status.HTTP_200_OK,
)
def get_payment_event(
    payment_event_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> PaymentEvent:
    del current_admin
    return get_payment_event_record(db, payment_event_id)


# This route returns payment provider event rows currently stored in the app
# database, newest first for webhook/debug review.
@router.get("", response_model=list[PaymentEventRead], status_code=status.HTTP_200_OK)
def list_payment_events(
    payment_id: uuid.UUID | None = None,
    provider_event_id: str | None = None,
    event_type: str | None = None,
    processing_status: str | None = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> list[PaymentEvent]:
    del current_admin
    return list_payment_event_records(
        db,
        payment_id=payment_id,
        provider_event_id=provider_event_id,
        event_type=event_type,
        processing_status=processing_status,
    )


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
    current_admin: User = Depends(require_active_admin),
) -> PaymentEvent:
    del current_admin
    return update_payment_event_record(db, payment_event_id, payment_event_update)
