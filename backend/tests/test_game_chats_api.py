from fastapi.testclient import TestClient

from backend.tests.helpers import create_game, create_game_chat, create_user, create_venue


def test_game_chats_create_get_list_and_update(client: TestClient):
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue)
    game_chat = create_game_chat(client, game["id"])

    get_response = client.get(f"/game-chats/{game_chat['id']}")
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["id"] == game_chat["id"]

    list_response = client.get(f"/game-chats?game_id={game['id']}")
    assert list_response.status_code == 200, list_response.text
    assert any(item["id"] == game_chat["id"] for item in list_response.json())

    patch_response = client.patch(
        f"/game-chats/{game_chat['id']}",
        json={"chat_status": "locked"},
    )
    assert patch_response.status_code == 200, patch_response.text
    assert patch_response.json()["chat_status"] == "locked"
    assert patch_response.json()["locked_at"] is not None


def test_game_chats_reject_duplicate_game(client: TestClient):
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue)
    create_game_chat(client, game["id"])

    response = client.post(
        "/game-chats",
        json={
            "game_id": game["id"],
            "chat_status": "active",
        },
    )

    assert response.status_code == 409, response.text
    assert "already has a chat room" in response.text


def test_game_chats_reject_disabled_game_chat(client: TestClient):
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue, is_chat_enabled=False)

    response = client.post(
        "/game-chats",
        json={
            "game_id": game["id"],
            "chat_status": "active",
        },
    )

    assert response.status_code == 400, response.text
    assert "chat enabled" in response.text


def test_game_chats_reject_game_id_change(client: TestClient):
    user = create_user(client)
    venue = create_venue(client, user["id"])
    first_game = create_game(client, user["id"], venue)
    second_game = create_game(client, user["id"], venue)
    game_chat = create_game_chat(client, first_game["id"])

    response = client.patch(
        f"/game-chats/{game_chat['id']}",
        json={"game_id": second_game["id"]},
    )

    assert response.status_code == 400, response.text
    assert "game_id cannot be changed" in response.text


def test_game_chats_reject_invalid_status_filter(client: TestClient):
    response = client.get("/game-chats?chat_status=paused")

    assert response.status_code == 400, response.text
    assert "chat_status" in response.text


def test_game_chats_reject_update_after_archived(client: TestClient):
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue)
    game_chat = create_game_chat(client, game["id"])

    archive_response = client.patch(
        f"/game-chats/{game_chat['id']}",
        json={"chat_status": "archived"},
    )
    assert archive_response.status_code == 200, archive_response.text

    response = client.patch(
        f"/game-chats/{game_chat['id']}",
        json={"chat_status": "active"},
    )

    assert response.status_code == 400, response.text
    assert "Archived game chats cannot be updated" in response.text
