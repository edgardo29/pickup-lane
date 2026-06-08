from datetime import UTC, datetime

from fastapi.testclient import TestClient

from backend.tests.helpers import (
    authenticate_as,
    create_booking,
    create_chat_message,
    create_game,
    create_game_chat,
    create_game_participant,
    create_notification,
    create_sub_post,
    create_user,
    create_venue,
    set_user_role,
)


def notification_contract_fields(
    *,
    source_type: str = "pickup_lane",
    subject_label: str = "Pickup Lane",
    summary: str = "Pickup Lane posted an update.",
    action_key: str | None = None,
    subject_starts_at: str | None = None,
    subject_ends_at: str | None = None,
    subject_timezone: str | None = None,
) -> dict[str, object]:
    fields: dict[str, object] = {
        "source_type": source_type,
        "subject_label": subject_label,
        "summary": summary,
        "event_at": datetime.now(UTC).isoformat(),
    }

    if action_key is not None:
        fields["action_key"] = action_key
    if subject_starts_at is not None:
        fields["subject_starts_at"] = subject_starts_at
    if subject_ends_at is not None:
        fields["subject_ends_at"] = subject_ends_at
    if subject_timezone is not None:
        fields["subject_timezone"] = subject_timezone

    return fields


def game_notification_contract_fields(
    game: dict,
    *,
    summary: str = "New messages were posted.",
    action_key: str | None = "view_game",
) -> dict[str, object]:
    return notification_contract_fields(
        source_type=(
            "official_game" if game["game_type"] == "official" else "community_game"
        ),
        subject_label=game["title"],
        summary=summary,
        action_key=action_key,
        subject_starts_at=game["starts_at"],
        subject_ends_at=game["ends_at"],
        subject_timezone=game["timezone"],
    )


def need_a_sub_notification_contract_fields(
    sub_post: dict,
    *,
    action_key: str | None = "view_sub_post",
) -> dict[str, object]:
    return notification_contract_fields(
        source_type="need_a_sub",
        subject_label=f"{sub_post['team_name']} {sub_post['format_label']}",
        summary="A player requested a sub spot.",
        action_key=action_key,
        subject_starts_at=sub_post["starts_at"],
        subject_ends_at=sub_post["ends_at"],
        subject_timezone=sub_post["timezone"],
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


def create_sub_request(
    client: TestClient,
    requester_user_id: str,
    sub_post: dict,
    position_index: int = 0,
) -> dict:
    authenticate_as(requester_user_id)
    response = client.post(
        f"/need-a-sub/posts/{sub_post['id']}/requests",
        json={"sub_post_position_id": sub_post["positions"][position_index]["id"]},
    )

    assert response.status_code == 201, response.text
    return response.json()


def test_notifications_create_get_list_and_mark_read(client: TestClient):
    user, game, _booking, _participant, game_chat, chat_message = (
        create_notification_setup(client)
    )
    notification = create_notification(
        client,
        user["id"],
        notification_type="chat_message",
        notification_category="game_activity",
        notification_domain="game",
        title="New message",
        body="A new chat message was posted.",
        **game_notification_contract_fields(game),
        related_game_id=game["id"],
        related_chat_id=game_chat["id"],
        related_message_id=chat_message["id"],
    )

    get_response = client.get(f"/notifications/{notification['id']}")
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["id"] == notification["id"]
    assert get_response.json()["related_chat_id"] == game_chat["id"]
    assert get_response.json()["notification_category"] == "game_activity"
    assert get_response.json()["notification_domain"] == "game"
    assert get_response.json()["source_type"] == "official_game"
    assert get_response.json()["source_label"] == "Official Game"
    assert get_response.json()["row_subject"].startswith(f"{game['title']} · ")
    assert get_response.json()["action"]["key"] == "view_game"
    assert get_response.json()["icon"] == "MessageSquareText"
    assert get_response.json()["severity"] == "default"

    list_response = client.get("/notifications/me?notification_category=game_activity")
    assert list_response.status_code == 200, list_response.text
    assert any(item["id"] == notification["id"] for item in list_response.json())

    patch_response = client.patch(
        f"/notifications/{notification['id']}/read",
        json={},
    )
    assert patch_response.status_code == 200, patch_response.text
    assert patch_response.json()["is_read"] is True
    assert patch_response.json()["read_at"] is not None


def test_notifications_reject_empty_title(client: TestClient):
    user = create_user(client)
    authenticate_as(user["id"])

    response = client.post(
        "/notifications",
        json={
            "user_id": user["id"],
            "notification_type": "admin_notice",
            "notification_category": "app",
            "notification_domain": "admin",
            "title": "   ",
            **notification_contract_fields(),
            "body": "Body is present",
            "is_read": False,
        },
    )

    assert response.status_code == 400, response.text
    assert "title must not be empty" in response.text


def test_notifications_reject_missing_event_at(client: TestClient):
    user = create_user(client)
    authenticate_as(user["id"])
    contract_fields = notification_contract_fields()
    contract_fields.pop("event_at")

    response = client.post(
        "/notifications",
        json={
            "user_id": user["id"],
            "notification_type": "admin_notice",
            "notification_category": "app",
            "notification_domain": "admin",
            "title": "Missing event time",
            **contract_fields,
            "body": "This should not be accepted.",
            "is_read": False,
        },
    )

    assert response.status_code == 400, response.text
    assert "event_at cannot be null" in response.text


def test_notifications_reject_invalid_source_type(client: TestClient):
    user = create_user(client)
    authenticate_as(user["id"])

    response = client.post(
        "/notifications",
        json={
            "user_id": user["id"],
            "notification_type": "admin_notice",
            "notification_category": "app",
            "notification_domain": "admin",
            "title": "Invalid source",
            **notification_contract_fields(source_type="random"),
            "body": "This should not be accepted.",
            "is_read": False,
        },
    )

    assert response.status_code == 400, response.text
    assert "source_type is not supported" in response.text


def test_notifications_reject_subject_start_without_timezone(client: TestClient):
    user = create_user(client)
    authenticate_as(user["id"])

    response = client.post(
        "/notifications",
        json={
            "user_id": user["id"],
            "notification_type": "admin_notice",
            "notification_category": "app",
            "notification_domain": "admin",
            "title": "Missing subject timezone",
            **notification_contract_fields(
                subject_starts_at=datetime.now(UTC).isoformat(),
            ),
            "body": "This should not be accepted.",
            "is_read": False,
        },
    )

    assert response.status_code == 400, response.text
    assert "subject_timezone is required" in response.text


def test_notifications_reject_action_without_target(client: TestClient):
    user = create_user(client)
    authenticate_as(user["id"])

    response = client.post(
        "/notifications",
        json={
            "user_id": user["id"],
            "notification_type": "admin_notice",
            "notification_category": "app",
            "notification_domain": "admin",
            "title": "Broken action",
            **notification_contract_fields(action_key="view_game"),
            "body": "This should not be accepted.",
            "is_read": False,
        },
    )

    assert response.status_code == 400, response.text
    assert "view_game notifications require related_game_id" in response.text


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
    authenticate_as(user["id"])

    response = client.post(
        "/notifications",
        json={
            "user_id": user["id"],
            "notification_type": "booking_confirmed",
            "notification_category": "game_activity",
            "notification_domain": "game",
            "title": "Booking confirmed",
            **game_notification_contract_fields(second_game),
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


def test_notifications_reject_category_domain_mismatch(client: TestClient):
    user = create_user(client)
    authenticate_as(user["id"])

    response = client.post(
        "/notifications",
        json={
            "user_id": user["id"],
            "notification_type": "admin_notice",
            "notification_category": "app",
            "notification_domain": "game",
            "title": "Mismatch",
            **notification_contract_fields(
                source_type="game",
                subject_label="CI Test Match",
                summary="This should not be categorized as app.",
            ),
            "body": "This should not be categorized as app.",
            "is_read": False,
        },
    )

    assert response.status_code == 400, response.text
    assert "App notifications must use an app notification domain" in response.text


def test_notifications_reject_type_domain_mismatch(client: TestClient):
    user = create_user(client)
    authenticate_as(user["id"])

    response = client.post(
        "/notifications",
        json={
            "user_id": user["id"],
            "notification_type": "sub_request_received",
            "notification_category": "game_activity",
            "notification_domain": "game",
            "title": "Wrong lane",
            **notification_contract_fields(
                source_type="game",
                subject_label="CI Test Match",
                summary="This should be a Need a Sub notification.",
            ),
            "body": "This should be a Need a Sub notification.",
            "is_read": False,
        },
    )

    assert response.status_code == 400, response.text
    assert "Need a Sub notification types" in response.text


def test_notifications_are_scoped_to_owner_unless_admin(client: TestClient):
    owner = create_user(client)
    other_user = create_user(client)
    notification = create_notification(client, owner["id"])

    authenticate_as(other_user["id"])
    get_response = client.get(f"/notifications/{notification['id']}")
    assert get_response.status_code == 404, get_response.text

    patch_response = client.patch(f"/notifications/{notification['id']}/read", json={})
    assert patch_response.status_code == 404, patch_response.text

    list_response = client.get(f"/notifications?user_id={owner['id']}")
    assert list_response.status_code == 403, list_response.text

    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    authenticate_as(admin["id"])

    admin_get_response = client.get(f"/notifications/{notification['id']}")
    assert admin_get_response.status_code == 200, admin_get_response.text

    admin_list_response = client.get(f"/notifications?user_id={owner['id']}")
    assert admin_list_response.status_code == 200, admin_list_response.text
    assert [item["id"] for item in admin_list_response.json()] == [notification["id"]]


def test_notifications_support_need_a_sub_relations(client: TestClient):
    owner = create_user(client)
    requester = create_user(client)
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    sub_post = create_sub_post(client, owner["id"])
    sub_request = create_sub_request(client, requester["id"], sub_post)

    authenticate_as(admin["id"])
    response = client.post(
        "/notifications",
        json={
            "user_id": owner["id"],
            "notification_type": "sub_request_received",
            "notification_category": "game_activity",
            "notification_domain": "need_a_sub",
            "title": "New sub request",
            **need_a_sub_notification_contract_fields(sub_post),
            "body": "A player requested your Need a Sub spot.",
            "actor_user_id": requester["id"],
            "related_sub_post_id": sub_post["id"],
            "related_sub_post_request_id": sub_request["id"],
            "related_sub_post_position_id": sub_post["positions"][0]["id"],
            "is_read": False,
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["notification_category"] == "game_activity"
    assert body["notification_domain"] == "need_a_sub"
    assert body["related_sub_post_id"] == sub_post["id"]
    assert body["related_sub_post_request_id"] == sub_request["id"]
    assert body["related_sub_post_position_id"] == sub_post["positions"][0]["id"]


def test_notifications_reject_mismatched_need_a_sub_relations(client: TestClient):
    owner = create_user(client)
    other_owner = create_user(client)
    requester = create_user(client)
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    sub_post = create_sub_post(client, owner["id"])
    other_sub_post = create_sub_post(client, other_owner["id"])
    sub_request = create_sub_request(client, requester["id"], sub_post)

    authenticate_as(admin["id"])
    response = client.post(
        "/notifications",
        json={
            "user_id": other_owner["id"],
            "notification_type": "sub_request_received",
            "notification_category": "game_activity",
            "notification_domain": "need_a_sub",
            "title": "New sub request",
            **need_a_sub_notification_contract_fields(other_sub_post),
            "body": "A player requested your Need a Sub spot.",
            "actor_user_id": requester["id"],
            "related_sub_post_id": other_sub_post["id"],
            "related_sub_post_request_id": sub_request["id"],
            "related_sub_post_position_id": other_sub_post["positions"][0]["id"],
            "is_read": False,
        },
    )

    assert response.status_code == 400, response.text
    assert (
        "related_sub_post_request_id must belong to related_sub_post_id"
        in response.text
    )
