"""Browse's market dates, rolling window, and daylight-saving boundaries."""

from datetime import UTC, date, datetime, timedelta

import pytest


@pytest.mark.page("F15", 2)
def test_missing_date_returns_todays_games(clock, browse_game, browse):
    today = browse_game(starts_at=clock.now + timedelta(hours=6))
    browse_game(starts_at=clock.now + timedelta(days=1, hours=6))
    body = browse()
    assert body["browse_date"] == today.starts_on_local.isoformat()
    assert [game["id"] for game in body["games"]] == [str(today.id)]


@pytest.mark.page("F15", 3)
@pytest.mark.parametrize("days", [1, 9, 13])
def test_valid_date_returns_that_days_games(clock, browse_game, browse, days):
    browse_game(starts_at=clock.now + timedelta(hours=6))
    selected = browse_game(starts_at=clock.now + timedelta(days=days, hours=6))
    body = browse(starts_on=selected.starts_on_local.isoformat())
    assert body["browse_date"] == selected.starts_on_local.isoformat()
    assert [game["id"] for game in body["games"]] == [str(selected.id)]


@pytest.mark.page("F15", 20)
def test_date_before_today_opens_today(clock, browse):
    assert browse(starts_on="2026-06-14")["browse_date"] == "2026-06-15"


@pytest.mark.page("F15", 20)
def test_date_after_the_window_opens_the_last_available_day(clock, browse):
    assert browse(starts_on="2026-07-05")["browse_date"] == "2026-06-28"


@pytest.mark.page("F15", 21)
def test_market_midnight_moves_the_window_and_normalizes_old_date(clock, browse):
    clock.move_to(datetime(2026, 6, 16, 4, 59, 59, tzinfo=UTC))
    before = browse(starts_on="2026-06-15")
    clock.advance(timedelta(seconds=1))
    after = browse(starts_on="2026-06-15")
    assert (
        before["minimum_browse_date"],
        before["maximum_browse_date"],
        before["browse_date"],
    ) == ("2026-06-15", "2026-06-28", "2026-06-15")
    assert (
        after["minimum_browse_date"],
        after["maximum_browse_date"],
        after["browse_date"],
    ) == ("2026-06-16", "2026-06-29", "2026-06-16")


@pytest.mark.page("F15", 22)
def test_window_uses_market_today_instead_of_utc_date(clock, browse):
    clock.move_to(datetime(2026, 6, 16, 4, 30, tzinfo=UTC))
    body = browse()
    assert body["browse_timezone"] == "America/Chicago"
    assert body["browse_today"] == "2026-06-15"
    assert body["minimum_browse_date"] == "2026-06-15"
    assert body["maximum_browse_date"] == "2026-06-28"


@pytest.mark.page("F15", 22)
@pytest.mark.parametrize(
    ("now", "first", "last"),
    [
        (datetime(2026, 3, 1, 18, tzinfo=UTC), "2026-03-01", "2026-03-14"),
        (datetime(2026, 10, 25, 17, tzinfo=UTC), "2026-10-25", "2026-11-07"),
    ],
)
def test_window_keeps_fourteen_calendar_dates_across_daylight_saving(
    clock, browse, now, first, last
):
    clock.move_to(now)
    body = browse()
    assert body["minimum_browse_date"] == first
    assert body["maximum_browse_date"] == last
    assert (date.fromisoformat(last) - date.fromisoformat(first)).days == 13


@pytest.mark.page("F15", 22)
@pytest.mark.parametrize(
    ("now", "start", "local_day"),
    [
        (
            datetime(2026, 3, 1, 18, tzinfo=UTC),
            datetime(2026, 3, 8, 23, 30, tzinfo=UTC),
            "2026-03-08",
        ),
        (
            datetime(2026, 10, 25, 17, tzinfo=UTC),
            datetime(2026, 11, 2, 0, 30, tzinfo=UTC),
            "2026-11-01",
        ),
    ],
)
def test_hour_groups_use_market_time_across_daylight_saving(
    clock, browse_game, browse, now, start, local_day
):
    clock.move_to(now)
    browse_game(starts_at=start)
    body = browse(starts_on=local_day)
    assert body["games"][0]["time_group_key"] == "18:00"
    assert body["time_groups"] == [{"group_key": "18:00", "total_games": 1}]
