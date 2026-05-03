from fastapi.testclient import TestClient

from backend.tests.helpers import (
    create_booking,
    create_booking_status_history,
    create_game,
    create_user,
    create_venue,
)


def create_booking_status_history_setup(
    client: TestClient,
) -> tuple[dict, dict, dict, dict]:
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue)
    booking = create_booking(client, user["id"], game["id"])
    return user, venue, game, booking


def test_booking_status_history_create_get_list_and_update_reason(
    client: TestClient,
):
    user, _venue, _game, booking = create_booking_status_history_setup(client)
    history = create_booking_status_history(
        client,
        booking["id"],
        changed_by_user_id=user["id"],
    )

    get_response = client.get(f"/booking-status-history/{history['id']}")
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["id"] == history["id"]

    list_response = client.get(f"/booking-status-history?booking_id={booking['id']}")
    assert list_response.status_code == 200, list_response.text
    assert any(item["id"] == history["id"] for item in list_response.json())

    patch_response = client.patch(
        f"/booking-status-history/{history['id']}",
        json={"change_reason": "Corrected CI booking reason."},
    )
    assert patch_response.status_code == 200, patch_response.text
    assert patch_response.json()["change_reason"] == "Corrected CI booking reason."


def test_booking_status_history_reject_no_status_change(client: TestClient):
    user, _venue, _game, booking = create_booking_status_history_setup(client)

    response = client.post(
        "/booking-status-history",
        json={
            "booking_id": booking["id"],
            "old_booking_status": "confirmed",
            "new_booking_status": "confirmed",
            "old_payment_status": "paid",
            "new_payment_status": "paid",
            "changed_by_user_id": user["id"],
            "change_source": "admin",
            "change_reason": "No real change",
        },
    )

    assert response.status_code == 400, response.text
    assert "At least one booking or payment status must change" in response.text


def test_booking_status_history_reject_invalid_payment_status(client: TestClient):
    user, _venue, _game, booking = create_booking_status_history_setup(client)

    response = client.post(
        "/booking-status-history",
        json={
            "booking_id": booking["id"],
            "old_booking_status": "pending_payment",
            "new_booking_status": "confirmed",
            "old_payment_status": "processing",
            "new_payment_status": "settled",
            "changed_by_user_id": user["id"],
            "change_source": "payment_webhook",
        },
    )

    assert response.status_code == 400, response.text
    assert "new_payment_status" in response.text


def test_booking_status_history_reject_missing_actor(client: TestClient):
    _user, _venue, _game, booking = create_booking_status_history_setup(client)

    response = client.post(
        "/booking-status-history",
        json={
            "booking_id": booking["id"],
            "old_booking_status": "pending_payment",
            "new_booking_status": "confirmed",
            "old_payment_status": "processing",
            "new_payment_status": "paid",
            "changed_by_user_id": "00000000-0000-4000-8000-000000000000",
            "change_source": "admin",
        },
    )

    assert response.status_code == 404, response.text
    assert "Changed by user not found" in response.text


def test_booking_status_history_reject_lifecycle_field_update(client: TestClient):
    user, _venue, _game, booking = create_booking_status_history_setup(client)
    history = create_booking_status_history(
        client,
        booking["id"],
        changed_by_user_id=user["id"],
    )

    response = client.patch(
        f"/booking-status-history/{history['id']}",
        json={"new_booking_status": "cancelled"},
    )

    assert response.status_code == 400, response.text
    assert "cannot be changed" in response.text
