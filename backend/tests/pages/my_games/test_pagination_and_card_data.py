from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import UTC, datetime, timedelta
from json import dumps, loads
from uuid import UUID

from fastapi.testclient import TestClient
import pytest

from backend.tests.support.auth import authenticate_as
from backend.tests.support.factories import create_user
from backend.tests.support.my_games_cursors import make_my_games_cursor


def _game_ids(body: dict) -> list[str]:
    return [item["game"]["id"] for item in body["items"]]


def _sub_post_ids(body: dict) -> list[str]:
    return [item["post"]["id"] for item in body["items"]]


def _cursor_from_payload(payload: dict) -> str:
    serialized = dumps(payload, separators=(",", ":"), sort_keys=True).encode(
        "utf-8"
    )
    return urlsafe_b64encode(serialized).decode("ascii")


def _cursor_payload(cursor: str) -> dict:
    return loads(urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8"))


def test_exact_limit_page_has_no_next_cursor_for_both_my_games_domains(
    client: TestClient,
    my_games_factory,
):
    user = create_user(client)
    now = datetime.now(UTC).replace(microsecond=0)
    my_games_factory.create_game(
        user_id=user["id"],
        starts_at=now + timedelta(days=7),
    )
    my_games_factory.create_game(
        user_id=user["id"],
        starts_at=now + timedelta(days=8),
    )
    my_games_factory.create_sub_post(
        owner_user_id=user["id"],
        starts_at=now + timedelta(days=7),
    )
    my_games_factory.create_sub_post(
        owner_user_id=user["id"],
        starts_at=now + timedelta(days=8),
    )

    authenticate_as(user["id"])
    games_response = client.get(
        "/my-games",
        params={"view": "upcoming", "limit": 2},
    )
    sub_response = client.get(
        "/my-games/need-a-sub",
        params={"view": "upcoming", "limit": 2},
    )

    assert games_response.status_code == 200, games_response.text
    assert sub_response.status_code == 200, sub_response.text
    for body in (games_response.json(), sub_response.json()):
        assert body["limit"] == 2
        assert body["has_more"] is False
        assert body["next_cursor"] is None
        assert len(body["items"]) == 2


def test_games_pagination_sorts_by_starts_at_created_at_and_id_without_duplicates(
    client: TestClient,
    my_games_factory,
):
    user = create_user(client)
    now = datetime.now(UTC).replace(microsecond=0)
    starts_at = now + timedelta(days=7)
    same_created_at = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
    ordered_ids = [
        UUID("00000000-0000-4000-8000-000000000001"),
        UUID("00000000-0000-4000-8000-000000000002"),
        UUID("00000000-0000-4000-8000-000000000003"),
    ]
    for game_id in ordered_ids:
        my_games_factory.create_game(
            id=game_id,
            user_id=user["id"],
            starts_at=starts_at,
            created_at=same_created_at,
            game_type="official",
            payment_collection_type="in_app",
            policy_mode="official_standard",
        )

    authenticate_as(user["id"])
    first_page = client.get("/my-games", params={"view": "upcoming", "limit": 2})

    assert first_page.status_code == 200, first_page.text
    first_body = first_page.json()
    assert first_body["has_more"] is True
    assert first_body["next_cursor"]
    assert _game_ids(first_body) == [str(ordered_ids[0]), str(ordered_ids[1])]

    second_page = client.get(
        "/my-games",
        params={
            "view": "upcoming",
            "limit": 2,
            "cursor": first_body["next_cursor"],
        },
    )

    assert second_page.status_code == 200, second_page.text
    second_body = second_page.json()
    assert _game_ids(second_body) == [str(ordered_ids[2])]
    assert second_body["has_more"] is False
    assert second_body["next_cursor"] is None
    assert _game_ids(first_body) + _game_ids(second_body) == [
        str(game_id) for game_id in ordered_ids
    ]


def test_my_games_three_page_cursor_pagination_covers_middle_page_for_both_domains(
    client: TestClient,
    freeze_my_games_now,
    my_games_factory,
):
    user = create_user(client)
    now = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)
    freeze_my_games_now(now)
    starts_at = now + timedelta(days=7)
    created_at = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
    game_ids = [
        UUID("00000000-0000-4000-8000-000000000021"),
        UUID("00000000-0000-4000-8000-000000000022"),
        UUID("00000000-0000-4000-8000-000000000023"),
        UUID("00000000-0000-4000-8000-000000000024"),
        UUID("00000000-0000-4000-8000-000000000025"),
    ]
    sub_post_ids = [
        UUID("00000000-0000-4000-8000-000000000031"),
        UUID("00000000-0000-4000-8000-000000000032"),
        UUID("00000000-0000-4000-8000-000000000033"),
        UUID("00000000-0000-4000-8000-000000000034"),
        UUID("00000000-0000-4000-8000-000000000035"),
    ]

    for game_id in game_ids:
        my_games_factory.create_game(
            id=game_id,
            user_id=user["id"],
            starts_at=starts_at,
            created_at=created_at,
            game_type="official",
            payment_collection_type="in_app",
            policy_mode="official_standard",
        )
    for index, post_id in enumerate(sub_post_ids):
        my_games_factory.create_sub_post(
            id=post_id,
            owner_user_id=user["id"],
            starts_at=starts_at + timedelta(days=index),
            created_at=created_at,
        )

    authenticate_as(user["id"])
    games_first = client.get("/my-games", params={"view": "upcoming", "limit": 2})
    sub_first = client.get(
        "/my-games/need-a-sub",
        params={"view": "upcoming", "limit": 2},
    )

    assert games_first.status_code == 200, games_first.text
    assert sub_first.status_code == 200, sub_first.text

    games_first_body = games_first.json()
    sub_first_body = sub_first.json()
    assert _game_ids(games_first_body) == [str(game_ids[0]), str(game_ids[1])]
    assert _sub_post_ids(sub_first_body) == [
        str(sub_post_ids[0]),
        str(sub_post_ids[1]),
    ]
    assert games_first_body["has_more"] is True
    assert sub_first_body["has_more"] is True
    assert games_first_body["next_cursor"]
    assert sub_first_body["next_cursor"]

    games_middle = client.get(
        "/my-games",
        params={
            "view": "upcoming",
            "limit": 2,
            "cursor": games_first_body["next_cursor"],
        },
    )
    sub_middle = client.get(
        "/my-games/need-a-sub",
        params={
            "view": "upcoming",
            "limit": 2,
            "cursor": sub_first_body["next_cursor"],
        },
    )

    assert games_middle.status_code == 200, games_middle.text
    assert sub_middle.status_code == 200, sub_middle.text
    games_middle_body = games_middle.json()
    sub_middle_body = sub_middle.json()
    assert _game_ids(games_middle_body) == [str(game_ids[2]), str(game_ids[3])]
    assert _sub_post_ids(sub_middle_body) == [
        str(sub_post_ids[2]),
        str(sub_post_ids[3]),
    ]
    assert games_middle_body["has_more"] is True
    assert sub_middle_body["has_more"] is True
    assert games_middle_body["next_cursor"]
    assert sub_middle_body["next_cursor"]

    games_final = client.get(
        "/my-games",
        params={
            "view": "upcoming",
            "limit": 2,
            "cursor": games_middle_body["next_cursor"],
        },
    )
    sub_final = client.get(
        "/my-games/need-a-sub",
        params={
            "view": "upcoming",
            "limit": 2,
            "cursor": sub_middle_body["next_cursor"],
        },
    )

    assert games_final.status_code == 200, games_final.text
    assert sub_final.status_code == 200, sub_final.text
    games_final_body = games_final.json()
    sub_final_body = sub_final.json()
    assert _game_ids(games_final_body) == [str(game_ids[4])]
    assert _sub_post_ids(sub_final_body) == [str(sub_post_ids[4])]
    assert games_final_body["has_more"] is False
    assert sub_final_body["has_more"] is False
    assert games_final_body["next_cursor"] is None
    assert sub_final_body["next_cursor"] is None

    all_game_ids = (
        _game_ids(games_first_body)
        + _game_ids(games_middle_body)
        + _game_ids(games_final_body)
    )
    all_sub_post_ids = (
        _sub_post_ids(sub_first_body)
        + _sub_post_ids(sub_middle_body)
        + _sub_post_ids(sub_final_body)
    )
    assert all_game_ids == [str(game_id) for game_id in game_ids]
    assert all_sub_post_ids == [str(post_id) for post_id in sub_post_ids]
    assert len(all_game_ids) == len(set(all_game_ids))
    assert len(all_sub_post_ids) == len(set(all_sub_post_ids))

    games_first_cursor = _cursor_payload(games_first_body["next_cursor"])
    games_middle_cursor = _cursor_payload(games_middle_body["next_cursor"])
    sub_first_cursor = _cursor_payload(sub_first_body["next_cursor"])
    sub_middle_cursor = _cursor_payload(sub_middle_body["next_cursor"])
    assert games_first_cursor["domain"] == "games"
    assert games_middle_cursor["domain"] == "games"
    assert sub_first_cursor["domain"] == "need-a-sub"
    assert sub_middle_cursor["domain"] == "need-a-sub"
    assert games_first_cursor["view"] == "upcoming"
    assert games_middle_cursor["view"] == "upcoming"
    assert sub_first_cursor["view"] == "upcoming"
    assert sub_middle_cursor["view"] == "upcoming"
    assert games_first_cursor["sort_direction"] == "asc"
    assert games_middle_cursor["sort_direction"] == "asc"
    assert sub_first_cursor["sort_direction"] == "asc"
    assert sub_middle_cursor["sort_direction"] == "asc"
    assert games_first_cursor["id"] == str(game_ids[1])
    assert games_middle_cursor["id"] == str(game_ids[3])
    assert sub_first_cursor["id"] == str(sub_post_ids[1])
    assert sub_middle_cursor["id"] == str(sub_post_ids[3])


def test_games_history_pagination_sorts_descending_and_survives_limit_change(
    client: TestClient,
    my_games_factory,
):
    user = create_user(client)
    now = datetime.now(UTC).replace(microsecond=0)
    ordered_games = []
    for index in range(4):
        start = now - timedelta(days=index + 3, hours=2)
        ordered_games.append(
            my_games_factory.create_game(
                user_id=user["id"],
                starts_at=start,
                ends_at=start + timedelta(hours=1),
                game_status="completed",
                created_at=datetime(2026, 7, 1, 12, index, tzinfo=UTC),
            )
        )

    authenticate_as(user["id"])
    first_page = client.get("/my-games", params={"view": "history", "limit": 1})

    assert first_page.status_code == 200, first_page.text
    first_body = first_page.json()
    assert _game_ids(first_body) == [str(ordered_games[0].id)]
    assert first_body["has_more"] is True

    second_page = client.get(
        "/my-games",
        params={
            "view": "history",
            "limit": 3,
            "cursor": first_body["next_cursor"],
        },
    )

    assert second_page.status_code == 200, second_page.text
    second_body = second_page.json()
    assert _game_ids(second_body) == [str(game.id) for game in ordered_games[1:]]
    assert second_body["has_more"] is False
    assert second_body["next_cursor"] is None


def test_games_card_metadata_is_loaded_after_paging_without_duplicate_cards(
    client: TestClient,
    my_games_factory,
):
    host = create_user(client)
    player_one = create_user(client)
    player_two = create_user(client)
    now = datetime.now(UTC).replace(microsecond=0)
    game = my_games_factory.create_game(
        user_id=host["id"],
        starts_at=now + timedelta(days=7),
        total_spots=6,
    )
    my_games_factory.create_participant(
        game_id=game.id,
        user_id=host["id"],
        participant_status="confirmed",
    )
    my_games_factory.create_participant(
        game_id=game.id,
        user_id=host["id"],
        participant_status="cancelled",
        cancellation_type="host_cancelled",
    )
    my_games_factory.create_participant(
        game_id=game.id,
        user_id=player_one["id"],
        participant_status="confirmed",
        roster_order=2,
    )
    my_games_factory.create_participant(
        game_id=game.id,
        user_id=player_two["id"],
        participant_status="confirmed",
        roster_order=3,
    )
    cancelled = my_games_factory.create_participant(
        game_id=game.id,
        user_id=player_two["id"],
        participant_status="cancelled",
        cancellation_type="host_cancelled",
        roster_order=4,
    )
    my_games_factory.create_participant_history(
        participant_id=cancelled.id,
        old_status="confirmed",
        new_status="cancelled",
        change_source="host",
        created_at=datetime.now(UTC).replace(microsecond=0),
    )
    my_games_factory.create_game_image(
        game_id=game.id,
        image_url="https://example.com/my-games-primary.jpg",
        is_primary=True,
        sort_order=0,
    )
    my_games_factory.create_game_image(
        game_id=game.id,
        image_url="https://example.com/my-games-gallery.jpg",
        is_primary=False,
        sort_order=1,
    )

    authenticate_as(host["id"])
    response = client.get("/my-games", params={"view": "upcoming"})

    assert response.status_code == 200, response.text
    body = response.json()
    assert _game_ids(body) == [str(game.id)]
    [item] = body["items"]
    assert item["status_label"] == "Hosting"
    assert item["game"]["participant_count"] == 3
    assert item["game"]["primary_image_url"] == (
        "https://example.com/my-games-primary.jpg"
    )
    assert item["game"]["availability"]["total_spots"] == 6
    assert "cancel_reason" not in item["game"]


def test_need_a_sub_pagination_sorts_by_starts_at_created_at_and_id_without_duplicates(
    client: TestClient,
    my_games_factory,
):
    requester = create_user(client)
    now = datetime.now(UTC).replace(microsecond=0)
    starts_at = now + timedelta(days=7)
    same_created_at = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
    ordered_ids = [
        UUID("00000000-0000-4000-8000-000000000011"),
        UUID("00000000-0000-4000-8000-000000000012"),
        UUID("00000000-0000-4000-8000-000000000013"),
    ]
    for index, post_id in enumerate(ordered_ids):
        owner = create_user(client)
        post, position = my_games_factory.create_sub_post(
            id=post_id,
            owner_user_id=owner["id"],
            starts_at=starts_at,
            created_at=same_created_at,
        )
        my_games_factory.create_sub_request(
            post_id=post.id,
            position_id=position.id,
            requester_user_id=requester["id"],
            request_status="confirmed",
            created_at=same_created_at + timedelta(minutes=index),
        )

    authenticate_as(requester["id"])
    first_page = client.get(
        "/my-games/need-a-sub",
        params={"view": "upcoming", "limit": 2},
    )

    assert first_page.status_code == 200, first_page.text
    first_body = first_page.json()
    assert first_body["has_more"] is True
    assert _sub_post_ids(first_body) == [str(ordered_ids[0]), str(ordered_ids[1])]

    second_page = client.get(
        "/my-games/need-a-sub",
        params={
            "view": "upcoming",
            "limit": 2,
            "cursor": first_body["next_cursor"],
        },
    )

    assert second_page.status_code == 200, second_page.text
    second_body = second_page.json()
    assert _sub_post_ids(second_body) == [str(ordered_ids[2])]
    assert second_body["has_more"] is False
    assert second_body["next_cursor"] is None


def test_need_a_sub_history_three_page_cursor_pagination_sorts_descending_without_duplicates(
    client: TestClient,
    my_games_factory,
):
    user = create_user(client)
    now = datetime.now(UTC).replace(microsecond=0)
    created_at = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
    ordered_ids = [
        UUID("00000000-0000-4000-8000-000000000041"),
        UUID("00000000-0000-4000-8000-000000000042"),
        UUID("00000000-0000-4000-8000-000000000043"),
        UUID("00000000-0000-4000-8000-000000000044"),
        UUID("00000000-0000-4000-8000-000000000045"),
    ]
    for index, post_id in enumerate(ordered_ids):
        start = now - timedelta(days=index + 3, hours=2)
        my_games_factory.create_sub_post(
            id=post_id,
            owner_user_id=user["id"],
            starts_at=start,
            ends_at=start + timedelta(hours=1),
            post_status="completed",
            created_at=created_at + timedelta(minutes=index),
        )

    authenticate_as(user["id"])
    first_page = client.get(
        "/my-games/need-a-sub",
        params={"view": "history", "limit": 2},
    )

    assert first_page.status_code == 200, first_page.text
    first_body = first_page.json()
    assert _sub_post_ids(first_body) == [str(ordered_ids[0]), str(ordered_ids[1])]
    assert first_body["has_more"] is True
    assert first_body["next_cursor"]

    middle_page = client.get(
        "/my-games/need-a-sub",
        params={
            "view": "history",
            "limit": 2,
            "cursor": first_body["next_cursor"],
        },
    )

    assert middle_page.status_code == 200, middle_page.text
    middle_body = middle_page.json()
    assert _sub_post_ids(middle_body) == [str(ordered_ids[2]), str(ordered_ids[3])]
    assert middle_body["has_more"] is True
    assert middle_body["next_cursor"]

    final_page = client.get(
        "/my-games/need-a-sub",
        params={
            "view": "history",
            "limit": 2,
            "cursor": middle_body["next_cursor"],
        },
    )

    assert final_page.status_code == 200, final_page.text
    final_body = final_page.json()
    assert _sub_post_ids(final_body) == [str(ordered_ids[4])]
    assert final_body["has_more"] is False
    assert final_body["next_cursor"] is None

    all_ids = (
        _sub_post_ids(first_body)
        + _sub_post_ids(middle_body)
        + _sub_post_ids(final_body)
    )
    assert all_ids == [str(post_id) for post_id in ordered_ids]
    assert len(all_ids) == len(set(all_ids))

    first_cursor = _cursor_payload(first_body["next_cursor"])
    middle_cursor = _cursor_payload(middle_body["next_cursor"])
    assert first_cursor["domain"] == "need-a-sub"
    assert middle_cursor["domain"] == "need-a-sub"
    assert first_cursor["view"] == "history"
    assert middle_cursor["view"] == "history"
    assert first_cursor["sort_direction"] == "desc"
    assert middle_cursor["sort_direction"] == "desc"
    assert first_cursor["id"] == str(ordered_ids[1])
    assert middle_cursor["id"] == str(ordered_ids[3])


def test_need_a_sub_card_data_is_loaded_after_paging_without_duplicate_cards(
    client: TestClient,
    my_games_factory,
):
    owner = create_user(client)
    requester = create_user(client)
    other_requester = create_user(client)
    now = datetime.now(UTC).replace(microsecond=0)
    post, position = my_games_factory.create_sub_post(
        owner_user_id=owner["id"],
        starts_at=now + timedelta(days=7),
        subs_needed=2,
    )
    my_games_factory.create_sub_position(
        post_id=post.id,
        position_label="goalkeeper",
        player_group="open",
        sort_order=1,
    )
    my_games_factory.create_sub_request(
        post_id=post.id,
        position_id=position.id,
        requester_user_id=requester["id"],
        request_status="confirmed",
    )
    my_games_factory.create_sub_request(
        post_id=post.id,
        position_id=position.id,
        requester_user_id=requester["id"],
        request_status="canceled_by_player",
    )
    my_games_factory.create_sub_request(
        post_id=post.id,
        position_id=position.id,
        requester_user_id=other_requester["id"],
        request_status="pending",
    )
    my_games_factory.create_sub_request(
        post_id=post.id,
        position_id=position.id,
        requester_user_id=other_requester["id"],
        request_status="declined",
    )

    authenticate_as(requester["id"])
    response = client.get("/my-games/need-a-sub", params={"view": "upcoming"})

    assert response.status_code == 200, response.text
    body = response.json()
    assert _sub_post_ids(body) == [str(post.id)]
    [item] = body["items"]
    assert item["is_owner"] is False
    assert item["request_status"] == "confirmed"
    assert item["status_label"] == "Confirmed"
    assert item["post"]["subs_needed"] == 2
    assert len(item["post"]["positions"]) == 2
    assert item["post"]["confirmed_count"] == 1
    assert item["post"]["pending_count"] == 1


@pytest.mark.parametrize(
    ("path", "cursor", "expected_detail"),
    [
        ("/my-games", "not-a-valid-cursor", "cursor is invalid"),
        (
            "/my-games",
            make_my_games_cursor(extra_payload={"starts_at": 1}),
            "cursor is invalid",
        ),
        (
            "/my-games",
            make_my_games_cursor(extra_payload={"starts_at": "not-a-date"}),
            "cursor is invalid",
        ),
        (
            "/my-games",
            _cursor_from_payload(
                {
                    "domain": "games",
                    "view": "upcoming",
                    "sort_direction": "asc",
                }
            ),
            "cursor is invalid",
        ),
        (
            "/my-games",
            make_my_games_cursor(extra_payload={"id": "not-a-uuid"}),
            "cursor is invalid",
        ),
        (
            "/my-games",
            make_my_games_cursor(sort_direction="desc"),
            "cursor does not match",
        ),
        (
            "/my-games/need-a-sub",
            "not-a-valid-cursor",
            "cursor is invalid",
        ),
        (
            "/my-games/need-a-sub",
            make_my_games_cursor(domain="need-a-sub", extra_payload={"created_at": 1}),
            "cursor is invalid",
        ),
        (
            "/my-games/need-a-sub",
            make_my_games_cursor(
                domain="need-a-sub",
                extra_payload={"created_at": "not-a-date"},
            ),
            "cursor is invalid",
        ),
        (
            "/my-games/need-a-sub",
            _cursor_from_payload(
                {
                    "domain": "need-a-sub",
                    "view": "upcoming",
                    "sort_direction": "asc",
                }
            ),
            "cursor is invalid",
        ),
        (
            "/my-games/need-a-sub",
            make_my_games_cursor(domain="need-a-sub", extra_payload={"id": "nope"}),
            "cursor is invalid",
        ),
        (
            "/my-games/need-a-sub",
            make_my_games_cursor(domain="need-a-sub", sort_direction="desc"),
            "cursor does not match",
        ),
    ],
)
def test_my_games_invalid_cursor_payloads_return_client_error(
    client: TestClient,
    path: str,
    cursor: str,
    expected_detail: str,
):
    user = create_user(client)
    authenticate_as(user["id"])

    response = client.get(path, params={"view": "upcoming", "cursor": cursor})

    assert response.status_code == 400, response.text
    assert expected_detail in response.text


def test_my_games_cursors_are_bound_to_domain_and_view(
    client: TestClient,
    my_games_factory,
):
    user = create_user(client)
    now = datetime.now(UTC).replace(microsecond=0)
    first_game = my_games_factory.create_game(
        user_id=user["id"],
        starts_at=now + timedelta(days=7),
    )
    second_game = my_games_factory.create_game(
        user_id=user["id"],
        starts_at=now + timedelta(days=8),
    )
    first_post, _ = my_games_factory.create_sub_post(
        owner_user_id=user["id"],
        starts_at=now + timedelta(days=7),
    )
    my_games_factory.create_sub_post(
        owner_user_id=user["id"],
        starts_at=now + timedelta(days=8),
    )

    authenticate_as(user["id"])
    games_page = client.get("/my-games", params={"view": "upcoming", "limit": 1})
    sub_page = client.get(
        "/my-games/need-a-sub",
        params={"view": "upcoming", "limit": 1},
    )

    assert games_page.status_code == 200, games_page.text
    assert sub_page.status_code == 200, sub_page.text
    games_cursor = games_page.json()["next_cursor"]
    sub_cursor = sub_page.json()["next_cursor"]
    assert games_cursor
    assert sub_cursor
    assert _game_ids(games_page.json()) == [str(first_game.id)]
    assert sub_page.json()["items"][0]["post"]["id"] == str(first_post.id)

    games_with_sub_cursor = client.get(
        "/my-games",
        params={"view": "upcoming", "cursor": sub_cursor},
    )
    sub_with_games_cursor = client.get(
        "/my-games/need-a-sub",
        params={"view": "upcoming", "cursor": games_cursor},
    )
    games_history_with_upcoming_cursor = client.get(
        "/my-games",
        params={"view": "history", "cursor": games_cursor},
    )
    sub_history_with_upcoming_cursor = client.get(
        "/my-games/need-a-sub",
        params={"view": "history", "cursor": sub_cursor},
    )

    for response in (
        games_with_sub_cursor,
        sub_with_games_cursor,
        games_history_with_upcoming_cursor,
        sub_history_with_upcoming_cursor,
    ):
        assert response.status_code == 400, response.text
        assert "cursor does not match" in response.text
