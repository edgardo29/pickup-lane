"""Read-only admin payment search and detail context."""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.models import (
    AdminAction,
    Booking,
    Game,
    GameCredit,
    GameCreditUsage,
    Payment,
    Refund,
    SupportFlag,
    User,
)
from backend.schemas.admin_money_schema import AdminMoneyPaymentDetailRead
from backend.services.admin_action_service import user_can_read_admin_action
from backend.services.admin_money_support_flag_read_service import (
    MONEY_SUPPORT_FLAG_TYPES,
)
from backend.services.admin_permission_service import (
    PERMISSION_AUDIT_READ,
    user_has_admin_permission,
)
from backend.services.support_flag_service import user_can_read_support_flag

ADMIN_MONEY_DETAIL_RELATED_LIMIT = 100
ADMIN_MONEY_PAYMENT_STATUSES = (
    "requires_payment_method",
    "processing",
    "requires_action",
    "succeeded",
    "failed",
    "canceled",
    "refunded",
    "partially_refunded",
    "disputed",
    "all",
)


def get_payment_or_404(db: Session, payment_id: uuid.UUID) -> Payment:
    payment = db.get(Payment, payment_id)
    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found.",
        )
    return payment


def validate_admin_money_payment_status(payment_status: str) -> None:
    if payment_status not in ADMIN_MONEY_PAYMENT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="payment_status is not supported.",
        )


def list_admin_money_payments(
    db: Session,
    *,
    user_id: uuid.UUID | None = None,
    payment_status: str = "all",
    booking_id: uuid.UUID | None = None,
    game_id: uuid.UUID | None = None,
    limit: int = 100,
) -> list[Payment]:
    validate_admin_money_payment_status(payment_status)

    query = select(Payment)
    if user_id is not None:
        query = query.where(Payment.payer_user_id == user_id)
    if payment_status != "all":
        query = query.where(Payment.payment_status == payment_status)
    if booking_id is not None:
        query = query.where(Payment.booking_id == booking_id)
    if game_id is not None:
        query = query.outerjoin(Booking, Payment.booking_id == Booking.id).where(
            or_(Payment.game_id == game_id, Booking.game_id == game_id)
        )

    return list(
        db.scalars(
            query.order_by(Payment.created_at.desc(), Payment.id.desc()).limit(limit)
        ).all()
    )


def get_payment_booking(db: Session, payment: Payment) -> Booking | None:
    if payment.booking_id is None:
        return None
    return db.get(Booking, payment.booking_id)


def get_payment_game(
    db: Session,
    *,
    payment: Payment,
    booking: Booking | None,
) -> Game | None:
    game_id = payment.game_id or (booking.game_id if booking is not None else None)
    if game_id is None:
        return None
    return db.get(Game, game_id)


def list_payment_refunds(db: Session, payment_id: uuid.UUID) -> list[Refund]:
    return list(
        db.scalars(
            select(Refund)
            .where(Refund.payment_id == payment_id)
            .order_by(Refund.created_at.desc(), Refund.id.desc())
        ).all()
    )


def list_payment_credit_usages(
    db: Session,
    *,
    payment_id: uuid.UUID,
    booking_id: uuid.UUID | None,
) -> list[GameCreditUsage]:
    filters = [GameCreditUsage.payment_id == payment_id]
    if booking_id is not None:
        filters.append(GameCreditUsage.booking_id == booking_id)

    return list(
        db.scalars(
            select(GameCreditUsage)
            .where(or_(*filters))
            .order_by(GameCreditUsage.created_at.desc(), GameCreditUsage.id.desc())
        ).all()
    )


def list_payment_credit_grants(
    db: Session,
    *,
    payment_id: uuid.UUID,
    booking_id: uuid.UUID | None,
    credit_usages: list[GameCreditUsage],
) -> list[GameCredit]:
    filters = [GameCredit.source_payment_id == payment_id]
    if booking_id is not None:
        filters.append(GameCredit.source_booking_id == booking_id)

    usage_credit_ids = [usage.game_credit_id for usage in credit_usages]
    if usage_credit_ids:
        filters.append(GameCredit.id.in_(usage_credit_ids))

    return list(
        db.scalars(
            select(GameCredit)
            .where(or_(*filters))
            .order_by(GameCredit.created_at.desc(), GameCredit.id.desc())
        ).all()
    )


def list_payment_support_flags(
    db: Session,
    *,
    viewer_user: User,
    payment: Payment,
    booking_id: uuid.UUID | None,
    refunds: list[Refund],
    credit_grants: list[GameCredit],
) -> list[SupportFlag]:
    filters = [SupportFlag.target_payment_id == payment.id]

    if booking_id is not None:
        filters.append(SupportFlag.target_booking_id == booking_id)

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
        .limit(ADMIN_MONEY_DETAIL_RELATED_LIMIT)
    ).all()

    return [
        support_flag
        for support_flag in support_flags
        if user_can_read_support_flag(viewer_user, support_flag)
    ]


def list_payment_audit_actions(
    db: Session,
    *,
    viewer_user: User,
    payment: Payment,
    booking_id: uuid.UUID | None,
    refunds: list[Refund],
    credit_grants: list[GameCredit],
    support_flags: list[SupportFlag],
) -> list[AdminAction]:
    if not user_has_admin_permission(viewer_user, PERMISSION_AUDIT_READ):
        return []

    filters = [AdminAction.target_payment_id == payment.id]

    if booking_id is not None:
        filters.append(AdminAction.target_booking_id == booking_id)

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
        .limit(ADMIN_MONEY_DETAIL_RELATED_LIMIT)
    ).all()

    return [
        audit_action
        for audit_action in audit_actions
        if user_can_read_admin_action(viewer_user, audit_action)
    ]


def get_admin_money_payment_detail(
    db: Session,
    *,
    payment_id: uuid.UUID,
    viewer_user: User,
) -> AdminMoneyPaymentDetailRead:
    payment = get_payment_or_404(db, payment_id)
    booking = get_payment_booking(db, payment)
    game = get_payment_game(db, payment=payment, booking=booking)
    refunds = list_payment_refunds(db, payment.id)
    credit_usages = list_payment_credit_usages(
        db,
        payment_id=payment.id,
        booking_id=payment.booking_id,
    )
    credit_grants = list_payment_credit_grants(
        db,
        payment_id=payment.id,
        booking_id=payment.booking_id,
        credit_usages=credit_usages,
    )
    support_flags = list_payment_support_flags(
        db,
        viewer_user=viewer_user,
        payment=payment,
        booking_id=payment.booking_id,
        refunds=refunds,
        credit_grants=credit_grants,
    )
    audit_actions = list_payment_audit_actions(
        db,
        viewer_user=viewer_user,
        payment=payment,
        booking_id=payment.booking_id,
        refunds=refunds,
        credit_grants=credit_grants,
        support_flags=support_flags,
    )

    return AdminMoneyPaymentDetailRead(
        payment=payment,
        booking=booking,
        game=game,
        refunds=refunds,
        credit_grants=credit_grants,
        credit_usages=credit_usages,
        support_flags=support_flags,
        audit_actions=audit_actions,
    )
