from fastapi.testclient import TestClient
from uuid import UUID
from datetime import UTC, datetime, timedelta
from urllib.parse import quote

from backend.tests.helpers import (
    authenticate_as,
    create_booking,
    create_chat_message,
    create_game,
    create_game_chat,
    create_game_participant,
    create_user,
    create_venue,
    run_as_temporary_admin,
    set_user_account_status,
    set_user_role,
)


def create_chat_message_setup(client: TestClient) -> tuple[dict, dict, dict, dict]:
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue, host_user_id=user["id"])
    booking = create_booking(client, user["id"], game["id"])
    create_game_participant(
        client,
        user["id"],
        game["id"],
        booking["id"],
    )
    game_chat = create_game_chat(client, game["id"])
    return user, venue, game, game_chat


def test_chat_message_routes_reject_suspended_user(client: TestClient):
    user = create_user(client)
    set_user_account_status(user["id"], "suspended")
    authenticate_as(user["id"])
    chat_id = "00000000-0000-4000-8000-000000000001"
    message_id = "00000000-0000-4000-8000-000000000002"

    responses = [
        client.post(
            "/chat-messages",
            json={
                "chat_id": chat_id,
                "message_body": "Suspended user should not send.",
            },
        ),
        client.get(f"/chat-messages/{message_id}"),
        client.get(f"/chat-messages?chat_id={chat_id}"),
        client.patch(
            f"/chat-messages/{message_id}",
            json={"message_body": "Suspended user should not edit."},
        ),
    ]

    for response in responses:
        assert response.status_code == 403, response.text
        assert response.json()["detail"] == "Active account required."


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


def test_chat_messages_list_after_created_at_returns_newer_messages(client: TestClient):
    user, _venue, _game, game_chat = create_chat_message_setup(client)
    first_message = create_chat_message(client, game_chat["id"], user["id"])

    from backend.database import SessionLocal
    from backend.models import ChatMessage

    with SessionLocal() as db:
        db_first_message = db.get(ChatMessage, UUID(first_message["id"]))
        assert db_first_message is not None
        db_first_message.created_at = datetime.now(UTC) - timedelta(seconds=3)
        db.commit()
        after_created_at = quote(db_first_message.created_at.isoformat())

    second_message = create_chat_message(
        client,
        game_chat["id"],
        user["id"],
        message_body="Newer CI chat message",
    )
    authenticate_as(user["id"])

    response = client.get(
        f"/chat-messages?chat_id={game_chat['id']}"
        f"&moderation_status=visible&after_created_at={after_created_at}"
    )

    assert response.status_code == 200, response.text
    message_ids = [item["id"] for item in response.json()]
    assert second_message["id"] in message_ids
    assert first_message["id"] not in message_ids


def test_chat_messages_reject_message_to_locked_chat(client: TestClient):
    user, _venue, _game, game_chat = create_chat_message_setup(client)
    authenticate_as(user["id"])
    lock_response = run_as_temporary_admin(
        client,
        lambda: client.patch(
            f"/game-chats/{game_chat['id']}",
            json={"chat_status": "locked"},
        ),
    )
    assert lock_response.status_code == 200, lock_response.text

    response = client.post(
        "/chat-messages",
        json={
            "chat_id": game_chat["id"],
            "message_body": "This should not send",
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
            "message_body": "x" * 301,
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
            "message_body": "Trying to sneak into chat",
        },
    )

    assert response.status_code == 403, response.text
    assert "confirmed players and the host" in response.text


def test_chat_messages_reject_player_system_and_pinned_fields(client: TestClient):
    user, _venue, _game, game_chat = create_chat_message_setup(client)
    authenticate_as(user["id"])

    system_response = client.post(
        "/chat-messages",
        json={
            "chat_id": game_chat["id"],
            "message_type": "system",
            "message_body": "Forged system message",
            "is_pinned": False,
            "moderation_status": "visible",
        },
    )
    pinned_response = client.post(
        "/chat-messages",
        json={
            "chat_id": game_chat["id"],
            "message_type": "text",
            "message_body": "Forged pinned message",
            "is_pinned": True,
            "pinned_by_user_id": user["id"],
            "moderation_status": "visible",
        },
    )

    assert system_response.status_code == 422, system_response.text
    assert pinned_response.status_code == 422, pinned_response.text


def test_chat_message_sender_can_delete_own_message(client: TestClient):
    user, _venue, _game, game_chat = create_chat_message_setup(client)
    chat_message = create_chat_message(client, game_chat["id"], user["id"])
    authenticate_as(user["id"])

    delete_response = client.patch(
        f"/chat-messages/{chat_message['id']}",
        json={"moderation_status": "deleted_by_sender"},
    )
    assert delete_response.status_code == 200, delete_response.text
    assert delete_response.json()["moderation_status"] == "deleted_by_sender"
    assert delete_response.json()["deleted_by_user_id"] == user["id"]
    assert delete_response.json()["deleted_at"] is not None

    get_response = client.get(f"/chat-messages/{chat_message['id']}")
    assert get_response.status_code == 404, get_response.text

    list_response = client.get(f"/chat-messages?chat_id={game_chat['id']}")
    assert list_response.status_code == 200, list_response.text
    assert chat_message["id"] not in {
        item["id"] for item in list_response.json()
    }


def test_chat_message_sender_cannot_set_moderation_actor_fields(client: TestClient):
    user, _venue, _game, game_chat = create_chat_message_setup(client)
    chat_message = create_chat_message(client, game_chat["id"], user["id"])
    authenticate_as(user["id"])

    response = client.patch(
        f"/chat-messages/{chat_message['id']}",
        json={
            "moderation_status": "deleted_by_sender",
            "deleted_by_user_id": user["id"],
        },
    )

    assert response.status_code == 422, response.text


def test_chat_messages_notify_other_confirmed_members_and_mark_read(client: TestClient):
    host = create_user(client)
    player = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(client, host["id"], venue, host_user_id=host["id"])
    create_game_participant(
        client,
        host["id"],
        game["id"],
        participant_type="host",
        price_cents=0,
        roster_order=1,
    )
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

    authenticate_as(player["id"])
    notifications_response = client.get(
        "/notifications/me?notification_type=chat_message"
    )
    assert notifications_response.status_code == 200, notifications_response.text
    notifications = notifications_response.json()
    assert len(notifications) == 1
    assert notifications[0]["related_game_id"] == game["id"]
    assert notifications[0]["related_chat_id"] == game_chat["id"]
    assert notifications[0]["related_message_id"] == chat_message["id"]
    assert (
        notifications[0]["aggregation_key"]
        == f"game:{game['id']}:chat:{game_chat['id']}:user:{player['id']}:chat_message"
    )
    assert notifications[0]["aggregate_count"] == 1
    assert notifications[0]["is_read"] is False

    read_response = client.post(f"/game-chats/{game_chat['id']}/read", json={})
    assert read_response.status_code == 200, read_response.text
    assert read_response.json()["unread_count"] == 0

    notifications_response = client.get(
        "/notifications/me?notification_type=chat_message"
    )
    assert notifications_response.status_code == 200, notifications_response.text
    notifications = notifications_response.json()
    assert notifications[0]["is_read"] is True
    assert notifications[0]["read_at"] is not None
    assert notifications[0]["aggregate_count"] is None


def test_chat_messages_reuse_single_notification_per_user_chat(
    client: TestClient,
):
    host = create_user(client)
    player = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(client, host["id"], venue, host_user_id=host["id"])
    create_game_participant(
        client,
        host["id"],
        game["id"],
        participant_type="host",
        price_cents=0,
        roster_order=1,
    )
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

    first_message = create_chat_message(
        client,
        game_chat["id"],
        host["id"],
        message_body="First notification message",
    )

    from backend.database import SessionLocal
    from backend.models import ChatMessage

    with SessionLocal() as db:
        db_first_message = db.get(ChatMessage, UUID(first_message["id"]))
        assert db_first_message is not None
        db_first_message.created_at = datetime.now(UTC) - timedelta(seconds=3)
        db.commit()

    second_message = create_chat_message(
        client,
        game_chat["id"],
        host["id"],
        message_body="Second notification message",
    )

    authenticate_as(player["id"])
    notifications_response = client.get(
        "/notifications/me?notification_type=chat_message"
    )
    assert notifications_response.status_code == 200, notifications_response.text
    notifications = notifications_response.json()
    assert len(notifications) == 1
    notification_id = notifications[0]["id"]
    assert notifications[0]["related_message_id"] == second_message["id"]
    assert notifications[0]["aggregate_count"] == 2
    assert notifications[0]["is_read"] is False

    read_response = client.post(f"/game-chats/{game_chat['id']}/read", json={})
    assert read_response.status_code == 200, read_response.text

    notifications_response = client.get(
        "/notifications/me?notification_type=chat_message"
    )
    assert notifications_response.status_code == 200, notifications_response.text
    notifications = notifications_response.json()
    assert notifications[0]["id"] == notification_id
    assert notifications[0]["is_read"] is True
    assert notifications[0]["aggregate_count"] is None

    with SessionLocal() as db:
        db_second_message = db.get(ChatMessage, UUID(second_message["id"]))
        assert db_second_message is not None
        db_second_message.created_at = datetime.now(UTC) - timedelta(seconds=3)
        db.commit()

    third_message = create_chat_message(
        client,
        game_chat["id"],
        host["id"],
        message_body="Third notification message",
    )

    authenticate_as(player["id"])
    notifications_response = client.get(
        "/notifications/me?notification_type=chat_message"
    )
    assert notifications_response.status_code == 200, notifications_response.text
    notifications = notifications_response.json()
    assert len(notifications) == 1
    assert notifications[0]["id"] == notification_id
    assert notifications[0]["related_message_id"] == third_message["id"]
    assert notifications[0]["is_read"] is False
    assert notifications[0]["read_at"] is None
    assert notifications[0]["aggregate_count"] == 1


def test_chat_messages_hide_requires_admin(client: TestClient):
    user, _venue, _game, game_chat = create_chat_message_setup(client)
    chat_message = create_chat_message(client, game_chat["id"], user["id"])

    response = client.patch(
        f"/chat-messages/{chat_message['id']}",
        json={
            "moderation_status": "hidden_by_admin",
            "reason": "Player attempted a moderation action.",
        },
    )

    assert response.status_code == 403, response.text
    assert "Content moderation permission required" in response.text


def test_chat_messages_hide_by_moderator_is_audited_and_terminal(
    client: TestClient,
):
    user, _venue, _game, game_chat = create_chat_message_setup(client)
    moderator = create_user(client)
    set_user_role(moderator["id"], "moderator")
    chat_message = create_chat_message(client, game_chat["id"], user["id"])
    authenticate_as(moderator["id"])

    hide_response = client.patch(
        f"/chat-messages/{chat_message['id']}",
        json={
            "moderation_status": "hidden_by_admin",
            "reason": "Message violated the chat rules.",
        },
    )
    assert hide_response.status_code == 200, hide_response.text
    assert hide_response.json()["deleted_by_user_id"] == moderator["id"]
    assert hide_response.json()["deleted_at"] is not None

    hidden_list_response = client.get(
        f"/chat-messages?chat_id={game_chat['id']}"
        "&moderation_status=hidden_by_admin"
    )
    assert hidden_list_response.status_code == 200, hidden_list_response.text
    assert [item["id"] for item in hidden_list_response.json()] == [
        chat_message["id"]
    ]

    from sqlalchemy import select

    from backend.database import SessionLocal
    from backend.models import AdminAction

    with SessionLocal() as db:
        audit_action = db.scalar(
            select(AdminAction).where(
                AdminAction.action_type == "hide_chat_message",
                AdminAction.target_message_id == UUID(chat_message["id"]),
            )
        )
        assert audit_action is not None
        assert audit_action.admin_user_id == UUID(moderator["id"])
        assert audit_action.target_game_id == UUID(_game["id"])
        assert audit_action.target_user_id == UUID(user["id"])
        assert audit_action.reason == "Message violated the chat rules."
        assert "message_body" not in (audit_action.metadata_ or {})

    response = client.patch(
        f"/chat-messages/{chat_message['id']}",
        json={"message_body": "Trying to edit hidden message"},
    )

    assert response.status_code == 400, response.text
    assert "cannot be updated" in response.text

    authenticate_as(user["id"])
    member_get_response = client.get(f"/chat-messages/{chat_message['id']}")
    member_list_response = client.get(
        f"/chat-messages?chat_id={game_chat['id']}"
        "&moderation_status=hidden_by_admin"
    )
    assert member_get_response.status_code == 404, member_get_response.text
    assert member_list_response.status_code == 403, member_list_response.text


def test_chat_message_moderation_requires_reason(client: TestClient):
    user, _venue, _game, game_chat = create_chat_message_setup(client)
    moderator = create_user(client)
    set_user_role(moderator["id"], "moderator")
    chat_message = create_chat_message(client, game_chat["id"], user["id"])
    authenticate_as(moderator["id"])

    response = client.patch(
        f"/chat-messages/{chat_message['id']}",
        json={"moderation_status": "hidden_by_admin"},
    )

    assert response.status_code == 400, response.text
    assert "reason is required" in response.text
