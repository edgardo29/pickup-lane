from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient


def unique_suffix() -> str:
    # Generate unique values for fields with database uniqueness constraints
    # such as email, phone, auth_user_id, and provider payment method IDs.
    return uuid4().hex


def create_user(client: TestClient, **overrides: object) -> dict:
    # Helpers create real rows through the API instead of inserting directly,
    # so setup data exercises the same validation as normal requests.
    suffix = unique_suffix()
    payload = {
        "auth_user_id": f"firebase-{suffix}",
        "email": f"user-{suffix}@example.com",
        "phone": f"+1555{suffix[:7]}",
        "first_name": "Test",
        "last_name": "User",
        "date_of_birth": "1995-01-01",
        "home_city": "Chicago",
        "home_state": "IL",
    }
    payload.update(overrides)

    response = client.post("/users", json=payload)

    assert response.status_code == 201, response.text
    return response.json()


def create_user_settings(client: TestClient, user_id: str, **overrides: object) -> dict:
    payload = {
        "user_id": user_id,
        "selected_city": "Chicago",
        "selected_state": "IL",
    }
    payload.update(overrides)

    response = client.post("/user-settings", json=payload)

    assert response.status_code == 201, response.text
    return response.json()


def create_user_payment_method(
    client: TestClient, user_id: str, **overrides: object
) -> dict:
    payload = {
        "user_id": user_id,
        "provider_payment_method_id": f"pm_{unique_suffix()}",
        "card_brand": "visa",
        "card_last4": "4242",
        "exp_month": 12,
        "exp_year": 2030,
        "is_default": True,
        "is_active": True,
    }
    payload.update(overrides)

    response = client.post("/user-payment-methods", json=payload)

    assert response.status_code == 201, response.text
    return response.json()


def create_venue(client: TestClient, user_id: str, **overrides: object) -> dict:
    payload = {
        "name": "CI Test Field",
        "address_line_1": "123 Test Ave",
        "city": "Chicago",
        "state": "IL",
        "postal_code": "60601",
        "country_code": "US",
        "venue_status": "approved",
        "created_by_user_id": user_id,
        "approved_by_user_id": user_id,
        "is_active": True,
    }
    payload.update(overrides)

    response = client.post("/venues", json=payload)

    assert response.status_code == 201, response.text
    return response.json()


def create_game(
    client: TestClient, user_id: str, venue: dict, **overrides: object
) -> dict:
    starts_at = datetime.now(UTC) + timedelta(days=7)
    ends_at = starts_at + timedelta(hours=1)
    payload = {
        "game_type": "official",
        "publish_status": "published",
        "game_status": "scheduled",
        "title": "CI Test Match",
        "venue_id": venue["id"],
        "venue_name_snapshot": venue["name"],
        "address_snapshot": venue["address_line_1"],
        "city_snapshot": venue["city"],
        "state_snapshot": venue["state"],
        "created_by_user_id": user_id,
        "starts_at": starts_at.isoformat(),
        "ends_at": ends_at.isoformat(),
        "timezone": "America/Chicago",
        "sport_type": "soccer",
        "format_label": "5v5",
        "environment_type": "indoor",
        "total_spots": 10,
        "price_per_player_cents": 1200,
        "currency": "USD",
        "allow_guests": True,
        "max_guests_per_booking": 2,
        "waitlist_enabled": True,
        "is_chat_enabled": True,
        "policy_mode": "official_standard",
    }
    payload.update(overrides)

    response = client.post("/games", json=payload)

    assert response.status_code == 201, response.text
    return response.json()


def create_booking(client: TestClient, user_id: str, game_id: str) -> dict:
    response = client.post(
        "/bookings",
        json={
            "game_id": game_id,
            "buyer_user_id": user_id,
            "booking_status": "confirmed",
            "payment_status": "paid",
            "participant_count": 1,
            "subtotal_cents": 1200,
            "platform_fee_cents": 100,
            "discount_cents": 0,
            "total_cents": 1300,
            "currency": "USD",
            "price_per_player_snapshot_cents": 1200,
            "platform_fee_snapshot_cents": 100,
        },
    )

    assert response.status_code == 201, response.text
    return response.json()


def create_game_participant(
    client: TestClient,
    user_id: str,
    game_id: str,
    booking_id: str | None = None,
    **overrides: object,
) -> dict:
    payload = {
        "game_id": game_id,
        "booking_id": booking_id,
        "participant_type": "registered_user",
        "user_id": user_id,
        "display_name_snapshot": "Test User",
        "participant_status": "confirmed",
        "attendance_status": "unknown",
        "cancellation_type": "none",
        "price_cents": 1200,
        "currency": "USD",
        "roster_order": 1,
    }
    payload.update(overrides)

    response = client.post("/game-participants", json=payload)

    assert response.status_code == 201, response.text
    return response.json()


def create_waitlist_entry(
    client: TestClient, user_id: str, game_id: str, **overrides: object
) -> dict:
    payload = {
        "game_id": game_id,
        "user_id": user_id,
        "party_size": 1,
        "position": 1,
    }
    payload.update(overrides)

    response = client.post("/waitlist-entries", json=payload)

    assert response.status_code == 201, response.text
    return response.json()


def create_payment(
    client: TestClient,
    payer_user_id: str,
    booking_id: str | None = None,
    game_id: str | None = None,
    **overrides: object,
) -> dict:
    # Payment helper keeps Stripe-like identifiers unique so repeated tests
    # do not trip database uniqueness constraints.
    suffix = unique_suffix()
    payload = {
        "payer_user_id": payer_user_id,
        "booking_id": booking_id,
        "game_id": game_id,
        "payment_type": "booking",
        "provider": "stripe",
        "provider_payment_intent_id": f"pi_{suffix}",
        "provider_charge_id": None,
        "idempotency_key": f"payment-{suffix}",
        "amount_cents": 1300,
        "currency": "USD",
        "payment_status": "processing",
        "failure_reason": None,
        "metadata": {"source": "ci"},
    }
    payload.update(overrides)

    response = client.post("/payments", json=payload)

    assert response.status_code == 201, response.text
    return response.json()


def create_refund(
    client: TestClient,
    payment_id: str,
    booking_id: str | None = None,
    participant_id: str | None = None,
    **overrides: object,
) -> dict:
    payload = {
        "payment_id": payment_id,
        "booking_id": booking_id,
        "participant_id": participant_id,
        "provider_refund_id": f"re_{unique_suffix()}",
        "amount_cents": 500,
        "currency": "USD",
        "refund_reason": "player_cancelled",
        "refund_status": "pending",
    }
    payload.update(overrides)

    response = client.post("/refunds", json=payload)

    assert response.status_code == 201, response.text
    return response.json()
