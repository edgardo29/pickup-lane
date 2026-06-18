from fastapi.testclient import TestClient

from backend.tests.helpers import (
    authenticate_as,
    create_booking,
    create_game,
    create_user,
    create_venue,
    get_money_as_admin,
    set_user_role,
)


def test_bookings_create_get_list_and_update(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue)
    booking = create_booking(client, user["id"], game["id"])

    authenticate_as(user["id"])
    get_response = client.get(f"/bookings/{booking['id']}")
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["id"] == booking["id"]

    list_response = get_money_as_admin(client, f"/bookings?game_id={game['id']}")
    assert list_response.status_code == 200, list_response.text
    assert any(item["id"] == booking["id"] for item in list_response.json())

    authenticate_as(admin["id"])
    patch_response = client.patch(
        f"/bookings/{booking['id']}",
        json={"payment_status": "paid"},
    )
    assert patch_response.status_code == 200, patch_response.text
    assert patch_response.json()["payment_status"] == "paid"


def test_booking_single_read_rejects_non_owner_and_allows_admin(
    client: TestClient,
):
    admin = create_user(client)
    owner = create_user(client)
    other_user = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, owner["id"])
    game = create_game(client, owner["id"], venue)
    booking = create_booking(client, owner["id"], game["id"])

    authenticate_as(other_user["id"])
    other_response = client.get(f"/bookings/{booking['id']}")
    assert other_response.status_code == 403, other_response.text

    authenticate_as(admin["id"])
    admin_response = client.get(f"/bookings/{booking['id']}")
    assert admin_response.status_code == 200, admin_response.text
    assert admin_response.json()["id"] == booking["id"]


def test_bookings_list_scopes_to_current_user_and_allows_admin(
    client: TestClient,
):
    admin = create_user(client)
    user = create_user(client)
    other_user = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue)
    user_booking = create_booking(client, user["id"], game["id"])
    other_booking = create_booking(client, other_user["id"], game["id"])

    authenticate_as(user["id"])
    user_response = client.get(f"/bookings?game_id={game['id']}")
    assert user_response.status_code == 200, user_response.text
    assert [booking["id"] for booking in user_response.json()] == [
        user_booking["id"]
    ]

    other_filter_response = client.get(f"/bookings?buyer_user_id={other_user['id']}")
    assert other_filter_response.status_code == 403, other_filter_response.text

    authenticate_as(admin["id"])
    admin_response = client.get(f"/bookings?game_id={game['id']}")
    assert admin_response.status_code == 200, admin_response.text
    booking_ids = {booking["id"] for booking in admin_response.json()}
    assert {user_booking["id"], other_booking["id"]} <= booking_ids


def test_my_bookings_requires_authentication(client: TestClient):
    response = client.get("/bookings/me")

    assert response.status_code == 401, response.text


def test_my_bookings_returns_current_user_bookings_only(client: TestClient):
    user = create_user(client)
    other_user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue)
    my_booking = create_booking(client, user["id"], game["id"])
    other_booking = create_booking(client, other_user["id"], game["id"])
    authenticate_as(user["id"])

    response = client.get("/bookings/me")

    assert response.status_code == 200, response.text
    booking_ids = {booking["id"] for booking in response.json()}
    assert my_booking["id"] in booking_ids
    assert other_booking["id"] not in booking_ids
    assert all(booking["buyer_user_id"] == user["id"] for booking in response.json())


def test_booking_scaffold_mutations_reject_non_admin(client: TestClient):
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue)
    authenticate_as(user["id"])

    create_response = client.post(
        "/bookings",
        json={
            "game_id": game["id"],
            "buyer_user_id": user["id"],
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
    assert create_response.status_code == 403, create_response.text

    update_response = client.patch(
        "/bookings/00000000-0000-0000-0000-000000000000",
        json={"payment_status": "paid"},
    )
    assert update_response.status_code == 403, update_response.text


def test_bookings_reject_bad_total_math(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue)
    authenticate_as(admin["id"])

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
