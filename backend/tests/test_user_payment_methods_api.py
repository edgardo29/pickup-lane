from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.database import SessionLocal
from backend.models import UserPaymentMethod
from backend.services.stripe_service import (
    StripeCustomerResult,
    StripePaymentMethodCardResult,
    StripeSetupIntentResult,
)
from backend.tests.helpers import (
    authenticate_as,
    create_user,
    create_user_payment_method,
)


def mock_stripe_customer_and_setup(monkeypatch):
    def fake_create_customer(**kwargs):
        return StripeCustomerResult(id="cus_saved_card_test")

    def fake_create_setup_intent(**kwargs):
        return StripeSetupIntentResult(
            id="seti_saved_card_test",
            client_secret="seti_saved_card_test_secret",
            status="requires_payment_method",
            customer_id=kwargs["customer_id"],
            payment_method_id=None,
        )

    monkeypatch.setattr(
        "backend.routes.user_payment_method_routes.create_customer",
        fake_create_customer,
    )
    monkeypatch.setattr(
        "backend.routes.user_payment_method_routes.create_setup_intent",
        fake_create_setup_intent,
    )


def mock_stripe_sync(
    monkeypatch,
    *,
    customer_id: str = "cus_saved_card_test",
    exp_month: int = 12,
    exp_year: int = 2030,
    fingerprint: str = "fp_saved_card_test",
    payment_method_id: str = "pm_saved_card_test",
):
    def fake_retrieve_setup_intent(setup_intent_id):
        return StripeSetupIntentResult(
            id=setup_intent_id,
            client_secret=None,
            status="succeeded",
            customer_id=customer_id,
            payment_method_id=payment_method_id,
        )

    def fake_retrieve_payment_method(stripe_payment_method_id):
        return StripePaymentMethodCardResult(
            id=stripe_payment_method_id,
            customer_id=customer_id,
            card_fingerprint=fingerprint,
            card_brand="visa",
            card_last4="4242",
            exp_month=exp_month,
            exp_year=exp_year,
        )

    monkeypatch.setattr(
        "backend.routes.user_payment_method_routes.retrieve_setup_intent",
        fake_retrieve_setup_intent,
    )
    monkeypatch.setattr(
        "backend.routes.user_payment_method_routes.retrieve_payment_method",
        fake_retrieve_payment_method,
    )
    monkeypatch.setattr(
        "backend.routes.user_payment_method_routes.set_customer_default_payment_method",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        "backend.routes.user_payment_method_routes.detach_payment_method",
        lambda stripe_payment_method_id: None,
    )


def set_user_stripe_customer_id(user_id: str, stripe_customer_id: str) -> None:
    from backend.models import User

    with SessionLocal() as db:
        db_user = db.get(User, UUID(user_id))
        assert db_user is not None
        db_user.stripe_customer_id = stripe_customer_id
        db.commit()


def test_payment_method_setup_intent_stores_customer_on_user(
    client: TestClient,
    monkeypatch,
):
    from backend.models import User

    user = create_user(client)
    mock_stripe_customer_and_setup(monkeypatch)
    authenticate_as(user["id"])

    response = client.post("/user-payment-methods/setup-intent", json={})

    assert response.status_code == 201, response.text
    assert response.json()["client_secret"] == "seti_saved_card_test_secret"
    with SessionLocal() as db:
        db_user = db.get(User, UUID(user["id"]))
        assert db_user is not None
        assert db_user.stripe_customer_id == "cus_saved_card_test"


def test_payment_method_setup_intent_reuses_existing_customer(
    client: TestClient,
    monkeypatch,
):
    user = create_user(client)
    set_user_stripe_customer_id(user["id"], "cus_existing_saved_card")
    captured_setup: dict[str, object] = {}

    def fake_create_customer(**kwargs):
        raise AssertionError("existing customer should be reused")

    def fake_create_setup_intent(**kwargs):
        captured_setup.update(kwargs)
        return StripeSetupIntentResult(
            id="seti_existing_saved_card",
            client_secret="seti_existing_saved_card_secret",
            status="requires_payment_method",
            customer_id=kwargs["customer_id"],
            payment_method_id=None,
        )

    monkeypatch.setattr(
        "backend.routes.user_payment_method_routes.create_customer",
        fake_create_customer,
    )
    monkeypatch.setattr(
        "backend.routes.user_payment_method_routes.create_setup_intent",
        fake_create_setup_intent,
    )
    authenticate_as(user["id"])

    response = client.post("/user-payment-methods/setup-intent", json={})

    assert response.status_code == 201, response.text
    assert response.json()["client_secret"] == "seti_existing_saved_card_secret"
    assert captured_setup["customer_id"] == "cus_existing_saved_card"


def test_payment_method_sync_stores_stripe_verified_card(client: TestClient, monkeypatch):
    user = create_user(client)
    set_user_stripe_customer_id(user["id"], "cus_saved_card_test")
    mock_stripe_sync(monkeypatch)
    authenticate_as(user["id"])

    response = client.post(
        "/user-payment-methods/sync",
        json={"setup_intent_id": "seti_saved_card_test"},
    )

    assert response.status_code == 201, response.text
    payment_method = response.json()
    assert payment_method["card_brand"] == "visa"
    assert payment_method["card_last4"] == "4242"
    assert payment_method["is_default"] is True
    assert "card_fingerprint" not in payment_method
    assert "stripe_payment_method_id" not in payment_method

    list_response = client.get("/user-payment-methods")
    assert list_response.status_code == 200, list_response.text
    assert [item["id"] for item in list_response.json()] == [payment_method["id"]]


def test_payment_method_sync_rejects_setup_intent_for_other_customer(
    client: TestClient,
    monkeypatch,
):
    user = create_user(client)
    set_user_stripe_customer_id(user["id"], "cus_saved_card_test")
    mock_stripe_sync(monkeypatch, customer_id="cus_other_customer")
    authenticate_as(user["id"])

    response = client.post(
        "/user-payment-methods/sync",
        json={"setup_intent_id": "seti_saved_card_test"},
    )

    assert response.status_code == 403, response.text
    assert response.json()["detail"] == (
        "This setup intent does not belong to the current user."
    )


def test_payment_method_sync_rejects_incomplete_setup_intent(
    client: TestClient,
    monkeypatch,
):
    user = create_user(client)
    set_user_stripe_customer_id(user["id"], "cus_saved_card_test")

    def fake_retrieve_setup_intent(setup_intent_id):
        return StripeSetupIntentResult(
            id=setup_intent_id,
            client_secret=None,
            status="requires_payment_method",
            customer_id="cus_saved_card_test",
            payment_method_id=None,
        )

    monkeypatch.setattr(
        "backend.routes.user_payment_method_routes.retrieve_setup_intent",
        fake_retrieve_setup_intent,
    )
    authenticate_as(user["id"])

    response = client.post(
        "/user-payment-methods/sync",
        json={"setup_intent_id": "seti_saved_card_test"},
    )

    assert response.status_code == 409, response.text
    assert response.json()["detail"] == (
        "This setup intent has not completed with a payment method."
    )


def test_payment_methods_reject_client_created_fake_cards(client: TestClient):
    user = create_user(client)
    authenticate_as(user["id"])

    response = client.post(
        "/user-payment-methods",
        json={
            "stripe_payment_method_id": "pm_fake",
            "card_brand": "visa",
            "card_last4": "4242",
        },
    )

    assert response.status_code == 405, response.text


def test_payment_method_cannot_be_read_by_another_user(client: TestClient):
    owner = create_user(client)
    other_user = create_user(client)
    payment_method = create_user_payment_method(client, owner["id"])
    authenticate_as(other_user["id"])

    response = client.get(f"/user-payment-methods/{payment_method['id']}")

    assert response.status_code == 404, response.text


def test_payment_method_sync_adds_second_card_without_changing_default(
    client: TestClient,
    monkeypatch,
):
    user = create_user(client)
    first_payment_method = create_user_payment_method(
        client,
        user["id"],
        stripe_customer_id="cus_saved_card_test",
        stripe_payment_method_id="pm_first_default",
        card_fingerprint="fp_first_default",
    )
    mock_stripe_sync(
        monkeypatch,
        fingerprint="fp_second_card",
        payment_method_id="pm_second_card",
    )
    authenticate_as(user["id"])

    response = client.post(
        "/user-payment-methods/sync",
        json={"setup_intent_id": "seti_saved_card_test", "set_as_default": False},
    )

    assert response.status_code == 201, response.text
    second_payment_method = response.json()
    assert second_payment_method["is_default"] is False
    with SessionLocal() as db:
        default_methods = db.scalars(
            select(UserPaymentMethod).where(
                UserPaymentMethod.user_id == UUID(user["id"]),
                UserPaymentMethod.is_default.is_(True),
            )
        ).all()
        assert len(default_methods) == 1
        assert str(default_methods[0].id) == first_payment_method["id"]

    list_response = client.get("/user-payment-methods")
    assert list_response.status_code == 200, list_response.text
    assert [item["id"] for item in list_response.json()] == [
        first_payment_method["id"],
        second_payment_method["id"],
    ]


def test_payment_method_sync_can_make_new_card_default(
    client: TestClient,
    monkeypatch,
):
    user = create_user(client)
    first_payment_method = create_user_payment_method(
        client,
        user["id"],
        stripe_customer_id="cus_saved_card_test",
        stripe_payment_method_id="pm_first_default",
        card_fingerprint="fp_first_default",
    )
    captured_default: dict[str, str] = {}
    mock_stripe_sync(
        monkeypatch,
        fingerprint="fp_second_default",
        payment_method_id="pm_second_default",
    )

    def fake_set_customer_default_payment_method(**kwargs):
        captured_default.update(kwargs)

    monkeypatch.setattr(
        "backend.routes.user_payment_method_routes.set_customer_default_payment_method",
        fake_set_customer_default_payment_method,
    )
    authenticate_as(user["id"])

    response = client.post(
        "/user-payment-methods/sync",
        json={"setup_intent_id": "seti_saved_card_test", "set_as_default": True},
    )

    assert response.status_code == 201, response.text
    second_payment_method = response.json()
    assert second_payment_method["is_default"] is True
    assert captured_default == {
        "customer_id": "cus_saved_card_test",
        "payment_method_id": "pm_second_default",
    }

    list_response = client.get("/user-payment-methods")
    assert list_response.status_code == 200, list_response.text
    listed_methods = list_response.json()
    assert [item["id"] for item in listed_methods] == [
        first_payment_method["id"],
        second_payment_method["id"],
    ]
    assert listed_methods[0]["is_default"] is False
    assert listed_methods[1]["is_default"] is True


def test_payment_method_default_change_keeps_added_order(
    client: TestClient,
    monkeypatch,
):
    user = create_user(client)
    first_payment_method = create_user_payment_method(
        client,
        user["id"],
        stripe_customer_id="cus_saved_card_test",
        stripe_payment_method_id="pm_first_default",
        card_fingerprint="fp_first_default",
        is_default=True,
    )
    second_payment_method = create_user_payment_method(
        client,
        user["id"],
        stripe_customer_id="cus_saved_card_test",
        stripe_payment_method_id="pm_second_card",
        card_fingerprint="fp_second_card",
        is_default=False,
    )
    monkeypatch.setattr(
        "backend.routes.user_payment_method_routes.set_customer_default_payment_method",
        lambda **kwargs: None,
    )
    authenticate_as(user["id"])

    response = client.patch(
        f"/user-payment-methods/{second_payment_method['id']}/default",
    )

    assert response.status_code == 200, response.text
    assert response.json()["is_default"] is True
    list_response = client.get("/user-payment-methods")
    assert list_response.status_code == 200, list_response.text
    listed_methods = list_response.json()
    assert [item["id"] for item in listed_methods] == [
        first_payment_method["id"],
        second_payment_method["id"],
    ]
    assert listed_methods[0]["is_default"] is False
    assert listed_methods[1]["is_default"] is True


def test_payment_method_sync_blocks_active_duplicate_card(
    client: TestClient,
    monkeypatch,
):
    user = create_user(client)
    create_user_payment_method(
        client,
        user["id"],
        stripe_customer_id="cus_saved_card_test",
        stripe_payment_method_id="pm_existing_card",
        card_fingerprint="fp_duplicate_card",
    )
    mock_stripe_sync(
        monkeypatch,
        fingerprint="fp_duplicate_card",
        payment_method_id="pm_new_duplicate_card",
    )
    authenticate_as(user["id"])

    response = client.post(
        "/user-payment-methods/sync",
        json={"setup_intent_id": "seti_saved_card_test"},
    )

    assert response.status_code == 409, response.text
    assert response.json()["detail"] == "This card is already saved."


def test_payment_method_sync_reactivates_detached_duplicate_card(
    client: TestClient,
    monkeypatch,
):
    user = create_user(client)
    detached_payment_method = create_user_payment_method(
        client,
        user["id"],
        stripe_customer_id="cus_saved_card_test",
        stripe_payment_method_id="pm_detached_card",
        card_fingerprint="fp_reactivated_card",
        method_status="detached",
        is_default=False,
        exp_month=8,
        exp_year=2028,
    )
    mock_stripe_sync(
        monkeypatch,
        exp_month=9,
        exp_year=2031,
        fingerprint="fp_reactivated_card",
        payment_method_id="pm_reactivated_card",
    )
    authenticate_as(user["id"])

    response = client.post(
        "/user-payment-methods/sync",
        json={"setup_intent_id": "seti_saved_card_test"},
    )

    assert response.status_code == 201, response.text
    payment_method = response.json()
    assert payment_method["id"] == detached_payment_method["id"]
    assert payment_method["method_status"] == "active"
    assert payment_method["exp_month"] == 9
    assert payment_method["exp_year"] == 2031
    assert payment_method["is_default"] is True
    with SessionLocal() as db:
        payment_methods = db.scalars(
            select(UserPaymentMethod).where(
                UserPaymentMethod.user_id == UUID(user["id"]),
            )
        ).all()
        assert len(payment_methods) == 1
        assert payment_methods[0].stripe_payment_method_id == "pm_reactivated_card"


def test_payment_method_sync_limits_active_cards(
    client: TestClient,
    monkeypatch,
):
    user = create_user(client)
    for index in range(5):
        create_user_payment_method(
            client,
            user["id"],
            stripe_customer_id="cus_saved_card_test",
            stripe_payment_method_id=f"pm_existing_{index}",
            card_fingerprint=f"fp_existing_{index}",
            is_default=index == 0,
        )
    mock_stripe_sync(
        monkeypatch,
        fingerprint="fp_sixth_card",
        payment_method_id="pm_sixth_card",
    )
    authenticate_as(user["id"])

    response = client.post(
        "/user-payment-methods/sync",
        json={"setup_intent_id": "seti_saved_card_test"},
    )

    assert response.status_code == 400, response.text
    assert response.json()["detail"] == "You can save up to 5 active cards."


def test_payment_method_sync_allows_same_fingerprint_for_different_users(
    client: TestClient,
    monkeypatch,
):
    owner = create_user(client)
    other_user = create_user(client)
    create_user_payment_method(
        client,
        owner["id"],
        stripe_customer_id="cus_owner_card",
        stripe_payment_method_id="pm_owner_card",
        card_fingerprint="fp_shared_card",
    )
    set_user_stripe_customer_id(other_user["id"], "cus_other_card")
    mock_stripe_sync(
        monkeypatch,
        customer_id="cus_other_card",
        fingerprint="fp_shared_card",
        payment_method_id="pm_other_card",
    )
    authenticate_as(other_user["id"])

    response = client.post(
        "/user-payment-methods/sync",
        json={"setup_intent_id": "seti_saved_card_test"},
    )

    assert response.status_code == 201, response.text
    assert response.json()["card_last4"] == "4242"


def test_payment_method_delete_detaches_and_hides_card(
    client: TestClient,
    monkeypatch,
):
    user = create_user(client)
    payment_method = create_user_payment_method(client, user["id"])
    detached_ids: list[str] = []

    def fake_detach_payment_method(stripe_payment_method_id):
        detached_ids.append(stripe_payment_method_id)

    monkeypatch.setattr(
        "backend.routes.user_payment_method_routes.detach_payment_method",
        fake_detach_payment_method,
    )
    monkeypatch.setattr(
        "backend.routes.user_payment_method_routes.clear_customer_default_payment_method",
        lambda **kwargs: None,
    )
    authenticate_as(user["id"])

    response = client.delete(f"/user-payment-methods/{payment_method['id']}")

    assert response.status_code == 200, response.text
    assert response.json()["method_status"] == "detached"
    assert response.json()["is_default"] is False
    assert detached_ids == [payment_method["stripe_payment_method_id"]]

    list_response = client.get("/user-payment-methods")
    assert list_response.status_code == 200, list_response.text
    assert list_response.json() == []


def test_payment_method_delete_promotes_oldest_remaining_card(
    client: TestClient,
    monkeypatch,
):
    user = create_user(client)
    first_payment_method = create_user_payment_method(
        client,
        user["id"],
        stripe_customer_id="cus_saved_card_test",
        stripe_payment_method_id="pm_first_default",
        card_fingerprint="fp_first_default",
        is_default=True,
    )
    second_payment_method = create_user_payment_method(
        client,
        user["id"],
        stripe_customer_id="cus_saved_card_test",
        stripe_payment_method_id="pm_second_card",
        card_fingerprint="fp_second_card",
        is_default=False,
    )
    captured_default: dict[str, str] = {}

    monkeypatch.setattr(
        "backend.routes.user_payment_method_routes.detach_payment_method",
        lambda stripe_payment_method_id: None,
    )

    def fake_set_customer_default_payment_method(**kwargs):
        captured_default.update(kwargs)

    monkeypatch.setattr(
        "backend.routes.user_payment_method_routes.set_customer_default_payment_method",
        fake_set_customer_default_payment_method,
    )
    authenticate_as(user["id"])

    response = client.delete(f"/user-payment-methods/{first_payment_method['id']}")

    assert response.status_code == 200, response.text
    assert response.json()["method_status"] == "detached"
    assert response.json()["is_default"] is False
    assert captured_default == {
        "customer_id": "cus_saved_card_test",
        "payment_method_id": "pm_second_card",
    }

    list_response = client.get("/user-payment-methods")
    assert list_response.status_code == 200, list_response.text
    listed_methods = list_response.json()
    assert [item["id"] for item in listed_methods] == [second_payment_method["id"]]
    assert listed_methods[0]["is_default"] is True
