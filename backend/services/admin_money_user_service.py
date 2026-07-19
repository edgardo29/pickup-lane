"""Read-only admin user money summaries and saved-card metadata."""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.models import (
    AdminAction,
    GameCredit,
    GameCreditUsage,
    Payment,
    Refund,
    SupportFlag,
    User,
    UserPaymentMethod,
)
from backend.schemas.admin_money_schema import AdminMoneyUserDetailRead
from backend.services.admin_action_service import user_can_read_admin_action
from backend.services.admin_money_support_flag_read_service import (
    MONEY_SUPPORT_FLAG_TYPES,
)
from backend.services.support_flag_service import user_can_read_support_flag

ADMIN_MONEY_DETAIL_RELATED_LIMIT = 100


def unique_by_id(records: list) -> list:
    seen_ids = set()
    unique_records = []
    for record in records:
        if record.id in seen_ids:
            continue
        seen_ids.add(record.id)
        unique_records.append(record)
    return unique_records


def get_user_or_404(db: Session, user_id: uuid.UUID) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )
    return user


def list_admin_money_payment_methods(
    db: Session,
    *,
    user_id: uuid.UUID,
    include_inactive: bool = False,
) -> list[UserPaymentMethod]:
    query = select(UserPaymentMethod).where(UserPaymentMethod.user_id == user_id)
    if not include_inactive:
        query = query.where(UserPaymentMethod.method_status == "active")

    return list(
        db.scalars(
            query.order_by(
                UserPaymentMethod.created_at.asc(),
                UserPaymentMethod.id.asc(),
            )
    ).all()
    )


def list_user_payments(
    db: Session,
    *,
    user_id: uuid.UUID,
    limit: int,
) -> list[Payment]:
    return list(
        db.scalars(
            select(Payment)
            .where(Payment.payer_user_id == user_id)
            .order_by(Payment.created_at.desc(), Payment.id.desc())
            .limit(limit)
        ).all()
    )


def list_user_refunds(
    db: Session,
    *,
    payments: list[Payment],
    limit: int,
) -> list[Refund]:
    payment_ids = [payment.id for payment in payments]
    if not payment_ids:
        return []

    return list(
        db.scalars(
            select(Refund)
            .where(Refund.payment_id.in_(payment_ids))
            .order_by(Refund.created_at.desc(), Refund.id.desc())
            .limit(limit)
        ).all()
    )


def list_user_credit_usages(
    db: Session,
    *,
    user_id: uuid.UUID,
    limit: int,
) -> list[GameCreditUsage]:
    return list(
        db.scalars(
            select(GameCreditUsage)
            .where(GameCreditUsage.user_id == user_id)
            .order_by(GameCreditUsage.created_at.desc(), GameCreditUsage.id.desc())
            .limit(limit)
        ).all()
    )


def list_user_credit_grants(
    db: Session,
    *,
    user_id: uuid.UUID,
    limit: int,
) -> list[GameCredit]:
    return list(
        db.scalars(
            select(GameCredit)
            .where(GameCredit.user_id == user_id)
            .order_by(GameCredit.created_at.desc(), GameCredit.id.desc())
            .limit(limit)
        ).all()
    )


def list_user_support_flags(
    db: Session,
    *,
    viewer_user: User,
    user_id: uuid.UUID,
    payments: list[Payment],
    refunds: list[Refund],
    credit_grants: list[GameCredit],
    credit_usages: list[GameCreditUsage],
    limit: int,
) -> list[SupportFlag]:
    filters = [SupportFlag.target_user_id == user_id]

    payment_ids = [payment.id for payment in payments]
    if payment_ids:
        filters.append(SupportFlag.target_payment_id.in_(payment_ids))

    booking_ids = [
        payment.booking_id for payment in payments if payment.booking_id is not None
    ]
    booking_ids.extend(
        refund.booking_id for refund in refunds if refund.booking_id is not None
    )
    booking_ids.extend(
        usage.booking_id for usage in credit_usages if usage.booking_id is not None
    )
    if booking_ids:
        filters.append(SupportFlag.target_booking_id.in_(booking_ids))

    refund_ids = [refund.id for refund in refunds]
    if refund_ids:
        filters.append(SupportFlag.target_refund_id.in_(refund_ids))

    credit_ids = [credit.id for credit in credit_grants]
    if credit_ids:
        filters.append(SupportFlag.target_game_credit_id.in_(credit_ids))

    support_flags = db.scalars(
        select(SupportFlag)
        .where(
            SupportFlag.flag_type.in_(MONEY_SUPPORT_FLAG_TYPES),
            or_(*filters),
        )
        .order_by(SupportFlag.created_at.desc(), SupportFlag.id.desc())
        .limit(limit)
    ).all()

    return [
        support_flag
        for support_flag in unique_by_id(list(support_flags))
        if user_can_read_support_flag(viewer_user, support_flag)
    ]


def list_user_audit_actions(
    db: Session,
    *,
    viewer_user: User,
    user_id: uuid.UUID,
    payments: list[Payment],
    refunds: list[Refund],
    credit_grants: list[GameCredit],
    support_flags: list[SupportFlag],
    limit: int,
) -> list[AdminAction]:
    filters = [AdminAction.target_user_id == user_id]

    payment_ids = [payment.id for payment in payments]
    if payment_ids:
        filters.append(AdminAction.target_payment_id.in_(payment_ids))

    booking_ids = [
        payment.booking_id for payment in payments if payment.booking_id is not None
    ]
    booking_ids.extend(
        refund.booking_id for refund in refunds if refund.booking_id is not None
    )
    if booking_ids:
        filters.append(AdminAction.target_booking_id.in_(booking_ids))

    refund_ids = [refund.id for refund in refunds]
    if refund_ids:
        filters.append(AdminAction.target_refund_id.in_(refund_ids))

    credit_ids = [credit.id for credit in credit_grants]
    if credit_ids:
        filters.append(AdminAction.target_game_credit_id.in_(credit_ids))

    support_flag_ids = [support_flag.id for support_flag in support_flags]
    if support_flag_ids:
        filters.append(AdminAction.target_support_flag_id.in_(support_flag_ids))

    audit_actions = db.scalars(
        select(AdminAction)
        .where(or_(*filters))
        .order_by(AdminAction.created_at.desc(), AdminAction.id.desc())
        .limit(limit)
    ).all()

    return [
        audit_action
        for audit_action in unique_by_id(list(audit_actions))
        if user_can_read_admin_action(viewer_user, audit_action)
    ]


def get_admin_money_user_detail(
    db: Session,
    *,
    user_id: uuid.UUID,
    viewer_user: User,
    include_inactive_payment_methods: bool = False,
    limit: int = ADMIN_MONEY_DETAIL_RELATED_LIMIT,
) -> AdminMoneyUserDetailRead:
    user = get_user_or_404(db, user_id)
    payments = list_user_payments(db, user_id=user.id, limit=limit)
    refunds = list_user_refunds(db, payments=payments, limit=limit)
    credit_usages = list_user_credit_usages(
        db,
        user_id=user.id,
        limit=limit,
    )
    credit_grants = list_user_credit_grants(
        db,
        user_id=user.id,
        limit=limit,
    )
    payment_methods = list_admin_money_payment_methods(
        db,
        user_id=user.id,
        include_inactive=include_inactive_payment_methods,
    )
    support_flags = list_user_support_flags(
        db,
        viewer_user=viewer_user,
        user_id=user.id,
        payments=payments,
        refunds=refunds,
        credit_grants=credit_grants,
        credit_usages=credit_usages,
        limit=limit,
    )
    audit_actions = list_user_audit_actions(
        db,
        viewer_user=viewer_user,
        user_id=user.id,
        payments=payments,
        refunds=refunds,
        credit_grants=credit_grants,
        support_flags=support_flags,
        limit=limit,
    )

    return AdminMoneyUserDetailRead(
        user=user,
        payments=payments,
        refunds=refunds,
        credit_grants=credit_grants,
        credit_usages=credit_usages,
        payment_methods=payment_methods,
        support_flags=support_flags,
        audit_actions=audit_actions,
    )
