"""F13 changing the default card and removing cards."""

import dataclasses
import time
import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy import func, select

from backend.models import (
    Booking,
    CommunityPublishAttempt,
    Game,
    Payment,
    UserPaymentMethod,
)
from backend.services import payment_method_service
from backend.services.payment_method_service import (
    verify_saved_payment_method_with_stripe as real_stripe_verification,
)
from backend.tests.conftest import database_now
from backend.tests.factories import make_game, make_user


def player(db, **overrides):
    return make_user(db, date_of_birth=date(1990, 1, 1), **overrides)


def with_key(headers):
    return {**headers, "Idempotency-Key": str(uuid.uuid4())}


def add_card(client, headers, stripe, *, fingerprint, last4="4242"):
    """Run the page's add-card flow: start setup, enter a card, then save it."""
    is_first = not client.get("/user-payment-methods", headers=headers).json()
    setup = client.post(
        "/user-payment-methods/setup-intent",
        headers=with_key(headers),
        json={"set_as_default": is_first},
    )
    setup_intent_id = setup.json()["client_secret"].removesuffix("_secret")
    stripe.enter_card(setup_intent_id, fingerprint=fingerprint, last4=last4)
    saved = client.post(
        "/user-payment-methods/sync",
        headers=with_key(headers),
        json={"setup_intent_id": setup_intent_id, "set_as_default": is_first},
    )
    assert saved.status_code == 201, saved.text
    return uuid.UUID(saved.json()["id"])


def cards_by_id(db, user):
    db.expire_all()
    return {
        card.id: card
        for card in db.scalars(
            select(UserPaymentMethod).where(UserPaymentMethod.user_id == user.id)
        )
    }


def set_default(client, headers, card_id):
    return client.patch(
        f"/user-payment-methods/{card_id}/default", headers=with_key(headers)
    )


def remove(client, headers, card_id):
    return client.delete(f"/user-payment-methods/{card_id}", headers=with_key(headers))


@pytest.mark.page("F13", 3)
def test_making_another_card_default_leaves_exactly_that_card_default(
    db, client, firebase, stripe
):
    me = player(db)
    headers = firebase.sign_in(me)
    first = add_card(client, headers, stripe, fingerprint="fp_first")
    second = add_card(client, headers, stripe, fingerprint="fp_second")

    response = set_default(client, headers, second)

    assert response.status_code == 200, response.text
    cards = cards_by_id(db, me)
    assert (cards[first].is_default, cards[second].is_default) == (False, True)
    db.refresh(me)
    assert stripe.customer_defaults[me.stripe_customer_id] == (
        cards[second].stripe_payment_method_id
    )


@pytest.mark.page("F13", 4)
def test_a_removed_card_is_detached_and_no_longer_listed(db, client, firebase, stripe):
    me = player(db)
    headers = firebase.sign_in(me)
    kept = add_card(client, headers, stripe, fingerprint="fp_kept")
    removed = add_card(client, headers, stripe, fingerprint="fp_removed")

    response = remove(client, headers, removed)

    assert response.status_code == 200, response.text
    cards = cards_by_id(db, me)
    assert cards[removed].method_status == "detached"
    assert cards[removed].detached_at is not None
    assert cards[removed].stripe_payment_method_id in stripe.detached
    listed = client.get("/user-payment-methods", headers=headers).json()
    assert [card["id"] for card in listed] == [str(kept)]


@pytest.mark.page("F13", 4)
def test_removing_the_default_card_promotes_the_oldest_remaining_card(
    db, client, firebase, stripe
):
    me = player(db)
    headers = firebase.sign_in(me)
    first = add_card(client, headers, stripe, fingerprint="fp_first")
    newest = add_card(client, headers, stripe, fingerprint="fp_newest")
    middle = add_card(client, headers, stripe, fingerprint="fp_middle")
    # Cards saved in one test share a creation time; set the order explicitly.
    now = database_now(db)
    for offset, card_id in enumerate([first, middle, newest]):
        db.get(UserPaymentMethod, card_id).created_at = now + timedelta(minutes=offset)
    db.commit()

    response = remove(client, headers, first)

    assert response.status_code == 200, response.text
    cards = cards_by_id(db, me)
    assert (cards[middle].is_default, cards[newest].is_default) == (True, False)
    db.refresh(me)
    assert stripe.customer_defaults[me.stripe_customer_id] == (
        cards[middle].stripe_payment_method_id
    )


@pytest.mark.page("F13", 4)
def test_a_removed_card_cannot_be_used_for_checkout(db, client, firebase, stripe):
    me = player(db)
    headers = firebase.sign_in(me)
    card = add_card(client, headers, stripe, fingerprint="fp_removed")
    add_card(client, headers, stripe, fingerprint="fp_kept")
    remove(client, headers, card)
    game = make_game(db, starts_at=database_now(db) + timedelta(days=2))

    response = client.post(
        f"/checkout/games/{game.id}/payment-intent",
        headers=headers,
        json={"payment_method_id": str(card)},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Only active payment methods can be used for checkout."
    )
    bookings = select(func.count(Booking.id)).where(Booking.buyer_user_id == me.id)
    assert db.scalar(bookings) == 0
    assert db.scalar(select(func.count(Payment.id))) == 0
    assert stripe.created == []


def use_fake_stripe_for_publish_fees(monkeypatch, stripe):
    """Publish fees call Stripe from their own module, which the shared stripe
    fixture does not cover; without this, no publish-fee payment can succeed."""
    from backend.services import community_game_publish_service

    for name in ("create_payment_intent", "confirm_payment_intent"):
        monkeypatch.setattr(community_game_publish_service, name, getattr(stripe, name))
    monkeypatch.setattr(
        community_game_publish_service, "get_stripe_currency", lambda: "USD"
    )


def community_game_request(starts_at):
    """A free community game as the Create Game page sends it."""
    return {
        "starts_at": starts_at.isoformat(),
        "ends_at": (starts_at + timedelta(hours=1)).isoformat(),
        "format_label": "7v7",
        "environment_type": "outdoor",
        "total_spots": 14,
        "price_per_player_cents": 0,
        "venue": {
            "name": "Union Park",
            "address_line_1": "100 Shared Street",
            "city": "Chicago",
            "state": "IL",
            "postal_code": "60601",
        },
    }


@pytest.mark.page("F13", 4)
def test_a_removed_card_cannot_pay_a_publish_fee(
    db, client, firebase, stripe, monkeypatch
):
    use_fake_stripe_for_publish_fees(monkeypatch, stripe)
    me = player(db, hosting_status="eligible")
    headers = firebase.sign_in(me)
    removed = add_card(client, headers, stripe, fingerprint="fp_removed")
    add_card(client, headers, stripe, fingerprint="fp_kept")
    remove(client, headers, removed)
    first_day = database_now(db) + timedelta(days=2)
    # The host's first game uses the free publish, so the next one owes a fee.
    free = client.post(
        "/community-games/publish",
        headers=headers,
        json=community_game_request(first_day),
    )
    assert free.status_code == 201, free.text
    assert free.json()["status"] == "published"

    response = client.post(
        "/community-games/publish",
        headers=headers,
        json={
            **community_game_request(first_day + timedelta(days=1)),
            "payment_method_id": str(removed),
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Only active payment methods can be used for checkout."
    )
    hosted_games = select(func.count(Game.id)).where(Game.host_user_id == me.id)
    assert db.scalar(hosted_games) == 1
    attempts = select(func.count(CommunityPublishAttempt.id)).where(
        CommunityPublishAttempt.host_user_id == me.id
    )
    assert db.scalar(attempts) == 0
    assert db.scalar(select(func.count(Payment.id))) == 0
    assert stripe.created == []


@pytest.mark.page("F13", 9)
def test_another_players_card_cannot_be_made_default(db, client, firebase, stripe):
    owner, me = player(db), player(db)
    owner_card = add_card(
        client, firebase.sign_in(owner), stripe, fingerprint="fp_owner"
    )
    # The other player is an ordinary player with a saved card of their own.
    headers = firebase.sign_in(me)
    my_card = add_card(client, headers, stripe, fingerprint="fp_mine")
    db.refresh(me)
    my_stripe_default = stripe.customer_defaults[me.stripe_customer_id]

    response = set_default(client, headers, owner_card)

    assert response.status_code == 404
    assert response.json()["detail"] == "Payment method not found."
    assert cards_by_id(db, me)[my_card].is_default is True
    assert stripe.customer_defaults[me.stripe_customer_id] == my_stripe_default


@pytest.mark.page("F13", 9)
def test_another_players_card_cannot_be_removed(db, client, firebase, stripe):
    owner, me = player(db), player(db)
    owner_card = add_card(
        client, firebase.sign_in(owner), stripe, fingerprint="fp_owner"
    )

    response = remove(client, firebase.sign_in(me), owner_card)

    assert response.status_code == 404
    assert response.json()["detail"] == "Payment method not found."
    card = cards_by_id(db, owner)[owner_card]
    assert (card.method_status, card.is_default) == ("active", True)
    assert card.stripe_payment_method_id not in stripe.detached


@pytest.mark.page("F13", 9)
def test_a_removed_card_cannot_be_made_default(db, client, firebase, stripe):
    me = player(db)
    headers = firebase.sign_in(me)
    kept = add_card(client, headers, stripe, fingerprint="fp_kept")
    removed = add_card(client, headers, stripe, fingerprint="fp_removed")
    remove(client, headers, removed)

    response = set_default(client, headers, removed)

    assert response.status_code == 400
    assert (
        response.json()["detail"] == "Only active payment methods can be made default."
    )
    cards = cards_by_id(db, me)
    assert (cards[kept].is_default, cards[removed].is_default) == (True, False)


def use_real_stripe_verification(monkeypatch):
    """The shared stripe fixture skips the check that asks Stripe whether a
    saved card is still valid; turn it back on for tests of that check."""
    monkeypatch.setattr(
        payment_method_service,
        "verify_saved_payment_method_with_stripe",
        real_stripe_verification,
    )


def let_card_expire(db, stripe, card_id):
    """Time passes and the saved card's expiry date is now last month."""
    last_month = database_now(db).replace(day=1) - timedelta(days=1)
    card = db.get(UserPaymentMethod, card_id)
    card.exp_month, card.exp_year = last_month.month, last_month.year
    db.commit()
    provider_card = stripe.cards[card.stripe_payment_method_id]
    stripe.cards[card.stripe_payment_method_id] = dataclasses.replace(
        provider_card, exp_month=last_month.month, exp_year=last_month.year
    )


@pytest.mark.page("F13", 9)
def test_an_expired_card_cannot_be_made_default(
    db, client, firebase, stripe, monkeypatch
):
    use_real_stripe_verification(monkeypatch)
    me = player(db)
    headers = firebase.sign_in(me)
    kept = add_card(client, headers, stripe, fingerprint="fp_kept")
    expired = add_card(client, headers, stripe, fingerprint="fp_expired")
    let_card_expire(db, stripe, expired)

    response = set_default(client, headers, expired)

    assert response.status_code == 400
    assert (
        response.json()["detail"] == "This saved card is expired. Choose another card."
    )
    cards = cards_by_id(db, me)
    assert (cards[kept].is_default, cards[expired].is_default) == (True, False)


@pytest.mark.page("F13", 4)
def test_an_expired_card_can_be_removed(db, client, firebase, stripe, monkeypatch):
    use_real_stripe_verification(monkeypatch)
    me = player(db)
    headers = firebase.sign_in(me)
    kept = add_card(client, headers, stripe, fingerprint="fp_kept")
    expired = add_card(client, headers, stripe, fingerprint="fp_expired")
    let_card_expire(db, stripe, expired)

    response = remove(client, headers, expired)

    assert response.status_code == 200, response.text
    cards = cards_by_id(db, me)
    assert cards[expired].method_status == "detached"
    assert cards[expired].stripe_payment_method_id in stripe.detached
    assert (cards[kept].method_status, cards[kept].is_default) == ("active", True)


@pytest.mark.page("F13", 9)
def test_making_a_card_default_without_recent_confirmation_is_refused(
    db, client, firebase, stripe
):
    me = player(db)
    first = add_card(client, firebase.sign_in(me), stripe, fingerprint="fp_first")
    second = add_card(client, firebase.sign_in(me), stripe, fingerprint="fp_second")
    stale = firebase.sign_in(me, auth_time=int(time.time()) - 24 * 60 * 60)

    response = set_default(client, stale, second)

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "AUTH.RECENT_AUTH_REQUIRED"
    cards = cards_by_id(db, me)
    assert (cards[first].is_default, cards[second].is_default) == (True, False)


@pytest.mark.page("F13", 9)
def test_removing_a_card_without_recent_confirmation_is_refused(
    db, client, firebase, stripe
):
    me = player(db)
    card = add_card(client, firebase.sign_in(me), stripe, fingerprint="fp_card")
    stale = firebase.sign_in(me, auth_time=int(time.time()) - 24 * 60 * 60)

    response = remove(client, stale, card)

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "AUTH.RECENT_AUTH_REQUIRED"
    stored = cards_by_id(db, me)[card]
    assert (stored.method_status, stored.is_default) == ("active", True)
    assert stored.stripe_payment_method_id not in stripe.detached


@pytest.mark.page("F13", 9)
def test_a_card_change_is_refused_when_stripe_no_longer_links_the_card(
    db, client, firebase, stripe, monkeypatch
):
    use_real_stripe_verification(monkeypatch)
    me = player(db)
    headers = firebase.sign_in(me)
    first = add_card(client, headers, stripe, fingerprint="fp_first")
    unlinked = add_card(client, headers, stripe, fingerprint="fp_unlinked")
    stripe_id = cards_by_id(db, me)[unlinked].stripe_payment_method_id
    stripe.cards[stripe_id] = dataclasses.replace(
        stripe.cards[stripe_id], customer_id=None
    )

    response = set_default(client, headers, unlinked)

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "This saved card is no longer linked to your Stripe customer."
    )
    cards = cards_by_id(db, me)
    assert (cards[first].is_default, cards[unlinked].is_default) == (True, False)
    db.refresh(me)
    assert stripe.customer_defaults[me.stripe_customer_id] == (
        cards[first].stripe_payment_method_id
    )


@pytest.mark.page("F13", 8)
def test_a_failed_default_change_reports_an_error_and_changes_nothing(
    db, client, firebase, stripe
):
    me = player(db)
    headers = firebase.sign_in(me)
    first = add_card(client, headers, stripe, fingerprint="fp_first")
    second = add_card(client, headers, stripe, fingerprint="fp_second")
    stripe.failing.add("set_customer_default_payment_method")

    response = set_default(client, headers, second)

    assert response.status_code == 502
    assert (
        response.json()["detail"] == "Stripe could not set this default payment method."
    )
    cards = cards_by_id(db, me)
    assert (cards[first].is_default, cards[second].is_default) == (True, False)


@pytest.mark.page("F13", 8)
def test_a_failed_default_change_can_be_retried(db, client, firebase, stripe):
    me = player(db)
    headers = firebase.sign_in(me)
    first = add_card(client, headers, stripe, fingerprint="fp_first")
    second = add_card(client, headers, stripe, fingerprint="fp_second")
    stripe.failing.add("set_customer_default_payment_method")
    failed = set_default(client, headers, second)
    assert failed.status_code == 502, failed.text
    stripe.failing.clear()

    retry = set_default(client, headers, second)

    assert retry.status_code == 200, retry.text
    cards = cards_by_id(db, me)
    assert (cards[first].is_default, cards[second].is_default) == (False, True)


@pytest.mark.page("F13", 8)
def test_a_failed_removal_reports_an_error_and_changes_nothing(
    db, client, firebase, stripe
):
    me = player(db)
    headers = firebase.sign_in(me)
    card = add_card(client, headers, stripe, fingerprint="fp_card")
    stripe.failing.add("detach_payment_method")

    response = remove(client, headers, card)

    assert response.status_code == 502
    assert response.json()["detail"] == "Stripe could not detach this payment method."
    stored = cards_by_id(db, me)[card]
    assert (stored.method_status, stored.is_default) == ("active", True)


@pytest.mark.page("F13", 8)
def test_a_failed_removal_can_be_retried(db, client, firebase, stripe):
    me = player(db)
    headers = firebase.sign_in(me)
    card = add_card(client, headers, stripe, fingerprint="fp_card")
    stripe.failing.add("detach_payment_method")
    failed = remove(client, headers, card)
    assert failed.status_code == 502, failed.text
    stripe.failing.clear()

    retry = remove(client, headers, card)

    assert retry.status_code == 200, retry.text
    assert cards_by_id(db, me)[card].method_status == "detached"
