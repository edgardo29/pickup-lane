from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services.stripe_service import StripeConfigError, construct_webhook_event
from backend.services.stripe_webhook_service import (
    record_and_process_stripe_webhook_event,
)

router = APIRouter(prefix="/stripe", tags=["stripe"])


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

    return record_and_process_stripe_webhook_event(db, stripe_event)
