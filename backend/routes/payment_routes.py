import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Payment, User
from backend.routes.retired_route_helpers import raise_retired_mutation_route
from backend.schemas import PaymentSummaryRead
from backend.services.auth_service import (
    get_current_app_user,
    require_active_account,
    require_active_admin,
)
from backend.services.payment_service import (
    get_payment_for_user_or_404,
    list_payments as list_payments_workflow,
)

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("", status_code=status.HTTP_410_GONE)
def create_payment(
    current_admin: User = Depends(require_active_admin),
) -> None:
    del current_admin
    raise_retired_mutation_route(
        code="payment_generic_mutation_removed",
        message=(
            "Generic payment creation is retired. Use checkout, signed webhook, "
            "or supported admin-money workflows."
        ),
    )


# This route fetches a single payment record by its internal UUID.
@router.get(
    "/{payment_id}",
    response_model=PaymentSummaryRead,
    status_code=status.HTTP_200_OK,
)
def get_payment(
    payment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_app_user),
) -> Payment:
    require_active_account(current_user)
    return get_payment_for_user_or_404(db, payment_id, current_user)


# This route returns payment records currently stored in the app database.
@router.get("", response_model=list[PaymentSummaryRead], status_code=status.HTTP_200_OK)
def list_payments(
    payer_user_id: uuid.UUID | None = None,
    booking_id: uuid.UUID | None = None,
    game_id: uuid.UUID | None = None,
    payment_type: str | None = None,
    payment_status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_app_user),
) -> list[Payment]:
    require_active_account(current_user)
    return list_payments_workflow(
        db,
        current_user,
        payer_user_id=payer_user_id,
        booking_id=booking_id,
        game_id=game_id,
        payment_type=payment_type,
        payment_status=payment_status,
    )


@router.patch(
    "/{payment_id}",
    status_code=status.HTTP_410_GONE,
)
def update_payment(
    payment_id: uuid.UUID,
    current_admin: User = Depends(require_active_admin),
) -> None:
    del payment_id, current_admin
    raise_retired_mutation_route(
        code="payment_generic_mutation_removed",
        message=(
            "Generic payment updates are retired. Use checkout, signed webhook, "
            "or supported admin-money workflows."
        ),
    )
