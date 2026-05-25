from fastapi.testclient import TestClient

from backend.services.stripe_service import StripePaymentIntentResult
from backend.tests.helpers import (
    authenticate_as,
    create_game,
    create_user,
    create_user_payment_method,
    create_venue,
)


def test_checkout_payment_intent_creates_pending_rows(
    client: TestClient, monkeypatch
):
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue, price_per_player_cents=1500)
    captured: dict[str, object] = {}

    def fake_create_payment_intent(**kwargs):
        captured.update(kwargs)
        return StripePaymentIntentResult(
            id="pi_checkout_test",
            client_secret="pi_checkout_test_secret",
            status="requires_payment_method",
        )

    monkeypatch.setattr(
        "backend.routes.checkout_routes.create_payment_intent",
        fake_create_payment_intent,
    )
    authenticate_as(user["id"])

    response = client.post(
        f"/checkout/games/{game['id']}/payment-intent",
        json={"guest_count": 1},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["client_secret"] == "pi_checkout_test_secret"
    assert body["amount_cents"] == 3000
    assert body["currency"] == "USD"
    assert captured["amount_cents"] == 3000
    assert captured["currency"] == "USD"
    assert captured["metadata"]["user_id"] == user["id"]
    assert captured["metadata"]["game_id"] == game["id"]
    assert captured["metadata"]["booking_id"] == body["booking_id"]
    assert captured["metadata"]["payment_id"] == body["payment_id"]

    booking_response = client.get(f"/bookings/{body['booking_id']}")
    assert booking_response.status_code == 200, booking_response.text
    booking = booking_response.json()
    assert booking["booking_status"] == "pending_payment"
    assert booking["payment_status"] == "processing"
    assert booking["participant_count"] == 2
    assert booking["total_cents"] == 3000

    payment_response = client.get(f"/payments/{body['payment_id']}")
    assert payment_response.status_code == 200, payment_response.text
    payment = payment_response.json()
    assert payment["booking_id"] == body["booking_id"]
    assert payment["payment_status"] == "requires_payment_method"
    assert payment["provider_payment_intent_id"] == "pi_checkout_test"

    participants_response = client.get(
        f"/game-participants?booking_id={body['booking_id']}"
    )
    assert participants_response.status_code == 200, participants_response.text
    participants = participants_response.json()
    assert len(participants) == 2
    assert {participant["participant_status"] for participant in participants} == {
        "pending_payment"
    }


def test_checkout_payment_intent_rejects_non_official_games(client: TestClient):
    host_user = create_user(client)
    buyer_user = create_user(client)
    venue = create_venue(client, host_user["id"])
    game = create_game(
        client,
        host_user["id"],
        venue,
        game_type="community",
        host_user_id=host_user["id"],
        payment_collection_type="external_host",
        policy_mode="custom_hosted",
    )
    authenticate_as(buyer_user["id"])

    response = client.post(
        f"/checkout/games/{game['id']}/payment-intent",
        json={"guest_count": 0},
    )

    assert response.status_code == 400, response.text
    assert "official in-app games" in response.text


def test_checkout_payment_intent_can_use_saved_payment_method(
    client: TestClient,
    monkeypatch,
):
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue, price_per_player_cents=1800)
    payment_method = create_user_payment_method(
        client,
        user["id"],
        stripe_customer_id="cus_checkout_saved_card",
        stripe_payment_method_id="pm_checkout_saved_card",
    )
    captured_create: dict[str, object] = {}
    captured_confirm: dict[str, object] = {}

    def fake_create_payment_intent(**kwargs):
        captured_create.update(kwargs)
        return StripePaymentIntentResult(
            id="pi_checkout_saved_card",
            client_secret="pi_checkout_saved_card_secret",
            status="requires_payment_method",
        )

    def fake_confirm_payment_intent(payment_intent_id, **kwargs):
        captured_confirm["payment_intent_id"] = payment_intent_id
        captured_confirm.update(kwargs)
        return StripePaymentIntentResult(
            id=payment_intent_id,
            client_secret="pi_checkout_saved_card_secret",
            status="processing",
        )

    monkeypatch.setattr(
        "backend.routes.checkout_routes.create_payment_intent",
        fake_create_payment_intent,
    )
    monkeypatch.setattr(
        "backend.routes.checkout_routes.confirm_payment_intent",
        fake_confirm_payment_intent,
    )
    authenticate_as(user["id"])

    response = client.post(
        f"/checkout/games/{game['id']}/payment-intent",
        json={
            "guest_count": 0,
            "payment_method_id": payment_method["id"],
            "return_url": f"http://localhost:5173/games/{game['id']}/checkout",
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["client_secret"] == "pi_checkout_saved_card_secret"
    assert body["stripe_status"] == "processing"
    assert captured_create["customer_id"] == "cus_checkout_saved_card"
    assert captured_confirm == {
        "payment_intent_id": "pi_checkout_saved_card",
        "payment_method_id": "pm_checkout_saved_card",
        "return_url": f"http://localhost:5173/games/{game['id']}/checkout",
    }
