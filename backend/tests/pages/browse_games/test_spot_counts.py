"""Filled-spot counts on Browse game cards.

Filled spots include confirmed players and guests, and checkout holds only while
the hold is unexpired. Other participant statuses never fill a spot.
"""

from datetime import UTC, datetime, timedelta

import pytest

from backend.tests.factories import (
    make_game,
    make_held_booking,
    make_participant,
    make_user,
)


def chicago(hour: int) -> datetime:
    """A time on 2026-06-15 in America/Chicago (UTC-5 during daylight saving)."""
    return datetime(2026, 6, 15, hour, tzinfo=UTC) + timedelta(hours=5)


def browse_card(client) -> dict:
    response = client.get("/games/browse")
    assert response.status_code == 200, response.text
    return response.json()["games"][0]


@pytest.mark.page("F15", 9)
def test_confirmed_player_and_their_guest_each_fill_a_spot(clock, db, client):
    game = make_game(db, starts_at=chicago(18), total_spots=10)
    player = make_user(db)
    make_participant(db, game=game, user=player)
    make_participant(db, game=game, user=player, participant_type="guest")

    card = browse_card(client)

    assert card["participant_count"] == 2
    assert card["availability"]["occupied_spots"] == 2
    assert card["availability"]["spots_remaining"] == 8


@pytest.mark.page("F15", 9)
@pytest.mark.parametrize(
    "participant_status",
    ["waitlisted", "cancelled", "late_cancelled", "removed", "refunded"],
)
def test_participant_that_is_not_confirmed_does_not_fill_a_spot(
    clock, db, client, participant_status
):
    game = make_game(db, starts_at=chicago(18), total_spots=10)
    make_participant(db, game=game, participant_status=participant_status)

    card = browse_card(client)

    assert card["participant_count"] == 0
    assert card["availability"]["spots_remaining"] == 10


@pytest.mark.page("F15", 10)
@pytest.mark.parametrize("payment_status", ["processing", "requires_action"])
def test_unexpired_checkout_hold_fills_a_spot(clock, db, client, payment_status):
    game = make_game(db, starts_at=chicago(18), total_spots=10)
    booking = make_held_booking(
        db,
        game=game,
        expires_at=clock.now + timedelta(seconds=1),
        payment_status=payment_status,
    )
    make_participant(
        db, game=game, booking=booking, participant_status="pending_payment"
    )

    card = browse_card(client)

    assert card["participant_count"] == 1


@pytest.mark.page("F15", 10)
@pytest.mark.parametrize(
    "expires_after_now",
    [timedelta(0), -timedelta(seconds=1)],
    ids=["expires-exactly-now", "already-expired"],
)
def test_expired_checkout_hold_stops_filling_a_spot_before_cleanup(
    clock, db, client, expires_after_now
):
    game = make_game(db, starts_at=chicago(18), total_spots=10)
    booking = make_held_booking(db, game=game, expires_at=clock.now + expires_after_now)
    make_participant(
        db, game=game, booking=booking, participant_status="pending_payment"
    )

    card = browse_card(client)

    assert card["participant_count"] == 0


@pytest.mark.page("F15", 10)
def test_checkout_that_has_not_started_payment_does_not_fill_a_spot(clock, db, client):
    # A hold exists only while payment is in progress (Game Checkout spec,
    # Section 4.2: "A temporary paid-checkout hold lasts two minutes").
    game = make_game(db, starts_at=chicago(18), total_spots=10)
    booking = make_held_booking(
        db,
        game=game,
        expires_at=clock.now + timedelta(minutes=2),
        payment_status="unpaid",
    )
    make_participant(
        db, game=game, booking=booking, participant_status="pending_payment"
    )

    card = browse_card(client)

    assert card["participant_count"] == 0
