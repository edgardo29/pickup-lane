"""F17 who can check out, for which party, and when."""

from datetime import timedelta

import pytest
from sqlalchemy import func, select

from backend.models import Booking, GameParticipant, Payment, WaitlistEntry
from backend.tests.conftest import database_now
from backend.tests.factories import make_booking, make_game, make_participant
from backend.tests.pages.game_checkout.conftest import paying_player, upcoming_game


def count_rows(db, model, game):
    return db.scalar(select(func.count(model.id)).where(model.game_id == game.id))


def nothing_created(db, game):
    return (
        count_rows(db, Booking, game) == 0
        and count_rows(db, GameParticipant, game) == 0
        and count_rows(db, WaitlistEntry, game) == 0
    )


@pytest.mark.page("F17", 2)
def test_community_game_confirms_the_whole_party_without_an_app_charge(
    db, client, firebase
):
    game = make_game(
        db,
        game_type="community",
        starts_at=database_now(db) + timedelta(days=2),
        allow_guests=True,
        max_guests_per_booking=2,
        price_per_player_cents=0,
    )
    user, _card = paying_player(db)

    response = client.post(
        f"/games/{game.id}/join",
        headers=firebase.sign_in(user),
        json={"guest_count": 2},
    )

    assert response.status_code == 201, response.text
    assert response.json()["status"] == "joined"
    statuses = db.scalars(
        select(GameParticipant.participant_status).where(
            GameParticipant.game_id == game.id
        )
    ).all()
    assert statuses == ["confirmed", "confirmed", "confirmed"]
    booking = db.scalars(select(Booking).where(Booking.game_id == game.id)).one()
    assert booking.payment_status == "not_required"
    assert (
        db.scalars(select(Payment).where(Payment.booking_id == booking.id)).all() == []
    )


@pytest.mark.page("F17", 7)
def test_incomplete_profile_cannot_check_out(db, client, firebase, stripe):
    game = upcoming_game(db)
    user, card = paying_player(db, stripe, date_of_birth=None)

    response = client.post(
        f"/checkout/games/{game.id}/payment-intent",
        headers=firebase.sign_in(user),
        json={"guest_count": 0, "payment_method_id": str(card.id)},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Finish your profile before joining a game."
    assert nothing_created(db, game)


@pytest.mark.page("F17", 7)
def test_unverified_email_cannot_submit_a_booking(db, client, firebase, stripe):
    game = upcoming_game(db)
    user, card = paying_player(db, stripe)

    response = client.post(
        f"/checkout/games/{game.id}/payment-intent",
        headers=firebase.sign_in(user, email_verified=False),
        json={"guest_count": 0, "payment_method_id": str(card.id)},
    )

    assert response.status_code == 403
    assert nothing_created(db, game)
    assert stripe.created == []


@pytest.mark.page("F17", 8)
def test_party_over_the_guest_limit_is_rejected(db, client, firebase, stripe):
    game = upcoming_game(db, max_guests_per_booking=1)
    user, card = paying_player(db, stripe)

    response = client.post(
        f"/checkout/games/{game.id}/payment-intent",
        headers=firebase.sign_in(user),
        json={"guest_count": 2, "payment_method_id": str(card.id)},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "This game allows up to 1 guests."
    assert nothing_created(db, game)


@pytest.mark.page("F17", 8)
def test_party_that_cannot_fit_is_not_split_or_confirmed(db, client, firebase, stripe):
    game = upcoming_game(db, total_spots=2, waitlist_enabled=False)
    make_participant(db, game=game, booking=make_booking(db, game=game))
    user, card = paying_player(db, stripe)

    response = client.post(
        f"/checkout/games/{game.id}/payment-intent",
        headers=firebase.sign_in(user),
        json={"guest_count": 1, "payment_method_id": str(card.id)},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Not enough spots are available for checkout."
    assert count_rows(db, GameParticipant, game) == 1


@pytest.mark.page("F17", 9)
def test_a_confirmed_player_cannot_book_a_second_time(db, client, firebase, stripe):
    game = upcoming_game(db)
    user, card = paying_player(db, stripe)
    booking = make_booking(db, game=game, buyer=user)
    make_participant(db, game=game, booking=booking, user=user)

    response = client.post(
        f"/checkout/games/{game.id}/payment-intent",
        headers=firebase.sign_in(user),
        json={"guest_count": 0, "payment_method_id": str(card.id)},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "You already joined this game."
    assert count_rows(db, Booking, game) == 1
    assert stripe.created == []


@pytest.mark.page("F17", 9)
def test_add_guests_needs_a_confirmed_booking(db, client, firebase, stripe):
    game = upcoming_game(db)
    user, card = paying_player(db, stripe)
    booking = make_booking(
        db,
        game=game,
        buyer=user,
        booking_status="waitlisted",
        payment_status="unpaid",
        reservation_status="not_required",
        booked_at=None,
    )
    make_participant(
        db, game=game, booking=booking, user=user, participant_status="waitlisted"
    )

    response = client.post(
        f"/checkout/games/{game.id}/guest-payment-intent",
        headers=firebase.sign_in(user),
        json={"guest_count": 1, "payment_method_id": str(card.id)},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Only confirmed players can add guests."
    assert count_rows(db, GameParticipant, game) == 1
    assert stripe.created == []


@pytest.mark.page("F17", 10)
def test_checkout_closes_five_minutes_after_start(db, client, firebase, stripe):
    game = make_game(db, starts_at=database_now(db) - timedelta(minutes=5, seconds=1))
    user, card = paying_player(db, stripe)

    response = client.post(
        f"/checkout/games/{game.id}/payment-intent",
        headers=firebase.sign_in(user),
        json={"guest_count": 0, "payment_method_id": str(card.id)},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Checkout is closed for this game."
    assert nothing_created(db, game)


@pytest.mark.page("F17", 10)
def test_a_game_that_stopped_being_joinable_cannot_confirm(
    db, client, firebase, stripe
):
    game = upcoming_game(db, game_status="cancelled", cancelled_at=database_now(db))
    user, card = paying_player(db, stripe)

    response = client.post(
        f"/checkout/games/{game.id}/payment-intent",
        headers=firebase.sign_in(user),
        json={"guest_count": 0, "payment_method_id": str(card.id)},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "This game is not open for checkout."
    assert nothing_created(db, game)


@pytest.mark.page("F17", 15)
def test_suspended_player_cannot_book_waitlist_or_add_guests(
    db, client, firebase, stripe
):
    game = upcoming_game(db, total_spots=2)
    user, card = paying_player(db, stripe, account_status="suspended")
    booking = make_booking(db, game=game, buyer=user)
    existing = make_participant(db, game=game, booking=booking, user=user)
    headers = firebase.sign_in(user)
    other_game = upcoming_game(db, total_spots=1)
    make_participant(db, game=other_game, booking=make_booking(db, game=other_game))

    responses = [
        client.post(
            f"/checkout/games/{upcoming_game(db).id}/payment-intent",
            headers=headers,
            json={"guest_count": 0, "payment_method_id": str(card.id)},
        ),
        client.post(
            f"/games/{other_game.id}/join",
            headers=headers,
            json={
                "guest_count": 0,
                "payment_method_id": str(card.id),
                "auto_charge_consent_accepted": True,
                "auto_charge_consent_version": "waitlist-auto-charge-v1",
            },
        ),
        client.post(
            f"/checkout/games/{game.id}/guest-payment-intent",
            headers=headers,
            json={"guest_count": 1, "payment_method_id": str(card.id)},
        ),
    ]

    assert [response.status_code for response in responses] == [403, 403, 403]
    assert count_rows(db, WaitlistEntry, other_game) == 0
    assert count_rows(db, GameParticipant, game) == 1
    db.refresh(existing)
    assert existing.participant_status == "confirmed"
    assert stripe.created == []
