"""F13 listing saved cards and saving new ones."""

import uuid
from datetime import date

import pytest
from sqlalchemy import func, select

from backend.models import PaymentMethodOperation, UserPaymentMethod
from backend.tests.factories import make_user


def player(db, **overrides):
    return make_user(db, date_of_birth=date(1990, 1, 1), **overrides)


def start_setup(client, headers, set_as_default=False):
    return client.post(
        "/user-payment-methods/setup-intent",
        headers={**headers, "Idempotency-Key": str(uuid.uuid4())},
        json={"set_as_default": set_as_default},
    )


def save_setup(client, headers, setup_intent_id, set_as_default=False):
    return client.post(
        "/user-payment-methods/sync",
        headers={**headers, "Idempotency-Key": str(uuid.uuid4())},
        json={"setup_intent_id": setup_intent_id, "set_as_default": set_as_default},
    )


def add_card(client, headers, stripe, *, fingerprint, last4="4242"):
    """Run the page's add-card flow: start setup, enter a card, then save it."""
    has_cards = bool(list_cards(client, headers))
    setup = start_setup(client, headers, set_as_default=not has_cards)
    assert setup.status_code == 201, setup.text
    setup_intent_id = setup.json()["client_secret"].removesuffix("_secret")
    stripe.enter_card(setup_intent_id, fingerprint=fingerprint, last4=last4)
    return save_setup(client, headers, setup_intent_id, set_as_default=not has_cards)


def list_cards(client, headers):
    response = client.get("/user-payment-methods", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def active_card_count(db, user):
    return db.scalar(
        select(func.count(UserPaymentMethod.id)).where(
            UserPaymentMethod.user_id == user.id,
            UserPaymentMethod.method_status == "active",
        )
    )


@pytest.mark.page("F13", 1)
def test_each_listed_card_includes_its_brand_last_four_expiry_and_default_flag(
    db, client, firebase, stripe
):
    me = player(db)
    headers = firebase.sign_in(me)
    add_card(client, headers, stripe, fingerprint="fp_card", last4="1111")

    (card,) = list_cards(client, headers)

    assert {
        key: card[key]
        for key in ("card_brand", "card_last4", "exp_month", "exp_year", "is_default")
    } == {
        "card_brand": "visa",
        "card_last4": "1111",
        "exp_month": 12,
        "exp_year": 2035,
        "is_default": True,
    }


@pytest.mark.page("F13", 2)
def test_the_first_saved_card_becomes_the_default(db, client, firebase, stripe):
    """The server makes the first card default even when not asked to."""
    me = player(db)
    headers = firebase.sign_in(me)
    setup = start_setup(client, headers, set_as_default=False)
    setup_intent_id = setup.json()["client_secret"].removesuffix("_secret")
    stripe.enter_card(setup_intent_id, fingerprint="fp_first")

    response = save_setup(client, headers, setup_intent_id, set_as_default=False)

    assert response.status_code == 201, response.text
    assert response.json()["is_default"] is True
    db.expire_all()
    stored = db.get(UserPaymentMethod, uuid.UUID(response.json()["id"]))
    assert stored.is_default is True
    assert stripe.customer_defaults[me.stripe_customer_id] == (
        stored.stripe_payment_method_id
    )


@pytest.mark.page("F13", 2)
def test_saving_another_card_does_not_replace_the_default(db, client, firebase, stripe):
    me = player(db)
    headers = firebase.sign_in(me)
    first = add_card(client, headers, stripe, fingerprint="fp_first").json()["id"]

    second = add_card(client, headers, stripe, fingerprint="fp_second")

    assert second.status_code == 201, second.text
    assert second.json()["is_default"] is False
    db.expire_all()
    first_card = db.get(UserPaymentMethod, uuid.UUID(first))
    second_card = db.get(UserPaymentMethod, uuid.UUID(second.json()["id"]))
    assert (first_card.is_default, second_card.is_default) == (True, False)
    assert stripe.customer_defaults[me.stripe_customer_id] == (
        first_card.stripe_payment_method_id
    )


@pytest.mark.page("F13", 1)
def test_a_player_sees_only_their_own_cards(db, client, firebase, stripe):
    me, other = player(db), player(db)
    add_card(client, firebase.sign_in(other), stripe, fingerprint="fp_other")
    add_card(client, firebase.sign_in(me), stripe, fingerprint="fp_mine")

    cards = list_cards(client, firebase.sign_in(me))

    assert [card["user_id"] for card in cards] == [str(me.id)]


SIGNED_OUT_REQUESTS = {
    "list": lambda client: client.get("/user-payment-methods"),
    "start setup": lambda client: start_setup(client, {}, set_as_default=True),
    "save": lambda client: save_setup(client, {}, "seti_test_unknown"),
    "make default": lambda client: client.patch(
        f"/user-payment-methods/{uuid.uuid4()}/default",
        headers={"Idempotency-Key": str(uuid.uuid4())},
    ),
    "remove": lambda client: client.delete(
        f"/user-payment-methods/{uuid.uuid4()}",
        headers={"Idempotency-Key": str(uuid.uuid4())},
    ),
}


@pytest.mark.page("F13", 11)
@pytest.mark.parametrize("request_kind", list(SIGNED_OUT_REQUESTS))
def test_signed_out_card_requests_are_refused(db, client, stripe, request_kind):
    response = SIGNED_OUT_REQUESTS[request_kind](client)

    assert response.status_code == 401
    assert stripe.setup_intents == {}
    assert db.scalar(select(func.count(UserPaymentMethod.id))) == 0


@pytest.mark.page("F13", 11)
def test_an_account_with_no_cards_gets_an_empty_list(db, client, firebase):
    assert list_cards(client, firebase.sign_in(player(db))) == []


def setup_operation_count(db, user):
    return db.scalar(
        select(func.count(PaymentMethodOperation.id)).where(
            PaymentMethodOperation.user_id == user.id,
            PaymentMethodOperation.operation_kind == "setup_create",
        )
    )


@pytest.mark.page("F13", 6)
def test_a_sixth_active_card_cannot_be_saved(db, client, firebase, stripe):
    """Two card setups started at four cards, as from two open tabs."""
    me = player(db)
    headers = firebase.sign_in(me)
    for index in range(4):
        saved = add_card(client, headers, stripe, fingerprint=f"fp_{index}")
        assert saved.status_code == 201, saved.text
    setup_ids = []
    for fingerprint in ("fp_fifth", "fp_sixth"):
        setup = start_setup(client, headers)
        assert setup.status_code == 201, setup.text
        setup_id = setup.json()["client_secret"].removesuffix("_secret")
        stripe.enter_card(setup_id, fingerprint=fingerprint)
        setup_ids.append(setup_id)
    fifth = save_setup(client, headers, setup_ids[0])
    assert fifth.status_code == 201, fifth.text

    sixth = save_setup(client, headers, setup_ids[1])

    assert sixth.status_code == 409
    assert sixth.json()["detail"] == "You can save up to 5 active cards."
    assert active_card_count(db, me) == 5
    assert stripe.setup_intents[setup_ids[1]].payment_method_id in stripe.detached


@pytest.mark.page("F13", 6)
def test_card_setup_cannot_start_at_five_active_cards(db, client, firebase, stripe):
    me = player(db)
    headers = firebase.sign_in(me)
    for index in range(5):
        saved = add_card(client, headers, stripe, fingerprint=f"fp_{index}")
        assert saved.status_code == 201, saved.text
    setups_before = len(stripe.setup_intents)
    operations_before = setup_operation_count(db, me)

    response = start_setup(client, headers)

    assert response.status_code == 409
    assert response.json()["detail"] == "You can save up to 5 active cards."
    assert len(stripe.setup_intents) == setups_before
    assert setup_operation_count(db, me) == operations_before
    assert active_card_count(db, me) == 5


@pytest.mark.page("F13", 13)
def test_saving_an_already_active_card_again_is_rejected(db, client, firebase, stripe):
    me = player(db)
    headers = firebase.sign_in(me)
    add_card(client, headers, stripe, fingerprint="fp_same", last4="1111")
    add_card(client, headers, stripe, fingerprint="fp_other", last4="2222")

    duplicate = add_card(client, headers, stripe, fingerprint="fp_same", last4="1111")

    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "This card is already saved."
    cards = list_cards(client, headers)
    assert sorted((card["card_last4"], card["is_default"]) for card in cards) == [
        ("1111", True),
        ("2222", False),
    ]


@pytest.mark.page("F13", 10)
def test_card_setup_is_refused_while_card_payments_are_off(
    db, client, firebase, stripe, monkeypatch
):
    """With the fake Stripe in place, only the payments-off rule can refuse."""
    from backend.services import payment_method_service

    monkeypatch.setattr(
        payment_method_service, "stripe_payments_enabled", lambda: False
    )
    me = player(db)

    response = start_setup(client, firebase.sign_in(me), set_as_default=True)

    assert response.status_code == 503
    assert (
        response.json()["detail"]
        == payment_method_service.STRIPE_PAYMENTS_DISABLED_DETAIL
    )
    assert active_card_count(db, me) == 0


@pytest.mark.page("F13", 8)
def test_a_failed_card_setup_start_reports_an_error_and_saves_nothing(
    db, client, firebase, stripe
):
    me = player(db)
    headers = firebase.sign_in(me)
    stripe.failing.add("create_setup_intent")

    response = start_setup(client, headers, set_as_default=True)

    assert response.status_code == 502
    assert response.json()["detail"] == "Stripe could not create this setup intent."
    assert active_card_count(db, me) == 0
    assert stripe.setup_intents == {}


@pytest.mark.page("F13", 8)
def test_a_failed_card_setup_start_can_be_retried(db, client, firebase, stripe):
    me = player(db)
    headers = firebase.sign_in(me)
    stripe.failing.add("create_setup_intent")
    failed = start_setup(client, headers, set_as_default=True)
    assert failed.status_code == 502, failed.text
    stripe.failing.clear()

    retry = start_setup(client, headers, set_as_default=True)

    assert retry.status_code == 201, retry.text
    assert len(stripe.setup_intents) == 1


@pytest.mark.page("F13", 8)
def test_a_failed_card_save_reports_an_error_and_saves_nothing(
    db, client, firebase, stripe
):
    me = player(db)
    headers = firebase.sign_in(me)
    setup = start_setup(client, headers, set_as_default=True)
    setup_intent_id = setup.json()["client_secret"].removesuffix("_secret")
    stripe.enter_card(setup_intent_id, fingerprint="fp_card")
    stripe.failing.add("retrieve_setup_intent")

    response = save_setup(client, headers, setup_intent_id, set_as_default=True)

    assert response.status_code == 502
    assert response.json()["detail"] == "Stripe could not retrieve this setup intent."
    assert active_card_count(db, me) == 0


@pytest.mark.page("F13", 8)
def test_a_failed_card_save_can_be_retried(db, client, firebase, stripe):
    me = player(db)
    headers = firebase.sign_in(me)
    setup = start_setup(client, headers, set_as_default=True)
    setup_intent_id = setup.json()["client_secret"].removesuffix("_secret")
    stripe.enter_card(setup_intent_id, fingerprint="fp_card")
    stripe.failing.add("retrieve_setup_intent")
    failed = save_setup(client, headers, setup_intent_id, set_as_default=True)
    assert failed.status_code == 502, failed.text
    stripe.failing.clear()

    retry = save_setup(client, headers, setup_intent_id, set_as_default=True)

    assert retry.status_code == 201, retry.text
    assert active_card_count(db, me) == 1


def remove_card(client, headers, card_id):
    response = client.delete(
        f"/user-payment-methods/{card_id}",
        headers={**headers, "Idempotency-Key": str(uuid.uuid4())},
    )
    assert response.status_code == 200, response.text


def cards_with_fingerprint(db, user, fingerprint):
    db.expire_all()
    return db.scalars(
        select(UserPaymentMethod).where(
            UserPaymentMethod.user_id == user.id,
            UserPaymentMethod.card_fingerprint == fingerprint,
        )
    ).all()


@pytest.mark.page("F13", 14)
def test_a_re_added_removed_card_returns_as_the_same_card(db, client, firebase, stripe):
    me = player(db)
    headers = firebase.sign_in(me)
    card_id = add_card(client, headers, stripe, fingerprint="fp_card").json()["id"]
    remove_card(client, headers, card_id)

    re_added = add_card(client, headers, stripe, fingerprint="fp_card")

    assert re_added.status_code == 201, re_added.text
    assert re_added.json()["id"] == card_id
    (stored,) = cards_with_fingerprint(db, me, "fp_card")
    assert stored.method_status == "active"


@pytest.mark.page("F13", 14)
def test_a_re_added_removed_card_counts_toward_the_five_card_limit(
    db, client, firebase, stripe
):
    me = player(db)
    headers = firebase.sign_in(me)
    card_id = add_card(client, headers, stripe, fingerprint="fp_card").json()["id"]
    remove_card(client, headers, card_id)
    for index in range(4):
        saved = add_card(client, headers, stripe, fingerprint=f"fp_{index}")
        assert saved.status_code == 201, saved.text
    re_added = add_card(client, headers, stripe, fingerprint="fp_card")
    assert re_added.status_code == 201, re_added.text

    sixth_setup = start_setup(client, headers)

    assert active_card_count(db, me) == 5
    assert sixth_setup.status_code == 409
    assert sixth_setup.json()["detail"] == "You can save up to 5 active cards."


@pytest.mark.page("F13", 14)
def test_a_re_added_card_becomes_default_when_it_is_the_only_active_card(
    db, client, firebase, stripe
):
    me = player(db)
    headers = firebase.sign_in(me)
    card_id = add_card(client, headers, stripe, fingerprint="fp_card").json()["id"]
    remove_card(client, headers, card_id)

    re_added = add_card(client, headers, stripe, fingerprint="fp_card")

    assert re_added.status_code == 201, re_added.text
    assert re_added.json()["is_default"] is True
    (stored,) = cards_with_fingerprint(db, me, "fp_card")
    assert stored.is_default is True


@pytest.mark.page("F13", 14)
def test_a_re_added_card_leaves_an_existing_default_unchanged(
    db, client, firebase, stripe
):
    me = player(db)
    headers = firebase.sign_in(me)
    kept_id = add_card(client, headers, stripe, fingerprint="fp_kept").json()["id"]
    card_id = add_card(client, headers, stripe, fingerprint="fp_card").json()["id"]
    remove_card(client, headers, card_id)

    re_added = add_card(client, headers, stripe, fingerprint="fp_card")

    assert re_added.status_code == 201, re_added.text
    assert re_added.json()["is_default"] is False
    cards = list_cards(client, headers)
    assert sorted((card["id"], card["is_default"]) for card in cards) == sorted(
        [(kept_id, True), (card_id, False)]
    )
