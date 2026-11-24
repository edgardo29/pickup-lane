"""Browse counts confirmed places and only unexpired payment holds."""

from datetime import timedelta

import pytest

from backend.tests.factories import (
    make_booking,
    make_held_booking,
    make_participant,
    make_user,
)


@pytest.mark.page("F15", 9)
@pytest.mark.parametrize("participant_type", ["registered_user", "host", "admin_added"])
def test_confirmed_player_fills_a_spot(
    clock, db, browse_game, browse, participant_type
):
    game = browse_game(starts_at=clock.now + timedelta(hours=6), total_spots=10)
    make_participant(db, game=game, participant_type=participant_type)
    card = browse()["games"][0]
    assert card["participant_count"] == 1
    assert card["availability"]["occupied_spots"] == 1
    assert card["availability"]["spots_remaining"] == 9


@pytest.mark.page("F15", 9)
def test_confirmed_guest_fills_a_spot(clock, db, browse_game, browse):
    game = browse_game(starts_at=clock.now + timedelta(hours=6), total_spots=10)
    player = make_user(db)
    booking = make_booking(db, game=game, buyer=player, participant_count=2)
    make_participant(db, game=game, booking=booking, user=player)
    make_participant(
        db, game=game, booking=booking, user=player, participant_type="guest"
    )
    card = browse()["games"][0]
    assert card["participant_count"] == 2
    assert card["availability"]["occupied_spots"] == 2
    assert card["availability"]["spots_remaining"] == 8


@pytest.mark.page("F15", 9)
@pytest.mark.parametrize(
    "participant_status",
    ["waitlisted", "cancelled", "late_cancelled", "removed", "refunded"],
)
def test_participant_that_is_not_confirmed_does_not_fill_a_spot(
    clock, db, browse_game, browse, participant_status
):
    game = browse_game(starts_at=clock.now + timedelta(hours=6), total_spots=10)
    make_participant(db, game=game, participant_status=participant_status)
    card = browse()["games"][0]
    assert card["participant_count"] == 0
    assert card["availability"]["occupied_spots"] == 0
    assert card["availability"]["spots_remaining"] == 10


@pytest.mark.page("F15", 10)
@pytest.mark.parametrize("payment_status", ["processing", "requires_action"])
def test_unexpired_checkout_hold_fills_a_spot(
    clock, db, browse_game, browse, payment_status
):
    game = browse_game(starts_at=clock.now + timedelta(hours=6), total_spots=10)
    booking = make_held_booking(
        db,
        game=game,
        expires_at=clock.now + timedelta(seconds=1),
        payment_status=payment_status,
    )
    make_participant(
        db, game=game, booking=booking, participant_status="pending_payment"
    )
    card = browse()["games"][0]
    assert card["participant_count"] == 1
    assert card["availability"]["occupied_spots"] == 1
    assert card["availability"]["spots_remaining"] == 9


@pytest.mark.page("F15", 10)
@pytest.mark.parametrize("seconds", [0, -1])
def test_expired_checkout_hold_stops_filling_a_spot_before_cleanup(
    clock, db, browse_game, browse, seconds
):
    game = browse_game(starts_at=clock.now + timedelta(hours=6))
    booking = make_held_booking(
        db, game=game, expires_at=clock.now + timedelta(seconds=seconds)
    )
    participant = make_participant(
        db, game=game, booking=booking, participant_status="pending_payment"
    )
    assert browse()["games"][0]["participant_count"] == 0
    db.refresh(booking)
    db.refresh(participant)
    assert booking.booking_status == "pending_payment"
    assert participant.participant_status == "pending_payment"


@pytest.mark.page("F15", 10)
@pytest.mark.parametrize(
    "payment_status",
    [
        "not_required",
        "unpaid",
        "paid",
        "failed",
        "partially_refunded",
        "refunded",
        "credit_restored",
        "disputed",
    ],
)
def test_checkout_without_an_active_payment_does_not_fill_a_spot(
    clock, db, browse_game, browse, payment_status
):
    game = browse_game(starts_at=clock.now + timedelta(hours=6))
    # Released attempts are never holds; active-status qualification is checked
    # separately from reservation lifecycle by using valid pending rows where possible.
    if payment_status in {"partially_refunded", "refunded", "credit_restored"}:
        booking = make_booking(
            db,
            game=game,
            booking_status="failed",
            reservation_status="released",
            payment_status=payment_status,
            expires_at=None,
            booked_at=None,
        )
    else:
        booking = make_held_booking(
            db,
            game=game,
            expires_at=clock.now + timedelta(minutes=2),
            payment_status=payment_status,
        )
    make_participant(
        db, game=game, booking=booking, participant_status="pending_payment"
    )
    assert browse()["games"][0]["participant_count"] == 0


@pytest.mark.page("F15", 10)
def test_unexpired_additional_guest_hold_fills_a_spot(clock, db, browse_game, browse):
    game = browse_game(starts_at=clock.now + timedelta(hours=6), total_spots=10)
    buyer = make_user(db)
    booking = make_booking(db, game=game, buyer=buyer)
    make_participant(db, game=game, user=buyer, booking=booking)
    make_participant(
        db,
        game=game,
        user=buyer,
        booking=booking,
        participant_type="guest",
        participant_status="pending_payment",
        hold_expires_at=clock.now + timedelta(seconds=1),
    )
    card = browse()["games"][0]
    assert card["participant_count"] == 2
    assert card["availability"]["spots_remaining"] == 8


@pytest.mark.page("F15", 10)
@pytest.mark.parametrize("seconds", [0, -1])
def test_expired_additional_guest_hold_stops_filling_a_spot(
    clock, db, browse_game, browse, seconds
):
    game = browse_game(starts_at=clock.now + timedelta(hours=6))
    buyer = make_user(db)
    booking = make_booking(db, game=game, buyer=buyer)
    make_participant(db, game=game, user=buyer, booking=booking)
    guest = make_participant(
        db,
        game=game,
        user=buyer,
        booking=booking,
        participant_type="guest",
        participant_status="pending_payment",
        hold_expires_at=clock.now + timedelta(seconds=seconds),
    )
    assert browse()["games"][0]["participant_count"] == 1
    db.refresh(guest)
    assert guest.participant_status == "pending_payment"


@pytest.mark.page("F15", 34)
def test_full_game_count_drops_when_a_hold_expires(clock, db, browse_game, browse):
    game = browse_game(starts_at=clock.now + timedelta(hours=6), total_spots=6)
    for _ in range(5):
        make_participant(db, game=game)
    booking = make_held_booking(
        db, game=game, expires_at=clock.now + timedelta(seconds=1)
    )
    make_participant(
        db, game=game, booking=booking, participant_status="pending_payment"
    )
    before = browse()["games"][0]
    clock.advance(timedelta(seconds=1))
    after = browse()["games"][0]
    assert before["participant_count"] == 6
    assert after["participant_count"] == 5
    assert after["availability"]["spots_remaining"] == 1
