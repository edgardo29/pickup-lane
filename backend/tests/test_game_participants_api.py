from fastapi.testclient import TestClient

from backend.tests.helpers import (
    create_booking,
    create_game,
    create_game_participant,
    create_user,
    create_venue,
)


def test_game_participants_create_get_list_and_update(client: TestClient):
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue)
    booking = create_booking(client, user["id"], game["id"])
    participant = create_game_participant(
        client, user["id"], game["id"], booking["id"]
    )

    get_response = client.get(f"/game-participants/{participant['id']}")
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["id"] == participant["id"]

    list_response = client.get(f"/game-participants?game_id={game['id']}")
    assert list_response.status_code == 200, list_response.text
    assert any(item["id"] == participant["id"] for item in list_response.json())

    patch_response = client.patch(
        f"/game-participants/{participant['id']}",
        json={"attendance_status": "attended", "marked_attendance_by_user_id": user["id"]},
    )
    assert patch_response.status_code == 200, patch_response.text
    assert patch_response.json()["attendance_status"] == "attended"
    assert patch_response.json()["attendance_decided_at"] is not None


def test_game_participants_reject_guest_without_guest_name(client: TestClient):
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue)

    response = client.post(
        "/game-participants",
        json={
            "game_id": game["id"],
            "participant_type": "guest",
            "display_name_snapshot": "Guest Player",
            "participant_status": "pending_payment",
            "attendance_status": "unknown",
            "cancellation_type": "none",
            "price_cents": 1200,
            "currency": "USD",
        },
    )

    assert response.status_code == 400, response.text
    assert "guest_name" in response.text
