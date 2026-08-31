"""Production durable-job registry and WS05-02 payment consumers."""

from __future__ import annotations

import uuid
from datetime import timedelta
from typing import Any

from sqlalchemy.orm import Session

from backend.models import DurableJob
from backend.services.durable_job_service import (
    DurableJobRegistry,
    HandlerResult,
    InvalidJobPayloadError,
    JobDefinition,
    enqueue_job,
)
from backend.services.payment_lifecycle_policy import (
    PAYMENT_JOB_MAXIMUM_ATTEMPTS,
    PAYMENT_METHOD_RECONCILE_RETRY_DELAYS_SECONDS,
    PAYMENT_RECONCILE_RETRY_DELAYS_SECONDS,
    WEBHOOK_RETRY_DELAYS_SECONDS,
    retry_delay_seconds,
)

STRIPE_WEBHOOK_EVENT_JOB = "stripe_webhook_event"
STRIPE_PAYMENT_INTENT_RECONCILE_JOB = "stripe_payment_intent_reconcile"
STRIPE_PAYMENT_METHOD_OPERATION_RECONCILE_JOB = (
    "stripe_payment_method_operation_reconcile"
)
PAYMENT_JOB_PAYLOAD_VERSION = 1


def _validate_uuid_only_payload(payload: dict[str, Any], key: str) -> None:
    if set(payload) != {key}:
        raise InvalidJobPayloadError(f"payload must contain only {key}")
    value = payload.get(key)
    if not isinstance(value, str):
        raise InvalidJobPayloadError(f"{key} must be a UUID string")
    try:
        uuid.UUID(value)
    except ValueError as exc:
        raise InvalidJobPayloadError(f"{key} must be a UUID string") from exc


def _webhook_payload(payload: dict[str, Any]) -> None:
    _validate_uuid_only_payload(payload, "payment_event_id")


def _payment_payload(payload: dict[str, Any]) -> None:
    _validate_uuid_only_payload(payload, "payment_id")


def _payment_method_payload(payload: dict[str, Any]) -> None:
    _validate_uuid_only_payload(payload, "payment_method_operation_id")


def _retry_result(job: DurableJob, code: str, schedule: tuple[int, ...]) -> HandlerResult:
    return HandlerResult.transient_failure(
        code,
        retry_delay=timedelta(
            seconds=retry_delay_seconds(job.attempt_count, schedule)
        ),
    )


def _handle_webhook(db: Session, job: DurableJob) -> HandlerResult:
    from backend.services.stripe_webhook_service import (
        mark_stored_event_exhausted,
        process_stored_stripe_event,
    )

    outcome = process_stored_stripe_event(
        db,
        uuid.UUID(job.payload["payment_event_id"]),
    )
    if outcome == "processed" or outcome == "ignored":
        return HandlerResult.success({"event_outcome": outcome})
    if outcome == "failed":
        return HandlerResult.permanent_failure("invalid_provider_event")
    if job.attempt_count >= job.maximum_attempts:
        mark_stored_event_exhausted(
            db,
            uuid.UUID(job.payload["payment_event_id"]),
        )
    return _retry_result(job, "provider_event_retry", WEBHOOK_RETRY_DELAYS_SECONDS)


def _handle_payment_reconcile(db: Session, job: DurableJob) -> HandlerResult:
    from backend.services.payment_transition_service import reconcile_payment_intent
    from backend.services.stripe_webhook_service import (
        expire_payment_checkout_hold_if_stale,
    )

    payment_id = uuid.UUID(job.payload["payment_id"])
    outcome = reconcile_payment_intent(db, payment_id)
    if outcome in {"processed", "already_terminal"}:
        return HandlerResult.success({"reconcile_outcome": outcome})
    if outcome == "permanent_failure":
        return HandlerResult.permanent_failure("payment_reconcile_invalid")
    if job.attempt_count >= job.maximum_attempts:
        expire_payment_checkout_hold_if_stale(db, payment_id)
    return _retry_result(
        job,
        "payment_reconcile_retry",
        PAYMENT_RECONCILE_RETRY_DELAYS_SECONDS,
    )


def _handle_payment_method_reconcile(db: Session, job: DurableJob) -> HandlerResult:
    from backend.services.payment_method_service import (
        reconcile_payment_method_operation,
    )

    outcome = reconcile_payment_method_operation(
        db,
        uuid.UUID(job.payload["payment_method_operation_id"]),
    )
    if outcome in {"succeeded", "failed"}:
        return HandlerResult.success({"operation_outcome": outcome})
    return _retry_result(
        job,
        "payment_method_reconcile_retry",
        PAYMENT_METHOD_RECONCILE_RETRY_DELAYS_SECONDS,
    )


def build_production_job_registry() -> DurableJobRegistry:
    return DurableJobRegistry(
        (
            JobDefinition(
                job_type=STRIPE_WEBHOOK_EVENT_JOB,
                payload_version=PAYMENT_JOB_PAYLOAD_VERSION,
                maximum_attempts=PAYMENT_JOB_MAXIMUM_ATTEMPTS,
                handler=_handle_webhook,
                payload_validator=_webhook_payload,
            ),
            JobDefinition(
                job_type=STRIPE_PAYMENT_INTENT_RECONCILE_JOB,
                payload_version=PAYMENT_JOB_PAYLOAD_VERSION,
                maximum_attempts=PAYMENT_JOB_MAXIMUM_ATTEMPTS,
                handler=_handle_payment_reconcile,
                payload_validator=_payment_payload,
            ),
            JobDefinition(
                job_type=STRIPE_PAYMENT_METHOD_OPERATION_RECONCILE_JOB,
                payload_version=PAYMENT_JOB_PAYLOAD_VERSION,
                maximum_attempts=PAYMENT_JOB_MAXIMUM_ATTEMPTS,
                handler=_handle_payment_method_reconcile,
                payload_validator=_payment_method_payload,
            ),
        )
    )


def enqueue_webhook_event_job(db: Session, event_id: uuid.UUID) -> DurableJob:
    return enqueue_job(
        db,
        registry=build_production_job_registry(),
        job_type=STRIPE_WEBHOOK_EVENT_JOB,
        payload_version=PAYMENT_JOB_PAYLOAD_VERSION,
        payload={"payment_event_id": str(event_id)},
        protected_identity={"payment_event_id": str(event_id)},
        idempotency_key=f"stripe-webhook-event:{event_id}:v1",
        origin_reference_type="payment_event",
        origin_reference_id=str(event_id),
    )


def enqueue_payment_reconcile_job(
    db: Session,
    payment_id: uuid.UUID,
    *,
    reason: str,
) -> DurableJob:
    if not reason or len(reason) > 120 or any(
        character not in "abcdefghijklmnopqrstuvwxyz0123456789_:-"
        for character in reason
    ):
        raise ValueError("payment reconciliation reason must be a safe label")
    return enqueue_job(
        db,
        registry=build_production_job_registry(),
        job_type=STRIPE_PAYMENT_INTENT_RECONCILE_JOB,
        payload_version=PAYMENT_JOB_PAYLOAD_VERSION,
        payload={"payment_id": str(payment_id)},
        protected_identity={
            "payment_id": str(payment_id),
            "reconciliation_kind": reason,
        },
        idempotency_key=f"stripe-payment-reconcile:{payment_id}:{reason}:v1",
        origin_reference_type="payment",
        origin_reference_id=str(payment_id),
    )


def enqueue_payment_method_reconcile_job(
    db: Session,
    operation_id: uuid.UUID,
) -> DurableJob:
    return enqueue_job(
        db,
        registry=build_production_job_registry(),
        job_type=STRIPE_PAYMENT_METHOD_OPERATION_RECONCILE_JOB,
        payload_version=PAYMENT_JOB_PAYLOAD_VERSION,
        payload={"payment_method_operation_id": str(operation_id)},
        protected_identity={"payment_method_operation_id": str(operation_id)},
        idempotency_key=f"stripe-payment-method-reconcile:{operation_id}:v1",
        origin_reference_type="payment_method_operation",
        origin_reference_id=str(operation_id),
    )
