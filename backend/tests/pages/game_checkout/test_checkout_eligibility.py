"""F17 eligibility and whole-party registration."""

from datetime import timedelta

import pytest
from sqlalchemy import select

from backend.models import Booking, GameParticipant, Payment, User
from backend.tests.conftest import database_now
from backend.tests.factories import (
    make_booking,
    make_community_game_detail,
    make_participant,
)
from backend.tests.pages.game_checkout.conftest import (
    financial_and_attendance_state,
    paying_player,
    submit_checkout,
    upcoming_game,
)


def community(db, *, price=0, total_spots=14, waitlist_enabled=True):
    game = upcoming_game(
        db,
        game_type="community",
        price_per_player_cents=price,
        total_spots=total_spots,
        waitlist_enabled=waitlist_enabled,
    )
    make_community_game_detail(db, game=game)
    make_participant(db, game=game, user=db.get(User, game.host_user_id), price_cents=0)
    return game


def assert_unchanged(db, before, stripe):
    assert financial_and_attendance_state(db) == before
    assert stripe.created == []


@pytest.mark.page("F17", 2)
def test_free_community_whole_party_joins(db, client, firebase, stripe):
    game = community(db, price=0)
    user, _card = paying_player(db, stripe)
    response = client.post(
        f"/games/{game.id}/join",
        headers=firebase.sign_in(user),
        json={"guest_count": 2},
    )
    assert response.status_code == 201, response.text
    booking = db.scalars(
        select(Booking).where(
            Booking.buyer_user_id == user.id, Booking.game_id == game.id
        )
    ).one()
    assert response.json()["status"] == "joined"
    assert booking.participant_count == 3
    assert (
        db.scalars(
            select(GameParticipant.participant_status).where(
                GameParticipant.booking_id == booking.id
            )
        ).all()
        == ["confirmed"] * 3
    )


@pytest.mark.page("F17", 2)
def test_host_paid_community_whole_party_joins(db, client, firebase, stripe):
    game = community(db, price=1000)
    user, _card = paying_player(db, stripe)
    response = client.post(
        f"/games/{game.id}/join",
        headers=firebase.sign_in(user),
        json={"guest_count": 2},
    )
    assert response.status_code == 201, response.text
    booking = db.scalars(
        select(Booking).where(
            Booking.buyer_user_id == user.id, Booking.game_id == game.id
        )
    ).one()
    assert response.json()["status"] == "joined"
    assert booking.participant_count == 3
    assert (
        db.scalars(
            select(GameParticipant.participant_status).where(
                GameParticipant.booking_id == booking.id
            )
        ).all()
        == ["confirmed"] * 3
    )


@pytest.mark.page("F17", 2)
def test_free_community_has_no_app_charge(db, client, firebase, stripe):
    game = community(db, price=0)
    user, _card = paying_player(db, stripe)
    response = client.post(
        f"/games/{game.id}/join",
        headers=firebase.sign_in(user),
        json={"guest_count": 2},
    )
    assert response.status_code == 201, response.text
    booking = db.scalars(
        select(Booking).where(
            Booking.buyer_user_id == user.id, Booking.game_id == game.id
        )
    ).one()
    assert booking.payment_status == "not_required"
    assert (
        db.scalars(select(Payment).where(Payment.booking_id == booking.id)).all() == []
    )
    assert stripe.created == []


@pytest.mark.page("F17", 2)
def test_host_paid_community_has_no_app_charge(db, client, firebase, stripe):
    game = community(db, price=1000)
    user, _card = paying_player(db, stripe)
    response = client.post(
        f"/games/{game.id}/join",
        headers=firebase.sign_in(user),
        json={"guest_count": 2},
    )
    assert response.status_code == 201, response.text
    booking = db.scalars(
        select(Booking).where(
            Booking.buyer_user_id == user.id, Booking.game_id == game.id
        )
    ).one()
    assert booking.payment_status == "not_required"
    assert (
        db.scalars(select(Payment).where(Payment.booking_id == booking.id)).all() == []
    )
    assert stripe.created == []


@pytest.mark.page("F17", 8)
@pytest.mark.parametrize("allow_guests, limit", [(True, 1), (False, 0)])
def test_party_over_the_guest_limit_is_rejected(
    db, client, firebase, stripe, allow_guests, limit
):
    game = upcoming_game(db, allow_guests=allow_guests, max_guests_per_booking=limit)
    user, card = paying_player(db, stripe)
    before = financial_and_attendance_state(db)
    response = submit_checkout(client, firebase, game, user, card, guests=2)
    assert response.status_code == 400
    assert response.json()["detail"] == (
        "This game does not allow guests."
        if not allow_guests
        else "This game allows up to 1 guests."
    )
    assert_unchanged(db, before, stripe)


@pytest.mark.page("F17", 8)
def test_party_that_cannot_fit_without_a_waitlist_is_not_split(
    db, client, firebase, stripe
):
    game = community(db, total_spots=2, waitlist_enabled=False)
    user, _card = paying_player(db, stripe)
    before = financial_and_attendance_state(db)
    response = client.post(
        f"/games/{game.id}/join",
        headers=firebase.sign_in(user),
        json={"guest_count": 1},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Not enough spots are available for this join."
    assert_unchanged(db, before, stripe)


@pytest.mark.page("F17", 9)
@pytest.mark.parametrize(
    "status", ["absent", "waitlisted", "cancelled", "expired", "failed"]
)
def test_add_guests_requires_a_confirmed_booking(db, client, firebase, stripe, status):
    game = upcoming_game(db)
    user, card = paying_player(db, stripe)
    if status != "absent":
        booking = make_booking(
            db,
            game=game,
            buyer=user,
            booking_status=status,
            payment_status="unpaid",
            reservation_status="released"
            if status in {"expired", "failed"}
            else "not_required",
            cancelled_at=database_now(db) if status == "cancelled" else None,
            booked_at=None,
        )
        make_participant(
            db,
            game=game,
            booking=booking,
            user=user,
            participant_status="waitlisted" if status == "waitlisted" else "cancelled",
        )
    before = financial_and_attendance_state(db)
    response = submit_checkout(
        client, firebase, game, user, card, guests=1, add_guests=True
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Only confirmed players can add guests."
    assert_unchanged(db, before, stripe)


@pytest.mark.page("F17", 7)
@pytest.mark.parametrize("path", ["official", "community", "guest"])
def test_signed_out_booking_changes_are_rejected(db, client, firebase, stripe, path):
    game = community(db) if path == "community" else upcoming_game(db)
    user, card = paying_player(db, stripe)
    if path == "guest":
        booking = make_booking(db, game=game, buyer=user)
        make_participant(db, game=game, booking=booking, user=user)
    before = financial_and_attendance_state(db)
    headers = {}
    if path == "community":
        response = client.post(
            f"/games/{game.id}/join", headers=headers, json={"guest_count": 0}
        )
    else:
        response = submit_checkout(
            client,
            firebase,
            game,
            user,
            card,
            guests=1 if path == "guest" else 0,
            add_guests=path == "guest",
            headers=headers,
        )
    assert response.status_code == 401, response.text
    assert_unchanged(db, before, stripe)


@pytest.mark.page("F17", 7)
@pytest.mark.parametrize("path", ["official", "community", "guest"])
def test_incomplete_profile_cannot_submit_booking_changes(
    db, client, firebase, stripe, path
):
    game = community(db) if path == "community" else upcoming_game(db)
    user, card = paying_player(db, stripe, date_of_birth=None)
    if path == "guest":
        booking = make_booking(db, game=game, buyer=user)
        make_participant(db, game=game, booking=booking, user=user)
    before = financial_and_attendance_state(db)
    headers = firebase.sign_in(user)
    if path == "community":
        response = client.post(
            f"/games/{game.id}/join", headers=headers, json={"guest_count": 0}
        )
    else:
        response = submit_checkout(
            client,
            firebase,
            game,
            user,
            card,
            guests=1 if path == "guest" else 0,
            add_guests=path == "guest",
            headers=headers,
        )
    assert response.status_code == 400, response.text
    assert_unchanged(db, before, stripe)


@pytest.mark.page("F17", 7)
@pytest.mark.parametrize("path", ["official", "community", "guest"])
def test_unverified_email_cannot_submit_booking_changes(
    db, client, firebase, stripe, path
):
    game = community(db) if path == "community" else upcoming_game(db)
    user, card = paying_player(db, stripe)
    if path == "guest":
        booking = make_booking(db, game=game, buyer=user)
        make_participant(db, game=game, booking=booking, user=user)
    before = financial_and_attendance_state(db)
    headers = firebase.sign_in(user, email_verified=False)
    if path == "community":
        response = client.post(
            f"/games/{game.id}/join", headers=headers, json={"guest_count": 0}
        )
    else:
        response = submit_checkout(
            client,
            firebase,
            game,
            user,
            card,
            guests=1 if path == "guest" else 0,
            add_guests=path == "guest",
            headers=headers,
        )
    assert response.status_code == 403, response.text
    assert_unchanged(db, before, stripe)


@pytest.mark.page("F17", 15)
def test_suspension_blocks_booking_without_changing_existing_attendance(
    db, client, firebase, stripe
):
    game = upcoming_game(db, total_spots=14)
    user, card = paying_player(db, stripe, account_status="suspended")
    existing_game = upcoming_game(db)
    existing_booking = make_booking(db, game=existing_game, buyer=user)
    make_participant(db, game=existing_game, booking=existing_booking, user=user)
    before = financial_and_attendance_state(db)
    response = submit_checkout(
        client, firebase, game, user, card, guests=0, add_guests=False
    )
    assert response.status_code == 403
    assert_unchanged(db, before, stripe)


@pytest.mark.page("F17", 15)
def test_suspension_blocks_waitlist_without_changing_existing_attendance(
    db, client, firebase, stripe
):
    game = upcoming_game(db, total_spots=1)
    user, card = paying_player(db, stripe, account_status="suspended")
    existing_game = upcoming_game(db)
    existing_booking = make_booking(db, game=existing_game, buyer=user)
    make_participant(db, game=existing_game, booking=existing_booking, user=user)
    make_participant(db, game=game, booking=make_booking(db, game=game))
    before = financial_and_attendance_state(db)
    response = client.post(
        f"/games/{game.id}/join",
        headers=firebase.sign_in(user),
        json={
            "guest_count": 0,
            "payment_method_id": str(card.id),
            "auto_charge_consent_accepted": True,
            "auto_charge_consent_version": "waitlist-auto-charge-v1",
        },
    )
    assert response.status_code == 403
    assert_unchanged(db, before, stripe)


@pytest.mark.page("F17", 15)
def test_suspension_blocks_guest_addition_without_changing_existing_attendance(
    db, client, firebase, stripe
):
    game = upcoming_game(db, total_spots=14)
    user, card = paying_player(db, stripe, account_status="suspended")
    existing_game = game
    existing_booking = make_booking(db, game=existing_game, buyer=user)
    make_participant(db, game=existing_game, booking=existing_booking, user=user)
    before = financial_and_attendance_state(db)
    response = submit_checkout(
        client, firebase, game, user, card, guests=1, add_guests=True
    )
    assert response.status_code == 403
    assert_unchanged(db, before, stripe)


@pytest.mark.page("F17", 9)
def test_a_confirmed_player_cannot_book_a_second_time(db, client, firebase, stripe):
    game = upcoming_game(db)
    user, card = paying_player(db, stripe)
    booking = make_booking(db, game=game, buyer=user)
    make_participant(db, game=game, booking=booking, user=user)
    before = financial_and_attendance_state(db)
    response = submit_checkout(client, firebase, game, user, card)
    assert response.status_code == 409
    assert response.json()["detail"] == "You already joined this game."
    assert_unchanged(db, before, stripe)


@pytest.mark.page("F17", 10)
@pytest.mark.parametrize("path", ["official", "community", "waitlist", "guest"])
@pytest.mark.parametrize("seconds_before", [1, 0, -1])
def test_new_checkout_actions_close_exactly_at_five_minutes(
    db, client, firebase, stripe, clock, path, seconds_before
):
    now = database_now(db)
    clock.move_to(now)
    game = (
        community(db, total_spots=1 if path == "waitlist" else 14)
        if path in {"community", "waitlist"}
        else upcoming_game(db)
    )
    game.starts_at = now - timedelta(minutes=5) + timedelta(seconds=seconds_before)
    game.ends_at = game.starts_at + timedelta(hours=1)
    db.flush()
    user, card = paying_player(db, stripe)
    if path == "guest":
        booking = make_booking(db, game=game, buyer=user)
        make_participant(db, game=game, booking=booking, user=user)
    before = financial_and_attendance_state(db)
    if path in {"community", "waitlist"}:
        response = client.post(
            f"/games/{game.id}/join",
            headers=firebase.sign_in(user),
            json={"guest_count": 0},
        )
    else:
        response = submit_checkout(
            client,
            firebase,
            game,
            user,
            card,
            guests=1 if path == "guest" else 0,
            add_guests=path == "guest",
        )
    assert response.status_code == (201 if seconds_before > 0 else 400), response.text
    if seconds_before <= 0:
        assert_unchanged(db, before, stripe)
    else:
        assert (
            db.scalar(
                select(Booking.id).where(
                    Booking.buyer_user_id == user.id, Booking.game_id == game.id
                )
            )
            is not None
        )


@pytest.mark.page("F17", 10)
@pytest.mark.parametrize(
    "condition",
    [
        ("game_status", "completed"),
        ("game_status", "cancelled"),
        ("game_status", "expired"),
        ("game_status", "removed"),
        ("publish_status", "draft"),
        ("publish_status", "archived"),
        ("public_visibility_status", "hidden"),
        ("join_enforcement_status", "paused"),
    ],
)
def test_changed_game_eligibility_rejects_stale_checkout(
    db, client, firebase, stripe, condition
):
    game = upcoming_game(db)
    user, card = paying_player(db, stripe)
    field, value = condition
    setattr(game, field, value)
    if field == "game_status" and value == "cancelled":
        game.cancelled_at = database_now(db)
    if field == "game_status" and value == "completed":
        game.completed_at = database_now(db)
    db.flush()
    before = financial_and_attendance_state(db)
    response = submit_checkout(client, firebase, game, user, card)
    assert response.status_code == (404 if field == "public_visibility_status" else 400)
    assert_unchanged(db, before, stripe)


@pytest.mark.page("F17", 10)
def test_current_capacity_blocks_a_stale_party(db, client, firebase, stripe):
    game = upcoming_game(db, total_spots=2)
    user, card = paying_player(db, stripe)
    quote_response = client.get(
        f"/checkout/games/{game.id}/quote?guest_count=1", headers=firebase.sign_in(user)
    )
    assert quote_response.status_code == 200
    make_participant(db, game=game, booking=make_booking(db, game=game))
    before = financial_and_attendance_state(db)
    response = submit_checkout(client, firebase, game, user, card, guests=1)
    assert response.status_code == 400
    assert response.json()["detail"] == "Not enough spots are available for checkout."
    assert_unchanged(db, before, stripe)


@pytest.mark.page("F17", 6)
@pytest.mark.parametrize("price", [0, 1000])
def test_community_guests_do_not_create_an_app_payment(
    db, client, firebase, stripe, price
):
    game = community(db, price=price)
    user, _card = paying_player(db, stripe)
    booking = make_booking(db, game=game, buyer=user, payment_status="not_required")
    make_participant(db, game=game, booking=booking, user=user)
    response = client.post(
        f"/games/{game.id}/booking-guests/add",
        headers=firebase.sign_in(user),
        json={"guest_count": 2},
    )
    assert response.status_code == 201, response.text
    db.refresh(booking)
    assert booking.participant_count == 3
    assert (
        db.scalars(
            select(GameParticipant.participant_status).where(
                GameParticipant.booking_id == booking.id
            )
        ).all()
        == ["confirmed"] * 3
    )
    assert (
        db.scalars(select(Payment).where(Payment.booking_id == booking.id)).all() == []
    )
    assert stripe.created == []
