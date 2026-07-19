"""Read-only admin game-credit search and detail context."""

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
from backend.schemas.admin_money_schema import AdminMoneyCreditDetailRead
from backend.services.admin_action_service import user_can_read_admin_action
from backend.services.admin_money_support_flag_read_service import (
    MONEY_SUPPORT_FLAG_TYPES,
)
from backend.services.support_flag_service import user_can_read_support_flag

ADMIN_MONEY_DETAIL_RELATED_LIMIT = 100
ADMIN_MONEY_CREDIT_STATUSES = ("active", "used", "expired", "reversed", "all")


def get_credit_or_404(db: Session, game_credit_id: uuid.UUID) -> GameCredit:
    credit = db.get(GameCredit, game_credit_id)
    if credit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credit not found.",
        )
    return credit


def validate_admin_money_credit_status(credit_status: str) -> None:
    if credit_status not in ADMIN_MONEY_CREDIT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="credit_status is not supported.",
        )


def list_admin_money_credits(
    db: Session,
    *,
    user_id: uuid.UUID | None = None,
    credit_status: str = "all",
    source_game_id: uuid.UUID | None = None,
    source_booking_id: uuid.UUID | None = None,
    source_payment_id: uuid.UUID | None = None,
    limit: int = 100,
) -> list[GameCredit]:
    validate_admin_money_credit_status(credit_status)

    query = select(GameCredit)
    if user_id is not None:
        query = query.where(GameCredit.user_id == user_id)
    if credit_status != "all":
        query = query.where(GameCredit.credit_status == credit_status)
    if source_game_id is not None:
        query = query.where(GameCredit.source_game_id == source_game_id)
    if source_booking_id is not None:
        query = query.where(GameCredit.source_booking_id == source_booking_id)
    if source_payment_id is not None:
        query = query.where(GameCredit.source_payment_id == source_payment_id)

    return list(
        db.scalars(
            query.order_by(GameCredit.created_at.desc(), GameCredit.id.desc()).limit(limit)
        ).all()
    )


def list_credit_usages(db: Session, credit_id: uuid.UUID) -> list[GameCreditUsage]:
    return list(
        db.scalars(
            select(GameCreditUsage)
            .where(GameCreditUsage.game_credit_id == credit_id)
            .order_by(GameCreditUsage.created_at.desc(), GameCreditUsage.id.desc())
        ).all()
    )


def get_credit_booking_id(
    *,
    credit: GameCredit,
    credit_usages: list[GameCreditUsage],
    payments: list[Payment],
) -> uuid.UUID | None:
    if credit.source_booking_id is not None:
        return credit.source_booking_id

    for usage in credit_usages:
        if usage.booking_id is not None:
            return usage.booking_id

    for payment in payments:
        if payment.booking_id is not None:
            return payment.booking_id

    return None


def get_credit_game_id(
    *,
    credit: GameCredit,
    credit_usages: list[GameCreditUsage],
    booking: Booking | None,
    payments: list[Payment],
) -> uuid.UUID | None:
    if credit.source_game_id is not None:
        return credit.source_game_id

    if booking is not None:
        return booking.game_id

    for usage in credit_usages:
        if usage.game_id is not None:
            return usage.game_id

    for payment in payments:
        if payment.game_id is not None:
            return payment.game_id

    return None


def list_credit_payments(
    db: Session,
    *,
    credit: GameCredit,
    credit_usages: list[GameCreditUsage],
) -> list[Payment]:
    filters = []

    if credit.source_payment_id is not None:
        filters.append(Payment.id == credit.source_payment_id)

    usage_payment_ids = [
        usage.payment_id for usage in credit_usages if usage.payment_id is not None
    ]
    if usage_payment_ids:
        filters.append(Payment.id.in_(usage_payment_ids))

    if credit.source_booking_id is not None:
        filters.append(Payment.booking_id == credit.source_booking_id)

    if not filters:
        return []

    return list(
        db.scalars(
            select(Payment)
            .where(or_(*filters))
            .order_by(Payment.created_at.desc(), Payment.id.desc())
            .limit(ADMIN_MONEY_DETAIL_RELATED_LIMIT)
        ).all()
    )


def list_credit_refunds(
    db: Session,
    *,
    payments: list[Payment],
    booking_id: uuid.UUID | None,
) -> list[Refund]:
    filters = []

    payment_ids = [payment.id for payment in payments]
    if payment_ids:
        filters.append(Refund.payment_id.in_(payment_ids))

    if booking_id is not None:
        filters.append(Refund.booking_id == booking_id)

    if not filters:
        return []

    return list(
        db.scalars(
            select(Refund)
            .where(or_(*filters))
            .order_by(Refund.created_at.desc(), Refund.id.desc())
            .limit(ADMIN_MONEY_DETAIL_RELATED_LIMIT)
        ).all()
    )


def list_credit_support_flags(
    db: Session,
    *,
    viewer_user: User,
    credit: GameCredit,
    credit_usages: list[GameCreditUsage],
    payments: list[Payment],
    refunds: list[Refund],
    booking_id: uuid.UUID | None,
) -> list[SupportFlag]:
    filters = [SupportFlag.target_game_credit_id == credit.id]

    if booking_id is not None:
        filters.append(SupportFlag.target_booking_id == booking_id)

    payment_ids = [payment.id for payment in payments]
    if credit.source_payment_id is not None:
        payment_ids.append(credit.source_payment_id)
    payment_ids.extend(
        usage.payment_id for usage in credit_usages if usage.payment_id is not None
    )
    if payment_ids:
        filters.append(SupportFlag.target_payment_id.in_(payment_ids))

    refund_ids = [refund.id for refund in refunds]
    if refund_ids:
        filters.append(SupportFlag.target_refund_id.in_(refund_ids))

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


def list_credit_audit_actions(
    db: Session,
    *,
    viewer_user: User,
    credit: GameCredit,
    payments: list[Payment],
    refunds: list[Refund],
    support_flags: list[SupportFlag],
    booking_id: uuid.UUID | None,
) -> list[AdminAction]:
    filters = [AdminAction.target_game_credit_id == credit.id]

    if booking_id is not None:
        filters.append(AdminAction.target_booking_id == booking_id)

    payment_ids = [payment.id for payment in payments]
    if payment_ids:
        filters.append(AdminAction.target_payment_id.in_(payment_ids))

    refund_ids = [refund.id for refund in refunds]
    if refund_ids:
        filters.append(AdminAction.target_refund_id.in_(refund_ids))

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


def get_admin_money_credit_detail(
    db: Session,
    *,
    game_credit_id: uuid.UUID,
    viewer_user: User,
) -> AdminMoneyCreditDetailRead:
    credit = get_credit_or_404(db, game_credit_id)
    credit_usages = list_credit_usages(db, credit.id)
    payments = list_credit_payments(
        db,
        credit=credit,
        credit_usages=credit_usages,
    )
    booking_id = get_credit_booking_id(
        credit=credit,
        credit_usages=credit_usages,
        payments=payments,
    )
    booking = db.get(Booking, booking_id) if booking_id is not None else None
    game_id = get_credit_game_id(
        credit=credit,
        credit_usages=credit_usages,
        booking=booking,
        payments=payments,
    )
    game = db.get(Game, game_id) if game_id is not None else None
    refunds = list_credit_refunds(
        db,
        payments=payments,
        booking_id=booking_id,
    )
    support_flags = list_credit_support_flags(
        db,
        viewer_user=viewer_user,
        credit=credit,
        credit_usages=credit_usages,
        payments=payments,
        refunds=refunds,
        booking_id=booking_id,
    )
    audit_actions = list_credit_audit_actions(
        db,
        viewer_user=viewer_user,
        credit=credit,
        payments=payments,
        refunds=refunds,
        support_flags=support_flags,
        booking_id=booking_id,
    )

    return AdminMoneyCreditDetailRead(
        credit=credit,
        credit_usages=credit_usages,
        payments=payments,
        refunds=refunds,
        booking=booking,
        game=game,
        support_flags=support_flags,
        audit_actions=audit_actions,
    )
