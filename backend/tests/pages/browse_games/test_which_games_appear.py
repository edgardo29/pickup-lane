"""Which games Browse lists: eligibility, cutoff, full games, window, and local dates."""

from datetime import UTC, date, datetime, timedelta

import pytest

from backend.tests.factories import make_game, make_participant

# FIXED_NOW in the root conftest is 2026-06-15 12:00 in America/Chicago.
TODAY = date(2026, 6, 15)


def game_ids(body) -> list[str]:
    return [card["id"] for card in body["games"]]


def chicago(hour: int, minute: int = 0, day: int = 15) -> datetime:
    """A June 2026 time in America/Chicago (UTC-5 during daylight saving)."""
    return datetime(2026, 6, day, hour, minute, tzinfo=UTC) + timedelta(hours=5)


@pytest.mark.page("F15", 1)
def test_signed_in_and_signed_out_visitors_get_the_same_games(clock, db, client):
    make_game(db, starts_at=chicago(18))
    make_game(db, starts_at=chicago(19), game_type="community")

    signed_out = client.get("/games/browse")
    signed_in = client.get(
        "/games/browse", headers={"Authorization": "Bearer signed-in-visitor-token"}
    )

    assert signed_out.status_code == 200, signed_out.text
    assert signed_in.status_code == 200, signed_in.text
    assert signed_in.json() == signed_out.json()


@pytest.mark.page("F15", 6)
def test_official_and_community_games_for_the_date_appear_together(clock, db, browse):
    official = make_game(db, starts_at=chicago(18))
    community = make_game(db, starts_at=chicago(19), game_type="community")

    body = browse()

    assert game_ids(body) == [str(official.id), str(community.id)]
    assert body["browse_date"] == TODAY.isoformat()


@pytest.mark.page("F15", 6)
@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"publish_status": "draft", "published_at": None}, id="draft"),
        pytest.param({"publish_status": "archived"}, id="archived"),
        pytest.param({"public_visibility_status": "hidden"}, id="hidden"),
        pytest.param({"join_enforcement_status": "paused"}, id="paused"),
        pytest.param(
            {
                "game_status": "cancelled",
                "cancelled_at": datetime(2026, 6, 15, tzinfo=UTC),
                "cancellation_source": "host",
            },
            id="cancelled",
        ),
        pytest.param(
            {
                "game_status": "completed",
                "completed_at": datetime(2026, 6, 15, tzinfo=UTC),
            },
            id="completed",
        ),
        pytest.param({"game_status": "expired"}, id="expired"),
        pytest.param({"game_status": "removed"}, id="removed"),
        pytest.param({"deleted_at": datetime(2026, 6, 15, tzinfo=UTC)}, id="deleted"),
        pytest.param({"starts_on_local": date(2026, 6, 16)}, id="wrong-date"),
    ],
)
def test_ineligible_game_is_not_listed_or_counted(clock, db, browse, overrides):
    listed = make_game(db, starts_at=chicago(18))
    make_game(db, starts_at=chicago(18, 30), **overrides)

    body = browse()

    assert game_ids(body) == [str(listed.id)]
    assert body["time_groups"] == [{"group_key": "18:00", "total_games": 1}]


@pytest.mark.page("F15", 7)
def test_game_stays_listed_until_just_before_the_cutoff(clock, db, browse):
    game = make_game(db, starts_at=clock.now - timedelta(minutes=4, seconds=59))

    assert game_ids(browse()) == [str(game.id)]


@pytest.mark.page("F15", 7)
def test_game_disappears_exactly_at_the_registration_cutoff(clock, db, browse):
    make_game(db, starts_at=clock.now - timedelta(minutes=5))

    body = browse()

    assert body["games"] == []
    assert body["time_groups"] == []


@pytest.mark.page("F15", 8)
@pytest.mark.parametrize(
    ("waitlist_enabled", "expected_status"),
    [(True, "waitlist_open"), (False, "full")],
)
def test_full_game_stays_listed_with_no_spots_remaining(
    clock, db, browse, waitlist_enabled, expected_status
):
    game = make_game(
        db, starts_at=chicago(18), total_spots=2, waitlist_enabled=waitlist_enabled
    )
    make_participant(db, game=game)
    make_participant(db, game=game)

    body = browse()

    assert game_ids(body) == [str(game.id)]
    assert body["games"][0]["availability"] == {
        "status": expected_status,
        "occupied_spots": 2,
        "total_spots": 2,
        "spots_remaining": 0,
    }


@pytest.mark.page("F15", 33)
def test_game_beyond_the_window_appears_once_its_date_enters_it(clock, db, browse):
    beyond_window = TODAY + timedelta(days=14)
    game = make_game(db, starts_at=chicago(18, day=beyond_window.day))

    before = browse(starts_on=beyond_window.isoformat())
    clock.advance(timedelta(days=1))
    after = browse(starts_on=beyond_window.isoformat())

    assert before["browse_date"] == (TODAY + timedelta(days=13)).isoformat()
    assert before["games"] == []
    assert after["browse_date"] == beyond_window.isoformat()
    assert game_ids(after) == [str(game.id)]


@pytest.mark.page("F15", 35)
def test_game_is_listed_under_its_own_local_start_date(clock, db, browse):
    # 00:30 on June 17 in New York is 23:30 on June 16 in Chicago.
    game = make_game(
        db,
        starts_at=datetime(2026, 6, 17, 4, 30, tzinfo=UTC),
        timezone="America/New_York",
    )

    on_local_date = browse(starts_on="2026-06-17")
    on_market_date = browse(starts_on="2026-06-16")

    assert game_ids(on_local_date) == [str(game.id)]
    assert on_market_date["games"] == []
