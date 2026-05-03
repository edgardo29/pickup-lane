from fastapi.testclient import TestClient

from backend.tests.helpers import (
    create_game,
    create_game_status_history,
    create_user,
    create_venue,
)


def create_game_status_history_setup(client: TestClient) -> tuple[dict, dict, dict]:
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue)
    return user, venue, game


def test_game_status_history_create_get_list_and_update_reason(
    client: TestClient,
):
    user, _venue, game = create_game_status_history_setup(client)
    history = create_game_status_history(
        client,
        game["id"],
        changed_by_user_id=user["id"],
    )

    get_response = client.get(f"/game-status-history/{history['id']}")
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["id"] == history["id"]

    list_response = client.get(f"/game-status-history?game_id={game['id']}")
    assert list_response.status_code == 200, list_response.text
    assert any(item["id"] == history["id"] for item in list_response.json())

    patch_response = client.patch(
        f"/game-status-history/{history['id']}",
        json={"change_reason": "Corrected CI reason."},
    )
    assert patch_response.status_code == 200, patch_response.text
    assert patch_response.json()["change_reason"] == "Corrected CI reason."


def test_game_status_history_reject_no_status_change(client: TestClient):
    user, _venue, game = create_game_status_history_setup(client)

    response = client.post(
        "/game-status-history",
        json={
            "game_id": game["id"],
            "old_publish_status": "published",
            "new_publish_status": "published",
            "old_game_status": "scheduled",
            "new_game_status": "scheduled",
            "changed_by_user_id": user["id"],
            "change_source": "admin",
            "change_reason": "No real change",
        },
    )

    assert response.status_code == 400, response.text
    assert "At least one publish or game status must change" in response.text


def test_game_status_history_reject_invalid_change_source(client: TestClient):
    user, _venue, game = create_game_status_history_setup(client)

    response = client.post(
        "/game-status-history",
        json={
            "game_id": game["id"],
            "old_publish_status": "draft",
            "new_publish_status": "published",
            "old_game_status": "scheduled",
            "new_game_status": "scheduled",
            "changed_by_user_id": user["id"],
            "change_source": "robot",
        },
    )

    assert response.status_code == 400, response.text
    assert "change_source" in response.text


def test_game_status_history_reject_missing_actor(client: TestClient):
    _user, _venue, game = create_game_status_history_setup(client)

    response = client.post(
        "/game-status-history",
        json={
            "game_id": game["id"],
            "old_publish_status": "draft",
            "new_publish_status": "published",
            "old_game_status": "scheduled",
            "new_game_status": "scheduled",
            "changed_by_user_id": "00000000-0000-4000-8000-000000000000",
            "change_source": "admin",
        },
    )

    assert response.status_code == 404, response.text
    assert "Changed by user not found" in response.text


def test_game_status_history_reject_lifecycle_field_update(client: TestClient):
    user, _venue, game = create_game_status_history_setup(client)
    history = create_game_status_history(
        client,
        game["id"],
        changed_by_user_id=user["id"],
    )

    response = client.patch(
        f"/game-status-history/{history['id']}",
        json={"new_game_status": "cancelled"},
    )

    assert response.status_code == 400, response.text
    assert "cannot be changed" in response.text
