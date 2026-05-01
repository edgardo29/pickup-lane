from fastapi.testclient import TestClient

from backend.tests.helpers import create_booking, create_game, create_user, create_venue


def test_bookings_create_get_list_and_update(client: TestClient):
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue)
    booking = create_booking(client, user["id"], game["id"])

    get_response = client.get(f"/bookings/{booking['id']}")
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["id"] == booking["id"]

    list_response = client.get(f"/bookings?game_id={game['id']}")
    assert list_response.status_code == 200, list_response.text
    assert any(item["id"] == booking["id"] for item in list_response.json())

    patch_response = client.patch(
        f"/bookings/{booking['id']}",
        json={"payment_status": "paid"},
    )
    assert patch_response.status_code == 200, patch_response.text
    assert patch_response.json()["payment_status"] == "paid"


def test_bookings_reject_bad_total_math(client: TestClient):
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue)

    response = client.post(
        "/bookings",
        json={
            "game_id": game["id"],
            "buyer_user_id": user["id"],
            "booking_status": "pending_payment",
            "payment_status": "unpaid",
            "participant_count": 1,
            "subtotal_cents": 1200,
            "platform_fee_cents": 100,
            "discount_cents": 0,
            "total_cents": 1200,
            "currency": "USD",
            "price_per_player_snapshot_cents": 1200,
            "platform_fee_snapshot_cents": 100,
        },
    )

    assert response.status_code == 400, response.text
    assert "total_cents must equal" in response.text
