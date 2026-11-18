"""F16 roster actions must enforce capacity, status, and payment boundaries."""

from datetime import date, timedelta

import pytest
from sqlalchemy import func, select

from backend.models import GameParticipant, Payment
from backend.tests.conftest import database_now
from backend.tests.factories import (
    make_booking,
    make_game,
    make_participant,
    make_saved_card,
    make_user,
)


def player(db, **overrides):
    return make_user(db, date_of_birth=date(1990, 1, 1), **overrides)


def active_count(db, game):
    return db.scalar(
        select(func.count(GameParticipant.id)).where(
            GameParticipant.game_id == game.id,
            GameParticipant.participant_status.in_(("confirmed", "waitlisted")),
        )
    )


@pytest.mark.page("F16", 5)
@pytest.mark.parametrize(
    "waitlist_enabled, expected_status", [(True, 201), (False, 400)]
)
def test_full_community_game_waitlist_policy(
    clock, db, client, firebase, waitlist_enabled, expected_status
):
    game = make_game(
        db,
        game_type="community",
        starts_at=clock.now + timedelta(days=2),
        total_spots=1,
        waitlist_enabled=waitlist_enabled,
    )
    make_participant(db, game=game, user=player(db))
    joining_player = player(db)

    response = client.post(
        f"/games/{game.id}/join", headers=firebase.sign_in(joining_player), json={}
    )

    assert response.status_code == expected_status, response.text
    if waitlist_enabled:
        assert response.json()["status"] == "waitlisted"
        assert active_count(db, game) == 2
    else:
        assert active_count(db, game) == 1


@pytest.mark.page("F16", 7)
def test_booked_player_removes_guest_without_leaving(clock, db, client, firebase):
    game = make_game(
        db,
        game_type="community",
        starts_at=clock.now + timedelta(days=2),
        allow_guests=True,
        max_guests_per_booking=2,
    )
    owner = player(db)
    booking = make_booking(db, game=game, buyer=owner, participant_count=2)
    owner_participant = make_participant(db, game=game, booking=booking, user=owner)
    guest = make_participant(
        db, game=game, booking=booking, user=owner, participant_type="guest"
    )

    response = client.post(
        f"/games/{game.id}/guests/remove",
        headers=firebase.sign_in(owner),
        json={"remove_count": 1},
    )

    assert response.status_code == 200, response.text
    assert response.json()["removed_count"] == 1
    db.refresh(owner_participant)
    db.refresh(guest)
    assert owner_participant.participant_status == "confirmed"
    assert guest.participant_status not in ("confirmed", "waitlisted")


@pytest.mark.page("F16", 7)
def test_community_checkout_guest_addition_updates_booking_and_roster(
    clock, db, client, firebase
):
    game = make_game(
        db,
        game_type="community",
        starts_at=clock.now + timedelta(days=2),
        allow_guests=True,
        max_guests_per_booking=2,
    )
    owner = player(db)
    booking = make_booking(db, game=game, buyer=owner)
    make_participant(db, game=game, booking=booking, user=owner)

    response = client.post(
        f"/games/{game.id}/booking-guests/add",
        headers=firebase.sign_in(owner),
        json={"guest_count": 1},
    )

    assert response.status_code == 201, response.text
    assert response.json()["added_count"] == 1
    db.refresh(booking)
    assert booking.participant_count == 2
    assert active_count(db, game) == 2
    assert db.scalar(select(func.count(Payment.id))) == 0


@pytest.mark.page("F16", 8)
def test_host_guest_limit_and_capacity_are_checked_by_api(clock, db, client, firebase):
    host = player(db)
    game = make_game(
        db,
        game_type="community",
        host=host,
        starts_at=clock.now + timedelta(days=2),
        total_spots=2,
        allow_guests=True,
        host_guest_max=1,
    )
    headers = firebase.sign_in(host)
    too_many = client.post(
        f"/games/{game.id}/guests/add", headers=headers, json={"guest_count": 2}
    )
    assert too_many.status_code == 400
    assert active_count(db, game) == 0

    first = client.post(
        f"/games/{game.id}/guests/add", headers=headers, json={"guest_count": 1}
    )
    second = client.post(
        f"/games/{game.id}/guests/add", headers=headers, json={"guest_count": 1}
    )
    assert first.status_code == 201, first.text
    assert second.status_code == 400
    assert active_count(db, game) == 1


@pytest.mark.page("F16", 15)
def test_stale_guest_addition_after_capacity_change_creates_no_guest(
    clock, db, client, firebase
):
    host = player(db)
    game = make_game(
        db,
        game_type="community",
        host=host,
        starts_at=clock.now + timedelta(days=2),
        total_spots=1,
        allow_guests=True,
        host_guest_max=2,
    )
    make_participant(db, game=game, user=player(db))

    response = client.post(
        f"/games/{game.id}/guests/add",
        headers=firebase.sign_in(host),
        json={"guest_count": 1},
    )

    assert response.status_code == 400
    assert active_count(db, game) == 1


@pytest.mark.page("F16", 16)
def test_cancelled_game_stays_visible_but_rejects_join_and_chat(
    clock, db, client, firebase
):
    game = make_game(
        db,
        game_type="community",
        starts_at=clock.now + timedelta(days=2),
        game_status="cancelled",
        cancelled_at=clock.now,
    )
    joining_player = player(db)
    headers = firebase.sign_in(joining_player)

    detail = client.get(f"/games/{game.id}")
    join = client.post(f"/games/{game.id}/join", headers=headers, json={})
    chat = client.post(f"/game-chats/for-game/{game.id}", headers=headers, json={})

    assert detail.status_code == 200
    assert detail.json()["game_status"] == "cancelled"
    assert join.status_code == 400
    assert chat.status_code in (400, 403, 404)
    assert active_count(db, game) == 0


@pytest.mark.page("F16", 20)
def test_suspended_player_cannot_add_checkout_guests_to_existing_booking(
    clock, db, client, firebase
):
    game = make_game(
        db,
        game_type="community",
        starts_at=clock.now + timedelta(days=2),
        allow_guests=True,
        max_guests_per_booking=2,
    )
    owner = make_user(db, date_of_birth=date(1990, 1, 1), account_status="suspended")
    booking = make_booking(db, game=game, buyer=owner)
    make_participant(db, game=game, booking=booking, user=owner)

    response = client.post(
        f"/games/{game.id}/booking-guests/add",
        headers=firebase.sign_in(owner),
        json={"guest_count": 1},
    )

    assert response.status_code == 403
    assert active_count(db, game) == 1


@pytest.mark.page("F16", 22)
def test_paid_official_guests_cannot_skip_the_checkout_charge(
    clock, db, client, firebase
):
    game = make_game(
        db,
        starts_at=clock.now + timedelta(days=2),
        allow_guests=True,
        max_guests_per_booking=2,
    )
    owner = player(db)
    booking = make_booking(db, game=game, buyer=owner)
    make_participant(db, game=game, booking=booking, user=owner)

    response = client.post(
        f"/games/{game.id}/booking-guests/add",
        headers=firebase.sign_in(owner),
        json={"guest_count": 1},
    )

    assert response.status_code == 503
    assert active_count(db, game) == 1
    assert db.scalar(select(func.count(Payment.id))) == 0


@pytest.mark.page("F16", 5)
def test_paid_official_join_cannot_bypass_secure_checkout(clock, db, client, firebase):
    game = make_game(db, starts_at=clock.now + timedelta(days=2))
    joining_player = player(db)

    response = client.post(
        f"/games/{game.id}/join",
        headers=firebase.sign_in(joining_player),
        json={},
    )

    assert response.status_code == 503
    assert active_count(db, game) == 0
    assert db.scalar(select(func.count(Payment.id))) == 0


@pytest.mark.page("F16", 22)
def test_paid_official_guests_are_added_after_their_charge_succeeds(
    db, client, firebase, stripe
):
    game = make_game(
        db,
        starts_at=database_now(db) + timedelta(days=2),
        allow_guests=True,
        max_guests_per_booking=2,
    )
    owner = player(db, stripe_customer_id="cus_test_f16_owner")
    card = make_saved_card(db, user=owner)
    booking = make_booking(db, game=game, buyer=owner)
    make_participant(db, game=game, booking=booking, user=owner)

    response = client.post(
        f"/checkout/games/{game.id}/guest-payment-intent",
        headers=firebase.sign_in(owner),
        json={"guest_count": 1, "payment_method_id": str(card.id)},
    )

    assert response.status_code == 201, response.text
    payment = db.scalars(select(Payment).where(Payment.booking_id == booking.id)).one()
    assert (payment.amount_cents, payment.payment_status) == (1000, "succeeded")
    assert active_count(db, game) == 2
    db.refresh(booking)
    assert booking.participant_count == 2
