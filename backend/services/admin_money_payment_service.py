"""Read-only admin payment search and detail context."""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from backend.models import (
    AdminAction,
    Booking,
    CommunityPublishAttempt,
    Game,
    GameCredit,
    GameCreditUsage,
    HostPublishFee,
    MoneyIssue,
    Payment,
    Refund,
    User,
)
from backend.schemas.admin_money_schema import (
    AdminMoneyCommunityPublishAttemptContextRead,
    AdminMoneyHostPublishFeeContextRead,
    AdminMoneyPaymentDetailItemRead,
    AdminMoneyPaymentDetailRead,
    AdminMoneyPaymentListRead,
    AdminMoneyPaymentListResponseRead,
    AdminMoneyPaymentUserContextRead,
    AdminMoneyRefundDetailItemRead,
)
from backend.services.admin_action_service import user_can_read_admin_action
from backend.services.admin_money_cursor import (
    apply_desc_cursor,
    next_cursor_for_rows,
    page_has_more,
)
from backend.services.admin_money_display import admin_money_display, compact_id
from backend.services.admin_money_issue_service import (
    list_related_money_issues,
    sort_money_issues_open_first,
)
from backend.services.payment_rules import VALID_PAYMENT_STATUSES, VALID_PAYMENT_TYPES

ADMIN_MONEY_DETAIL_RELATED_LIMIT = 100
ADMIN_MONEY_PAYMENT_STATUSES = VALID_PAYMENT_STATUSES | {"all"}


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


def validate_admin_money_payment_type(payment_type: str | None) -> None:
    if payment_type is not None and payment_type not in VALID_PAYMENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="payment_type is not supported.",
        )


def maybe_uuid(value: str | None) -> uuid.UUID | None:
    if value is None:
        return None
    try:
        return uuid.UUID(value.strip())
    except (TypeError, ValueError):
        return None


def list_admin_money_payments(
    db: Session,
    *,
    user_id: uuid.UUID | None = None,
    payment_status: str = "all",
    payment_type: str | None = None,
    query_text: str | None = None,
    limit: int = 50,
    cursor: str | None = None,
) -> AdminMoneyPaymentListResponseRead:
    validate_admin_money_payment_status(payment_status)
    validate_admin_money_payment_type(payment_type)

    query = (
        select(Payment)
        .outerjoin(User, Payment.payer_user_id == User.id)
        .outerjoin(Booking, Payment.booking_id == Booking.id)
    )
    if user_id is not None:
        query = query.where(Payment.payer_user_id == user_id)
    if payment_status != "all":
        query = query.where(Payment.payment_status == payment_status)
    if payment_type is not None:
        query = query.where(Payment.payment_type == payment_type)

    normalized_query = " ".join((query_text or "").strip().split())
    if normalized_query:
        query_uuid = maybe_uuid(normalized_query)
        query_filters = []
        if query_uuid is not None:
            host_fee_match = (
                select(HostPublishFee.id)
                .where(
                    HostPublishFee.id == query_uuid,
                    HostPublishFee.payment_id == Payment.id,
                )
                .correlate(Payment)
            )
            publish_attempt_match = (
                select(CommunityPublishAttempt.id)
                .where(
                    CommunityPublishAttempt.id == query_uuid,
                    CommunityPublishAttempt.payment_id == Payment.id,
                )
                .correlate(Payment)
            )
            query_filters.extend(
                [
                    Payment.id == query_uuid,
                    Payment.payer_user_id == query_uuid,
                    Payment.booking_id == query_uuid,
                    Payment.game_id == query_uuid,
                    Booking.game_id == query_uuid,
                    host_fee_match.exists(),
                    publish_attempt_match.exists(),
                ]
            )
        elif normalized_query.startswith("pi_"):
            query_filters.append(Payment.provider_payment_intent_id == normalized_query)
        elif normalized_query.startswith("ch_"):
            query_filters.append(Payment.provider_charge_id == normalized_query)
        else:
            prefix_query = f"{normalized_query}%"
            query_filters.extend(
                [
                    User.email.ilike(prefix_query),
                    User.first_name.ilike(prefix_query),
                    User.last_name.ilike(prefix_query),
                ]
            )
            name_parts = normalized_query.split()
            if len(name_parts) >= 2:
                query_filters.append(
                    and_(
                        User.first_name.ilike(f"{name_parts[0]}%"),
                        User.last_name.ilike(f"{name_parts[-1]}%"),
                    )
                )
        query = query.where(or_(*query_filters))
    query = apply_desc_cursor(query, Payment, Payment.created_at, cursor)

    payments = list(
        db.scalars(
            query.order_by(Payment.created_at.desc(), Payment.id.desc()).limit(limit + 1)
        ).all()
    )
    return AdminMoneyPaymentListResponseRead(
        items=build_payment_summaries(db, payments[:limit]),
        has_more=page_has_more(payments, limit=limit),
        next_cursor=next_cursor_for_rows(
            payments,
            limit=limit,
            sort_attr="created_at",
        ),
    )


def sum_payment_refunded_cents(db: Session, payment_id: uuid.UUID) -> int:
    from sqlalchemy import func

    total = db.scalar(
        select(func.coalesce(func.sum(Refund.amount_cents), 0)).where(
            Refund.payment_id == payment_id,
            Refund.refund_status == "succeeded",
        )
    )
    return int(total or 0)


def sum_payment_credit_usage_cents(
    db: Session,
    *,
    payment_id: uuid.UUID,
    booking_id: uuid.UUID | None,
    payment_type: str,
    usage_status: str,
) -> int:
    from sqlalchemy import func

    filters = [GameCreditUsage.payment_id == payment_id]
    if booking_id is not None and payment_type == "booking":
        filters.append(
            and_(
                GameCreditUsage.payment_id.is_(None),
                GameCreditUsage.booking_id == booking_id,
            )
        )
    total = db.scalar(
        select(func.coalesce(func.sum(GameCreditUsage.amount_cents), 0)).where(
            or_(*filters),
            GameCreditUsage.usage_type == "redeem",
            GameCreditUsage.usage_status == usage_status,
        )
    )
    return int(total or 0)


def count_open_money_issues_for_payment(db: Session, payment_id: uuid.UUID) -> int:
    refund_ids = select(Refund.id).where(Refund.payment_id == payment_id)
    total = db.scalar(
        select(func.count(func.distinct(MoneyIssue.id))).where(
            MoneyIssue.status == "open",
            or_(
                MoneyIssue.target_payment_id == payment_id,
                MoneyIssue.target_refund_id.in_(refund_ids),
            ),
        )
    )
    return int(total or 0)


def load_by_id(db: Session, model, ids: set[uuid.UUID]) -> dict[uuid.UUID, object]:
    if not ids:
        return {}
    return {
        row.id: row
        for row in db.scalars(select(model).where(model.id.in_(ids))).all()
    }


def payment_refund_totals(
    db: Session,
    payment_ids: set[uuid.UUID],
) -> dict[uuid.UUID, int]:
    if not payment_ids:
        return {}
    return {
        payment_id: int(total or 0)
        for payment_id, total in db.execute(
            select(Refund.payment_id, func.coalesce(func.sum(Refund.amount_cents), 0))
            .where(
                Refund.payment_id.in_(payment_ids),
                Refund.refund_status == "succeeded",
            )
            .group_by(Refund.payment_id)
        ).all()
    }


def payment_credit_usage_totals(
    db: Session,
    *,
    payment_ids: set[uuid.UUID],
    booking_ids: set[uuid.UUID],
) -> tuple[dict[tuple[uuid.UUID, str], int], dict[tuple[uuid.UUID, str], int]]:
    direct_totals: dict[tuple[uuid.UUID, str], int] = {}
    booking_totals: dict[tuple[uuid.UUID, str], int] = {}
    if payment_ids:
        direct_totals = {
            (payment_id, usage_status): int(total or 0)
            for payment_id, usage_status, total in db.execute(
                select(
                    GameCreditUsage.payment_id,
                    GameCreditUsage.usage_status,
                    func.coalesce(func.sum(GameCreditUsage.amount_cents), 0),
                )
                .where(
                    GameCreditUsage.payment_id.in_(payment_ids),
                    GameCreditUsage.usage_type == "redeem",
                    GameCreditUsage.usage_status.in_(("reserved", "redeemed")),
                )
                .group_by(GameCreditUsage.payment_id, GameCreditUsage.usage_status)
            ).all()
            if payment_id is not None
        }
    if booking_ids:
        booking_totals = {
            (booking_id, usage_status): int(total or 0)
            for booking_id, usage_status, total in db.execute(
                select(
                    GameCreditUsage.booking_id,
                    GameCreditUsage.usage_status,
                    func.coalesce(func.sum(GameCreditUsage.amount_cents), 0),
                )
                .where(
                    GameCreditUsage.payment_id.is_(None),
                    GameCreditUsage.booking_id.in_(booking_ids),
                    GameCreditUsage.usage_type == "redeem",
                    GameCreditUsage.usage_status.in_(("reserved", "redeemed")),
                )
                .group_by(GameCreditUsage.booking_id, GameCreditUsage.usage_status)
            ).all()
            if booking_id is not None
        }
    return direct_totals, booking_totals


def payment_open_issue_counts(
    db: Session,
    payment_ids: set[uuid.UUID],
) -> dict[uuid.UUID, int]:
    counts = {payment_id: 0 for payment_id in payment_ids}
    if not payment_ids:
        return counts

    direct_rows = db.execute(
        select(
            MoneyIssue.target_payment_id,
            func.count(func.distinct(MoneyIssue.id)),
        )
        .where(
            MoneyIssue.target_payment_id.in_(payment_ids),
            MoneyIssue.status == "open",
        )
        .group_by(MoneyIssue.target_payment_id)
    ).all()
    for payment_id, total in direct_rows:
        if payment_id is not None:
            counts[payment_id] = counts.get(payment_id, 0) + int(total or 0)

    refund_rows = db.execute(
        select(
            Refund.payment_id,
            func.count(func.distinct(MoneyIssue.id)),
        )
        .join(Refund, MoneyIssue.target_refund_id == Refund.id)
        .where(
            Refund.payment_id.in_(payment_ids),
            MoneyIssue.status == "open",
        )
        .group_by(Refund.payment_id)
    ).all()
    for payment_id, total in refund_rows:
        counts[payment_id] = counts.get(payment_id, 0) + int(total or 0)

    return counts


def build_payment_summary_from_context(
    payment: Payment,
    *,
    payer: User | None,
    booking: Booking | None,
    game: Game | None,
    refunded_cents: int,
    reserved_credit_cents: int,
    redeemed_credit_cents: int,
    open_money_issue_count: int,
    detail: bool = False,
) -> AdminMoneyPaymentListRead | AdminMoneyPaymentDetailItemRead:
    context_label = None
    if booking is not None:
        context_label = f"Booking {compact_id(booking.id)}"
    elif payment.payment_type == "community_publish_fee":
        context_label = "Community publish fee"
    elif payment.payment_type == "admin_charge":
        context_label = "Admin charge"

    data = {
        "id": payment.id,
        "payer_user_id": payment.payer_user_id,
        "booking_id": payment.booking_id,
        "game_id": payment.game_id,
        "payment_type": payment.payment_type,
        "provider": payment.provider,
        "provider_payment_intent_id": payment.provider_payment_intent_id,
        "provider_charge_id": payment.provider_charge_id,
        "amount_cents": payment.amount_cents,
        "currency": payment.currency,
        "payment_status": payment.payment_status,
        "paid_at": payment.paid_at,
        "failure_code": payment.failure_code,
        "failure_message": payment.failure_message,
        "is_fully_refunded": refunded_cents >= payment.amount_cents
        if payment.amount_cents > 0
        else False,
        "reserved_credit_cents": reserved_credit_cents,
        "redeemed_credit_cents": redeemed_credit_cents,
        "open_money_issue_count": open_money_issue_count,
        "display": admin_money_display(
            user=payer,
            game=game,
            context_label=context_label,
            payment_id=payment.id,
        ),
        "created_at": payment.created_at,
        "updated_at": payment.updated_at,
    }
    if detail:
        data["idempotency_key"] = payment.idempotency_key
        return AdminMoneyPaymentDetailItemRead(**data)
    return AdminMoneyPaymentListRead(**data)


def build_payment_summaries(
    db: Session,
    payments: list[Payment],
    *,
    detail: bool = False,
) -> list[AdminMoneyPaymentListRead | AdminMoneyPaymentDetailItemRead]:
    payment_ids = {payment.id for payment in payments}
    payer_ids = {payment.payer_user_id for payment in payments}
    booking_ids = {payment.booking_id for payment in payments if payment.booking_id is not None}
    users = load_by_id(db, User, payer_ids)
    bookings = load_by_id(db, Booking, booking_ids)
    game_ids = {payment.game_id for payment in payments if payment.game_id is not None}
    game_ids.update(
        booking.game_id for booking in bookings.values() if booking is not None
    )
    games = load_by_id(db, Game, game_ids)
    refund_totals = payment_refund_totals(db, payment_ids)
    direct_credit_totals, booking_credit_totals = payment_credit_usage_totals(
        db,
        payment_ids=payment_ids,
        booking_ids=booking_ids,
    )
    issue_counts = payment_open_issue_counts(db, payment_ids)

    summaries = []
    for payment in payments:
        booking = bookings.get(payment.booking_id) if payment.booking_id is not None else None
        game_id = payment.game_id or (booking.game_id if booking is not None else None)
        reserved_credit_cents = direct_credit_totals.get((payment.id, "reserved"), 0)
        redeemed_credit_cents = direct_credit_totals.get((payment.id, "redeemed"), 0)
        if payment.payment_type == "booking" and payment.booking_id is not None:
            reserved_credit_cents += booking_credit_totals.get(
                (payment.booking_id, "reserved"),
                0,
            )
            redeemed_credit_cents += booking_credit_totals.get(
                (payment.booking_id, "redeemed"),
                0,
            )
        summaries.append(
            build_payment_summary_from_context(
                payment,
                payer=users.get(payment.payer_user_id),
                booking=booking,
                game=games.get(game_id) if game_id is not None else None,
                refunded_cents=refund_totals.get(payment.id, 0),
                reserved_credit_cents=reserved_credit_cents,
                redeemed_credit_cents=redeemed_credit_cents,
                open_money_issue_count=issue_counts.get(payment.id, 0),
                detail=detail,
            )
        )
    return summaries


def build_payment_summary(
    db: Session,
    payment: Payment,
    *,
    detail: bool = False,
) -> AdminMoneyPaymentListRead | AdminMoneyPaymentDetailItemRead:
    refunded_cents = sum_payment_refunded_cents(db, payment.id)
    payer = db.get(User, payment.payer_user_id)
    booking = get_payment_booking(db, payment)
    game = get_payment_game(db, payment=payment, booking=booking)
    return build_payment_summary_from_context(
        payment,
        payer=payer,
        booking=booking,
        game=game,
        refunded_cents=refunded_cents,
        reserved_credit_cents=sum_payment_credit_usage_cents(
            db,
            payment_id=payment.id,
            booking_id=payment.booking_id,
            payment_type=payment.payment_type,
            usage_status="reserved",
        ),
        redeemed_credit_cents=sum_payment_credit_usage_cents(
            db,
            payment_id=payment.id,
            booking_id=payment.booking_id,
            payment_type=payment.payment_type,
            usage_status="redeemed",
        ),
        open_money_issue_count=count_open_money_issues_for_payment(db, payment.id),
        detail=detail,
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


def get_payment_host_publish_fee(
    db: Session,
    payment_id: uuid.UUID,
) -> HostPublishFee | None:
    return db.scalars(
        select(HostPublishFee).where(HostPublishFee.payment_id == payment_id)
    ).first()


def get_payment_community_publish_attempt(
    db: Session,
    payment_id: uuid.UUID,
) -> CommunityPublishAttempt | None:
    return db.scalars(
        select(CommunityPublishAttempt).where(
            CommunityPublishAttempt.payment_id == payment_id
        )
    ).first()


def get_payment_publish_host(
    db: Session,
    *,
    host_publish_fee: HostPublishFee | None,
    community_publish_attempt: CommunityPublishAttempt | None,
) -> User | None:
    host_user_id = (
        host_publish_fee.host_user_id
        if host_publish_fee is not None
        else (
            community_publish_attempt.host_user_id
            if community_publish_attempt is not None
            else None
        )
    )
    if host_user_id is None:
        return None
    return db.get(User, host_user_id)


def list_payment_refunds(db: Session, payment_id: uuid.UUID) -> list[Refund]:
    return list(
        db.scalars(
            select(Refund)
            .where(Refund.payment_id == payment_id)
            .order_by(Refund.created_at.desc(), Refund.id.desc())
            .limit(ADMIN_MONEY_DETAIL_RELATED_LIMIT)
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
        filters.append(
            and_(
                GameCreditUsage.payment_id.is_(None),
                GameCreditUsage.booking_id == booking_id,
            )
        )

    return list(
        db.scalars(
            select(GameCreditUsage)
            .where(or_(*filters))
            .order_by(GameCreditUsage.created_at.desc(), GameCreditUsage.id.desc())
            .limit(ADMIN_MONEY_DETAIL_RELATED_LIMIT)
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
            .limit(ADMIN_MONEY_DETAIL_RELATED_LIMIT)
        ).all()
    )


def list_payment_money_issues(
    db: Session,
    *,
    payment: Payment,
    booking_id: uuid.UUID | None,
    refunds: list[Refund],
    credit_grants: list[GameCredit],
) -> list:
    refund_ids = [refund.id for refund in refunds]
    credit_ids = [credit.id for credit in credit_grants]
    issues = list_related_money_issues(
        db,
        payment_id=payment.id,
        limit=ADMIN_MONEY_DETAIL_RELATED_LIMIT,
    )
    if refund_ids:
        for refund_id in refund_ids:
            issues.extend(
                list_related_money_issues(
                    db,
                    refund_id=refund_id,
                    limit=ADMIN_MONEY_DETAIL_RELATED_LIMIT,
                )
            )
    if credit_ids:
        for credit_id in credit_ids:
            issues.extend(
                list_related_money_issues(
                    db,
                    game_credit_id=credit_id,
                    limit=ADMIN_MONEY_DETAIL_RELATED_LIMIT,
                )
            )
    seen = set()
    unique_issues = []
    for issue in issues:
        if issue.id in seen:
            continue
        seen.add(issue.id)
        unique_issues.append(issue)
    return sort_money_issues_open_first(unique_issues)[
        :ADMIN_MONEY_DETAIL_RELATED_LIMIT
    ]


def list_payment_audit_actions(
    db: Session,
    *,
    viewer_user: User,
    payment: Payment,
    booking_id: uuid.UUID | None,
    refunds: list[Refund],
    credit_grants: list[GameCredit],
    money_issues: list,
) -> list[AdminAction]:
    audit_actions = db.scalars(
        select(AdminAction)
        .where(AdminAction.target_payment_id == payment.id)
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
    from backend.services.admin_money_credit_service import build_credit_summaries
    from backend.services.admin_money_refund_service import build_refund_summaries

    payment = get_payment_or_404(db, payment_id)
    payer = db.get(User, payment.payer_user_id)
    booking = get_payment_booking(db, payment)
    game = get_payment_game(db, payment=payment, booking=booking)
    host_publish_fee = get_payment_host_publish_fee(db, payment.id)
    community_publish_attempt = get_payment_community_publish_attempt(db, payment.id)
    publish_host = get_payment_publish_host(
        db,
        host_publish_fee=host_publish_fee,
        community_publish_attempt=community_publish_attempt,
    )
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
    money_issues = list_payment_money_issues(
        db,
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
        money_issues=money_issues,
    )
    refund_items = [
        AdminMoneyRefundDetailItemRead(**refund.model_dump())
        for refund in build_refund_summaries(db, refunds)
    ]

    return AdminMoneyPaymentDetailRead(
        payment=build_payment_summary(db, payment, detail=True),
        payer=(
            AdminMoneyPaymentUserContextRead.model_validate(payer)
            if payer is not None
            else None
        ),
        booking=booking,
        game=game,
        host_publish_fee=(
            AdminMoneyHostPublishFeeContextRead.model_validate(host_publish_fee)
            if host_publish_fee is not None
            else None
        ),
        community_publish_attempt=(
            AdminMoneyCommunityPublishAttemptContextRead.model_validate(
                community_publish_attempt
            )
            if community_publish_attempt is not None
            else None
        ),
        publish_host=(
            AdminMoneyPaymentUserContextRead.model_validate(publish_host)
            if publish_host is not None
            else None
        ),
        refunds=refund_items,
        credit_grants=build_credit_summaries(db, credit_grants),
        credit_usages=credit_usages,
        linked_money_issues=money_issues,
        admin_actions=audit_actions,
    )
