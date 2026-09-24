"""Admin money refund search, events, and detail projections."""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from backend.models import (
    AdminAction,
    AdminFinancialOutcome,
    Booking,
    DurableJob,
    Game,
    GameParticipant,
    HostPublishEntitlement,
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
    AdminMoneyRefundDetailItemRead,
    AdminMoneyRefundDetailRead,
    AdminMoneyRefundEventListResponseRead,
    AdminMoneyRefundJobDiagnosticRead,
    AdminMoneyRefundListRead,
    AdminMoneyRefundListResponseRead,
    AdminMoneyRefundProviderSnapshotRead,
)
from backend.services.admin_action_display_service import (
    admin_action_label,
    admin_label,
    reason_preview,
    users_by_id,
)
from backend.services.admin_action_policy import SENSITIVE_READ_ACTION_TYPES
from backend.services.admin_action_service import (
    load_frozen_audited_rows,
    record_sensitive_admin_read_batch,
    user_can_read_admin_action,
)
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
    list_payment_credit_grants,
    list_payment_credit_usages,
    load_by_id,
)
from backend.services.auth_service import require_active_admin_user
from backend.services.publish_fee_financial_policy import (
    publish_fee_prior_cash_attempts_are_incapable,
)
from backend.services.refund_attempt_policy import (
    refund_attempt_evidence_for_refunds,
    refund_attempt_identity_matches_refund,
    refund_attempt_statuses,
    refund_expected_attempts_are_terminal,
)
from backend.services.refund_retry_policy import evaluate_refund_retry_eligibility
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
    durable_job = get_current_exhausted_refund_job(db, refund)
    confirmed_returned_cents = confirmed_returned_by_payment(
        db, {refund.payment_id}
    ).get(refund.payment_id, 0)
    final_replacement_fee_ids = final_replacement_host_publish_fee_ids(
        db,
        {refund.host_publish_fee_id}
        if refund.host_publish_fee_id is not None
        else set(),
    )
    no_action_resolved_refund_ids = refund_ids_with_final_no_action_resolution(
        db, {refund.id}
    )
    return build_refund_summary_from_context(
        refund,
        payment=payment,
        booking=booking,
        game=game,
        payer=payer,
        linked_issue=linked_issues[0] if linked_issues else None,
        durable_job=durable_job,
        confirmed_returned_cents=confirmed_returned_cents,
        has_final_replacement=refund.host_publish_fee_id in final_replacement_fee_ids,
        has_final_no_action_resolution=refund.id in no_action_resolved_refund_ids,
    )


def build_refund_summary_from_context(
    refund: Refund,
    *,
    payment: Payment | None,
    booking: Booking | None,
    game: Game | None,
    payer: User | None,
    linked_issue: MoneyIssue | None,
    durable_job: DurableJob | None = None,
    confirmed_returned_cents: int = 0,
    has_final_replacement: bool = False,
    has_final_no_action_resolution: bool = False,
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
        current_attempt_number=refund.current_attempt_number,
        provider_attempt_started_at=refund.provider_attempt_started_at,
        automatic_mutation_blocked_reason=refund.automatic_mutation_blocked_reason,
        durable_job_diagnostic=(
            AdminMoneyRefundJobDiagnosticRead(
                status=durable_job.status,
                refund_attempt_number=refund.current_attempt_number,
                error_code=durable_job.last_error_code,
            )
            if refund_has_current_exhausted_diagnostic(
                refund,
                payment=payment,
                durable_job=durable_job,
                linked_issue=linked_issue,
                confirmed_returned_cents=confirmed_returned_cents,
                has_final_replacement=has_final_replacement,
                has_final_no_action_resolution=has_final_no_action_resolution,
            )
            else None
        ),
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
    confirmed_returned_cents_by_payment = confirmed_returned_by_payment(
        db, payment_ids
    )
    host_publish_fee_ids = {
        refund.host_publish_fee_id
        for refund in refunds
        if refund.host_publish_fee_id is not None
    }
    final_replacement_fee_ids = final_replacement_host_publish_fee_ids(
        db, host_publish_fee_ids
    )
    no_action_resolved_refund_ids = refund_ids_with_final_no_action_resolution(
        db, refund_ids
    )
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
        payment.payer_user_id for payment in payments.values() if payment is not None
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
    exhausted_job_by_refund_id: dict[uuid.UUID, DurableJob] = {}
    job_rows = list(
        db.scalars(
            select(DurableJob).where(
                DurableJob.job_type == "stripe_refund_fulfillment",
                DurableJob.payload_version == 1,
                DurableJob.status == "exhausted",
                DurableJob.origin_reference_type == "refund",
                DurableJob.origin_reference_id.in_(
                    [str(refund_id) for refund_id in refund_ids]
                ),
            )
        ).all()
    )
    for job in job_rows:
        try:
            refund_id = uuid.UUID(job.origin_reference_id or "")
        except ValueError:
            continue
        refund = next((row for row in refunds if row.id == refund_id), None)
        if (
            refund is not None
            and job.idempotency_key == refund.stripe_request_key
            and job.protected_identity
            == {
                "refund_id": str(refund.id),
                "attempt_number": refund.current_attempt_number,
            }
        ):
            exhausted_job_by_refund_id[refund.id] = job
    issue_statement = select(MoneyIssue).where(
        MoneyIssue.target_refund_id.in_(refund_ids)
    )
    if linked_issue_status is not None:
        issue_statement = issue_statement.where(
            MoneyIssue.status == linked_issue_status
        )
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
                durable_job=exhausted_job_by_refund_id.get(refund.id),
                confirmed_returned_cents=confirmed_returned_cents_by_payment.get(
                    refund.payment_id, 0
                ),
                has_final_replacement=(
                    refund.host_publish_fee_id in final_replacement_fee_ids
                ),
                has_final_no_action_resolution=(
                    refund.id in no_action_resolved_refund_ids
                ),
            )
        )
    return summaries


def refund_has_current_exhausted_diagnostic(
    refund: Refund,
    *,
    payment: Payment | None,
    durable_job: DurableJob | None,
    linked_issue: MoneyIssue | None,
    confirmed_returned_cents: int,
    has_final_replacement: bool,
    has_final_no_action_resolution: bool,
) -> bool:
    if not (
        durable_job is not None
        and durable_job.status == "exhausted"
        and durable_job.idempotency_key == refund.stripe_request_key
        and durable_job.protected_identity
        == {
            "refund_id": str(refund.id),
            "attempt_number": refund.current_attempt_number,
        }
    ):
        return False
    if (
        (linked_issue is not None and linked_issue.status == "open")
        or has_final_replacement
        or has_final_no_action_resolution
    ):
        return False
    if (
        refund.automatic_mutation_blocked_reason is not None
        or refund.refund_status == "processing"
        or refund.provider_status == "unknown"
    ):
        return True
    return bool(
        refund.refund_status in {"failed", "cancelled"}
        and (
            payment is None
            or confirmed_returned_cents < payment.amount_cents
        )
    )


def refund_ids_with_final_no_action_resolution(
    db: Session,
    refund_ids: set[uuid.UUID],
) -> set[uuid.UUID]:
    if not refund_ids:
        return set()
    return set(
        db.scalars(
            select(MoneyIssue.target_refund_id).where(
                MoneyIssue.target_refund_id.in_(refund_ids),
                MoneyIssue.status == "resolved",
                MoneyIssue.resolution_reason_code
                == "provider_completed_no_action_required",
            )
        ).all()
    )


def confirmed_returned_by_payment(
    db: Session, payment_ids: set[uuid.UUID]
) -> dict[uuid.UUID, int]:
    if not payment_ids:
        return {}
    refunds = list(
        db.scalars(select(Refund).where(Refund.payment_id.in_(payment_ids))).all()
    )
    evidence = refund_attempt_evidence_for_refunds(
        db, (refund.id for refund in refunds)
    )
    totals = {payment_id: 0 for payment_id in payment_ids}
    for refund in refunds:
        totals[refund.payment_id] += sum(
            attempt.amount_cents
            for attempt_number, attempt in evidence.get(refund.id, {}).items()
            if attempt.status == "succeeded"
            and refund_attempt_identity_matches_refund(
                refund,
                attempt_number=attempt_number,
                attempt=attempt,
            )
        )
    return totals


def final_replacement_host_publish_fee_ids(
    db: Session, host_publish_fee_ids: set[uuid.UUID]
) -> set[uuid.UUID]:
    if not host_publish_fee_ids:
        return set()
    valid_credit_exists = (
        select(HostPublishEntitlement.id)
        .where(
            HostPublishEntitlement.id
            == AdminFinancialOutcome.host_publish_entitlement_id,
            HostPublishEntitlement.host_user_id
            == AdminFinancialOutcome.host_user_id,
            HostPublishEntitlement.entitlement_type == "refund_replacement",
            HostPublishEntitlement.source == "financial_outcome",
            HostPublishEntitlement.source_financial_outcome_id
            == AdminFinancialOutcome.id,
            HostPublishEntitlement.status != "revoked",
        )
        .exists()
    )
    rows = list(db.scalars(
        select(AdminFinancialOutcome)
        .join(
            HostPublishFee,
            HostPublishFee.id == AdminFinancialOutcome.host_publish_fee_id,
        )
        .where(
            AdminFinancialOutcome.host_publish_fee_id.in_(host_publish_fee_ids),
            AdminFinancialOutcome.applied_status == "applied",
            or_(
                AdminFinancialOutcome.outcome == "forfeit",
                and_(
                    AdminFinancialOutcome.outcome == "credit",
                    valid_credit_exists,
                ),
                AdminFinancialOutcome.outcome == "refund",
            ),
            AdminFinancialOutcome.amount_cents == HostPublishFee.amount_cents,
            AdminFinancialOutcome.currency == HostPublishFee.currency,
        )
    ).all())
    refund_rows = {
        refund.id: refund
        for refund in db.scalars(
            select(Refund).where(
                Refund.id.in_(
                    [row.refund_id for row in rows if row.refund_id is not None]
                )
            )
        ).all()
    }
    refund_evidence = refund_attempt_evidence_for_refunds(
        db, refund_rows.keys()
    )
    final_ids: set[uuid.UUID] = set()
    for row in rows:
        if row.host_publish_fee_id is None:
            continue
        if row.outcome == "refund":
            refund = refund_rows.get(row.refund_id)
            if (
                refund is None
                or refund.automatic_mutation_blocked_reason is not None
                or not refund_expected_attempts_are_terminal(db, refund)
            ):
                continue
            returned_cents = sum(
                attempt.amount_cents
                for attempt_number, attempt in refund_evidence.get(
                    refund.id, {}
                ).items()
                if attempt.status == "succeeded"
                and refund_attempt_identity_matches_refund(
                    refund,
                    attempt_number=attempt_number,
                    attempt=attempt,
                )
            )
            if returned_cents < row.amount_cents:
                continue
        if publish_fee_prior_cash_attempts_are_incapable(
            db,
            host_publish_fee_id=row.host_publish_fee_id,
            excluding_refund_id=row.refund_id,
        ):
            final_ids.add(row.host_publish_fee_id)
    return final_ids


def get_current_exhausted_refund_job(
    db: Session, refund: Refund
) -> DurableJob | None:
    job = db.scalars(
        select(DurableJob)
        .where(
            DurableJob.job_type == "stripe_refund_fulfillment",
            DurableJob.payload_version == 1,
            DurableJob.status == "exhausted",
            DurableJob.origin_reference_type == "refund",
            DurableJob.origin_reference_id == str(refund.id),
            DurableJob.idempotency_key == refund.stripe_request_key,
        )
        .order_by(DurableJob.created_at.desc(), DurableJob.id.desc())
        .limit(1)
    ).first()
    return job


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
    authenticated_admin_id: uuid.UUID,
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
    cursor_context = {
        "kind": "admin_money_refunds",
        "payment_id": str(payment_id) if payment_id is not None else None,
        "query": normalized_query,
        "refund_status": refund_status,
        "user_id": str(user_id) if user_id is not None else None,
    }
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

    query = apply_desc_cursor(
        query,
        Refund,
        Refund.created_at,
        cursor,
        context=cursor_context,
    )

    page_rows = list(
        db.execute(
            query.with_only_columns(Refund.id, Refund.created_at)
            .order_by(Refund.created_at.desc(), Refund.id.desc())
            .limit(limit + 1)
        ).all()
    )
    selected_ids = [row.id for row in page_rows[:limit]]
    if selected_ids:
        record_sensitive_admin_read_batch(
            authenticated_admin_id=authenticated_admin_id,
            action_type="read_admin_money_refund_list_item",
            target_ids=selected_ids,
        )
    refunds = load_frozen_audited_rows(db, model=Refund, target_ids=selected_ids)
    return AdminMoneyRefundListResponseRead(
        items=build_refund_summaries(
            db,
            refunds,
            linked_issue_status="open",
        ),
        has_more=page_has_more(page_rows, limit=limit),
        next_cursor=next_cursor_for_rows(
            page_rows,
            limit=limit,
            sort_attr="created_at",
            context=cursor_context,
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
    cursor_context = {
        "event_source": event_source,
        "event_type": event_type,
        "kind": "admin_money_refund_events",
        "refund_id": str(refund_id),
    }
    statement = apply_desc_cursor(
        statement,
        RefundEvent,
        RefundEvent.occurred_at,
        cursor,
        context=cursor_context,
    )
    rows = list(
        db.scalars(
            statement.order_by(
                RefundEvent.occurred_at.desc(), RefundEvent.id.desc()
            ).limit(limit + 1)
        ).all()
    )
    return AdminMoneyRefundEventListResponseRead(
        items=rows[:limit],
        has_more=page_has_more(rows, limit=limit),
        next_cursor=next_cursor_for_rows(
            rows,
            limit=limit,
            sort_attr="occurred_at",
            context=cursor_context,
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


def build_refund_provider_snapshot(
    refund: Refund,
) -> AdminMoneyRefundProviderSnapshotRead:
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
    require_active_admin_user(viewer_user)
    filters = [AdminAction.target_refund_id == refund.id]
    if linked_money_issue is not None:
        filters.append(AdminAction.target_money_issue_id == linked_money_issue.id)

    actions = db.scalars(
        select(AdminAction)
        .where(
            or_(*filters),
            AdminAction.action_type.not_in(SENSITIVE_READ_ACTION_TYPES),
        )
        .order_by(AdminAction.created_at.desc(), AdminAction.id.desc())
        .limit(ADMIN_MONEY_DETAIL_RELATED_LIMIT)
    ).all()
    return [
        action for action in actions if user_can_read_admin_action(viewer_user, action)
    ]


def refund_available_actions(
    db: Session,
    *,
    refund: Refund,
    payment: Payment | None,
    linked_money_issue: MoneyIssue | None = None,
) -> list[AdminMoneyRefundActionRead]:
    retry_eligibility = evaluate_refund_retry_eligibility(
        db, refund=refund, payment=payment
    )
    retry_blockers = [blocker.message for blocker in retry_eligibility.blockers]
    if retry_eligibility.no_action_required:
        retry_blockers.append(
            "No refundable cash remains; review the linked Money Issue as no action."
        )

    check_provider_blockers: list[str] = []
    if (
        refund.refund_status == "succeeded"
        and refund_expected_attempts_are_terminal(db, refund)
        and refund_attempt_statuses(db, refund.id).get(
            refund.current_attempt_number
        )
        == "succeeded"
    ):
        check_provider_blockers.append("Refund already succeeded.")
    elif (
        refund.provider_refund_id
        or refund.provider_status in {"processing", "unknown"}
        or refund.refund_status == "processing"
    ):
        pass
    else:
        check_provider_blockers.append(
            "Refund has no provider state that can be checked."
        )

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
    require_active_admin_user(viewer_user)
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
        build_payment_summary(db, payment, detail=True) if payment is not None else None
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

    admin_users = users_by_id(
        db,
        sorted({action.admin_user_id for action in admin_activity}, key=str),
    )

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
            AdminMoneyGameContextRead.model_validate(game) if game is not None else None
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
            AdminMoneyAuditActionSummaryRead(
                id=action.id,
                action_label=admin_action_label(action.action_type),
                admin_label=admin_label(
                    admin_users.get(action.admin_user_id),
                    fallback_admin_id=action.admin_user_id,
                ),
                reason_preview=reason_preview(action.reason),
                created_at=action.created_at,
            )
            for action in admin_activity
        ],
        linked_money_issue=linked_money_issue,
        available_actions=refund_available_actions(
            db,
            refund=refund,
            payment=payment,
            linked_money_issue=linked_money_issue,
        ),
    )
