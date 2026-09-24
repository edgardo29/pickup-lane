from types import SimpleNamespace
from uuid import uuid4

import pytest

pytestmark = [
    pytest.mark.suite_type("ordinary"),
    pytest.mark.no_db_cleanup,
    pytest.mark.requirement("WS05-03A-R4"),
]


@pytest.mark.parametrize("payment_status", ["partially_refunded", "refunded", "credit_restored"])
def test_generic_booking_create_and_update_reject_financial_summaries(
    payment_status: str,
) -> None:
    from fastapi import HTTPException

    from backend.schemas.booking_schema import BookingCreate, BookingUpdate
    from backend.services.booking_service import (
        create_booking_workflow,
        update_booking_workflow,
    )

    create = BookingCreate(
        game_id=uuid4(),
        buyer_user_id=uuid4(),
        booking_status="cancelled",
        payment_status=payment_status,
        reservation_status="released",
        participant_count=1,
        subtotal_cents=100,
        total_cents=100,
        price_per_player_snapshot_cents=100,
        cancelled_by_user_id=uuid4(),
    )
    with pytest.raises(HTTPException) as create_error:
        create_booking_workflow(SimpleNamespace(), create)
    assert create_error.value.status_code == 400

    booking = SimpleNamespace(id=uuid4())
    db = SimpleNamespace(get=lambda _model, _booking_id: booking)
    with pytest.raises(HTTPException) as update_error:
        update_booking_workflow(
            db, booking.id, BookingUpdate(payment_status=payment_status)
        )
    assert update_error.value.status_code == 400


@pytest.mark.parametrize(
    ("booking_status", "reservation_status"),
    [
        ("confirmed", "confirmed"),
        ("expired", "released"),
        ("capacity_conflict", "capacity_conflict"),
        ("partially_cancelled", "confirmed"),
        ("cancelled", "released"),
    ],
)
def test_committed_refund_summary_is_valid_across_retained_lifecycle_states(
    booking_status: str,
    reservation_status: str,
) -> None:
    from backend.services.booking_rules import validate_booking_business_rules

    validate_booking_business_rules(
        {
            "game_id": uuid4(),
            "buyer_user_id": uuid4(),
            "booking_status": booking_status,
            "payment_status": "refunded",
            "reservation_status": reservation_status,
            "participant_count": 1,
            "subtotal_cents": 100,
            "platform_fee_cents": 0,
            "discount_cents": 0,
            "total_cents": 100,
            "currency": "USD",
            "price_per_player_snapshot_cents": 100,
            "platform_fee_snapshot_cents": 0,
            "booked_at": None,
            "cancelled_at": None,
            "cancelled_by_user_id": uuid4()
            if booking_status in {"cancelled", "partially_cancelled"}
            else None,
            "cancel_reason": None,
            "expires_at": None,
        }
    )
