"""Saved payment method validation shared by checkout-style flows."""

import uuid
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.models import User, UserPaymentMethod
from backend.services.stripe_service import StripeConfigError, retrieve_payment_method

ACTIVE_PAYMENT_METHOD_STATUS = "active"


def is_saved_payment_method_expired(
    payment_method: UserPaymentMethod,
    now: datetime,
) -> bool:
    return (
        payment_method.exp_year < now.year
        or (
            payment_method.exp_year == now.year
            and payment_method.exp_month < now.month
        )
    )


def get_current_user_saved_payment_method_for_checkout(
    db: Session,
    payment_method_id: uuid.UUID | None,
    current_user: User,
    *,
    now: datetime,
) -> UserPaymentMethod | None:
    if payment_method_id is None:
        return None

    payment_method = db.get(UserPaymentMethod, payment_method_id)
    if payment_method is None or payment_method.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment method not found.",
        )

    if payment_method.method_status != ACTIVE_PAYMENT_METHOD_STATUS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only active payment methods can be used for checkout.",
        )

    if is_saved_payment_method_expired(payment_method, now):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This saved card is expired. Choose another card.",
        )

    if (
        not current_user.stripe_customer_id
        or payment_method.stripe_customer_id != current_user.stripe_customer_id
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This payment method is not linked to your Stripe customer.",
        )

    verify_saved_payment_method_with_stripe(payment_method, current_user, now)

    return payment_method


def verify_saved_payment_method_with_stripe(
    payment_method: UserPaymentMethod,
    current_user: User,
    now: datetime,
) -> None:
    try:
        stripe_payment_method = retrieve_payment_method(
            payment_method.stripe_payment_method_id
        )
    except StripeConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This saved card could not be verified. Choose another card.",
        ) from exc

    if (
        stripe_payment_method.customer_id != current_user.stripe_customer_id
        or stripe_payment_method.customer_id != payment_method.stripe_customer_id
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This saved card is no longer linked to your Stripe customer.",
        )

    if stripe_payment_method.card_fingerprint != payment_method.card_fingerprint:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This saved card no longer matches the saved card details.",
        )

    if is_saved_payment_method_expired(stripe_payment_method, now):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This saved card is expired. Choose another card.",
        )
