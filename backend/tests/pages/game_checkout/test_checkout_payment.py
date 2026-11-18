"""F17 official checkout: credit first, small balances covered, Stripe for the rest."""

from datetime import timedelta

import pytest
from sqlalchemy import select

from backend.models import (
    Booking,
    GameCredit,
    GameCreditUsage,
    GameParticipant,
    Payment,
    PaymentCompensation,
)
from backend.tests.conftest import database_now
from backend.tests.factories import make_game_credit, make_saved_card
from backend.tests.pages.game_checkout.conftest import paying_player, upcoming_game


def booking_for(db, game, user):
    return db.scalars(
        select(Booking).where(
            Booking.game_id == game.id, Booking.buyer_user_id == user.id
        )
    ).one_or_none()


def roster_statuses(db, booking):
    return sorted(
        db.scalars(
            select(GameParticipant.participant_status).where(
                GameParticipant.booking_id == booking.id
            )
        ).all()
    )


@pytest.mark.page("F17", 3)
def test_balance_after_credit_is_charged_and_confirms_only_after_payment(
    db, client, firebase, stripe
):
    game = upcoming_game(db, price_per_player_cents=1000)
    user, card = paying_player(db, stripe)
    make_game_credit(db, user=user, amount_cents=300)
    headers = firebase.sign_in(user)

    quote = client.get(f"/checkout/games/{game.id}/quote", headers=headers)
    response = client.post(
        f"/checkout/games/{game.id}/payment-intent",
        headers=headers,
        json={"guest_count": 0, "payment_method_id": str(card.id)},
    )

    assert quote.status_code == 200, quote.text
    assert quote.json() == {
        "subtotal_cents": 1000,
        "platform_fee_cents": 0,
        "checkout_total_cents": 1000,
        "available_credit_cents": 300,
        "credit_applied_cents": 300,
        "minimum_charge_adjustment_cents": 0,
        "final_amount_due_cents": 700,
        "payment_required": True,
    }
    assert response.status_code == 201, response.text
    assert response.json()["credit_applied_cents"] == 300
    assert response.json()["final_amount_due_cents"] == 700
    booking = booking_for(db, game, user)
    payment = db.scalars(select(Payment).where(Payment.booking_id == booking.id)).one()
    assert payment.amount_cents == 700
    assert payment.payment_status == "succeeded"
    assert booking.booking_status == "confirmed"
    assert roster_statuses(db, booking) == ["confirmed"]
    usage = db.scalars(
        select(GameCreditUsage).where(GameCreditUsage.booking_id == booking.id)
    ).one()
    assert (usage.amount_cents, usage.usage_status) == (300, "redeemed")


@pytest.mark.page("F17", 26)
def test_low_price_without_credit_is_covered_without_a_card(
    db, client, firebase, stripe
):
    game = upcoming_game(db, price_per_player_cents=30)
    user, _card = paying_player(db, stripe)

    response = client.post(
        f"/checkout/games/{game.id}/payment-intent",
        headers=firebase.sign_in(user),
        json={"guest_count": 0},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["payment_required"] is False
    assert body["credit_applied_cents"] == 0
    assert body["minimum_charge_adjustment_cents"] == 30
    assert body["final_amount_due_cents"] == 0
    booking = booking_for(db, game, user)
    assert booking.booking_status == "confirmed"
    assert (booking.discount_cents, booking.total_cents) == (30, 0)
    assert (
        db.scalars(select(Payment).where(Payment.booking_id == booking.id)).all() == []
    )
    assert (
        db.scalars(
            select(GameCreditUsage).where(GameCreditUsage.booking_id == booking.id)
        ).all()
        == []
    )
    assert stripe.created == []
    assert db.scalars(select(GameCredit)).all() == []


def only_payment(db, booking):
    return db.scalars(select(Payment).where(Payment.booking_id == booking.id)).one()


def credit_usages(db, booking):
    return db.scalars(
        select(GameCreditUsage).where(GameCreditUsage.booking_id == booking.id)
    ).all()


@pytest.mark.page("F17", 4)
def test_the_selected_saved_card_pays_and_other_cards_are_rejected(
    db, client, firebase, stripe
):
    game = upcoming_game(db)
    user, _first_card = paying_player(db, stripe)
    second_card = make_saved_card(db, user=user, is_default=False)
    _other_user, other_card = paying_player(db, stripe)
    detached_card = make_saved_card(
        db, user=user, is_default=False, method_status="detached"
    )
    headers = firebase.sign_in(user)

    rejected = [
        client.post(
            f"/checkout/games/{game.id}/payment-intent",
            headers=headers,
            json={"guest_count": 0, "payment_method_id": str(card.id)},
        )
        for card in (other_card, detached_card)
    ]
    accepted = client.post(
        f"/checkout/games/{game.id}/payment-intent",
        headers=headers,
        json={"guest_count": 0, "payment_method_id": str(second_card.id)},
    )

    assert [response.status_code for response in rejected] == [404, 400]
    assert accepted.status_code == 201, accepted.text
    assert len(stripe.created) == 1
    assert booking_for(db, game, user).booking_status == "confirmed"


@pytest.mark.page("F17", 12)
def test_card_authentication_leaves_the_spot_unconfirmed(db, client, firebase, stripe):
    game = upcoming_game(db)
    user, card = paying_player(db, stripe)
    stripe.confirm_status = "requires_action"

    response = client.post(
        f"/checkout/games/{game.id}/payment-intent",
        headers=firebase.sign_in(user),
        json={"guest_count": 0, "payment_method_id": str(card.id)},
    )

    assert response.status_code == 201, response.text
    assert response.json()["stripe_status"] == "requires_action"
    assert response.json()["client_secret"]
    booking = booking_for(db, game, user)
    assert booking.booking_status == "pending_payment"
    assert roster_statuses(db, booking) == ["pending_payment"]


@pytest.mark.page("F17", 12)
def test_an_expired_saved_card_is_rejected_before_any_hold(
    db, client, firebase, stripe
):
    game = upcoming_game(db)
    user, _card = paying_player(db, stripe)
    expired = make_saved_card(db, user=user, is_default=False, exp_year=2020)

    response = client.post(
        f"/checkout/games/{game.id}/payment-intent",
        headers=firebase.sign_in(user),
        json={"guest_count": 0, "payment_method_id": str(expired.id)},
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"] == "This saved card is expired. Choose another card."
    )
    assert booking_for(db, game, user) is None
    assert stripe.created == []


@pytest.mark.page("F17", 13)
def test_expired_hold_then_late_payment_is_refunded_not_confirmed(
    db, client, firebase, stripe
):
    game = upcoming_game(db)
    user, card = paying_player(db, stripe)
    stripe.confirm_status = "requires_action"
    headers = firebase.sign_in(user)
    client.post(
        f"/checkout/games/{game.id}/payment-intent",
        headers=headers,
        json={"guest_count": 0, "payment_method_id": str(card.id)},
    )
    booking = booking_for(db, game, user)
    booking.expires_at = database_now(db) - timedelta(seconds=1)
    db.commit()

    status = client.get(f"/checkout/bookings/{booking.id}/status", headers=headers)
    stripe.report(db, only_payment(db, booking), "succeeded")

    assert status.status_code == 200, status.text
    assert status.json()["booking_status"] == "expired"
    db.refresh(booking)
    assert booking.booking_status == "expired"
    assert roster_statuses(db, booking) == ["cancelled"]
    compensation = db.scalars(
        select(PaymentCompensation).where(PaymentCompensation.booking_id == booking.id)
    ).one()
    assert (compensation.reason, compensation.action) == (
        "reservation_expired",
        "refund",
    )


@pytest.mark.page("F17", 14)
def test_submitting_twice_while_pending_keeps_one_booking(db, client, firebase, stripe):
    game = upcoming_game(db)
    user, card = paying_player(db, stripe)
    stripe.confirm_status = "requires_action"
    headers = firebase.sign_in(user)
    body = {"guest_count": 0, "payment_method_id": str(card.id)}

    first = client.post(
        f"/checkout/games/{game.id}/payment-intent", headers=headers, json=body
    )
    second = client.post(
        f"/checkout/games/{game.id}/payment-intent", headers=headers, json=body
    )

    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert first.json()["booking_id"] == second.json()["booking_id"]
    bookings = db.scalars(select(Booking).where(Booking.game_id == game.id)).all()
    assert len(bookings) == 1
    assert len(stripe.created) == 1


@pytest.mark.page("F17", 19)
def test_full_credit_confirms_without_a_card_and_deducts_once(
    db, client, firebase, stripe
):
    game = upcoming_game(db, price_per_player_cents=1000)
    user, _card = paying_player(db, stripe)
    credit = make_game_credit(db, user=user, amount_cents=1500)

    response = client.post(
        f"/checkout/games/{game.id}/payment-intent",
        headers=firebase.sign_in(user),
        json={"guest_count": 0},
    )

    assert response.status_code == 201, response.text
    assert response.json()["final_amount_due_cents"] == 0
    booking = booking_for(db, game, user)
    assert booking.booking_status == "confirmed"
    assert (
        db.scalars(select(Payment).where(Payment.booking_id == booking.id)).all() == []
    )
    assert [(u.amount_cents, u.usage_status) for u in credit_usages(db, booking)] == [
        (1000, "redeemed")
    ]
    db.refresh(credit)
    assert credit.available_cents == 500
    assert stripe.created == []


@pytest.mark.page("F17", 20)
def test_partial_credit_is_released_when_the_payment_fails(
    db, client, firebase, stripe
):
    game = upcoming_game(db, price_per_player_cents=1000)
    user, card = paying_player(db, stripe)
    credit = make_game_credit(db, user=user, amount_cents=300)
    stripe.confirm_status = "requires_payment_method"
    client.post(
        f"/checkout/games/{game.id}/payment-intent",
        headers=firebase.sign_in(user),
        json={"guest_count": 0, "payment_method_id": str(card.id)},
    )
    booking = booking_for(db, game, user)
    payment = only_payment(db, booking)

    stripe.report(db, payment, "canceled")

    assert payment.amount_cents == 700
    db.refresh(booking)
    db.refresh(credit)
    assert booking.booking_status == "failed"
    assert roster_statuses(db, booking) == ["cancelled"]
    assert [u.usage_status for u in credit_usages(db, booking)] == ["released"]
    assert credit.available_cents == 300


@pytest.mark.page("F17", 21)
def test_overlapping_checkouts_cannot_spend_the_same_credit_twice(
    db, client, firebase, stripe
):
    first_game = upcoming_game(db, price_per_player_cents=1000)
    second_game = upcoming_game(db, price_per_player_cents=1000)
    user, card = paying_player(db, stripe)
    make_game_credit(db, user=user, amount_cents=500)
    stripe.confirm_status = "requires_action"
    headers = firebase.sign_in(user)
    body = {"guest_count": 0, "payment_method_id": str(card.id)}

    first = client.post(
        f"/checkout/games/{first_game.id}/payment-intent", headers=headers, json=body
    )
    second = client.post(
        f"/checkout/games/{second_game.id}/payment-intent", headers=headers, json=body
    )

    assert first.json()["credit_applied_cents"] == 500
    assert second.json()["credit_applied_cents"] == 0
    assert second.json()["final_amount_due_cents"] == 1000
    used = db.scalars(
        select(GameCreditUsage).where(GameCreditUsage.usage_status == "reserved")
    ).all()
    assert sum(usage.amount_cents for usage in used) == 500


@pytest.mark.page("F17", 24)
def test_small_remainder_after_credit_is_covered_and_recorded_apart(
    db, client, firebase, stripe
):
    game = upcoming_game(db, price_per_player_cents=1000)
    user, _card = paying_player(db, stripe)
    make_game_credit(db, user=user, amount_cents=970)

    response = client.post(
        f"/checkout/games/{game.id}/payment-intent",
        headers=firebase.sign_in(user),
        json={"guest_count": 0},
    )

    assert response.status_code == 201, response.text
    assert response.json()["credit_applied_cents"] == 970
    assert response.json()["minimum_charge_adjustment_cents"] == 30
    assert response.json()["final_amount_due_cents"] == 0
    booking = booking_for(db, game, user)
    assert booking.booking_status == "confirmed"
    assert (booking.discount_cents, booking.total_cents) == (1000, 0)
    assert sum(u.amount_cents for u in credit_usages(db, booking)) == 970
    assert stripe.created == []


@pytest.mark.page("F17", 25)
def test_remainder_exactly_at_the_minimum_is_charged_normally(
    db, client, firebase, stripe
):
    game = upcoming_game(db, price_per_player_cents=1000)
    user, card = paying_player(db, stripe)
    make_game_credit(db, user=user, amount_cents=950)

    response = client.post(
        f"/checkout/games/{game.id}/payment-intent",
        headers=firebase.sign_in(user),
        json={"guest_count": 0, "payment_method_id": str(card.id)},
    )

    assert response.status_code == 201, response.text
    assert response.json()["credit_applied_cents"] == 950
    assert response.json()["minimum_charge_adjustment_cents"] == 0
    assert only_payment(db, booking_for(db, game, user)).amount_cents == 50
