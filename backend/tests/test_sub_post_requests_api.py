from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi.testclient import TestClient

from backend.services.need_a_sub_service import MAX_WAITLIST_REQUESTS_PER_POST
from backend.tests.helpers import authenticate_as, create_sub_post, create_user


def request_spot(client: TestClient, requester_id: str, post: dict, position_index: int = 0):
    authenticate_as(requester_id)
    return client.post(
        f"/need-a-sub/posts/{post['id']}/requests",
        json={"sub_post_position_id": post["positions"][position_index]["id"]},
    )


def list_need_a_sub_notifications(client: TestClient, user_id: str) -> list[dict]:
    authenticate_as(user_id)
    response = client.get("/notifications/me?notification_domain=need_a_sub")

    assert response.status_code == 200, response.text
    return response.json()


def notification_types(notifications: list[dict]) -> set[str]:
    return {notification["notification_type"] for notification in notifications}


def test_sub_post_request_owner_accept_marks_confirmed_and_filled(client: TestClient):
    owner = create_user(client)
    requester_one = create_user(client)
    requester_two = create_user(client)
    post = create_sub_post(client, owner["id"])

    first_response = request_spot(client, requester_one["id"], post, 0)
    assert first_response.status_code == 201, first_response.text
    first_request = first_response.json()
    assert first_request["request_status"] == "pending"
    owner_notifications = list_need_a_sub_notifications(client, owner["id"])
    assert owner_notifications[0]["notification_type"] == "sub_request_received"
    assert owner_notifications[0]["actor_user_id"] == requester_one["id"]
    assert owner_notifications[0]["related_sub_post_id"] == post["id"]
    assert owner_notifications[0]["related_sub_post_request_id"] == first_request["id"]

    second_response = request_spot(client, requester_two["id"], post, 1)
    assert second_response.status_code == 201, second_response.text
    second_request = second_response.json()

    authenticate_as(owner["id"])
    first_accept = client.patch(f"/need-a-sub/requests/{first_request['id']}/accept")
    assert first_accept.status_code == 200, first_accept.text
    assert first_accept.json()["request_status"] == "confirmed"
    assert first_accept.json()["confirmed_at"] is not None
    requester_notifications = list_need_a_sub_notifications(
        client,
        requester_one["id"],
    )
    assert "sub_request_confirmed" in notification_types(requester_notifications)

    get_post_before_full = client.get(f"/need-a-sub/posts/{post['id']}")
    assert get_post_before_full.status_code == 200
    assert get_post_before_full.json()["post_status"] == "active"

    authenticate_as(owner["id"])
    second_accept = client.patch(f"/need-a-sub/requests/{second_request['id']}/accept")
    assert second_accept.status_code == 200, second_accept.text

    get_post_after_full = client.get(f"/need-a-sub/posts/{post['id']}")
    assert get_post_after_full.status_code == 200
    assert get_post_after_full.json()["post_status"] == "filled"
    assert get_post_after_full.json()["confirmed_count"] == 2


def test_sub_post_request_blocks_owner_and_duplicate_requests(client: TestClient):
    owner = create_user(client)
    requester = create_user(client)
    post = create_sub_post(client, owner["id"])

    owner_response = request_spot(client, owner["id"], post)
    assert owner_response.status_code == 400, owner_response.text
    assert "Owners cannot request" in owner_response.text

    first_response = request_spot(client, requester["id"], post)
    assert first_response.status_code == 201, first_response.text

    duplicate_response = request_spot(client, requester["id"], post, 1)
    assert duplicate_response.status_code == 409, duplicate_response.text


def test_sub_post_request_allows_new_request_after_player_cancel(client: TestClient):
    owner = create_user(client)
    requester = create_user(client)
    post = create_sub_post(client, owner["id"])
    first_request = request_spot(client, requester["id"], post).json()

    cancel_response = client.patch(f"/need-a-sub/requests/{first_request['id']}/cancel")
    assert cancel_response.status_code == 200, cancel_response.text
    assert cancel_response.json()["request_status"] == "canceled_by_player"
    owner_notifications = list_need_a_sub_notifications(client, owner["id"])
    assert "sub_request_canceled_by_player" in notification_types(owner_notifications)

    new_response = request_spot(client, requester["id"], post, 1)
    assert new_response.status_code == 201, new_response.text
    assert new_response.json()["id"] != first_request["id"]


def test_sub_post_request_allows_new_request_after_owner_cancel(client: TestClient):
    owner = create_user(client)
    requester = create_user(client)
    post = create_sub_post(client, owner["id"])
    first_request = request_spot(client, requester["id"], post).json()

    authenticate_as(owner["id"])
    assert client.patch(f"/need-a-sub/requests/{first_request['id']}/accept").status_code == 200
    cancel_response = client.patch(f"/need-a-sub/requests/{first_request['id']}/cancel-by-owner", json={})
    assert cancel_response.status_code == 200, cancel_response.text
    assert cancel_response.json()["request_status"] == "canceled_by_owner"
    requester_notifications = list_need_a_sub_notifications(client, requester["id"])
    assert {
        "sub_request_confirmed",
        "sub_request_canceled_by_owner",
    } <= notification_types(requester_notifications)

    new_response = request_spot(client, requester["id"], post, 1)
    assert new_response.status_code == 201, new_response.text
    assert new_response.json()["id"] != first_request["id"]


def test_sub_post_request_auto_waitlists_when_position_queue_is_full(client: TestClient):
    owner = create_user(client)
    requester_one = create_user(client)
    requester_two = create_user(client)
    post = create_sub_post(client, owner["id"])
    first_request = request_spot(client, requester_one["id"], post, 0).json()
    second_response = request_spot(client, requester_two["id"], post, 0)
    assert second_response.status_code == 201, second_response.text
    second_request = second_response.json()

    assert first_request["request_status"] == "pending"
    assert second_request["request_status"] == "sub_waitlist"
    owner_notifications = list_need_a_sub_notifications(client, owner["id"])
    assert notification_types(owner_notifications) == {"sub_request_received"}

    authenticate_as(requester_two["id"])
    my_requests = client.get("/need-a-sub/my-requests")
    assert my_requests.status_code == 200, my_requests.text
    assert my_requests.json()[0]["waitlist_ahead_count"] == 0

    post_with_counts = client.get(f"/need-a-sub/posts/{post['id']}")
    assert post_with_counts.status_code == 200
    first_position = post_with_counts.json()["positions"][0]
    assert first_position["pending_count"] == 1
    assert first_position["sub_waitlist_count"] == 1

    authenticate_as(owner["id"])
    decline_response = client.patch(f"/need-a-sub/requests/{first_request['id']}/decline", json={})
    assert decline_response.status_code == 200, decline_response.text
    assert decline_response.json()["request_status"] == "declined"

    waitlist_after_decline = client.get(f"/need-a-sub/posts/{post['id']}/requests")
    promoted_request = next(
        row for row in waitlist_after_decline.json() if row["id"] == second_request["id"]
    )
    assert promoted_request["request_status"] == "pending"
    assert promoted_request["requester_display_name"] == "Test User"
    assert promoted_request["requester_initials"] == "TU"
    requester_one_notifications = list_need_a_sub_notifications(
        client,
        requester_one["id"],
    )
    assert "sub_request_declined" in notification_types(requester_one_notifications)
    requester_two_notifications = list_need_a_sub_notifications(
        client,
        requester_two["id"],
    )
    assert "sub_waitlist_promoted_to_pending" in notification_types(
        requester_two_notifications
    )


def test_sub_post_request_blocks_when_post_waitlist_is_full(client: TestClient):
    owner = create_user(client)
    first_requester = create_user(client)
    post = create_sub_post(client, owner["id"])
    first_response = request_spot(client, first_requester["id"], post, 0)
    assert first_response.status_code == 201, first_response.text
    assert first_response.json()["request_status"] == "pending"

    for _ in range(MAX_WAITLIST_REQUESTS_PER_POST):
        requester = create_user(client)
        waitlist_response = request_spot(client, requester["id"], post, 0)
        assert waitlist_response.status_code == 201, waitlist_response.text
        assert waitlist_response.json()["request_status"] == "sub_waitlist"

    blocked_requester = create_user(client)
    blocked_response = request_spot(client, blocked_requester["id"], post, 0)
    assert blocked_response.status_code == 400, blocked_response.text
    assert "waitlist is full" in blocked_response.text


def test_sub_post_request_filled_post_accepts_new_waitlist_requests(client: TestClient):
    owner = create_user(client)
    first = create_user(client)
    second = create_user(client)
    waitlisted = create_user(client)
    post = create_sub_post(client, owner["id"])
    first_request = request_spot(client, first["id"], post, 0).json()
    second_request = request_spot(client, second["id"], post, 1).json()

    authenticate_as(owner["id"])
    assert client.patch(f"/need-a-sub/requests/{first_request['id']}/accept").status_code == 200
    assert client.patch(f"/need-a-sub/requests/{second_request['id']}/accept").status_code == 200
    filled_post = client.get(f"/need-a-sub/posts/{post['id']}")
    assert filled_post.status_code == 200
    assert filled_post.json()["post_status"] == "filled"

    waitlist_response = request_spot(client, waitlisted["id"], post, 0)
    assert waitlist_response.status_code == 201, waitlist_response.text
    assert waitlist_response.json()["request_status"] == "sub_waitlist"


def test_sub_post_request_create_rejects_canceled_post(client: TestClient):
    owner = create_user(client)
    requester = create_user(client)
    post = create_sub_post(client, owner["id"])

    authenticate_as(owner["id"])
    cancel_response = client.patch(
        f"/need-a-sub/posts/{post['id']}/cancel",
        json={"cancel_reason": "No longer needed."},
    )
    assert cancel_response.status_code == 200, cancel_response.text

    response = request_spot(client, requester["id"], post, 0)

    assert response.status_code == 400, response.text
    assert "Requests can only be created for open posts" in response.text


def test_sub_post_request_actions_reject_canceled_post_even_with_stale_request(
    client: TestClient,
):
    from backend.database import SessionLocal
    from backend.models import SubPost

    owner = create_user(client)
    requester = create_user(client)
    post = create_sub_post(client, owner["id"])
    sub_request = request_spot(client, requester["id"], post, 0).json()

    with SessionLocal() as db:
        db_post = db.get(SubPost, UUID(post["id"]))
        db_post.post_status = "canceled"
        db_post.canceled_at = datetime.now(UTC)
        db_post.canceled_by_user_id = UUID(owner["id"])
        db.commit()

    authenticate_as(owner["id"])
    accept_response = client.patch(f"/need-a-sub/requests/{sub_request['id']}/accept")
    assert accept_response.status_code == 400, accept_response.text
    assert "not accepting requests" in accept_response.text

    decline_response = client.patch(
        f"/need-a-sub/requests/{sub_request['id']}/decline",
        json={},
    )
    assert decline_response.status_code == 400, decline_response.text
    assert "Only active or filled posts can be reviewed" in decline_response.text

    owner_cancel_response = client.patch(
        f"/need-a-sub/requests/{sub_request['id']}/cancel-by-owner",
        json={},
    )
    assert owner_cancel_response.status_code == 400, owner_cancel_response.text
    assert "Only active or filled posts can be reviewed" in owner_cancel_response.text

    authenticate_as(requester["id"])
    requester_cancel_response = client.patch(
        f"/need-a-sub/requests/{sub_request['id']}/cancel"
    )
    assert requester_cancel_response.status_code == 400, requester_cancel_response.text
    assert "Only active or filled posts can be updated" in requester_cancel_response.text


def test_sub_post_request_wrong_position_does_not_fill_post(client: TestClient):
    owner = create_user(client)
    first = create_user(client)
    second = create_user(client)
    post = create_sub_post(
        client,
        owner["id"],
        subs_needed=4,
        positions=[
            {
                "position_label": "field_player",
                "player_group": "men",
                "spots_needed": 2,
                "sort_order": 0,
            },
            {
                "position_label": "field_player",
                "player_group": "women",
                "spots_needed": 2,
                "sort_order": 1,
            },
        ],
    )
    first_request = request_spot(client, first["id"], post, 0).json()
    second_request = request_spot(client, second["id"], post, 0).json()

    authenticate_as(owner["id"])
    assert client.patch(f"/need-a-sub/requests/{first_request['id']}/accept").status_code == 200
    assert client.patch(f"/need-a-sub/requests/{second_request['id']}/accept").status_code == 200

    response = client.get(f"/need-a-sub/posts/{post['id']}")
    assert response.status_code == 200
    assert response.json()["confirmed_count"] == 2
    assert response.json()["post_status"] == "active"


def test_sub_post_request_cancel_reopens_filled_post(client: TestClient):
    owner = create_user(client)
    first = create_user(client)
    second = create_user(client)
    post = create_sub_post(client, owner["id"])
    first_request = request_spot(client, first["id"], post, 0).json()
    second_request = request_spot(client, second["id"], post, 1).json()

    authenticate_as(owner["id"])
    client.patch(f"/need-a-sub/requests/{first_request['id']}/accept")
    client.patch(f"/need-a-sub/requests/{second_request['id']}/accept")
    assert client.get(f"/need-a-sub/posts/{post['id']}").json()["post_status"] == "filled"

    authenticate_as(second["id"])
    cancel_response = client.patch(f"/need-a-sub/requests/{second_request['id']}/cancel")
    assert cancel_response.status_code == 200, cancel_response.text
    assert cancel_response.json()["request_status"] == "canceled_by_player"
    assert client.get(f"/need-a-sub/posts/{post['id']}").json()["post_status"] == "active"


def test_sub_post_request_create_after_start_expires_and_blocks_post(client: TestClient):
    from backend.database import SessionLocal
    from backend.models import SubPost

    owner = create_user(client)
    requester = create_user(client)
    post = create_sub_post(client, owner["id"])

    with SessionLocal() as db:
        db_post = db.get(SubPost, UUID(post["id"]))
        db_post.starts_at = datetime.now(UTC) - timedelta(minutes=5)
        db_post.ends_at = datetime.now(UTC) + timedelta(minutes=55)
        db_post.expires_at = db_post.starts_at
        db.commit()

    blocked_response = request_spot(client, requester["id"], post, 0)
    assert blocked_response.status_code == 400, blocked_response.text

    with SessionLocal() as db:
        db_post = db.get(SubPost, UUID(post["id"]))
        assert db_post.post_status == "expired"


def test_sub_post_request_confirmed_player_and_owner_actions_after_start_are_blocked(client: TestClient):
    from backend.database import SessionLocal
    from backend.models import SubPost

    owner = create_user(client)
    requester = create_user(client)
    post = create_sub_post(client, owner["id"])
    request = request_spot(client, requester["id"], post, 0).json()

    authenticate_as(owner["id"])
    accept_response = client.patch(f"/need-a-sub/requests/{request['id']}/accept")
    assert accept_response.status_code == 200, accept_response.text

    with SessionLocal() as db:
        db_post = db.get(SubPost, UUID(post["id"]))
        db_post.starts_at = datetime.now(UTC) - timedelta(minutes=5)
        db_post.ends_at = datetime.now(UTC) + timedelta(minutes=55)
        db_post.expires_at = db_post.starts_at
        db.commit()

    authenticate_as(requester["id"])
    cancel_response = client.patch(f"/need-a-sub/requests/{request['id']}/cancel")
    assert cancel_response.status_code == 400, cancel_response.text
    assert "after the game starts" in cancel_response.text

    authenticate_as(owner["id"])
    owner_cancel_response = client.patch(
        f"/need-a-sub/requests/{request['id']}/cancel-by-owner",
        json={},
    )
    assert owner_cancel_response.status_code == 400, owner_cancel_response.text
    assert "after the game starts" in owner_cancel_response.text


def test_sub_post_request_no_show_requires_game_end(client: TestClient):
    owner = create_user(client)
    requester = create_user(client)
    post = create_sub_post(client, owner["id"])
    request = request_spot(client, requester["id"], post, 0).json()
    authenticate_as(owner["id"])
    client.patch(f"/need-a-sub/requests/{request['id']}/accept")

    authenticate_as(owner["id"])
    early_response = client.patch(
        f"/need-a-sub/requests/{request['id']}/no-show",
        json={"reason": "Did not show."},
    )
    assert early_response.status_code == 400, early_response.text

    from backend.database import SessionLocal
    from backend.models import SubPost

    with SessionLocal() as db:
        db_post = db.get(SubPost, UUID(post["id"]))
        db_post.starts_at = datetime.now(UTC) - timedelta(hours=2)
        db_post.ends_at = datetime.now(UTC) - timedelta(minutes=1)
        db_post.expires_at = db_post.starts_at
        db.commit()

    late_response = client.patch(
        f"/need-a-sub/requests/{request['id']}/no-show",
        json={"reason": "Did not show."},
    )
    assert late_response.status_code == 200, late_response.text
    assert late_response.json()["request_status"] == "no_show_reported"
