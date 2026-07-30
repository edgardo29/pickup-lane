from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy.exc import IntegrityError

from backend.database import SessionLocal
from backend.models import Booking
from backend.tests.support.api_helpers import create_game, create_venue
from backend.tests.support.factories import create_user


def _assert_constraint_failed(exc_info, name: str) -> None:
    original_error = exc_info.value.orig
    diagnostic = getattr(original_error, "diag", None)
    constraint_name = getattr(diagnostic, "constraint_name", None)

    if constraint_name is not None:
        assert constraint_name == name
        return

    assert name in str(original_error)


def _build_booking_row(
    *,
    game_id: str,
    buyer_user_id: str,
    booking_status: str = "pending_payment",
    payment_status: str = "processing",
    expires_at: datetime | None = None,
) -> Booking:
    return Booking(
        id=uuid4(),
        game_id=UUID(game_id),
        buyer_user_id=UUID(buyer_user_id),
        booking_status=booking_status,
        payment_status=payment_status,
        participant_count=1,
        subtotal_cents=1200,
        platform_fee_cents=100,
        discount_cents=0,
        total_cents=1300,
        currency="USD",
        price_per_player_snapshot_cents=1200,
        platform_fee_snapshot_cents=100,
        expires_at=expires_at,
    )


def test_pending_payment_booking_without_expires_at_is_rejected_by_database(
    client: TestClient,
):
    admin = create_user(client)
    buyer = create_user(client)
    venue = create_venue(client, admin["id"])
    game = create_game(client, admin["id"], venue)
    booking = _build_booking_row(
        game_id=game["id"],
        buyer_user_id=buyer["id"],
        booking_status="pending_payment",
        payment_status="processing",
        expires_at=None,
    )
    booking_id = booking.id

    with SessionLocal() as db:
        db.add(booking)

        with pytest.raises(IntegrityError) as exc_info:
            db.commit()

        _assert_constraint_failed(
            exc_info,
            "ck_bookings_pending_payment_requires_expires_at",
        )
        db.rollback()
        assert db.get(Booking, booking_id) is None


def test_unknown_booking_payment_status_is_rejected_by_database(
    client: TestClient,
):
    admin = create_user(client)
    buyer = create_user(client)
    venue = create_venue(client, admin["id"])
    game = create_game(client, admin["id"], venue)
    booking = _build_booking_row(
        game_id=game["id"],
        buyer_user_id=buyer["id"],
        booking_status="pending_payment",
        payment_status="mystery_status",
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
    )
    booking_id = booking.id

    with SessionLocal() as db:
        db.add(booking)

        with pytest.raises(IntegrityError) as exc_info:
            db.commit()

        _assert_constraint_failed(exc_info, "ck_bookings_payment_status")
        db.rollback()
        assert db.get(Booking, booking_id) is None
