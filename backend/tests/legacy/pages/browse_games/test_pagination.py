from datetime import UTC, datetime, timedelta, tzinfo
from typing import Callable
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
import pytest

from backend.tests.support.api_helpers import (
    create_game,
    create_game_image,
    create_game_participant,
    create_venue,
)
from backend.tests.support.factories import create_user
from backend.tests.support.time import local_date_string


def _create_ordered_browse_games(
    client: TestClient,
    *,
    admin_id: str,
    venue: dict,
    starts_at_values: list[datetime],
    title_prefix: str,
) -> list[dict]:
    games: list[dict] = []
    for index, starts_at in enumerate(starts_at_values, start=1):
        game = create_game(
            client,
            admin_id,
            venue,
            title=f"{title_prefix} {index}",
            starts_at=starts_at.isoformat(),
            ends_at=(starts_at + timedelta(hours=1)).isoformat(),
        )
        games.append(game)
    return games


def test_browse_game_cards_cursor_paginates_in_stable_order(
    client: TestClient,
):
    admin = create_user(client)
    venue = create_venue(client, admin["id"])
    base_start = (
        datetime.now(UTC).replace(hour=18, minute=0, second=0, microsecond=0)
        + timedelta(days=7)
    )

    game_ids: list[str] = []
    for index in range(3):
        starts_at = base_start + timedelta(hours=index)
        game = create_game(
            client,
            admin["id"],
            venue,
            title=f"Browse Card {index + 1}",
            starts_at=starts_at.isoformat(),
            ends_at=(starts_at + timedelta(hours=1)).isoformat(),
        )
        game_ids.append(game["id"])

    starts_on = local_date_string(base_start, "America/Chicago")
    first_page = client.get(
        "/games/browse",
        params={"starts_on": starts_on, "limit": 2},
    )

    assert first_page.status_code == 200, first_page.text
    first_body = first_page.json()
    assert first_body["limit"] == 2
    assert first_body["has_more"] is True
    assert first_body["next_cursor"]
    assert [item["id"] for item in first_body["games"]] == game_ids[:2]

    second_page = client.get(
        "/games/browse",
        params={
            "starts_on": starts_on,
            "limit": 2,
            "cursor": first_body["next_cursor"],
        },
    )
    assert second_page.status_code == 200, second_page.text
    second_body = second_page.json()
    assert [item["id"] for item in second_body["games"]] == [game_ids[2]]
    assert second_body["has_more"] is False
    assert second_body["next_cursor"] is None
    assert {
        item["id"] for item in [*first_body["games"], *second_body["games"]]
    } == set(game_ids)


def test_browse_game_cards_exact_limit_page_has_no_next_cursor(
    client: TestClient,
):
    admin = create_user(client)
    venue = create_venue(client, admin["id"])
    base_start = (
        datetime.now(UTC).replace(hour=18, minute=0, second=0, microsecond=0)
        + timedelta(days=7)
    )

    game_ids: list[str] = []
    for index in range(2):
        starts_at = base_start + timedelta(hours=index)
        game = create_game(
            client,
            admin["id"],
            venue,
            title=f"Exact Limit Browse Card {index + 1}",
            starts_at=starts_at.isoformat(),
            ends_at=(starts_at + timedelta(hours=1)).isoformat(),
        )
        game_ids.append(game["id"])

    response = client.get(
        "/games/browse",
        params={
            "starts_on": local_date_string(base_start, "America/Chicago"),
            "limit": 2,
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["limit"] == 2
    assert body["has_more"] is False
    assert body["next_cursor"] is None
    assert [item["id"] for item in body["games"]] == game_ids


def test_browse_game_cards_include_loaded_card_metadata(
    client: TestClient,
):
    admin = create_user(client)
    player = create_user(client)
    second_player = create_user(client)
    venue = create_venue(client, admin["id"])
    browse_local_start = (
        datetime.now(ZoneInfo("America/Chicago")) + timedelta(days=7)
    ).replace(hour=18, minute=0, second=0, microsecond=0)
    starts_at = browse_local_start.astimezone(UTC)
    game = create_game(
        client,
        admin["id"],
        venue,
        title="Browse Metadata Card",
        starts_at=starts_at.isoformat(),
        ends_at=(starts_at + timedelta(hours=1)).isoformat(),
    )
    create_game_participant(client, player["id"], game["id"])
    create_game_participant(
        client,
        second_player["id"],
        game["id"],
        roster_order=2,
    )
    create_game_image(
        client,
        game["id"],
        admin["id"],
        image_url="https://example.com/browse-primary.jpg",
        image_status="active",
        is_primary=True,
    )

    response = client.get(
        "/games/browse",
        params={"starts_on": local_date_string(starts_at, "America/Chicago")},
    )

    assert response.status_code == 200, response.text
    [card] = response.json()["games"]
    assert card["id"] == game["id"]
    assert card["participant_count"] == 2
    assert card["time_group_key"] == "18:00"
    assert card["primary_image_url"] == "https://example.com/browse-primary.jpg"


def test_browse_game_cards_cursor_date_mismatch_returns_400(
    client: TestClient,
):
    admin = create_user(client)
    venue = create_venue(client, admin["id"])
    base_start = (
        datetime.now(UTC).replace(hour=18, minute=0, second=0, microsecond=0)
        + timedelta(days=7)
    )

    for index in range(2):
        starts_at = base_start + timedelta(hours=index)
        create_game(
            client,
            admin["id"],
            venue,
            title=f"Cursor Mismatch Browse Card {index + 1}",
            starts_at=starts_at.isoformat(),
            ends_at=(starts_at + timedelta(hours=1)).isoformat(),
        )

    starts_on = local_date_string(base_start, "America/Chicago")
    first_page = client.get(
        "/games/browse",
        params={"starts_on": starts_on, "limit": 1},
    )
    assert first_page.status_code == 200, first_page.text
    cursor = first_page.json()["next_cursor"]
    assert cursor

    mismatch_response = client.get(
        "/games/browse",
        params={
            "starts_on": local_date_string(
                base_start + timedelta(days=1),
                "America/Chicago",
            ),
            "cursor": cursor,
        },
    )

    assert mismatch_response.status_code == 400, mismatch_response.text
    assert "cursor does not match" in mismatch_response.text


def test_browse_game_cards_sort_equal_start_times_by_created_at_then_id(
    client: TestClient,
    update_browse_game: Callable[..., None],
):
    admin = create_user(client)
    venue = create_venue(client, admin["id"])
    starts_at = (
        datetime.now(UTC).replace(hour=18, minute=0, second=0, microsecond=0)
        + timedelta(days=7)
    )
    same_created_at = datetime(2026, 7, 28, 12, 0, tzinfo=UTC)
    game_ids: list[str] = []
    for index in range(3):
        game = create_game(
            client,
            admin["id"],
            venue,
            title=f"Equal Start Browse Card {index + 1}",
            starts_at=starts_at.isoformat(),
            ends_at=(starts_at + timedelta(hours=1)).isoformat(),
        )
        update_browse_game(game["id"], created_at=same_created_at)
        game_ids.append(game["id"])

    response = client.get(
        "/games/browse",
        params={
            "starts_on": local_date_string(starts_at, "America/Chicago"),
            "limit": 10,
        },
    )

    assert response.status_code == 200, response.text
    expected_ids = [
        str(game_id) for game_id in sorted(UUID(value) for value in game_ids)
    ]
    assert [game["id"] for game in response.json()["games"]] == expected_ids


@pytest.mark.parametrize(
    "ineligible_state",
    ["hidden", "deleted", "cancelled"],
    ids=["hidden", "deleted", "cancelled"],
)
def test_browse_game_cards_cursor_skips_games_made_unlistable_between_pages(
    client: TestClient,
    update_browse_game: Callable[..., None],
    ineligible_state: str,
):
    admin = create_user(client)
    venue = create_venue(client, admin["id"])
    base_start = (
        datetime.now(UTC).replace(hour=18, minute=0, second=0, microsecond=0)
        + timedelta(days=7)
    )
    games = _create_ordered_browse_games(
        client,
        admin_id=admin["id"],
        venue=venue,
        starts_at_values=[base_start + timedelta(hours=index) for index in range(4)],
        title_prefix=f"Cursor Changed {ineligible_state.title()}",
    )
    starts_on = local_date_string(base_start, "America/Chicago")
    first_page = client.get(
        "/games/browse",
        params={"starts_on": starts_on, "limit": 2},
    )
    assert first_page.status_code == 200, first_page.text
    first_body = first_page.json()
    assert [game["id"] for game in first_body["games"]] == [
        games[0]["id"],
        games[1]["id"],
    ]
    assert first_body["next_cursor"]

    changed_game = games[2]
    if ineligible_state == "hidden":
        update_browse_game(
            changed_game["id"],
            public_visibility_status="hidden",
        )
    elif ineligible_state == "deleted":
        update_browse_game(changed_game["id"], deleted_at=datetime.now(UTC))
    else:
        update_browse_game(
            changed_game["id"],
            game_status="cancelled",
            cancelled_at=datetime.now(UTC),
            cancellation_source="system",
            cancel_reason="Browse pagination eligibility changed.",
        )

    second_page = client.get(
        "/games/browse",
        params={
            "starts_on": starts_on,
            "limit": 2,
            "cursor": first_body["next_cursor"],
        },
    )

    assert second_page.status_code == 200, second_page.text
    second_body = second_page.json()
    second_page_ids = [game["id"] for game in second_body["games"]]
    assert second_page_ids == [games[3]["id"]]
    assert changed_game["id"] not in second_page_ids
    assert second_body["has_more"] is False
    assert second_body["next_cursor"] is None


def test_browse_game_cards_cursor_rechecks_registration_cutoff_between_pages(
    client: TestClient,
    monkeypatch,
):
    admin = create_user(client)
    venue = create_venue(client, admin["id"])
    browse_timezone = ZoneInfo("America/Chicago")
    first_now = (datetime.now(browse_timezone) + timedelta(days=7)).replace(
        hour=12,
        minute=0,
        second=0,
        microsecond=0,
    ).astimezone(UTC)
    games = _create_ordered_browse_games(
        client,
        admin_id=admin["id"],
        venue=venue,
        starts_at_values=[
            first_now + timedelta(minutes=30),
            first_now + timedelta(minutes=31),
            first_now + timedelta(minutes=32),
            first_now + timedelta(minutes=40),
        ],
        title_prefix="Cursor Cutoff",
    )
    starts_on = local_date_string(first_now, "America/Chicago")
    group_key = first_now.astimezone(browse_timezone).strftime("%H:00")

    class FrozenDateTime(datetime):
        current = first_now

        @classmethod
        def now(cls, tz: tzinfo | None = None) -> datetime:
            if tz is None:
                return cls.current.replace(tzinfo=None)
            return cls.current.astimezone(tz)

    monkeypatch.setattr("backend.services.game_service.datetime", FrozenDateTime)

    first_page = client.get(
        "/games/browse",
        params={"starts_on": starts_on, "limit": 2},
    )
    assert first_page.status_code == 200, first_page.text
    first_body = first_page.json()
    assert [game["id"] for game in first_body["games"]] == [
        games[0]["id"],
        games[1]["id"],
    ]
    assert first_body["next_cursor"]
    assert first_body["time_groups"] == [
        {"group_key": group_key, "total_games": 4},
    ]

    FrozenDateTime.current = first_now + timedelta(minutes=38)
    second_page = client.get(
        "/games/browse",
        params={
            "starts_on": starts_on,
            "limit": 2,
            "cursor": first_body["next_cursor"],
        },
    )

    assert second_page.status_code == 200, second_page.text
    second_body = second_page.json()
    second_page_ids = [game["id"] for game in second_body["games"]]
    assert second_page_ids == [games[3]["id"]]
    assert games[2]["id"] not in second_page_ids
    assert second_body["time_groups"] == [
        {"group_key": group_key, "total_games": 1},
    ]
    assert second_body["has_more"] is False
    assert second_body["next_cursor"] is None
