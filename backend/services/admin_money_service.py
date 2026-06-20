"""Read-only admin money support views."""

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
    UserPaymentMethod,
)
from backend.schemas.admin_money_schema import (
    AdminMoneyCreditDetailRead,
    AdminMoneyPaymentDetailRead,
    AdminMoneyRefundDetailRead,
    AdminMoneySupportFlagDetailRead,
    AdminMoneyUserDetailRead,
)
from backend.services.admin_action_service import user_can_read_admin_action
from backend.services.admin_permission_service import (
    PERMISSION_AUDIT_READ,
    user_has_admin_permission,
)
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
ADMIN_MONEY_CREDIT_STATUSES = ("active", "used", "expired", "reversed", "all")
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
ADMIN_MONEY_REFUND_STATUSES = (
    "pending",
    "approved",
    "processing",
    "succeeded",
    "failed",
    "cancelled",
    "all",
)


def unique_by_id(records: list) -> list:
    seen_ids = set()
    unique_records = []
    for record in records:
        if record.id in seen_ids:
            continue
        seen_ids.add(record.id)
        unique_records.append(record)
    return unique_records


def get_payment_or_404(db: Session, payment_id: uuid.UUID) -> Payment:
    payment = db.get(Payment, payment_id)
    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found.",
        )
    return payment


def get_refund_or_404(db: Session, refund_id: uuid.UUID) -> Refund:
    refund = db.get(Refund, refund_id)
    if refund is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refund not found.",
        )
    return refund


def get_credit_or_404(db: Session, game_credit_id: uuid.UUID) -> GameCredit:
    credit = db.get(GameCredit, game_credit_id)
    if credit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credit not found.",
        )
    return credit


def get_user_or_404(db: Session, user_id: uuid.UUID) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )
    return user


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


def validate_admin_money_refund_status(refund_status: str) -> None:
    if refund_status not in ADMIN_MONEY_REFUND_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="refund_status is not supported.",
        )


def list_admin_money_refunds(
    db: Session,
    *,
    user_id: uuid.UUID | None = None,
    refund_status: str = "all",
    payment_id: uuid.UUID | None = None,
    booking_id: uuid.UUID | None = None,
    game_id: uuid.UUID | None = None,
    limit: int = 100,
) -> list[Refund]:
    validate_admin_money_refund_status(refund_status)

    query = select(Refund).join(Payment, Refund.payment_id == Payment.id)
    if user_id is not None:
        query = query.where(Payment.payer_user_id == user_id)
    if refund_status != "all":
        query = query.where(Refund.refund_status == refund_status)
    if payment_id is not None:
        query = query.where(Refund.payment_id == payment_id)
    if booking_id is not None:
        query = query.where(
            or_(Refund.booking_id == booking_id, Payment.booking_id == booking_id)
        )
    if game_id is not None:
        query = query.outerjoin(
            Booking,
            or_(Refund.booking_id == Booking.id, Payment.booking_id == Booking.id),
        ).where(or_(Payment.game_id == game_id, Booking.game_id == game_id))

    return list(
        db.scalars(
            query.order_by(Refund.created_at.desc(), Refund.id.desc()).limit(limit)
        ).all()
    )


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
    if not user_has_admin_permission(viewer_user, PERMISSION_AUDIT_READ):
        return []

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


def get_refund_payment(db: Session, refund: Refund) -> Payment | None:
    return db.get(Payment, refund.payment_id)


def get_refund_booking(
    db: Session,
    *,
    refund: Refund,
    payment: Payment | None,
) -> Booking | None:
    booking_id = refund.booking_id or (
        payment.booking_id if payment is not None else None
    )
    if booking_id is None:
        return None
    return db.get(Booking, booking_id)


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
    if not user_has_admin_permission(viewer_user, PERMISSION_AUDIT_READ):
        return []

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


def list_refund_support_flags(
    db: Session,
    *,
    viewer_user: User,
    refund: Refund,
    payment: Payment | None,
    booking_id: uuid.UUID | None,
    credit_grants: list[GameCredit],
) -> list[SupportFlag]:
    filters = [SupportFlag.target_refund_id == refund.id]

    if payment is not None:
        filters.append(SupportFlag.target_payment_id == payment.id)

    if booking_id is not None:
        filters.append(SupportFlag.target_booking_id == booking_id)

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


def list_refund_audit_actions(
    db: Session,
    *,
    viewer_user: User,
    refund: Refund,
    payment: Payment | None,
    booking_id: uuid.UUID | None,
    credit_grants: list[GameCredit],
    support_flags: list[SupportFlag],
) -> list[AdminAction]:
    if not user_has_admin_permission(viewer_user, PERMISSION_AUDIT_READ):
        return []

    filters = [AdminAction.target_refund_id == refund.id]

    if payment is not None:
        filters.append(AdminAction.target_payment_id == payment.id)

    if booking_id is not None:
        filters.append(AdminAction.target_booking_id == booking_id)

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


def get_admin_money_refund_detail(
    db: Session,
    *,
    refund_id: uuid.UUID,
    viewer_user: User,
) -> AdminMoneyRefundDetailRead:
    refund = get_refund_or_404(db, refund_id)
    payment = get_refund_payment(db, refund)
    booking = get_refund_booking(db, refund=refund, payment=payment)
    game = (
        get_payment_game(db, payment=payment, booking=booking)
        if payment is not None
        else None
    )
    payment_id = payment.id if payment is not None else refund.payment_id
    booking_id = booking.id if booking is not None else refund.booking_id
    credit_usages = list_payment_credit_usages(
        db,
        payment_id=payment_id,
        booking_id=booking_id,
    )
    credit_grants = list_payment_credit_grants(
        db,
        payment_id=payment_id,
        booking_id=booking_id,
        credit_usages=credit_usages,
    )
    support_flags = list_refund_support_flags(
        db,
        viewer_user=viewer_user,
        refund=refund,
        payment=payment,
        booking_id=booking_id,
        credit_grants=credit_grants,
    )
    audit_actions = list_refund_audit_actions(
        db,
        viewer_user=viewer_user,
        refund=refund,
        payment=payment,
        booking_id=booking_id,
        credit_grants=credit_grants,
        support_flags=support_flags,
    )

    return AdminMoneyRefundDetailRead(
        refund=refund,
        payment=payment,
        booking=booking,
        game=game,
        credit_grants=credit_grants,
        credit_usages=credit_usages,
        support_flags=support_flags,
        audit_actions=audit_actions,
    )


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
    if not user_has_admin_permission(viewer_user, PERMISSION_AUDIT_READ):
        return []

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
