import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Payment, Refund, User
from backend.schemas import RefundCreate, RefundRead, RefundUpdate
from backend.services.admin_permission_service import (
    PERMISSION_MONEY_READ,
    PERMISSION_MONEY_REFUND,
    require_user_admin_permission,
    user_has_admin_permission,
)
from backend.services.auth_service import (
    get_current_app_user,
    require_active_account,
    require_admin_permission,
)
from backend.services.refund_service import (
    VALID_REFUND_REASONS,
    VALID_REFUND_STATUSES,
    create_refund_record,
    get_payment_or_404,
    update_refund_record,
)

router = APIRouter(prefix="/refunds", tags=["refunds"])


# This route records a Stripe-backed refund request or refund result after
# validating the payment and optional booking/participant scope.
@router.post("", response_model=RefundRead, status_code=status.HTTP_201_CREATED)
def create_refund(
    refund: RefundCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin_permission(PERMISSION_MONEY_REFUND)),
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
    db_refund = db.get(Refund, refund_id)

    if db_refund is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refund not found.",
        )

    db_payment = get_payment_or_404(db, db_refund.payment_id)
    if db_payment.payer_user_id != current_user.id:
        require_user_admin_permission(current_user, PERMISSION_MONEY_READ)

    return db_refund


# This route returns refund records currently stored in the app database.
@router.get("", response_model=list[RefundRead], status_code=status.HTTP_200_OK)
def list_refunds(
    payment_id: uuid.UUID | None = None,
    booking_id: uuid.UUID | None = None,
    participant_id: uuid.UUID | None = None,
    refund_status: str | None = None,
    refund_reason: str | None = None,
    requested_by_user_id: uuid.UUID | None = None,
    approved_by_user_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_app_user),
) -> list[Refund]:
    require_active_account(current_user)
    can_read_all_money = user_has_admin_permission(current_user, PERMISSION_MONEY_READ)
    statement = select(Refund).join(Payment, Refund.payment_id == Payment.id)

    if not can_read_all_money:
        statement = statement.where(Payment.payer_user_id == current_user.id)

    if payment_id is not None:
        statement = statement.where(Refund.payment_id == payment_id)

    if booking_id is not None:
        statement = statement.where(Refund.booking_id == booking_id)

    if participant_id is not None:
        statement = statement.where(Refund.participant_id == participant_id)

    if refund_status is not None:
        if refund_status not in VALID_REFUND_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "refund_status must be 'pending', 'approved', 'processing', "
                    "'succeeded', 'failed', or 'cancelled'."
                ),
            )
        statement = statement.where(Refund.refund_status == refund_status)

    if refund_reason is not None:
        if refund_reason not in VALID_REFUND_REASONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "refund_reason must be 'player_cancelled', 'late_cancel', "
                    "'host_cancelled', 'game_cancelled', 'weather', 'admin_refund', "
                    "'duplicate_payment', or 'dispute_resolution'."
                ),
            )
        statement = statement.where(Refund.refund_reason == refund_reason)

    if requested_by_user_id is not None:
        statement = statement.where(Refund.requested_by_user_id == requested_by_user_id)

    if approved_by_user_id is not None:
        statement = statement.where(Refund.approved_by_user_id == approved_by_user_id)

    refunds = db.scalars(statement.order_by(Refund.created_at.desc())).all()
    return list(refunds)


# This route applies partial updates to an existing refund record while keeping
# references, amount limits, and lifecycle timestamps aligned with status.
@router.patch("/{refund_id}", response_model=RefundRead, status_code=status.HTTP_200_OK)
def update_refund(
    refund_id: uuid.UUID,
    refund_update: RefundUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin_permission(PERMISSION_MONEY_REFUND)),
) -> Refund:
    return update_refund_record(
        db,
        admin_user=current_admin,
        refund_id=refund_id,
        payload=refund_update,
    )
