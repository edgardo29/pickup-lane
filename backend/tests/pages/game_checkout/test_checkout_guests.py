"""F17 add-guest checkout: paid guests join only after their own payment."""

from datetime import timedelta

import pytest
from sqlalchemy import select

from backend.models import (
    Booking,
    GameCreditUsage,
    GameParticipant,
    Payment,
    PaymentCompensation,
)
from backend.services.game_service import count_roster_players
from backend.tests.conftest import database_now
from backend.tests.factories import (
    make_booking,
    make_game_credit,
    make_participant,
    make_saved_card,
)
from backend.tests.pages.game_checkout.conftest import (
    financial_and_attendance_state,
    paying_player,
    register_card,
    upcoming_game,
)


def booked_player(db, stripe, game):
    """A player with a confirmed, paid booking for just themselves."""
    user, card = paying_player(db, stripe)
    booking = make_booking(db, game=game, buyer=user)
    make_participant(db, game=game, booking=booking, user=user)
    return user, card, booking


def guests(db, booking):
    return db.scalars(
        select(GameParticipant)
        .where(
            GameParticipant.booking_id == booking.id,
            GameParticipant.participant_type == "guest",
        )
        .order_by(GameParticipant.guest_name)
    ).all()


def guest_payment(db, booking):
    return db.scalars(select(Payment).where(Payment.booking_id == booking.id)).one()


def add_guests(client, firebase, game, user, card, guest_count=2):
    return client.post(
        f"/checkout/games/{game.id}/guest-payment-intent",
        headers=firebase.sign_in(user),
        json={"guest_count": guest_count, "payment_method_id": str(card.id)},
    )


def guest_attempt(
    db,
    client,
    firebase,
    stripe,
    *,
    credit_amount=500,
    status="succeeded",
    with_card=True,
    guest_count=2,
    booking_status="confirmed",
):
    game = upcoming_game(db)
    user, card, booking = booked_player(db, stripe, game)
    if booking_status != "confirmed":
        booking.booking_status = booking_status
        db.commit()
    credit = make_game_credit(db, user=user, amount_cents=credit_amount)
    stripe.confirm_status = status
    body = {"guest_count": guest_count}
    if with_card:
        body["payment_method_id"] = str(card.id)
    else:
        db.delete(card)
        db.commit()
    response = client.post(
        f"/checkout/games/{game.id}/guest-payment-intent",
        headers=firebase.sign_in(user),
        json=body,
    )
    assert response.status_code == 201, response.text
    return game, user, card, credit, booking, response


@pytest.mark.page("F17", 6)
def test_guest_payment_prices_only_new_guests_after_credit(
    db, client, firebase, stripe
):
    _game, _user, _card, _credit, booking, response = guest_attempt(
        db, client, firebase, stripe
    )
    assert response.json()["credit_applied_cents"] == 500
    assert response.json()["final_amount_due_cents"] == 1500
    assert guest_payment(db, booking).amount_cents == 1500
    db.refresh(booking)
    assert (booking.subtotal_cents, booking.discount_cents, booking.total_cents) == (
        3000,
        500,
        2500,
    )


@pytest.mark.page("F17", 6)
def test_pending_guest_payment_does_not_confirm_added_guests(
    db, client, firebase, stripe
):
    _game, user, _card, _credit, booking, response = guest_attempt(
        db, client, firebase, stripe, status="processing"
    )
    assert [guest.participant_status for guest in guests(db, booking)] == [
        "pending_payment",
        "pending_payment",
    ]
    assert response.json()["payment_status"] == "processing"
    db.refresh(booking)
    assert booking.participant_count == 1
    status = client.get(
        f"/checkout/bookings/{booking.id}/status", headers=firebase.sign_in(user)
    )
    assert status.status_code == 200
    assert status.json()["guest_reservation_status"] == "held"
    assert status.json()["booking_status"] == "confirmed"
    assert status.json()["roster_counts"]["occupied_spots"] == 3


@pytest.mark.page("F17", 6)
@pytest.mark.parametrize("booking_status", ["confirmed", "partially_cancelled"])
def test_added_guests_confirm_only_after_their_payment_succeeds(
    db, client, firebase, stripe, booking_status
):
    _game, user, _card, _credit, booking, _response = guest_attempt(
        db, client, firebase, stripe, status="processing", booking_status=booking_status
    )
    assert [guest.participant_status for guest in guests(db, booking)] == [
        "pending_payment",
        "pending_payment",
    ]
    stripe.report(db, guest_payment(db, booking), "succeeded")
    db.refresh(booking)
    assert [guest.participant_status for guest in guests(db, booking)] == [
        "confirmed",
        "confirmed",
    ]
    assert booking.participant_count == 3
    status = client.get(
        f"/checkout/bookings/{booking.id}/status", headers=firebase.sign_in(user)
    )
    assert status.status_code == 200
    assert status.json()["guest_reservation_status"] == "confirmed"


@pytest.mark.page("F17", 6)
def test_full_credit_guest_addition_needs_no_saved_card_or_charge(
    db, client, firebase, stripe
):
    _game, _user, _card, _credit, booking, response = guest_attempt(
        db, client, firebase, stripe, credit_amount=1000, guest_count=1, with_card=False
    )
    assert response.json()["payment_required"] is False
    assert [guest.participant_status for guest in guests(db, booking)] == ["confirmed"]
    db.refresh(booking)
    assert booking.participant_count == 2
    assert (
        db.scalars(select(Payment).where(Payment.booking_id == booking.id)).all() == []
    )
    assert stripe.created == []


@pytest.mark.page("F17", 6)
def test_small_guest_balance_is_covered_without_a_card_charge(
    db, client, firebase, stripe
):
    _game, _user, _card, _credit, booking, response = guest_attempt(
        db, client, firebase, stripe, credit_amount=970, guest_count=1, with_card=False
    )
    assert response.json()["payment_required"] is False
    assert response.json()["minimum_charge_adjustment_cents"] == 30
    assert [guest.participant_status for guest in guests(db, booking)] == ["confirmed"]
    usages = db.scalars(
        select(GameCreditUsage).where(GameCreditUsage.booking_id == booking.id)
    ).all()
    assert [(u.amount_cents, u.usage_status) for u in usages] == [(970, "redeemed")]
    assert stripe.created == []


@pytest.mark.page("F17", 18)
def test_failed_guest_charge_adds_no_guests_or_held_spots(db, client, firebase, stripe):
    game, _user, _card, _credit, booking, response = guest_attempt(
        db, client, firebase, stripe, status="requires_payment_method"
    )
    assert response.json()["payment_status"] == "requires_payment_method"
    assert [guest.participant_status for guest in guests(db, booking)] == [
        "cancelled",
        "cancelled",
    ]
    db.refresh(booking)
    assert (booking.booking_status, booking.participant_count, booking.total_cents) == (
        "confirmed",
        1,
        1000,
    )
    assert count_roster_players(db, game.id, now=database_now(db)) == 1
    stripe.report(db, guest_payment(db, booking), "canceled")
    assert [guest.participant_status for guest in guests(db, booking)] == [
        "cancelled",
        "cancelled",
    ]


@pytest.mark.page("F17", 18)
def test_failed_guest_charge_releases_reserved_credit(db, client, firebase, stripe):
    _game, _user, _card, credit, booking, _response = guest_attempt(
        db, client, firebase, stripe, status="requires_payment_method"
    )
    db.refresh(credit)
    assert credit.available_cents == 500
    assert [
        (u.amount_cents, u.usage_status)
        for u in db.scalars(
            select(GameCreditUsage).where(GameCreditUsage.booking_id == booking.id)
        )
    ] == [(500, "released")]


@pytest.mark.page("F17", 13)
@pytest.mark.parametrize("payment_status", ["requires_action", "processing"])
def test_guest_hold_expiry_releases_spots_and_credit(
    db, client, firebase, stripe, payment_status
):
    game, user, _card, credit, booking, _response = guest_attempt(
        db, client, firebase, stripe, status=payment_status
    )
    for guest in guests(db, booking):
        guest.hold_expires_at = database_now(db)
    db.commit()
    response = client.get(
        f"/checkout/bookings/{booking.id}/status", headers=firebase.sign_in(user)
    )
    assert response.status_code == 200
    db.refresh(booking)
    db.refresh(credit)
    assert response.json()["guest_reservation_status"] == "released"
    assert response.json()["roster_counts"]["occupied_spots"] == 1
    assert response.json()["payment_status"] == payment_status
    assert (booking.booking_status, booking.participant_count) == ("confirmed", 1)
    assert [guest.participant_status for guest in guests(db, booking)] == [
        "cancelled",
        "cancelled",
    ]
    assert credit.available_cents == 500
    assert count_roster_players(db, game.id, now=database_now(db)) == 1


@pytest.mark.page("F17", 18)
def test_a_declined_guest_payment_can_be_retried_with_another_card(
    db, client, firebase, stripe
):
    game = upcoming_game(db, price_per_player_cents=1000)
    user, card, booking = booked_player(db, stripe, game)
    credit = make_game_credit(db, user=user, amount_cents=300)
    other_card = make_saved_card(db, user=user, is_default=False)
    register_card(stripe, other_card)
    stripe.confirm_status = "requires_payment_method"
    declined = add_guests(client, firebase, game, user, card, guest_count=1)

    stripe.confirm_status = "succeeded"
    retried = add_guests(client, firebase, game, user, other_card, guest_count=1)

    assert declined.status_code == 201, declined.text
    assert retried.status_code == 201, retried.text
    assert [guest.participant_status for guest in guests(db, booking)] == [
        "cancelled",
        "confirmed",
    ]
    db.refresh(booking)
    db.refresh(credit)
    assert booking.participant_count == 2
    assert credit.available_cents == 0
    usages = db.scalars(
        select(GameCreditUsage)
        .where(GameCreditUsage.booking_id == booking.id)
        .order_by(GameCreditUsage.created_at, GameCreditUsage.usage_status)
    ).all()
    assert sorted(usage.usage_status for usage in usages) == ["redeemed", "released"]


@pytest.mark.page("F17", 14)
def test_a_second_guest_payment_waits_for_the_first(db, client, firebase, stripe):
    game = upcoming_game(db)
    user, card, booking = booked_player(db, stripe, game)
    stripe.confirm_status = "requires_action"

    first = add_guests(client, firebase, game, user, card, guest_count=1)
    before = financial_and_attendance_state(db)
    second = add_guests(client, firebase, game, user, card, guest_count=1)

    assert first.status_code == 201, first.text
    assert second.status_code == 409
    assert second.json()["detail"] == (
        "A guest payment is already in progress for your booking."
    )
    assert len(guests(db, booking)) == 1
    assert db.scalars(select(Booking).where(Booking.game_id == game.id)).all() == [
        booking
    ]
    assert financial_and_attendance_state(db) == before
    assert len(stripe.created) == 1


@pytest.mark.page("F17", 13)
def test_guest_payment_after_the_hold_ends_is_refunded(db, client, firebase, stripe):
    game = upcoming_game(db, price_per_player_cents=1000)
    user, card, booking = booked_player(db, stripe, game)
    stripe.confirm_status = "requires_action"
    add_guests(client, firebase, game, user, card, guest_count=1)
    for guest in guests(db, booking):
        guest.hold_expires_at = database_now(db) - timedelta(seconds=1)
    db.commit()

    status = client.get(
        f"/checkout/bookings/{booking.id}/status", headers=firebase.sign_in(user)
    )
    stripe.report(db, guest_payment(db, booking), "succeeded")

    assert status.status_code == 200, status.text
    assert [guest.participant_status for guest in guests(db, booking)] == ["cancelled"]
    db.refresh(booking)
    assert (booking.booking_status, booking.participant_count) == ("confirmed", 1)
    compensation = db.scalar(
        select(PaymentCompensation).where(PaymentCompensation.booking_id == booking.id)
    )
    assert compensation is not None
    assert (compensation.reason, compensation.amount_cents) == (
        "reservation_expired",
        1000,
    )


@pytest.mark.page("F17", 6)
@pytest.mark.parametrize("credit_amount", [1000, 970])
@pytest.mark.parametrize("card_state", ["expired", "detached", "stripe_unavailable"])
def test_covered_guests_ignore_an_unneeded_card_after_credit_changes(
    db, client, firebase, stripe, credit_amount, card_state
):
    game = upcoming_game(db)
    user, card, booking = booked_player(db, stripe, game)
    headers = firebase.sign_in(user)
    quote = client.get(
        f"/checkout/games/{game.id}/quote?guest_count=1&add_guests=true",
        headers=headers,
    )
    assert quote.status_code == 200
    assert quote.json()["payment_required"] is True
    credit = make_game_credit(db, user=user, amount_cents=credit_amount)
    if card_state == "expired":
        card.exp_year = 2020
    elif card_state == "detached":
        card.method_status = "detached"
        card.is_default = False
    else:
        stripe.cards.pop(card.stripe_payment_method_id)
    db.commit()

    response = add_guests(client, firebase, game, user, card, guest_count=1)

    assert response.status_code == 201, response.text
    assert response.json()["payment_required"] is False
    assert response.json()["minimum_charge_adjustment_cents"] == 1000 - credit_amount
    assert [guest.participant_status for guest in guests(db, booking)] == ["confirmed"]
    db.refresh(booking)
    db.refresh(credit)
    assert booking.participant_count == 2
    assert credit.available_cents == 0
    usages = db.scalars(
        select(GameCreditUsage).where(GameCreditUsage.booking_id == booking.id)
    ).all()
    assert [(usage.amount_cents, usage.usage_status) for usage in usages] == [
        (credit_amount, "redeemed")
    ]
    assert (
        db.scalars(select(Payment).where(Payment.booking_id == booking.id)).all() == []
    )
    assert stripe.created == []


@pytest.mark.page("F17", 12)
@pytest.mark.parametrize("card_state", ["expired", "detached", "stripe_detached"])
def test_required_guest_charge_rejects_an_unusable_card(
    db, client, firebase, stripe, card_state
):
    game = upcoming_game(db)
    user, card, _booking = booked_player(db, stripe, game)
    if card_state == "expired":
        card.exp_year = 2020
    elif card_state == "detached":
        card.method_status = "detached"
        card.is_default = False
    else:
        from dataclasses import replace

        stripe.cards[card.stripe_payment_method_id] = replace(
            stripe.cards[card.stripe_payment_method_id], customer_id="cus_other"
        )
    db.commit()
    before = financial_and_attendance_state(db)

    response = add_guests(client, firebase, game, user, card, guest_count=1)

    assert response.status_code == (409 if card_state == "stripe_detached" else 400)
    assert financial_and_attendance_state(db) == before
    assert stripe.created == []


@pytest.mark.page("F17", 6)
@pytest.mark.parametrize("new_credit", [0, 200])
def test_reopened_guest_quote_keeps_only_its_reserved_credit(
    db, client, firebase, stripe, new_credit
):
    game, user, _card, _credit, booking, _response = guest_attempt(
        db,
        client,
        firebase,
        stripe,
        credit_amount=300,
        status="processing",
        guest_count=1,
    )
    if new_credit:
        make_game_credit(db, user=user, amount_cents=new_credit)
    before = financial_and_attendance_state(db)
    response = client.get(
        f"/checkout/games/{game.id}/quote?guest_count=1&add_guests=true",
        headers=firebase.sign_in(user),
    )
    assert response.status_code == 200, response.text
    assert response.json()["credit_applied_cents"] == 300
    assert response.json()["available_credit_cents"] == 300 + new_credit
    assert response.json()["final_amount_due_cents"] == 700
    assert response.json()["checkout_total_cents"] == 1000
    assert financial_and_attendance_state(db) == before
    assert booking.participant_count == 1


@pytest.mark.page("F17", 12)
def test_reopened_guest_payment_returns_its_authentication_secret(
    db, client, firebase, stripe
):
    _game, user, _card, _credit, booking, _response = guest_attempt(
        db, client, firebase, stripe, status="requires_action"
    )
    payment = guest_payment(db, booking)
    before = financial_and_attendance_state(db)
    response = client.get(
        f"/checkout/bookings/{booking.id}/status", headers=firebase.sign_in(user)
    )
    assert response.status_code == 200, response.text
    assert (
        response.json().get("client_secret")
        == stripe.intents[payment.provider_payment_intent_id].client_secret
    )
    assert response.json()["guest_reservation_status"] == "held"
    assert financial_and_attendance_state(db) == before
    assert len(stripe.created) == 1


@pytest.mark.page("F17", 13)
def test_expired_guest_payment_returns_no_authentication_secret(
    db, client, firebase, stripe
):
    _game, user, _card, credit, booking, _response = guest_attempt(
        db, client, firebase, stripe, status="requires_action"
    )
    for guest in guests(db, booking):
        guest.hold_expires_at = database_now(db)
    db.commit()
    response = client.get(
        f"/checkout/bookings/{booking.id}/status", headers=firebase.sign_in(user)
    )
    assert response.status_code == 200, response.text
    assert response.json().get("client_secret") is None
    assert response.json()["guest_reservation_status"] == "released"
    assert [guest.participant_status for guest in guests(db, booking)] == [
        "cancelled",
        "cancelled",
    ]
    db.refresh(credit)
    assert credit.available_cents == 500
    assert booking.participant_count == 1
    assert len(stripe.created) == 1


@pytest.mark.page("F17", 12)
@pytest.mark.parametrize("role", ["player", "admin"])
def test_guest_authentication_secret_is_only_for_the_booking_owner(
    db, client, firebase, stripe, role
):
    _game, _user, _card, _credit, booking, _response = guest_attempt(
        db, client, firebase, stripe, status="requires_action"
    )
    other, _other_card = paying_player(db, stripe, role=role)
    before = financial_and_attendance_state(db)
    response = client.get(
        f"/checkout/bookings/{booking.id}/status", headers=firebase.sign_in(other)
    )
    assert response.status_code == (200 if role == "admin" else 403), response.text
    assert response.json().get("client_secret") is None
    assert financial_and_attendance_state(db) == before
    assert len(stripe.created) == 1


@pytest.mark.page("F17", 12)
def test_guest_authentication_retrieval_failure_keeps_attendance_unconfirmed(
    db, client, firebase, stripe, monkeypatch
):
    _game, user, _card, _credit, booking, _response = guest_attempt(
        db, client, firebase, stripe, status="requires_action"
    )
    before = financial_and_attendance_state(db)

    def unavailable(_intent_id):
        raise RuntimeError("Synthetic Stripe read failure")

    monkeypatch.setattr(
        "backend.services.checkout_service.retrieve_payment_intent", unavailable
    )
    response = client.get(
        f"/checkout/bookings/{booking.id}/status", headers=firebase.sign_in(user)
    )
    assert response.status_code == 502, response.text
    assert (
        response.json()["detail"]
        == "Payment authentication could not be loaded. Try again."
    )
    assert financial_and_attendance_state(db) == before
    assert len(stripe.created) == 1
