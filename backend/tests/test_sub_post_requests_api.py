from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi.testclient import TestClient

from backend.tests.helpers import authenticate_as, create_sub_post, create_user


def request_spot(client: TestClient, requester_id: str, post: dict, position_index: int = 0):
    authenticate_as(requester_id)
    return client.post(
        f"/need-a-sub/posts/{post['id']}/requests",
        json={"sub_post_position_id": post["positions"][position_index]["id"]},
    )


def test_sub_post_request_full_confirm_flow_marks_post_filled(client: TestClient):
    owner = create_user(client)
    requester_one = create_user(client)
    requester_two = create_user(client)
    post = create_sub_post(client, owner["id"])

    first_response = request_spot(client, requester_one["id"], post, 0)
    assert first_response.status_code == 201, first_response.text
    first_request = first_response.json()
    assert first_request["request_status"] == "pending"

    second_response = request_spot(client, requester_two["id"], post, 1)
    assert second_response.status_code == 201, second_response.text
    second_request = second_response.json()

    authenticate_as(owner["id"])
    first_accept = client.patch(f"/need-a-sub/requests/{first_request['id']}/accept")
    assert first_accept.status_code == 200, first_accept.text
    assert first_accept.json()["request_status"] == "accepted"
    assert first_accept.json()["confirmation_due_at"] is not None

    second_accept = client.patch(f"/need-a-sub/requests/{second_request['id']}/accept")
    assert second_accept.status_code == 200, second_accept.text

    authenticate_as(requester_one["id"])
    first_confirm = client.patch(f"/need-a-sub/requests/{first_request['id']}/confirm")
    assert first_confirm.status_code == 200, first_confirm.text
    assert first_confirm.json()["request_status"] == "confirmed"

    get_post_before_full = client.get(f"/need-a-sub/posts/{post['id']}")
    assert get_post_before_full.status_code == 200
    assert get_post_before_full.json()["post_status"] == "active"

    authenticate_as(requester_two["id"])
    second_confirm = client.patch(f"/need-a-sub/requests/{second_request['id']}/confirm")
    assert second_confirm.status_code == 200, second_confirm.text

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


def test_sub_post_request_accept_holds_position_capacity(client: TestClient):
    owner = create_user(client)
    requester_one = create_user(client)
    requester_two = create_user(client)
    post = create_sub_post(client, owner["id"])
    first_request = request_spot(client, requester_one["id"], post, 0).json()
    second_request = request_spot(client, requester_two["id"], post, 1).json()

    authenticate_as(owner["id"])
    first_accept = client.patch(f"/need-a-sub/requests/{first_request['id']}/accept")
    assert first_accept.status_code == 200, first_accept.text

    second_same_position_response = client.patch(
        f"/need-a-sub/requests/{second_request['id']}/accept"
    )
    assert second_same_position_response.status_code == 200, second_same_position_response.text

    # Create a third request for the first position through direct DB mutation to
    # validate capacity on the exact row while preserving the one-request-per-post rule.
    third_user = create_user(client)
    other_post = create_sub_post(client, owner["id"])
    third_request = request_spot(client, third_user["id"], other_post, 0).json()
    from backend.database import SessionLocal
    from backend.models import SubPostRequest

    with SessionLocal() as db:
        db_request = db.get(SubPostRequest, UUID(third_request["id"]))
        db_request.sub_post_id = UUID(post["id"])
        db_request.sub_post_position_id = UUID(post["positions"][0]["id"])
        db.commit()

    authenticate_as(owner["id"])
    third_accept = client.patch(f"/need-a-sub/requests/{third_request['id']}/accept")
    assert third_accept.status_code == 400, third_accept.text
    assert "already full" in third_accept.text


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
                "position_label": "any",
                "player_group": "men",
                "spots_needed": 2,
                "sort_order": 0,
            },
            {
                "position_label": "any",
                "player_group": "women",
                "spots_needed": 2,
                "sort_order": 1,
            },
        ],
    )
    first_request = request_spot(client, first["id"], post, 0).json()
    second_request = request_spot(client, second["id"], post, 0).json()

    authenticate_as(owner["id"])
    client.patch(f"/need-a-sub/requests/{first_request['id']}/accept")
    client.patch(f"/need-a-sub/requests/{second_request['id']}/accept")
    authenticate_as(first["id"])
    client.patch(f"/need-a-sub/requests/{first_request['id']}/confirm")
    authenticate_as(second["id"])
    client.patch(f"/need-a-sub/requests/{second_request['id']}/confirm")

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
    authenticate_as(first["id"])
    client.patch(f"/need-a-sub/requests/{first_request['id']}/confirm")
    authenticate_as(second["id"])
    client.patch(f"/need-a-sub/requests/{second_request['id']}/confirm")
    assert client.get(f"/need-a-sub/posts/{post['id']}").json()["post_status"] == "filled"

    cancel_response = client.patch(f"/need-a-sub/requests/{second_request['id']}/cancel")
    assert cancel_response.status_code == 200, cancel_response.text
    assert cancel_response.json()["request_status"] == "canceled_by_player"
    assert client.get(f"/need-a-sub/posts/{post['id']}").json()["post_status"] == "active"


def test_sub_post_request_no_show_requires_game_end(client: TestClient):
    owner = create_user(client)
    requester = create_user(client)
    post = create_sub_post(client, owner["id"])
    request = request_spot(client, requester["id"], post, 0).json()
    authenticate_as(owner["id"])
    client.patch(f"/need-a-sub/requests/{request['id']}/accept")
    authenticate_as(requester["id"])
    client.patch(f"/need-a-sub/requests/{request['id']}/confirm")

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
