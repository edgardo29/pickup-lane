import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Payment, User
from backend.schemas import PaymentCreate, PaymentRead, PaymentUpdate
from backend.services.admin_permission_service import (
    PERMISSION_MONEY_PAYMENT_MANAGE,
)
from backend.services.auth_service import (
    get_current_app_user,
    require_active_account,
    require_admin_permission,
)
from backend.services.payment_service import (
    create_payment_record,
    get_payment_for_user_or_404,
    list_payments as list_payments_workflow,
    update_payment_record,
)

router = APIRouter(prefix="/payments", tags=["payments"])


# This route records a Stripe-backed payment attempt or payment result after
# validating the payer and any booking/game references.
@router.post("", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
def create_payment(
    payment: PaymentCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_MONEY_PAYMENT_MANAGE)
    ),
) -> Payment:
    return create_payment_record(db, admin_user=current_admin, payload=payment)


# This route fetches a single payment record by its internal UUID.
@router.get("/{payment_id}", response_model=PaymentRead, status_code=status.HTTP_200_OK)
def get_payment(
    payment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_app_user),
) -> Payment:
    require_active_account(current_user)
    return get_payment_for_user_or_404(db, payment_id, current_user)


# This route returns payment records currently stored in the app database.
@router.get("", response_model=list[PaymentRead], status_code=status.HTTP_200_OK)
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


# This route applies partial updates to an existing payment record while
# keeping references and payment lifecycle timestamps aligned with status.
@router.patch(
    "/{payment_id}", response_model=PaymentRead, status_code=status.HTTP_200_OK
)
def update_payment(
    payment_id: uuid.UUID,
    payment_update: PaymentUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_MONEY_PAYMENT_MANAGE)
    ),
) -> Payment:
    return update_payment_record(
        db,
        admin_user=current_admin,
        payment_id=payment_id,
        payload=payment_update,
    )
