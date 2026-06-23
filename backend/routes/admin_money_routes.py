import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.schemas import (
    AdminMoneyCreditDetailRead,
    AdminMoneyCreditGrantSummaryRead,
    AdminMoneyPaymentDetailRead,
    AdminMoneyPaymentListRead,
    AdminMoneyPaymentMethodRead,
    AdminMoneyRefundDetailRead,
    AdminMoneyRefundListRead,
    AdminMoneyRefundRetryCreate,
    AdminMoneySupportFlagDetailRead,
    AdminMoneySupportFlagSummaryRead,
    AdminMoneyUserDetailRead,
    SupportFlagResolve,
)
from backend.services.admin_money_credit_service import (
    get_admin_money_credit_detail,
    list_admin_money_credits,
)
from backend.services.admin_money_payment_service import (
    get_admin_money_payment_detail,
    list_admin_money_payments,
)
from backend.services.admin_money_refund_service import (
    get_admin_money_refund_detail,
    list_admin_money_refunds,
    retry_admin_money_refund,
)
from backend.services.admin_money_support_flag_read_service import (
    get_admin_money_support_flag_detail,
    list_admin_money_support_flags,
)
from backend.services.admin_money_support_flag_service import (
    resolve_admin_money_support_flag,
)
from backend.services.admin_money_user_service import (
    get_admin_money_user_detail,
    list_admin_money_payment_methods,
)
from backend.services.admin_permission_service import (
    PERMISSION_MONEY_READ,
    PERMISSION_MONEY_REFUND,
)
from backend.services.auth_service import require_admin_permission

router = APIRouter(prefix="/admin/money", tags=["admin_money"])


@router.get(
    "/payment-methods",
    response_model=list[AdminMoneyPaymentMethodRead],
    status_code=status.HTTP_200_OK,
)
def list_admin_money_payment_methods_route(
    user_id: uuid.UUID = Query(...),
    include_inactive: bool = Query(default=False),
    current_admin: User = Depends(require_admin_permission(PERMISSION_MONEY_READ)),
    db: Session = Depends(get_db),
) -> list[AdminMoneyPaymentMethodRead]:
    return list_admin_money_payment_methods(
        db,
        user_id=user_id,
        include_inactive=include_inactive,
    )


@router.get(
    "/users/{user_id}",
    response_model=AdminMoneyUserDetailRead,
    status_code=status.HTTP_200_OK,
)
def get_admin_money_user(
    user_id: uuid.UUID,
    include_inactive_payment_methods: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=250),
    current_admin: User = Depends(require_admin_permission(PERMISSION_MONEY_READ)),
    db: Session = Depends(get_db),
) -> AdminMoneyUserDetailRead:
    return get_admin_money_user_detail(
        db,
        user_id=user_id,
        viewer_user=current_admin,
        include_inactive_payment_methods=include_inactive_payment_methods,
        limit=limit,
    )


@router.get(
    "/credits",
    response_model=list[AdminMoneyCreditGrantSummaryRead],
    status_code=status.HTTP_200_OK,
)
def list_admin_money_credits_route(
    user_id: uuid.UUID | None = None,
    credit_status: str = Query(default="all"),
    source_game_id: uuid.UUID | None = None,
    source_booking_id: uuid.UUID | None = None,
    source_payment_id: uuid.UUID | None = None,
    limit: int = Query(default=100, ge=1, le=250),
    current_admin: User = Depends(require_admin_permission(PERMISSION_MONEY_READ)),
    db: Session = Depends(get_db),
) -> list[AdminMoneyCreditGrantSummaryRead]:
    return list_admin_money_credits(
        db,
        user_id=user_id,
        credit_status=credit_status,
        source_game_id=source_game_id,
        source_booking_id=source_booking_id,
        source_payment_id=source_payment_id,
        limit=limit,
    )


@router.get(
    "/credits/{game_credit_id}",
    response_model=AdminMoneyCreditDetailRead,
    status_code=status.HTTP_200_OK,
)
def get_admin_money_credit(
    game_credit_id: uuid.UUID,
    current_admin: User = Depends(require_admin_permission(PERMISSION_MONEY_READ)),
    db: Session = Depends(get_db),
) -> AdminMoneyCreditDetailRead:
    return get_admin_money_credit_detail(
        db,
        game_credit_id=game_credit_id,
        viewer_user=current_admin,
    )


@router.get(
    "/payments",
    response_model=list[AdminMoneyPaymentListRead],
    status_code=status.HTTP_200_OK,
)
def list_admin_money_payments_route(
    user_id: uuid.UUID | None = None,
    payment_status: str = Query(default="all"),
    booking_id: uuid.UUID | None = None,
    game_id: uuid.UUID | None = None,
    limit: int = Query(default=100, ge=1, le=250),
    current_admin: User = Depends(require_admin_permission(PERMISSION_MONEY_READ)),
    db: Session = Depends(get_db),
) -> list[AdminMoneyPaymentListRead]:
    return list_admin_money_payments(
        db,
        user_id=user_id,
        payment_status=payment_status,
        booking_id=booking_id,
        game_id=game_id,
        limit=limit,
    )


@router.get(
    "/payments/{payment_id}",
    response_model=AdminMoneyPaymentDetailRead,
    status_code=status.HTTP_200_OK,
)
def get_admin_money_payment(
    payment_id: uuid.UUID,
    current_admin: User = Depends(require_admin_permission(PERMISSION_MONEY_READ)),
    db: Session = Depends(get_db),
) -> AdminMoneyPaymentDetailRead:
    return get_admin_money_payment_detail(
        db,
        payment_id=payment_id,
        viewer_user=current_admin,
    )


@router.get(
    "/refunds",
    response_model=list[AdminMoneyRefundListRead],
    status_code=status.HTTP_200_OK,
)
def list_admin_money_refunds_route(
    user_id: uuid.UUID | None = None,
    refund_status: str = Query(default="all"),
    payment_id: uuid.UUID | None = None,
    booking_id: uuid.UUID | None = None,
    game_id: uuid.UUID | None = None,
    limit: int = Query(default=100, ge=1, le=250),
    current_admin: User = Depends(require_admin_permission(PERMISSION_MONEY_READ)),
    db: Session = Depends(get_db),
) -> list[AdminMoneyRefundListRead]:
    return list_admin_money_refunds(
        db,
        user_id=user_id,
        refund_status=refund_status,
        payment_id=payment_id,
        booking_id=booking_id,
        game_id=game_id,
        limit=limit,
    )


@router.get(
    "/refunds/{refund_id}",
    response_model=AdminMoneyRefundDetailRead,
    status_code=status.HTTP_200_OK,
)
def get_admin_money_refund(
    refund_id: uuid.UUID,
    current_admin: User = Depends(require_admin_permission(PERMISSION_MONEY_READ)),
    db: Session = Depends(get_db),
) -> AdminMoneyRefundDetailRead:
    return get_admin_money_refund_detail(
        db,
        refund_id=refund_id,
        viewer_user=current_admin,
    )


@router.post(
    "/refunds/{refund_id}/retry",
    response_model=AdminMoneyRefundDetailRead,
    status_code=status.HTTP_200_OK,
)
def retry_admin_money_refund_route(
    refund_id: uuid.UUID,
    payload: AdminMoneyRefundRetryCreate,
    current_admin: User = Depends(require_admin_permission(PERMISSION_MONEY_REFUND)),
    db: Session = Depends(get_db),
) -> AdminMoneyRefundDetailRead:
    return retry_admin_money_refund(
        db,
        admin_user=current_admin,
        refund_id=refund_id,
        payload=payload,
    )


@router.get(
    "/support-flags",
    response_model=list[AdminMoneySupportFlagSummaryRead],
    status_code=status.HTTP_200_OK,
)
def list_admin_money_support_flags_route(
    flag_status: str = Query(default="open"),
    limit: int = Query(default=100, ge=1, le=250),
    current_admin: User = Depends(require_admin_permission(PERMISSION_MONEY_READ)),
    db: Session = Depends(get_db),
) -> list[AdminMoneySupportFlagSummaryRead]:
    return list_admin_money_support_flags(
        db,
        viewer_user=current_admin,
        flag_status=flag_status,
        limit=limit,
    )


@router.get(
    "/support-flags/{support_flag_id}",
    response_model=AdminMoneySupportFlagDetailRead,
    status_code=status.HTTP_200_OK,
)
def get_admin_money_support_flag(
    support_flag_id: uuid.UUID,
    current_admin: User = Depends(require_admin_permission(PERMISSION_MONEY_READ)),
    db: Session = Depends(get_db),
) -> AdminMoneySupportFlagDetailRead:
    return get_admin_money_support_flag_detail(
        db,
        support_flag_id=support_flag_id,
        viewer_user=current_admin,
    )


@router.post(
    "/support-flags/{support_flag_id}/resolve",
    response_model=AdminMoneySupportFlagDetailRead,
    status_code=status.HTTP_200_OK,
)
def resolve_admin_money_support_flag_route(
    support_flag_id: uuid.UUID,
    payload: SupportFlagResolve,
    current_admin: User = Depends(require_admin_permission(PERMISSION_MONEY_READ)),
    db: Session = Depends(get_db),
) -> AdminMoneySupportFlagDetailRead:
    return resolve_admin_money_support_flag(
        db,
        support_flag_id=support_flag_id,
        admin_user=current_admin,
        payload=payload,
    )
