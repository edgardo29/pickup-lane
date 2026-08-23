"""Admin money issue search, summary, and detail projections."""

import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from backend.models import (
    Booking,
    Game,
    GameCredit,
    GameCreditUsage,
    MoneyIssue,
    MoneyIssueEvent,
    Payment,
    Refund,
    RefundEvent,
    User,
)
from backend.schemas.admin_money_credit_schema import (
    AdminMoneyCreditGrantSummaryRead,
)
from backend.schemas.admin_money_issue_detail_schema import AdminMoneyIssueDetailRead
from backend.schemas.admin_money_issue_schema import (
    AdminMoneyIssueListResponseRead,
    AdminMoneyIssueSummaryRead,
)
from backend.schemas.admin_money_refund_schema import AdminMoneyRefundDetailItemRead
from backend.services.admin_money_cursor import (
    apply_asc_cursor,
    apply_desc_cursor,
    next_cursor_for_rows,
    page_has_more,
)
from backend.services.admin_money_display import admin_money_display, compact_id
from backend.services.admin_money_issue_rules import (
    ADMIN_MONEY_ISSUE_STATUSES,
    ISSUE_DEFAULTS,
    MONEY_ISSUE_EVENT_LIMIT,
    MONEY_ISSUE_OPERATION_KEY_MIN_PREFIX_CHARS,
    MONEY_ISSUE_OPERATION_KEY_PREFIXES,
    MONEY_ISSUE_REFUND_EVENT_LIMIT,
    MONEY_ISSUE_SEARCH_USER_LIMIT,
)
from backend.services.admin_user_service import (
    apply_admin_user_text_search,
    escape_like_search,
    parse_exact_email_query,
)


def sort_money_issues_open_first(issues: list[MoneyIssue]) -> list[MoneyIssue]:
    def sort_key(issue: MoneyIssue) -> tuple[int, float, str]:
        activity_at = (
            issue.last_activity_at
            or issue.first_detected_at
            or issue.created_at
        )
        activity_timestamp = activity_at.timestamp() if activity_at is not None else 0
        return (
            0 if issue.status == "open" else 1,
            -activity_timestamp,
            str(issue.id),
        )

    return sorted(issues, key=sort_key)


def load_by_id(db: Session, model, ids: set[uuid.UUID]) -> dict[uuid.UUID, object]:
    if not ids:
        return {}
    return {
        row.id: row
        for row in db.scalars(select(model).where(model.id.in_(ids))).all()
    }


def build_money_issue_context_label(
    issue: MoneyIssue,
    *,
    booking: Booking | None,
    payment: Payment | None,
    refund: Refund | None,
    credit: GameCredit | None,
    credit_usage: GameCreditUsage | None,
) -> str | None:
    if booking is not None:
        return f"Booking {compact_id(booking.id)}"
    if refund is not None:
        return f"Refund {compact_id(refund.id)}"
    if payment is not None:
        return f"Payment {compact_id(payment.id)}"
    if credit is not None:
        return f"Credit {compact_id(credit.id)}"
    if credit_usage is not None:
        return f"Credit usage {compact_id(credit_usage.id)}"
    if issue.target_game_id is not None:
        return f"Game {compact_id(issue.target_game_id)}"
    return None


def build_money_issue_summary_from_context(
    issue: MoneyIssue,
    *,
    user: User | None,
    game: Game | None,
    booking: Booking | None,
    payment: Payment | None,
    refund: Refund | None,
    credit: GameCredit | None,
    credit_usage: GameCreditUsage | None,
) -> AdminMoneyIssueSummaryRead:
    display = admin_money_display(
        user=user,
        game=game,
        context_label=build_money_issue_context_label(
            issue,
            booking=booking,
            payment=payment,
            refund=refund,
            credit=credit,
            credit_usage=credit_usage,
        ),
        payment_id=payment.id if payment is not None else issue.target_payment_id,
        refund_id=refund.id if refund is not None else issue.target_refund_id,
        credit_id=credit.id if credit is not None else issue.target_game_credit_id,
    )
    return AdminMoneyIssueSummaryRead.model_validate(issue).model_copy(
        update={"display": display}
    )


def build_money_issue_summaries(
    db: Session,
    issues: list[MoneyIssue],
) -> list[AdminMoneyIssueSummaryRead]:
    if not issues:
        return []

    refund_ids = {
        issue.target_refund_id
        for issue in issues
        if issue.target_refund_id is not None
    }
    refunds = load_by_id(db, Refund, refund_ids)

    credit_usage_ids = {
        issue.target_credit_usage_id
        for issue in issues
        if issue.target_credit_usage_id is not None
    }
    credit_usages = load_by_id(db, GameCreditUsage, credit_usage_ids)

    payment_ids = {
        issue.target_payment_id
        for issue in issues
        if issue.target_payment_id is not None
    }
    payment_ids.update(refund.payment_id for refund in refunds.values())
    payments = load_by_id(db, Payment, payment_ids)

    credit_ids = {
        issue.target_game_credit_id
        for issue in issues
        if issue.target_game_credit_id is not None
    }
    credit_ids.update(
        usage.game_credit_id
        for usage in credit_usages.values()
        if usage.game_credit_id is not None
    )
    credits = load_by_id(db, GameCredit, credit_ids)

    booking_ids = {
        issue.target_booking_id
        for issue in issues
        if issue.target_booking_id is not None
    }
    booking_ids.update(
        refund.booking_id
        for refund in refunds.values()
        if refund.booking_id is not None
    )
    booking_ids.update(
        payment.booking_id
        for payment in payments.values()
        if payment.booking_id is not None
    )
    booking_ids.update(
        credit.source_booking_id
        for credit in credits.values()
        if credit.source_booking_id is not None
    )
    booking_ids.update(
        usage.booking_id
        for usage in credit_usages.values()
        if usage.booking_id is not None
    )
    bookings = load_by_id(db, Booking, booking_ids)

    user_ids = {
        issue.target_user_id
        for issue in issues
        if issue.target_user_id is not None
    }
    user_ids.update(payment.payer_user_id for payment in payments.values())
    user_ids.update(credit.user_id for credit in credits.values())
    users = load_by_id(db, User, user_ids)

    game_ids = {
        issue.target_game_id
        for issue in issues
        if issue.target_game_id is not None
    }
    game_ids.update(
        payment.game_id
        for payment in payments.values()
        if payment.game_id is not None
    )
    game_ids.update(
        credit.source_game_id
        for credit in credits.values()
        if credit.source_game_id is not None
    )
    game_ids.update(
        usage.game_id
        for usage in credit_usages.values()
        if usage.game_id is not None
    )
    game_ids.update(
        booking.game_id
        for booking in bookings.values()
        if booking.game_id is not None
    )
    games = load_by_id(db, Game, game_ids)

    summaries = []
    for issue in issues:
        refund = (
            refunds.get(issue.target_refund_id)
            if issue.target_refund_id is not None
            else None
        )
        payment = (
            payments.get(issue.target_payment_id)
            if issue.target_payment_id is not None
            else None
        )
        if payment is None and refund is not None:
            payment = payments.get(refund.payment_id)
        credit_usage = (
            credit_usages.get(issue.target_credit_usage_id)
            if issue.target_credit_usage_id is not None
            else None
        )
        credit = (
            credits.get(issue.target_game_credit_id)
            if issue.target_game_credit_id is not None
            else None
        )
        if credit is None and credit_usage is not None:
            credit = credits.get(credit_usage.game_credit_id)

        booking_id = (
            issue.target_booking_id
            or (refund.booking_id if refund is not None else None)
            or (payment.booking_id if payment is not None else None)
            or (credit.source_booking_id if credit is not None else None)
            or (credit_usage.booking_id if credit_usage is not None else None)
        )
        booking = bookings.get(booking_id) if booking_id is not None else None
        user_id = (
            issue.target_user_id
            or (payment.payer_user_id if payment is not None else None)
            or (credit.user_id if credit is not None else None)
        )
        game_id = (
            issue.target_game_id
            or (payment.game_id if payment is not None else None)
            or (credit.source_game_id if credit is not None else None)
            or (credit_usage.game_id if credit_usage is not None else None)
            or (booking.game_id if booking is not None else None)
        )
        summaries.append(
            build_money_issue_summary_from_context(
                issue,
                user=users.get(user_id) if user_id is not None else None,
                game=games.get(game_id) if game_id is not None else None,
                booking=booking,
                payment=payment,
                refund=refund,
                credit=credit,
                credit_usage=credit_usage,
            )
        )
    return summaries


def build_money_issue_summary(
    db: Session,
    issue: MoneyIssue,
) -> AdminMoneyIssueSummaryRead:
    return build_money_issue_summaries(db, [issue])[0]


def normalize_issue_status(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in ADMIN_MONEY_ISSUE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="issue status is not supported.",
        )
    return normalized


def maybe_uuid(value: str | None) -> uuid.UUID | None:
    if value is None:
        return None
    try:
        return uuid.UUID(value.strip())
    except (TypeError, ValueError):
        return None


def normalize_issue_type(value: str | None) -> str | None:
    normalized = " ".join((value or "").strip().lower().split())
    if not normalized:
        return None
    if normalized not in ISSUE_DEFAULTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="money issue type is not supported.",
        )
    return normalized


def list_query_user_ids(db: Session, normalized_query: str) -> list[uuid.UUID]:
    exact_email = parse_exact_email_query(normalized_query)
    if exact_email is not None:
        user_statement = select(User.id).where(
            User.deleted_at.is_(None),
            User.account_status != "deleted",
            func.lower(func.coalesce(User.email, "")) == exact_email,
        )
    else:
        user_statement = apply_admin_user_text_search(
            select(User.id),
            normalized_query,
        ).order_by(User.created_at.desc(), User.id.desc())
    return list(
        db.scalars(user_statement.limit(MONEY_ISSUE_SEARCH_USER_LIMIT)).all()
    )


def apply_money_issue_query_filter(
    db: Session,
    statement: Any,
    query_text: str | None,
) -> Any:
    normalized_query = " ".join((query_text or "").strip().split())
    if not normalized_query:
        return statement

    query_filters = []
    query_uuid = maybe_uuid(normalized_query)
    if query_uuid is not None:
        query_filters.extend(
            [
                MoneyIssue.id == query_uuid,
                MoneyIssue.target_user_id == query_uuid,
            ]
        )
    else:
        query_filters.extend(
            MoneyIssue.target_user_id == user_id
            for user_id in list_query_user_ids(db, normalized_query)
        )

    normalized_operation_key_query = normalized_query.lower()
    if any(
        normalized_operation_key_query.startswith(prefix)
        and len(normalized_operation_key_query)
        >= len(prefix) + MONEY_ISSUE_OPERATION_KEY_MIN_PREFIX_CHARS
        for prefix in MONEY_ISSUE_OPERATION_KEY_PREFIXES
    ):
        query_filters.append(
            MoneyIssue.operation_key.like(
                f"{escape_like_search(normalized_operation_key_query)}%",
                escape="\\",
            )
        )
    else:
        query_filters.append(MoneyIssue.operation_key == normalized_operation_key_query)

    return statement.where(or_(*query_filters))


def apply_money_issue_filters(
    statement: Any,
    *,
    issue_status: str,
    issue_type: str | None = None,
    user_id: uuid.UUID | None = None,
) -> Any:
    if issue_status != "all":
        statement = statement.where(MoneyIssue.status == issue_status)
    if issue_type is not None:
        statement = statement.where(MoneyIssue.issue_type == issue_type)
    if user_id is not None:
        statement = statement.where(MoneyIssue.target_user_id == user_id)
    return statement


def list_admin_money_issues(
    db: Session,
    *,
    issue_status: str = "open",
    issue_type: str | None = None,
    user_id: uuid.UUID | None = None,
    limit: int = 50,
) -> list[MoneyIssue]:
    normalized_status = normalize_issue_status(issue_status)
    normalized_issue_type = normalize_issue_type(issue_type)
    statement = apply_money_issue_filters(
        select(MoneyIssue),
        issue_status=normalized_status,
        issue_type=normalized_issue_type,
        user_id=user_id,
    )

    if normalized_status == "open":
        sort_columns = (MoneyIssue.first_detected_at.asc(), MoneyIssue.id.asc())
    elif normalized_status == "resolved":
        sort_columns = (MoneyIssue.resolved_at.desc(), MoneyIssue.id.desc())
    else:
        sort_columns = (MoneyIssue.last_activity_at.desc(), MoneyIssue.id.desc())
    return list(db.scalars(statement.order_by(*sort_columns).limit(limit)).all())


def list_admin_money_issues_page(
    db: Session,
    *,
    issue_status: str = "open",
    issue_type: str | None = None,
    user_id: uuid.UUID | None = None,
    query_text: str | None = None,
    limit: int = 50,
    cursor: str | None = None,
) -> AdminMoneyIssueListResponseRead:
    normalized_status = normalize_issue_status(issue_status)
    normalized_issue_type = normalize_issue_type(issue_type)
    normalized_query = " ".join((query_text or "").strip().split())
    cursor_context = {
        "issue_status": normalized_status,
        "issue_type": normalized_issue_type,
        "kind": "admin_money_issues",
        "query": normalized_query,
        "user_id": str(user_id) if user_id is not None else None,
    }

    statement = apply_money_issue_filters(
        select(MoneyIssue),
        issue_status=normalized_status,
        issue_type=normalized_issue_type,
        user_id=user_id,
    )
    statement = apply_money_issue_query_filter(db, statement, normalized_query)

    if normalized_status == "open":
        statement = apply_asc_cursor(
            statement,
            MoneyIssue,
            MoneyIssue.first_detected_at,
            cursor,
            context=cursor_context,
        )
        rows = list(
            db.scalars(
                statement.order_by(
                    MoneyIssue.first_detected_at.asc(),
                    MoneyIssue.id.asc(),
                )
                .limit(limit + 1)
            ).all()
        )
        return AdminMoneyIssueListResponseRead(
            items=build_money_issue_summaries(db, rows[:limit]),
            has_more=page_has_more(rows, limit=limit),
            next_cursor=next_cursor_for_rows(
                rows,
                limit=limit,
                sort_attr="first_detected_at",
                context=cursor_context,
            ),
        )

    sort_column = (
        MoneyIssue.resolved_at
        if normalized_status == "resolved"
        else MoneyIssue.last_activity_at
    )
    sort_attr = "resolved_at" if normalized_status == "resolved" else "last_activity_at"
    statement = apply_desc_cursor(
        statement,
        MoneyIssue,
        sort_column,
        cursor,
        context=cursor_context,
    )
    rows = list(
        db.scalars(
            statement.order_by(sort_column.desc(), MoneyIssue.id.desc())
            .limit(limit + 1)
        ).all()
    )
    return AdminMoneyIssueListResponseRead(
        items=build_money_issue_summaries(db, rows[:limit]),
        has_more=page_has_more(rows, limit=limit),
        next_cursor=next_cursor_for_rows(
            rows,
            limit=limit,
            sort_attr=sort_attr,
            context=cursor_context,
        ),
    )


def list_related_money_issues(
    db: Session,
    *,
    user_id: uuid.UUID | None = None,
    payment_id: uuid.UUID | None = None,
    refund_id: uuid.UUID | None = None,
    game_credit_id: uuid.UUID | None = None,
    credit_usage_ids: list[uuid.UUID] | None = None,
    status_filter: str | None = None,
    limit: int = 100,
) -> list[MoneyIssue]:
    filters = []
    if user_id is not None:
        filters.append(MoneyIssue.target_user_id == user_id)
    if payment_id is not None:
        filters.append(MoneyIssue.target_payment_id == payment_id)
    if refund_id is not None:
        filters.append(MoneyIssue.target_refund_id == refund_id)
    if game_credit_id is not None:
        filters.append(MoneyIssue.target_game_credit_id == game_credit_id)
    if credit_usage_ids:
        filters.append(MoneyIssue.target_credit_usage_id.in_(credit_usage_ids))
    if not filters:
        return []

    statement = select(MoneyIssue).where(or_(*filters))
    if status_filter is not None:
        statement = statement.where(MoneyIssue.status == status_filter)

    status_rank = case(
        (MoneyIssue.status == "open", 0),
        else_=1,
    )
    issues = list(
        db.scalars(
            statement.order_by(
                status_rank.asc(),
                MoneyIssue.last_activity_at.desc(),
                MoneyIssue.id.desc(),
            ).limit(limit)
        ).all()
    )
    return sort_money_issues_open_first(issues)


def get_money_issue_or_404(db: Session, money_issue_id: uuid.UUID) -> MoneyIssue:
    money_issue = db.get(MoneyIssue, money_issue_id)
    if money_issue is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Money issue not found.",
        )
    return money_issue


def list_money_issue_events(
    db: Session,
    money_issue_id: uuid.UUID,
) -> list[MoneyIssueEvent]:
    return list(
        db.scalars(
            select(MoneyIssueEvent)
            .where(MoneyIssueEvent.money_issue_id == money_issue_id)
            .order_by(MoneyIssueEvent.occurred_at.asc(), MoneyIssueEvent.id.asc())
            .limit(MONEY_ISSUE_EVENT_LIMIT)
        ).all()
    )


def list_money_issue_refund_events(
    db: Session,
    refund_id: uuid.UUID,
) -> list[RefundEvent]:
    return list(
        db.scalars(
            select(RefundEvent)
            .where(RefundEvent.refund_id == refund_id)
            .order_by(RefundEvent.occurred_at.desc(), RefundEvent.id.desc())
            .limit(MONEY_ISSUE_REFUND_EVENT_LIMIT)
        ).all()
    )


def get_admin_money_issue_detail(
    db: Session,
    *,
    money_issue_id: uuid.UUID,
) -> AdminMoneyIssueDetailRead:
    from backend.services.admin_money_credit_service import build_credit_summary
    from backend.services.admin_money_payment_service import build_payment_summary
    from backend.services.admin_money_refund_query_service import build_refund_summary

    money_issue = get_money_issue_or_404(db, money_issue_id)
    events = list_money_issue_events(db, money_issue.id)
    refund = (
        db.get(Refund, money_issue.target_refund_id)
        if money_issue.target_refund_id
        else None
    )
    payment = (
        db.get(Payment, money_issue.target_payment_id)
        if money_issue.target_payment_id
        else None
    )
    booking = (
        db.get(Booking, money_issue.target_booking_id)
        if money_issue.target_booking_id
        else None
    )
    game = (
        db.get(Game, money_issue.target_game_id)
        if money_issue.target_game_id
        else None
    )
    credit = (
        db.get(GameCredit, money_issue.target_game_credit_id)
        if money_issue.target_game_credit_id
        else None
    )
    credit_usages = []
    if money_issue.target_credit_usage_id is not None:
        credit_usage = db.get(GameCreditUsage, money_issue.target_credit_usage_id)
        if credit_usage is not None:
            credit_usages.append(credit_usage)
    recent_refund_events = (
        list_money_issue_refund_events(db, refund.id)
        if refund is not None
        else []
    )

    refund_summary = build_refund_summary(db, refund) if refund is not None else None

    return AdminMoneyIssueDetailRead(
        money_issue=build_money_issue_summary(db, money_issue),
        events=events,
        recent_refund_events=recent_refund_events,
        refund=(
            AdminMoneyRefundDetailItemRead(**refund_summary.model_dump())
            if refund_summary is not None
            else None
        ),
        payment=build_payment_summary(db, payment, detail=True)
        if payment is not None
        else None,
        booking=booking,
        game=game,
        credit=build_credit_summary(db, credit) if credit is not None else None,
        credit_usages=credit_usages,
    )
