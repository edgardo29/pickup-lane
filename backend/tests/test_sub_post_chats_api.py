from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4
from urllib.parse import quote

from fastapi.testclient import TestClient

from backend.database import SessionLocal
from backend.models import SubPostChatMessage
from backend.tests.helpers import (
    authenticate_as,
    create_sub_post,
    create_user,
    set_user_account_status,
)


def authenticate_optional_as(user_id: str) -> None:
    from backend.database import SessionLocal
    from backend.main import app
    from backend.models import User
    from backend.services.auth_service import get_optional_current_app_user

    def override_current_user() -> User:
        with SessionLocal() as db:
            db_user = db.get(User, UUID(user_id))
            assert db_user is not None
            return db_user

    app.dependency_overrides[get_optional_current_app_user] = override_current_user


def request_spot(
    client: TestClient,
    requester_id: str,
    post: dict,
    position_index: int = 0,
) -> dict:
    authenticate_as(requester_id)
    response = client.post(
        f"/need-a-sub/posts/{post['id']}/requests",
        json={"sub_post_position_id": post["positions"][position_index]["id"]},
    )
    assert response.status_code == 201, response.text
    return response.json()


def accept_request(client: TestClient, owner_id: str, request_id: str) -> dict:
    authenticate_as(owner_id)
    response = client.patch(f"/need-a-sub/requests/{request_id}/accept")
    assert response.status_code == 200, response.text
    return response.json()


def ensure_sub_post_chat(client: TestClient, user_id: str, post_id: str) -> dict:
    authenticate_as(user_id)
    response = client.post(f"/need-a-sub/posts/{post_id}/chat", json={})
    assert response.status_code == 200, response.text
    return response.json()


def send_sub_chat_message(
    client: TestClient,
    user_id: str,
    post_id: str,
    chat_id: str,
    body: str = "See you near the main entrance.",
) -> dict:
    authenticate_as(user_id)
    response = client.post(
        f"/need-a-sub/posts/{post_id}/chat/messages",
        json={
            "chat_id": chat_id,
            "message_body": body,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def list_user_notifications(
    client: TestClient,
    user_id: str,
    notification_type: str,
) -> list[dict]:
    authenticate_as(user_id)
    response = client.get(f"/notifications/me?notification_type={notification_type}")
    assert response.status_code == 200, response.text
    return response.json()


def create_confirmed_sub_chat_setup(client: TestClient) -> tuple[dict, dict, dict, dict, dict]:
    owner = create_user(client, first_name="Olivia", last_name="Owner")
    confirmed_player = create_user(client, first_name="Casey", last_name="Confirmed")
    post = create_sub_post(client, owner["id"])
    sub_request = request_spot(client, confirmed_player["id"], post, 0)
    accept_request(client, owner["id"], sub_request["id"])
    chat = ensure_sub_post_chat(client, owner["id"], post["id"])
    return owner, confirmed_player, post, sub_request, chat


def insert_visible_sub_chat_messages(
    chat_id: str,
    sender_user_id: str,
    count: int,
    *,
    start_at: datetime | None = None,
) -> list[str]:
    created_ids: list[str] = []
    start_value = start_at or (datetime.now(UTC) - timedelta(minutes=count + 1))
    with SessionLocal() as db:
        for index in range(count):
            message_id = uuid4()
            created_at = start_value + timedelta(seconds=index)
            db.add(
                SubPostChatMessage(
                    id=message_id,
                    chat_id=UUID(chat_id),
                    sender_user_id=UUID(sender_user_id),
                    sender_display_name_snapshot="Test Sender",
                    sender_initials_snapshot="TS",
                    message_type="text",
                    message_body=f"Seeded message {index}",
                    visibility_status="visible",
                    review_status="clear",
                    created_at=created_at,
                    updated_at=created_at,
                )
            )
            created_ids.append(str(message_id))
        db.commit()
    return created_ids


def test_need_a_sub_chat_routes_reject_suspended_user(client: TestClient):
    user = create_user(client)
    set_user_account_status(user["id"], "suspended")
    authenticate_as(user["id"])
    post_id = "00000000-0000-4000-8000-000000000001"
    chat_id = "00000000-0000-4000-8000-000000000002"
    message_id = "00000000-0000-4000-8000-000000000003"

    responses = [
        client.post(f"/need-a-sub/posts/{post_id}/chat", json={}),
        client.get(f"/need-a-sub/posts/{post_id}/chat"),
        client.get(f"/need-a-sub/posts/{post_id}/chat/read-state"),
        client.post(f"/need-a-sub/posts/{post_id}/chat/read", json={}),
        client.get(f"/need-a-sub/posts/{post_id}/chat/messages"),
        client.post(
            f"/need-a-sub/posts/{post_id}/chat/messages",
            json={
                "chat_id": chat_id,
                "message_body": "Can still make this?",
            },
        ),
        client.patch(
            f"/need-a-sub/posts/{post_id}/chat/messages/{message_id}",
            json={"message_body": "Updated message."},
        ),
    ]

    for response in responses:
        assert response.status_code == 403, response.text
        assert response.json()["detail"] == "Active account required."


def test_need_a_sub_chat_owner_can_open_before_confirmed_players(client: TestClient):
    owner = create_user(client)
    post = create_sub_post(client, owner["id"])

    chat = ensure_sub_post_chat(client, owner["id"], post["id"])

    assert chat["sub_post_id"] == post["id"]
    assert chat["chat_status"] == "active"
    assert chat["unread_count"] == 0


def test_need_a_sub_chat_noop_edit_does_not_flag_repeated_message(
    client: TestClient,
):
    owner, _confirmed_player, post, _sub_request, chat = create_confirmed_sub_chat_setup(
        client
    )
    message = send_sub_chat_message(
        client,
        owner["id"],
        post["id"],
        chat["id"],
        "Normal sub logistics update",
    )
    authenticate_as(owner["id"])

    response = client.patch(
        f"/need-a-sub/posts/{post['id']}/chat/messages/{message['id']}",
        json={"message_body": "Normal sub logistics update"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["review_status"] == "clear"


def test_need_a_sub_chat_rejects_request_supplied_actor_fields(client: TestClient):
    owner, _confirmed_player, post, _sub_request, chat = create_confirmed_sub_chat_setup(
        client
    )
    authenticate_as(owner["id"])

    ensure_response = client.post(
        f"/need-a-sub/posts/{post['id']}/chat",
        json={"acting_user_id": owner["id"]},
    )
    assert ensure_response.status_code == 422, ensure_response.text

    read_response = client.post(
        f"/need-a-sub/posts/{post['id']}/chat/read",
        json={"acting_user_id": owner["id"]},
    )
    assert read_response.status_code == 422, read_response.text

    message_response = client.post(
        f"/need-a-sub/posts/{post['id']}/chat/messages",
        json={
            "chat_id": chat["id"],
            "sender_user_id": owner["id"],
            "message_body": "This should derive sender from auth.",
        },
    )
    assert message_response.status_code == 422, message_response.text

    message = send_sub_chat_message(client, owner["id"], post["id"], chat["id"])
    update_response = client.patch(
        f"/need-a-sub/posts/{post['id']}/chat/messages/{message['id']}",
        json={
            "sender_user_id": owner["id"],
            "message_body": "This should also derive sender from auth.",
        },
    )
    assert update_response.status_code == 422, update_response.text


def test_need_a_sub_private_detail_stays_available_for_chat_window(
    client: TestClient,
):
    owner, confirmed_player, post, _sub_request, _chat = create_confirmed_sub_chat_setup(
        client
    )
    now = datetime.now(UTC)

    from backend.database import SessionLocal
    from backend.models import SubPost

    with SessionLocal() as db:
        db_post = db.get(SubPost, UUID(post["id"]))
        assert db_post is not None
        db_post.starts_at = now - timedelta(hours=1)
        db_post.ends_at = now + timedelta(hours=1)
        db_post.expires_at = db_post.starts_at
        db_post.updated_at = now
        db.add(db_post)
        db.commit()

    public_response = client.get(f"/need-a-sub/posts/{post['id']}")
    assert public_response.status_code == 404, public_response.text

    authenticate_optional_as(owner["id"])
    owner_response = client.get(f"/need-a-sub/posts/{post['id']}")
    assert owner_response.status_code == 200, owner_response.text
    assert owner_response.json()["id"] == post["id"]

    authenticate_optional_as(confirmed_player["id"])
    confirmed_response = client.get(f"/need-a-sub/posts/{post['id']}")
    assert confirmed_response.status_code == 200, confirmed_response.text
    assert confirmed_response.json()["id"] == post["id"]


def test_need_a_sub_chat_access_is_confirmed_only(client: TestClient):
    owner = create_user(client)
    pending_player = create_user(client)
    waitlisted_player = create_user(client)
    unrelated_user = create_user(client)
    post = create_sub_post(client, owner["id"])
    pending_request = request_spot(client, pending_player["id"], post, 0)
    request_spot(client, waitlisted_player["id"], post, 0)

    authenticate_as(pending_player["id"])
    pending_response = client.post(f"/need-a-sub/posts/{post['id']}/chat", json={})
    assert pending_response.status_code == 403, pending_response.text

    authenticate_as(waitlisted_player["id"])
    waitlisted_response = client.post(f"/need-a-sub/posts/{post['id']}/chat", json={})
    assert waitlisted_response.status_code == 403, waitlisted_response.text

    authenticate_as(unrelated_user["id"])
    unrelated_response = client.post(f"/need-a-sub/posts/{post['id']}/chat", json={})
    assert unrelated_response.status_code == 403, unrelated_response.text

    accept_request(client, owner["id"], pending_request["id"])
    chat = ensure_sub_post_chat(client, pending_player["id"], post["id"])
    assert chat["sub_post_id"] == post["id"]


def test_need_a_sub_closed_chat_rejects_message_changes(client: TestClient):
    owner, confirmed_player, post, _sub_request, chat = create_confirmed_sub_chat_setup(
        client
    )
    message = send_sub_chat_message(
        client,
        owner["id"],
        post["id"],
        chat["id"],
        "This message is visible before cancellation.",
    )
    authenticate_as(owner["id"])
    cancel_response = client.patch(
        f"/need-a-sub/posts/{post['id']}/cancel",
        json={"cancel_reason": "Close this chat."},
    )
    assert cancel_response.status_code == 200, cancel_response.text

    authenticate_as(confirmed_player["id"])
    create_response = client.post(
        f"/need-a-sub/posts/{post['id']}/chat/messages",
        json={
            "chat_id": chat["id"],
            "message_body": "This should not send.",
        },
    )
    edit_response = client.patch(
        f"/need-a-sub/posts/{post['id']}/chat/messages/{message['id']}",
        json={"message_body": "This should not edit."},
    )
    remove_response = client.patch(
        f"/need-a-sub/posts/{post['id']}/chat/messages/{message['id']}",
        json={"visibility_status": "removed"},
    )

    for response in (create_response, edit_response, remove_response):
        assert response.status_code == 400, response.text
        assert "cannot receive messages" in response.text


def test_need_a_sub_closed_chat_still_hides_write_access_from_non_members(
    client: TestClient,
):
    owner, _confirmed_player, post, _sub_request, chat = create_confirmed_sub_chat_setup(
        client
    )
    unrelated_user = create_user(client)
    authenticate_as(owner["id"])
    cancel_response = client.patch(
        f"/need-a-sub/posts/{post['id']}/cancel",
        json={"cancel_reason": "Close this chat."},
    )
    assert cancel_response.status_code == 200, cancel_response.text

    authenticate_as(unrelated_user["id"])
    response = client.post(
        f"/need-a-sub/posts/{post['id']}/chat/messages",
        json={
            "chat_id": chat["id"],
            "message_body": "This should still be hidden from me.",
        },
    )

    assert response.status_code == 403, response.text
    assert response.json()["detail"] == (
        "Only the post owner and confirmed players can use this chat."
    )


def test_need_a_sub_chat_notifies_current_members_and_marks_read(client: TestClient):
    owner, confirmed_player, post, _sub_request, chat = create_confirmed_sub_chat_setup(client)

    first_message = send_sub_chat_message(
        client,
        owner["id"],
        post["id"],
        chat["id"],
        "Bring a dark shirt.",
    )
    first_notifications = list_user_notifications(
        client,
        confirmed_player["id"],
        "sub_chat_message",
    )
    assert len(first_notifications) == 1
    first_notification = first_notifications[0]
    assert first_notification["related_sub_post_id"] == post["id"]
    assert first_notification["related_sub_post_chat_id"] == chat["id"]
    assert first_notification["related_sub_post_chat_message_id"] == first_message["id"]
    assert first_notification["aggregate_count"] == 1
    assert first_notification["is_read"] is False
    assert (
        first_notification["aggregation_key"]
        == f"need_a_sub:post:{post['id']}:chat:{chat['id']}:"
        f"user:{confirmed_player['id']}:sub_chat_message"
    )

    send_sub_chat_message(
        client,
        owner["id"],
        post["id"],
        chat["id"],
        "Meet by field two.",
    )
    second_notifications = list_user_notifications(
        client,
        confirmed_player["id"],
        "sub_chat_message",
    )
    assert len(second_notifications) == 1
    assert second_notifications[0]["id"] == first_notification["id"]
    assert second_notifications[0]["aggregate_count"] == 2

    authenticate_as(confirmed_player["id"])
    read_response = client.post(f"/need-a-sub/posts/{post['id']}/chat/read", json={})
    assert read_response.status_code == 200, read_response.text
    assert read_response.json()["unread_count"] == 0

    read_notifications = list_user_notifications(
        client,
        confirmed_player["id"],
        "sub_chat_message",
    )
    assert read_notifications[0]["is_read"] is True
    assert read_notifications[0]["read_at"] is not None
    assert read_notifications[0]["aggregate_count"] is None


def test_need_a_sub_chat_excludes_sender_and_non_confirmed_users_from_notifications(
    client: TestClient,
):
    owner = create_user(client)
    confirmed_player = create_user(client)
    pending_player = create_user(client)
    waitlisted_player = create_user(client)
    post = create_sub_post(client, owner["id"])
    confirmed_request = request_spot(client, confirmed_player["id"], post, 0)
    request_spot(client, pending_player["id"], post, 1)
    request_spot(client, waitlisted_player["id"], post, 0)
    accept_request(client, owner["id"], confirmed_request["id"])
    chat = ensure_sub_post_chat(client, owner["id"], post["id"])

    send_sub_chat_message(client, confirmed_player["id"], post["id"], chat["id"])

    owner_notifications = list_user_notifications(client, owner["id"], "sub_chat_message")
    assert len(owner_notifications) == 1
    assert list_user_notifications(client, confirmed_player["id"], "sub_chat_message") == []
    assert list_user_notifications(client, pending_player["id"], "sub_chat_message") == []
    assert list_user_notifications(client, waitlisted_player["id"], "sub_chat_message") == []


def test_need_a_sub_chat_enforces_message_limits(client: TestClient):
    owner, _confirmed_player, post, _sub_request, chat = create_confirmed_sub_chat_setup(client)
    authenticate_as(owner["id"])

    long_response = client.post(
        f"/need-a-sub/posts/{post['id']}/chat/messages",
        json={
            "chat_id": chat["id"],
            "message_body": "x" * 301,
        },
    )
    assert long_response.status_code == 400, long_response.text
    assert "300 characters" in long_response.text

    for index in range(5):
        response = client.post(
            f"/need-a-sub/posts/{post['id']}/chat/messages",
            json={
                "chat_id": chat["id"],
                "message_body": f"Quick message {index}",
            },
        )
        assert response.status_code == 201, response.text

    rate_limited_response = client.post(
        f"/need-a-sub/posts/{post['id']}/chat/messages",
        json={
            "chat_id": chat["id"],
            "message_body": "One too many",
        },
    )
    assert rate_limited_response.status_code == 429, rate_limited_response.text


def test_need_a_sub_chat_enforces_total_visible_message_limit(client: TestClient):
    owner, _confirmed_player, post, _sub_request, chat = create_confirmed_sub_chat_setup(client)
    insert_visible_sub_chat_messages(chat["id"], owner["id"], 200)

    authenticate_as(owner["id"])
    response = client.post(
        f"/need-a-sub/posts/{post['id']}/chat/messages",
        json={
            "chat_id": chat["id"],
            "message_body": "Past the cap",
        },
    )

    assert response.status_code == 400, response.text
    assert "message limit" in response.text


def test_need_a_sub_chat_lists_latest_messages_and_paginates_older(
    client: TestClient,
):
    owner, _confirmed_player, post, _sub_request, chat = create_confirmed_sub_chat_setup(client)
    message_ids = insert_visible_sub_chat_messages(chat["id"], owner["id"], 55)

    authenticate_as(owner["id"])
    latest_response = client.get(f"/need-a-sub/posts/{post['id']}/chat/messages")
    assert latest_response.status_code == 200, latest_response.text
    latest_messages = latest_response.json()
    assert len(latest_messages) == 50
    assert latest_messages[0]["id"] == message_ids[5]
    assert latest_messages[-1]["id"] == message_ids[-1]

    before_created_at = quote(latest_messages[0]["created_at"])
    older_response = client.get(
        f"/need-a-sub/posts/{post['id']}/chat/messages"
        f"?before_created_at={before_created_at}"
    )
    assert older_response.status_code == 200, older_response.text
    older_messages = older_response.json()
    assert len(older_messages) == 5
    assert [message["id"] for message in older_messages] == message_ids[:5]


def test_need_a_sub_chat_removed_confirmed_player_loses_access_and_label_changes(
    client: TestClient,
):
    owner, confirmed_player, post, sub_request, chat = create_confirmed_sub_chat_setup(client)
    message = send_sub_chat_message(
        client,
        confirmed_player["id"],
        post["id"],
        chat["id"],
        "I can bring the ball.",
    )

    authenticate_as(owner["id"])
    cancel_response = client.patch(
        f"/need-a-sub/requests/{sub_request['id']}/cancel-by-owner",
        json={"reason": "Spot no longer needed."},
    )
    assert cancel_response.status_code == 200, cancel_response.text

    authenticate_as(confirmed_player["id"])
    player_chat_response = client.get(f"/need-a-sub/posts/{post['id']}/chat")
    assert player_chat_response.status_code == 403, player_chat_response.text

    authenticate_as(owner["id"])
    list_response = client.get(f"/need-a-sub/posts/{post['id']}/chat/messages")
    assert list_response.status_code == 200, list_response.text
    messages = list_response.json()
    removed_player_message = next(item for item in messages if item["id"] == message["id"])
    assert removed_player_message["sender_is_current_chat_member"] is False
    assert removed_player_message["sender_status_label"] == "No longer in game"


def test_need_a_sub_chat_notification_action_disables_after_player_loses_access(
    client: TestClient,
):
    owner, confirmed_player, post, sub_request, chat = create_confirmed_sub_chat_setup(client)
    message = send_sub_chat_message(
        client,
        owner["id"],
        post["id"],
        chat["id"],
        "Please confirm your jersey color.",
    )
    notifications = list_user_notifications(client, confirmed_player["id"], "sub_chat_message")
    notification = notifications[0]
    assert notification["related_sub_post_chat_message_id"] == message["id"]
    assert notification["action"] is not None
    assert notification["action"]["disabled"] is False

    authenticate_as(owner["id"])
    cancel_response = client.patch(
        f"/need-a-sub/requests/{sub_request['id']}/cancel-by-owner",
        json={"reason": "Spot no longer needed."},
    )
    assert cancel_response.status_code == 200, cancel_response.text

    authenticate_as(confirmed_player["id"])
    get_response = client.get(f"/notifications/{notification['id']}")
    assert get_response.status_code == 200, get_response.text
    resolved_notification = get_response.json()
    assert resolved_notification["action"] is not None
    assert resolved_notification["action"]["key"] == "view_sub_post"
    assert resolved_notification["action"]["disabled"] is True
    assert resolved_notification["action"]["path"] is None
    assert "no longer have access" in resolved_notification["action"]["disabled_reason"]
