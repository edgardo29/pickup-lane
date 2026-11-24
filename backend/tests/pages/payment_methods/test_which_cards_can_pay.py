"""F13 only active, unexpired saved cards can pay for anything.

A removed or expired card cannot be chosen for a paid waitlist, checkout, or a
publish fee, and a card removed or expired while its owner waits on a paid
waitlist is not charged when a spot opens.
"""

import dataclasses
import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy import func, select

from backend.models import (
    Booking,
    CommunityPublishAttempt,
    Game,
    GameParticipant,
    Payment,
    UserPaymentMethod,
    WaitlistEntry,
)
from backend.tests.conftest import database_now
from backend.tests.factories import make_booking, make_game, make_participant, make_user

EXPIRED_DETAIL = "This saved card is expired. Choose another card."
WAITLIST_CONSENT = {
    "auto_charge_consent_accepted": True,
    "auto_charge_consent_version": "waitlist-auto-charge-v1",
}


def player(db, **overrides):
    return make_user(db, date_of_birth=date(1990, 1, 1), **overrides)


def with_key(headers):
    return {**headers, "Idempotency-Key": str(uuid.uuid4())}


def add_card(client, headers, stripe, *, fingerprint):
    """Run the page's add-card flow: start setup, enter a card, then save it."""
    is_first = not client.get("/user-payment-methods", headers=headers).json()
    setup = client.post(
        "/user-payment-methods/setup-intent",
        headers=with_key(headers),
        json={"set_as_default": is_first},
    )
    setup_intent_id = setup.json()["client_secret"].removesuffix("_secret")
    stripe.enter_card(setup_intent_id, fingerprint=fingerprint)
    saved = client.post(
        "/user-payment-methods/sync",
        headers=with_key(headers),
        json={"setup_intent_id": setup_intent_id, "set_as_default": is_first},
    )
    assert saved.status_code == 201, saved.text
    return uuid.UUID(saved.json()["id"])


def remove(client, headers, card_id):
    response = client.delete(
        f"/user-payment-methods/{card_id}", headers=with_key(headers)
    )
    assert response.status_code == 200, response.text


def let_card_expire(db, stripe, card_id):
    """Time passes and the saved card's expiry date is now last month.

    Stripe reports the same expiry the card was saved with, so both the saved
    card and Stripe's copy of it carry the past date.
    """
    last_month = database_now(db).replace(day=1) - timedelta(days=1)
    card = db.get(UserPaymentMethod, card_id)
    card.exp_month, card.exp_year = last_month.month, last_month.year
    db.commit()
    provider_card = stripe.cards[card.stripe_payment_method_id]
    stripe.cards[card.stripe_payment_method_id] = dataclasses.replace(
        provider_card, exp_month=last_month.month, exp_year=last_month.year
    )


def full_paid_game(db):
    """A paid official game with one spot, held by a player who can leave."""
    game = make_game(
        db,
        starts_at=database_now(db) + timedelta(days=2),
        total_spots=1,
        waitlist_enabled=True,
    )
    holder = player(db)
    booking = make_booking(db, game=game, buyer=holder)
    make_participant(db, game=game, booking=booking, user=holder)
    return game, holder


def join_waitlist(client, headers, game, card_id):
    return client.post(
        f"/games/{game.id}/join",
        headers=headers,
        json={"guest_count": 0, "payment_method_id": str(card_id), **WAITLIST_CONSENT},
    )


def waitlist_entries(db, user):
    return db.scalars(
        select(WaitlistEntry).where(WaitlistEntry.user_id == user.id)
    ).all()


def participant_statuses(db, game, user):
    return db.scalars(
        select(GameParticipant.participant_status).where(
            GameParticipant.game_id == game.id, GameParticipant.user_id == user.id
        )
    ).all()


def payments_for(db, user):
    return db.scalars(select(Payment).where(Payment.payer_user_id == user.id)).all()


@pytest.mark.page("F13", 9)
def test_a_removed_card_cannot_be_chosen_for_a_paid_waitlist(
    db, client, firebase, stripe
):
    game, _holder = full_paid_game(db)
    me = player(db)
    headers = firebase.sign_in(me)
    removed = add_card(client, headers, stripe, fingerprint="fp_removed")
    add_card(client, headers, stripe, fingerprint="fp_kept")
    remove(client, headers, removed)

    response = join_waitlist(client, headers, game, removed)

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Only active payment methods can be used for waitlist auto-charge."
    )
    assert waitlist_entries(db, me) == []
    assert participant_statuses(db, game, me) == []
    assert payments_for(db, me) == []


@pytest.mark.page("F13", 9)
def test_an_expired_card_cannot_be_chosen_for_a_paid_waitlist(
    db, client, firebase, stripe
):
    game, _holder = full_paid_game(db)
    me = player(db)
    headers = firebase.sign_in(me)
    expired = add_card(client, headers, stripe, fingerprint="fp_expired")
    let_card_expire(db, stripe, expired)

    response = join_waitlist(client, headers, game, expired)

    assert response.status_code == 400
    assert response.json()["detail"] == EXPIRED_DETAIL
    assert waitlist_entries(db, me) == []
    assert participant_statuses(db, game, me) == []
    assert payments_for(db, me) == []


@pytest.mark.page("F13", 9)
def test_a_card_removed_while_on_a_paid_waitlist_is_not_charged_when_a_spot_opens(
    db, client, firebase, stripe
):
    game, holder = full_paid_game(db)
    me = player(db)
    headers = firebase.sign_in(me)
    authorized = add_card(client, headers, stripe, fingerprint="fp_authorized")
    add_card(client, headers, stripe, fingerprint="fp_kept")
    joined = join_waitlist(client, headers, game, authorized)
    assert joined.status_code == 201, joined.text
    remove(client, headers, authorized)

    left = client.post(
        f"/games/{game.id}/leave", headers=firebase.sign_in(holder), json={}
    )

    assert left.status_code == 200, left.text
    db.expire_all()
    (entry,) = waitlist_entries(db, me)
    assert entry.waitlist_status == "payment_failed"
    assert "confirmed" not in participant_statuses(db, game, me)
    assert [payment.payment_status for payment in payments_for(db, me)] == ["failed"]
    assert stripe.created == []
    booking = db.scalars(
        select(Booking).where(
            Booking.game_id == game.id, Booking.buyer_user_id == me.id
        )
    ).one()
    assert booking.booking_status != "confirmed"


@pytest.mark.page("F13", 9)
def test_a_card_that_expires_while_on_a_paid_waitlist_is_not_charged_when_a_spot_opens(
    db, client, firebase, stripe
):
    game, holder = full_paid_game(db)
    me = player(db)
    headers = firebase.sign_in(me)
    authorized = add_card(client, headers, stripe, fingerprint="fp_authorized")
    joined = join_waitlist(client, headers, game, authorized)
    assert joined.status_code == 201, joined.text
    let_card_expire(db, stripe, authorized)

    left = client.post(
        f"/games/{game.id}/leave", headers=firebase.sign_in(holder), json={}
    )

    assert left.status_code == 200, left.text
    db.expire_all()
    (entry,) = waitlist_entries(db, me)
    assert entry.waitlist_status == "payment_failed"
    assert "confirmed" not in participant_statuses(db, game, me)
    assert [payment.payment_status for payment in payments_for(db, me)] == ["failed"]
    assert stripe.created == []
    assert db.get(UserPaymentMethod, authorized).method_status == "expired"


@pytest.mark.page("F13", 9)
def test_an_expired_card_cannot_pay_at_checkout(db, client, firebase, stripe):
    me = player(db)
    headers = firebase.sign_in(me)
    expired = add_card(client, headers, stripe, fingerprint="fp_expired")
    let_card_expire(db, stripe, expired)
    game = make_game(db, starts_at=database_now(db) + timedelta(days=2))

    response = client.post(
        f"/checkout/games/{game.id}/payment-intent",
        headers=headers,
        json={"payment_method_id": str(expired)},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == EXPIRED_DETAIL
    assert participant_statuses(db, game, me) == []
    assert payments_for(db, me) == []
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


@pytest.mark.page("F13", 9)
def test_an_expired_card_cannot_pay_a_publish_fee(
    db, client, firebase, stripe, monkeypatch
):
    use_fake_stripe_for_publish_fees(monkeypatch, stripe)
    me = player(db, hosting_status="eligible")
    headers = firebase.sign_in(me)
    expired = add_card(client, headers, stripe, fingerprint="fp_expired")
    first_day = database_now(db) + timedelta(days=2)
    # The host's first game uses the free publish, so the next one owes a fee.
    free = client.post(
        "/community-games/publish",
        headers=headers,
        json=community_game_request(first_day),
    )
    assert free.status_code == 201, free.text
    assert free.json()["status"] == "published"
    let_card_expire(db, stripe, expired)

    response = client.post(
        "/community-games/publish",
        headers=headers,
        json={
            **community_game_request(first_day + timedelta(days=1)),
            "payment_method_id": str(expired),
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == EXPIRED_DETAIL
    hosted_games = select(func.count(Game.id)).where(Game.host_user_id == me.id)
    assert db.scalar(hosted_games) == 1
    attempts = select(func.count(CommunityPublishAttempt.id)).where(
        CommunityPublishAttempt.host_user_id == me.id
    )
    assert db.scalar(attempts) == 0
    assert payments_for(db, me) == []
    assert stripe.created == []
