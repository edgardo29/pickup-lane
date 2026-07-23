import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.schemas import (
    AdminMoneyFinancialOutcomeCreate,
    AdminMoneyFinancialOutcomeRead,
    AdminMoneyCreditDetailRead,
    AdminMoneyCreditListResponseRead,
    AdminMoneyIssueCreditRetryCreate,
    AdminMoneyIssueDetailRead,
    AdminMoneyIssueListResponseRead,
    AdminMoneyIssueResolveCreate,
    AdminMoneyPaymentDetailRead,
    AdminMoneyPaymentListResponseRead,
    AdminMoneyRefundDetailRead,
    AdminMoneyRefundEventListResponseRead,
    AdminMoneyRefundListResponseRead,
    AdminMoneyRefundReconcileCreate,
    AdminMoneyRefundRetryCreate,
    AdminMoneyUserDetailRead,
)
from backend.services.admin_money_credit_service import (
    get_admin_money_credit_detail,
    list_admin_money_credits,
)
from backend.services.admin_financial_outcome_service import (
    create_admin_financial_outcome,
    get_admin_financial_outcome_detail,
)
from backend.services.admin_money_payment_service import (
    get_admin_money_payment_detail,
    list_admin_money_payments,
)
from backend.services.admin_money_refund_service import (
    list_refund_events,
    get_admin_money_refund_detail,
    list_admin_money_refunds,
    reconcile_admin_money_refund,
    retry_admin_money_refund,
)
from backend.services.admin_money_issue_service import (
    get_admin_money_issue_detail,
    list_admin_money_issues_page,
    resolve_admin_money_issue,
    retry_admin_money_issue_credit,
)
from backend.services.admin_money_user_service import (
    get_admin_money_user_detail,
)
from backend.services.auth_service import require_active_admin

router = APIRouter(prefix="/admin/money", tags=["admin_money"])
MONEY_ISSUE_LIST_QUERY_PARAMS = frozenset(
    {
        "status",
        "issue_type",
        "user_id",
        "q",
        "limit",
        "cursor",
    }
)
MONEY_PAYMENT_LIST_QUERY_PARAMS = frozenset(
    {
        "q",
        "payment_status",
        "payment_type",
        "user_id",
        "limit",
        "cursor",
    }
)
MONEY_REFUND_LIST_QUERY_PARAMS = frozenset(
    {
        "q",
        "refund_status",
        "user_id",
        "payment_id",
        "limit",
        "cursor",
    }
)
MONEY_CREDIT_LIST_QUERY_PARAMS = frozenset(
    {
        "q",
        "credit_status",
        "user_id",
        "source_game_id",
        "source_booking_id",
        "source_payment_id",
        "limit",
        "cursor",
    }
)


@router.post(
    "/financial-outcomes",
    response_model=AdminMoneyFinancialOutcomeRead,
    status_code=status.HTTP_201_CREATED,
)
def create_admin_money_financial_outcome_route(
    payload: AdminMoneyFinancialOutcomeCreate,
    current_admin: User = Depends(require_active_admin),
    db: Session = Depends(get_db),
) -> AdminMoneyFinancialOutcomeRead:
    return create_admin_financial_outcome(
        db,
        admin_user=current_admin,
        payload=payload,
    )


@router.get(
    "/financial-outcomes/{financial_outcome_id}",
    response_model=AdminMoneyFinancialOutcomeRead,
    status_code=status.HTTP_200_OK,
)
def get_admin_money_financial_outcome_route(
    financial_outcome_id: uuid.UUID,
    current_admin: User = Depends(require_active_admin),
    db: Session = Depends(get_db),
) -> AdminMoneyFinancialOutcomeRead:
    return get_admin_financial_outcome_detail(
        db,
        financial_outcome_id=financial_outcome_id,
    )


@router.get(
    "/users/{user_id}",
    response_model=AdminMoneyUserDetailRead,
    status_code=status.HTTP_200_OK,
)
def get_admin_money_user(
    user_id: uuid.UUID,
    include_inactive_payment_methods: bool = Query(default=False),
    saved_cards_cursor: str | None = None,
    current_admin: User = Depends(require_active_admin),
    db: Session = Depends(get_db),
) -> AdminMoneyUserDetailRead:
    return get_admin_money_user_detail(
        db,
        user_id=user_id,
        viewer_user=current_admin,
        include_inactive_payment_methods=include_inactive_payment_methods,
        saved_cards_cursor=saved_cards_cursor,
    )


@router.get(
    "/issues",
    response_model=AdminMoneyIssueListResponseRead,
    status_code=status.HTTP_200_OK,
)
def list_admin_money_issues_route(
    request: Request,
    status_filter: str | None = Query(default=None, alias="status"),
    issue_type: str | None = None,
    user_id: uuid.UUID | None = None,
    q: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=50, ge=1, le=100),
    cursor: str | None = None,
    current_admin: User = Depends(require_active_admin),
    db: Session = Depends(get_db),
) -> AdminMoneyIssueListResponseRead:
    unsupported_params = sorted(
        set(request.query_params.keys()) - MONEY_ISSUE_LIST_QUERY_PARAMS
    )
    if unsupported_params:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Unsupported money issue list filter: "
                f"{', '.join(unsupported_params)}."
            ),
        )
    return list_admin_money_issues_page(
        db,
        issue_status=status_filter or "open",
        issue_type=issue_type,
        user_id=user_id,
        query_text=q,
        limit=limit,
        cursor=cursor,
    )


@router.get(
    "/issues/{money_issue_id}",
    response_model=AdminMoneyIssueDetailRead,
    status_code=status.HTTP_200_OK,
)
def get_admin_money_issue_route(
    money_issue_id: uuid.UUID,
    current_admin: User = Depends(require_active_admin),
    db: Session = Depends(get_db),
) -> AdminMoneyIssueDetailRead:
    return get_admin_money_issue_detail(db, money_issue_id=money_issue_id)


@router.post(
    "/issues/{money_issue_id}/resolve",
    response_model=AdminMoneyIssueDetailRead,
    status_code=status.HTTP_200_OK,
)
def resolve_admin_money_issue_route(
    money_issue_id: uuid.UUID,
    payload: AdminMoneyIssueResolveCreate,
    current_admin: User = Depends(require_active_admin),
    db: Session = Depends(get_db),
) -> AdminMoneyIssueDetailRead:
    return resolve_admin_money_issue(
        db,
        admin_user=current_admin,
        money_issue_id=money_issue_id,
        payload=payload,
    )


@router.post(
    "/issues/{money_issue_id}/retry-credit",
    response_model=AdminMoneyIssueDetailRead,
    status_code=status.HTTP_200_OK,
)
def retry_admin_money_issue_credit_route(
    money_issue_id: uuid.UUID,
    payload: AdminMoneyIssueCreditRetryCreate,
    current_admin: User = Depends(require_active_admin),
    db: Session = Depends(get_db),
) -> AdminMoneyIssueDetailRead:
    return retry_admin_money_issue_credit(
        db,
        admin_user=current_admin,
        money_issue_id=money_issue_id,
        payload=payload,
    )


@router.get(
    "/credits",
    response_model=AdminMoneyCreditListResponseRead,
    status_code=status.HTTP_200_OK,
)
def list_admin_money_credits_route(
    request: Request,
    user_id: uuid.UUID | None = None,
    credit_status: str = Query(default="all"),
    source_game_id: uuid.UUID | None = None,
    source_booking_id: uuid.UUID | None = None,
    source_payment_id: uuid.UUID | None = None,
    q: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=50, ge=1, le=100),
    cursor: str | None = None,
    current_admin: User = Depends(require_active_admin),
    db: Session = Depends(get_db),
) -> AdminMoneyCreditListResponseRead:
    unsupported_params = sorted(
        set(request.query_params.keys()) - MONEY_CREDIT_LIST_QUERY_PARAMS
    )
    if unsupported_params:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Unsupported money credit list filter: "
                f"{', '.join(unsupported_params)}."
            ),
        )
    return list_admin_money_credits(
        db,
        user_id=user_id,
        credit_status=credit_status,
        source_game_id=source_game_id,
        source_booking_id=source_booking_id,
        source_payment_id=source_payment_id,
        query_text=q,
        limit=limit,
        cursor=cursor,
    )


@router.get(
    "/credits/{game_credit_id}",
    response_model=AdminMoneyCreditDetailRead,
    status_code=status.HTTP_200_OK,
)
def get_admin_money_credit(
    game_credit_id: uuid.UUID,
    current_admin: User = Depends(require_active_admin),
    db: Session = Depends(get_db),
) -> AdminMoneyCreditDetailRead:
    return get_admin_money_credit_detail(
        db,
        game_credit_id=game_credit_id,
        viewer_user=current_admin,
    )


@router.get(
    "/payments",
    response_model=AdminMoneyPaymentListResponseRead,
    status_code=status.HTTP_200_OK,
)
def list_admin_money_payments_route(
    request: Request,
    user_id: uuid.UUID | None = None,
    payment_status: str = Query(default="all"),
    payment_type: str | None = None,
    q: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=50, ge=1, le=100),
    cursor: str | None = None,
    current_admin: User = Depends(require_active_admin),
    db: Session = Depends(get_db),
) -> AdminMoneyPaymentListResponseRead:
    unsupported_params = sorted(
        set(request.query_params.keys()) - MONEY_PAYMENT_LIST_QUERY_PARAMS
    )
    if unsupported_params:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Unsupported money payment list filter: "
                f"{', '.join(unsupported_params)}."
            ),
        )
    return list_admin_money_payments(
        db,
        user_id=user_id,
        payment_status=payment_status,
        payment_type=payment_type,
        query_text=q,
        limit=limit,
        cursor=cursor,
    )


@router.get(
    "/payments/{payment_id}",
    response_model=AdminMoneyPaymentDetailRead,
    status_code=status.HTTP_200_OK,
)
def get_admin_money_payment(
    payment_id: uuid.UUID,
    current_admin: User = Depends(require_active_admin),
    db: Session = Depends(get_db),
) -> AdminMoneyPaymentDetailRead:
    return get_admin_money_payment_detail(
        db,
        payment_id=payment_id,
        viewer_user=current_admin,
    )


@router.get(
    "/refunds",
    response_model=AdminMoneyRefundListResponseRead,
    status_code=status.HTTP_200_OK,
)
def list_admin_money_refunds_route(
    request: Request,
    user_id: uuid.UUID | None = None,
    refund_status: str = Query(default="all"),
    payment_id: uuid.UUID | None = None,
    q: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=50, ge=1, le=100),
    cursor: str | None = None,
    current_admin: User = Depends(require_active_admin),
    db: Session = Depends(get_db),
) -> AdminMoneyRefundListResponseRead:
    unsupported_params = sorted(
        set(request.query_params.keys()) - MONEY_REFUND_LIST_QUERY_PARAMS
    )
    if unsupported_params:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Unsupported money refund list filter: "
                f"{', '.join(unsupported_params)}."
            ),
        )
    return list_admin_money_refunds(
        db,
        user_id=user_id,
        refund_status=refund_status,
        payment_id=payment_id,
        query_text=q,
        limit=limit,
        cursor=cursor,
    )


@router.get(
    "/refunds/{refund_id}",
    response_model=AdminMoneyRefundDetailRead,
    status_code=status.HTTP_200_OK,
)
def get_admin_money_refund(
    refund_id: uuid.UUID,
    current_admin: User = Depends(require_active_admin),
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
    current_admin: User = Depends(require_active_admin),
    db: Session = Depends(get_db),
) -> AdminMoneyRefundDetailRead:
    return retry_admin_money_refund(
        db,
        admin_user=current_admin,
        refund_id=refund_id,
        payload=payload,
    )


@router.get(
    "/refunds/{refund_id}/events",
    response_model=AdminMoneyRefundEventListResponseRead,
    status_code=status.HTTP_200_OK,
)
def list_admin_money_refund_events_route(
    refund_id: uuid.UUID,
    event_type: str | None = None,
    event_source: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    cursor: str | None = None,
    current_admin: User = Depends(require_active_admin),
    db: Session = Depends(get_db),
) -> AdminMoneyRefundEventListResponseRead:
    return list_refund_events(
        db,
        refund_id,
        event_type=event_type,
        event_source=event_source,
        limit=limit,
        cursor=cursor,
    )


@router.post(
    "/refunds/{refund_id}/reconcile",
    response_model=AdminMoneyRefundDetailRead,
    status_code=status.HTTP_200_OK,
)
def reconcile_admin_money_refund_route(
    refund_id: uuid.UUID,
    payload: AdminMoneyRefundReconcileCreate,
    current_admin: User = Depends(require_active_admin),
    db: Session = Depends(get_db),
) -> AdminMoneyRefundDetailRead:
    return reconcile_admin_money_refund(
        db,
        admin_user=current_admin,
        refund_id=refund_id,
        payload=payload,
    )
