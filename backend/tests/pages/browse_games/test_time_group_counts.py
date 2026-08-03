from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from backend.tests.support.api_helpers import (
    create_game,
    create_game_participant,
    create_venue,
)
from backend.tests.support.factories import create_user
from backend.tests.support.time import local_date_string


def test_browse_game_cards_return_exact_time_group_totals_across_pages(
    client: TestClient,
):
    admin = create_user(client)
    player = create_user(client)
    venue = create_venue(client, admin["id"])
    browse_timezone = ZoneInfo("America/Chicago")
    base_local = (datetime.now(browse_timezone) + timedelta(days=7)).replace(
        hour=18,
        minute=0,
        second=0,
        microsecond=0,
    )
    base_start = base_local.astimezone(UTC)

    open_game = create_game(
        client,
        admin["id"],
        venue,
        starts_at=base_start.isoformat(),
        ends_at=(base_start + timedelta(hours=1)).isoformat(),
        format_label="3v3",
        total_spots=6,
    )
    paused_game = create_game(
        client,
        admin["id"],
        venue,
        starts_at=(base_start + timedelta(minutes=20)).isoformat(),
        ends_at=(base_start + timedelta(hours=1, minutes=20)).isoformat(),
        join_enforcement_status="paused",
        format_label="3v3",
        total_spots=6,
    )
    waitlist_open_game = create_game(
        client,
        admin["id"],
        venue,
        starts_at=(base_start + timedelta(minutes=40)).isoformat(),
        ends_at=(base_start + timedelta(hours=1, minutes=40)).isoformat(),
        format_label="3v3",
        total_spots=6,
        waitlist_enabled=True,
    )
    full_game = create_game(
        client,
        admin["id"],
        venue,
        starts_at=(base_start + timedelta(hours=1)).isoformat(),
        ends_at=(base_start + timedelta(hours=2)).isoformat(),
        format_label="3v3",
        total_spots=6,
        waitlist_enabled=False,
    )

    create_game_participant(client, player["id"], open_game["id"])
    for _index in range(6):
        create_game_participant(
            client,
            create_user(client)["id"],
            waitlist_open_game["id"],
        )
        create_game_participant(client, create_user(client)["id"], full_game["id"])

    first_page = client.get(
        "/games/browse",
        params={
            "starts_on": local_date_string(base_start, "America/Chicago"),
            "limit": 2,
        },
    )

    assert first_page.status_code == 200, first_page.text
    first_body = first_page.json()
    assert first_body["has_more"] is True
    assert first_body["time_groups"] == [
        {"group_key": "18:00", "total_games": 2},
        {"group_key": "19:00", "total_games": 1},
    ]
    assert [game["time_group_key"] for game in first_body["games"]] == [
        "18:00",
        "18:00",
    ]

    second_page = client.get(
        "/games/browse",
        params={
            "starts_on": local_date_string(base_start, "America/Chicago"),
            "limit": 2,
            "cursor": first_body["next_cursor"],
        },
    )
    assert second_page.status_code == 200, second_page.text

    loaded_ids = {
        game["id"] for game in [*first_body["games"], *second_page.json()["games"]]
    }
    assert loaded_ids == {
        open_game["id"],
        waitlist_open_game["id"],
        full_game["id"],
    }
    assert paused_game["id"] not in loaded_ids
