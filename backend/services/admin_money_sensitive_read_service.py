"""Commit resource-bound admin-money read audits before protected detail loads."""

import uuid

from sqlalchemy.orm import Session

from backend.models import User
from backend.schemas.admin_money_credit_detail_schema import AdminMoneyCreditDetailRead
from backend.schemas.admin_money_issue_detail_schema import AdminMoneyIssueDetailRead
from backend.schemas.admin_money_payment_detail_schema import (
    AdminMoneyPaymentDetailRead,
)
from backend.schemas.admin_money_refund_schema import (
    AdminMoneyRefundDetailRead,
    AdminMoneyRefundEventListResponseRead,
)
from backend.schemas.admin_money_user_schema import AdminMoneyUserDetailRead
from backend.services.admin_action_policy import (
    TARGET_FINANCIAL_OUTCOME_ID,
    TARGET_GAME_CREDIT_ID,
    TARGET_MONEY_ISSUE_ID,
    TARGET_PAYMENT_ID,
    TARGET_REFUND_ID,
    TARGET_USER_ID,
)
from backend.services.admin_action_service import (
    precheck_sensitive_read_target,
    record_financial_sensitive_read,
)
from backend.services.admin_financial_outcome_service import (
    get_admin_financial_outcome_detail,
)
from backend.services.admin_money_credit_service import get_admin_money_credit_detail
from backend.services.admin_money_cursor import parse_money_cursor
from backend.services.admin_money_issue_query_service import (
    get_admin_money_issue_detail,
)
from backend.services.admin_money_payment_service import get_admin_money_payment_detail
from backend.services.admin_money_refund_query_service import (
    get_admin_money_refund_detail,
    list_refund_events,
)
from backend.services.admin_money_user_service import (
    get_admin_money_user_detail,
    parse_offset_cursor,
)


def _audit_detail(
    db: Session,
    *,
    admin: User,
    action_type: str,
    target_field: str,
    target_id: uuid.UUID,
    not_found_detail: str,
    allow_deleted_user: bool = False,
) -> None:
    precheck_sensitive_read_target(
        db,
        target_field=target_field,
        target_id=target_id,
        not_found_detail=not_found_detail,
        allow_deleted_user=allow_deleted_user,
    )
    record_financial_sensitive_read(
        authenticated_admin_id=admin.id,
        action_type=action_type,
        target_id=target_id,
    )


def read_admin_money_financial_outcome_detail(
    db: Session, *, admin: User, financial_outcome_id: uuid.UUID
):
    _audit_detail(
        db,
        admin=admin,
        action_type="read_admin_money_financial_outcome_detail",
        target_field=TARGET_FINANCIAL_OUTCOME_ID,
        target_id=financial_outcome_id,
        not_found_detail="Financial outcome not found.",
    )
    return get_admin_financial_outcome_detail(
        db, financial_outcome_id=financial_outcome_id
    )


def read_admin_money_user_detail(
    db: Session,
    *,
    admin: User,
    user_id: uuid.UUID,
    include_inactive_payment_methods: bool,
    saved_cards_cursor: str | None,
) -> AdminMoneyUserDetailRead:
    parse_offset_cursor(saved_cards_cursor)
    _audit_detail(
        db,
        admin=admin,
        action_type="read_admin_money_user_detail",
        target_field=TARGET_USER_ID,
        target_id=user_id,
        not_found_detail="User not found.",
        allow_deleted_user=True,
    )
    return get_admin_money_user_detail(
        db,
        user_id=user_id,
        viewer_user=admin,
        include_inactive_payment_methods=include_inactive_payment_methods,
        saved_cards_cursor=saved_cards_cursor,
    )


def read_admin_money_issue_detail(
    db: Session, *, admin: User, money_issue_id: uuid.UUID
) -> AdminMoneyIssueDetailRead:
    _audit_detail(
        db,
        admin=admin,
        action_type="read_admin_money_issue_detail",
        target_field=TARGET_MONEY_ISSUE_ID,
        target_id=money_issue_id,
        not_found_detail="Money issue not found.",
    )
    return get_admin_money_issue_detail(db, money_issue_id=money_issue_id)


def read_admin_money_credit_detail(
    db: Session, *, admin: User, game_credit_id: uuid.UUID
) -> AdminMoneyCreditDetailRead:
    _audit_detail(
        db,
        admin=admin,
        action_type="read_admin_money_credit_detail",
        target_field=TARGET_GAME_CREDIT_ID,
        target_id=game_credit_id,
        not_found_detail="Credit not found.",
    )
    return get_admin_money_credit_detail(
        db, game_credit_id=game_credit_id, viewer_user=admin
    )


def read_admin_money_payment_detail(
    db: Session, *, admin: User, payment_id: uuid.UUID
) -> AdminMoneyPaymentDetailRead:
    _audit_detail(
        db,
        admin=admin,
        action_type="read_admin_money_payment_detail",
        target_field=TARGET_PAYMENT_ID,
        target_id=payment_id,
        not_found_detail="Payment not found.",
    )
    return get_admin_money_payment_detail(db, payment_id=payment_id, viewer_user=admin)


def read_admin_money_refund_detail(
    db: Session, *, admin: User, refund_id: uuid.UUID
) -> AdminMoneyRefundDetailRead:
    _audit_detail(
        db,
        admin=admin,
        action_type="read_admin_money_refund_detail",
        target_field=TARGET_REFUND_ID,
        target_id=refund_id,
        not_found_detail="Refund not found.",
    )
    return get_admin_money_refund_detail(db, refund_id=refund_id, viewer_user=admin)


def read_admin_money_refund_events(
    db: Session,
    *,
    admin: User,
    refund_id: uuid.UUID,
    event_type: str | None,
    event_source: str | None,
    limit: int,
    cursor: str | None,
) -> AdminMoneyRefundEventListResponseRead:
    parse_money_cursor(
        cursor,
        context={
            "event_source": event_source,
            "event_type": event_type,
            "kind": "admin_money_refund_events",
            "refund_id": str(refund_id),
        },
    )
    _audit_detail(
        db,
        admin=admin,
        action_type="read_admin_money_refund_events",
        target_field=TARGET_REFUND_ID,
        target_id=refund_id,
        not_found_detail="Refund not found.",
    )
    return list_refund_events(
        db,
        refund_id,
        event_type=event_type,
        event_source=event_source,
        limit=limit,
        cursor=cursor,
    )
