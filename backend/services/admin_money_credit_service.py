"""Read-only admin game-credit search and detail context."""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from backend.models import (
    AdminAction,
    Booking,
    Game,
    GameCredit,
    GameCreditUsage,
    MoneyIssue,
    Payment,
    Refund,
    User,
)
from backend.schemas.admin_money_schema import (
    AdminMoneyCreditDetailRead,
    AdminMoneyCreditGrantListRead,
    AdminMoneyCreditGrantSummaryRead,
    AdminMoneyCreditListResponseRead,
    AdminMoneyRefundDetailItemRead,
)
from backend.services.admin_money_cursor import (
    apply_desc_cursor,
    next_cursor_for_rows,
    page_has_more,
)
from backend.services.admin_money_display import admin_money_display, compact_id
from backend.services.admin_money_issue_service import list_related_money_issues
from backend.services.admin_money_payment_service import build_payment_summaries
from backend.services.admin_money_refund_service import build_refund_summaries
from backend.services.admin_action_service import user_can_read_admin_action

ADMIN_MONEY_DETAIL_RELATED_LIMIT = 100
ADMIN_MONEY_CREDIT_USAGE_DETAIL_LIMIT = 100
ADMIN_MONEY_CREDIT_STATUSES = ("active", "used", "reversed", "all")


def get_credit_or_404(db: Session, game_credit_id: uuid.UUID) -> GameCredit:
    credit = db.get(GameCredit, game_credit_id)
    if credit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credit not found.",
        )
    return credit


def maybe_uuid(value: str | None) -> uuid.UUID | None:
    if value is None:
        return None
    try:
        return uuid.UUID(value.strip())
    except (TypeError, ValueError):
        return None


def load_by_id(db: Session, model, ids: set[uuid.UUID]) -> dict[uuid.UUID, object]:
    if not ids:
        return {}
    return {
        row.id: row
        for row in db.scalars(select(model).where(model.id.in_(ids))).all()
    }


def sum_credit_reserved_cents(db: Session, credit_id: uuid.UUID) -> int:
    total = db.scalar(
        select(func.coalesce(func.sum(GameCreditUsage.amount_cents), 0)).where(
            GameCreditUsage.game_credit_id == credit_id,
            GameCreditUsage.usage_type == "redeem",
            GameCreditUsage.usage_status == "reserved",
        )
    )
    return int(total or 0)


def count_credit_open_money_issues(db: Session, credit_id: uuid.UUID) -> int:
    total = db.scalar(
        select(func.count(func.distinct(MoneyIssue.id))).where(
            MoneyIssue.target_game_credit_id == credit_id,
            MoneyIssue.status == "open",
        )
    )
    return int(total or 0)


def credit_reserved_totals(
    db: Session,
    credit_ids: set[uuid.UUID],
) -> dict[uuid.UUID, int]:
    if not credit_ids:
        return {}
    return {
        credit_id: int(total or 0)
        for credit_id, total in db.execute(
            select(
                GameCreditUsage.game_credit_id,
                func.coalesce(func.sum(GameCreditUsage.amount_cents), 0),
            )
            .where(
                GameCreditUsage.game_credit_id.in_(credit_ids),
                GameCreditUsage.usage_type == "redeem",
                GameCreditUsage.usage_status == "reserved",
            )
            .group_by(GameCreditUsage.game_credit_id)
        ).all()
    }


def credit_open_issue_counts(
    db: Session,
    credit_ids: set[uuid.UUID],
) -> dict[uuid.UUID, int]:
    if not credit_ids:
        return {}
    return {
        credit_id: int(total or 0)
        for credit_id, total in db.execute(
            select(
                MoneyIssue.target_game_credit_id,
                func.count(func.distinct(MoneyIssue.id)),
            )
            .where(
                MoneyIssue.target_game_credit_id.in_(credit_ids),
                MoneyIssue.status == "open",
            )
            .group_by(MoneyIssue.target_game_credit_id)
        ).all()
        if credit_id is not None
    }


def build_credit_summary_from_context(
    credit: GameCredit,
    *,
    user: User | None,
    booking: Booking | None,
    game: Game | None,
    reserved_cents: int,
    open_money_issue_count: int,
) -> AdminMoneyCreditGrantSummaryRead:
    context_label = None
    if booking is not None:
        context_label = f"Booking {compact_id(booking.id)}"
    elif credit.source_game_id is not None:
        context_label = f"Game {compact_id(credit.source_game_id)}"

    return AdminMoneyCreditGrantSummaryRead(
        id=credit.id,
        user_id=credit.user_id,
        amount_cents=credit.amount_cents,
        available_cents=credit.available_cents,
        reserved_cents=reserved_cents,
        currency=credit.currency,
        credit_status=credit.credit_status,
        credit_reason=credit.credit_reason,
        source_game_id=credit.source_game_id,
        source_booking_id=credit.source_booking_id,
        source_payment_id=credit.source_payment_id,
        issued_by_user_id=credit.issued_by_user_id,
        reversed_by_user_id=credit.reversed_by_user_id,
        idempotency_key=credit.idempotency_key,
        note=credit.note,
        reversed_at=credit.reversed_at,
        open_money_issue_count=open_money_issue_count,
        display=admin_money_display(
            user=user,
            game=game,
            context_label=context_label,
            credit_id=credit.id,
        ),
        created_at=credit.created_at,
        updated_at=credit.updated_at,
    )


def build_credit_summaries(
    db: Session,
    credits: list[GameCredit],
) -> list[AdminMoneyCreditGrantSummaryRead]:
    if not credits:
        return []
    credit_ids = {credit.id for credit in credits}
    user_ids = {credit.user_id for credit in credits}
    booking_ids = {
        credit.source_booking_id
        for credit in credits
        if credit.source_booking_id is not None
    }
    users = load_by_id(db, User, user_ids)
    bookings = load_by_id(db, Booking, booking_ids)
    game_ids = {
        credit.source_game_id
        for credit in credits
        if credit.source_game_id is not None
    }
    game_ids.update(
        booking.game_id for booking in bookings.values() if booking is not None
    )
    games = load_by_id(db, Game, game_ids)
    reserved_totals = credit_reserved_totals(db, credit_ids)
    issue_counts = credit_open_issue_counts(db, credit_ids)

    summaries = []
    for credit in credits:
        booking = (
            bookings.get(credit.source_booking_id)
            if credit.source_booking_id is not None
            else None
        )
        game_id = credit.source_game_id or (
            booking.game_id if booking is not None else None
        )
        summaries.append(
            build_credit_summary_from_context(
                credit,
                user=users.get(credit.user_id),
                booking=booking,
                game=games.get(game_id) if game_id is not None else None,
                reserved_cents=reserved_totals.get(credit.id, 0),
                open_money_issue_count=issue_counts.get(credit.id, 0),
            )
        )
    return summaries


def build_credit_summary(
    db: Session,
    credit: GameCredit,
) -> AdminMoneyCreditGrantSummaryRead:
    user = db.get(User, credit.user_id)
    booking = (
        db.get(Booking, credit.source_booking_id)
        if credit.source_booking_id is not None
        else None
    )
    game_id = credit.source_game_id or (
        booking.game_id if booking is not None else None
    )
    game = db.get(Game, game_id) if game_id is not None else None
    return build_credit_summary_from_context(
        credit,
        user=user,
        booking=booking,
        game=game,
        reserved_cents=sum_credit_reserved_cents(db, credit.id),
        open_money_issue_count=count_credit_open_money_issues(db, credit.id),
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
    query_text: str | None = None,
    limit: int = 50,
    cursor: str | None = None,
) -> AdminMoneyCreditListResponseRead:
    validate_admin_money_credit_status(credit_status)

    query = select(GameCredit).outerjoin(User, GameCredit.user_id == User.id)
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

    normalized_query = " ".join((query_text or "").strip().split())
    if normalized_query:
        query_uuid = maybe_uuid(normalized_query)
        query_filters = []
        if query_uuid is not None:
            usage_match = (
                select(GameCreditUsage.id)
                .where(
                    GameCreditUsage.game_credit_id == GameCredit.id,
                    GameCreditUsage.id == query_uuid,
                )
                .correlate(GameCredit)
            )
            query_filters.extend(
                [
                    GameCredit.id == query_uuid,
                    GameCredit.user_id == query_uuid,
                    GameCredit.source_game_id == query_uuid,
                    GameCredit.source_booking_id == query_uuid,
                    GameCredit.source_payment_id == query_uuid,
                    usage_match.exists(),
                ]
            )
        else:
            prefix_query = f"{normalized_query.lower()}%"
            query_filters.extend(
                [
                    func.lower(User.email).like(prefix_query),
                    func.lower(User.first_name).like(prefix_query),
                    func.lower(User.last_name).like(prefix_query),
                ]
            )
        query = query.where(or_(*query_filters))
    query = apply_desc_cursor(query, GameCredit, GameCredit.created_at, cursor)

    credits = list(
        db.scalars(
            query.order_by(GameCredit.created_at.desc(), GameCredit.id.desc()).limit(limit + 1)
        ).all()
    )
    return AdminMoneyCreditListResponseRead(
        items=[
            AdminMoneyCreditGrantListRead(**credit.model_dump())
            for credit in build_credit_summaries(db, credits[:limit])
        ],
        has_more=page_has_more(credits, limit=limit),
        next_cursor=next_cursor_for_rows(
            credits,
            limit=limit,
            sort_attr="created_at",
        ),
    )


def count_credit_usages(db: Session, credit_id: uuid.UUID) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(GameCreditUsage)
            .where(GameCreditUsage.game_credit_id == credit_id)
        )
        or 0
    )


def list_credit_usages(db: Session, credit_id: uuid.UUID) -> list[GameCreditUsage]:
    return list(
        db.scalars(
            select(GameCreditUsage)
            .where(GameCreditUsage.game_credit_id == credit_id)
            .order_by(GameCreditUsage.created_at.desc(), GameCreditUsage.id.desc())
            .limit(ADMIN_MONEY_CREDIT_USAGE_DETAIL_LIMIT)
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


def list_credit_money_issues(
    db: Session,
    *,
    credit: GameCredit,
    credit_usages: list[GameCreditUsage],
) -> list:
    return list_related_money_issues(
        db,
        game_credit_id=credit.id,
        credit_usage_ids=[usage.id for usage in credit_usages],
        limit=ADMIN_MONEY_DETAIL_RELATED_LIMIT,
    )


def list_credit_audit_actions(
    db: Session,
    *,
    viewer_user: User,
    credit: GameCredit,
    credit_usages: list[GameCreditUsage],
) -> list[AdminAction]:
    usage_ids = [usage.id for usage in credit_usages]
    filters = [AdminAction.target_game_credit_id == credit.id]
    if usage_ids:
        filters.append(AdminAction.target_credit_usage_id.in_(usage_ids))

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
    credit_usage_count = count_credit_usages(db, credit.id)
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
    money_issues = list_credit_money_issues(
        db,
        credit=credit,
        credit_usages=credit_usages,
    )
    audit_actions = list_credit_audit_actions(
        db,
        viewer_user=viewer_user,
        credit=credit,
        credit_usages=credit_usages,
    )

    refund_items = [
        AdminMoneyRefundDetailItemRead(**refund.model_dump())
        for refund in build_refund_summaries(db, refunds)
    ]

    return AdminMoneyCreditDetailRead(
        credit=build_credit_summary(db, credit),
        credit_usages=credit_usages,
        credit_usage_count=credit_usage_count,
        credit_usages_truncated=credit_usage_count > len(credit_usages),
        payments=build_payment_summaries(db, payments, detail=True),
        refunds=refund_items,
        booking=booking,
        game=game,
        linked_money_issues=money_issues,
        admin_actions=audit_actions,
    )
