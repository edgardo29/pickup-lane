"""Read-only admin money support flag views."""

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
from backend.schemas.admin_money_schema import AdminMoneySupportFlagDetailRead
from backend.services.admin_action_service import user_can_read_admin_action
from backend.services.support_flag_service import user_can_read_support_flag

ADMIN_MONEY_DETAIL_RELATED_LIMIT = 100
MONEY_SUPPORT_FLAG_TYPES = (
    "refund_follow_up_required",
    "stripe_refund_failed",
    "missing_stripe_charge_id",
    "credit_restore_failed",
    "credit_release_failed",
)
ADMIN_MONEY_SUPPORT_FLAG_STATUSES = ("open", "resolved", "all")


def validate_admin_money_support_flag_status(flag_status: str) -> None:
    if flag_status not in ADMIN_MONEY_SUPPORT_FLAG_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="flag_status is not supported.",
        )


def list_admin_money_support_flags(
    db: Session,
    *,
    viewer_user: User,
    flag_status: str = "open",
    limit: int = 100,
) -> list[SupportFlag]:
    validate_admin_money_support_flag_status(flag_status)

    query = select(SupportFlag).where(SupportFlag.flag_type.in_(MONEY_SUPPORT_FLAG_TYPES))
    if flag_status != "all":
        query = query.where(SupportFlag.flag_status == flag_status)

    support_flags = db.scalars(
        query.order_by(SupportFlag.created_at.desc(), SupportFlag.id.desc()).limit(limit)
    ).all()

    return [
        support_flag
        for support_flag in support_flags
        if user_can_read_support_flag(viewer_user, support_flag)
    ]


def get_admin_money_support_flag_or_404(
    db: Session,
    *,
    support_flag_id: uuid.UUID,
    viewer_user: User,
) -> SupportFlag:
    support_flag = db.get(SupportFlag, support_flag_id)
    if (
        support_flag is None
        or support_flag.flag_type not in MONEY_SUPPORT_FLAG_TYPES
        or not user_can_read_support_flag(viewer_user, support_flag)
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Support flag not found.",
        )

    return support_flag


def pick_support_flag_booking_id(
    support_flag: SupportFlag,
    *,
    refunds: list[Refund],
    payments: list[Payment],
) -> uuid.UUID | None:
    if support_flag.target_booking_id is not None:
        return support_flag.target_booking_id

    for refund in refunds:
        if refund.booking_id is not None:
            return refund.booking_id

    for payment in payments:
        if payment.booking_id is not None:
            return payment.booking_id

    return None


def list_support_flag_payments(
    db: Session,
    *,
    support_flag: SupportFlag,
    targeted_refund: Refund | None,
    booking_id: uuid.UUID | None,
    credit_grants: list[GameCredit],
    credit_usages: list[GameCreditUsage],
) -> list[Payment]:
    filters = []

    if support_flag.target_payment_id is not None:
        filters.append(Payment.id == support_flag.target_payment_id)

    if targeted_refund is not None:
        filters.append(Payment.id == targeted_refund.payment_id)

    if booking_id is not None:
        filters.append(Payment.booking_id == booking_id)

    credit_payment_ids = [
        credit.source_payment_id
        for credit in credit_grants
        if credit.source_payment_id is not None
    ]
    credit_payment_ids.extend(
        usage.payment_id
        for usage in credit_usages
        if usage.payment_id is not None
    )
    if credit_payment_ids:
        filters.append(Payment.id.in_(credit_payment_ids))

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


def list_support_flag_refunds(
    db: Session,
    *,
    support_flag: SupportFlag,
    payments: list[Payment],
    booking_id: uuid.UUID | None,
) -> list[Refund]:
    filters = []

    if support_flag.target_refund_id is not None:
        filters.append(Refund.id == support_flag.target_refund_id)

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


def list_support_flag_credit_usages(
    db: Session,
    *,
    support_flag: SupportFlag,
    payments: list[Payment],
    booking_id: uuid.UUID | None,
) -> list[GameCreditUsage]:
    filters = []

    if support_flag.target_game_credit_id is not None:
        filters.append(GameCreditUsage.game_credit_id == support_flag.target_game_credit_id)

    payment_ids = [payment.id for payment in payments]
    if payment_ids:
        filters.append(GameCreditUsage.payment_id.in_(payment_ids))

    if booking_id is not None:
        filters.append(GameCreditUsage.booking_id == booking_id)

    if not filters:
        return []

    return list(
        db.scalars(
            select(GameCreditUsage)
            .where(or_(*filters))
            .order_by(GameCreditUsage.created_at.desc(), GameCreditUsage.id.desc())
            .limit(ADMIN_MONEY_DETAIL_RELATED_LIMIT)
        ).all()
    )


def list_support_flag_credit_grants(
    db: Session,
    *,
    support_flag: SupportFlag,
    payments: list[Payment],
    booking_id: uuid.UUID | None,
    credit_usages: list[GameCreditUsage],
) -> list[GameCredit]:
    filters = []

    if support_flag.target_game_credit_id is not None:
        filters.append(GameCredit.id == support_flag.target_game_credit_id)

    payment_ids = [payment.id for payment in payments]
    if payment_ids:
        filters.append(GameCredit.source_payment_id.in_(payment_ids))

    if booking_id is not None:
        filters.append(GameCredit.source_booking_id == booking_id)

    usage_credit_ids = [usage.game_credit_id for usage in credit_usages]
    if usage_credit_ids:
        filters.append(GameCredit.id.in_(usage_credit_ids))

    if not filters:
        return []

    return list(
        db.scalars(
            select(GameCredit)
            .where(or_(*filters))
            .order_by(GameCredit.created_at.desc(), GameCredit.id.desc())
            .limit(ADMIN_MONEY_DETAIL_RELATED_LIMIT)
        ).all()
    )


def get_support_flag_game(
    db: Session,
    *,
    support_flag: SupportFlag,
    booking: Booking | None,
    payments: list[Payment],
) -> Game | None:
    game_id = support_flag.target_game_id
    if game_id is None and booking is not None:
        game_id = booking.game_id
    if game_id is None:
        for payment in payments:
            if payment.game_id is not None:
                game_id = payment.game_id
                break
    if game_id is None:
        return None
    return db.get(Game, game_id)


def get_credit_context_booking_id(
    *,
    credit_grants: list[GameCredit],
    credit_usages: list[GameCreditUsage],
) -> uuid.UUID | None:
    for credit in credit_grants:
        if credit.source_booking_id is not None:
            return credit.source_booking_id

    for usage in credit_usages:
        if usage.booking_id is not None:
            return usage.booking_id

    return None


def get_credit_context_game_id(
    *,
    credit_grants: list[GameCredit],
    credit_usages: list[GameCreditUsage],
) -> uuid.UUID | None:
    for credit in credit_grants:
        if credit.source_game_id is not None:
            return credit.source_game_id

    for usage in credit_usages:
        if usage.game_id is not None:
            return usage.game_id

    return None


def list_support_flag_audit_actions(
    db: Session,
    *,
    viewer_user: User,
    support_flag: SupportFlag,
    payments: list[Payment],
    refunds: list[Refund],
    booking_id: uuid.UUID | None,
    credit_grants: list[GameCredit],
) -> list[AdminAction]:
    filters = [AdminAction.target_support_flag_id == support_flag.id]
    action_ids = [
        action_id
        for action_id in (
            support_flag.source_admin_action_id,
            support_flag.resolution_admin_action_id,
        )
        if action_id is not None
    ]
    if action_ids:
        filters.append(AdminAction.id.in_(action_ids))

    payment_ids = [payment.id for payment in payments]
    if payment_ids:
        filters.append(AdminAction.target_payment_id.in_(payment_ids))

    refund_ids = [refund.id for refund in refunds]
    if refund_ids:
        filters.append(AdminAction.target_refund_id.in_(refund_ids))

    if booking_id is not None:
        filters.append(AdminAction.target_booking_id == booking_id)

    credit_ids = [credit.id for credit in credit_grants]
    if credit_ids:
        filters.append(AdminAction.target_game_credit_id.in_(credit_ids))

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


def get_admin_money_support_flag_detail(
    db: Session,
    *,
    support_flag_id: uuid.UUID,
    viewer_user: User,
) -> AdminMoneySupportFlagDetailRead:
    support_flag = get_admin_money_support_flag_or_404(
        db,
        support_flag_id=support_flag_id,
        viewer_user=viewer_user,
    )
    targeted_refund = (
        db.get(Refund, support_flag.target_refund_id)
        if support_flag.target_refund_id is not None
        else None
    )
    targeted_credit = (
        db.get(GameCredit, support_flag.target_game_credit_id)
        if support_flag.target_game_credit_id is not None
        else None
    )
    booking_id = pick_support_flag_booking_id(
        support_flag,
        refunds=[targeted_refund] if targeted_refund is not None else [],
        payments=[],
    )
    credit_usages = list_support_flag_credit_usages(
        db,
        support_flag=support_flag,
        payments=[],
        booking_id=booking_id,
    )
    credit_grants = list_support_flag_credit_grants(
        db,
        support_flag=support_flag,
        payments=[],
        booking_id=booking_id,
        credit_usages=credit_usages,
    )
    if targeted_credit is not None and targeted_credit.id not in {
        credit.id for credit in credit_grants
    }:
        credit_grants.insert(0, targeted_credit)

    if booking_id is None:
        booking_id = get_credit_context_booking_id(
            credit_grants=credit_grants,
            credit_usages=credit_usages,
        )

    payments = list_support_flag_payments(
        db,
        support_flag=support_flag,
        targeted_refund=targeted_refund,
        booking_id=booking_id,
        credit_grants=credit_grants,
        credit_usages=credit_usages,
    )
    booking_id = pick_support_flag_booking_id(
        support_flag,
        refunds=[targeted_refund] if targeted_refund is not None else [],
        payments=payments,
    )
    if booking_id is None:
        booking_id = get_credit_context_booking_id(
            credit_grants=credit_grants,
            credit_usages=credit_usages,
        )

    # Reconcile through the resolved booking so all payment attempts tied to the
    # same support context are included, not just the initially targeted row.
    payments = list_support_flag_payments(
        db,
        support_flag=support_flag,
        targeted_refund=targeted_refund,
        booking_id=booking_id,
        credit_grants=credit_grants,
        credit_usages=credit_usages,
    )
    refunds = list_support_flag_refunds(
        db,
        support_flag=support_flag,
        payments=payments,
        booking_id=booking_id,
    )
    booking_id = pick_support_flag_booking_id(
        support_flag,
        refunds=refunds,
        payments=payments,
    )
    if booking_id is None:
        booking_id = get_credit_context_booking_id(
            credit_grants=credit_grants,
            credit_usages=credit_usages,
        )

    booking = db.get(Booking, booking_id) if booking_id is not None else None
    game = get_support_flag_game(
        db,
        support_flag=support_flag,
        booking=booking,
        payments=payments,
    )
    credit_usages = list_support_flag_credit_usages(
        db,
        support_flag=support_flag,
        payments=payments,
        booking_id=booking_id,
    )
    credit_grants = list_support_flag_credit_grants(
        db,
        support_flag=support_flag,
        payments=payments,
        booking_id=booking_id,
        credit_usages=credit_usages,
    )
    if targeted_credit is not None and targeted_credit.id not in {
        credit.id for credit in credit_grants
    }:
        credit_grants.insert(0, targeted_credit)

    if game is None:
        credit_game_id = get_credit_context_game_id(
            credit_grants=credit_grants,
            credit_usages=credit_usages,
        )
        if credit_game_id is None and booking is not None:
            credit_game_id = booking.game_id
        if credit_game_id is not None:
            game = db.get(Game, credit_game_id)

    audit_actions = list_support_flag_audit_actions(
        db,
        viewer_user=viewer_user,
        support_flag=support_flag,
        payments=payments,
        refunds=refunds,
        booking_id=booking_id,
        credit_grants=credit_grants,
    )

    return AdminMoneySupportFlagDetailRead(
        support_flag=support_flag,
        payments=payments,
        refunds=refunds,
        booking=booking,
        game=game,
        credit_grants=credit_grants,
        credit_usages=credit_usages,
        audit_actions=audit_actions,
    )
