"""Durable Stripe refund intent, execution, and observation policy."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.models import (
    AdminFinancialOutcome,
    Booking,
    DurableJob,
    Game,
    GameCreditUsage,
    HostPublishFee,
    MoneyIssue,
    Payment,
    PaymentCompensation,
    Refund,
    RefundEvent,
)
from backend.observability.timeouts import (
    DependencyMutationTimeoutUnknownError,
    DependencyReadTimeoutError,
)
from backend.services.admin_money_issue_service import (
    append_money_issue_event,
    refund_issue_action_under_publish_fee_policy,
    stage_refund_money_issue,
)
from backend.services.durable_job_service import (
    ConflictingIdempotencyKeyError,
    DurableJobRegistry,
    HandlerResult,
    InvalidJobPayloadError,
    enqueue_job,
)
from backend.services.publish_fee_financial_policy import (
    active_publish_fee_sibling_outcome,
)
from backend.services.refund_attempt_policy import (
    authoritative_succeeded_amount_for_refunds,
    reduce_refund_attempt_status,
    refund_attempt_statuses,
    refund_expected_attempts_are_terminal,
    refund_has_only_terminal_attempts,
)
from backend.services.refund_event_service import record_refund_event
from backend.services.refund_service import get_refund_payment_ledger
from backend.services.status_history_service import (
    add_booking_status_history_if_changed,
)
from backend.services.stripe_service import (
    StripeConfigError,
    StripeRefundOperationError,
    StripeRefundResult,
    create_refund,
    list_refunds_for_charge,
    retrieve_refund,
    validate_refund_preflight,
)

STRIPE_REFUND_FULFILLMENT_JOB = "stripe_refund_fulfillment"
REFUND_JOB_PAYLOAD_VERSION = 1
REFUND_JOB_MAXIMUM_ATTEMPTS = 6
REFUND_RETRY_DELAYS_SECONDS = (60, 300, 1800, 7200, 86400)
REFUND_MUTATION_CUTOFF = timedelta(hours=12)


def refund_attempt_key(refund_id: uuid.UUID, attempt_number: int) -> str:
    if attempt_number < 1:
        raise ValueError("local refund attempt number must be positive")
    return f"refund:{refund_id}:attempt:{attempt_number}"


def initialize_local_refund_attempt(refund: Refund, attempt_number: int = 1) -> None:
    refund.current_attempt_number = attempt_number
    refund.stripe_request_key = refund_attempt_key(refund.id, attempt_number)
    refund.provider_attempt_started_at = None
    refund.provider_refund_id = None
    refund.provider_status = None
    refund.provider_status_observed_at = None
    refund.refunded_at = None


def validate_refund_job_payload(payload: dict[str, Any]) -> None:
    if set(payload) != {"refund_id", "attempt_number"}:
        raise InvalidJobPayloadError(
            "payload must contain only refund_id and attempt_number"
        )
    try:
        normalized_id = str(uuid.UUID(payload["refund_id"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidJobPayloadError("refund_id must be a UUID string") from exc
    if payload["refund_id"] != normalized_id:
        raise InvalidJobPayloadError("refund_id must be a canonical UUID string")
    attempt_number = payload["attempt_number"]
    if isinstance(attempt_number, bool) or not isinstance(attempt_number, int):
        raise InvalidJobPayloadError("attempt_number must be a positive integer")
    if attempt_number < 1:
        raise InvalidJobPayloadError("attempt_number must be a positive integer")


def enqueue_refund_fulfillment_job(
    db: Session,
    *,
    refund: Refund,
    registry: DurableJobRegistry,
):
    identity = {
        "refund_id": str(refund.id),
        "attempt_number": refund.current_attempt_number,
    }
    validate_refund_job_payload(identity)
    expected_key = refund_attempt_key(refund.id, refund.current_attempt_number)
    if refund.stripe_request_key != expected_key:
        raise ConflictingIdempotencyKeyError("refund attempt key is inconsistent")
    job = enqueue_job(
        db,
        registry=registry,
        job_type=STRIPE_REFUND_FULFILLMENT_JOB,
        payload_version=REFUND_JOB_PAYLOAD_VERSION,
        payload=identity,
        protected_identity=identity,
        idempotency_key=expected_key,
        maximum_attempts=REFUND_JOB_MAXIMUM_ATTEMPTS,
        origin_reference_type="refund",
        origin_reference_id=str(refund.id),
    )
    if (
        job.payload != identity
        or job.protected_identity != identity
        or job.idempotency_key != expected_key
        or job.job_type != STRIPE_REFUND_FULFILLMENT_JOB
        or job.payload_version != REFUND_JOB_PAYLOAD_VERSION
        or job.origin_reference_type != "refund"
        or job.origin_reference_id != str(refund.id)
        or job.maximum_attempts != REFUND_JOB_MAXIMUM_ATTEMPTS
    ):
        raise ConflictingIdempotencyKeyError(
            "existing refund job does not match the refund attempt"
        )
    return job


def _normalize_provider_status(raw_status: str) -> tuple[str, str, str]:
    normalized = raw_status.strip().lower()
    if normalized == "pending":
        return "processing", "processing", "stripe_refund_pending"
    if normalized == "requires_action":
        return "processing", "processing", "stripe_refund_requires_action"
    if normalized == "succeeded":
        return "succeeded", "succeeded", "stripe_refund_succeeded"
    if normalized == "failed":
        return "failed", "failed", "stripe_refund_failed"
    if normalized in {"canceled", "cancelled"}:
        return "cancelled", "cancelled", "stripe_refund_cancelled"
    return "processing", "unknown", "stripe_refund_unknown"


def _attempt_metadata_matches(
    result: StripeRefundResult,
    *,
    refund_id: uuid.UUID,
    payment_id: uuid.UUID,
    attempt_number: int,
) -> bool:
    metadata = result.metadata or {}
    return (
        metadata.get("refund_id") == str(refund_id)
        and metadata.get("payment_id") == str(payment_id)
        and metadata.get("attempt_number") == str(attempt_number)
    )


def _validate_provider_result(
    refund: Refund,
    payment: Payment,
    result: StripeRefundResult,
    *,
    attempt: RefundEvent | None = None,
    expected_provider_refund_id_override: str | None = None,
) -> bool:
    attempt_number = refund.current_attempt_number
    attempt_amount = refund.amount_cents
    attempt_currency = refund.currency
    attempt_key = refund.stripe_request_key
    expected_provider_refund_id = (
        expected_provider_refund_id_override or refund.provider_refund_id
    )
    if attempt is not None:
        attempt_number = attempt.attempt_number
        attempt_amount = attempt.attempt_amount_cents
        attempt_currency = attempt.attempt_currency
        attempt_key = attempt.attempt_request_key
        expected_provider_refund_id = attempt.provider_refund_id
    expected_key = (
        refund_attempt_key(refund.id, attempt_number) if attempt_number > 0 else None
    )
    return bool(
        result.id
        and attempt_key == expected_key
        and (
            expected_provider_refund_id is None
            or result.id == expected_provider_refund_id
        )
        and result.amount_cents == attempt_amount
        and result.currency == attempt_currency
        and result.charge_id == refund.provider_charge_id
        and (
            result.payment_intent_id is None
            or result.payment_intent_id == payment.provider_payment_intent_id
        )
        and (
            attempt_number == 0
            or _attempt_metadata_matches(
                result,
                refund_id=refund.id,
                payment_id=payment.id,
                attempt_number=attempt_number,
            )
        )
    )


def _stage_failure_issue(
    db: Session,
    *,
    refund: Refund,
    payment: Payment,
    refund_event: RefundEvent,
    reason_code: str,
    issue_type: str | None = None,
) -> None:
    resolved_issue_type = issue_type or {
        "failed": "refund_failed",
        "cancelled": "refund_cancelled",
    }.get(refund.refund_status, "refund_outcome_unknown")
    stage_refund_money_issue(
        db,
        refund=refund,
        payment=payment,
        issue_type=resolved_issue_type,
        reason_code=reason_code,
        summary="Refund fulfillment requires staff review.",
        refund_event=refund_event,
    )


def _confirmed_returned_for_payment(db: Session, payment_id: uuid.UUID) -> int:
    payment = db.get(Payment, payment_id)
    if payment is None:
        return 0
    return get_refund_payment_ledger(
        db,
        payment_id=payment.id,
        payment_amount_cents=payment.amount_cents,
    ).confirmed_returned_cents


def _booking_cash_totals(db: Session, booking_id: uuid.UUID) -> tuple[int, int]:
    payments = list(
        db.scalars(
            select(Payment).where(
                Payment.booking_id == booking_id,
                Payment.payment_status == "succeeded",
            )
        ).all()
    )
    collected = sum(payment.amount_cents for payment in payments)
    returned = sum(
        get_refund_payment_ledger(
            db,
            payment_id=payment.id,
            payment_amount_cents=payment.amount_cents,
        ).confirmed_returned_cents
        for payment in payments
    )
    return collected, returned


def _booking_history_attribution(
    *, event_source: str, actor_user_id: uuid.UUID | None
) -> tuple[str, uuid.UUID | None]:
    if actor_user_id is not None:
        return "admin", actor_user_id
    if event_source == "webhook":
        return "payment_webhook", None
    return "scheduled_job", None


def _booking_credit_component(db: Session, booking_id: uuid.UUID) -> str:
    statuses = set(
        db.scalars(
            select(GameCreditUsage.usage_status).where(
                GameCreditUsage.booking_id == booking_id,
                GameCreditUsage.usage_status.in_({"released", "restored"}),
            )
        ).all()
    )
    if statuses == {"released", "restored"}:
        return "mixed"
    if "released" in statuses:
        return "released"
    if "restored" in statuses:
        return "restored"
    return "none"


def _sync_dependents(
    db: Session,
    *,
    refund: Refund,
    payment: Payment,
    now: datetime,
    confirmed_value_changed: bool = False,
    event_source: str = "system",
    actor_user_id: uuid.UUID | None = None,
    compensation_error_code: str | None = None,
) -> None:
    compensations = list(db.scalars(
        select(PaymentCompensation)
        .where(PaymentCompensation.payment_id == payment.id)
        .order_by(PaymentCompensation.id.asc())
        .with_for_update()
    ).all())
    compensation = next(
        (row for row in compensations if row.refund_id == refund.id), None
    )
    returned = _confirmed_returned_for_payment(db, payment.id)
    refund_has_confirmed_return = (
        authoritative_succeeded_amount_for_refunds(db, (refund,)) > 0
    )
    for payment_compensation in compensations:
        if returned >= payment.amount_cents:
            payment_compensation.status = "succeeded"
            payment_compensation.error_code = None
            payment_compensation.resolved_at = now
        elif payment_compensation.refund_id == refund.id:
            if refund.refund_status in {"failed", "cancelled"}:
                payment_compensation.status = "failed"
                payment_compensation.error_code = f"refund_{refund.refund_status}"
                payment_compensation.resolved_at = now
            else:
                payment_compensation.status = "processing"
                if compensation_error_code is not None:
                    payment_compensation.error_code = compensation_error_code
                payment_compensation.processing_started_at = (
                    payment_compensation.processing_started_at or now
                )
                payment_compensation.resolved_at = None
        payment_compensation.updated_at = now
        db.add(payment_compensation)

    outcome = db.scalars(
        select(AdminFinancialOutcome)
        .where(AdminFinancialOutcome.refund_id == refund.id)
        .with_for_update()
    ).first()
    if outcome is not None:
        active_sibling = active_publish_fee_sibling_outcome(db, refund=refund)
        returned = _confirmed_returned_for_payment(db, payment.id)
        if refund_has_confirmed_return or (
            confirmed_value_changed and returned >= refund.amount_cents
        ):
            if active_sibling is None:
                outcome.applied_status = "applied"
                outcome.failure_reason = None
                outcome.applied_at = now
                outcome.applied_by_user_id = refund.approved_by_user_id
            else:
                outcome.applied_status = "failed"
                outcome.failure_reason = (
                    "Cash refund succeeded after a later financial decision became active."
                )
                outcome.applied_at = now
                outcome.applied_by_user_id = refund.approved_by_user_id
        elif refund.refund_status in {"failed", "cancelled"}:
            outcome.applied_status = "failed"
            outcome.failure_reason = f"Stripe refund {refund.refund_status}."
            outcome.applied_at = now
            outcome.applied_by_user_id = refund.approved_by_user_id
        else:
            outcome.applied_status = "pending"
            outcome.applied_at = None
            outcome.applied_by_user_id = None
        outcome.updated_at = now
        db.add(outcome)

    if (refund_has_confirmed_return or confirmed_value_changed) and payment.booking_id is not None:
        booking = db.get(Booking, payment.booking_id)
        if booking is not None:
            old_booking_status = booking.booking_status
            old_payment_status = booking.payment_status
            old_reservation_status = booking.reservation_status
            collected, returned = _booking_cash_totals(db, booking.id)
            booking.payment_status = (
                "refunded" if collected > 0 and returned >= collected else "partially_refunded"
            )
            booking.updated_at = now
            db.add(booking)
            history_source, history_actor = _booking_history_attribution(
                event_source=event_source,
                actor_user_id=actor_user_id,
            )
            add_booking_status_history_if_changed(
                db,
                booking,
                old_booking_status=old_booking_status,
                old_payment_status=old_payment_status,
                old_reservation_status=old_reservation_status,
                reason="refund_summary_recalculated",
                changed_by_user_id=history_actor,
                change_source=history_source,
            )
            game = db.get(Game, booking.game_id)
            if game is not None:
                from backend.services.game_notification_service import (
                    create_or_reopen_booking_refunded_notification,
                    refund_notice_context_for,
                )

                credit_component = _booking_credit_component(db, booking.id)
                create_or_reopen_booking_refunded_notification(
                    db,
                    db_game=game,
                    booking=booking,
                    payment=payment,
                    refund=refund,
                    now=now,
                    stripe_refund_processed=True,
                    credit_component=credit_component,
                    notice_context=refund_notice_context_for(
                        refund,
                        compensation_reason=(
                            compensation.reason if compensation is not None else None
                        ),
                    ),
                )

    if (refund_has_confirmed_return or confirmed_value_changed) and refund.host_publish_fee_id is not None:
        host_publish_fee = db.get(HostPublishFee, refund.host_publish_fee_id)
        if host_publish_fee is not None and _confirmed_returned_for_payment(db, payment.id) >= payment.amount_cents:
            host_publish_fee.fee_status = "refunded"
            host_publish_fee.updated_at = now
            db.add(host_publish_fee)

    if outcome is not None:
        from backend.services.admin_financial_outcome_service import (
            create_financial_outcome_notice_if_needed,
            reclassify_superseded_publish_refund_issues,
            recompute_superseded_publish_refund_issues,
        )

        if outcome.applied_status in {"applied", "not_applicable"}:
            reclassify_superseded_publish_refund_issues(
                db, financial_outcome=outcome
            )
        elif outcome.applied_status == "failed":
            recompute_superseded_publish_refund_issues(
                db, financial_outcome=outcome
            )

        create_financial_outcome_notice_if_needed(
            db,
            financial_outcome=outcome,
            created_by_user_id=outcome.created_by_user_id,
        )

    if refund.refund_status in {"succeeded", "failed", "cancelled"}:
        from backend.services.stripe_webhook_service import (
            advance_required_payment_compensations_for_payment,
        )

        advance_required_payment_compensations_for_payment(
            db, payment=payment, now=now
        )


def apply_refund_provider_result(
    db: Session,
    *,
    refund: Refund,
    payment: Payment,
    result: StripeRefundResult,
    event_source: str,
    provider_event_id: str | None = None,
    actor_user_id: uuid.UUID | None = None,
    admin_action_id: uuid.UUID | None = None,
    expected_provider_refund_id: str | None = None,
) -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    if not _validate_provider_result(
        refund,
        payment,
        result,
        expected_provider_refund_id_override=expected_provider_refund_id,
    ):
        _, observed_provider_status, _ = _normalize_provider_status(result.status)
        event = record_refund_event(
            db,
            refund=refund,
            event_type="provider_outcome_unknown",
            event_source=event_source,
            provider_event_id=provider_event_id,
            actor_user_id=actor_user_id,
            admin_action_id=admin_action_id,
            provider_refund_id=result.id,
            provider_charge_id=result.charge_id,
            provider_status=observed_provider_status,
            new_refund_status=None,
            reason_code="refund_invalid_provider_result",
            summary="Stripe refund result did not match the committed attempt.",
            occurred_at=now,
            apply_to_refund=False,
        )
        if getattr(event, "_recorded_now", True):
            _stage_failure_issue(
                db,
                refund=refund,
                payment=payment,
                refund_event=event,
                reason_code="refund_invalid_provider_result",
            )
        return "unsafe", "refund_invalid_provider_result"

    local_status, provider_status, reason_code = _normalize_provider_status(result.status)
    prior_refund_status = refund.refund_status
    prior_confirmed = _confirmed_returned_for_payment(db, payment.id)
    event = record_refund_event(
        db,
        refund=refund,
        event_type="provider_result_recorded",
        event_source=event_source,
        provider_refund_id=result.id,
        provider_charge_id=result.charge_id,
        provider_status=provider_status,
        new_refund_status=local_status,
        provider_event_id=provider_event_id,
        actor_user_id=actor_user_id,
        admin_action_id=admin_action_id,
        reason_code=reason_code,
        summary="Stripe refund result recorded.",
        occurred_at=now,
    )
    effective_status = refund.refund_status
    confirmed_value_changed = (
        _confirmed_returned_for_payment(db, payment.id) > prior_confirmed
    )
    transition_changed = confirmed_value_changed or effective_status != prior_refund_status
    if transition_changed:
        _sync_dependents(
            db,
            refund=refund,
            payment=payment,
            now=now,
            confirmed_value_changed=confirmed_value_changed,
            event_source=event_source,
            actor_user_id=actor_user_id,
        )
    if effective_status == "succeeded" and payment.booking_id is not None:
        collected, returned = _booking_cash_totals(db, payment.booking_id)
        if returned > collected:
            stage_refund_money_issue(
                db,
                refund=refund,
                payment=payment,
                issue_type="refund_outcome_unknown",
                reason_code="booking_cash_over_refunded",
                summary="Confirmed booking refunds exceed collected cash.",
                refund_event=event,
                now=now,
            )
    attempt_history_is_safe = (
        effective_status == "succeeded"
        and refund_expected_attempts_are_terminal(db, refund)
    )
    if effective_status == "succeeded" and not attempt_history_is_safe:
        refund.automatic_mutation_blocked_reason = "historical_attempt_conflict"
        refund.automatic_mutation_blocked_at = now
        refund.updated_at = now
        db.add(refund)
        stage_refund_money_issue(
            db,
            refund=refund,
            payment=payment,
            issue_type="refund_outcome_unknown",
            reason_code="refund_incomplete_attempt_history",
            summary=(
                "Provider confirmed returned cash, but the complete refund attempt "
                "history is not authoritative."
            ),
            refund_event=event,
            now=now,
        )
    if effective_status in {"failed", "cancelled"}:
        if not transition_changed:
            return "handled", reason_code
        _stage_failure_issue(
            db,
            refund=refund,
            payment=payment,
            refund_event=event,
            reason_code=reason_code,
        )
        return "handled", reason_code
    if effective_status == "succeeded":
        if not transition_changed:
            return "handled", reason_code
        for issue in db.scalars(
            select(MoneyIssue)
            .where(
                MoneyIssue.target_refund_id == refund.id,
                MoneyIssue.status == "open",
            )
            .order_by(MoneyIssue.id.asc())
            .with_for_update()
        ).all():
            previous_action = issue.recommended_action_code
            next_action, policy_reason, policy_summary = (
                refund_issue_action_under_publish_fee_policy(
                    db,
                    refund=refund,
                    default_action=(
                        "review_and_resolve_no_action"
                        if attempt_history_is_safe
                        else "review_unknown_outcome"
                    ),
                )
            )
            issue.latest_reason_code = policy_reason or (
                "provider_refund_succeeded"
                if attempt_history_is_safe
                else "refund_incomplete_attempt_history"
            )
            issue.latest_summary = policy_summary or (
                "Provider confirmed the refund succeeded."
                if attempt_history_is_safe
                else (
                    "Returned cash is confirmed, but the complete attempt history "
                    "still requires review."
                )
            )
            issue.recommended_action_code = next_action
            issue.updated_at = now
            append_money_issue_event(
                db,
                money_issue=issue,
                event_type="refund_outcome_linked",
                event_source="admin" if actor_user_id is not None else "system",
                actor_user_id=actor_user_id,
                admin_action_id=admin_action_id,
                refund_event_id=event.id,
                reason_code=issue.latest_reason_code,
                summary=issue.latest_summary,
                previous_recommended_action_code=previous_action,
                new_recommended_action_code=issue.recommended_action_code,
                occurred_at=now,
            )
        return "handled", reason_code
    return "retry", "refund_processing" if provider_status == "processing" else "refund_outcome_unknown"


def apply_historical_refund_provider_result(
    db: Session,
    *,
    refund: Refund,
    payment: Payment,
    attempt: RefundEvent,
    result: StripeRefundResult,
    event_source: str,
    provider_event_id: str | None = None,
    actor_user_id: uuid.UUID | None = None,
    admin_action_id: uuid.UUID | None = None,
) -> tuple[str, str]:
    """Apply an observation for an attempt older than Refund.current_attempt_number."""
    now = datetime.now(timezone.utc)
    expected_key = (
        refund_attempt_key(refund.id, attempt.attempt_number)
        if attempt.attempt_number > 0
        else None
    )
    identity_matches = (
        attempt.refund_id == refund.id
        and attempt.attempt_number < refund.current_attempt_number
        and attempt.attempt_request_key == expected_key
        and attempt.provider_refund_id == result.id
        and attempt.provider_charge_id == result.charge_id
        and attempt.attempt_amount_cents == result.amount_cents
        and attempt.attempt_currency == result.currency
        and _validate_provider_result(refund, payment, result, attempt=attempt)
    )
    if not identity_matches:
        _, observed_provider_status, _ = _normalize_provider_status(result.status)
        event = record_refund_event(
            db,
            refund=refund,
            event_type="provider_outcome_unknown",
            event_source=event_source,
            provider_event_id=provider_event_id,
            actor_user_id=actor_user_id,
            admin_action_id=admin_action_id,
            provider_refund_id=result.id,
            provider_charge_id=result.charge_id,
            provider_status=observed_provider_status,
            new_refund_status=None,
            reason_code="historical_attempt_identity_mismatch",
            summary="Historical Stripe refund did not match its immutable attempt.",
            occurred_at=now,
            attempt_number=attempt.attempt_number,
            attempt_amount_cents=attempt.attempt_amount_cents,
            attempt_currency=attempt.attempt_currency,
            attempt_request_key=attempt.attempt_request_key,
            apply_to_refund=False,
        )
        _stage_failure_issue(
            db,
            refund=refund,
            payment=payment,
            refund_event=event,
            reason_code="historical_attempt_identity_mismatch",
        )
        return "unsafe", "historical_attempt_identity_mismatch"

    local_status, provider_status, reason_code = _normalize_provider_status(result.status)
    prior_status = refund_attempt_statuses(db, refund.id).get(attempt.attempt_number)
    effective_status = reduce_refund_attempt_status(prior_status, local_status)
    accepted_status = local_status if effective_status != prior_status else None
    historical_event = record_refund_event(
        db,
        refund=refund,
        event_type="provider_result_recorded",
        event_source=event_source,
        provider_event_id=provider_event_id,
        provider_refund_id=result.id,
        provider_charge_id=result.charge_id,
        provider_status=provider_status,
        new_refund_status=accepted_status,
        actor_user_id=actor_user_id,
        admin_action_id=admin_action_id,
        reason_code=reason_code,
        summary="Historical Stripe refund result recorded.",
        occurred_at=now,
        attempt_number=attempt.attempt_number,
        attempt_amount_cents=attempt.attempt_amount_cents,
        attempt_currency=attempt.attempt_currency,
        attempt_request_key=attempt.attempt_request_key,
        apply_to_refund=False,
    )
    if effective_status != "succeeded" or prior_status == "succeeded":
        return "handled", reason_code

    refund.automatic_mutation_blocked_reason = "historical_attempt_conflict"
    refund.automatic_mutation_blocked_at = now
    refund.updated_at = now
    db.add(refund)
    if refund.refund_status == "approved" and refund.provider_attempt_started_at is None:
        record_refund_event(
            db,
            refund=refund,
            event_type="local_status_changed",
            event_source="system",
            new_refund_status="failed",
            reason_code="historical_attempt_conflict",
            summary="Unstarted newer attempt was stopped after an older attempt succeeded.",
            metadata={"provider_call_started": False},
            occurred_at=now,
        )
    _sync_dependents(
        db,
        refund=refund,
        payment=payment,
        now=now,
        confirmed_value_changed=True,
        event_source=event_source,
        actor_user_id=actor_user_id,
    )
    stage_refund_money_issue(
        db,
        refund=refund,
        payment=payment,
        issue_type="refund_outcome_unknown",
        reason_code="historical_attempt_conflict",
        summary="An older Stripe refund attempt succeeded while a newer attempt exists.",
        refund_event=historical_event,
        admin_action=None,
        now=now,
    )
    return "unsafe", "historical_attempt_conflict"


def _matching_list_result(
    *,
    provider_charge_id: str | None,
    refund_id: uuid.UUID,
    payment_id: uuid.UUID,
    attempt_number: int,
) -> tuple[StripeRefundResult | None, bool]:
    if provider_charge_id is None:
        return None, False
    results, truncated = list_refunds_for_charge(provider_charge_id)
    matches = []
    for result in results:
        metadata = result.metadata or {}
        if (
            metadata.get("refund_id") == str(refund_id)
            and metadata.get("payment_id") == str(payment_id)
            and metadata.get("attempt_number") == str(attempt_number)
        ):
            matches.append(result)
    if truncated or len(matches) > 1:
        return None, True
    return (matches[0] if matches else None), False


def lock_refund_financial_context(
    db: Session, refund_id: uuid.UUID
) -> tuple[Payment, Refund]:
    refund_reference = db.get(Refund, refund_id)
    if refund_reference is None:
        raise LookupError("refund is missing")
    payment_reference = db.get(Payment, refund_reference.payment_id)
    if payment_reference is None:
        raise LookupError("refund payment is missing")
    booking_id = refund_reference.booking_id or payment_reference.booking_id
    if booking_id is not None:
        booking_reference = db.get(Booking, booking_id)
        if booking_reference is not None:
            db.scalar(
                select(Game)
                .where(Game.id == booking_reference.game_id)
                .with_for_update()
            )
            db.scalar(
                select(Booking).where(Booking.id == booking_id).with_for_update()
            )
    payment = db.scalars(
        select(Payment).where(Payment.id == payment_reference.id).with_for_update()
    ).one()
    fee_id = refund_reference.host_publish_fee_id
    if fee_id is not None:
        db.scalar(
            select(HostPublishFee)
            .where(HostPublishFee.id == fee_id)
            .with_for_update()
        )
    related_refunds = list(
        db.scalars(
            select(Refund)
            .where(Refund.payment_id == payment.id)
            .order_by(Refund.id.asc())
            .with_for_update()
        ).all()
    )
    refund = next(row for row in related_refunds if row.id == refund_id)
    related_refund_ids = [row.id for row in related_refunds]
    list(
        db.scalars(
            select(PaymentCompensation)
            .where(PaymentCompensation.payment_id == payment.id)
            .order_by(PaymentCompensation.id.asc())
            .with_for_update()
        ).all()
    )
    outcome_filters = [
        AdminFinancialOutcome.payment_id == payment.id,
        AdminFinancialOutcome.refund_id.in_(related_refund_ids),
    ]
    if fee_id is not None:
        outcome_filters.append(AdminFinancialOutcome.host_publish_fee_id == fee_id)
    list(
        db.scalars(
            select(AdminFinancialOutcome)
            .where(or_(*outcome_filters))
            .order_by(AdminFinancialOutcome.id.asc())
            .with_for_update()
        ).all()
    )
    list(
        db.scalars(
            select(MoneyIssue)
            .where(MoneyIssue.target_refund_id.in_(related_refund_ids))
            .order_by(MoneyIssue.id.asc())
            .with_for_update()
        ).all()
    )
    return payment, refund


def handle_refund_fulfillment(db: Session, job) -> HandlerResult:
    job = db.scalars(
        select(DurableJob).where(DurableJob.id == job.id).with_for_update()
    ).one()
    job_id = job.id
    lease_token = job.lease_token
    job_attempt_count = job.attempt_count
    payload = dict(job.payload)
    validate_refund_job_payload(payload)
    refund_id = uuid.UUID(payload["refund_id"])
    attempt_number = payload["attempt_number"]

    refund = db.get(Refund, refund_id)
    if refund is None:
        return HandlerResult.permanent_failure("refund_unsafe_replay")
    if refund.current_attempt_number != attempt_number:
        return HandlerResult.success({"refund_outcome": "stale_attempt"})
    expected_key = refund_attempt_key(refund.id, attempt_number)
    if (
        refund.stripe_request_key != expected_key
        or job.idempotency_key != expected_key
        or job.protected_identity != payload
        or job.origin_reference_type != "refund"
        or job.origin_reference_id != str(refund.id)
        or job.maximum_attempts != REFUND_JOB_MAXIMUM_ATTEMPTS
    ):
        return HandlerResult.permanent_failure("refund_unsafe_replay")
    payment, refund = lock_refund_financial_context(db, refund_id)
    now = datetime.now(timezone.utc)
    current_attempt_status = refund_attempt_statuses(db, refund.id).get(
        refund.current_attempt_number
    )
    if refund.refund_status == "succeeded" and current_attempt_status == "succeeded":
        return HandlerResult.success({"refund_outcome": "succeeded"})
    if refund.refund_status in {"failed", "cancelled"}:
        if refund_has_only_terminal_attempts(db, refund):
            return HandlerResult.success({"refund_outcome": refund.refund_status})
        return HandlerResult.permanent_failure("refund_outcome_unknown")
    if refund.automatic_mutation_blocked_reason is not None:
        return HandlerResult.permanent_failure("refund_outcome_unknown")
    ledger = get_refund_payment_ledger(
        db,
        payment_id=payment.id,
        payment_amount_cents=payment.amount_cents,
        exclude_refund_id=refund.id,
    )
    if (
        not ledger.attempt_history_complete
        or refund.amount_cents > ledger.available_cents
    ):
        now = datetime.now(timezone.utc)
        refund.automatic_mutation_blocked_reason = "historical_attempt_conflict"
        refund.automatic_mutation_blocked_at = now
        refund.updated_at = now
        if refund.provider_attempt_started_at is None:
            event = record_refund_event(
                db,
                refund=refund,
                event_type="local_status_changed",
                event_source="system",
                new_refund_status="failed",
                reason_code="payment_refund_amount_no_longer_available",
                summary="Refund was stopped before provider mutation because the payment remainder changed.",
                metadata={"provider_call_started": False},
                occurred_at=now,
            )
            _sync_dependents(db, refund=refund, payment=payment, now=now)
            _stage_failure_issue(
                db,
                refund=refund,
                payment=payment,
                refund_event=event,
                reason_code="payment_refund_amount_no_longer_available",
                issue_type=(
                    "refund_outcome_unknown"
                    if not ledger.attempt_history_complete
                    else None
                ),
            )
            return HandlerResult.success({"refund_outcome": "failed_preflight"})
        return HandlerResult.permanent_failure("refund_outcome_unknown")
    if refund.provider_attempt_started_at is None:
        if not refund.provider_charge_id:
            event = record_refund_event(
                db,
                refund=refund,
                event_type="local_status_changed",
                event_source="system",
                new_refund_status="failed",
                reason_code="provider_charge_id_missing",
                summary="Refund could not start because the payment has no Stripe charge.",
                metadata={"provider_call_started": False},
                occurred_at=now,
            )
            _sync_dependents(db, refund=refund, payment=payment, now=now)
            _stage_failure_issue(
                db,
                refund=refund,
                payment=payment,
                refund_event=event,
                reason_code="provider_charge_id_missing",
            )
            return HandlerResult.success({"refund_outcome": "failed_preflight"})
        try:
            validate_refund_preflight(refund.currency)
        except StripeConfigError:
            event = record_refund_event(
                db,
                refund=refund,
                event_type="local_status_changed",
                event_source="system",
                new_refund_status="failed",
                reason_code="stripe_refunds_not_configured",
                summary="Stripe refund could not start because configuration is unavailable.",
                metadata={"provider_call_started": False},
                occurred_at=now,
            )
            _sync_dependents(db, refund=refund, payment=payment, now=now)
            _stage_failure_issue(
                db,
                refund=refund,
                payment=payment,
                refund_event=event,
                reason_code="stripe_refunds_not_configured",
            )
            return HandlerResult.success({"refund_outcome": "failed_preflight"})
        refund.provider_attempt_started_at = now
        record_refund_event(
            db,
            refund=refund,
            event_type="local_status_changed",
            event_source="system",
            new_refund_status="processing",
            reason_code="refund_provider_attempt_started",
            summary="Refund provider attempt checkpoint committed.",
            occurred_at=now,
        )
        _sync_dependents(db, refund=refund, payment=payment, now=now)
    provider_refund_id = refund.provider_refund_id
    provider_charge_id = refund.provider_charge_id
    provider_attempt_started_at = refund.provider_attempt_started_at
    refund_amount_cents = refund.amount_cents
    refund_currency = refund.currency
    payment_id = payment.id
    db.commit()

    try:
        result: StripeRefundResult | None = None
        unsafe_search = False
        if provider_refund_id:
            result = retrieve_refund(provider_refund_id)
        elif job_attempt_count > 1:
            result, unsafe_search = _matching_list_result(
                provider_charge_id=provider_charge_id,
                refund_id=refund_id,
                payment_id=payment_id,
                attempt_number=attempt_number,
            )
        if unsafe_search:
            return HandlerResult.permanent_failure("refund_unsafe_replay")
        if result is None:
            started_at = provider_attempt_started_at
            if started_at is None or datetime.now(timezone.utc) - started_at >= REFUND_MUTATION_CUTOFF:
                return HandlerResult.permanent_failure("refund_outcome_unknown")
            result = create_refund(
                charge_id=provider_charge_id,
                amount_cents=refund_amount_cents,
                currency=refund_currency,
                idempotency_key=expected_key,
                metadata={
                    "refund_id": str(refund_id),
                    "payment_id": str(payment_id),
                    "attempt_number": attempt_number,
                },
            )
    except StripeConfigError:
        return HandlerResult.transient_failure(
            "refund_read_retry",
            retry_delay=_refund_retry_delay(job_attempt_count),
        )
    except StripeRefundOperationError as exc:
        if exc.classification == "rate_limited":
            return HandlerResult.transient_failure(
                "refund_provider_retry",
                retry_delay=_refund_retry_delay(job_attempt_count),
            )
        try:
            recovered, unsafe_recovery = _matching_list_result(
                provider_charge_id=provider_charge_id,
                refund_id=refund_id,
                payment_id=payment_id,
                attempt_number=attempt_number,
            )
        except (StripeRefundOperationError, StripeConfigError):
            return HandlerResult.transient_failure(
                "refund_read_retry",
                retry_delay=_refund_retry_delay(job_attempt_count),
            )
        if unsafe_recovery:
            return HandlerResult.permanent_failure("refund_unsafe_replay")
        if recovered is not None:
            result = recovered
        elif exc.classification == "unsafe_client_error":
            return HandlerResult.permanent_failure("refund_outcome_unknown")
        else:
            return HandlerResult.transient_failure(
                "refund_read_retry" if provider_refund_id else "refund_provider_retry",
                retry_delay=_refund_retry_delay(job_attempt_count),
            )
    except (DependencyMutationTimeoutUnknownError, DependencyReadTimeoutError):
        return HandlerResult.transient_failure(
            "refund_read_retry" if provider_refund_id else "refund_provider_retry",
            retry_delay=_refund_retry_delay(job_attempt_count),
        )
    except Exception as exc:  # noqa: BLE001 - provider failures remain unsafe.
        if getattr(exc, "http_status", None) == 429:
            return HandlerResult.transient_failure(
                "refund_provider_retry", retry_delay=_refund_retry_delay(job_attempt_count)
            )
        return HandlerResult.permanent_failure("refund_outcome_unknown")

    current_job = db.scalars(
        select(DurableJob).where(DurableJob.id == job_id).with_for_update()
    ).one()
    if current_job.status != "leased" or current_job.lease_token != lease_token:
        return HandlerResult.permanent_failure("refund_unsafe_replay")
    payment, refund = lock_refund_financial_context(db, refund_id)
    if payment.id != payment_id:
        return HandlerResult.permanent_failure("refund_unsafe_replay")
    outcome, code = apply_refund_provider_result(
        db,
        refund=refund,
        payment=payment,
        result=result,
        event_source="reconciliation",
    )
    if outcome == "handled":
        return HandlerResult.success({"refund_outcome": refund.refund_status})
    if outcome == "retry":
        return HandlerResult.transient_failure(
            code, retry_delay=_refund_retry_delay(job_attempt_count)
        )
    return HandlerResult.permanent_failure(code)


def _refund_retry_delay(attempt_count: int) -> timedelta:
    index = min(max(attempt_count - 1, 0), len(REFUND_RETRY_DELAYS_SECONDS) - 1)
    return timedelta(seconds=REFUND_RETRY_DELAYS_SECONDS[index])


def _proven_exhausted_identity(job) -> tuple[uuid.UUID, int] | None:
    identity = job.protected_identity
    if not isinstance(identity, dict) or set(identity) != {"refund_id", "attempt_number"}:
        return None
    try:
        refund_id = uuid.UUID(identity["refund_id"])
    except (TypeError, ValueError):
        return None
    attempt_number = identity["attempt_number"]
    if isinstance(attempt_number, bool) or not isinstance(attempt_number, int) or attempt_number < 1:
        return None
    expected_key = refund_attempt_key(refund_id, attempt_number)
    if (
        identity["refund_id"] != str(refund_id)
        or job.idempotency_key != expected_key
        or job.origin_reference_type != "refund"
        or job.origin_reference_id != str(refund_id)
    ):
        return None
    if isinstance(job.payload, dict):
        try:
            validate_refund_job_payload(job.payload)
        except InvalidJobPayloadError:
            pass
        else:
            if job.payload != identity:
                return None
    return refund_id, attempt_number


def handle_refund_job_exhausted(
    db: Session, job, error_code: str
) -> str | None:
    proven = _proven_exhausted_identity(job)
    if proven is None:
        return None
    refund_id, attempt_number = proven
    refund_reference = db.get(Refund, refund_id)
    if refund_reference is None:
        return None
    try:
        payment, refund = lock_refund_financial_context(db, refund_id)
    except LookupError:
        return None
    if (
        payment is None
        or refund is None
        or refund.current_attempt_number != attempt_number
        or refund.stripe_request_key != refund_attempt_key(refund_id, attempt_number)
        or (
            refund.refund_status == "succeeded"
            and refund_attempt_statuses(db, refund.id).get(attempt_number)
            == "succeeded"
        )
        or (
            refund.refund_status in {"failed", "cancelled"}
            and refund_has_only_terminal_attempts(db, refund)
        )
    ):
        return None
    now = datetime.now(timezone.utc)
    if refund.provider_attempt_started_at is None:
        event = record_refund_event(
            db,
            refund=refund,
            event_type="local_status_changed",
            event_source="system",
            new_refund_status="failed",
            reason_code=error_code,
            summary="Unstarted refund attempt exhausted.",
            metadata={"provider_call_started": False},
            occurred_at=now,
        )
    else:
        refund.provider_status = "unknown"
        refund.provider_status_observed_at = now
        event = record_refund_event(
            db,
            refund=refund,
            event_type="provider_outcome_unknown",
            event_source="system",
            provider_status="unknown",
            reason_code=error_code,
            summary="Started refund attempt exhausted without a verified outcome.",
            occurred_at=now,
        )
    _sync_dependents(
        db,
        refund=refund,
        payment=payment,
        now=now,
        compensation_error_code=(
            error_code if refund.provider_attempt_started_at is not None else None
        ),
    )
    db.flush()
    try:
        with db.begin_nested():
            _stage_failure_issue(
                db,
                refund=refund,
                payment=payment,
                refund_event=event,
                reason_code=error_code,
            )
            db.flush()
    except Exception:  # noqa: BLE001 - support staging cannot block exhaustion.
        return "refund_support_staging_failed"
    return None
