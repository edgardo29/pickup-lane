from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
import pytest

from backend.models import SubPost, SubPostRequest, SubPostRequestStatusHistory
from backend.database import SessionLocal
from backend.tests.compliance.runtime import assert_effect, assert_time_boundary
from backend.tests.support.constraints import constraint_values
from backend.tests.support.auth import authenticate_as
from backend.tests.support.factories import create_user


def _sub_items_by_id(response: dict) -> dict[str, dict]:
    return {item["post"]["id"]: item for item in response["items"]}


def _create_confirmed_request_post(
    my_games_factory,
    *,
    requester_id: str,
    starts_at: datetime,
    ends_at: datetime | None = None,
    post_status: str = "active",
    **post_overrides: object,
):
    owner = create_user(None)
    post, position = my_games_factory.create_sub_post(
        owner_user_id=owner["id"],
        starts_at=starts_at,
        ends_at=ends_at,
        post_status=post_status,
        **post_overrides,
    )
    request = my_games_factory.create_sub_request(
        post_id=post.id,
        position_id=position.id,
        requester_user_id=requester_id,
        request_status="confirmed",
    )
    return post, position, request


def _create_cancelled_confirmed_request_post(
    my_games_factory,
    *,
    requester_id: str,
    starts_at: datetime,
    ends_at: datetime | None = None,
    old_status: str = "confirmed",
    change_source: str = "owner",
    history_created_at_delta: timedelta = timedelta(),
    request_canceled_at_delta: timedelta = timedelta(),
    request_is_still_confirmed: bool = False,
    add_newer_history: bool = False,
):
    owner = create_user(None)
    canceled_at = datetime.now(UTC).replace(microsecond=0)
    post, position = my_games_factory.create_sub_post(
        owner_user_id=owner["id"],
        starts_at=starts_at,
        ends_at=ends_at,
        post_status="cancelled",
        canceled_at=canceled_at,
        canceled_by_user_id=owner["id"],
    )
    if request_is_still_confirmed:
        request = my_games_factory.create_sub_request(
            post_id=post.id,
            position_id=position.id,
            requester_user_id=requester_id,
            request_status="confirmed",
        )
        return post, request

    request = my_games_factory.create_sub_request(
        post_id=post.id,
        position_id=position.id,
        requester_user_id=requester_id,
        request_status="canceled_by_owner",
        canceled_at=canceled_at + request_canceled_at_delta,
    )
    my_games_factory.create_sub_request_history(
        request_id=request.id,
        old_status=old_status,
        new_status="canceled_by_owner",
        change_source=change_source,
        created_at=canceled_at + history_created_at_delta,
    )
    if add_newer_history:
        my_games_factory.create_sub_request_history(
            request_id=request.id,
            old_status="pending",
            new_status="canceled_by_owner",
            change_source="owner",
            created_at=canceled_at + timedelta(minutes=1),
        )

    return post, request


def test_need_a_sub_status_matrices_cover_authoritative_model_values():
    all_request_statuses = constraint_values(
        SubPostRequest,
        "ck_sub_post_requests_request_status",
    )
    qualifying_current_request_statuses = {"confirmed"}
    excluded_request_statuses = {
        "pending",
        "declined",
        "sub_waitlist",
        "canceled_by_player",
        "canceled_by_owner",
        "no_show_reported",
        "expired",
        "closed_by_admin",
    }
    assert qualifying_current_request_statuses.isdisjoint(excluded_request_statuses)
    assert qualifying_current_request_statuses | excluded_request_statuses == (
        all_request_statuses
    )

    all_post_statuses = constraint_values(SubPost, "ck_sub_posts_post_status")
    upcoming_allowed_post_statuses = {"active", "completed", "expired"}
    excluded_post_statuses = {"cancelled", "removed"}
    assert upcoming_allowed_post_statuses.isdisjoint(excluded_post_statuses)
    assert upcoming_allowed_post_statuses | excluded_post_statuses == (
        all_post_statuses
    )

    all_history_change_sources = constraint_values(
        SubPostRequestStatusHistory,
        "ck_sub_post_request_status_history_change_source",
    )
    qualifying_change_sources = {"owner"}
    rejected_change_sources = {"requester", "admin", "system", "scheduled_job"}
    assert qualifying_change_sources.isdisjoint(rejected_change_sources)
    assert qualifying_change_sources | rejected_change_sources == (
        all_history_change_sources
    )


def test_need_a_sub_upcoming_includes_owner_and_confirmed_requester_only(
    client: TestClient,
    my_games_factory,
):
    user = create_user(client)
    other_owner = create_user(client)
    now = datetime.now(UTC).replace(microsecond=0)
    future = now + timedelta(days=7)
    owned, _ = my_games_factory.create_sub_post(
        owner_user_id=user["id"],
        starts_at=future,
    )
    confirmed, _, _ = _create_confirmed_request_post(
        my_games_factory,
        requester_id=user["id"],
        starts_at=future + timedelta(days=1),
    )
    excluded_posts: list[SubPost] = []
    for index, request_status in enumerate(
        [
            "pending",
            "sub_waitlist",
            "declined",
            "canceled_by_player",
            "expired",
            "no_show_reported",
            "closed_by_admin",
        ],
        start=2,
    ):
        post, position = my_games_factory.create_sub_post(
            owner_user_id=other_owner["id"],
            starts_at=future + timedelta(days=index),
        )
        my_games_factory.create_sub_request(
            post_id=post.id,
            position_id=position.id,
            requester_user_id=user["id"],
            request_status=request_status,
        )
        excluded_posts.append(post)
    other_user_request_post, position = my_games_factory.create_sub_post(
        owner_user_id=other_owner["id"],
        starts_at=future + timedelta(days=10),
    )
    my_games_factory.create_sub_request(
        post_id=other_user_request_post.id,
        position_id=position.id,
        requester_user_id=other_owner["id"],
        request_status="confirmed",
    )
    excluded_posts.append(other_user_request_post)

    authenticate_as(user["id"])
    response = client.get("/my-games/need-a-sub", params={"view": "upcoming"})

    assert response.status_code == 200, response.text
    items_by_id = _sub_items_by_id(response.json())
    assert set(items_by_id) == {str(owned.id), str(confirmed.id)}
    assert items_by_id[str(owned.id)]["is_owner"] is True
    assert items_by_id[str(owned.id)]["status_label"] == "Your Post"
    assert items_by_id[str(owned.id)]["status_tone"] == "owner"
    assert items_by_id[str(confirmed.id)]["is_owner"] is False
    assert items_by_id[str(confirmed.id)]["status_label"] == "Confirmed"
    assert items_by_id[str(confirmed.id)]["status_tone"] == "confirmed"
    assert not {str(post.id) for post in excluded_posts} & set(items_by_id)


def test_need_a_sub_owner_priority_returns_one_card(
    client: TestClient,
    my_games_factory,
):
    owner = create_user(client)
    now = datetime.now(UTC).replace(microsecond=0)
    post, position = my_games_factory.create_sub_post(
        owner_user_id=owner["id"],
        starts_at=now + timedelta(days=7),
    )
    my_games_factory.create_sub_request(
        post_id=post.id,
        position_id=position.id,
        requester_user_id=owner["id"],
        request_status="confirmed",
    )
    my_games_factory.create_sub_request(
        post_id=post.id,
        position_id=position.id,
        requester_user_id=owner["id"],
        request_status="canceled_by_player",
    )

    authenticate_as(owner["id"])
    response = client.get("/my-games/need-a-sub", params={"view": "upcoming"})

    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert [item["post"]["id"] for item in items] == [str(post.id)]
    assert items[0]["is_owner"] is True
    assert items[0]["status_label"] == "Your Post"
    assert items[0]["request_status"] == "confirmed"


@pytest.mark.parametrize(
    ("post_status", "should_appear"),
    [
        ("active", True),
        ("completed", True),
        ("expired", True),
        ("cancelled", False),
        ("removed", False),
    ],
)
def test_need_a_sub_upcoming_post_lifecycle_filters(
    client: TestClient,
    my_games_factory,
    post_status: str,
    should_appear: bool,
):
    owner = create_user(client)
    now = datetime.now(UTC).replace(microsecond=0)
    post, _ = my_games_factory.create_sub_post(
        owner_user_id=owner["id"],
        starts_at=now + timedelta(days=7),
        post_status=post_status,
    )

    authenticate_as(owner["id"])
    response = client.get("/my-games/need-a-sub", params={"view": "upcoming"})

    assert response.status_code == 200, response.text
    item_ids = {item["post"]["id"] for item in response.json()["items"]}
    assert (str(post.id) in item_ids) is should_appear


@pytest.mark.parametrize(
    ("relationship", "request_status"),
    [
        ("owner", None),
        ("requester", "confirmed"),
    ],
)
def test_need_a_sub_hidden_qualifying_relationships_still_appear(
    client: TestClient,
    my_games_factory,
    relationship: str,
    request_status: str | None,
):
    user = create_user(client)
    other_owner = create_user(client)
    now = datetime.now(UTC).replace(microsecond=0)
    owner_id = user["id"] if relationship == "owner" else other_owner["id"]
    post, position = my_games_factory.create_sub_post(
        owner_user_id=owner_id,
        starts_at=now + timedelta(days=7),
        public_visibility_status="hidden",
    )
    if request_status is not None:
        my_games_factory.create_sub_request(
            post_id=post.id,
            position_id=position.id,
            requester_user_id=user["id"],
            request_status=request_status,
        )

    authenticate_as(user["id"])
    response = client.get("/my-games/need-a-sub", params={"view": "upcoming"})

    assert response.status_code == 200, response.text
    assert {item["post"]["id"] for item in response.json()["items"]} == {
        str(post.id)
    }


@pytest.mark.parametrize("request_status", ["pending", "sub_waitlist"])
def test_need_a_sub_hidden_pending_and_sub_waitlist_requesters_do_not_appear(
    client: TestClient,
    my_games_factory,
    request_status: str,
):
    user = create_user(client)
    other_owner = create_user(client)
    now = datetime.now(UTC).replace(microsecond=0)
    post, position = my_games_factory.create_sub_post(
        owner_user_id=other_owner["id"],
        starts_at=now + timedelta(days=7),
        public_visibility_status="hidden",
    )
    my_games_factory.create_sub_request(
        post_id=post.id,
        position_id=position.id,
        requester_user_id=user["id"],
        request_status=request_status,
    )

    authenticate_as(user["id"])
    response = client.get("/my-games/need-a-sub", params={"view": "upcoming"})

    assert response.status_code == 200, response.text
    assert response.json()["items"] == []


def test_need_a_sub_in_progress_stays_upcoming_after_cleanup_changes_lifecycle(
    client: TestClient,
    my_games_factory,
    freeze_my_games_now,
    backend_test_evidence,
):
    owner = create_user(client)
    now = datetime(2026, 8, 10, 18, 0, tzinfo=UTC)
    freeze_my_games_now(now)
    post, _ = my_games_factory.create_sub_post(
        owner_user_id=owner["id"],
        starts_at=now - timedelta(minutes=30),
        ends_at=now + timedelta(minutes=30),
        expires_at=now - timedelta(minutes=30),
        post_status="active",
    )

    authenticate_as(owner["id"])
    backend_test_evidence.register_label(
        "need_a_sub_in_progress_cleanup_post",
        {"id": post.id},
    )
    assert_time_boundary(
        backend_test_evidence,
        time_id="TIME-SUB-IN-PROGRESS-CLEANUP",
        baseline=now.isoformat(),
        boundary="after_starts_at",
        actual=post.starts_at < now,
        expected=True,
    )
    assert_time_boundary(
        backend_test_evidence,
        time_id="TIME-SUB-IN-PROGRESS-CLEANUP",
        baseline=now.isoformat(),
        boundary="before_ends_at",
        actual=post.ends_at > now,
        expected=True,
    )
    assert_time_boundary(
        backend_test_evidence,
        time_id="TIME-SUB-IN-PROGRESS-CLEANUP",
        baseline=now.isoformat(),
        boundary="expired_cleanup_due",
        actual=post.expires_at <= now,
        expected=True,
    )
    with SessionLocal() as db:
        with assert_effect(
            backend_test_evidence,
            effect_id="EFF-SUB-PRE-READ-CLEANUP",
            kind="field_changed",
            session=db,
            model=SubPost,
            lookup={
                "by": "contract_label",
                "label": "need_a_sub_in_progress_cleanup_post",
            },
            field="post_status",
            before={"equals": "active"},
            expect="in",
            value=["completed", "expired"],
        ):
            response = client.get("/my-games/need-a-sub", params={"view": "upcoming"})

    assert response.status_code == 200, response.text
    [item] = response.json()["items"]
    assert item["post"]["id"] == str(post.id)
    assert item["status_label"] == "Your Post"
    assert item["post"]["post_status"] in {"completed", "expired"}


def test_need_a_sub_history_includes_recent_ended_owner_and_confirmed_relationships(
    client: TestClient,
    my_games_factory,
):
    user = create_user(client)
    now = datetime.now(UTC).replace(microsecond=0)
    owned_statuses = ["active", "completed", "expired"]
    owned_posts = [
        my_games_factory.create_sub_post(
            owner_user_id=user["id"],
            starts_at=now - timedelta(days=index + 3, hours=2),
            ends_at=now - timedelta(days=index + 3),
            post_status=post_status,
        )[0]
        for index, post_status in enumerate(owned_statuses)
    ]
    confirmed, _, _ = _create_confirmed_request_post(
        my_games_factory,
        requester_id=user["id"],
        starts_at=now - timedelta(days=8, hours=2),
        ends_at=now - timedelta(days=8),
        post_status="completed",
    )

    authenticate_as(user["id"])
    response = client.get("/my-games/need-a-sub", params={"view": "history"})

    assert response.status_code == 200, response.text
    items_by_id = _sub_items_by_id(response.json())
    assert {str(post.id) for post in owned_posts} | {str(confirmed.id)} == set(
        items_by_id
    )
    for item in items_by_id.values():
        assert item["status_label"] == "Ended"
        assert item["status_tone"] == "ended"


@pytest.mark.parametrize(
    "request_status",
    [
        "pending",
        "sub_waitlist",
        "declined",
        "canceled_by_player",
        "expired",
        "no_show_reported",
        "closed_by_admin",
    ],
)
def test_need_a_sub_history_excludes_non_confirmed_past_relationships(
    client: TestClient,
    my_games_factory,
    request_status: str,
):
    user = create_user(client)
    owner = create_user(client)
    now = datetime.now(UTC).replace(microsecond=0)
    post, position = my_games_factory.create_sub_post(
        owner_user_id=owner["id"],
        starts_at=now - timedelta(days=5, hours=2),
        ends_at=now - timedelta(days=5),
        post_status="completed",
    )
    my_games_factory.create_sub_request(
        post_id=post.id,
        position_id=position.id,
        requester_user_id=user["id"],
        request_status=request_status,
    )

    authenticate_as(user["id"])
    response = client.get("/my-games/need-a-sub", params={"view": "history"})

    assert response.status_code == 200, response.text
    assert response.json()["items"] == []


def test_need_a_sub_history_excludes_admin_removed_owned_and_confirmed_requester_posts(
    client: TestClient,
    my_games_factory,
):
    user = create_user(client)
    admin = create_user(client)
    other_owner = create_user(client)
    now = datetime.now(UTC).replace(microsecond=0)
    owned, _ = my_games_factory.create_sub_post(
        owner_user_id=user["id"],
        starts_at=now - timedelta(days=5, hours=2),
        ends_at=now - timedelta(days=5),
        post_status="removed",
        removed_by_user_id=admin["id"],
    )
    confirmed, position = my_games_factory.create_sub_post(
        owner_user_id=other_owner["id"],
        starts_at=now - timedelta(days=6, hours=2),
        ends_at=now - timedelta(days=6),
        post_status="removed",
        removed_by_user_id=admin["id"],
    )
    my_games_factory.create_sub_request(
        post_id=confirmed.id,
        position_id=position.id,
        requester_user_id=user["id"],
        request_status="confirmed",
    )

    authenticate_as(user["id"])
    response = client.get("/my-games/need-a-sub", params={"view": "history"})

    assert response.status_code == 200, response.text
    assert not {str(owned.id), str(confirmed.id)} & {
        item["post"]["id"] for item in response.json()["items"]
    }


def test_need_a_sub_cancelled_history_requires_whole_post_cancellation_proof(
    client: TestClient,
    my_games_factory,
):
    user = create_user(client)
    now = datetime.now(UTC).replace(microsecond=0)
    owner_post, _ = my_games_factory.create_sub_post(
        owner_user_id=user["id"],
        starts_at=now + timedelta(days=2),
        post_status="cancelled",
    )
    confirmed, _ = _create_cancelled_confirmed_request_post(
        my_games_factory,
        requester_id=user["id"],
        starts_at=now + timedelta(days=3),
    )
    stale_confirmed, _ = _create_cancelled_confirmed_request_post(
        my_games_factory,
        requester_id=user["id"],
        starts_at=now - timedelta(days=3, hours=2),
        ends_at=now - timedelta(days=3),
        request_is_still_confirmed=True,
    )
    bad_old_status, _ = _create_cancelled_confirmed_request_post(
        my_games_factory,
        requester_id=user["id"],
        starts_at=now + timedelta(days=4),
        old_status="sub_waitlist",
    )
    bad_source, _ = _create_cancelled_confirmed_request_post(
        my_games_factory,
        requester_id=user["id"],
        starts_at=now + timedelta(days=5),
        change_source="requester",
    )
    bad_timestamp, _ = _create_cancelled_confirmed_request_post(
        my_games_factory,
        requester_id=user["id"],
        starts_at=now + timedelta(days=6),
        history_created_at_delta=timedelta(minutes=1),
    )
    bad_request_timestamp, _ = _create_cancelled_confirmed_request_post(
        my_games_factory,
        requester_id=user["id"],
        starts_at=now + timedelta(days=7),
        request_canceled_at_delta=timedelta(minutes=1),
    )
    bad_newer_history, _ = _create_cancelled_confirmed_request_post(
        my_games_factory,
        requester_id=user["id"],
        starts_at=now + timedelta(days=8),
        add_newer_history=True,
    )

    authenticate_as(user["id"])
    response = client.get("/my-games/need-a-sub", params={"view": "history"})

    assert response.status_code == 200, response.text
    items_by_id = _sub_items_by_id(response.json())
    assert set(items_by_id) == {str(owner_post.id), str(confirmed.id)}
    assert items_by_id[str(owner_post.id)]["status_label"] == "Cancelled"
    assert items_by_id[str(confirmed.id)]["status_label"] == "Cancelled"
    assert not {
        str(post.id)
        for post in (
            stale_confirmed,
            bad_old_status,
            bad_source,
            bad_timestamp,
            bad_request_timestamp,
            bad_newer_history,
        )
    } & set(items_by_id)


def test_need_a_sub_exact_boundary_and_sixty_day_scheduled_history_window(
    client: TestClient,
    my_games_factory,
    freeze_my_games_now,
    backend_test_evidence,
):
    owner = create_user(client)
    frozen_now = datetime(2026, 8, 10, 18, 0, tzinfo=UTC)
    freeze_my_games_now(frozen_now)
    boundary, _ = my_games_factory.create_sub_post(
        owner_user_id=owner["id"],
        starts_at=frozen_now - timedelta(hours=2),
        ends_at=frozen_now,
        post_status="active",
    )
    old_post, _ = my_games_factory.create_sub_post(
        owner_user_id=owner["id"],
        starts_at=frozen_now - timedelta(days=61, hours=2),
        ends_at=frozen_now - timedelta(days=61),
        post_status="completed",
    )
    future_cancelled, _ = my_games_factory.create_sub_post(
        owner_user_id=owner["id"],
        starts_at=frozen_now + timedelta(days=3),
        ends_at=frozen_now + timedelta(days=3, hours=2),
        post_status="cancelled",
        canceled_at=frozen_now,
        canceled_by_user_id=owner["id"],
    )
    old_cancelled, _ = my_games_factory.create_sub_post(
        owner_user_id=owner["id"],
        starts_at=frozen_now - timedelta(days=61, hours=2),
        ends_at=frozen_now - timedelta(days=61),
        post_status="cancelled",
        canceled_at=frozen_now,
        canceled_by_user_id=owner["id"],
    )

    authenticate_as(owner["id"])
    upcoming_response = client.get(
        "/my-games/need-a-sub",
        params={"view": "upcoming"},
    )
    history_response = client.get(
        "/my-games/need-a-sub",
        params={"view": "history"},
    )

    assert upcoming_response.status_code == 200, upcoming_response.text
    assert history_response.status_code == 200, history_response.text
    upcoming_ids = {
        item["post"]["id"] for item in upcoming_response.json()["items"]
    }
    history_ids = {item["post"]["id"] for item in history_response.json()["items"]}
    assert_time_boundary(
        backend_test_evidence,
        time_id="TIME-SUB-EXACT-AND-WINDOW",
        baseline=frozen_now.isoformat(),
        boundary="at_ends_at",
        actual=str(boundary.id) not in upcoming_ids and str(boundary.id) in history_ids,
        expected=True,
    )
    assert_time_boundary(
        backend_test_evidence,
        time_id="TIME-SUB-EXACT-AND-WINDOW",
        baseline=frozen_now.isoformat(),
        boundary="sixty_day_window",
        actual=str(boundary.id) in history_ids,
        expected=True,
    )
    assert_time_boundary(
        backend_test_evidence,
        time_id="TIME-SUB-EXACT-AND-WINDOW",
        baseline=frozen_now.isoformat(),
        boundary="older_than_sixty_days",
        actual=str(old_post.id) not in history_ids and str(old_cancelled.id) not in history_ids,
        expected=True,
    )
    assert_time_boundary(
        backend_test_evidence,
        time_id="TIME-SUB-EXACT-AND-WINDOW",
        baseline=frozen_now.isoformat(),
        boundary="future_cancelled_immediate",
        actual=str(future_cancelled.id) in history_ids,
        expected=True,
    )
