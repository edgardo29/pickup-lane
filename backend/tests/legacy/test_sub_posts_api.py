from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from backend.tests.helpers import (
    authenticate_as,
    build_sub_post_payload,
    create_sub_post,
    create_user,
    set_user_account_status,
    set_user_role,
    unique_suffix,
)


def authenticate_optional_as(user_id: str) -> None:
    from uuid import UUID

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


def request_sub_spot(
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


def list_need_a_sub_notifications(client: TestClient, user_id: str) -> list[dict]:
    authenticate_as(user_id)
    response = client.get("/notifications/me?notification_domain=need_a_sub")

    assert response.status_code == 200, response.text
    return response.json()


def notification_types(notifications: list[dict]) -> set[str]:
    return {notification["notification_type"] for notification in notifications}


def parse_iso_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def sub_post_local_date(post: dict) -> str:
    return (
        parse_iso_datetime(post["starts_at"])
        .astimezone(ZoneInfo(post["timezone"]))
        .date()
        .isoformat()
    )


def test_need_a_sub_post_routes_reject_suspended_user(client: TestClient):
    user = create_user(client)
    set_user_account_status(user["id"], "suspended")
    authenticate_as(user["id"])
    post_id = "00000000-0000-4000-8000-000000000001"

    responses = [
        client.post("/need-a-sub/posts", json=build_sub_post_payload()),
        client.get("/need-a-sub/posts/mine"),
        client.patch(
            f"/need-a-sub/posts/{post_id}",
            json=build_sub_post_payload(format_label="7v7"),
        ),
        client.patch(
            f"/need-a-sub/posts/{post_id}/cancel",
            json={"cancel_reason": "Cannot make it."},
        ),
    ]

    for response in responses:
        assert response.status_code == 403, response.text
        assert response.json()["detail"] == "Active account required."


def test_sub_posts_create_get_list_cancel_and_remove(client: TestClient):
    owner = create_user(client)
    admin = create_user(client)
    set_user_role(admin["id"], "admin")

    post = create_sub_post(client, owner["id"])
    assert post["owner_user_id"] == owner["id"]
    assert post["post_status"] == "active"
    assert post["environment_type"] == "outdoor"
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
    assert cancel_response.json()["post_status"] == "cancelled"
    assert cancel_response.json()["canceled_at"] is not None

    list_after_cancel = client.get("/need-a-sub/posts?city=Chicago&state=IL")
    assert list_after_cancel.status_code == 200, list_after_cancel.text
    assert post["id"] not in {item["id"] for item in list_after_cancel.json()}

    mine_after_cancel = client.get("/need-a-sub/posts/mine")
    assert mine_after_cancel.status_code == 200, mine_after_cancel.text
    assert post["id"] not in {item["id"] for item in mine_after_cancel.json()}

    detail_after_cancel = client.get(f"/need-a-sub/posts/{post['id']}")
    assert detail_after_cancel.status_code == 404, detail_after_cancel.text

    authenticate_optional_as(owner["id"])
    owner_detail_after_cancel = client.get(f"/need-a-sub/posts/{post['id']}")
    assert owner_detail_after_cancel.status_code == 404, owner_detail_after_cancel.text

    history_response = client.get(f"/need-a-sub/posts/{post['id']}/status-history")
    assert history_response.status_code == 200, history_response.text
    status_history = history_response.json()
    assert [row["new_status"] for row in status_history] == ["active", "cancelled"]
    assert status_history[-1]["change_source"] == "owner"
    assert status_history[-1]["change_reason"] == "Weather issue."

    authenticate_as(admin["id"])
    remove_response = client.patch(
        f"/need-a-sub/posts/{post['id']}/remove",
        json={
            "remove_reason": "Moderation cleanup.",
            "idempotency_key": f"remove-sub-post-{unique_suffix()}",
        },
    )
    assert remove_response.status_code == 200, remove_response.text
    assert remove_response.json()["post_status"] == "removed"

    audit_response = client.get(f"/admin/actions?target_sub_post_id={post['id']}")
    assert audit_response.status_code == 200, audit_response.text
    remove_actions = [
        action
        for action in audit_response.json()
        if action["action_type"] == "remove_sub_post"
    ]
    assert len(remove_actions) == 1
    audit_action = remove_actions[0]
    assert audit_action["target_user_id"] == owner["id"]
    assert audit_action["target_sub_post_id"] == post["id"]
    assert audit_action["reason"] == "Moderation cleanup."
    audit_metadata = audit_action["metadata"]
    assert {
        key: audit_metadata[key]
        for key in ("source", "old_status", "new_status", "removed_by")
    } == {
        "source": "need_a_sub",
        "old_status": "cancelled",
        "new_status": "removed",
        "removed_by": "admin",
    }
    assert audit_metadata["closed_request_ids"] == []
    assert len(audit_metadata["notice_ids"]) == 1


def test_sub_post_cards_cursor_paginates_and_returns_counts(client: TestClient):
    owners = [create_user(client) for _ in range(3)]
    requester = create_user(client)
    base_start = (
        datetime.now(UTC)
        .replace(hour=18, minute=0, second=0, microsecond=0)
        + timedelta(days=7)
    )

    posts: list[dict] = []
    for index, owner in enumerate(owners):
        starts_at = base_start + timedelta(hours=index)
        post = create_sub_post(
            client,
            owner["id"],
            location_name=f"Card Field {index + 1}",
            starts_at=starts_at.isoformat(),
            ends_at=(starts_at + timedelta(hours=2)).isoformat(),
        )
        posts.append(post)

    request_sub_spot(client, requester["id"], posts[0])

    starts_on = sub_post_local_date(posts[0])
    first_page = client.get(
        "/need-a-sub/posts/cards",
        params={"view": "all", "starts_on": starts_on, "limit": 2},
    )

    assert first_page.status_code == 200, first_page.text
    first_body = first_page.json()
    assert first_body["limit"] == 2
    assert first_body["has_more"] is True
    assert first_body["next_cursor"]
    assert [post["id"] for post in first_body["posts"]] == [
        posts[0]["id"],
        posts[1]["id"],
    ]
    assert first_body["posts"][0]["pending_count"] == 1
    assert first_body["posts"][0]["positions"][0]["pending_count"] == 1

    second_page = client.get(
        "/need-a-sub/posts/cards",
        params={
            "view": "all",
            "starts_on": starts_on,
            "limit": 2,
            "cursor": first_body["next_cursor"],
        },
    )
    assert second_page.status_code == 200, second_page.text
    second_body = second_page.json()
    assert [post["id"] for post in second_body["posts"]] == [posts[2]["id"]]
    assert second_body["has_more"] is False
    assert second_body["next_cursor"] is None

    authenticate_optional_as(owners[0]["id"])
    mismatch_response = client.get(
        "/need-a-sub/posts/cards",
        params={
            "view": "mine",
            "starts_on": starts_on,
            "cursor": first_body["next_cursor"],
        },
    )
    assert mismatch_response.status_code == 400, mismatch_response.text
    assert "cursor does not match" in mismatch_response.text


def test_sub_post_cards_mine_filters_owner_and_caps_limit(client: TestClient):
    owner = create_user(client)
    other_owner = create_user(client)
    base_start = (
        datetime.now(UTC)
        .replace(hour=18, minute=0, second=0, microsecond=0)
        + timedelta(days=7)
    )
    owner_post = create_sub_post(
        client,
        owner["id"],
        starts_at=base_start.isoformat(),
        ends_at=(base_start + timedelta(hours=2)).isoformat(),
    )
    create_sub_post(
        client,
        other_owner["id"],
        location_name="Other Owner Field",
        starts_at=(base_start + timedelta(hours=1)).isoformat(),
        ends_at=(base_start + timedelta(hours=3)).isoformat(),
    )

    authenticate_optional_as(owner["id"])
    response = client.get(
        "/need-a-sub/posts/cards",
        params={
            "view": "mine",
            "starts_on": sub_post_local_date(owner_post),
            "limit": 500,
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["limit"] == 100
    assert [post["id"] for post in body["posts"]] == [owner_post["id"]]


def test_sub_posts_cancel_cancels_active_requests_and_blocks_review(client: TestClient):
    owner = create_user(client)
    pending_player = create_user(client)
    confirmed_player = create_user(client)
    waitlisted_player = create_user(client)
    post = create_sub_post(client, owner["id"])

    pending_request = request_sub_spot(client, pending_player["id"], post, 0)
    waitlisted_request = request_sub_spot(client, waitlisted_player["id"], post, 0)
    confirmed_request = request_sub_spot(client, confirmed_player["id"], post, 1)

    authenticate_as(owner["id"])
    accept_response = client.patch(f"/need-a-sub/requests/{confirmed_request['id']}/accept")
    assert accept_response.status_code == 200, accept_response.text

    cancel_response = client.patch(
        f"/need-a-sub/posts/{post['id']}/cancel",
        json={"cancel_reason": "League changed schedule."},
    )
    assert cancel_response.status_code == 200, cancel_response.text

    review_response = client.get(f"/need-a-sub/posts/{post['id']}/requests")
    assert review_response.status_code == 400, review_response.text
    assert "Only active posts can be reviewed" in review_response.text

    for player, sub_request in (
        (pending_player, pending_request),
        (confirmed_player, confirmed_request),
        (waitlisted_player, waitlisted_request),
    ):
        authenticate_as(player["id"])
        my_requests_response = client.get("/need-a-sub/my-requests")
        assert my_requests_response.status_code == 200, my_requests_response.text
        requests_by_id = {
            request["id"]: request for request in my_requests_response.json()
        }
        assert requests_by_id[sub_request["id"]]["request_status"] == "canceled_by_owner"
        player_notifications = list_need_a_sub_notifications(client, player["id"])
        assert "sub_post_canceled" in notification_types(player_notifications)


def test_sub_posts_cancel_rejects_non_owner_and_second_cancel(client: TestClient):
    owner = create_user(client)
    other_user = create_user(client)
    post = create_sub_post(client, owner["id"])

    authenticate_as(other_user["id"])
    non_owner_response = client.patch(
        f"/need-a-sub/posts/{post['id']}/cancel",
        json={"cancel_reason": "Not mine."},
    )
    assert non_owner_response.status_code == 403, non_owner_response.text

    authenticate_as(owner["id"])
    first_cancel = client.patch(
        f"/need-a-sub/posts/{post['id']}/cancel",
        json={"cancel_reason": "No longer needed."},
    )
    assert first_cancel.status_code == 200, first_cancel.text

    second_cancel = client.patch(
        f"/need-a-sub/posts/{post['id']}/cancel",
        json={"cancel_reason": "Again."},
    )
    assert second_cancel.status_code == 400, second_cancel.text
    assert "Only active posts can be cancelled" in second_cancel.text


def test_sub_posts_cancelled_post_cannot_be_edited(client: TestClient):
    owner = create_user(client)
    post = create_sub_post(client, owner["id"])

    authenticate_as(owner["id"])
    cancel_response = client.patch(
        f"/need-a-sub/posts/{post['id']}/cancel",
        json={"cancel_reason": "No longer needed."},
    )
    assert cancel_response.status_code == 200, cancel_response.text

    edit_response = client.patch(
        f"/need-a-sub/posts/{post['id']}",
        json=build_sub_post_payload(format_label="3v3"),
    )
    assert edit_response.status_code == 400, edit_response.text
    assert "Only active posts can be edited" in edit_response.text


def test_sub_posts_cancel_notifies_active_requesters_and_resolves_owner_row(
    client: TestClient,
):
    owner = create_user(client)
    pending_player = create_user(client)
    waitlisted_player = create_user(client)
    confirmed_player = create_user(client)
    declined_player = create_user(client)
    post = create_sub_post(client, owner["id"])

    pending_request = request_sub_spot(client, pending_player["id"], post, 0)
    waitlisted_request = request_sub_spot(client, waitlisted_player["id"], post, 0)
    confirmed_request = request_sub_spot(client, confirmed_player["id"], post, 1)
    declined_request = request_sub_spot(client, declined_player["id"], post, 1)
    assert pending_request["request_status"] == "pending"
    assert waitlisted_request["request_status"] == "sub_waitlist"

    authenticate_as(owner["id"])
    accept_response = client.patch(
        f"/need-a-sub/requests/{confirmed_request['id']}/accept"
    )
    assert accept_response.status_code == 200, accept_response.text
    decline_response = client.patch(
        f"/need-a-sub/requests/{declined_request['id']}/decline",
        json={},
    )
    assert decline_response.status_code == 200, decline_response.text

    cancel_response = client.patch(
        f"/need-a-sub/posts/{post['id']}/cancel",
        json={"cancel_reason": "Weather issue."},
    )
    assert cancel_response.status_code == 200, cancel_response.text

    owner_notifications = list_need_a_sub_notifications(client, owner["id"])
    pending_owner_row = next(
        notification
        for notification in owner_notifications
        if notification["related_sub_post_request_id"] == pending_request["id"]
    )
    assert pending_owner_row["notification_type"] == "sub_request_received"
    assert pending_owner_row["is_read"] is True
    assert pending_owner_row["title"] == "Request handled"

    for player in (pending_player, waitlisted_player, confirmed_player):
        notifications = list_need_a_sub_notifications(client, player["id"])
        cancel_notifications = [
            notification
            for notification in notifications
            if notification["notification_type"] == "sub_post_canceled"
        ]
        assert len(cancel_notifications) == 1
        assert cancel_notifications[0]["action_key"] is None
        assert cancel_notifications[0]["action"] is None

    declined_notifications = list_need_a_sub_notifications(client, declined_player["id"])
    assert "sub_post_canceled" not in notification_types(declined_notifications)


def test_sub_posts_public_reads_hide_private_location_and_owner_fields(client: TestClient):
    owner = create_user(client)
    post = create_sub_post(client, owner["id"])

    list_response = client.get("/need-a-sub/posts")
    assert list_response.status_code == 200, list_response.text
    listed_post = next(item for item in list_response.json() if item["id"] == post["id"])

    detail_response = client.get(f"/need-a-sub/posts/{post['id']}")
    assert detail_response.status_code == 200, detail_response.text
    public_post = detail_response.json()

    for payload in (listed_post, public_post):
        assert payload["id"] == post["id"]
        assert payload["location_name"] == post["location_name"]
        assert payload["city"] == post["city"]
        assert payload["state"] == post["state"]
        assert "owner_user_id" not in payload
        assert "address_line_1" not in payload
        assert "postal_code" not in payload
        assert "payment_note" not in payload
        assert "notes" not in payload
        assert "cancel_reason" not in payload


def test_sub_posts_signed_in_detail_and_mine_return_private_owner_fields(client: TestClient):
    owner = create_user(client)
    post = create_sub_post(client, owner["id"])
    authenticate_optional_as(owner["id"])

    detail_response = client.get(f"/need-a-sub/posts/{post['id']}")
    assert detail_response.status_code == 200, detail_response.text
    detail = detail_response.json()
    assert detail["owner_user_id"] == owner["id"]
    assert detail["address_line_1"] == post["address_line_1"]
    assert detail["postal_code"] == post["postal_code"]
    assert detail["notes"] == post["notes"]

    authenticate_as(owner["id"])
    mine_response = client.get("/need-a-sub/posts/mine")
    assert mine_response.status_code == 200, mine_response.text
    mine_posts = mine_response.json()
    assert [item["id"] for item in mine_posts] == [post["id"]]
    assert mine_posts[0]["owner_user_id"] == owner["id"]


def test_sub_posts_mine_requires_auth(client: TestClient):
    response = client.get("/need-a-sub/posts/mine")

    assert response.status_code == 401, response.text


def test_sub_posts_create_requires_auth(client: TestClient):
    response = client.post("/need-a-sub/posts", json=build_sub_post_payload())

    assert response.status_code == 401, response.text
    assert "Missing authorization header" in response.text


def test_sub_posts_reject_invalid_enums_and_limits(client: TestClient):
    owner = create_user(client)
    authenticate_as(owner["id"])

    invalid_skill = client.post(
        "/need-a-sub/posts",
        json=build_sub_post_payload(skill_level="elite"),
    )
    assert invalid_skill.status_code == 422, invalid_skill.text

    invalid_post_group = client.post(
        "/need-a-sub/posts",
        json=build_sub_post_payload(game_player_group="open"),
    )
    assert invalid_post_group.status_code == 422, invalid_post_group.text

    invalid_environment = client.post(
        "/need-a-sub/posts",
        json=build_sub_post_payload(environment_type="covered"),
    )
    assert invalid_environment.status_code == 422, invalid_environment.text

    too_many_subs = client.post(
        "/need-a-sub/posts",
        json=build_sub_post_payload(subs_needed=12),
    )
    assert too_many_subs.status_code == 422, too_many_subs.text

    too_many_rows = client.post(
        "/need-a-sub/posts",
        json=build_sub_post_payload(
            subs_needed=7,
            positions=[
                {
                    "position_label": "field_player",
                    "player_group": "open",
                    "spots_needed": 1,
                    "sort_order": 0,
                },
                {
                    "position_label": "field_player",
                    "player_group": "men",
                    "spots_needed": 1,
                    "sort_order": 1,
                },
                {
                    "position_label": "field_player",
                    "player_group": "women",
                    "spots_needed": 1,
                    "sort_order": 2,
                },
                {
                    "position_label": "goalkeeper",
                    "player_group": "open",
                    "spots_needed": 1,
                    "sort_order": 3,
                },
                {
                    "position_label": "goalkeeper",
                    "player_group": "men",
                    "spots_needed": 1,
                    "sort_order": 4,
                },
                {
                    "position_label": "goalkeeper",
                    "player_group": "women",
                    "spots_needed": 1,
                    "sort_order": 5,
                },
                {
                    "position_label": "field_player",
                    "player_group": "open",
                    "spots_needed": 1,
                    "sort_order": 6,
                },
            ],
        ),
    )
    assert too_many_rows.status_code == 422, too_many_rows.text


def test_sub_posts_reject_invalid_position_total(client: TestClient):
    owner = create_user(client)
    authenticate_as(owner["id"])

    payload = build_sub_post_payload(subs_needed=3)
    response = client.post("/need-a-sub/posts", json=payload)

    assert response.status_code == 400, response.text
    assert "add up to subs_needed" in response.text


def test_sub_posts_reject_duplicate_position_group_rows_cleanly(client: TestClient):
    owner = create_user(client)
    authenticate_as(owner["id"])

    payload = build_sub_post_payload(
        subs_needed=2,
        positions=[
            {
                "position_label": "field_player",
                "player_group": "men",
                "spots_needed": 1,
                "sort_order": 0,
            },
            {
                "position_label": "field_player",
                "player_group": "men",
                "spots_needed": 1,
                "sort_order": 1,
            },
        ],
    )
    response = client.post("/need-a-sub/posts", json=payload)

    assert response.status_code == 400, response.text
    assert "unique" in response.text


def test_sub_posts_allow_gendered_rows_for_same_position(client: TestClient):
    owner = create_user(client)
    authenticate_as(owner["id"])

    payload = build_sub_post_payload(
        subs_needed=2,
        positions=[
            {
                "position_label": "field_player",
                "player_group": "men",
                "spots_needed": 1,
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
    response = client.post("/need-a-sub/posts", json=payload)

    assert response.status_code == 201, response.text
    assert {
        (position["position_label"], position["player_group"])
        for position in response.json()["positions"]
    } == {("field_player", "men"), ("field_player", "women")}


def test_sub_posts_allow_any_and_gendered_rows_across_positions(client: TestClient):
    owner = create_user(client)
    authenticate_as(owner["id"])

    payload = build_sub_post_payload(
        subs_needed=2,
        positions=[
            {
                "position_label": "field_player",
                "player_group": "open",
                "spots_needed": 1,
                "sort_order": 0,
            },
            {
                "position_label": "goalkeeper",
                "player_group": "men",
                "spots_needed": 1,
                "sort_order": 1,
            },
        ],
    )
    response = client.post("/need-a-sub/posts", json=payload)

    assert response.status_code == 201, response.text
    assert {
        (position["position_label"], position["player_group"])
        for position in response.json()["positions"]
    } == {("field_player", "open"), ("goalkeeper", "men")}


def test_sub_posts_reject_any_combined_with_gendered_rows(client: TestClient):
    owner = create_user(client)
    authenticate_as(owner["id"])

    payload = build_sub_post_payload(
        subs_needed=2,
        positions=[
            {
                "position_label": "field_player",
                "player_group": "open",
                "spots_needed": 1,
                "sort_order": 0,
            },
            {
                "position_label": "field_player",
                "player_group": "men",
                "spots_needed": 1,
                "sort_order": 1,
            },
        ],
    )
    response = client.post("/need-a-sub/posts", json=payload)

    assert response.status_code == 400, response.text
    assert "Any player rows cannot be combined" in response.text


def test_sub_posts_reject_any_combined_with_gendered_goalkeeper_rows(client: TestClient):
    owner = create_user(client)
    authenticate_as(owner["id"])

    payload = build_sub_post_payload(
        subs_needed=2,
        positions=[
            {
                "position_label": "goalkeeper",
                "player_group": "open",
                "spots_needed": 1,
                "sort_order": 0,
            },
            {
                "position_label": "goalkeeper",
                "player_group": "women",
                "spots_needed": 1,
                "sort_order": 1,
            },
        ],
    )
    response = client.post("/need-a-sub/posts", json=payload)

    assert response.status_code == 400, response.text
    assert "Any player rows cannot be combined" in response.text


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


def test_sub_posts_reject_start_more_than_fourteen_days_out(client: TestClient):
    owner = create_user(client)
    authenticate_as(owner["id"])
    starts_at = datetime.now(UTC) + timedelta(days=15)
    ends_at = starts_at + timedelta(hours=2)

    response = client.post(
        "/need-a-sub/posts",
        json=build_sub_post_payload(
            starts_at=starts_at.isoformat(),
            ends_at=ends_at.isoformat(),
        ),
    )

    assert response.status_code == 400, response.text
    assert "up to 14 days in advance" in response.text


def test_sub_posts_limit_owner_to_one_live_post_per_local_date(
    client: TestClient,
):
    owner = create_user(client)
    post = create_sub_post(client, owner["id"])
    starts_at = parse_iso_datetime(post["starts_at"])
    ends_at = parse_iso_datetime(post["ends_at"])

    authenticate_as(owner["id"])
    duplicate_response = client.post(
        "/need-a-sub/posts",
        json=build_sub_post_payload(
            starts_at=(starts_at + timedelta(hours=1)).isoformat(),
            ends_at=(ends_at + timedelta(hours=1)).isoformat(),
        ),
    )
    assert duplicate_response.status_code == 409, duplicate_response.text
    assert (
        "already have an active Need a Sub post for this date"
        in duplicate_response.text
    )

    next_day_starts_at = starts_at + timedelta(days=1)
    next_day_response = client.post(
        "/need-a-sub/posts",
        json=build_sub_post_payload(
            starts_at=next_day_starts_at.isoformat(),
            ends_at=(next_day_starts_at + timedelta(hours=2)).isoformat(),
        ),
    )
    assert next_day_response.status_code == 201, next_day_response.text

    cancel_response = client.patch(
        f"/need-a-sub/posts/{post['id']}/cancel",
        json={"cancel_reason": "Testing same-day replacement."},
    )
    assert cancel_response.status_code == 200, cancel_response.text

    replacement_response = client.post(
        "/need-a-sub/posts",
        json=build_sub_post_payload(
            starts_at=(starts_at + timedelta(hours=2)).isoformat(),
            ends_at=(ends_at + timedelta(hours=2)).isoformat(),
        ),
    )
    assert replacement_response.status_code == 201, replacement_response.text


def test_sub_posts_owner_can_edit_post_without_requests(client: TestClient):
    owner = create_user(client)
    post = create_sub_post(client, owner["id"])
    authenticate_as(owner["id"])

    payload = build_sub_post_payload(
        format_label="3v3",
        environment_type="indoor",
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
    assert response.json()["format_label"] == "3v3"
    assert response.json()["environment_type"] == "indoor"
    assert response.json()["skill_level"] == "advanced"
    assert response.json()["subs_needed"] == 1
    assert response.json()["positions"][0]["position_label"] == "goalkeeper"


def test_sub_posts_edit_rejects_changing_post_date(client: TestClient):
    owner = create_user(client)
    post = create_sub_post(client, owner["id"])
    authenticate_as(owner["id"])
    starts_at = parse_iso_datetime(post["starts_at"])
    ends_at = parse_iso_datetime(post["ends_at"])

    response = client.patch(
        f"/need-a-sub/posts/{post['id']}",
        json=build_sub_post_payload(
            starts_at=(starts_at + timedelta(days=1)).isoformat(),
            ends_at=(ends_at + timedelta(days=1)).isoformat(),
        ),
    )

    assert response.status_code == 400, response.text
    assert "Post date cannot be changed" in response.text


def test_sub_posts_edit_allows_same_date_time_change(client: TestClient):
    owner = create_user(client)
    post = create_sub_post(client, owner["id"])
    authenticate_as(owner["id"])
    starts_at = parse_iso_datetime(post["starts_at"])
    ends_at = parse_iso_datetime(post["ends_at"])
    updated_starts_at = starts_at + timedelta(minutes=30)
    updated_ends_at = ends_at + timedelta(minutes=30)

    response = client.patch(
        f"/need-a-sub/posts/{post['id']}",
        json=build_sub_post_payload(
            starts_at=updated_starts_at.isoformat(),
            ends_at=updated_ends_at.isoformat(),
        ),
    )

    assert response.status_code == 200, response.text
    assert parse_iso_datetime(response.json()["starts_at"]) == updated_starts_at
    assert parse_iso_datetime(response.json()["ends_at"]) == updated_ends_at


def test_sub_posts_structural_edit_notifies_active_requesters(client: TestClient):
    owner = create_user(client)
    pending_player = create_user(client)
    waitlisted_player = create_user(client)
    confirmed_player = create_user(client)
    post = create_sub_post(client, owner["id"])
    pending_request = request_sub_spot(client, pending_player["id"], post, 0)
    waitlisted_request = request_sub_spot(client, waitlisted_player["id"], post, 0)
    confirmed_request = request_sub_spot(client, confirmed_player["id"], post, 1)

    assert pending_request["request_status"] == "pending"
    assert waitlisted_request["request_status"] == "sub_waitlist"
    authenticate_as(owner["id"])
    accept_response = client.patch(
        f"/need-a-sub/requests/{confirmed_request['id']}/accept"
    )
    assert accept_response.status_code == 200, accept_response.text

    starts_at = parse_iso_datetime(post["starts_at"])
    ends_at = parse_iso_datetime(post["ends_at"])
    response = client.patch(
        f"/need-a-sub/posts/{post['id']}",
        json=build_sub_post_payload(
            starts_at=(starts_at + timedelta(minutes=30)).isoformat(),
            ends_at=(ends_at + timedelta(minutes=30)).isoformat(),
        ),
    )
    assert response.status_code == 200, response.text

    for user, sub_request in (
        (pending_player, pending_request),
        (waitlisted_player, waitlisted_request),
        (confirmed_player, confirmed_request),
    ):
        notifications = list_need_a_sub_notifications(client, user["id"])
        update_notifications = [
            notification
            for notification in notifications
            if notification["notification_type"] == "sub_post_updated"
        ]
        assert len(update_notifications) == 1
        notification = update_notifications[0]
        assert notification["actor_user_id"] == owner["id"]
        assert notification["related_sub_post_id"] == post["id"]
        assert notification["related_sub_post_request_id"] == sub_request["id"]
        assert (
            notification["related_sub_post_position_id"]
            == sub_request["sub_post_position_id"]
        )
        assert notification["aggregation_key"] == (
            f"need_a_sub:post:{post['id']}:user:{user['id']}:sub_post_updated"
        )
        assert notification["aggregate_count"] is None
        assert notification["action_key"] == "view_sub_post"


def test_sub_posts_structural_edit_reuses_requester_update_notification(
    client: TestClient,
):
    owner = create_user(client)
    requester = create_user(client)
    post = create_sub_post(client, owner["id"])
    sub_request = request_sub_spot(client, requester["id"], post, 0)

    authenticate_as(owner["id"])
    first_response = client.patch(
        f"/need-a-sub/posts/{post['id']}",
        json=build_sub_post_payload(location_name="First Update Field"),
    )
    assert first_response.status_code == 200, first_response.text

    notifications = list_need_a_sub_notifications(client, requester["id"])
    first_notification = next(
        notification
        for notification in notifications
        if notification["notification_type"] == "sub_post_updated"
    )
    assert first_notification["related_sub_post_request_id"] == sub_request["id"]

    read_response = client.patch(
        f"/notifications/{first_notification['id']}/read",
        json={},
    )
    assert read_response.status_code == 200, read_response.text

    authenticate_as(owner["id"])
    second_response = client.patch(
        f"/need-a-sub/posts/{post['id']}",
        json=build_sub_post_payload(location_name="Second Update Field"),
    )
    assert second_response.status_code == 200, second_response.text

    notifications = list_need_a_sub_notifications(client, requester["id"])
    update_notifications = [
        notification
        for notification in notifications
        if notification["notification_type"] == "sub_post_updated"
    ]
    assert len(update_notifications) == 1
    assert update_notifications[0]["id"] == first_notification["id"]
    assert update_notifications[0]["is_read"] is False
    assert update_notifications[0]["read_at"] is None
    assert update_notifications[0]["aggregate_count"] is None


def test_sub_posts_text_and_capacity_only_edits_do_not_notify_requesters(
    client: TestClient,
):
    owner = create_user(client)
    requester = create_user(client)
    post = create_sub_post(client, owner["id"])
    request_sub_spot(client, requester["id"], post, 0)

    authenticate_as(owner["id"])
    text_response = client.patch(
        f"/need-a-sub/posts/{post['id']}",
        json=build_sub_post_payload(notes="Typo cleanup only."),
    )
    assert text_response.status_code == 200, text_response.text
    requester_notifications = list_need_a_sub_notifications(client, requester["id"])
    assert "sub_post_updated" not in notification_types(requester_notifications)

    authenticate_as(owner["id"])
    capacity_response = client.patch(
        f"/need-a-sub/posts/{post['id']}",
        json=build_sub_post_payload(
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
        ),
    )
    assert capacity_response.status_code == 200, capacity_response.text
    requester_notifications = list_need_a_sub_notifications(client, requester["id"])
    assert "sub_post_updated" not in notification_types(requester_notifications)


def test_sub_posts_edit_allows_safe_player_group_change(client: TestClient):
    owner = create_user(client)
    post = create_sub_post(
        client,
        owner["id"],
        game_player_group="women",
        subs_needed=1,
        positions=[
            {
                "position_label": "field_player",
                "player_group": "women",
                "spots_needed": 1,
                "sort_order": 0,
            }
        ],
    )
    authenticate_as(owner["id"])

    response = client.patch(
        f"/need-a-sub/posts/{post['id']}",
        json=build_sub_post_payload(
            game_player_group="coed",
            starts_at=post["starts_at"],
            ends_at=post["ends_at"],
            subs_needed=1,
            positions=[
                {
                    "position_label": "field_player",
                    "player_group": "women",
                    "spots_needed": 1,
                    "sort_order": 0,
                }
            ],
        ),
    )

    assert response.status_code == 200, response.text
    assert response.json()["game_player_group"] == "coed"


def test_sub_posts_edit_rejects_incompatible_player_group_change(client: TestClient):
    owner = create_user(client)
    post = create_sub_post(
        client,
        owner["id"],
        game_player_group="women",
        subs_needed=1,
        positions=[
            {
                "position_label": "field_player",
                "player_group": "women",
                "spots_needed": 1,
                "sort_order": 0,
            }
        ],
    )
    authenticate_as(owner["id"])

    response = client.patch(
        f"/need-a-sub/posts/{post['id']}",
        json=build_sub_post_payload(
            game_player_group="men",
            starts_at=post["starts_at"],
            ends_at=post["ends_at"],
            subs_needed=1,
            positions=[
                {
                    "position_label": "field_player",
                    "player_group": "women",
                    "spots_needed": 1,
                    "sort_order": 0,
                }
            ],
        ),
    )

    assert response.status_code == 400, response.text
    assert "not compatible" in response.text


def test_sub_posts_edit_rejects_any_combined_with_gendered_rows(client: TestClient):
    owner = create_user(client)
    post = create_sub_post(client, owner["id"])
    authenticate_as(owner["id"])

    payload = build_sub_post_payload(
        subs_needed=2,
        positions=[
            {
                "position_label": "goalkeeper",
                "player_group": "open",
                "spots_needed": 1,
                "sort_order": 0,
            },
            {
                "position_label": "goalkeeper",
                "player_group": "women",
                "spots_needed": 1,
                "sort_order": 1,
            },
        ],
    )
    response = client.patch(f"/need-a-sub/posts/{post['id']}", json=payload)

    assert response.status_code == 400, response.text
    assert "Any player rows cannot be combined" in response.text


def test_sub_posts_edit_allows_any_and_gendered_rows_across_positions(client: TestClient):
    owner = create_user(client)
    post = create_sub_post(client, owner["id"])
    authenticate_as(owner["id"])

    payload = build_sub_post_payload(
        subs_needed=2,
        positions=[
            {
                "position_label": "field_player",
                "player_group": "open",
                "spots_needed": 1,
                "sort_order": 0,
            },
            {
                "position_label": "goalkeeper",
                "player_group": "men",
                "spots_needed": 1,
                "sort_order": 1,
            },
        ],
    )
    response = client.patch(f"/need-a-sub/posts/{post['id']}", json=payload)

    assert response.status_code == 200, response.text
    assert {
        (position["position_label"], position["player_group"])
        for position in response.json()["positions"]
    } == {("field_player", "open"), ("goalkeeper", "men")}


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


def test_sub_posts_edit_rejects_blank_required_fields_before_service(client: TestClient):
    owner = create_user(client)
    post = create_sub_post(client, owner["id"])

    authenticate_as(owner["id"])
    response = client.patch(
        f"/need-a-sub/posts/{post['id']}",
        json={"location_name": "   "},
    )

    assert response.status_code == 422, response.text


def test_sub_posts_edit_cancel_and_remove_expire_due_post_before_action(client: TestClient):
    from uuid import UUID

    from backend.database import SessionLocal
    from backend.models import SubPost

    owner = create_user(client)
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    post = create_sub_post(client, owner["id"])

    with SessionLocal() as db:
        db_post = db.get(SubPost, UUID(post["id"]))
        db_post.starts_at = datetime.now(UTC) - timedelta(minutes=5)
        db_post.ends_at = datetime.now(UTC) + timedelta(minutes=55)
        db_post.expires_at = db_post.starts_at
        db.commit()

    authenticate_as(owner["id"])
    edit_response = client.patch(
        f"/need-a-sub/posts/{post['id']}",
        json=build_sub_post_payload(format_label="11v11"),
    )
    assert edit_response.status_code == 400, edit_response.text
    assert "Only active posts can be edited" in edit_response.text

    cancel_response = client.patch(
        f"/need-a-sub/posts/{post['id']}/cancel",
        json={"cancel_reason": "Too late."},
    )
    assert cancel_response.status_code == 400, cancel_response.text
    assert "Only active posts can be cancelled" in cancel_response.text

    authenticate_as(admin["id"])
    remove_response = client.patch(
        f"/need-a-sub/posts/{post['id']}/remove",
        json={
            "remove_reason": "Moderation cleanup.",
            "idempotency_key": f"remove-sub-post-{unique_suffix()}",
        },
    )
    assert remove_response.status_code == 200, remove_response.text
    assert remove_response.json()["post_status"] == "removed"


def test_sub_posts_admin_can_remove_post(client: TestClient):
    owner = create_user(client)
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    post = create_sub_post(client, owner["id"])

    authenticate_as(admin["id"])
    response = client.patch(
        f"/need-a-sub/posts/{post['id']}/remove",
        json={
            "remove_reason": "Unsafe payment details.",
            "idempotency_key": f"remove-sub-post-{unique_suffix()}",
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["post_status"] == "removed"
    assert response.json()["removed_by_user_id"] == admin["id"]


def test_sub_posts_remove_requires_reason_for_audit(client: TestClient):
    owner = create_user(client)
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    post = create_sub_post(client, owner["id"])

    authenticate_as(admin["id"])
    response = client.patch(
        f"/need-a-sub/posts/{post['id']}/remove",
        json={
            "remove_reason": "   ",
            "idempotency_key": f"remove-sub-post-{unique_suffix()}",
        },
    )

    assert response.status_code == 400, response.text
    assert "remove_sub_post requires a reason" in response.text

    detail_response = client.get(f"/need-a-sub/posts/{post['id']}")
    assert detail_response.status_code == 200, detail_response.text
    assert detail_response.json()["post_status"] == "active"

    audit_response = client.get(f"/admin/actions?target_sub_post_id={post['id']}")
    assert audit_response.status_code == 200, audit_response.text
    assert audit_response.json() == []


def test_sub_posts_remove_replays_matching_idempotency_key(client: TestClient):
    owner = create_user(client)
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    post = create_sub_post(client, owner["id"])
    idempotency_key = f"remove-sub-post-{unique_suffix()}"
    payload = {
        "remove_reason": "Repeated support request.",
        "idempotency_key": idempotency_key,
    }

    authenticate_as(admin["id"])
    first_response = client.patch(
        f"/need-a-sub/posts/{post['id']}/remove",
        json=payload,
    )
    replay_response = client.patch(
        f"/need-a-sub/posts/{post['id']}/remove",
        json=payload,
    )
    mismatch_response = client.patch(
        f"/need-a-sub/posts/{post['id']}/remove",
        json={
            "remove_reason": "Different support request.",
            "idempotency_key": idempotency_key,
        },
    )

    assert first_response.status_code == 200, first_response.text
    assert replay_response.status_code == 200, replay_response.text
    assert replay_response.json()["removed_at"] == first_response.json()["removed_at"]
    assert mismatch_response.status_code == 409, mismatch_response.text
    assert "different Need a Sub removal request" in mismatch_response.text

    audit_response = client.get(f"/admin/actions?target_sub_post_id={post['id']}")
    assert audit_response.status_code == 200, audit_response.text
    remove_actions = [
        action
        for action in audit_response.json()
        if action["action_type"] == "remove_sub_post"
    ]
    assert len(remove_actions) == 1
    assert remove_actions[0]["idempotency_key"] == idempotency_key

    owner_notifications = list_need_a_sub_notifications(client, owner["id"])
    assert [
        notification["notification_type"]
        for notification in owner_notifications
        if notification["notification_type"] == "sub_post_removed"
    ] == ["sub_post_removed"]


def test_sub_posts_suspended_staff_cannot_remove_post(client: TestClient):
    for role in ("admin",):
        owner = create_user(client)
        staff = create_user(client)
        set_user_role(staff["id"], role)
        set_user_account_status(staff["id"], "suspended")
        post = create_sub_post(client, owner["id"])

        authenticate_as(staff["id"])
        response = client.patch(
            f"/need-a-sub/posts/{post['id']}/remove",
            json={
                "remove_reason": "Should not run.",
                "idempotency_key": f"remove-sub-post-{unique_suffix()}",
            },
        )

        assert response.status_code == 403, response.text
        assert response.json()["detail"] == "Admin access required."


def test_sub_posts_admin_remove_cancels_active_requests(client: TestClient):
    owner = create_user(client)
    pending_player = create_user(client)
    waitlisted_player = create_user(client)
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    post = create_sub_post(client, owner["id"])

    authenticate_as(pending_player["id"])
    pending_request = client.post(
        f"/need-a-sub/posts/{post['id']}/requests",
        json={"sub_post_position_id": post["positions"][0]["id"]},
    ).json()
    authenticate_as(waitlisted_player["id"])
    waitlisted_request = client.post(
        f"/need-a-sub/posts/{post['id']}/requests",
        json={"sub_post_position_id": post["positions"][0]["id"]},
    ).json()

    authenticate_as(admin["id"])
    remove_response = client.patch(
        f"/need-a-sub/posts/{post['id']}/remove",
        json={
            "remove_reason": "Moderation cleanup.",
            "idempotency_key": f"remove-sub-post-{unique_suffix()}",
        },
    )
    assert remove_response.status_code == 200, remove_response.text
    owner_notifications = list_need_a_sub_notifications(client, owner["id"])
    pending_owner_row = next(
        notification
        for notification in owner_notifications
        if notification["related_sub_post_request_id"] == pending_request["id"]
    )
    assert pending_owner_row["notification_type"] == "sub_request_received"
    assert pending_owner_row["is_read"] is True
    assert pending_owner_row["title"] == "Request handled"

    for player, sub_request in (
        (pending_player, pending_request),
        (waitlisted_player, waitlisted_request),
    ):
        authenticate_as(player["id"])
        request_response = client.get("/need-a-sub/my-requests")
        assert request_response.status_code == 200, request_response.text
        requests_by_id = {request["id"]: request for request in request_response.json()}
        assert requests_by_id[sub_request["id"]]["request_status"] == "closed_by_admin"
        player_notifications = list_need_a_sub_notifications(client, player["id"])
        assert "sub_post_removed" in notification_types(player_notifications)
        remove_notification = next(
            notification
            for notification in player_notifications
            if notification["notification_type"] == "sub_post_removed"
        )
        assert remove_notification["action_key"] is None
        assert remove_notification["action"] is None


def test_sub_posts_expiration_service_expires_posts_and_open_requests(client: TestClient):
    from uuid import UUID

    from backend.database import SessionLocal
    from backend.models import SubPost, SubPostRequest
    from backend.services.need_a_sub_lifecycle_service import (
        expire_due_posts_and_requests,
    )

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

    assert counts == {
        "posts_completed": 0,
        "posts_expired": 1,
        "requests_expired": 1,
    }
    assert db_post.post_status == "expired"
    assert db_request.request_status == "expired"


def test_sub_posts_list_opportunistically_expires_due_posts(client: TestClient):
    from uuid import UUID

    from backend.database import SessionLocal
    from backend.models import SubPost

    owner = create_user(client)
    post = create_sub_post(client, owner["id"])

    with SessionLocal() as db:
        db_post = db.get(SubPost, UUID(post["id"]))
        db_post.starts_at = datetime.now(UTC) - timedelta(minutes=5)
        db_post.ends_at = datetime.now(UTC) + timedelta(minutes=55)
        db_post.expires_at = db_post.starts_at
        db.commit()

    list_response = client.get("/need-a-sub/posts")
    assert list_response.status_code == 200, list_response.text
    assert post["id"] not in {item["id"] for item in list_response.json()}

    with SessionLocal() as db:
        db_post = db.get(SubPost, UUID(post["id"]))
        assert db_post.post_status == "expired"
