import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import PaymentEvent
from backend.services.payment_event_service import build_payment_event_conflict_detail
from backend.services.stripe_service import StripeConfigError, construct_webhook_event
from backend.services.stripe_webhook_service import process_stripe_event

router = APIRouter(prefix="/stripe", tags=["stripe"])


def stripe_object_to_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value

    if hasattr(value, "to_dict_recursive"):
        return value.to_dict_recursive()

    if hasattr(value, "to_dict"):
        return value.to_dict()

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Stripe webhook payload could not be parsed.",
    )


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def handle_stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(None, alias="Stripe-Signature"),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    if not stripe_signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe-Signature header.",
        )

    payload = await request.body()
    try:
        stripe_event = construct_webhook_event(payload, stripe_signature)
    except StripeConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Stripe webhook signature or payload.",
        ) from exc

    event_payload = stripe_object_to_dict(stripe_event)
    provider_event_id = event_payload.get("id")
    event_type = event_payload.get("type")
    if not isinstance(provider_event_id, str) or not provider_event_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stripe event is missing id.",
        )

    if not isinstance(event_type, str) or not event_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stripe event is missing type.",
        )

    existing_event = db.scalars(
        select(PaymentEvent)
        .where(PaymentEvent.provider_event_id == provider_event_id)
        .limit(1)
    ).first()
    if existing_event is not None:
        return {
            "received": True,
            "duplicate": True,
            "processing_status": existing_event.processing_status,
        }

    now = datetime.now(timezone.utc)
    payment_event = PaymentEvent(
        id=uuid.uuid4(),
        payment_id=None,
        provider="stripe",
        provider_event_id=provider_event_id,
        event_type=event_type,
        raw_payload=event_payload,
        processing_status="pending",
        processed_at=None,
        processing_error=None,
        created_at=now,
    )

    try:
        db.add(payment_event)
        process_stripe_event(db, payment_event, event_payload, now)
        db.add(payment_event)
        db.commit()
        db.refresh(payment_event)
    except IntegrityError as exc:
        db.rollback()
        if "uq_payment_events_provider_event_id" in str(exc.orig):
            return {
                "received": True,
                "duplicate": True,
                "processing_status": "duplicate",
            }

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_payment_event_conflict_detail(exc),
        ) from exc

    return {
        "received": True,
        "duplicate": False,
        "processing_status": payment_event.processing_status,
    }
