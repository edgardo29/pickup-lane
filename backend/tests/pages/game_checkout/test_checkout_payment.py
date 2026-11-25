"""F17 official checkout: credit first, small balances covered, Stripe for the rest."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

import pytest
from sqlalchemy import select

from backend.models import (
    Booking,
    GameCredit,
    GameCreditUsage,
    GameParticipant,
    Payment,
    PaymentCompensation,
    Refund,
)
from backend.services import checkout_service
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
    submit_checkout,
    upcoming_game,
)


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


def start_checkout(
    db,
    client,
    firebase,
    stripe,
    *,
    amount=1000,
    credit_amount=300,
    status="succeeded",
    with_card=True,
    guests=0,
):
    game = upcoming_game(db, price_per_player_cents=amount)
    user, card = paying_player(db, stripe)
    credit = (
        make_game_credit(db, user=user, amount_cents=credit_amount)
        if credit_amount
        else None
    )
    if not with_card:
        db.delete(card)
        db.commit()
    stripe.confirm_status = status
    response = submit_checkout(
        client, firebase, game, user, card if with_card else None, guests=guests
    )
    assert response.status_code == 201, response.text
    booking = booking_for(db, game, user)
    return game, user, card, credit, booking, response


@pytest.mark.page("F17", 3)
def test_quote_returns_party_price(db, client, firebase, stripe):
    game = upcoming_game(db)
    user, _card = paying_player(db, stripe)
    make_game_credit(db, user=user, amount_cents=400)
    before = financial_and_attendance_state(db)
    response = client.get(
        f"/checkout/games/{game.id}/quote?guest_count=2", headers=firebase.sign_in(user)
    )
    assert response.status_code == 200, response.text
    assert response.json()["checkout_total_cents"] == 3000
    assert financial_and_attendance_state(db) == before


@pytest.mark.page("F17", 3)
def test_quote_returns_available_credit(db, client, firebase, stripe):
    game = upcoming_game(db)
    user, _card = paying_player(db, stripe)
    make_game_credit(db, user=user, amount_cents=400)
    before = financial_and_attendance_state(db)
    response = client.get(
        f"/checkout/games/{game.id}/quote?guest_count=2", headers=firebase.sign_in(user)
    )
    assert response.status_code == 200, response.text
    assert response.json()["available_credit_cents"] == 400
    assert financial_and_attendance_state(db) == before


@pytest.mark.page("F17", 3)
def test_quote_returns_applied_credit(db, client, firebase, stripe):
    game = upcoming_game(db)
    user, _card = paying_player(db, stripe)
    make_game_credit(db, user=user, amount_cents=400)
    before = financial_and_attendance_state(db)
    response = client.get(
        f"/checkout/games/{game.id}/quote?guest_count=2", headers=firebase.sign_in(user)
    )
    assert response.status_code == 200, response.text
    assert response.json()["credit_applied_cents"] == 400
    assert financial_and_attendance_state(db) == before


@pytest.mark.page("F17", 3)
def test_quote_returns_amount_due(db, client, firebase, stripe):
    game = upcoming_game(db)
    user, _card = paying_player(db, stripe)
    make_game_credit(db, user=user, amount_cents=400)
    before = financial_and_attendance_state(db)
    response = client.get(
        f"/checkout/games/{game.id}/quote?guest_count=2", headers=firebase.sign_in(user)
    )
    assert response.status_code == 200, response.text
    assert response.json()["final_amount_due_cents"] == 2600
    assert financial_and_attendance_state(db) == before


@pytest.mark.page("F17", 3)
def test_stripe_charges_only_the_balance_after_credit(db, client, firebase, stripe):
    _game, _user, _card, _credit, booking, response = start_checkout(
        db, client, firebase, stripe, credit_amount=300, guests=1
    )
    assert only_payment(db, booking).amount_cents == 1700
    assert stripe.created[0]["amount_cents"] == 1700
    assert response.json()["credit_applied_cents"] == 300
    assert booking.booking_status == "confirmed"


@pytest.mark.page("F17", 4)
def test_checkout_uses_the_selected_saved_card(
    db, client, firebase, stripe, monkeypatch
):
    game = upcoming_game(db)
    user, _first = paying_player(db, stripe)
    selected = make_saved_card(db, user=user, is_default=False)
    register_card(stripe, selected)
    calls = []
    confirm = stripe.confirm_payment_intent

    def record_selected(intent_id, **kwargs):
        calls.append(kwargs["payment_method_id"])
        return confirm(intent_id, **kwargs)

    monkeypatch.setattr(checkout_service, "confirm_payment_intent", record_selected)
    response = submit_checkout(client, firebase, game, user, selected)
    assert response.status_code == 201, response.text
    assert calls == [selected.stripe_payment_method_id]
    assert booking_for(db, game, user).booking_status == "confirmed"


@pytest.mark.page("F17", 4)
def test_checkout_rejects_another_players_saved_card(db, client, firebase, stripe):
    game = upcoming_game(db)
    user, _card = paying_player(db, stripe)
    _other, card = paying_player(db, stripe)
    before = financial_and_attendance_state(db)
    response = submit_checkout(client, firebase, game, user, card)
    assert response.status_code == 404
    assert response.json()["detail"] == "Payment method not found."
    assert financial_and_attendance_state(db) == before
    assert stripe.created == []


@pytest.mark.page("F17", 4)
@pytest.mark.parametrize("status", ["detached", "expired"])
def test_checkout_rejects_inactive_saved_cards(db, client, firebase, stripe, status):
    game = upcoming_game(db)
    user, card = paying_player(db, stripe)
    card.method_status = status
    card.is_default = False
    db.commit()
    before = financial_and_attendance_state(db)
    response = submit_checkout(client, firebase, game, user, card)
    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Only active payment methods can be used for checkout."
    )
    assert financial_and_attendance_state(db) == before
    assert stripe.created == []


@pytest.mark.page("F17", 12)
def test_expired_card_creates_no_hold_or_charge(db, client, firebase, stripe):
    game = upcoming_game(db)
    user, card = paying_player(db, stripe)
    card.exp_year = 2020
    db.commit()
    before = financial_and_attendance_state(db)
    response = submit_checkout(client, firebase, game, user, card)
    assert response.status_code == 400
    assert (
        response.json()["detail"] == "This saved card is expired. Choose another card."
    )
    assert financial_and_attendance_state(db) == before
    assert stripe.created == []


@pytest.mark.page("F17", 4)
def test_stripe_detached_card_cannot_pay_despite_local_active_state(
    db, client, firebase, stripe
):
    game = upcoming_game(db)
    user, card = paying_player(db, stripe)
    from dataclasses import replace

    stripe.cards[card.stripe_payment_method_id] = replace(
        stripe.cards[card.stripe_payment_method_id], customer_id="cus_other"
    )
    before = financial_and_attendance_state(db)
    response = submit_checkout(client, firebase, game, user, card)
    assert response.status_code == 409
    assert (
        response.json()["detail"]
        == "This saved card is no longer linked to your Stripe customer."
    )
    assert financial_and_attendance_state(db) == before
    assert stripe.created == []
    db.refresh(card)
    assert card.method_status == "detached"


@pytest.mark.page("F17", 13)
def test_paid_checkout_holds_spots_for_exactly_two_minutes(
    db, client, firebase, stripe
):
    now = database_now(db)
    _game, _user, _card, _credit, booking, _response = start_checkout(
        db, client, firebase, stripe, status="requires_action"
    )
    assert booking.expires_at == now + timedelta(minutes=2)
    assert booking.reservation_status == "held"
    assert roster_statuses(db, booking) == ["pending_payment"]


@pytest.mark.page("F17", 3)
def test_processing_payment_does_not_confirm_a_spot(db, client, firebase, stripe):
    _game, _user, _card, _credit, booking, response = start_checkout(
        db, client, firebase, stripe, status="processing"
    )
    assert response.json()["stripe_status"] == "processing"
    assert booking.booking_status == "pending_payment"
    assert roster_statuses(db, booking) == ["pending_payment"]


@pytest.mark.page("F17", 12)
def test_card_authentication_leaves_the_spot_unconfirmed(db, client, firebase, stripe):
    _game, _user, _card, _credit, booking, response = start_checkout(
        db, client, firebase, stripe, status="requires_action"
    )
    assert response.json()["stripe_status"] == "requires_action"
    assert response.json()["client_secret"]
    assert booking.booking_status == "pending_payment"
    assert roster_statuses(db, booking) == ["pending_payment"]


@pytest.mark.page("F17", 20)
def test_failed_required_payment_does_not_finalize_a_booking(
    db, client, firebase, stripe
):
    _game, _user, _card, _credit, booking, _response = start_checkout(
        db, client, firebase, stripe, status="requires_action"
    )
    stripe.report(db, only_payment(db, booking), "canceled")
    db.refresh(booking)
    assert booking.booking_status == "failed"
    assert roster_statuses(db, booking) == ["cancelled"]


@pytest.mark.page("F17", 13)
def test_expired_hold_releases_capacity_without_confirmation(
    db, client, firebase, stripe
):
    game, user, _card, _credit, booking, _response = start_checkout(
        db, client, firebase, stripe, status="requires_action"
    )
    booking.expires_at = database_now(db)
    db.commit()
    response = client.get(
        f"/checkout/bookings/{booking.id}/status", headers=firebase.sign_in(user)
    )
    assert response.status_code == 200
    assert response.json()["booking_status"] == "expired"
    db.refresh(booking)
    assert booking.reservation_status == "released"
    assert roster_statuses(db, booking) == ["cancelled"]
    from backend.services.game_service import count_roster_players

    assert count_roster_players(db, game.id, now=database_now(db)) == 0


@pytest.mark.page("F17", 13)
def test_late_payment_creates_a_refund_instead_of_reviving_an_expired_hold(
    db, client, firebase, stripe
):
    _game, _user, _card, _credit, booking, _response = start_checkout(
        db, client, firebase, stripe, status="requires_action"
    )
    booking.expires_at = database_now(db)
    db.commit()
    stripe.report(db, only_payment(db, booking), "succeeded")
    db.refresh(booking)
    assert booking.booking_status == "expired"
    assert roster_statuses(db, booking) == ["cancelled"]
    compensation = db.scalar(
        select(PaymentCompensation).where(PaymentCompensation.booking_id == booking.id)
    )
    assert compensation is not None
    assert (compensation.reason, compensation.action) == (
        "reservation_expired",
        "refund",
    )
    assert compensation.refund_id is not None
    assert db.get(Refund, compensation.refund_id).amount_cents == 700


@pytest.mark.page("F17", 13)
def test_capacity_conflict_after_payment_creates_a_refund(db, client, firebase, stripe):
    game, _user, _card, _credit, booking, _response = start_checkout(
        db, client, firebase, stripe, status="requires_action"
    )
    game.total_spots = 1
    make_participant(db, game=game, booking=make_booking(db, game=game))
    db.commit()
    stripe.report(db, only_payment(db, booking), "succeeded")
    db.refresh(booking)
    assert booking.booking_status == "capacity_conflict"
    assert roster_statuses(db, booking) == ["cancelled"]
    compensation = db.scalar(
        select(PaymentCompensation).where(PaymentCompensation.booking_id == booking.id)
    )
    assert compensation is not None
    assert (compensation.reason, compensation.action) == ("capacity_conflict", "refund")
    assert compensation.refund_id is not None
    assert db.get(Refund, compensation.refund_id).amount_cents == 700


@pytest.mark.page("F17", 19)
def test_full_credit_confirms_without_a_saved_card_or_charge(
    db, client, firebase, stripe
):
    _game, _user, _card, _credit, booking, response = start_checkout(
        db, client, firebase, stripe, credit_amount=1500, with_card=False
    )
    assert response.json()["payment_required"] is False
    assert booking.booking_status == "confirmed"
    assert roster_statuses(db, booking) == ["confirmed"]
    assert (
        db.scalars(select(Payment).where(Payment.booking_id == booking.id)).all() == []
    )
    assert stripe.created == []


@pytest.mark.page("F17", 19)
def test_reserved_credit_is_redeemed_only_when_checkout_completes(
    db, client, firebase, stripe
):
    _game, _user, _card, credit, booking, _response = start_checkout(
        db, client, firebase, stripe, status="requires_action"
    )
    assert booking.booking_status == "pending_payment"
    assert [u.usage_status for u in credit_usages(db, booking)] == ["reserved"]
    stripe.report(db, only_payment(db, booking), "succeeded")
    db.refresh(booking)
    db.refresh(credit)
    assert booking.booking_status == "confirmed"
    assert [(u.amount_cents, u.usage_status) for u in credit_usages(db, booking)] == [
        (300, "redeemed")
    ]
    assert credit.available_cents == 0


@pytest.mark.page("F17", 20)
def test_reserved_credit_is_released_when_payment_fails(db, client, firebase, stripe):
    _game, _user, _card, credit, booking, _response = start_checkout(
        db, client, firebase, stripe, status="requires_action"
    )
    db.refresh(credit)
    assert credit.available_cents == 0
    stripe.report(db, only_payment(db, booking), "canceled")
    db.refresh(credit)
    db.refresh(booking)
    assert credit.available_cents == 300
    assert [u.usage_status for u in credit_usages(db, booking)] == ["released"]
    assert booking.booking_status != "confirmed"


@pytest.mark.page("F17", 20)
def test_reserved_credit_is_released_when_payment_expires(db, client, firebase, stripe):
    _game, user, _card, credit, booking, _response = start_checkout(
        db, client, firebase, stripe, status="requires_action"
    )
    db.refresh(credit)
    assert credit.available_cents == 0
    booking.expires_at = database_now(db)
    db.commit()
    assert (
        client.get(
            f"/checkout/bookings/{booking.id}/status", headers=firebase.sign_in(user)
        ).status_code
        == 200
    )
    db.refresh(credit)
    db.refresh(booking)
    assert credit.available_cents == 300
    assert [u.usage_status for u in credit_usages(db, booking)] == ["released"]
    assert booking.booking_status != "confirmed"


@pytest.mark.page("F17", 21)
def test_overlapping_checkouts_cannot_spend_the_same_credit_twice(
    committed_db, client, firebase, stripe, monkeypatch
):
    first_game = upcoming_game(committed_db, price_per_player_cents=1000)
    second_game = upcoming_game(committed_db, price_per_player_cents=1000)
    user, card = paying_player(committed_db, stripe)
    credit = make_game_credit(committed_db, user=user, amount_cents=500)
    committed_db.commit()
    stripe.confirm_status = "requires_action"
    headers = firebase.sign_in(user)
    body = {"guest_count": 0, "payment_method_id": str(card.id)}
    both_at_reservation = Barrier(2)
    reserve = checkout_service.reserve_game_credits

    def reserve_after_both_priced(*args, **kwargs):
        both_at_reservation.wait(timeout=10)
        return reserve(*args, **kwargs)

    monkeypatch.setattr(
        checkout_service, "reserve_game_credits", reserve_after_both_priced
    )
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(
            client.post,
            f"/checkout/games/{first_game.id}/payment-intent",
            headers=headers,
            json=body,
        )
        second = pool.submit(
            client.post,
            f"/checkout/games/{second_game.id}/payment-intent",
            headers=headers,
            json=body,
        )
        responses = [first.result(timeout=30), second.result(timeout=30)]

    assert sorted(response.status_code for response in responses) == [201, 409]
    assert [
        response.json()["credit_applied_cents"]
        for response in responses
        if response.status_code == 201
    ] == [500]
    committed_db.expire_all()
    used = committed_db.scalars(
        select(GameCreditUsage).where(GameCreditUsage.usage_status == "reserved")
    ).all()
    assert sum(usage.amount_cents for usage in used) == 500
    assert committed_db.get(GameCredit, credit.id).available_cents == 0
    bookings = committed_db.scalars(
        select(Booking).where(Booking.buyer_user_id == user.id)
    ).all()
    assert len(bookings) == 1


@pytest.mark.page("F17", 21)
def test_repeated_checkout_does_not_spend_the_same_credit_twice(
    db, client, firebase, stripe
):
    game, user, card, credit, booking, _response = start_checkout(
        db, client, firebase, stripe, status="requires_action"
    )
    response = submit_checkout(client, firebase, game, user, card)
    assert response.status_code == 201, response.text
    assert response.json()["booking_id"] == str(booking.id)
    assert [(u.amount_cents, u.usage_status) for u in credit_usages(db, booking)] == [
        (300, "reserved")
    ]
    stripe.report(db, only_payment(db, booking), "succeeded")
    stripe.report(db, only_payment(db, booking), "succeeded")
    db.refresh(credit)
    assert credit.available_cents == 0
    assert [(u.amount_cents, u.usage_status) for u in credit_usages(db, booking)] == [
        (300, "redeemed")
    ]
    assert len(stripe.created) == 1


@pytest.mark.page("F17", 24)
def test_small_remainder_is_covered_without_a_card_charge(db, client, firebase, stripe):
    _game, _user, _card, _credit, booking, response = start_checkout(
        db, client, firebase, stripe, credit_amount=970, with_card=False
    )
    assert response.json()["credit_applied_cents"] == 970
    assert response.json()["final_amount_due_cents"] == 0
    assert response.json()["minimum_charge_adjustment_cents"] == 30
    assert booking.booking_status == "confirmed"
    assert stripe.created == []


@pytest.mark.page("F17", 24)
def test_credit_and_small_balance_coverage_are_recorded_separately(
    db, client, firebase, stripe
):
    _game, _user, _card, _credit, booking, response = start_checkout(
        db, client, firebase, stripe, credit_amount=970, with_card=False
    )
    assert [(u.amount_cents, u.usage_status) for u in credit_usages(db, booking)] == [
        (970, "redeemed")
    ]
    assert (booking.discount_cents, booking.total_cents) == (1000, 0)
    assert response.json()["minimum_charge_adjustment_cents"] == 30


@pytest.mark.page("F17", 25)
def test_balance_exactly_at_stripes_minimum_is_charged(db, client, firebase, stripe):
    _game, _user, _card, _credit, booking, response = start_checkout(
        db, client, firebase, stripe, credit_amount=950
    )
    assert response.json()["credit_applied_cents"] == 950
    assert response.json()["minimum_charge_adjustment_cents"] == 0
    assert only_payment(db, booking).amount_cents == 50
    assert booking.booking_status == "confirmed"


@pytest.mark.page("F17", 26)
def test_low_price_without_credit_confirms_without_a_card(db, client, firebase, stripe):
    _game, _user, _card, _credit, booking, response = start_checkout(
        db, client, firebase, stripe, amount=30, credit_amount=0, with_card=False
    )
    assert booking.booking_status == "confirmed"
    assert response.json()["minimum_charge_adjustment_cents"] == 30
    assert response.json()["final_amount_due_cents"] == 0
    assert (
        db.scalars(select(Payment).where(Payment.booking_id == booking.id)).all() == []
    )
    assert stripe.created == []


@pytest.mark.page("F17", 26)
def test_covered_low_price_does_not_invent_game_credit(db, client, firebase, stripe):
    _game, _user, _card, _credit, booking, response = start_checkout(
        db, client, firebase, stripe, amount=30, credit_amount=0, with_card=False
    )
    assert response.json()["credit_applied_cents"] == 0
    assert db.scalars(select(GameCredit)).all() == []
    assert credit_usages(db, booking) == []


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


def only_payment(db, booking):
    return db.scalars(select(Payment).where(Payment.booking_id == booking.id)).one()


def credit_usages(db, booking):
    return db.scalars(
        select(GameCreditUsage).where(GameCreditUsage.booking_id == booking.id)
    ).all()


@pytest.mark.page("F17", 3)
@pytest.mark.parametrize("new_credit", [0, 200])
def test_reopened_checkout_quote_keeps_its_reserved_credit(
    db, client, firebase, stripe, new_credit
):
    game, user, _card, _credit, _booking, _response = start_checkout(
        db, client, firebase, stripe, credit_amount=300, status="processing"
    )
    if new_credit:
        make_game_credit(db, user=user, amount_cents=new_credit)
    before = financial_and_attendance_state(db)
    response = client.get(
        f"/checkout/games/{game.id}/quote?guest_count=0", headers=firebase.sign_in(user)
    )
    assert response.status_code == 200, response.text
    assert response.json()["credit_applied_cents"] == 300
    assert response.json()["available_credit_cents"] == 300 + new_credit
    assert response.json()["final_amount_due_cents"] == 700
    assert financial_and_attendance_state(db) == before
