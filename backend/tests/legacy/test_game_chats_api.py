from fastapi.testclient import TestClient

from backend.tests.helpers import (
    authenticate_as,
    create_game,
    create_game_chat,
    create_user,
    create_venue,
    run_as_temporary_admin,
    set_user_account_status,
    set_user_role,
)


def test_game_chat_member_routes_reject_suspended_user(client: TestClient):
    user = create_user(client)
    set_user_account_status(user["id"], "suspended")
    authenticate_as(user["id"])
    game_id = "00000000-0000-4000-8000-000000000001"
    chat_id = "00000000-0000-4000-8000-000000000002"

    responses = [
        client.post(f"/game-chats/for-game/{game_id}", json={}),
        client.get(f"/game-chats/{chat_id}/read-state"),
        client.post(f"/game-chats/{chat_id}/read", json={}),
    ]

    for response in responses:
        assert response.status_code == 403, response.text
        assert response.json()["detail"] == "Active account required."


def test_game_chats_create_get_list_and_update(client: TestClient):
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue)
    game_chat = create_game_chat(client, game["id"])

    get_response = run_as_temporary_admin(
        client,
        lambda: client.get(f"/game-chats/{game_chat['id']}"),
    )
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["id"] == game_chat["id"]

    list_response = run_as_temporary_admin(
        client,
        lambda: client.get(f"/game-chats?game_id={game['id']}"),
    )
    assert list_response.status_code == 200, list_response.text
    assert any(item["id"] == game_chat["id"] for item in list_response.json())

    patch_response = run_as_temporary_admin(
        client,
        lambda: client.patch(
            f"/game-chats/{game_chat['id']}",
            json={"chat_status": "closed"},
        ),
    )
    assert patch_response.status_code == 200, patch_response.text
    assert patch_response.json()["chat_status"] == "closed"
    assert patch_response.json()["closed_at"] is not None

    audit_response = run_as_temporary_admin(
        client,
        lambda: client.get(f"/admin/actions?target_game_id={game['id']}"),
    )
    assert audit_response.status_code == 200, audit_response.text
    action_types = {item["action_type"] for item in audit_response.json()}
    assert "create_game_chat" in action_types
    assert "update_game_chat" in action_types


def test_game_chats_reject_duplicate_game(client: TestClient):
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue)
    create_game_chat(client, game["id"])

    response = run_as_temporary_admin(
        client,
        lambda: client.post(
            "/game-chats",
            json={
                "game_id": game["id"],
                "chat_status": "active",
            },
        ),
    )

    assert response.status_code == 409, response.text
    assert "already has a chat room" in response.text


def test_game_chats_reject_disabled_game_chat(client: TestClient):
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue, is_chat_enabled=False)

    response = run_as_temporary_admin(
        client,
        lambda: client.post(
            "/game-chats",
            json={
                "game_id": game["id"],
                "chat_status": "active",
            },
        ),
    )

    assert response.status_code == 400, response.text
    assert "chat enabled" in response.text


def test_game_chats_reject_game_id_change(client: TestClient):
    user = create_user(client)
    venue = create_venue(client, user["id"])
    first_game = create_game(client, user["id"], venue)
    second_game = create_game(client, user["id"], venue)
    game_chat = create_game_chat(client, first_game["id"])

    response = run_as_temporary_admin(
        client,
        lambda: client.patch(
            f"/game-chats/{game_chat['id']}",
            json={"game_id": second_game["id"]},
        ),
    )

    assert response.status_code == 400, response.text
    assert "game_id cannot be changed" in response.text


def test_game_chats_reject_invalid_status_filter(client: TestClient):
    response = run_as_temporary_admin(
        client,
        lambda: client.get("/game-chats?chat_status=paused"),
    )

    assert response.status_code == 400, response.text
    assert "chat_status" in response.text


def test_game_chats_reject_update_after_closed(client: TestClient):
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue)
    game_chat = create_game_chat(client, game["id"])

    close_response = run_as_temporary_admin(
        client,
        lambda: client.patch(
            f"/game-chats/{game_chat['id']}",
            json={"chat_status": "closed"},
        ),
    )
    assert close_response.status_code == 200, close_response.text

    response = run_as_temporary_admin(
        client,
        lambda: client.patch(
            f"/game-chats/{game_chat['id']}",
            json={"chat_status": "active"},
        ),
    )

    assert response.status_code == 400, response.text
    assert "Closed game chats cannot be updated" in response.text


def test_generic_game_chat_routes_require_staff_permission(client: TestClient):
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue)
    game_chat = create_game_chat(client, game["id"])
    authenticate_as(user["id"])

    get_response = client.get(f"/game-chats/{game_chat['id']}")
    list_response = client.get(f"/game-chats?game_id={game['id']}")
    create_response = client.post(
        "/game-chats",
        json={"game_id": game["id"], "chat_status": "active"},
    )
    patch_response = client.patch(
        f"/game-chats/{game_chat['id']}",
        json={"chat_status": "closed"},
    )

    assert get_response.status_code == 403, get_response.text
    assert list_response.status_code == 403, list_response.text
    assert create_response.status_code == 403, create_response.text
    assert patch_response.status_code == 403, patch_response.text


def test_admin_can_read_and_manage_generic_game_chats(
    client: TestClient,
):
    host = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(client, host["id"], venue)
    game_without_chat = create_game(client, host["id"], venue)
    game_chat = create_game_chat(client, game["id"])
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    authenticate_as(admin["id"])

    get_response = client.get(f"/game-chats/{game_chat['id']}")
    list_response = client.get(f"/game-chats?game_id={game['id']}")
    create_response = client.post(
        "/game-chats",
        json={"game_id": game_without_chat["id"], "chat_status": "active"},
    )
    patch_response = client.patch(
        f"/game-chats/{game_chat['id']}",
        json={"chat_status": "closed"},
    )

    assert get_response.status_code == 200, get_response.text
    assert list_response.status_code == 200, list_response.text
    assert create_response.status_code == 201, create_response.text
    assert patch_response.status_code == 200, patch_response.text
