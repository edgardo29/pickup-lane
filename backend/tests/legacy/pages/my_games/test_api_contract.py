from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
import pytest

from backend.tests.support.auth import authenticate_as
from backend.tests.support.assertions import assert_private_no_store
from backend.tests.support.factories import create_user


@pytest.mark.parametrize(
    ("path", "params"),
    [
        ("/my-games", {"view": "upcoming"}),
        ("/my-games/need-a-sub", {"view": "upcoming"}),
    ],
)
def test_my_games_endpoints_require_authentication(
    client: TestClient,
    path: str,
    params: dict[str, str],
):
    response = client.get(path, params=params)

    assert response.status_code == 401, response.text


@pytest.mark.parametrize("path", ["/my-games", "/my-games/need-a-sub"])
def test_my_games_endpoints_reject_invalid_view(
    client: TestClient,
    path: str,
):
    user = create_user(client)
    authenticate_as(user["id"])

    response = client.get(path, params={"view": "maybe"})

    assert response.status_code == 400, response.text
    assert "view must be 'upcoming' or 'history'" in response.text


@pytest.mark.parametrize("path", ["/my-games", "/my-games/need-a-sub"])
def test_my_games_empty_response_shape_and_default_limit(
    client: TestClient,
    path: str,
):
    user = create_user(client)
    authenticate_as(user["id"])

    response = client.get(path)

    assert response.status_code == 200, response.text
    assert_private_no_store(response)
    assert response.json() == {
        "items": [],
        "next_cursor": None,
        "has_more": False,
        "limit": 40,
    }


@pytest.mark.parametrize("path", ["/my-games", "/my-games/need-a-sub"])
def test_my_games_limit_validation_accepts_one_hundred_and_caps_above_max(
    client: TestClient,
    path: str,
):
    user = create_user(client)
    authenticate_as(user["id"])

    accepted_response = client.get(path, params={"limit": 100})
    capped_response = client.get(path, params={"limit": 500})
    rejected_response = client.get(path, params={"limit": 0})

    assert accepted_response.status_code == 200, accepted_response.text
    assert accepted_response.json()["limit"] == 100
    assert capped_response.status_code == 200, capped_response.text
    assert capped_response.json()["limit"] == 100
    assert rejected_response.status_code == 422, rejected_response.text


@pytest.mark.parametrize("path", ["/my-games", "/my-games/need-a-sub"])
def test_my_games_cursor_route_validation_uses_two_thousand_character_max(
    client: TestClient,
    path: str,
):
    user = create_user(client)
    authenticate_as(user["id"])

    invalid_cursor_response = client.get(path, params={"cursor": "x" * 2000})
    oversized_cursor_response = client.get(path, params={"cursor": "x" * 2001})

    assert invalid_cursor_response.status_code == 400, invalid_cursor_response.text
    assert oversized_cursor_response.status_code == 422, oversized_cursor_response.text


def test_my_games_response_item_bucket_matches_requested_view(
    client: TestClient,
    my_games_factory,
):
    host = create_user(client)
    now = datetime.now(UTC).replace(microsecond=0)
    my_games_factory.create_game(
        user_id=host["id"],
        starts_at=now + timedelta(days=7),
    )
    my_games_factory.create_game(
        user_id=host["id"],
        starts_at=now - timedelta(days=3, hours=2),
        ends_at=now - timedelta(days=3),
        game_status="completed",
    )

    authenticate_as(host["id"])
    upcoming_response = client.get("/my-games", params={"view": "upcoming"})
    history_response = client.get("/my-games", params={"view": "history"})

    assert upcoming_response.status_code == 200, upcoming_response.text
    assert history_response.status_code == 200, history_response.text
    assert_private_no_store(upcoming_response)
    assert_private_no_store(history_response)
    assert {item["bucket"] for item in upcoming_response.json()["items"]} == {
        "upcoming"
    }
    assert {item["bucket"] for item in history_response.json()["items"]} == {
        "history"
    }


def test_my_need_a_sub_response_item_bucket_matches_requested_view(
    client: TestClient,
    my_games_factory,
):
    owner = create_user(client)
    now = datetime.now(UTC).replace(microsecond=0)
    my_games_factory.create_sub_post(
        owner_user_id=owner["id"],
        starts_at=now + timedelta(days=7),
    )
    my_games_factory.create_sub_post(
        owner_user_id=owner["id"],
        starts_at=now - timedelta(days=3, hours=2),
        ends_at=now - timedelta(days=3),
        post_status="completed",
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
    assert_private_no_store(upcoming_response)
    assert_private_no_store(history_response)
    assert {item["bucket"] for item in upcoming_response.json()["items"]} == {
        "upcoming"
    }
    assert {item["bucket"] for item in history_response.json()["items"]} == {
        "history"
    }
