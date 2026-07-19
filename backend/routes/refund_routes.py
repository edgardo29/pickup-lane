import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Refund, User
from backend.schemas import RefundCreate, RefundRead, RefundUpdate
from backend.services.auth_service import get_current_app_user, require_active_account, require_active_admin
from backend.services.refund_service import (
    create_refund_record,
    get_refund_for_user_or_404,
    list_refunds as list_refunds_workflow,
    update_refund_record,
)

router = APIRouter(prefix="/refunds", tags=["refunds"])


# This route records a Stripe-backed refund request or refund result after
# validating the payment and optional booking/participant scope.
@router.post("", response_model=RefundRead, status_code=status.HTTP_201_CREATED)
def create_refund(
    refund: RefundCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> Refund:
    return create_refund_record(db, admin_user=current_admin, payload=refund)


# This route fetches a single refund record by its internal UUID.
@router.get("/{refund_id}", response_model=RefundRead, status_code=status.HTTP_200_OK)
def get_refund(
    refund_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_app_user),
) -> Refund:
    require_active_account(current_user)
    return get_refund_for_user_or_404(db, refund_id, current_user)


# This route returns refund records currently stored in the app database.
@router.get("", response_model=list[RefundRead], status_code=status.HTTP_200_OK)
def list_refunds(
    payment_id: uuid.UUID | None = None,
    booking_id: uuid.UUID | None = None,
    participant_id: uuid.UUID | None = None,
    host_publish_fee_id: uuid.UUID | None = None,
    refund_status: str | None = None,
    refund_reason: str | None = None,
    requested_by_user_id: uuid.UUID | None = None,
    approved_by_user_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_app_user),
) -> list[Refund]:
    require_active_account(current_user)
    return list_refunds_workflow(
        db,
        current_user,
        payment_id=payment_id,
        booking_id=booking_id,
        participant_id=participant_id,
        host_publish_fee_id=host_publish_fee_id,
        refund_status=refund_status,
        refund_reason=refund_reason,
        requested_by_user_id=requested_by_user_id,
        approved_by_user_id=approved_by_user_id,
    )


# This route applies partial updates to an existing refund record while keeping
# references, amount limits, and lifecycle timestamps aligned with status.
@router.patch("/{refund_id}", response_model=RefundRead, status_code=status.HTTP_200_OK)
def update_refund(
    refund_id: uuid.UUID,
    refund_update: RefundUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> Refund:
    return update_refund_record(
        db,
        admin_user=current_admin,
        refund_id=refund_id,
        payload=refund_update,
    )
