from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from backend.services.game_service import (
    BROWSE_DATE_WINDOW_DAYS,
    BROWSE_TIMEZONE,
    get_browse_date_context,
)
from backend.tests.support.api_helpers import create_game, create_venue
from backend.tests.support.factories import create_user
from backend.tests.support.time import local_date_string


def test_browse_game_cards_without_starts_on_uses_browse_today_and_default_limit(
    client: TestClient,
):
    response = client.get("/games/browse")

    assert response.status_code == 200, response.text
    body = response.json()
    minimum_date = datetime.fromisoformat(body["minimum_browse_date"]).date()
    maximum_date = datetime.fromisoformat(body["maximum_browse_date"]).date()

    assert body["browse_timezone"] == "America/Chicago"
    assert body["browse_today"] == body["minimum_browse_date"]
    assert body["browse_date"] == body["browse_today"]
    assert maximum_date == minimum_date + timedelta(days=13)
    assert body["time_groups"] == []
    assert body["games"] == []
    assert body["limit"] == 40


def test_browse_game_cards_clamps_dates_outside_window(client: TestClient):
    before_window = client.get(
        "/games/browse",
        params={"starts_on": "2000-01-01"},
    )
    assert before_window.status_code == 200, before_window.text
    before_body = before_window.json()
    assert before_body["browse_date"] == before_body["minimum_browse_date"]

    after_window = client.get(
        "/games/browse",
        params={"starts_on": "2999-01-01"},
    )
    assert after_window.status_code == 200, after_window.text
    after_body = after_window.json()
    assert after_body["browse_date"] == after_body["maximum_browse_date"]


def test_browse_date_window_uses_calendar_dates_across_dst_boundary():
    now_utc = datetime(2026, 3, 8, 6, 30, tzinfo=UTC)

    (
        browse_today,
        minimum_browse_date,
        maximum_browse_date,
        browse_date,
        browse_timezone,
    ) = get_browse_date_context(None, now=now_utc)

    assert browse_timezone == BROWSE_TIMEZONE
    assert browse_today == now_utc.astimezone(ZoneInfo(BROWSE_TIMEZONE)).date()
    assert browse_date == browse_today
    assert minimum_browse_date == browse_today
    assert maximum_browse_date == browse_today + timedelta(
        days=BROWSE_DATE_WINDOW_DAYS - 1
    )

    window_dates = [
        minimum_browse_date + timedelta(days=offset)
        for offset in range(BROWSE_DATE_WINDOW_DAYS)
    ]
    assert len(window_dates) == 14
    assert len(set(window_dates)) == 14
    assert window_dates[-1] == maximum_browse_date


def test_browse_api_ignores_browser_timezone_headers(client: TestClient):
    first_response = client.get("/games/browse")
    second_response = client.get(
        "/games/browse",
        headers={"Time-Zone": "America/Los_Angeles"},
    )

    assert first_response.status_code == 200, first_response.text
    assert second_response.status_code == 200, second_response.text
    first_body = first_response.json()
    second_body = second_response.json()
    assert second_body["browse_timezone"] == first_body["browse_timezone"]
    assert second_body["browse_today"] == first_body["browse_today"]
    assert second_body["minimum_browse_date"] == first_body["minimum_browse_date"]
    assert second_body["maximum_browse_date"] == first_body["maximum_browse_date"]


def test_browse_cards_use_browse_timezone_for_time_group_key(client: TestClient):
    admin = create_user(client)
    venue = create_venue(client, admin["id"])
    browse_timezone = ZoneInfo("America/Chicago")
    browse_local_start = (datetime.now(browse_timezone) + timedelta(days=7)).replace(
        hour=18,
        minute=30,
        second=0,
        microsecond=0,
    )
    starts_at = browse_local_start.astimezone(UTC)
    game = create_game(
        client,
        admin["id"],
        venue,
        starts_at=starts_at.isoformat(),
        ends_at=(starts_at + timedelta(hours=1)).isoformat(),
        timezone="America/Los_Angeles",
    )

    response = client.get(
        "/games/browse",
        params={"starts_on": local_date_string(starts_at, "America/Los_Angeles")},
    )

    assert response.status_code == 200, response.text
    [card] = response.json()["games"]
    assert card["id"] == game["id"]
    assert card["timezone"] == "America/Los_Angeles"
    assert card["time_group_key"] == "18:00"


def test_browse_games_near_midnight_use_local_browse_date(client: TestClient):
    admin = create_user(client)
    venue = create_venue(client, admin["id"])
    browse_timezone = ZoneInfo("America/Chicago")
    browse_date = (datetime.now(browse_timezone) + timedelta(days=7)).date()
    early_local = datetime.combine(
        browse_date,
        datetime.min.time(),
        tzinfo=browse_timezone,
    ).replace(hour=0, minute=30)
    late_local = datetime.combine(
        browse_date,
        datetime.min.time(),
        tzinfo=browse_timezone,
    ).replace(hour=23, minute=30)
    early_start = early_local.astimezone(UTC)
    late_start = late_local.astimezone(UTC)
    early_game = create_game(
        client,
        admin["id"],
        venue,
        title="Early Local Browse Game",
        starts_at=early_start.isoformat(),
        ends_at=(early_start + timedelta(hours=1)).isoformat(),
    )
    late_game = create_game(
        client,
        admin["id"],
        venue,
        title="Late Local Browse Game",
        starts_at=late_start.isoformat(),
        ends_at=(late_start + timedelta(hours=1)).isoformat(),
    )

    response = client.get(
        "/games/browse",
        params={"starts_on": browse_date.isoformat()},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    game_ids = {game["id"] for game in body["games"]}
    assert early_game["id"] in game_ids
    assert late_game["id"] in game_ids
    cards_by_id = {game["id"]: game for game in body["games"]}
    assert cards_by_id[early_game["id"]]["starts_on_local"] == browse_date.isoformat()
    assert cards_by_id[late_game["id"]]["starts_on_local"] == browse_date.isoformat()
