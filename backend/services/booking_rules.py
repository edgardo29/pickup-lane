"""Booking constants, validation, and lifecycle normalization."""

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from backend.models import Booking

VALID_BOOKING_STATUSES = {
    "pending_payment",
    "confirmed",
    "waitlisted",
    "partially_cancelled",
    "cancelled",
    "expired",
    "failed",
}
VALID_PAYMENT_STATUSES = {
    "not_required",
    "unpaid",
    "requires_action",
    "processing",
    "paid",
    "failed",
    "partially_refunded",
    "refunded",
    "credit_restored",
    "disputed",
}
VALID_CURRENCY = "USD"
CANCELLED_BOOKING_STATUSES = {"cancelled", "partially_cancelled"}
BOOKED_BOOKING_STATUSES = {"confirmed", "partially_cancelled", "cancelled"}


def build_booking_conflict_detail(exc: IntegrityError) -> str:
    return str(exc.orig)


def validate_booking_status(value: str) -> None:
    if value not in VALID_BOOKING_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "booking_status must be 'pending_payment', 'confirmed', "
                "'waitlisted', 'partially_cancelled', 'cancelled', "
                "'expired', or 'failed'."
            ),
        )


def validate_booking_payment_status(value: str) -> None:
    if value not in VALID_PAYMENT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "payment_status must be 'unpaid', 'requires_action', "
                "'not_required', 'processing', 'paid', 'failed', "
                "'partially_refunded', 'refunded', 'credit_restored', "
                "or 'disputed'."
            ),
        )


def validate_booking_business_rules(booking_data: dict[str, object]) -> None:
    validate_booking_status(booking_data["booking_status"])
    validate_booking_payment_status(booking_data["payment_status"])

    if booking_data["currency"] != VALID_CURRENCY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="currency must be 'USD'.",
        )

    if booking_data["participant_count"] <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="participant_count must be greater than 0.",
        )

    for field_name in (
        "subtotal_cents",
        "platform_fee_cents",
        "discount_cents",
        "total_cents",
        "price_per_player_snapshot_cents",
        "platform_fee_snapshot_cents",
    ):
        if booking_data[field_name] < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} must be greater than or equal to 0.",
            )

    expected_total = (
        booking_data["subtotal_cents"]
        + booking_data["platform_fee_cents"]
        - booking_data["discount_cents"]
    )
    if booking_data["total_cents"] != expected_total:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "total_cents must equal subtotal_cents + "
                "platform_fee_cents - discount_cents."
            ),
        )

    if (
        booking_data["booking_status"] == "confirmed"
        and booking_data["payment_status"] not in {"paid", "not_required"}
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmed bookings require payment_status 'paid' or 'not_required'.",
        )

    if (
        booking_data["booking_status"] == "failed"
        and booking_data["payment_status"] != "failed"
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed bookings require payment_status 'failed'.",
        )

    if (
        booking_data["payment_status"]
        in {"refunded", "partially_refunded", "credit_restored"}
        and booking_data["booking_status"] not in CANCELLED_BOOKING_STATUSES
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Refunded, partially_refunded, or credit_restored bookings must have "
                "booking_status 'cancelled' or 'partially_cancelled'."
            ),
        )

    if (
        booking_data["booking_status"] in CANCELLED_BOOKING_STATUSES
        and booking_data["cancelled_by_user_id"] is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Cancelled or partially_cancelled bookings require "
                "cancelled_by_user_id."
            ),
        )


def normalize_booking_lifecycle_fields(
    booking_data: dict[str, object],
    existing_booking: Booking | None = None,
) -> dict[str, object]:
    normalized_data = dict(booking_data)
    now = datetime.now(timezone.utc)

    if normalized_data["booking_status"] in BOOKED_BOOKING_STATUSES:
        normalized_data["booked_at"] = (
            normalized_data.get("booked_at")
            or (existing_booking.booked_at if existing_booking is not None else None)
            or now
        )
    else:
        normalized_data["booked_at"] = None

    if normalized_data["booking_status"] in CANCELLED_BOOKING_STATUSES:
        normalized_data["cancelled_at"] = (
            normalized_data.get("cancelled_at")
            or (
                existing_booking.cancelled_at
                if existing_booking is not None
                else None
            )
            or now
        )
    else:
        normalized_data["cancelled_at"] = None
        normalized_data["cancelled_by_user_id"] = None
        normalized_data["cancel_reason"] = None

    return normalized_data
