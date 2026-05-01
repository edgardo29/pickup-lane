from fastapi.testclient import TestClient

from backend.tests.helpers import (
    create_booking,
    create_game,
    create_payment,
    create_user,
    create_venue,
    unique_suffix,
)


def test_payments_create_get_list_and_update(client: TestClient):
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue)
    booking = create_booking(client, user["id"], game["id"])
    payment = create_payment(client, user["id"], booking_id=booking["id"])

    get_response = client.get(f"/payments/{payment['id']}")
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["id"] == payment["id"]
    assert get_response.json()["metadata"] == {"source": "ci"}

    list_response = client.get(f"/payments?booking_id={booking['id']}")
    assert list_response.status_code == 200, list_response.text
    assert any(item["id"] == payment["id"] for item in list_response.json())

    patch_response = client.patch(
        f"/payments/{payment['id']}",
        json={"payment_status": "succeeded", "provider_charge_id": "ch_test_123"},
    )
    assert patch_response.status_code == 200, patch_response.text
    assert patch_response.json()["payment_status"] == "succeeded"
    assert patch_response.json()["paid_at"] is not None


def test_payments_reject_booking_payer_mismatch(client: TestClient):
    buyer = create_user(client)
    other_user = create_user(client)
    venue = create_venue(client, buyer["id"])
    game = create_game(client, buyer["id"], venue)
    booking = create_booking(client, buyer["id"], game["id"])

    response = client.post(
        "/payments",
        json={
            "payer_user_id": other_user["id"],
            "booking_id": booking["id"],
            "payment_type": "booking",
            "provider": "stripe",
            "provider_payment_intent_id": f"pi_{unique_suffix()}",
            "idempotency_key": f"payment-{unique_suffix()}",
            "amount_cents": 1300,
            "currency": "USD",
            "payment_status": "processing",
        },
    )

    assert response.status_code == 400, response.text
    assert "booking buyer" in response.text


def test_payments_reject_duplicate_idempotency_key(client: TestClient):
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue)
    booking = create_booking(client, user["id"], game["id"])
    idempotency_key = f"payment-{unique_suffix()}"

    create_payment(
        client,
        user["id"],
        booking_id=booking["id"],
        idempotency_key=idempotency_key,
    )
    response = client.post(
        "/payments",
        json={
            "payer_user_id": user["id"],
            "booking_id": booking["id"],
            "payment_type": "booking",
            "provider": "stripe",
            "provider_payment_intent_id": f"pi_{unique_suffix()}",
            "idempotency_key": idempotency_key,
            "amount_cents": 1300,
            "currency": "USD",
            "payment_status": "processing",
        },
    )

    assert response.status_code == 409, response.text
    assert "idempotency_key already exists" in response.text


def test_payments_reject_failed_without_failure_reason(client: TestClient):
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue)
    booking = create_booking(client, user["id"], game["id"])

    response = client.post(
        "/payments",
        json={
            "payer_user_id": user["id"],
            "booking_id": booking["id"],
            "payment_type": "booking",
            "provider": "stripe",
            "provider_payment_intent_id": f"pi_{unique_suffix()}",
            "idempotency_key": f"payment-{unique_suffix()}",
            "amount_cents": 1300,
            "currency": "USD",
            "payment_status": "failed",
        },
    )

    assert response.status_code == 400, response.text
    assert "failure_reason" in response.text
