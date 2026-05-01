from fastapi.testclient import TestClient

from backend.tests.helpers import (
    create_booking,
    create_game,
    create_user,
    create_venue,
    create_waitlist_entry,
)


def test_waitlist_entries_create_get_list_and_update(client: TestClient):
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue)
    waitlist_entry = create_waitlist_entry(client, user["id"], game["id"])

    get_response = client.get(f"/waitlist-entries/{waitlist_entry['id']}")
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["id"] == waitlist_entry["id"]

    list_response = client.get(f"/waitlist-entries?game_id={game['id']}")
    assert list_response.status_code == 200, list_response.text
    assert any(item["id"] == waitlist_entry["id"] for item in list_response.json())

    patch_response = client.patch(
        f"/waitlist-entries/{waitlist_entry['id']}",
        json={"party_size": 2},
    )
    assert patch_response.status_code == 200, patch_response.text
    assert patch_response.json()["party_size"] == 2


def test_waitlist_entries_reject_duplicate_active_user_and_position(
    client: TestClient,
):
    first_user = create_user(client)
    second_user = create_user(client)
    venue = create_venue(client, first_user["id"])
    game = create_game(client, first_user["id"], venue)
    create_waitlist_entry(client, first_user["id"], game["id"], position=1)

    duplicate_user_response = client.post(
        "/waitlist-entries",
        json={
            "game_id": game["id"],
            "user_id": first_user["id"],
            "party_size": 1,
            "position": 2,
        },
    )
    assert duplicate_user_response.status_code == 409, duplicate_user_response.text
    assert "already has an active waitlist entry" in duplicate_user_response.text

    duplicate_position_response = client.post(
        "/waitlist-entries",
        json={
            "game_id": game["id"],
            "user_id": second_user["id"],
            "party_size": 1,
            "position": 1,
        },
    )
    assert duplicate_position_response.status_code == 409
    assert "already has an active waitlist entry at this position" in (
        duplicate_position_response.text
    )


def test_waitlist_entries_reject_accepted_without_booking(client: TestClient):
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue)

    response = client.post(
        "/waitlist-entries",
        json={
            "game_id": game["id"],
            "user_id": user["id"],
            "party_size": 1,
            "position": 1,
            "waitlist_status": "accepted",
        },
    )

    assert response.status_code == 400, response.text
    assert "promoted_booking_id" in response.text


def test_waitlist_entries_accept_promoted_booking(client: TestClient):
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue)
    booking = create_booking(client, user["id"], game["id"])

    response = client.post(
        "/waitlist-entries",
        json={
            "game_id": game["id"],
            "user_id": user["id"],
            "party_size": 1,
            "position": 1,
            "waitlist_status": "accepted",
            "promoted_booking_id": booking["id"],
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["waitlist_status"] == "accepted"
    assert response.json()["promoted_at"] is not None
