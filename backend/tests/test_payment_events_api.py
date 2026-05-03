from fastapi.testclient import TestClient

from backend.tests.helpers import (
    create_booking,
    create_game,
    create_payment,
    create_payment_event,
    create_user,
    create_venue,
)


def create_payment_event_setup(client: TestClient) -> tuple[dict, dict, dict, dict]:
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue)
    booking = create_booking(client, user["id"], game["id"])
    payment = create_payment(
        client,
        user["id"],
        booking_id=booking["id"],
    )
    return user, game, booking, payment


def test_payment_event_create_get_list_and_mark_processed(client: TestClient):
    _user, _game, _booking, payment = create_payment_event_setup(client)
    payment_event = create_payment_event(
        client,
        payment_id=payment["id"],
        provider_event_id="evt_ci_payment_event_001",
    )

    get_response = client.get(f"/payment-events/{payment_event['id']}")
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["id"] == payment_event["id"]

    list_by_payment_response = client.get(
        f"/payment-events?payment_id={payment['id']}"
    )
    assert list_by_payment_response.status_code == 200, list_by_payment_response.text
    assert any(
        item["id"] == payment_event["id"] for item in list_by_payment_response.json()
    )

    list_by_status_response = client.get("/payment-events?processing_status=pending")
    assert list_by_status_response.status_code == 200, list_by_status_response.text
    assert any(
        item["id"] == payment_event["id"] for item in list_by_status_response.json()
    )

    patch_response = client.patch(
        f"/payment-events/{payment_event['id']}",
        json={"processing_status": "processed"},
    )
    assert patch_response.status_code == 200, patch_response.text
    assert patch_response.json()["processing_status"] == "processed"
    assert patch_response.json()["processed_at"] is not None
    assert patch_response.json()["processing_error"] is None


def test_payment_event_can_be_created_without_payment_match(client: TestClient):
    payment_event = create_payment_event(
        client,
        payment_id=None,
        provider_event_id="evt_ci_unmatched_payment_event",
    )

    assert payment_event["payment_id"] is None
    assert payment_event["provider_event_id"] == "evt_ci_unmatched_payment_event"


def test_payment_event_reject_duplicate_provider_event_id(client: TestClient):
    create_payment_event(client, provider_event_id="evt_ci_duplicate")

    response = client.post(
        "/payment-events",
        json={
            "payment_id": None,
            "provider": "stripe",
            "provider_event_id": "evt_ci_duplicate",
            "event_type": "payment_intent.succeeded",
            "raw_payload": {
                "id": "evt_ci_duplicate",
                "type": "payment_intent.succeeded",
            },
            "processing_status": "pending",
        },
    )

    assert response.status_code == 409, response.text
    assert "This provider event has already been recorded" in response.text


def test_payment_event_reject_invalid_processing_status(client: TestClient):
    response = client.post(
        "/payment-events",
        json={
            "payment_id": None,
            "provider": "stripe",
            "provider_event_id": "evt_ci_invalid_status",
            "event_type": "payment_intent.succeeded",
            "raw_payload": {
                "id": "evt_ci_invalid_status",
                "type": "payment_intent.succeeded",
            },
            "processing_status": "done",
        },
    )

    assert response.status_code == 400, response.text
    assert "processing_status" in response.text


def test_payment_event_reject_failed_without_processing_error(client: TestClient):
    response = client.post(
        "/payment-events",
        json={
            "payment_id": None,
            "provider": "stripe",
            "provider_event_id": "evt_ci_failed_without_error",
            "event_type": "payment_intent.payment_failed",
            "raw_payload": {
                "id": "evt_ci_failed_without_error",
                "type": "payment_intent.payment_failed",
            },
            "processing_status": "failed",
        },
    )

    assert response.status_code == 400, response.text
    assert "Failed payment events require processing_error" in response.text


def test_payment_event_reject_empty_event_type(client: TestClient):
    response = client.post(
        "/payment-events",
        json={
            "payment_id": None,
            "provider": "stripe",
            "provider_event_id": "evt_ci_empty_event_type",
            "event_type": "   ",
            "raw_payload": {
                "id": "evt_ci_empty_event_type",
            },
            "processing_status": "pending",
        },
    )

    assert response.status_code == 400, response.text
    assert "event_type must not be empty" in response.text


def test_payment_event_reject_immutable_provider_field_update(client: TestClient):
    payment_event = create_payment_event(
        client,
        provider_event_id="evt_ci_immutable_update",
    )

    response = client.patch(
        f"/payment-events/{payment_event['id']}",
        json={"provider_event_id": "evt_ci_changed"},
    )

    assert response.status_code == 400, response.text
    assert "Payment event provider fields cannot be changed" in response.text


def test_payment_event_reject_missing_payment_reference(client: TestClient):
    payment_event = create_payment_event(
        client,
        payment_id=None,
        provider_event_id="evt_ci_missing_payment_reference",
    )

    response = client.patch(
        f"/payment-events/{payment_event['id']}",
        json={"payment_id": "00000000-0000-4000-8000-000000000000"},
    )

    assert response.status_code == 404, response.text
    assert "Payment not found" in response.text