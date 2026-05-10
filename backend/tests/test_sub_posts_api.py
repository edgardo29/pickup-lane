from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from backend.tests.helpers import (
    authenticate_as,
    build_sub_post_payload,
    create_sub_post,
    create_user,
    set_user_role,
)


def test_sub_posts_create_get_list_cancel_and_remove(client: TestClient):
    owner = create_user(client)
    admin = create_user(client)
    set_user_role(admin["id"], "admin")

    post = create_sub_post(client, owner["id"])
    assert post["owner_user_id"] == owner["id"]
    assert post["post_status"] == "active"
    assert post["expires_at"] == post["starts_at"]
    assert len(post["positions"]) == 2

    get_response = client.get(f"/need-a-sub/posts/{post['id']}")
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["id"] == post["id"]

    list_response = client.get("/need-a-sub/posts?city=Chicago&state=IL")
    assert list_response.status_code == 200, list_response.text
    assert any(item["id"] == post["id"] for item in list_response.json())

    authenticate_as(owner["id"])
    cancel_response = client.patch(
        f"/need-a-sub/posts/{post['id']}/cancel",
        json={"cancel_reason": "Weather issue."},
    )
    assert cancel_response.status_code == 200, cancel_response.text
    assert cancel_response.json()["post_status"] == "canceled"
    assert cancel_response.json()["canceled_at"] is not None

    authenticate_as(admin["id"])
    remove_response = client.patch(
        f"/need-a-sub/posts/{post['id']}/remove",
        json={"remove_reason": "Moderation cleanup."},
    )
    assert remove_response.status_code == 200, remove_response.text
    assert remove_response.json()["post_status"] == "removed"


def test_sub_posts_create_requires_auth(client: TestClient):
    response = client.post("/need-a-sub/posts", json=build_sub_post_payload())

    assert response.status_code == 401, response.text
    assert "Missing authorization header" in response.text


def test_sub_posts_reject_invalid_position_total(client: TestClient):
    owner = create_user(client)
    authenticate_as(owner["id"])

    payload = build_sub_post_payload(subs_needed=3)
    response = client.post("/need-a-sub/posts", json=payload)

    assert response.status_code == 400, response.text
    assert "add up to subs_needed" in response.text


def test_sub_posts_reject_invalid_group_position_combination(client: TestClient):
    owner = create_user(client)
    authenticate_as(owner["id"])

    payload = build_sub_post_payload(
        game_player_group="men",
        subs_needed=1,
        positions=[
            {
                "position_label": "field_player",
                "player_group": "women",
                "spots_needed": 1,
            }
        ],
    )
    response = client.post("/need-a-sub/posts", json=payload)

    assert response.status_code == 400, response.text
    assert "not compatible" in response.text


def test_sub_posts_reject_past_start_time(client: TestClient):
    owner = create_user(client)
    authenticate_as(owner["id"])
    starts_at = datetime.now(UTC) - timedelta(days=1)
    ends_at = starts_at + timedelta(hours=2)

    response = client.post(
        "/need-a-sub/posts",
        json=build_sub_post_payload(
            starts_at=starts_at.isoformat(),
            ends_at=ends_at.isoformat(),
        ),
    )

    assert response.status_code == 400, response.text
    assert "starts_at must be in the future" in response.text


def test_sub_posts_owner_can_edit_post_without_requests(client: TestClient):
    owner = create_user(client)
    post = create_sub_post(client, owner["id"])
    authenticate_as(owner["id"])

    payload = build_sub_post_payload(
        format_label="11v11",
        skill_level="advanced",
        subs_needed=1,
        positions=[
            {
                "position_label": "goalkeeper",
                "player_group": "open",
                "spots_needed": 1,
            }
        ],
    )
    response = client.patch(f"/need-a-sub/posts/{post['id']}", json=payload)

    assert response.status_code == 200, response.text
    assert response.json()["format_label"] == "11v11"
    assert response.json()["skill_level"] == "advanced"
    assert response.json()["subs_needed"] == 1
    assert response.json()["positions"][0]["position_label"] == "goalkeeper"


def test_sub_posts_edit_blocks_removing_requirement_with_active_requests(client: TestClient):
    owner = create_user(client)
    requester = create_user(client)
    post = create_sub_post(client, owner["id"])

    authenticate_as(requester["id"])
    request_response = client.post(
        f"/need-a-sub/posts/{post['id']}/requests",
        json={"sub_post_position_id": post["positions"][0]["id"]},
    )
    assert request_response.status_code == 201, request_response.text

    authenticate_as(owner["id"])
    payload = build_sub_post_payload(
        subs_needed=1,
        positions=[
            {
                "position_label": "field_player",
                "player_group": "women",
                "spots_needed": 1,
            }
        ],
    )
    response = client.patch(f"/need-a-sub/posts/{post['id']}", json=payload)

    assert response.status_code == 400, response.text
    assert "cannot be removed or changed" in response.text


def test_sub_posts_edit_allows_increasing_requested_requirement(client: TestClient):
    owner = create_user(client)
    requester = create_user(client)
    post = create_sub_post(client, owner["id"])

    authenticate_as(requester["id"])
    request_response = client.post(
        f"/need-a-sub/posts/{post['id']}/requests",
        json={"sub_post_position_id": post["positions"][0]["id"]},
    )
    assert request_response.status_code == 201, request_response.text

    authenticate_as(owner["id"])
    payload = build_sub_post_payload(
        subs_needed=3,
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
                "spots_needed": 1,
                "sort_order": 1,
            },
        ],
    )
    response = client.patch(f"/need-a-sub/posts/{post['id']}", json=payload)

    assert response.status_code == 200, response.text
    assert response.json()["subs_needed"] == 3


def test_sub_posts_expiration_service_expires_posts_and_open_requests(client: TestClient):
    from uuid import UUID

    from backend.database import SessionLocal
    from backend.models import SubPost, SubPostRequest
    from backend.services.need_a_sub_service import expire_due_posts_and_requests

    owner = create_user(client)
    requester = create_user(client)
    post = create_sub_post(client, owner["id"])

    authenticate_as(requester["id"])
    request_response = client.post(
        f"/need-a-sub/posts/{post['id']}/requests",
        json={"sub_post_position_id": post["positions"][0]["id"]},
    )
    assert request_response.status_code == 201, request_response.text

    with SessionLocal() as db:
        db_post = db.get(SubPost, UUID(post["id"]))
        db_post.starts_at = datetime.now(UTC) - timedelta(minutes=5)
        db_post.ends_at = datetime.now(UTC) + timedelta(minutes=55)
        db_post.expires_at = db_post.starts_at
        db.commit()

        counts = expire_due_posts_and_requests(db)
        db.commit()

        db.refresh(db_post)
        db_request = db.get(SubPostRequest, UUID(request_response.json()["id"]))

    assert counts == {"posts_expired": 1, "requests_expired": 1}
    assert db_post.post_status == "expired"
    assert db_request.request_status == "expired"
