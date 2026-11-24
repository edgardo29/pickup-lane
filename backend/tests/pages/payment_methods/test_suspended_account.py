"""F13 saved cards for suspended, deleting, and deleted accounts."""

import time
import uuid
from datetime import date

import pytest
from sqlalchemy import func, select

from backend.models import PaymentMethodOperation, UserPaymentMethod
from backend.tests.factories import make_user


def player(db, **overrides):
    return make_user(db, date_of_birth=date(1990, 1, 1), **overrides)


def with_key(headers):
    return {**headers, "Idempotency-Key": str(uuid.uuid4())}


def start_setup(client, headers, set_as_default):
    return client.post(
        "/user-payment-methods/setup-intent",
        headers=with_key(headers),
        json={"set_as_default": set_as_default},
    )


def save_setup(client, headers, setup_intent_id, set_as_default):
    return client.post(
        "/user-payment-methods/sync",
        headers=with_key(headers),
        json={"setup_intent_id": setup_intent_id, "set_as_default": set_as_default},
    )


def add_card(client, headers, stripe, *, fingerprint, last4="4242"):
    """Run the page's add-card flow: start setup, enter a card, then save it."""
    is_first = not client.get("/user-payment-methods", headers=headers).json()
    setup = start_setup(client, headers, is_first)
    assert setup.status_code == 201, setup.text
    setup_intent_id = setup.json()["client_secret"].removesuffix("_secret")
    stripe.enter_card(setup_intent_id, fingerprint=fingerprint, last4=last4)
    saved = save_setup(client, headers, setup_intent_id, is_first)
    assert saved.status_code == 201, saved.text
    return uuid.UUID(saved.json()["id"])


def suspend(db, user):
    """Suspend the account the way an admin does, keeping its saved cards."""
    user.account_status = "suspended"
    db.commit()


def cards_by_id(db, user):
    db.expire_all()
    return {
        card.id: card
        for card in db.scalars(
            select(UserPaymentMethod).where(UserPaymentMethod.user_id == user.id)
        )
    }


def setup_operation_count(db, user):
    return db.scalar(
        select(func.count(PaymentMethodOperation.id)).where(
            PaymentMethodOperation.user_id == user.id,
            PaymentMethodOperation.operation_kind == "setup_create",
        )
    )


@pytest.mark.page("F13", 15)
def test_a_suspended_player_still_sees_their_saved_cards(db, client, firebase, stripe):
    me = player(db)
    headers = firebase.sign_in(me)
    first = add_card(client, headers, stripe, fingerprint="fp_first", last4="1111")
    second = add_card(client, headers, stripe, fingerprint="fp_second", last4="2222")
    suspend(db, me)

    response = client.get("/user-payment-methods", headers=firebase.sign_in(me))

    assert response.status_code == 200, response.text
    assert sorted(
        (card["id"], card["card_last4"], card["is_default"]) for card in response.json()
    ) == sorted([(str(first), "1111", True), (str(second), "2222", False)])


@pytest.mark.page("F13", 15)
def test_a_suspended_player_can_remove_a_card(db, client, firebase, stripe):
    me = player(db)
    headers = firebase.sign_in(me)
    kept = add_card(client, headers, stripe, fingerprint="fp_kept")
    removed = add_card(client, headers, stripe, fingerprint="fp_removed")
    suspend(db, me)

    response = client.delete(
        f"/user-payment-methods/{removed}", headers=with_key(firebase.sign_in(me))
    )

    assert response.status_code == 200, response.text
    cards = cards_by_id(db, me)
    assert cards[removed].method_status == "detached"
    assert cards[removed].stripe_payment_method_id in stripe.detached
    assert (cards[kept].method_status, cards[kept].is_default) == ("active", True)


@pytest.mark.page("F13", 15)
def test_a_suspended_players_removal_still_needs_a_recent_confirmation(
    db, client, firebase, stripe
):
    me = player(db)
    card = add_card(client, firebase.sign_in(me), stripe, fingerprint="fp_card")
    suspend(db, me)
    stale = firebase.sign_in(me, auth_time=int(time.time()) - 24 * 60 * 60)

    response = client.delete(f"/user-payment-methods/{card}", headers=with_key(stale))

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "AUTH.RECENT_AUTH_REQUIRED"
    assert cards_by_id(db, me)[card].method_status == "active"


@pytest.mark.page("F13", 15)
def test_a_suspended_player_cannot_start_adding_a_card(db, client, firebase, stripe):
    me = player(db)
    add_card(client, firebase.sign_in(me), stripe, fingerprint="fp_card")
    suspend(db, me)
    setups_before = len(stripe.setup_intents)
    operations_before = setup_operation_count(db, me)

    response = start_setup(client, firebase.sign_in(me), set_as_default=False)

    assert response.status_code == 403
    assert response.json()["detail"] == "Active account required."
    assert len(stripe.setup_intents) == setups_before
    assert setup_operation_count(db, me) == operations_before


@pytest.mark.page("F13", 15)
def test_a_suspended_player_cannot_save_a_card_set_up_before_suspension(
    db, client, firebase, stripe
):
    me = player(db)
    headers = firebase.sign_in(me)
    existing = add_card(client, headers, stripe, fingerprint="fp_existing")
    setup = start_setup(client, headers, set_as_default=False)
    setup_intent_id = setup.json()["client_secret"].removesuffix("_secret")
    stripe.enter_card(setup_intent_id, fingerprint="fp_new")
    suspend(db, me)

    response = save_setup(
        client, firebase.sign_in(me), setup_intent_id, set_as_default=False
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Active account required."
    assert list(cards_by_id(db, me)) == [existing]


@pytest.mark.page("F13", 15)
def test_a_suspended_player_cannot_change_the_default(db, client, firebase, stripe):
    me = player(db)
    headers = firebase.sign_in(me)
    first = add_card(client, headers, stripe, fingerprint="fp_first")
    second = add_card(client, headers, stripe, fingerprint="fp_second")
    suspend(db, me)
    db.refresh(me)
    stripe_default_before = stripe.customer_defaults[me.stripe_customer_id]

    response = client.patch(
        f"/user-payment-methods/{second}/default",
        headers=with_key(firebase.sign_in(me)),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Active account required."
    cards = cards_by_id(db, me)
    assert (cards[first].is_default, cards[second].is_default) == (True, False)
    assert stripe.customer_defaults[me.stripe_customer_id] == stripe_default_before


CARD_REQUESTS = {
    "list": lambda client, headers: client.get(
        "/user-payment-methods", headers=headers
    ),
    "start setup": lambda client, headers: start_setup(
        client, headers, set_as_default=True
    ),
    "save": lambda client, headers: save_setup(
        client, headers, "seti_test_unknown", set_as_default=True
    ),
    "make default": lambda client, headers: client.patch(
        f"/user-payment-methods/{uuid.uuid4()}/default", headers=with_key(headers)
    ),
    "remove": lambda client, headers: client.delete(
        f"/user-payment-methods/{uuid.uuid4()}", headers=with_key(headers)
    ),
}


@pytest.mark.page("F13", 11)
@pytest.mark.parametrize("account_status", ["pending_deletion", "deleted"])
@pytest.mark.parametrize("request_kind", list(CARD_REQUESTS))
def test_a_deleted_or_deleting_account_cannot_use_saved_cards(
    clock, db, client, firebase, stripe, account_status, request_kind
):
    deleted_at = clock.now if account_status == "deleted" else None
    me = player(db, account_status=account_status, deleted_at=deleted_at)

    response = CARD_REQUESTS[request_kind](client, firebase.sign_in(me))

    # Sign-in treats a deleted or deleting account as no longer existing.
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found."
    assert stripe.setup_intents == {}
    assert cards_by_id(db, me) == {}
