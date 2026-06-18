import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Payment, User
from backend.schemas import PaymentCreate, PaymentRead, PaymentUpdate
from backend.services.admin_permission_service import (
    PERMISSION_MONEY_PAYMENT_MANAGE,
    PERMISSION_MONEY_READ,
    user_has_admin_permission,
)
from backend.services.auth_service import (
    get_current_app_user,
    require_active_account,
    require_admin_permission,
    require_user_admin_permission,
)
from backend.services.payment_service import (
    VALID_PAYMENT_STATUSES,
    VALID_PAYMENT_TYPES,
    create_payment_record,
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
    db_payment = db.get(Payment, payment_id)

    if db_payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found.",
        )

    if db_payment.payer_user_id != current_user.id:
        require_user_admin_permission(current_user, PERMISSION_MONEY_READ)

    return db_payment


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
    can_read_all_money = user_has_admin_permission(current_user, PERMISSION_MONEY_READ)
    statement = select(Payment)

    if payer_user_id is not None and payer_user_id != current_user.id:
        require_user_admin_permission(current_user, PERMISSION_MONEY_READ)
        can_read_all_money = True

    if not can_read_all_money:
        payer_user_id = current_user.id

    if payer_user_id is not None:
        statement = statement.where(Payment.payer_user_id == payer_user_id)

    if booking_id is not None:
        statement = statement.where(Payment.booking_id == booking_id)

    if game_id is not None:
        statement = statement.where(Payment.game_id == game_id)

    if payment_type is not None:
        if payment_type not in VALID_PAYMENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "payment_type must be 'booking', 'community_publish_fee', "
                    "'refund_adjustment', or 'admin_charge'."
                ),
            )
        statement = statement.where(Payment.payment_type == payment_type)

    if payment_status is not None:
        if payment_status not in VALID_PAYMENT_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "payment_status must be 'requires_payment_method', "
                    "'processing', 'requires_action', 'succeeded', 'failed', "
                    "'canceled', 'refunded', 'partially_refunded', or 'disputed'."
                ),
            )
        statement = statement.where(Payment.payment_status == payment_status)

    payments = db.scalars(statement.order_by(Payment.created_at.desc())).all()
    return list(payments)


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
