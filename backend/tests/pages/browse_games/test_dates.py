"""Browse dates: the 14-day market window, clamping, and daylight saving."""

from datetime import UTC, date, datetime, timedelta

import pytest

from backend.tests.factories import make_game

TODAY = date(2026, 6, 15)  # FIXED_NOW in the root conftest, in America/Chicago


@pytest.mark.page("F15", 20)
def test_date_before_today_opens_today(clock, browse):
    body = browse(starts_on=(TODAY - timedelta(days=1)).isoformat())

    assert body["browse_date"] == TODAY.isoformat()


@pytest.mark.page("F15", 20)
def test_date_after_the_window_opens_the_last_available_day(clock, browse):
    body = browse(starts_on=(TODAY + timedelta(days=20)).isoformat())

    assert body["browse_date"] == (TODAY + timedelta(days=13)).isoformat()


@pytest.mark.page("F15", 22)
def test_window_spans_fourteen_market_dates(clock, browse):
    body = browse()

    assert body["browse_timezone"] == "America/Chicago"
    assert body["browse_today"] == TODAY.isoformat()
    assert body["minimum_browse_date"] == TODAY.isoformat()
    assert body["maximum_browse_date"] == (TODAY + timedelta(days=13)).isoformat()


@pytest.mark.page("F15", 22)
def test_window_and_hour_groups_stay_in_market_time_across_daylight_saving_end(
    clock, db, browse
):
    # Noon on 2026-10-25 in Chicago. Daylight saving ends on 2026-11-01.
    clock.move_to(datetime(2026, 10, 25, 17, 0, tzinfo=UTC))
    # 00:30 UTC on Nov 2 is 18:30 on Nov 1 in Chicago, after the change to UTC-6.
    game = make_game(db, starts_at=datetime(2026, 11, 2, 0, 30, tzinfo=UTC))

    window = browse()
    day = browse(starts_on="2026-11-01")

    assert window["minimum_browse_date"] == "2026-10-25"
    assert window["maximum_browse_date"] == "2026-11-07"
    assert [card["id"] for card in day["games"]] == [str(game.id)]
    assert day["games"][0]["time_group_key"] == "18:00"
    assert day["time_groups"] == [{"group_key": "18:00", "total_games": 1}]
