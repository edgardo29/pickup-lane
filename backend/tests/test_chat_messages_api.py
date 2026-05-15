from fastapi.testclient import TestClient

from backend.tests.helpers import (
    authenticate_as,
    create_booking,
    create_chat_message,
    create_game,
    create_game_chat,
    create_game_participant,
    create_user,
    create_venue,
    set_user_role,
)


def create_chat_message_setup(client: TestClient) -> tuple[dict, dict, dict, dict]:
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue, host_user_id=user["id"])
    game_chat = create_game_chat(client, game["id"])
    return user, venue, game, game_chat


def test_chat_messages_create_get_list_and_update(client: TestClient):
    user, _venue, _game, game_chat = create_chat_message_setup(client)
    chat_message = create_chat_message(client, game_chat["id"], user["id"])
    authenticate_as(user["id"])

    get_response = client.get(f"/chat-messages/{chat_message['id']}")
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["id"] == chat_message["id"]

    list_response = client.get(f"/chat-messages?chat_id={game_chat['id']}")
    assert list_response.status_code == 200, list_response.text
    assert any(item["id"] == chat_message["id"] for item in list_response.json())

    patch_response = client.patch(
        f"/chat-messages/{chat_message['id']}",
        json={"message_body": "Updated CI chat message"},
    )
    assert patch_response.status_code == 200, patch_response.text
    assert patch_response.json()["message_body"] == "Updated CI chat message"
    assert patch_response.json()["edited_at"] is not None


def test_chat_messages_reject_message_to_locked_chat(client: TestClient):
    user, _venue, _game, game_chat = create_chat_message_setup(client)
    authenticate_as(user["id"])
    lock_response = client.patch(
        f"/game-chats/{game_chat['id']}",
        json={"chat_status": "locked"},
    )
    assert lock_response.status_code == 200, lock_response.text

    response = client.post(
        "/chat-messages",
        json={
            "chat_id": game_chat["id"],
            "sender_user_id": user["id"],
            "message_type": "text",
            "message_body": "This should not send",
            "is_pinned": False,
            "moderation_status": "visible",
        },
    )

    assert response.status_code == 400, response.text
    assert "cannot receive message changes" in response.text


def test_chat_messages_reject_long_message(client: TestClient):
    user, _venue, _game, game_chat = create_chat_message_setup(client)
    authenticate_as(user["id"])

    response = client.post(
        "/chat-messages",
        json={
            "chat_id": game_chat["id"],
            "message_type": "text",
            "message_body": "x" * 301,
            "is_pinned": False,
            "moderation_status": "visible",
        },
    )

    assert response.status_code == 400, response.text
    assert "300 characters" in response.text


def test_chat_messages_reject_non_member_sender(client: TestClient):
    user, _venue, _game, game_chat = create_chat_message_setup(client)
    non_member = create_user(client)
    authenticate_as(non_member["id"])

    response = client.post(
        "/chat-messages",
        json={
            "chat_id": game_chat["id"],
            "sender_user_id": non_member["id"],
            "message_type": "text",
            "message_body": "Trying to sneak into chat",
            "is_pinned": False,
            "moderation_status": "visible",
        },
    )

    assert response.status_code == 403, response.text
    assert "confirmed players and the host" in response.text


def test_chat_messages_notify_other_confirmed_members_and_mark_read(client: TestClient):
    host = create_user(client)
    player = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(client, host["id"], venue, host_user_id=host["id"])
    booking = create_booking(client, player["id"], game["id"])
    create_game_participant(
        client,
        player["id"],
        game["id"],
        booking["id"],
        display_name_snapshot="Chat Player",
        roster_order=2,
    )
    game_chat = create_game_chat(client, game["id"])

    chat_message = create_chat_message(client, game_chat["id"], host["id"])

    notifications_response = client.get(
        f"/notifications?user_id={player['id']}&notification_type=chat_message"
    )
    assert notifications_response.status_code == 200, notifications_response.text
    notifications = notifications_response.json()
    assert len(notifications) == 1
    assert notifications[0]["related_game_id"] == game["id"]
    assert notifications[0]["related_chat_id"] == game_chat["id"]
    assert notifications[0]["related_message_id"] == chat_message["id"]
    assert notifications[0]["is_read"] is False

    authenticate_as(player["id"])
    read_response = client.post(f"/game-chats/{game_chat['id']}/read", json={})
    assert read_response.status_code == 200, read_response.text
    assert read_response.json()["unread_count"] == 0

    notifications_response = client.get(
        f"/notifications?user_id={player['id']}&notification_type=chat_message"
    )
    assert notifications_response.status_code == 200, notifications_response.text
    notifications = notifications_response.json()
    assert notifications[0]["is_read"] is True
    assert notifications[0]["read_at"] is not None


def test_chat_messages_hide_requires_admin(client: TestClient):
    user, _venue, _game, game_chat = create_chat_message_setup(client)
    chat_message = create_chat_message(client, game_chat["id"], user["id"])

    response = client.patch(
        f"/chat-messages/{chat_message['id']}",
        json={
            "moderation_status": "hidden_by_admin",
            "deleted_by_user_id": user["id"],
        },
    )

    assert response.status_code == 400, response.text
    assert "admin deleted_by_user_id" in response.text


def test_chat_messages_hide_by_admin_is_terminal(client: TestClient):
    user, _venue, _game, game_chat = create_chat_message_setup(client)
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    chat_message = create_chat_message(client, game_chat["id"], user["id"])
    authenticate_as(admin["id"])

    hide_response = client.patch(
        f"/chat-messages/{chat_message['id']}",
        json={
            "moderation_status": "hidden_by_admin",
            "deleted_by_user_id": admin["id"],
        },
    )
    assert hide_response.status_code == 200, hide_response.text
    assert hide_response.json()["deleted_at"] is not None

    response = client.patch(
        f"/chat-messages/{chat_message['id']}",
        json={"message_body": "Trying to edit hidden message"},
    )

    assert response.status_code == 400, response.text
    assert "cannot be updated" in response.text
