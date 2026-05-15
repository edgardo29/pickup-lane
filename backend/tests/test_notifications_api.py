from fastapi.testclient import TestClient

from backend.tests.helpers import (
    create_booking,
    create_chat_message,
    create_game,
    create_game_chat,
    create_game_participant,
    create_notification,
    create_user,
    create_venue,
)


def create_notification_setup(
    client: TestClient,
) -> tuple[dict, dict, dict, dict, dict, dict]:
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue)
    booking = create_booking(client, user["id"], game["id"])
    participant = create_game_participant(client, user["id"], game["id"], booking["id"])
    game_chat = create_game_chat(client, game["id"])
    chat_message = create_chat_message(client, game_chat["id"], user["id"])
    return user, game, booking, participant, game_chat, chat_message


def test_notifications_create_get_list_and_mark_read(client: TestClient):
    user, game, _booking, _participant, game_chat, chat_message = (
        create_notification_setup(client)
    )
    notification = create_notification(
        client,
        user["id"],
        notification_type="chat_message",
        title="New message",
        body="A new chat message was posted.",
        related_game_id=game["id"],
        related_chat_id=game_chat["id"],
        related_message_id=chat_message["id"],
    )

    get_response = client.get(f"/notifications/{notification['id']}")
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["id"] == notification["id"]
    assert get_response.json()["related_chat_id"] == game_chat["id"]

    list_response = client.get(f"/notifications?user_id={user['id']}")
    assert list_response.status_code == 200, list_response.text
    assert any(item["id"] == notification["id"] for item in list_response.json())

    patch_response = client.patch(
        f"/notifications/{notification['id']}",
        json={"is_read": True},
    )
    assert patch_response.status_code == 200, patch_response.text
    assert patch_response.json()["is_read"] is True
    assert patch_response.json()["read_at"] is not None


def test_notifications_reject_empty_title(client: TestClient):
    user = create_user(client)

    response = client.post(
        "/notifications",
        json={
            "user_id": user["id"],
            "notification_type": "admin_notice",
            "title": "   ",
            "body": "Body is present",
            "is_read": False,
        },
    )

    assert response.status_code == 400, response.text
    assert "title must not be empty" in response.text


def test_notifications_reject_immutable_update_fields(client: TestClient):
    user = create_user(client)
    notification = create_notification(client, user["id"])

    response = client.patch(
        f"/notifications/{notification['id']}",
        json={"title": "New title"},
    )

    assert response.status_code == 400, response.text
    assert "cannot be changed" in response.text


def test_notifications_reject_booking_mismatched_game(client: TestClient):
    user = create_user(client)
    venue = create_venue(client, user["id"])
    first_game = create_game(client, user["id"], venue)
    second_game = create_game(client, user["id"], venue)
    booking = create_booking(client, user["id"], first_game["id"])

    response = client.post(
        "/notifications",
        json={
            "user_id": user["id"],
            "notification_type": "booking_confirmed",
            "title": "Booking confirmed",
            "body": "Your booking is confirmed.",
            "related_game_id": second_game["id"],
            "related_booking_id": booking["id"],
            "is_read": False,
        },
    )

    assert response.status_code == 400, response.text
    assert "related_booking_id must belong to related_game_id" in response.text


def test_notifications_unread_clears_read_at(client: TestClient):
    user = create_user(client)
    notification = create_notification(client, user["id"], is_read=True)
    assert notification["read_at"] is not None

    response = client.patch(
        f"/notifications/{notification['id']}",
        json={"is_read": False},
    )

    assert response.status_code == 200, response.text
    assert response.json()["is_read"] is False
    assert response.json()["read_at"] is None
