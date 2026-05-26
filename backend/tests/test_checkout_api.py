from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.database import SessionLocal
from backend.models import Booking, GameParticipant, Payment
from backend.services.stripe_service import StripePaymentIntentResult
from backend.tests.helpers import (
    authenticate_as,
    create_game,
    create_game_participant,
    create_user,
    create_user_payment_method,
    create_venue,
    mock_checkout_payment_method_verification,
)


def test_checkout_payment_intent_requires_saved_payment_method(client: TestClient):
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue, price_per_player_cents=1500)
    authenticate_as(user["id"])

    response = client.post(
        f"/checkout/games/{game['id']}/payment-intent",
        json={"guest_count": 1},
    )

    assert response.status_code == 400, response.text
    assert response.json()["detail"] == "Choose a saved card before checkout."


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


def test_checkout_payment_intent_rejects_other_user_payment_method(
    client: TestClient,
):
    host_user = create_user(client)
    buyer_user = create_user(client)
    venue = create_venue(client, host_user["id"])
    game = create_game(client, host_user["id"], venue, price_per_player_cents=1500)
    payment_method = create_user_payment_method(client, host_user["id"])
    authenticate_as(buyer_user["id"])

    response = client.post(
        f"/checkout/games/{game['id']}/payment-intent",
        json={"guest_count": 0, "payment_method_id": payment_method["id"]},
    )

    assert response.status_code == 404, response.text
    assert response.json()["detail"] == "Payment method not found."


def test_checkout_payment_intent_rejects_detached_payment_method(
    client: TestClient,
):
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue, price_per_player_cents=1500)
    payment_method = create_user_payment_method(
        client,
        user["id"],
        method_status="detached",
        is_default=False,
    )
    authenticate_as(user["id"])

    response = client.post(
        f"/checkout/games/{game['id']}/payment-intent",
        json={"guest_count": 0, "payment_method_id": payment_method["id"]},
    )

    assert response.status_code == 400, response.text
    assert response.json()["detail"] == "Only active payment methods can be used for checkout."


def test_checkout_payment_intent_rejects_expired_payment_method(
    client: TestClient,
):
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue, price_per_player_cents=1500)
    payment_method = create_user_payment_method(
        client,
        user["id"],
        exp_month=1,
        exp_year=2024,
    )
    authenticate_as(user["id"])

    response = client.post(
        f"/checkout/games/{game['id']}/payment-intent",
        json={"guest_count": 0, "payment_method_id": payment_method["id"]},
    )

    assert response.status_code == 400, response.text
    assert response.json()["detail"] == "This saved card is expired. Choose another card."


def test_checkout_payment_intent_rejects_stale_stripe_payment_method(
    client: TestClient,
    monkeypatch,
):
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue, price_per_player_cents=1500)
    payment_method = create_user_payment_method(client, user["id"])

    def fake_retrieve_payment_method(stripe_payment_method_id):
        raise RuntimeError("No such payment_method")

    monkeypatch.setattr(
        "backend.routes.checkout_routes.retrieve_payment_method",
        fake_retrieve_payment_method,
    )
    authenticate_as(user["id"])

    response = client.post(
        f"/checkout/games/{game['id']}/payment-intent",
        json={"guest_count": 0, "payment_method_id": payment_method["id"]},
    )

    assert response.status_code == 409, response.text
    assert response.json()["detail"] == (
        "This saved card could not be verified. Choose another card."
    )


def test_checkout_payment_intent_rejects_stripe_customer_mismatch(
    client: TestClient,
    monkeypatch,
):
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue, price_per_player_cents=1500)
    payment_method = create_user_payment_method(
        client,
        user["id"],
        stripe_customer_id="cus_checkout_saved_card",
        stripe_payment_method_id="pm_checkout_saved_card",
    )
    mock_checkout_payment_method_verification(
        monkeypatch,
        payment_method,
        customer_id="cus_other_customer",
    )
    authenticate_as(user["id"])

    response = client.post(
        f"/checkout/games/{game['id']}/payment-intent",
        json={"guest_count": 0, "payment_method_id": payment_method["id"]},
    )

    assert response.status_code == 409, response.text
    assert response.json()["detail"] == (
        "This saved card is no longer linked to your Stripe customer."
    )


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
    mock_checkout_payment_method_verification(monkeypatch, payment_method)
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

    booking_response = client.get(f"/bookings/{body['booking_id']}")
    assert booking_response.status_code == 200, booking_response.text
    booking = booking_response.json()
    assert booking["booking_status"] == "pending_payment"
    assert booking["payment_status"] == "processing"
    assert booking["participant_count"] == 1
    assert booking["total_cents"] == 1800

    payment_response = client.get(f"/payments/{body['payment_id']}")
    assert payment_response.status_code == 200, payment_response.text
    payment = payment_response.json()
    assert payment["booking_id"] == body["booking_id"]
    assert payment["payment_status"] == "processing"
    assert payment["provider_payment_intent_id"] == "pi_checkout_saved_card"


def test_checkout_payment_intent_rejects_frontend_amount(
    client: TestClient,
    monkeypatch,
):
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue, price_per_player_cents=1800)
    payment_method = create_user_payment_method(client, user["id"])
    mock_checkout_payment_method_verification(monkeypatch, payment_method)
    authenticate_as(user["id"])

    response = client.post(
        f"/checkout/games/{game['id']}/payment-intent",
        json={
            "guest_count": 0,
            "payment_method_id": payment_method["id"],
            "amount_cents": 1,
        },
    )

    assert response.status_code == 422, response.text
    assert any(
        error["loc"] == ["body", "amount_cents"]
        and error["type"] == "extra_forbidden"
        for error in response.json()["detail"]
    )


def test_checkout_payment_intent_recalculates_guest_total_server_side(
    client: TestClient,
    monkeypatch,
):
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(
        client,
        user["id"],
        venue,
        price_per_player_cents=1500,
        allow_guests=True,
        max_guests_per_booking=1,
    )
    payment_method = create_user_payment_method(
        client,
        user["id"],
        stripe_customer_id="cus_checkout_guest_total",
        stripe_payment_method_id="pm_checkout_guest_total",
    )
    mock_checkout_payment_method_verification(monkeypatch, payment_method)
    captured_create: dict[str, object] = {}

    def fake_create_payment_intent(**kwargs):
        captured_create.update(kwargs)
        return StripePaymentIntentResult(
            id="pi_checkout_guest_total",
            client_secret="pi_checkout_guest_total_secret",
            status="requires_payment_method",
        )

    def fake_confirm_payment_intent(payment_intent_id, **kwargs):
        return StripePaymentIntentResult(
            id=payment_intent_id,
            client_secret="pi_checkout_guest_total_secret",
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
        json={"guest_count": 1, "payment_method_id": payment_method["id"]},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["amount_cents"] == 3000
    assert captured_create["amount_cents"] == 3000

    booking_response = client.get(f"/bookings/{body['booking_id']}")
    assert booking_response.status_code == 200, booking_response.text
    booking = booking_response.json()
    assert booking["participant_count"] == 2
    assert booking["total_cents"] == 3000

    with SessionLocal() as db:
        participants = db.scalars(
            select(GameParticipant).where(
                GameParticipant.booking_id == UUID(body["booking_id"])
            )
        ).all()

    assert len(participants) == 2
    assert {participant.price_cents for participant in participants} == {1500}


def test_checkout_payment_intent_rejects_when_not_enough_spots_before_stripe(
    client: TestClient,
    monkeypatch,
):
    host_user = create_user(client)
    existing_players = [create_user(client) for _ in range(9)]
    buyer_user = create_user(client)
    venue = create_venue(client, host_user["id"])
    game = create_game(
        client,
        host_user["id"],
        venue,
        total_spots=10,
        price_per_player_cents=1500,
        allow_guests=True,
        max_guests_per_booking=1,
    )
    for roster_order, existing_player in enumerate(existing_players, start=1):
        create_game_participant(
            client,
            existing_player["id"],
            game["id"],
            price_cents=1500,
            roster_order=roster_order,
        )
    payment_method = create_user_payment_method(client, buyer_user["id"])
    mock_checkout_payment_method_verification(monkeypatch, payment_method)

    def fail_create_payment_intent(**kwargs):
        raise AssertionError("Stripe should not be called when the game is full.")

    monkeypatch.setattr(
        "backend.routes.checkout_routes.create_payment_intent",
        fail_create_payment_intent,
    )
    authenticate_as(buyer_user["id"])

    response = client.post(
        f"/checkout/games/{game['id']}/payment-intent",
        json={"guest_count": 1, "payment_method_id": payment_method["id"]},
    )

    assert response.status_code == 400, response.text
    assert response.json()["detail"] == "Not enough spots are available for checkout."

    with SessionLocal() as db:
        buyer_bookings = db.scalars(
            select(Booking).where(
                Booking.game_id == UUID(game["id"]),
                Booking.buyer_user_id == UUID(buyer_user["id"]),
            )
        ).all()
        buyer_payments = db.scalars(
            select(Payment).where(Payment.payer_user_id == UUID(buyer_user["id"]))
        ).all()

    assert buyer_bookings == []
    assert buyer_payments == []


def test_checkout_payment_intent_reuses_pending_checkout_without_reconfirming(
    client: TestClient,
    monkeypatch,
):
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue, price_per_player_cents=1800)
    payment_method = create_user_payment_method(
        client,
        user["id"],
        stripe_customer_id="cus_checkout_retry",
        stripe_payment_method_id="pm_checkout_retry",
    )
    mock_checkout_payment_method_verification(monkeypatch, payment_method)
    create_calls: list[dict[str, object]] = []
    confirm_calls: list[dict[str, object]] = []
    retrieve_calls: list[str] = []

    def fake_create_payment_intent(**kwargs):
        create_calls.append(kwargs)
        return StripePaymentIntentResult(
            id="pi_checkout_retry",
            client_secret="pi_checkout_retry_secret",
            status="requires_payment_method",
        )

    def fake_confirm_payment_intent(payment_intent_id, **kwargs):
        confirm_calls.append({"payment_intent_id": payment_intent_id, **kwargs})
        return StripePaymentIntentResult(
            id=payment_intent_id,
            client_secret="pi_checkout_retry_secret",
            status="processing",
        )

    def fake_retrieve_payment_intent(payment_intent_id):
        retrieve_calls.append(payment_intent_id)
        return StripePaymentIntentResult(
            id=payment_intent_id,
            client_secret="pi_checkout_retry_secret",
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
    monkeypatch.setattr(
        "backend.routes.checkout_routes.retrieve_payment_intent",
        fake_retrieve_payment_intent,
    )
    authenticate_as(user["id"])
    payload = {
        "guest_count": 0,
        "payment_method_id": payment_method["id"],
    }

    first_response = client.post(
        f"/checkout/games/{game['id']}/payment-intent",
        json=payload,
    )
    second_response = client.post(
        f"/checkout/games/{game['id']}/payment-intent",
        json=payload,
    )

    assert first_response.status_code == 201, first_response.text
    assert second_response.status_code == 201, second_response.text
    first_body = first_response.json()
    second_body = second_response.json()
    assert second_body["booking_id"] == first_body["booking_id"]
    assert second_body["payment_id"] == first_body["payment_id"]
    assert second_body["stripe_status"] == "processing"
    assert len(create_calls) == 1
    assert len(confirm_calls) == 1
    assert retrieve_calls == ["pi_checkout_retry"]

    with SessionLocal() as db:
        bookings = db.scalars(
            select(Booking).where(
                Booking.game_id == UUID(game["id"]),
                Booking.buyer_user_id == UUID(user["id"]),
            )
        ).all()
        payments = db.scalars(
            select(Payment).where(
                Payment.payer_user_id == UUID(user["id"]),
                Payment.provider_payment_intent_id == "pi_checkout_retry",
            )
        ).all()

    assert len(bookings) == 1
    assert len(payments) == 1
