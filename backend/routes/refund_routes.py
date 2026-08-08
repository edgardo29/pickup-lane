import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Refund, User
from backend.routes.retired_route_helpers import raise_retired_mutation_route
from backend.schemas import RefundRead
from backend.services.auth_service import (
    get_current_app_user,
    require_active_account,
    require_active_admin,
)
from backend.services.refund_service import (
    get_refund_for_user_or_404,
    list_refunds as list_refunds_workflow,
)

router = APIRouter(prefix="/refunds", tags=["refunds"])


@router.post("", status_code=status.HTTP_410_GONE)
def create_refund(
    current_admin: User = Depends(require_active_admin),
) -> None:
    del current_admin
    raise_retired_mutation_route(
        code="refund_generic_mutation_removed",
        message=(
            "Generic refund creation is retired. Use supported refund, retry, "
            "or reconcile workflows."
        ),
    )


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


@router.patch("/{refund_id}", status_code=status.HTTP_410_GONE)
def update_refund(
    refund_id: uuid.UUID,
    current_admin: User = Depends(require_active_admin),
) -> None:
    del refund_id, current_admin
    raise_retired_mutation_route(
        code="refund_generic_mutation_removed",
        message=(
            "Generic refund updates are retired. Use supported refund, retry, "
            "or reconcile workflows."
        ),
    )
