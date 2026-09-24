"""Admin money refund retry and reconciliation workflows."""

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import (
    AdminAction,
    AdminFinancialOutcome,
    Booking,
    Game,
    HostPublishFee,
    MoneyIssue,
    Payment,
    PaymentCompensation,
    Refund,
    RefundEvent,
    User,
)
from backend.observability.timeouts import PublicTimeoutError
from backend.schemas.admin_money_refund_schema import (
    AdminMoneyRefundDetailRead,
    AdminMoneyRefundReconcileCreate,
    AdminMoneyRefundRetryCreate,
)
from backend.services.admin_action_service import (
    build_admin_action_conflict_detail,
    record_admin_action,
)
from backend.services.admin_money_issue_query_service import list_related_money_issues
from backend.services.admin_money_issue_service import (
    append_money_issue_event,
    refund_issue_action_under_publish_fee_policy,
    stage_refund_money_issue,
)
from backend.services.admin_money_refund_query_service import (
    get_admin_money_refund_detail,
)
from backend.services.admin_money_refund_rules import REFUND_PROCESSING_OVERDUE_AFTER
from backend.services.admin_record_rules import (
    normalize_idempotency_key,
    normalize_optional_text,
)
from backend.services.game_notification_service import (
    create_or_reopen_booking_refunded_notification,
    refund_notice_context_for,
)
from backend.services.payment_job_service import build_production_job_registry
from backend.services.refund_attempt_policy import (
    authoritative_succeeded_amount_for_refunds,
    canonical_provider_attempt_event,
    reduce_refund_attempt_evidence,
    refund_attempt_identity_matches_refund,
    refund_attempt_statuses,
    refund_event_has_authoritative_provider_observation,
    refund_expected_attempts_are_terminal,
)
from backend.services.refund_event_service import (
    get_refund_event_by_idempotency_key,
    record_refund_event,
)
from backend.services.refund_fulfillment_service import (
    enqueue_refund_fulfillment_job,
    lock_refund_financial_context,
    refund_attempt_key,
)
from backend.services.refund_retry_policy import (
    RefundRetryEligibility,
    evaluate_refund_retry_eligibility,
)
from backend.services.refund_service import (
    build_refund_conflict_detail,
    get_refund_payment_ledger,
    refund_audit_metadata,
)
from backend.services.stripe_service import (
    StripeConfigError,
    StripeRefundOperationError,
)
from backend.services.stripe_service import (
    retrieve_refund as retrieve_stripe_refund,
)

ADMIN_REFUND_RETRY_PROVIDER_RESULT_RECORDING_FAILED_DETAIL = (
    "Stripe returned a refund result, but local refund state could not be fully "
    "recorded. Use refund reconciliation before retrying."
)


def normalize_retry_reason(value: str) -> str:
    reason = normalize_optional_text(value, "reason")
    if reason is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="reason is required.",
        )
    return reason


def normalize_retry_idempotency_key(value: str) -> str:
    idempotency_key = normalize_idempotency_key(value)
    if idempotency_key is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="idempotency_key is required.",
        )
    return idempotency_key


def get_existing_retry_action(
    db: Session,
    *,
    admin_user_id: uuid.UUID,
    refund_id: uuid.UUID,
    idempotency_key: str,
) -> AdminAction | None:
    actions = db.scalars(
        select(AdminAction)
        .where(
            AdminAction.admin_user_id == admin_user_id,
            AdminAction.action_type == "update_refund",
            AdminAction.target_refund_id == refund_id,
            AdminAction.idempotency_key == idempotency_key,
        )
        .order_by(AdminAction.created_at.desc(), AdminAction.id.desc())
        .limit(10)
    ).all()

    for action in actions:
        metadata = action.metadata_ or {}
        if metadata.get("source") == "admin_money_refund_retry":
            return action

    return None


def get_existing_reconcile_action(
    db: Session,
    *,
    admin_user_id: uuid.UUID,
    refund_id: uuid.UUID,
    idempotency_key: str,
) -> AdminAction | None:
    return db.scalars(
        select(AdminAction)
        .where(
            AdminAction.admin_user_id == admin_user_id,
            AdminAction.action_type == "reconcile_refund",
            AdminAction.target_refund_id == refund_id,
            AdminAction.idempotency_key == idempotency_key,
        )
        .order_by(AdminAction.created_at.desc(), AdminAction.id.desc())
    ).first()


def require_reconcile_replay_matches(
    action: AdminAction,
    *,
    reason: str,
    provider_refund_id: str | None,
) -> None:
    metadata = action.metadata_ or {}
    request_identity = metadata.get("request_identity") or {}
    if (
        request_identity.get("reason") != reason
        or request_identity.get("provider_refund_id") != provider_refund_id
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Idempotency key conflicts with another reconciliation request.",
        )


def get_refund_for_retry_or_404(db: Session, refund_id: uuid.UUID) -> Refund:
    reference = db.get(Refund, refund_id)
    if reference is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refund not found.",
        )
    if reference.host_publish_fee_id is not None:
        refunds = list(
            db.scalars(
                select(Refund)
                .where(
                    Refund.host_publish_fee_id == reference.host_publish_fee_id
                )
                .order_by(Refund.id.asc())
                .with_for_update()
            ).all()
        )
    else:
        refunds = list(
            db.scalars(
                select(Refund).where(Refund.id == refund_id).with_for_update()
            ).all()
        )
    refund = next((row for row in refunds if row.id == refund_id), None)

    if refund is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refund not found.",
        )

    refund_ids = [row.id for row in refunds]
    list(
        db.scalars(
            select(AdminFinancialOutcome)
            .where(
                AdminFinancialOutcome.host_publish_fee_id
                == refund.host_publish_fee_id
                if refund.host_publish_fee_id is not None
                else AdminFinancialOutcome.refund_id == refund.id
            )
            .order_by(AdminFinancialOutcome.id.asc())
            .with_for_update()
        ).all()
    )
    list(
        db.scalars(
            select(MoneyIssue)
            .where(MoneyIssue.target_refund_id.in_(refund_ids))
            .order_by(MoneyIssue.id.asc())
            .with_for_update()
        ).all()
    )
    return refund


def get_payment_for_retry_or_404(db: Session, payment_id: uuid.UUID) -> Payment:
    payment = db.scalars(
        select(Payment).where(Payment.id == payment_id).with_for_update()
    ).first()

    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found.",
        )

    return payment


def get_booking_for_retry(db: Session, booking_id: uuid.UUID | None) -> Booking | None:
    if booking_id is None:
        return None

    return db.scalars(
        select(Booking).where(Booking.id == booking_id).with_for_update()
    ).first()


def get_host_publish_fee_for_retry(
    db: Session,
    host_publish_fee_id: uuid.UUID | None,
) -> HostPublishFee | None:
    if host_publish_fee_id is None:
        return None

    return db.scalars(
        select(HostPublishFee)
        .where(HostPublishFee.id == host_publish_fee_id)
        .with_for_update()
    ).first()


def get_refund_processing_started_at(
    db: Session, refund: Refund
) -> datetime | None:
    if refund.current_attempt_number > 0:
        return refund.provider_attempt_started_at
    first_processing_event_at = db.scalar(
        select(func.min(RefundEvent.occurred_at)).where(
            RefundEvent.refund_id == refund.id,
            RefundEvent.attempt_number == 0,
            RefundEvent.event_type.in_({"provider_result_recorded", "reconciliation_checked"}),
            RefundEvent.provider == "stripe",
            RefundEvent.provider_refund_id.is_not(None),
            RefundEvent.provider_status == "processing",
            RefundEvent.new_refund_status == "processing",
        )
    )
    return first_processing_event_at


def refund_processing_threshold_reached(
    db: Session,
    *,
    refund: Refund,
    now: datetime,
) -> bool:
    processing_started_at = get_refund_processing_started_at(db, refund)
    return bool(
        processing_started_at is not None
        and processing_started_at <= now - REFUND_PROCESSING_OVERDUE_AFTER
    )


def canonical_historical_provider_attempts(
    db: Session,
    *,
    refund: Refund,
) -> dict[int, RefundEvent]:
    """Select only identity-consistent provider observations for older attempts."""
    rows = list(
        db.scalars(
            select(RefundEvent)
            .where(
                RefundEvent.refund_id == refund.id,
                RefundEvent.attempt_number < refund.current_attempt_number,
            )
            .order_by(
                RefundEvent.attempt_number.asc(),
                RefundEvent.occurred_at.asc(),
                RefundEvent.id.asc(),
            )
        ).all()
    )
    attempt_numbers = sorted(
        {
            row.attempt_number
            for row in rows
            if refund_event_has_authoritative_provider_observation(row)
        }
    )
    evidence = reduce_refund_attempt_evidence(rows)
    selected: dict[int, RefundEvent] = {}
    for attempt_number in attempt_numbers:
        attempt = evidence.get(attempt_number)
        canonical = canonical_provider_attempt_event(
            rows,
            attempt_number=attempt_number,
        )
        if (
            attempt is None
            or not refund_attempt_identity_matches_refund(
                refund,
                attempt_number=attempt_number,
                attempt=attempt,
            )
            or canonical is None
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Refund attempt history has conflicting provider identity "
                    "and cannot be reconciled automatically."
                ),
            )
        selected[attempt_number] = canonical
    return selected


def require_current_provider_attempt_identity(
    db: Session,
    *,
    refund: Refund,
) -> None:
    """Fail closed when current-attempt observations contradict the Refund row."""
    rows = list(
        db.scalars(
            select(RefundEvent)
            .where(
                RefundEvent.refund_id == refund.id,
                RefundEvent.attempt_number == refund.current_attempt_number,
            )
            .order_by(RefundEvent.occurred_at.asc(), RefundEvent.id.asc())
        ).all()
    )
    if not any(refund_event_has_authoritative_provider_observation(row) for row in rows):
        return
    attempt = reduce_refund_attempt_evidence(rows).get(refund.current_attempt_number)
    if (
        attempt is None
        or not attempt.identity_consistent
        or attempt.amount_cents != refund.amount_cents
        or attempt.currency != refund.currency
        or attempt.request_key != refund.stripe_request_key
        or attempt.provider != refund.provider
        or (
            refund.provider_refund_id is not None
            and attempt.provider_refund_id != refund.provider_refund_id
        )
        or (
            refund.provider_charge_id is not None
            and attempt.provider_charge_id != refund.provider_charge_id
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Current refund attempt has conflicting provider identity and "
                "cannot be reconciled automatically."
            ),
        )


def validate_refund_retry(
    eligibility: RefundRetryEligibility,
) -> None:
    if eligibility.mutation_allowed:
        return
    blocker = eligibility.blockers[0]
    raise HTTPException(
        status_code=(
            status.HTTP_409_CONFLICT
            if blocker.conflict
            else status.HTTP_400_BAD_REQUEST
        ),
        detail=blocker.message,
    )



def sum_succeeded_refunds_for_payment(
    db: Session,
    *,
    payment_id: uuid.UUID,
    excluding_refund_id: uuid.UUID | None = None,
) -> int:
    from backend.services.refund_attempt_policy import (
        authoritative_succeeded_amount_for_refunds,
    )

    statement = select(Refund).where(Refund.payment_id == payment_id)
    if excluding_refund_id is not None:
        statement = statement.where(Refund.id != excluding_refund_id)
    return authoritative_succeeded_amount_for_refunds(
        db, db.scalars(statement).all()
    )


def sync_refunded_payment_state(
    db: Session,
    *,
    payment: Payment,
    refund: Refund,
    booking: Booking | None,
    host_publish_fee: HostPublishFee | None = None,
    now: datetime,
) -> None:
    succeeded_total = get_refund_payment_ledger(
        db,
        payment_id=payment.id,
        payment_amount_cents=payment.amount_cents,
    ).confirmed_returned_cents
    if host_publish_fee is not None and succeeded_total >= payment.amount_cents:
        host_publish_fee.fee_status = "refunded"
        host_publish_fee.updated_at = now
        db.add(host_publish_fee)

    if booking is None:
        return

    booking_payments = list(
        db.scalars(
            select(Payment)
            .where(Payment.booking_id == booking.id)
            .order_by(Payment.created_at.asc(), Payment.id.asc())
            .with_for_update()
        ).all()
    )
    refundable_booking_payments = [
        booking_payment
        for booking_payment in booking_payments
        if booking_payment.payment_status == "succeeded"
    ]

    if refundable_booking_payments and all(
        sum_succeeded_refunds_for_payment(db, payment_id=booking_payment.id)
        >= booking_payment.amount_cents
        for booking_payment in refundable_booking_payments
    ):
        booking.payment_status = "refunded"
    else:
        booking.payment_status = "partially_refunded"

    booking.updated_at = now
    db.add(booking)


def maybe_notify_refund_processed(
    db: Session,
    *,
    refund: Refund,
    payment: Payment,
    booking: Booking | None,
    now: datetime,
) -> None:
    if booking is None:
        return

    game = db.get(Game, booking.game_id)
    if game is None or game.game_type != "official":
        return

    create_or_reopen_booking_refunded_notification(
        db,
        db_game=game,
        booking=booking,
        payment=payment,
        refund=refund,
        now=now,
        stripe_refund_processed=True,
        credit_component="none",
        notice_context=refund_notice_context_for(refund),
    )


def apply_refund_retry_result(
    db: Session,
    *,
    refund: Refund,
    payment: Payment,
    booking: Booking | None,
    host_publish_fee: HostPublishFee | None,
    admin_action: AdminAction,
    refund_event: RefundEvent,
    admin_user: User,
    reason: str,
    refund_status: str,
    now: datetime,
) -> None:
    if refund.requested_by_user_id is None:
        refund.requested_by_user_id = admin_user.id
    refund.approved_by_user_id = admin_user.id
    db.add(refund)

    existing_open_issues = list_related_money_issues(
        db,
        refund_id=refund.id,
        status_filter="open",
        limit=5,
    )
    for money_issue in existing_open_issues:
        append_money_issue_event(
            db,
            money_issue=money_issue,
            event_type="admin_retry_initiated",
            event_source="admin",
            actor_user_id=admin_user.id,
            admin_action_id=admin_action.id,
            reason_code="admin_retry_initiated",
            summary=reason,
        )

    if refund_status == "succeeded":
        for money_issue in existing_open_issues:
            previous_action = money_issue.recommended_action_code
            money_issue.latest_reason_code = "admin_retry_succeeded"
            money_issue.latest_summary = "Admin refund retry succeeded."
            money_issue.recommended_action_code = "review_and_resolve_no_action"
            money_issue.updated_at = now
            append_money_issue_event(
                db,
                money_issue=money_issue,
                event_type="refund_outcome_linked",
                event_source="admin",
                actor_user_id=admin_user.id,
                admin_action_id=admin_action.id,
                refund_event_id=refund_event.id,
                reason_code="admin_retry_succeeded",
                summary="Admin refund retry succeeded.",
                previous_recommended_action_code=previous_action,
                new_recommended_action_code=money_issue.recommended_action_code,
            )
        sync_refunded_payment_state(
            db,
            payment=payment,
            refund=refund,
            booking=booking,
            host_publish_fee=host_publish_fee,
            now=now,
        )
        maybe_notify_refund_processed(
            db,
            refund=refund,
            payment=payment,
            booking=booking,
            now=now,
        )
    elif refund_status in {"failed", "cancelled"}:
        stage_refund_money_issue(
            db,
            refund=refund,
            payment=payment,
            issue_type="refund_failed"
            if refund_status == "failed"
            else "refund_cancelled",
            reason_code=f"admin_retry_{refund_status}",
            summary="A refund retry did not complete with the provider.",
            refund_event=refund_event,
            admin_action=admin_action,
            now=now,
        )
    else:
        for money_issue in existing_open_issues:
            previous_action = money_issue.recommended_action_code
            money_issue.latest_reason_code = "admin_retry_processing"
            money_issue.latest_summary = "Admin refund retry returned processing."
            money_issue.recommended_action_code = "verify_provider_refund"
            money_issue.updated_at = now
            append_money_issue_event(
                db,
                money_issue=money_issue,
                event_type="refund_outcome_linked",
                event_source="admin",
                actor_user_id=admin_user.id,
                admin_action_id=admin_action.id,
                refund_event_id=refund_event.id,
                reason_code="admin_retry_processing",
                summary="Admin refund retry returned processing.",
                previous_recommended_action_code=previous_action,
                new_recommended_action_code=money_issue.recommended_action_code,
            )


def record_admin_refund_retry_provider_result_checkpoint(
    db: Session,
    *,
    admin_action_id: uuid.UUID,
    admin_user_id: uuid.UUID,
    refund_id: uuid.UUID,
    provider_charge_id: str | None,
    provider_refund_id: str | None,
    refund_status: str,
    now: datetime,
) -> uuid.UUID:
    admin_action = db.get(AdminAction, admin_action_id)
    if admin_action is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ADMIN_REFUND_RETRY_PROVIDER_RESULT_RECORDING_FAILED_DETAIL,
        )

    checkpoint_key = f"admin_refund_retry_provider_result:{admin_action_id}"
    existing_event = get_refund_event_by_idempotency_key(
        db, refund_id, checkpoint_key
    )
    if existing_event is not None:
        return existing_event.id

    refund = db.scalar(select(Refund).where(Refund.id == refund_id).with_for_update())
    if refund is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ADMIN_REFUND_RETRY_PROVIDER_RESULT_RECORDING_FAILED_DETAIL,
        )
    refund_event = record_refund_event(
        db,
        refund=refund,
        event_type="provider_result_recorded",
        event_source="admin",
        actor_user_id=admin_user_id,
        admin_action_id=admin_action_id,
        idempotency_key=checkpoint_key,
        provider=refund.provider,
        provider_refund_id=provider_refund_id,
        provider_charge_id=provider_charge_id,
        provider_status=refund_status,
        new_refund_status=refund_status,
        reason_code=f"admin_retry_{refund_status}",
        summary="Admin refund retry provider result recorded.",
        occurred_at=now,
    )
    db.commit()
    return refund_event.id


def retry_admin_money_refund(
    db: Session,
    *,
    admin_user: User,
    refund_id: uuid.UUID,
    payload: AdminMoneyRefundRetryCreate,
) -> AdminMoneyRefundDetailRead:
    reason = normalize_retry_reason(payload.reason)
    idempotency_key = normalize_retry_idempotency_key(payload.idempotency_key)
    existing = get_existing_retry_action(
        db,
        admin_user_id=admin_user.id,
        refund_id=refund_id,
        idempotency_key=idempotency_key,
    )
    if existing is not None:
        return get_admin_money_refund_detail(
            db, refund_id=refund_id, viewer_user=admin_user
        )

    refund_reference = db.get(Refund, refund_id)
    if refund_reference is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Refund not found."
        )
    payment_reference = db.get(Payment, refund_reference.payment_id)
    if payment_reference is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found."
        )
    try:
        payment, refund = lock_refund_financial_context(db, refund_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refund payment context was not found.",
        ) from exc
    existing = get_existing_retry_action(
        db,
        admin_user_id=admin_user.id,
        refund_id=refund_id,
        idempotency_key=idempotency_key,
    )
    if existing is not None:
        return get_admin_money_refund_detail(
            db, refund_id=refund_id, viewer_user=admin_user
        )
    retry_eligibility = evaluate_refund_retry_eligibility(
        db, refund=refund, payment=payment
    )
    validate_refund_retry(retry_eligibility)
    remaining_cents = retry_eligibility.remaining_cents

    prior_attempt = refund.current_attempt_number
    prior_amount = refund.amount_cents
    prior_key = refund.stripe_request_key
    now = datetime.now(timezone.utc)
    compensation = db.scalars(
        select(PaymentCompensation)
        .where(PaymentCompensation.refund_id == refund.id)
        .with_for_update()
    ).first()
    if remaining_cents == 0:
        admin_action = record_admin_action(
            db,
            admin_user_id=admin_user.id,
            action_type="update_refund",
            outcome="succeeded",
            target_user_id=payment.payer_user_id,
            target_booking_id=refund.booking_id or payment.booking_id,
            target_participant_id=refund.participant_id,
            target_payment_id=payment.id,
            target_refund_id=refund.id,
            target_host_publish_fee_id=refund.host_publish_fee_id,
            reason=reason,
            idempotency_key=idempotency_key,
            metadata={
                **refund_audit_metadata(
                    refund, source="admin_money_refund_retry_no_action"
                ),
                "prior_attempt_number": prior_attempt,
            },
        )
        if compensation is not None:
            compensation.status = "succeeded"
            compensation.error_code = None
            compensation.processing_started_at = None
            compensation.resolved_at = now
            compensation.updated_at = now
            db.add(compensation)
        for issue in list_related_money_issues(
            db, refund_id=refund.id, status_filter="open", limit=100
        ):
            previous_action = issue.recommended_action_code
            issue.recommended_action_code = "review_and_resolve_no_action"
            issue.latest_reason_code = "payment_obligation_already_satisfied"
            issue.latest_summary = (
                "Payment-level refund accounting found no remaining cash obligation."
            )
            issue.updated_at = now
            append_money_issue_event(
                db,
                money_issue=issue,
                event_type="recommended_action_changed",
                event_source="admin",
                actor_user_id=admin_user.id,
                admin_action_id=admin_action.id,
                reason_code="payment_obligation_already_satisfied",
                summary=issue.latest_summary,
                previous_recommended_action_code=previous_action,
                new_recommended_action_code=issue.recommended_action_code,
                occurred_at=now,
            )
        db.commit()
        return get_admin_money_refund_detail(
            db, refund_id=refund_id, viewer_user=admin_user
        )
    admin_action = record_admin_action(
        db,
        admin_user_id=admin_user.id,
        action_type="update_refund",
        outcome="pending",
        target_user_id=payment.payer_user_id,
        target_booking_id=refund.booking_id or payment.booking_id,
        target_participant_id=refund.participant_id,
        target_payment_id=payment.id,
        target_refund_id=refund.id,
        target_host_publish_fee_id=refund.host_publish_fee_id,
        reason=reason,
        idempotency_key=idempotency_key,
        metadata={
            **refund_audit_metadata(
                refund, source="admin_money_refund_retry"
            ),
            "prior_attempt_number": prior_attempt,
            "new_attempt_number": prior_attempt + 1,
        },
    )
    record_refund_event(
        db,
        refund=refund,
        event_type="local_status_changed",
        event_source="admin",
        actor_user_id=admin_user.id,
        admin_action_id=admin_action.id,
        idempotency_key=(
            f"refund:{refund.id}:admin-action:{admin_action.id}:"
            f"attempt:{prior_attempt}:preserved"
        ),
        reason_code="refund_retry_authorized",
        summary="Prior refund attempt retained before authorized retry.",
        occurred_at=now,
        attempt_number=prior_attempt,
        attempt_amount_cents=prior_amount,
        attempt_currency=refund.currency,
        attempt_request_key=prior_key,
    )
    refund.amount_cents = remaining_cents
    if remaining_cents != prior_amount:
        for issue in list_related_money_issues(
            db, refund_id=refund.id, status_filter="open", limit=100
        ):
            issue.amount_cents = remaining_cents
            issue.latest_reason_code = "refund_retry_remainder_recounted"
            issue.latest_summary = "Refund retry amount was reduced to the verified remainder."
            issue.updated_at = now
            append_money_issue_event(
                db,
                money_issue=issue,
                event_type="classification_changed",
                event_source="admin",
                actor_user_id=admin_user.id,
                admin_action_id=admin_action.id,
                reason_code="refund_retry_remainder_recounted",
                summary=issue.latest_summary,
                occurred_at=now,
                metadata={
                    "old_amount_cents": prior_amount,
                    "new_amount_cents": remaining_cents,
                },
            )
    refund.current_attempt_number = prior_attempt + 1
    refund.stripe_request_key = refund_attempt_key(
        refund.id, refund.current_attempt_number
    )
    refund.provider_attempt_started_at = None
    refund.provider_refund_id = None
    refund.provider_status = None
    refund.provider_status_observed_at = None
    refund.refund_status = "approved"
    refund.approved_by_user_id = admin_user.id
    refund.approved_at = now
    refund.refunded_at = None
    refund.updated_at = now
    db.add(refund)
    if compensation is not None:
        compensation.status = "required"
        compensation.error_code = None
        compensation.processing_started_at = None
        compensation.resolved_at = None
        compensation.updated_at = now
        db.add(compensation)
    record_refund_event(
        db,
        refund=refund,
        event_type="local_status_changed",
        event_source="admin",
        actor_user_id=admin_user.id,
        admin_action_id=admin_action.id,
        idempotency_key=(
            f"refund:{refund.id}:admin-action:{admin_action.id}:"
            f"attempt:{refund.current_attempt_number}:queued"
        ),
        new_refund_status="approved",
        reason_code="refund_retry_queued",
        summary="Authorized refund retry queued for durable fulfillment.",
        occurred_at=now,
    )
    enqueue_refund_fulfillment_job(
        db, refund=refund, registry=build_production_job_registry()
    )
    outcome = db.scalars(
        select(AdminFinancialOutcome).where(
            AdminFinancialOutcome.refund_id == refund.id
        )
    ).first()
    if outcome is not None:
        outcome.applied_status = "pending"
        outcome.applied_at = None
        outcome.applied_by_user_id = None
        outcome.failure_reason = None
        outcome.updated_at = now
        db.add(outcome)
    db.commit()
    return get_admin_money_refund_detail(
        db, refund_id=refund_id, viewer_user=admin_user
    )

def stage_refund_issue_for_terminal_or_unknown(
    db: Session,
    *,
    refund: Refund,
    payment: Payment,
    refund_event,
    reason_code: str,
    summary: str,
    now: datetime,
) -> None:
    if reason_code in {"provider_charge_id_missing", "missing_provider_refund_id"}:
        issue_type = "refund_missing_provider_reference"
    elif (
        refund.refund_status == "processing"
        and refund.provider_refund_id is not None
        and refund.provider_status == "processing"
        and refund_processing_threshold_reached(db, refund=refund, now=now)
    ):
        issue_type = "refund_processing_overdue"
        reason_code = "processing_threshold_reached"
        summary = "Stripe still reports the refund as processing after 24 hours."
    elif refund.refund_status == "failed":
        issue_type = "refund_failed"
    elif refund.refund_status == "cancelled":
        issue_type = "refund_cancelled"
    else:
        issue_type = "refund_outcome_unknown"

    stage_refund_money_issue(
        db,
        refund=refund,
        payment=payment,
        issue_type=issue_type,
        reason_code=reason_code,
        summary=summary,
        refund_event=refund_event,
        now=now,
    )


def link_reconciliation_to_open_issues(
    db: Session,
    *,
    refund: Refund,
    refund_event,
    admin_action: AdminAction,
    admin_user: User,
    reason_code: str,
    summary: str,
    recommended_action_code: str,
    now: datetime,
) -> None:
    for money_issue in list_related_money_issues(
        db,
        refund_id=refund.id,
        status_filter="open",
        limit=10,
    ):
        effective_action, policy_reason, policy_summary = (
            refund_issue_action_under_publish_fee_policy(
                db, refund=refund, default_action=recommended_action_code
            )
        )
        previous_action = money_issue.recommended_action_code
        money_issue.latest_reason_code = policy_reason or reason_code
        money_issue.latest_summary = policy_summary or summary
        money_issue.recommended_action_code = effective_action
        money_issue.updated_at = now
        append_money_issue_event(
            db,
            money_issue=money_issue,
            event_type="refund_outcome_linked",
            event_source="admin",
            actor_user_id=admin_user.id,
            admin_action_id=admin_action.id,
            refund_event_id=refund_event.id,
            reason_code=money_issue.latest_reason_code,
            summary=money_issue.latest_summary,
            previous_recommended_action_code=previous_action,
            new_recommended_action_code=effective_action,
            occurred_at=now,
        )


def reconcile_admin_money_refund(
    db: Session,
    *,
    admin_user: User,
    refund_id: uuid.UUID,
    payload: AdminMoneyRefundReconcileCreate,
) -> AdminMoneyRefundDetailRead:
    reason = normalize_retry_reason(payload.reason)
    idempotency_key = normalize_retry_idempotency_key(payload.idempotency_key)
    requested_provider_refund_id = (
        normalize_optional_text(payload.provider_refund_id, "provider_refund_id")
        if payload.provider_refund_id is not None
        else None
    )
    existing_action = get_existing_reconcile_action(
        db,
        admin_user_id=admin_user.id,
        refund_id=refund_id,
        idempotency_key=idempotency_key,
    )
    if existing_action is not None:
        require_reconcile_replay_matches(
            existing_action,
            reason=reason,
            provider_refund_id=requested_provider_refund_id,
        )
        return get_admin_money_refund_detail(
            db,
            refund_id=refund_id,
            viewer_user=admin_user,
        )

    refund_reference = db.get(Refund, refund_id)
    if refund_reference is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Refund not found."
        )
    payment_reference = db.get(Payment, refund_reference.payment_id)
    if payment_reference is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found."
        )
    try:
        payment, refund = lock_refund_financial_context(db, refund_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refund payment context was not found.",
        ) from exc
    require_current_provider_attempt_identity(db, refund=refund)
    if (
        refund.refund_status == "succeeded"
        and refund_expected_attempts_are_terminal(db, refund)
        and refund_attempt_statuses(db, refund.id).get(
            refund.current_attempt_number
        )
        == "succeeded"
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Succeeded refunds do not need provider reconciliation.",
        )

    if (
        refund.provider_refund_id is not None
        and requested_provider_refund_id is not None
        and refund.provider_refund_id != requested_provider_refund_id
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Provider refund ID conflicts with the current refund attempt.",
        )
    provider_refund_id = refund.provider_refund_id or requested_provider_refund_id

    def record_reconciliation_action() -> AdminAction:
        return record_admin_action(
            db,
            admin_user_id=admin_user.id,
            action_type="reconcile_refund",
            outcome="succeeded",
            target_user_id=payment.payer_user_id,
            target_booking_id=refund.booking_id or payment.booking_id,
            target_participant_id=refund.participant_id,
            target_payment_id=payment.id,
            target_refund_id=refund.id,
            target_host_publish_fee_id=refund.host_publish_fee_id,
            reason=reason,
            idempotency_key=idempotency_key,
            metadata={
                "source": "admin_money_refund_reconcile",
                "refund_status": refund.refund_status,
                "request_identity": {
                    "reason": reason,
                    "provider_refund_id": requested_provider_refund_id,
                },
            },
        )

    historical_attempts = canonical_historical_provider_attempts(db, refund=refund)
    historical_identity = tuple(
        (
            row.attempt_number,
            row.attempt_amount_cents,
            row.attempt_currency,
            row.attempt_request_key,
            row.provider_refund_id,
            row.provider_charge_id,
        )
        for row in historical_attempts.values()
    )

    now = datetime.now(timezone.utc)
    if provider_refund_id is None and not historical_attempts:
        try:
            admin_action = record_reconciliation_action()
            db.flush()
        except IntegrityError as exc:
            db.rollback()
            existing_action = get_existing_reconcile_action(
                db,
                admin_user_id=admin_user.id,
                refund_id=refund_id,
                idempotency_key=idempotency_key,
            )
            if existing_action is not None:
                require_reconcile_replay_matches(
                    existing_action,
                    reason=reason,
                    provider_refund_id=requested_provider_refund_id,
                )
                return get_admin_money_refund_detail(
                    db, refund_id=refund_id, viewer_user=admin_user
                )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=build_admin_action_conflict_detail(exc),
            ) from exc
        refund_event = record_refund_event(
            db,
            refund=refund,
            event_type="provider_outcome_unknown",
            event_source="reconciliation",
            actor_user_id=admin_user.id,
            admin_action_id=admin_action.id,
            provider=refund.provider,
            provider_refund_id=None,
            provider_charge_id=refund.provider_charge_id or payment.provider_charge_id,
            provider_status="unknown",
            new_refund_status="processing",
            reason_code="missing_provider_refund_id",
            summary="Provider status could not be checked because the refund has no provider refund id.",
            occurred_at=now,
        )
        stage_refund_issue_for_terminal_or_unknown(
            db,
            refund=refund,
            payment=payment,
            refund_event=refund_event,
            reason_code="missing_provider_refund_id",
            summary="Refund provider reference is missing.",
            now=now,
        )
        db.commit()
        return get_admin_money_refund_detail(
            db,
            refund_id=refund_id,
            viewer_user=admin_user,
        )

    snapshot = (
        refund.payment_id,
        refund.booking_id,
        refund.host_publish_fee_id,
        refund.current_attempt_number,
        refund.stripe_request_key,
        refund.provider_refund_id,
        refund.provider_charge_id,
        refund.amount_cents,
        refund.currency,
        refund.refund_status,
    )
    db.rollback()

    try:
        provider_results = {
            row.provider_refund_id: retrieve_stripe_refund(row.provider_refund_id)
            for row in historical_attempts.values()
            if row.provider_refund_id is not None
        }
        provider_refund = (
            retrieve_stripe_refund(provider_refund_id)
            if provider_refund_id is not None
            else None
        )
    except StripeConfigError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe refunds are not configured.",
        ) from exc
    except StripeRefundOperationError as exc:
        db.rollback()
        raise HTTPException(
            status_code=(
                status.HTTP_503_SERVICE_UNAVAILABLE
                if exc.classification == "rate_limited"
                else status.HTTP_502_BAD_GATEWAY
            ),
            detail="Stripe refund status could not be checked.",
        ) from exc

    existing_action = get_existing_reconcile_action(
        db,
        admin_user_id=admin_user.id,
        refund_id=refund_id,
        idempotency_key=idempotency_key,
    )
    if existing_action is not None:
        require_reconcile_replay_matches(
            existing_action,
            reason=reason,
            provider_refund_id=requested_provider_refund_id,
        )
        return get_admin_money_refund_detail(
            db, refund_id=refund_id, viewer_user=admin_user
        )
    refund_reference = db.get(Refund, refund_id)
    if refund_reference is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Refund not found."
        )
    payment_reference = db.get(Payment, refund_reference.payment_id)
    if payment_reference is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found."
        )
    try:
        payment, refund = lock_refund_financial_context(db, refund_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refund payment context was not found.",
        ) from exc
    current_snapshot = (
        refund.payment_id,
        refund.booking_id,
        refund.host_publish_fee_id,
        refund.current_attempt_number,
        refund.stripe_request_key,
        refund.provider_refund_id,
        refund.provider_charge_id,
        refund.amount_cents,
        refund.currency,
        refund.refund_status,
    )
    if current_snapshot != snapshot:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Refund changed while provider reconciliation was in progress.",
        )
    require_current_provider_attempt_identity(db, refund=refund)
    current_historical_attempts = canonical_historical_provider_attempts(
        db, refund=refund
    )
    current_historical_identity = tuple(
        (
            row.attempt_number,
            row.attempt_amount_cents,
            row.attempt_currency,
            row.attempt_request_key,
            row.provider_refund_id,
            row.provider_charge_id,
        )
        for row in current_historical_attempts.values()
    )
    if current_historical_identity != historical_identity:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Refund attempt history changed while provider reconciliation was in progress.",
        )
    now = datetime.now(timezone.utc)
    try:
        admin_action = record_reconciliation_action()
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        existing_action = get_existing_reconcile_action(
            db,
            admin_user_id=admin_user.id,
            refund_id=refund_id,
            idempotency_key=idempotency_key,
        )
        if existing_action is not None:
            require_reconcile_replay_matches(
                existing_action,
                reason=reason,
                provider_refund_id=requested_provider_refund_id,
            )
            return get_admin_money_refund_detail(
                db, refund_id=refund_id, viewer_user=admin_user
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_admin_action_conflict_detail(exc),
        ) from exc
    except PublicTimeoutError:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Stripe refund status could not be checked.",
        ) from exc

    from backend.services.refund_fulfillment_service import (
        apply_historical_refund_provider_result,
        apply_refund_provider_result,
    )

    reconciled_statuses: list[str] = []
    reconciled_attempts_are_safe_terminal = True
    for attempt_row in current_historical_attempts.values():
        if attempt_row.provider_refund_id is None:
            continue
        historical_result = provider_results[attempt_row.provider_refund_id]
        historical_outcome, historical_code = apply_historical_refund_provider_result(
            db,
            refund=refund,
            payment=payment,
            attempt=attempt_row,
            result=historical_result,
            event_source="reconciliation",
            actor_user_id=admin_user.id,
            admin_action_id=admin_action.id,
        )
        normalized_historical_status = historical_result.status.strip().lower()
        reconciled_statuses.append(normalized_historical_status)
        reconciled_attempts_are_safe_terminal = (
            reconciled_attempts_are_safe_terminal
            and normalized_historical_status
            in {"succeeded", "failed", "canceled", "cancelled"}
            and (
                historical_outcome == "handled"
                or historical_code == "historical_attempt_conflict"
            )
        )
    if provider_refund is not None:
        current_outcome, _current_code = apply_refund_provider_result(
            db,
            refund=refund,
            payment=payment,
            result=provider_refund,
            event_source="reconciliation",
            actor_user_id=admin_user.id,
            admin_action_id=admin_action.id,
            expected_provider_refund_id=provider_refund_id,
        )
        normalized_current_status = provider_refund.status.strip().lower()
        reconciled_statuses.append(normalized_current_status)
        reconciled_attempts_are_safe_terminal = (
            reconciled_attempts_are_safe_terminal
            and normalized_current_status
            in {"succeeded", "failed", "canceled", "cancelled"}
            and current_outcome == "handled"
        )
    if (
        refund.automatic_mutation_blocked_reason == "historical_attempt_conflict"
        and reconciled_statuses
        and reconciled_attempts_are_safe_terminal
        and refund_expected_attempts_are_terminal(db, refund)
        and not (
            refund.provider_attempt_started_at is not None
            and provider_refund is None
        )
    ):
        ledger = get_refund_payment_ledger(
            db,
            payment_id=payment.id,
            payment_amount_cents=payment.amount_cents,
        )
        if (
            ledger.confirmed_returned_cents <= payment.amount_cents
            and ledger.unresolved_attempt_cents == 0
        ):
            refund.automatic_mutation_blocked_reason = None
            refund.automatic_mutation_blocked_at = None
            refund.updated_at = now
            db.add(refund)
    refund_event = db.scalars(
        select(RefundEvent)
        .where(RefundEvent.admin_action_id == admin_action.id)
        .order_by(RefundEvent.occurred_at.desc(), RefundEvent.id.desc())
        .limit(1)
    ).first()
    if (
        authoritative_succeeded_amount_for_refunds(db, (refund,))
        >= refund.amount_cents
        and refund_expected_attempts_are_terminal(db, refund)
        and refund_event is not None
    ):
        link_reconciliation_to_open_issues(
            db,
            refund=refund,
            refund_event=refund_event,
            admin_action=admin_action,
            admin_user=admin_user,
            reason_code="provider_reconciliation_succeeded",
            summary="Provider confirmed the refund succeeded.",
            recommended_action_code="review_and_resolve_no_action",
            now=now,
        )
    elif refund.refund_status == "processing" and refund_event is not None:
        if refund_processing_threshold_reached(db, refund=refund, now=now):
            stage_refund_money_issue(
                db,
                refund=refund,
                payment=payment,
                issue_type="refund_processing_overdue",
                reason_code="processing_threshold_reached",
                summary=(
                    "Stripe still reports the refund as processing after 24 hours."
                ),
                refund_event=refund_event,
                admin_action=admin_action,
                now=now,
            )
        else:
            link_reconciliation_to_open_issues(
                db,
                refund=refund,
                refund_event=refund_event,
                admin_action=admin_action,
                admin_user=admin_user,
                reason_code="provider_reconciliation_processing",
                summary="Provider still reports the refund as processing.",
                recommended_action_code="verify_provider_refund",
                now=now,
            )

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_refund_conflict_detail(exc),
        ) from exc
    return get_admin_money_refund_detail(
        db,
        refund_id=refund_id,
        viewer_user=admin_user,
    )
