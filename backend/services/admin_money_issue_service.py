"""Money Issue queue reads and lifecycle actions."""

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import case, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import (
    AdminAction,
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
from backend.schemas.admin_money_schema import (
    AdminMoneyRefundDetailItemRead,
    AdminMoneyIssueCreditRetryCreate,
    AdminMoneyIssueDetailRead,
    AdminMoneyIssueListResponseRead,
    AdminMoneyIssueResolveCreate,
    AdminMoneyIssueSummaryRead,
)
from backend.services.admin_action_service import (
    build_admin_action_conflict_detail,
    record_admin_action,
)
from backend.services.admin_money_cursor import (
    apply_asc_cursor,
    apply_desc_cursor,
    next_cursor_for_rows,
    page_has_more,
)
from backend.services.admin_money_display import admin_money_display, compact_id
from backend.services.admin_user_service import (
    apply_admin_user_text_search,
    escape_like_search,
    parse_exact_email_query,
)
from backend.services.admin_record_rules import (
    normalize_idempotency_key,
    normalize_optional_text,
)
from backend.services.game_credit_service import (
    GameCreditLedgerError,
    release_reserved_game_credit_usage,
    restore_redeemed_game_credit_usage,
)

ADMIN_MONEY_ISSUE_STATUSES = {"open", "resolved", "all"}
MONEY_ISSUE_EVENT_LIMIT = 100
MONEY_ISSUE_REFUND_EVENT_LIMIT = 100
MONEY_ISSUE_SEARCH_USER_LIMIT = 25
MONEY_ISSUE_OPERATION_KEY_PREFIXES = (
    "refund:",
    "credit-restore:",
    "credit-release:",
)
MONEY_ISSUE_OPERATION_KEY_MIN_PREFIX_CHARS = 8
ISSUE_RESOLUTION_REASONS = {
    "retried_successfully",
    "provider_completed_no_action_required",
    "handled_externally",
    "invalid_issue",
    "unable_to_complete_documented",
}

ISSUE_DEFAULTS = {
    "refund_missing_provider_reference": (
        "cash_refund",
        "recover_provider_reference",
    ),
    "refund_processing_overdue": (
        "cash_refund",
        "verify_provider_refund",
    ),
    "refund_failed": (
        "cash_refund",
        "retry_refund",
    ),
    "refund_cancelled": (
        "cash_refund",
        "retry_refund",
    ),
    "refund_outcome_unknown": (
        "cash_refund",
        "review_unknown_outcome",
    ),
    "credit_restore_failed": (
        "game_credit_restore",
        "retry_credit_restore",
    ),
    "credit_release_failed": (
        "game_credit_release",
        "retry_credit_release",
    ),
}


def build_refund_issue_operation_key(refund_id: uuid.UUID) -> str:
    return f"refund:{refund_id}"


def build_credit_restore_issue_operation_key(usage_id: uuid.UUID) -> str:
    return f"credit-restore:{usage_id}"


def build_credit_release_issue_operation_key(usage_id: uuid.UUID) -> str:
    return f"credit-release:{usage_id}"


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

    statement = apply_money_issue_filters(
        select(MoneyIssue),
        issue_status=normalized_status,
        issue_type=normalized_issue_type,
        user_id=user_id,
    )
    statement = apply_money_issue_query_filter(db, statement, query_text)

    if normalized_status == "open":
        statement = apply_asc_cursor(
            statement,
            MoneyIssue,
            MoneyIssue.first_detected_at,
            cursor,
        )
        rows = list(
            db.scalars(
                statement.order_by(MoneyIssue.first_detected_at.asc(), MoneyIssue.id.asc())
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


def get_money_issue_for_update_or_404(
    db: Session,
    money_issue_id: uuid.UUID,
) -> MoneyIssue:
    money_issue = db.scalars(
        select(MoneyIssue).where(MoneyIssue.id == money_issue_id).with_for_update()
    ).first()
    if money_issue is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Money issue not found.",
        )
    return money_issue


def get_existing_money_issue_action(
    db: Session,
    *,
    admin_user_id: uuid.UUID,
    money_issue_id: uuid.UUID,
    action_type: str,
    idempotency_key: str,
) -> AdminAction | None:
    return db.scalars(
        select(AdminAction)
        .where(
            AdminAction.admin_user_id == admin_user_id,
            AdminAction.action_type == action_type,
            AdminAction.target_money_issue_id == money_issue_id,
            AdminAction.idempotency_key == idempotency_key,
        )
        .order_by(AdminAction.created_at.desc(), AdminAction.id.desc())
    ).first()


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


def detection_event_type(
    *,
    previous_status: str,
    previous_issue_type: str,
    issue_type: str,
    previous_action: str,
    recommended_action_code: str,
    fallback_event_type: str,
) -> str:
    if previous_status == "resolved":
        return "issue_reopened"
    if previous_issue_type != issue_type:
        return "classification_changed"
    if previous_action != recommended_action_code:
        return "recommended_action_changed"
    return fallback_event_type


def append_money_issue_event(
    db: Session,
    *,
    money_issue: MoneyIssue,
    event_type: str,
    event_source: str,
    reason_code: str,
    summary: str,
    actor_user_id: uuid.UUID | None = None,
    admin_action_id: uuid.UUID | None = None,
    refund_event_id: uuid.UUID | None = None,
    result_credit_usage_id: uuid.UUID | None = None,
    previous_status: str | None = None,
    new_status: str | None = None,
    previous_issue_type: str | None = None,
    new_issue_type: str | None = None,
    previous_recommended_action_code: str | None = None,
    new_recommended_action_code: str | None = None,
    metadata: dict[str, Any] | None = None,
    occurred_at: datetime | None = None,
) -> MoneyIssueEvent:
    now = occurred_at or datetime.now(timezone.utc)
    event = MoneyIssueEvent(
        id=uuid.uuid4(),
        money_issue_id=money_issue.id,
        event_type=event_type,
        event_source=event_source,
        actor_user_id=actor_user_id,
        admin_action_id=admin_action_id,
        refund_event_id=refund_event_id,
        result_credit_usage_id=result_credit_usage_id,
        previous_status=previous_status,
        new_status=new_status,
        previous_issue_type=previous_issue_type,
        new_issue_type=new_issue_type,
        previous_recommended_action_code=previous_recommended_action_code,
        new_recommended_action_code=new_recommended_action_code,
        reason_code=reason_code,
        summary=summary,
        event_metadata=metadata,
        occurred_at=now,
        created_at=now,
    )
    money_issue.last_activity_at = now
    money_issue.updated_at = now
    db.add(money_issue)
    db.add(event)
    db.flush()
    return event


def stage_refund_money_issue(
    db: Session,
    *,
    refund: Refund,
    payment: Payment | None,
    issue_type: str,
    reason_code: str,
    summary: str,
    refund_event: RefundEvent | None = None,
    admin_action: AdminAction | None = None,
    now: datetime | None = None,
) -> MoneyIssue:
    if issue_type not in ISSUE_DEFAULTS or not issue_type.startswith("refund_"):
        raise ValueError("Unsupported refund money issue type.")

    detected_at = now or datetime.now(timezone.utc)
    value_kind, recommended_action_code = ISSUE_DEFAULTS[issue_type]
    operation_key = build_refund_issue_operation_key(refund.id)
    target_booking_id = refund.booking_id or (payment.booking_id if payment is not None else None)
    target_game_id = payment.game_id if payment is not None else None
    if target_game_id is None:
        if target_booking_id is not None:
            booking = db.get(Booking, target_booking_id)
            target_game_id = booking.game_id if booking is not None else None
    money_issue = db.scalars(
        select(MoneyIssue).where(MoneyIssue.operation_key == operation_key).with_for_update()
    ).first()

    if money_issue is None:
        money_issue = MoneyIssue(
            id=uuid.uuid4(),
            operation_key=operation_key,
            status="open",
            issue_type=issue_type,
            origin_workflow=refund.origin_workflow,
            value_kind=value_kind,
            amount_cents=refund.amount_cents,
            currency=refund.currency,
            target_user_id=payment.payer_user_id if payment is not None else None,
            target_game_id=target_game_id,
            target_booking_id=target_booking_id,
            target_payment_id=refund.payment_id,
            target_refund_id=refund.id,
            target_game_credit_id=None,
            target_credit_usage_id=None,
            latest_reason_code=reason_code,
            latest_summary=summary,
            recommended_action_code=recommended_action_code,
            occurrence_count=1,
            reopen_count=0,
            first_detected_at=detected_at,
            last_detected_at=detected_at,
            last_activity_at=detected_at,
            created_at=detected_at,
            updated_at=detected_at,
        )
        db.add(money_issue)
        db.flush()
        append_money_issue_event(
            db,
            money_issue=money_issue,
            event_type="issue_opened",
            event_source="system",
            actor_user_id=admin_action.admin_user_id if admin_action is not None else None,
            admin_action_id=admin_action.id if admin_action is not None else None,
            refund_event_id=refund_event.id if refund_event is not None else None,
            reason_code=reason_code,
            summary=summary,
            new_status="open",
            new_issue_type=issue_type,
            new_recommended_action_code=recommended_action_code,
        )
        return money_issue

    previous_status = money_issue.status
    previous_issue_type = money_issue.issue_type
    previous_action = money_issue.recommended_action_code
    money_issue.status = "open"
    money_issue.issue_type = issue_type
    money_issue.origin_workflow = refund.origin_workflow
    money_issue.value_kind = value_kind
    money_issue.amount_cents = refund.amount_cents
    money_issue.currency = refund.currency
    money_issue.target_user_id = payment.payer_user_id if payment is not None else None
    money_issue.target_game_id = target_game_id
    money_issue.target_booking_id = target_booking_id
    money_issue.target_payment_id = refund.payment_id
    money_issue.target_refund_id = refund.id
    money_issue.latest_reason_code = reason_code
    money_issue.latest_summary = summary
    money_issue.recommended_action_code = recommended_action_code
    money_issue.occurrence_count += 1
    money_issue.last_detected_at = detected_at
    money_issue.resolved_at = None
    money_issue.resolved_by_user_id = None
    money_issue.resolution_reason_code = None
    money_issue.resolution_note = None
    money_issue.resolution_external_reference = None
    if previous_status == "resolved":
        money_issue.reopen_count += 1

    append_money_issue_event(
        db,
        money_issue=money_issue,
        event_type=detection_event_type(
            previous_status=previous_status,
            previous_issue_type=previous_issue_type,
            issue_type=issue_type,
            previous_action=previous_action,
            recommended_action_code=recommended_action_code,
            fallback_event_type="refund_outcome_linked"
            if refund_event is not None
            else "recommended_action_changed",
        ),
        event_source="system",
        actor_user_id=admin_action.admin_user_id if admin_action is not None else None,
        admin_action_id=admin_action.id if admin_action is not None else None,
        refund_event_id=refund_event.id if refund_event is not None else None,
        reason_code=reason_code,
        summary=summary,
        previous_status=previous_status,
        new_status="open",
        previous_issue_type=previous_issue_type,
        new_issue_type=issue_type,
        previous_recommended_action_code=previous_action,
        new_recommended_action_code=recommended_action_code,
    )
    return money_issue


def stage_credit_money_issue(
    db: Session,
    *,
    credit_usage: GameCreditUsage,
    game_credit: GameCredit | None,
    issue_type: str,
    origin_workflow: str,
    reason_code: str,
    summary: str,
    admin_action: AdminAction | None = None,
    now: datetime | None = None,
) -> MoneyIssue:
    if issue_type not in ISSUE_DEFAULTS or not issue_type.startswith("credit_"):
        raise ValueError("Unsupported credit money issue type.")

    detected_at = now or datetime.now(timezone.utc)
    value_kind, recommended_action_code = ISSUE_DEFAULTS[issue_type]
    operation_key = (
        build_credit_release_issue_operation_key(credit_usage.id)
        if issue_type == "credit_release_failed"
        else build_credit_restore_issue_operation_key(credit_usage.id)
    )
    money_issue = db.scalars(
        select(MoneyIssue).where(MoneyIssue.operation_key == operation_key).with_for_update()
    ).first()
    target_user_id = game_credit.user_id if game_credit is not None else None

    if money_issue is None:
        money_issue = MoneyIssue(
            id=uuid.uuid4(),
            operation_key=operation_key,
            status="open",
            issue_type=issue_type,
            origin_workflow=origin_workflow,
            value_kind=value_kind,
            amount_cents=credit_usage.amount_cents,
            currency=credit_usage.currency,
            target_user_id=target_user_id,
            target_game_id=credit_usage.game_id,
            target_booking_id=credit_usage.booking_id,
            target_payment_id=credit_usage.payment_id,
            target_refund_id=None,
            target_game_credit_id=credit_usage.game_credit_id,
            target_credit_usage_id=credit_usage.id,
            latest_reason_code=reason_code,
            latest_summary=summary,
            recommended_action_code=recommended_action_code,
            occurrence_count=1,
            reopen_count=0,
            first_detected_at=detected_at,
            last_detected_at=detected_at,
            last_activity_at=detected_at,
            created_at=detected_at,
            updated_at=detected_at,
        )
        db.add(money_issue)
        db.flush()
        append_money_issue_event(
            db,
            money_issue=money_issue,
            event_type="issue_opened",
            event_source="system",
            actor_user_id=admin_action.admin_user_id if admin_action is not None else None,
            admin_action_id=admin_action.id if admin_action is not None else None,
            reason_code=reason_code,
            summary=summary,
            new_status="open",
            new_issue_type=issue_type,
            new_recommended_action_code=recommended_action_code,
        )
        return money_issue

    previous_status = money_issue.status
    previous_issue_type = money_issue.issue_type
    previous_action = money_issue.recommended_action_code
    money_issue.status = "open"
    money_issue.issue_type = issue_type
    money_issue.origin_workflow = origin_workflow
    money_issue.value_kind = value_kind
    money_issue.amount_cents = credit_usage.amount_cents
    money_issue.currency = credit_usage.currency
    money_issue.target_user_id = target_user_id
    money_issue.target_game_id = credit_usage.game_id
    money_issue.target_booking_id = credit_usage.booking_id
    money_issue.target_payment_id = credit_usage.payment_id
    money_issue.target_game_credit_id = credit_usage.game_credit_id
    money_issue.target_credit_usage_id = credit_usage.id
    money_issue.latest_reason_code = reason_code
    money_issue.latest_summary = summary
    money_issue.recommended_action_code = recommended_action_code
    money_issue.occurrence_count += 1
    money_issue.last_detected_at = detected_at
    money_issue.resolved_at = None
    money_issue.resolved_by_user_id = None
    money_issue.resolution_reason_code = None
    money_issue.resolution_note = None
    money_issue.resolution_external_reference = None
    if previous_status == "resolved":
        money_issue.reopen_count += 1
    append_money_issue_event(
        db,
        money_issue=money_issue,
        event_type=detection_event_type(
            previous_status=previous_status,
            previous_issue_type=previous_issue_type,
            issue_type=issue_type,
            previous_action=previous_action,
            recommended_action_code=recommended_action_code,
            fallback_event_type=issue_type,
        ),
        event_source="system",
        actor_user_id=admin_action.admin_user_id if admin_action is not None else None,
        admin_action_id=admin_action.id if admin_action is not None else None,
        reason_code=reason_code,
        summary=summary,
        previous_status=previous_status,
        new_status="open",
        previous_issue_type=previous_issue_type,
        new_issue_type=issue_type,
        previous_recommended_action_code=previous_action,
        new_recommended_action_code=recommended_action_code,
    )
    return money_issue


def get_admin_money_issue_detail(
    db: Session,
    *,
    money_issue_id: uuid.UUID,
) -> AdminMoneyIssueDetailRead:
    from backend.services.admin_money_credit_service import build_credit_summary
    from backend.services.admin_money_payment_service import build_payment_summary
    from backend.services.admin_money_refund_service import build_refund_summary

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


def money_issue_has_successful_credit_retry(db: Session, money_issue: MoneyIssue) -> bool:
    if money_issue.target_credit_usage_id is None:
        return False

    if money_issue.issue_type == "credit_release_failed":
        target_usage = db.get(GameCreditUsage, money_issue.target_credit_usage_id)
        return target_usage is not None and target_usage.usage_status == "released"

    if money_issue.issue_type == "credit_restore_failed":
        restored_usage = db.scalars(
            select(GameCreditUsage)
            .where(
                GameCreditUsage.original_usage_id == money_issue.target_credit_usage_id,
                GameCreditUsage.usage_type == "restore",
                GameCreditUsage.usage_status == "restored",
            )
            .limit(1)
        ).first()
        return restored_usage is not None

    return False


def validate_money_issue_resolution(
    db: Session,
    *,
    money_issue: MoneyIssue,
    resolution_reason_code: str,
    resolution_note: str | None,
    resolution_external_reference: str | None,
) -> None:
    if resolution_reason_code not in ISSUE_RESOLUTION_REASONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="resolution_reason_code is not supported.",
        )

    if resolution_reason_code == "handled_externally":
        if resolution_note is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="handled_externally requires resolution_note.",
            )
        if resolution_external_reference is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="handled_externally requires resolution_external_reference.",
            )
        return

    if resolution_reason_code in {"invalid_issue", "unable_to_complete_documented"}:
        if resolution_note is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{resolution_reason_code} requires resolution_note.",
            )
        return

    if resolution_reason_code in {
        "retried_successfully",
        "provider_completed_no_action_required",
    }:
        if money_issue.issue_type.startswith("refund_"):
            if money_issue.target_refund_id is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Refund issue is missing refund context.",
                )
            refund = db.get(Refund, money_issue.target_refund_id)
            if refund is None or refund.refund_status != "succeeded":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"{resolution_reason_code} requires the related refund "
                        "to be succeeded."
                    ),
                )
            return

        if money_issue.issue_type.startswith("credit_"):
            if not money_issue_has_successful_credit_retry(db, money_issue):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"{resolution_reason_code} requires the related credit "
                        "movement to be completed."
                    ),
                )
            return

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Money issue resolution is not valid for this issue.",
    )


def resolve_admin_money_issue(
    db: Session,
    *,
    admin_user: User,
    money_issue_id: uuid.UUID,
    payload: AdminMoneyIssueResolveCreate,
) -> AdminMoneyIssueDetailRead:
    resolution_reason_code = normalize_optional_text(
        payload.resolution_reason_code,
        "resolution_reason_code",
        max_length=80,
    )
    resolution_note = normalize_optional_text(
        payload.resolution_note,
        "resolution_note",
        max_length=1000,
    )
    resolution_external_reference = normalize_optional_text(
        payload.resolution_external_reference,
        "resolution_external_reference",
        max_length=255,
    )
    idempotency_key = normalize_idempotency_key(payload.idempotency_key)
    if resolution_reason_code is None or idempotency_key is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid resolution payload.",
        )

    existing_action = get_existing_money_issue_action(
        db,
        admin_user_id=admin_user.id,
        money_issue_id=money_issue_id,
        action_type="resolve_money_issue",
        idempotency_key=idempotency_key,
    )
    if existing_action is not None:
        return get_admin_money_issue_detail(db, money_issue_id=money_issue_id)

    money_issue = get_money_issue_for_update_or_404(db, money_issue_id)
    existing_action = get_existing_money_issue_action(
        db,
        admin_user_id=admin_user.id,
        money_issue_id=money_issue_id,
        action_type="resolve_money_issue",
        idempotency_key=idempotency_key,
    )
    if existing_action is not None:
        return get_admin_money_issue_detail(db, money_issue_id=money_issue_id)
    if money_issue.status == "resolved":
        return get_admin_money_issue_detail(db, money_issue_id=money_issue.id)
    validate_money_issue_resolution(
        db,
        money_issue=money_issue,
        resolution_reason_code=resolution_reason_code,
        resolution_note=resolution_note,
        resolution_external_reference=resolution_external_reference,
    )

    now = datetime.now(timezone.utc)
    previous_status = money_issue.status
    admin_action = record_admin_action(
        db,
        admin_user_id=admin_user.id,
        action_type="resolve_money_issue",
        target_user_id=money_issue.target_user_id,
        target_game_id=money_issue.target_game_id,
        target_booking_id=money_issue.target_booking_id,
        target_payment_id=money_issue.target_payment_id,
        target_refund_id=money_issue.target_refund_id,
        target_game_credit_id=money_issue.target_game_credit_id,
        target_credit_usage_id=money_issue.target_credit_usage_id,
        target_money_issue_id=money_issue.id,
        reason=resolution_note or resolution_reason_code,
        idempotency_key=idempotency_key,
        metadata={
            "old_status": previous_status,
            "new_status": "resolved",
            "resolution_reason_code": resolution_reason_code,
            "resolution_external_reference": resolution_external_reference,
            "source": "admin_money_issue_resolve",
        },
    )
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        existing_action = get_existing_money_issue_action(
            db,
            admin_user_id=admin_user.id,
            money_issue_id=money_issue_id,
            action_type="resolve_money_issue",
            idempotency_key=idempotency_key,
        )
        if existing_action is not None:
            return get_admin_money_issue_detail(db, money_issue_id=money_issue_id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_admin_action_conflict_detail(exc),
        ) from exc
    money_issue.status = "resolved"
    money_issue.resolved_at = now
    money_issue.resolved_by_user_id = admin_user.id
    money_issue.resolution_reason_code = resolution_reason_code
    money_issue.resolution_note = resolution_note
    money_issue.resolution_external_reference = resolution_external_reference
    money_issue.updated_at = now
    append_money_issue_event(
        db,
        money_issue=money_issue,
        event_type="issue_resolved",
        event_source="admin",
        actor_user_id=admin_user.id,
        admin_action_id=admin_action.id,
        reason_code=resolution_reason_code,
        summary=resolution_note or "Money issue resolved.",
        previous_status=previous_status,
        new_status="resolved",
    )

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        existing_action = get_existing_money_issue_action(
            db,
            admin_user_id=admin_user.id,
            money_issue_id=money_issue_id,
            action_type="resolve_money_issue",
            idempotency_key=idempotency_key,
        )
        if existing_action is not None:
            return get_admin_money_issue_detail(db, money_issue_id=money_issue_id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_admin_action_conflict_detail(exc),
        ) from exc

    return get_admin_money_issue_detail(db, money_issue_id=money_issue.id)


def retry_admin_money_issue_credit(
    db: Session,
    *,
    admin_user: User,
    money_issue_id: uuid.UUID,
    payload: AdminMoneyIssueCreditRetryCreate,
) -> AdminMoneyIssueDetailRead:
    reason = normalize_optional_text(payload.reason, "reason", max_length=1000)
    idempotency_key = normalize_idempotency_key(payload.idempotency_key)
    if reason is None or idempotency_key is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid credit retry payload.",
        )

    existing_action = get_existing_money_issue_action(
        db,
        admin_user_id=admin_user.id,
        money_issue_id=money_issue_id,
        action_type="retry_money_issue_credit",
        idempotency_key=idempotency_key,
    )
    if existing_action is not None:
        return get_admin_money_issue_detail(db, money_issue_id=money_issue_id)

    money_issue = get_money_issue_for_update_or_404(db, money_issue_id)
    existing_action = get_existing_money_issue_action(
        db,
        admin_user_id=admin_user.id,
        money_issue_id=money_issue_id,
        action_type="retry_money_issue_credit",
        idempotency_key=idempotency_key,
    )
    if existing_action is not None:
        return get_admin_money_issue_detail(db, money_issue_id=money_issue_id)
    if money_issue.status != "open":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only open money issues can be retried.",
        )
    if money_issue.issue_type not in {"credit_restore_failed", "credit_release_failed"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Money issue is not a credit retry issue.",
        )
    if money_issue.target_credit_usage_id is None or money_issue.target_booking_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Credit retry issue is missing usage or booking context.",
        )

    target_usage = db.scalars(
        select(GameCreditUsage)
        .where(GameCreditUsage.id == money_issue.target_credit_usage_id)
        .with_for_update()
    ).first()
    if target_usage is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credit usage not found.",
        )

    target_credit = db.scalars(
        select(GameCredit)
        .where(GameCredit.id == target_usage.game_credit_id)
        .with_for_update()
    ).first()
    if target_credit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game credit not found.")

    now = datetime.now(timezone.utc)
    retry_kind = "release" if money_issue.issue_type == "credit_release_failed" else "restore"
    try:
        admin_action = record_admin_action(
            db,
            admin_user_id=admin_user.id,
            action_type="retry_money_issue_credit",
            target_user_id=money_issue.target_user_id,
            target_game_id=money_issue.target_game_id,
            target_booking_id=money_issue.target_booking_id,
            target_payment_id=money_issue.target_payment_id,
            target_game_credit_id=money_issue.target_game_credit_id,
            target_credit_usage_id=money_issue.target_credit_usage_id,
            target_money_issue_id=money_issue.id,
            reason=reason,
            idempotency_key=idempotency_key,
            metadata={
                "issue_type": money_issue.issue_type,
                "operation_key": money_issue.operation_key,
                "retry_kind": retry_kind,
                "source": "admin_money_issue_credit_retry",
            },
        )
        db.flush()
        append_money_issue_event(
            db,
            money_issue=money_issue,
            event_type="admin_retry_initiated",
            event_source="admin",
            actor_user_id=admin_user.id,
            admin_action_id=admin_action.id,
            reason_code="admin_retry_initiated",
            summary=reason,
            occurred_at=now,
        )

        if retry_kind == "release":
            result_usage = release_reserved_game_credit_usage(
                db,
                target_usage.id,
                now=now,
                reason_code="admin_retry_credit_release",
            )
        else:
            result_usage = restore_redeemed_game_credit_usage(
                db,
                target_usage.id,
                now=now,
                restore_reason="admin_retry_credit_restore",
            )

        if result_usage is None:
            raise GameCreditLedgerError("No eligible credit usage was retried.")

        previous_action = money_issue.recommended_action_code
        money_issue.latest_reason_code = f"admin_retry_credit_{retry_kind}_succeeded"
        money_issue.latest_summary = "Admin credit retry completed."
        money_issue.recommended_action_code = "review_and_resolve_no_action"
        money_issue.updated_at = now
        append_money_issue_event(
            db,
            money_issue=money_issue,
            event_type=f"credit_{retry_kind}_succeeded",
            event_source="admin",
            actor_user_id=admin_user.id,
            admin_action_id=admin_action.id,
            result_credit_usage_id=result_usage.id,
            reason_code=money_issue.latest_reason_code,
            summary="Admin credit retry completed.",
            previous_recommended_action_code=previous_action,
            new_recommended_action_code=money_issue.recommended_action_code,
            occurred_at=now,
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        existing_action = get_existing_money_issue_action(
            db,
            admin_user_id=admin_user.id,
            money_issue_id=money_issue_id,
            action_type="retry_money_issue_credit",
            idempotency_key=idempotency_key,
        )
        if existing_action is not None:
            return get_admin_money_issue_detail(db, money_issue_id=money_issue_id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_admin_action_conflict_detail(exc),
        ) from exc
    except GameCreditLedgerError as exc:
        db.rollback()
        failed_issue = get_money_issue_for_update_or_404(db, money_issue_id)
        failure_action = record_admin_action(
            db,
            admin_user_id=admin_user.id,
            action_type="retry_money_issue_credit",
            target_user_id=failed_issue.target_user_id,
            target_game_id=failed_issue.target_game_id,
            target_booking_id=failed_issue.target_booking_id,
            target_payment_id=failed_issue.target_payment_id,
            target_game_credit_id=failed_issue.target_game_credit_id,
            target_credit_usage_id=failed_issue.target_credit_usage_id,
            target_money_issue_id=failed_issue.id,
            reason=reason,
            idempotency_key=idempotency_key,
            metadata={
                "issue_type": failed_issue.issue_type,
                "operation_key": failed_issue.operation_key,
                "retry_kind": retry_kind,
                "failure": str(exc),
                "source": "admin_money_issue_credit_retry",
            },
        )
        try:
            db.flush()
        except IntegrityError as integrity_exc:
            db.rollback()
            existing_action = get_existing_money_issue_action(
                db,
                admin_user_id=admin_user.id,
                money_issue_id=money_issue_id,
                action_type="retry_money_issue_credit",
                idempotency_key=idempotency_key,
            )
            if existing_action is not None:
                return get_admin_money_issue_detail(db, money_issue_id=money_issue_id)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=build_admin_action_conflict_detail(integrity_exc),
            ) from integrity_exc
        failed_issue.latest_reason_code = f"admin_retry_credit_{retry_kind}_failed"
        failed_issue.latest_summary = str(exc)
        failed_issue.occurrence_count += 1
        failed_issue.last_detected_at = now
        failed_issue.updated_at = now
        append_money_issue_event(
            db,
            money_issue=failed_issue,
            event_type=f"credit_{retry_kind}_failed",
            event_source="admin",
            actor_user_id=admin_user.id,
            admin_action_id=failure_action.id,
            reason_code=failed_issue.latest_reason_code,
            summary=str(exc),
            occurred_at=now,
        )
        try:
            db.commit()
        except IntegrityError as integrity_exc:
            db.rollback()
            existing_action = get_existing_money_issue_action(
                db,
                admin_user_id=admin_user.id,
                money_issue_id=money_issue_id,
                action_type="retry_money_issue_credit",
                idempotency_key=idempotency_key,
            )
            if existing_action is not None:
                return get_admin_money_issue_detail(db, money_issue_id=money_issue_id)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=build_admin_action_conflict_detail(integrity_exc),
            ) from integrity_exc
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return get_admin_money_issue_detail(db, money_issue_id=money_issue.id)
