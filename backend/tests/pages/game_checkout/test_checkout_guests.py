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
from backend.tests.conftest import database_now
from backend.tests.factories import (
    make_booking,
    make_game_credit,
    make_participant,
    make_saved_card,
)
from backend.tests.pages.game_checkout.conftest import paying_player, upcoming_game


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


@pytest.mark.page("F17", 6)
def test_paid_guests_join_after_their_payment_succeeds(db, client, firebase, stripe):
    game = upcoming_game(db, price_per_player_cents=1000)
    user, card, booking = booked_player(db, stripe, game)
    make_game_credit(db, user=user, amount_cents=500)

    response = add_guests(client, firebase, game, user, card)

    assert response.status_code == 201, response.text
    assert response.json()["credit_applied_cents"] == 500
    assert response.json()["final_amount_due_cents"] == 1500
    payment = guest_payment(db, booking)
    assert (payment.amount_cents, payment.payment_status) == (1500, "succeeded")
    assert [guest.participant_status for guest in guests(db, booking)] == [
        "confirmed",
        "confirmed",
    ]
    db.refresh(booking)
    assert booking.participant_count == 3
    assert (booking.subtotal_cents, booking.discount_cents, booking.total_cents) == (
        3000,
        500,
        2500,
    )
    usage = db.scalars(
        select(GameCreditUsage).where(GameCreditUsage.booking_id == booking.id)
    ).one()
    assert (usage.amount_cents, usage.usage_status, usage.payment_id) == (
        500,
        "redeemed",
        payment.id,
    )


@pytest.mark.page("F17", 6)
def test_credit_covered_guests_join_at_once_without_a_card(
    db, client, firebase, stripe
):
    game = upcoming_game(db, price_per_player_cents=1000)
    user, _card, booking = booked_player(db, stripe, game)
    make_game_credit(db, user=user, amount_cents=1000)

    response = client.post(
        f"/checkout/games/{game.id}/guest-payment-intent",
        headers=firebase.sign_in(user),
        json={"guest_count": 1},
    )

    assert response.status_code == 201, response.text
    assert response.json()["payment_required"] is False
    assert [guest.participant_status for guest in guests(db, booking)] == ["confirmed"]
    db.refresh(booking)
    assert (booking.participant_count, booking.total_cents) == (2, 1000)
    assert (
        db.scalars(select(Payment).where(Payment.booking_id == booking.id)).all() == []
    )
    assert stripe.created == []


@pytest.mark.page("F17", 18)
def test_failed_guest_charge_adds_no_guests_and_releases_credit(
    db, client, firebase, stripe
):
    game = upcoming_game(db, price_per_player_cents=1000)
    user, card, booking = booked_player(db, stripe, game)
    credit = make_game_credit(db, user=user, amount_cents=500)
    stripe.confirm_status = "requires_payment_method"

    response = add_guests(client, firebase, game, user, card)
    stripe.report(db, guest_payment(db, booking), "canceled")

    assert response.status_code == 201, response.text
    assert response.json()["payment_status"] == "requires_payment_method"
    assert [guest.participant_status for guest in guests(db, booking)] == [
        "cancelled",
        "cancelled",
    ]
    db.refresh(booking)
    db.refresh(credit)
    assert (booking.booking_status, booking.participant_count) == ("confirmed", 1)
    assert booking.total_cents == 1000
    assert credit.available_cents == 500


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
    compensation = db.scalars(
        select(PaymentCompensation).where(PaymentCompensation.booking_id == booking.id)
    ).one()
    assert (compensation.reason, compensation.amount_cents) == (
        "reservation_expired",
        1000,
    )


@pytest.mark.page("F17", 14)
def test_a_second_guest_payment_waits_for_the_first(db, client, firebase, stripe):
    game = upcoming_game(db)
    user, card, booking = booked_player(db, stripe, game)
    stripe.confirm_status = "requires_action"

    first = add_guests(client, firebase, game, user, card, guest_count=1)
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


@pytest.mark.page("F17", 18)
def test_a_declined_guest_payment_can_be_retried_with_another_card(
    db, client, firebase, stripe
):
    game = upcoming_game(db, price_per_player_cents=1000)
    user, card, booking = booked_player(db, stripe, game)
    credit = make_game_credit(db, user=user, amount_cents=300)
    other_card = make_saved_card(db, user=user, is_default=False)
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
