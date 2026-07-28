"""Admin money refund search, events, and detail projections."""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from backend.models import (
    AdminAction,
    Booking,
    Game,
    GameParticipant,
    HostPublishFee,
    MoneyIssue,
    Payment,
    Refund,
    RefundEvent,
    User,
)
from backend.schemas.admin_money_context_schema import (
    AdminMoneyAuditActionSummaryRead,
    AdminMoneyBookingContextRead,
    AdminMoneyGameContextRead,
    AdminMoneyHostPublishFeeContextRead,
    AdminMoneyParticipantContextRead,
    AdminMoneyPaymentUserContextRead,
)
from backend.schemas.admin_money_refund_schema import (
    AdminMoneyRefundActionRead,
    AdminMoneyRefundCreditContextRead,
    AdminMoneyRefundDetailRead,
    AdminMoneyRefundDetailItemRead,
    AdminMoneyRefundEventListResponseRead,
    AdminMoneyRefundListRead,
    AdminMoneyRefundListResponseRead,
    AdminMoneyRefundProviderSnapshotRead,
)
from backend.services.admin_action_service import user_can_read_admin_action
from backend.services.admin_money_cursor import (
    apply_desc_cursor,
    next_cursor_for_rows,
    page_has_more,
)
from backend.services.admin_money_display import admin_money_display, compact_id
from backend.services.admin_money_issue_query_service import list_related_money_issues
from backend.services.admin_money_payment_service import (
    build_payment_summary,
    get_payment_game,
    load_by_id,
    list_payment_credit_grants,
    list_payment_credit_usages,
)
from backend.services.admin_money_refund_rules import (
    RETRYABLE_PAYMENT_STATUSES,
    RETRYABLE_REFUND_STATUSES,
    UNCERTAIN_PROVIDER_REFUND_STATUSES,
)
from backend.services.refund_service import VALID_REFUND_STATUSES


ADMIN_MONEY_DETAIL_RELATED_LIMIT = 100
ADMIN_MONEY_REFUND_STATUSES = VALID_REFUND_STATUSES | {"all"}


def get_refund_or_404(db: Session, refund_id: uuid.UUID) -> Refund:
    refund = db.get(Refund, refund_id)
    if refund is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refund not found.",
        )
    return refund


def build_refund_summary(db: Session, refund: Refund) -> AdminMoneyRefundListRead:
    payment = db.get(Payment, refund.payment_id)
    booking = get_refund_booking(db, refund=refund, payment=payment)
    game = (
        get_payment_game(db, payment=payment, booking=booking)
        if payment is not None
        else None
    )
    payer = db.get(User, payment.payer_user_id) if payment is not None else None
    linked_issues = list_related_money_issues(
        db,
        refund_id=refund.id,
        status_filter="open",
        limit=1,
    )
    context_label = None
    if booking is not None:
        context_label = f"Booking {compact_id(booking.id)}"
    elif refund.host_publish_fee_id is not None:
        context_label = f"Publish fee {compact_id(refund.host_publish_fee_id)}"

    return AdminMoneyRefundListRead(
        id=refund.id,
        payment_id=refund.payment_id,
        booking_id=refund.booking_id,
        participant_id=refund.participant_id,
        host_publish_fee_id=refund.host_publish_fee_id,
        game_id=game.id if game is not None else None,
        target_user_id=payment.payer_user_id if payment is not None else None,
        origin_workflow=refund.origin_workflow,
        provider=refund.provider,
        provider_refund_id=refund.provider_refund_id,
        provider_charge_id=refund.provider_charge_id,
        provider_status=refund.provider_status,
        provider_status_observed_at=refund.provider_status_observed_at,
        amount_cents=refund.amount_cents,
        currency=refund.currency,
        refund_reason=refund.refund_reason,
        refund_status=refund.refund_status,
        requested_by_user_id=refund.requested_by_user_id,
        approved_by_user_id=refund.approved_by_user_id,
        requested_at=refund.requested_at,
        approved_at=refund.approved_at,
        refunded_at=refund.refunded_at,
        last_refund_event_at=refund.last_refund_event_at,
        linked_issue=linked_issues[0] if linked_issues else None,
        display=admin_money_display(
            user=payer,
            game=game,
            context_label=context_label,
            payment_id=refund.payment_id,
            refund_id=refund.id,
        ),
        created_at=refund.created_at,
        updated_at=refund.updated_at,
    )


def build_refund_summary_from_context(
    refund: Refund,
    *,
    payment: Payment | None,
    booking: Booking | None,
    game: Game | None,
    payer: User | None,
    linked_issue: MoneyIssue | None,
) -> AdminMoneyRefundListRead:
    context_label = None
    if booking is not None:
        context_label = f"Booking {compact_id(booking.id)}"
    elif refund.host_publish_fee_id is not None:
        context_label = f"Publish fee {compact_id(refund.host_publish_fee_id)}"

    return AdminMoneyRefundListRead(
        id=refund.id,
        payment_id=refund.payment_id,
        booking_id=refund.booking_id,
        participant_id=refund.participant_id,
        host_publish_fee_id=refund.host_publish_fee_id,
        game_id=game.id if game is not None else None,
        target_user_id=payment.payer_user_id if payment is not None else None,
        origin_workflow=refund.origin_workflow,
        provider=refund.provider,
        provider_refund_id=refund.provider_refund_id,
        provider_charge_id=refund.provider_charge_id,
        provider_status=refund.provider_status,
        provider_status_observed_at=refund.provider_status_observed_at,
        amount_cents=refund.amount_cents,
        currency=refund.currency,
        refund_reason=refund.refund_reason,
        refund_status=refund.refund_status,
        requested_by_user_id=refund.requested_by_user_id,
        approved_by_user_id=refund.approved_by_user_id,
        requested_at=refund.requested_at,
        approved_at=refund.approved_at,
        refunded_at=refund.refunded_at,
        last_refund_event_at=refund.last_refund_event_at,
        linked_issue=linked_issue,
        display=admin_money_display(
            user=payer,
            game=game,
            context_label=context_label,
            payment_id=refund.payment_id,
            refund_id=refund.id,
        ),
        created_at=refund.created_at,
        updated_at=refund.updated_at,
    )


def build_refund_summaries(
    db: Session,
    refunds: list[Refund],
    *,
    linked_issue_status: str | None = "open",
) -> list[AdminMoneyRefundListRead]:
    if not refunds:
        return []
    refund_ids = {refund.id for refund in refunds}
    payment_ids = {refund.payment_id for refund in refunds}
    payments = load_by_id(db, Payment, payment_ids)
    booking_ids = {
        refund.booking_id for refund in refunds if refund.booking_id is not None
    }
    booking_ids.update(
        payment.booking_id
        for payment in payments.values()
        if payment is not None and payment.booking_id is not None
    )
    bookings = load_by_id(db, Booking, booking_ids)
    payer_ids = {
        payment.payer_user_id
        for payment in payments.values()
        if payment is not None
    }
    users = load_by_id(db, User, payer_ids)
    game_ids = {
        payment.game_id
        for payment in payments.values()
        if payment is not None and payment.game_id is not None
    }
    game_ids.update(
        booking.game_id for booking in bookings.values() if booking is not None
    )
    games = load_by_id(db, Game, game_ids)

    linked_issue_by_refund_id: dict[uuid.UUID, MoneyIssue] = {}
    issue_statement = select(MoneyIssue).where(
        MoneyIssue.target_refund_id.in_(refund_ids)
    )
    if linked_issue_status is not None:
        issue_statement = issue_statement.where(MoneyIssue.status == linked_issue_status)
    issue_rows = list(
        db.scalars(
            issue_statement.order_by(
                MoneyIssue.last_activity_at.desc(),
                MoneyIssue.id.desc(),
            )
        ).all()
    )
    for issue in issue_rows:
        if (
            issue.target_refund_id is not None
            and issue.target_refund_id not in linked_issue_by_refund_id
        ):
            linked_issue_by_refund_id[issue.target_refund_id] = issue

    summaries = []
    for refund in refunds:
        payment = payments.get(refund.payment_id)
        booking_id = refund.booking_id or (
            payment.booking_id if payment is not None else None
        )
        booking = bookings.get(booking_id) if booking_id is not None else None
        game_id = (
            payment.game_id
            if payment is not None and payment.game_id is not None
            else (booking.game_id if booking is not None else None)
        )
        payer = users.get(payment.payer_user_id) if payment is not None else None
        summaries.append(
            build_refund_summary_from_context(
                refund,
                payment=payment,
                booking=booking,
                game=games.get(game_id) if game_id is not None else None,
                payer=payer,
                linked_issue=linked_issue_by_refund_id.get(refund.id),
            )
        )
    return summaries


def validate_admin_money_refund_status(refund_status: str) -> None:
    if refund_status not in ADMIN_MONEY_REFUND_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="refund_status is not supported.",
        )


def parse_refund_query_uuid(query_text: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(query_text)
    except (TypeError, ValueError):
        return None


def list_admin_money_refunds(
    db: Session,
    *,
    user_id: uuid.UUID | None = None,
    refund_status: str = "all",
    payment_id: uuid.UUID | None = None,
    query_text: str | None = None,
    limit: int = 50,
    cursor: str | None = None,
) -> AdminMoneyRefundListResponseRead:
    validate_admin_money_refund_status(refund_status)

    query = (
        select(Refund)
        .join(Payment, Refund.payment_id == Payment.id)
        .outerjoin(
            Booking,
            Booking.id == func.coalesce(Refund.booking_id, Payment.booking_id),
        )
        .outerjoin(User, Payment.payer_user_id == User.id)
    )
    if user_id is not None:
        query = query.where(Payment.payer_user_id == user_id)
    if refund_status != "all":
        query = query.where(Refund.refund_status == refund_status)
    if payment_id is not None:
        query = query.where(Refund.payment_id == payment_id)

    normalized_query = " ".join((query_text or "").strip().split())
    if normalized_query:
        query_uuid = parse_refund_query_uuid(normalized_query)
        text_filters = []
        if query_uuid is not None:
            text_filters.extend(
                [
                    Refund.id == query_uuid,
                    Refund.payment_id == query_uuid,
                    Refund.booking_id == query_uuid,
                    Refund.participant_id == query_uuid,
                    Refund.host_publish_fee_id == query_uuid,
                    Payment.payer_user_id == query_uuid,
                    Payment.booking_id == query_uuid,
                ]
            )
        elif normalized_query.startswith("re_"):
            text_filters.append(Refund.provider_refund_id == normalized_query)
        elif normalized_query.startswith("ch_"):
            text_filters.extend(
                [
                    Refund.provider_charge_id == normalized_query,
                    Payment.provider_charge_id == normalized_query,
                ]
            )
        else:
            prefix_query = f"{normalized_query}%"
            text_filters.extend(
                [
                    User.email.ilike(prefix_query),
                    User.first_name.ilike(prefix_query),
                    User.last_name.ilike(prefix_query),
                ]
            )
            name_parts = normalized_query.split()
            if len(name_parts) >= 2:
                text_filters.append(
                    and_(
                        User.first_name.ilike(f"{name_parts[0]}%"),
                        User.last_name.ilike(f"{name_parts[-1]}%"),
                    )
                )
        query = query.where(or_(*text_filters))

    query = apply_desc_cursor(query, Refund, Refund.created_at, cursor)

    refunds = list(
        db.scalars(
            query.order_by(Refund.created_at.desc(), Refund.id.desc()).limit(limit + 1)
        ).all()
    )
    return AdminMoneyRefundListResponseRead(
        items=build_refund_summaries(
            db,
            refunds[:limit],
            linked_issue_status="open",
        ),
        has_more=page_has_more(refunds, limit=limit),
        next_cursor=next_cursor_for_rows(
            refunds,
            limit=limit,
            sort_attr="created_at",
        ),
    )


def list_refund_events(
    db: Session,
    refund_id: uuid.UUID,
    *,
    event_type: str | None = None,
    event_source: str | None = None,
    limit: int = 50,
    cursor: str | None = None,
) -> AdminMoneyRefundEventListResponseRead:
    if db.get(Refund, refund_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refund not found.",
        )
    statement = select(RefundEvent).where(RefundEvent.refund_id == refund_id)
    if event_type is not None:
        statement = statement.where(RefundEvent.event_type == event_type)
    if event_source is not None:
        statement = statement.where(RefundEvent.event_source == event_source)
    statement = apply_desc_cursor(statement, RefundEvent, RefundEvent.occurred_at, cursor)
    rows = list(
        db.scalars(
            statement
            .order_by(RefundEvent.occurred_at.desc(), RefundEvent.id.desc())
            .limit(limit + 1)
        ).all()
    )
    return AdminMoneyRefundEventListResponseRead(
        items=rows[:limit],
        has_more=page_has_more(rows, limit=limit),
        next_cursor=next_cursor_for_rows(
            rows,
            limit=limit,
            sort_attr="occurred_at",
        ),
    )


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


def get_refund_participant(db: Session, refund: Refund) -> GameParticipant | None:
    if refund.participant_id is None:
        return None
    return db.get(GameParticipant, refund.participant_id)


def get_refund_host_publish_fee(db: Session, refund: Refund) -> HostPublishFee | None:
    if refund.host_publish_fee_id is None:
        return None
    return db.get(HostPublishFee, refund.host_publish_fee_id)


def build_refund_provider_snapshot(refund: Refund) -> AdminMoneyRefundProviderSnapshotRead:
    return AdminMoneyRefundProviderSnapshotRead(
        provider=refund.provider,
        provider_status=refund.provider_status,
        provider_status_observed_at=refund.provider_status_observed_at,
        provider_refund_id=refund.provider_refund_id,
        provider_charge_id=refund.provider_charge_id,
    )


def list_refund_admin_activity(
    db: Session,
    *,
    viewer_user: User,
    refund: Refund,
    linked_money_issue: MoneyIssue | None,
) -> list[AdminAction]:
    filters = [AdminAction.target_refund_id == refund.id]
    if linked_money_issue is not None:
        filters.append(AdminAction.target_money_issue_id == linked_money_issue.id)

    actions = db.scalars(
        select(AdminAction)
        .where(or_(*filters))
        .order_by(AdminAction.created_at.desc(), AdminAction.id.desc())
        .limit(ADMIN_MONEY_DETAIL_RELATED_LIMIT)
    ).all()
    return [
        action
        for action in actions
        if user_can_read_admin_action(viewer_user, action)
    ]


def refund_available_actions(
    *,
    refund: Refund,
    payment: Payment | None,
    linked_money_issue: MoneyIssue | None = None,
) -> list[AdminMoneyRefundActionRead]:
    retry_blockers: list[str] = []
    if refund.refund_status not in RETRYABLE_REFUND_STATUSES:
        retry_blockers.append("Refund is not failed or cancelled.")
    if refund.provider_status in UNCERTAIN_PROVIDER_REFUND_STATUSES:
        retry_blockers.append("Refund provider outcome is still uncertain.")
    if payment is None:
        retry_blockers.append("Payment context is missing.")
    elif payment.payment_status not in RETRYABLE_PAYMENT_STATUSES:
        retry_blockers.append("Payment did not succeed.")
    elif payment.paid_at is None:
        retry_blockers.append("Payment was not marked paid.")
    elif not payment.provider_charge_id:
        retry_blockers.append("Payment is missing provider charge id.")

    check_provider_blockers: list[str] = []
    if refund.refund_status == "succeeded":
        check_provider_blockers.append("Refund already succeeded.")
    elif (
        refund.provider_refund_id
        or refund.provider_status in {"processing", "unknown"}
        or refund.refund_status == "processing"
    ):
        pass
    else:
        check_provider_blockers.append("Refund has no provider state that can be checked.")

    open_provider_blockers: list[str] = []
    if not refund.provider_refund_id:
        open_provider_blockers.append("Refund is missing provider refund id.")

    open_issue_blockers: list[str] = []
    if linked_money_issue is None:
        open_issue_blockers.append("No linked Money Issue exists.")

    return [
        AdminMoneyRefundActionRead(
            action_code="retry_refund",
            enabled=not retry_blockers,
            blockers=retry_blockers,
            confirmation_text="Retry this refund through Stripe.",
        ),
        AdminMoneyRefundActionRead(
            action_code="check_provider_status",
            enabled=not check_provider_blockers,
            blockers=check_provider_blockers,
            confirmation_text="Check Stripe for the latest refund status.",
        ),
        AdminMoneyRefundActionRead(
            action_code="open_provider_reference",
            enabled=not open_provider_blockers,
            blockers=open_provider_blockers,
            confirmation_text="Open the provider refund reference.",
        ),
        AdminMoneyRefundActionRead(
            action_code="open_money_issue",
            enabled=not open_issue_blockers,
            blockers=open_issue_blockers,
            confirmation_text="Open the linked Money Issue.",
        ),
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
    payer = db.get(User, payment.payer_user_id) if payment is not None else None
    participant = get_refund_participant(db, refund)
    host_publish_fee = get_refund_host_publish_fee(db, refund)
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
    linked_issues = list_related_money_issues(
        db,
        refund_id=refund.id,
        limit=1,
    )
    linked_money_issue = linked_issues[0] if linked_issues else None
    payment_summary = (
        build_payment_summary(db, payment, detail=True)
        if payment is not None
        else None
    )
    recent_refund_events = list_refund_events(
        db,
        refund.id,
        limit=ADMIN_MONEY_DETAIL_RELATED_LIMIT,
    ).items
    admin_activity = list_refund_admin_activity(
        db,
        viewer_user=viewer_user,
        refund=refund,
        linked_money_issue=linked_money_issue,
    )

    refund_summary = build_refund_summary(db, refund)

    return AdminMoneyRefundDetailRead(
        refund=AdminMoneyRefundDetailItemRead(**refund_summary.model_dump()),
        current_provider_snapshot=build_refund_provider_snapshot(refund),
        payment_summary=payment_summary,
        user_summary=(
            AdminMoneyPaymentUserContextRead.model_validate(payer)
            if payer is not None
            else None
        ),
        booking_summary=(
            AdminMoneyBookingContextRead.model_validate(booking)
            if booking is not None
            else None
        ),
        participant_summary=(
            AdminMoneyParticipantContextRead.model_validate(participant)
            if participant is not None
            else None
        ),
        game_summary=(
            AdminMoneyGameContextRead.model_validate(game)
            if game is not None
            else None
        ),
        publish_fee_summary=(
            AdminMoneyHostPublishFeeContextRead.model_validate(host_publish_fee)
            if host_publish_fee is not None
            else None
        ),
        credit_context=AdminMoneyRefundCreditContextRead(
            credit_grants=credit_grants,
            credit_usages=credit_usages,
        ),
        recent_refund_events=recent_refund_events,
        admin_activity=[
            AdminMoneyAuditActionSummaryRead.model_validate(action)
            for action in admin_activity
        ],
        linked_money_issue=linked_money_issue,
        available_actions=refund_available_actions(
            refund=refund,
            payment=payment,
            linked_money_issue=linked_money_issue,
        ),
    )
