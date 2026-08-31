"""Shared payment event helpers for routes and webhook processing."""

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import DurableJob, Payment, PaymentEvent
from backend.schemas.payment_event_schema import PaymentEventCreate, PaymentEventUpdate
from backend.services.durable_job_service import requeue_exhausted_job
from backend.services.payment_job_service import (
    PAYMENT_JOB_MAXIMUM_ATTEMPTS,
    STRIPE_WEBHOOK_EVENT_JOB,
    enqueue_webhook_event_job,
)
from backend.services.payment_rules import VALID_PROVIDERS
from backend.services.query_pagination import (
    DEFAULT_ADMIN_COLLECTION_LIMIT,
    MAX_ADMIN_COLLECTION_LIMIT,
    bounded_collection_limit,
    bounded_collection_offset,
)

VALID_PROCESSING_STATUSES = {
    "pending",
    "processing",
    "processed",
    "failed",
    "ignored",
}
IMMUTABLE_PAYMENT_EVENT_UPDATE_FIELDS = {
    "provider",
    "provider_event_id",
    "event_type",
    "event_envelope",
    "provider_created_at",
}


def build_payment_event_conflict_detail(exc: IntegrityError) -> str:
    error_text = str(exc.orig)

    if "uq_payment_events_provider_event_id" in error_text:
        return "This provider event has already been recorded."

    if "ck_payment_events_provider" in error_text:
        return "provider must be 'stripe'."

    if "ck_payment_events_processing_status" in error_text:
        return "processing_status is not supported."

    if "ck_payment_events_event_type_not_empty" in error_text:
        return "event_type must not be empty."

    return error_text


def get_payment_event_or_404(
    db: Session,
    payment_event_id: uuid.UUID,
) -> PaymentEvent:
    db_payment_event = db.get(PaymentEvent, payment_event_id)

    if db_payment_event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment event not found.",
        )

    return db_payment_event


def get_payment_or_404(db: Session, payment_id: uuid.UUID) -> Payment:
    db_payment = db.get(Payment, payment_id)

    if db_payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found.",
        )

    return db_payment


def validate_payment_event_business_rules(event_data: dict[str, Any]) -> None:
    for field_name in (
        "provider",
        "provider_event_id",
        "event_type",
        "event_envelope",
        "provider_created_at",
        "processing_status",
    ):
        if event_data[field_name] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} cannot be null.",
            )

    if event_data["provider"] not in VALID_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="provider must be 'stripe'.",
        )

    if event_data["processing_status"] not in VALID_PROCESSING_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "processing_status is not supported."
            ),
        )

    if not event_data["provider_event_id"].strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="provider_event_id must not be empty.",
        )

    if not event_data["event_type"].strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="event_type must not be empty.",
        )

    if event_data["processing_status"] == "failed" and not event_data["processing_error_code"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed payment events require processing_error_code.",
        )


def normalize_payment_event_lifecycle_fields(
    event_data: dict[str, Any],
) -> dict[str, Any]:
    normalized_data = dict(event_data)

    # processed_at is derived when an event is marked processed so clients do
    # not have to keep processing_status and timestamp fields aligned.
    if normalized_data["processing_status"] == "processed":
        normalized_data["processed_at"] = (
            normalized_data.get("processed_at") or datetime.now(timezone.utc)
        )
    elif normalized_data["processing_status"] != "processed":
        normalized_data["processed_at"] = None

    if normalized_data["processing_status"] != "failed":
        normalized_data["processing_error_code"] = None

    return normalized_data


def validate_payment_event_references(
    db: Session,
    event_data: dict[str, Any],
) -> None:
    if event_data["payment_id"] is not None:
        get_payment_or_404(db, event_data["payment_id"])


def validate_payment_event_update_fields(update_data: dict[str, Any]) -> None:
    immutable_fields = IMMUTABLE_PAYMENT_EVENT_UPDATE_FIELDS & update_data.keys()

    if immutable_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment event provider fields cannot be changed after creation.",
        )


def create_payment_event_record(
    db: Session,
    payload: PaymentEventCreate,
) -> PaymentEvent:
    event_data = normalize_payment_event_lifecycle_fields(payload.model_dump())
    validate_payment_event_business_rules(event_data)
    validate_payment_event_references(db, event_data)

    new_payment_event = PaymentEvent(
        id=uuid.uuid4(),
        **event_data,
    )

    try:
        db.add(new_payment_event)
        db.commit()
        db.refresh(new_payment_event)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_payment_event_conflict_detail(exc),
        ) from exc

    return new_payment_event


def get_payment_event_record(
    db: Session,
    payment_event_id: uuid.UUID,
) -> PaymentEvent:
    return get_payment_event_or_404(db, payment_event_id)


def list_payment_event_records(
    db: Session,
    *,
    payment_id: uuid.UUID | None = None,
    provider_event_id: str | None = None,
    event_type: str | None = None,
    processing_status: str | None = None,
    limit: int = DEFAULT_ADMIN_COLLECTION_LIMIT,
    offset: int = 0,
) -> list[PaymentEvent]:
    statement = select(PaymentEvent)

    if payment_id is not None:
        statement = statement.where(PaymentEvent.payment_id == payment_id)

    if provider_event_id is not None:
        statement = statement.where(PaymentEvent.provider_event_id == provider_event_id)

    if event_type is not None:
        statement = statement.where(PaymentEvent.event_type == event_type)

    if processing_status is not None:
        if processing_status not in VALID_PROCESSING_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "processing_status is not supported."
                ),
            )
        statement = statement.where(PaymentEvent.processing_status == processing_status)

    payment_events = db.scalars(
        statement.order_by(PaymentEvent.created_at.desc(), PaymentEvent.id.desc())
        .offset(bounded_collection_offset(offset))
        .limit(
            bounded_collection_limit(
                limit,
                max_limit=MAX_ADMIN_COLLECTION_LIMIT,
            )
        )
    ).all()
    return list(payment_events)


def update_payment_event_record(
    db: Session,
    payment_event_id: uuid.UUID,
    payload: PaymentEventUpdate,
) -> PaymentEvent:
    db_payment_event = get_payment_event_or_404(db, payment_event_id)

    update_data = payload.model_dump(exclude_unset=True)
    validate_payment_event_update_fields(update_data)

    payment_id = update_data.get("payment_id", db_payment_event.payment_id)
    if payment_id is not None:
        get_payment_or_404(db, payment_id)
    db_payment_event.payment_id = payment_id
    if update_data.get("reprocess"):
        job = db.scalars(
            select(DurableJob)
            .where(
                DurableJob.job_type == STRIPE_WEBHOOK_EVENT_JOB,
                DurableJob.origin_reference_type == "payment_event",
                DurableJob.origin_reference_id == str(db_payment_event.id),
            )
            .order_by(DurableJob.created_at.desc(), DurableJob.id.desc())
            .with_for_update()
            .limit(1)
        ).first()
        if job is None:
            enqueue_webhook_event_job(db, db_payment_event.id)
        elif job.status == "exhausted":
            requeue_exhausted_job(
                db,
                job_id=job.id,
                maximum_attempts=PAYMENT_JOB_MAXIMUM_ATTEMPTS,
                reason_code="payment_event_reprocess",
            )
        elif job.status not in {"pending", "retry_waiting", "leased"}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This payment event does not have requeueable durable work.",
            )
        db_payment_event.processing_status = "pending"
        db_payment_event.processed_at = None
        db_payment_event.processing_error_code = None

    try:
        db.add(db_payment_event)
        db.commit()
        db.refresh(db_payment_event)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_payment_event_conflict_detail(exc),
        ) from exc

    return db_payment_event
