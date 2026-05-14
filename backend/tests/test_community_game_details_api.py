from fastapi.testclient import TestClient

from backend.tests.helpers import (
    create_community_game_detail,
    create_game,
    create_user,
    create_venue,
)


def test_community_game_detail_create_get_list_and_update(client: TestClient):
    host = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
    )
    detail = create_community_game_detail(client, game["id"])

    get_response = client.get(f"/community-game-details/{detail['id']}")
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["id"] == detail["id"]

    list_response = client.get(f"/community-game-details?game_id={game['id']}")
    assert list_response.status_code == 200, list_response.text
    assert any(item["id"] == detail["id"] for item in list_response.json())

    patch_response = client.patch(
        f"/community-game-details/{detail['id']}",
        json={
            "payment_methods_snapshot": ["zelle"],
            "payment_due_timing_snapshot": "at_arrival",
            "player_message_snapshot": "Check in with the host on arrival.",
        },
    )
    assert patch_response.status_code == 200, patch_response.text
    assert patch_response.json()["payment_methods_snapshot"] == ["zelle"]
    assert patch_response.json()["payment_due_timing_snapshot"] == "at_arrival"


def test_community_game_detail_rejects_official_game(client: TestClient):
    host = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(client, host["id"], venue)

    response = client.post(
        "/community-game-details",
        json={
            "game_id": game["id"],
            "payment_methods_snapshot": ["venmo"],
        },
    )

    assert response.status_code == 400, response.text
    assert "require a community game" in response.text


def test_community_game_detail_rejects_duplicate_game(client: TestClient):
    host = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
    )
    create_community_game_detail(client, game["id"])

    response = client.post(
        "/community-game-details",
        json={
            "game_id": game["id"],
            "payment_methods_snapshot": ["cash"],
        },
    )

    assert response.status_code == 409, response.text
    assert "already has community game details" in response.text
