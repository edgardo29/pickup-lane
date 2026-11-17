"""Browse ordering, hour totals, and Load More pages."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from backend.tests.factories import make_game, make_user, make_venue


def chicago(hour: int, minute: int = 0) -> datetime:
    """A time on 2026-06-15 in America/Chicago (UTC-5 during daylight saving)."""
    return datetime(2026, 6, 15, hour, minute, tzinfo=UTC) + timedelta(hours=5)


def game_ids(body) -> list[str]:
    return [card["id"] for card in body["games"]]


def make_games(db, count: int, *, first_start: datetime) -> list:
    """Create ``count`` games one minute apart, sharing one venue and creator."""
    venue = make_venue(db)
    creator = make_user(db)
    return [
        make_game(
            db,
            starts_at=first_start + timedelta(minutes=index),
            venue=venue,
            created_by=creator,
        )
        for index in range(count)
    ]


@pytest.mark.page("F15", 15)
def test_games_run_earliest_first_and_ties_follow_creation_order(clock, db, browse):
    tie_start = chicago(17)
    # Give the earlier-created tie the larger id, so only creation order can
    # explain the expected order.
    created_first = make_game(
        db,
        starts_at=tie_start,
        id=uuid.UUID("ffffffff-ffff-4fff-bfff-ffffffffffff"),
        created_at=clock.now - timedelta(hours=2),
    )
    created_second = make_game(
        db,
        starts_at=tie_start,
        id=uuid.UUID("00000000-0000-4000-8000-000000000001"),
        created_at=clock.now - timedelta(hours=1),
    )
    latest = make_game(db, starts_at=chicago(20))
    earliest = make_game(db, starts_at=chicago(13), game_type="community")

    body = browse()

    assert game_ids(body) == [
        str(earliest.id),
        str(created_first.id),
        str(created_second.id),
        str(latest.id),
    ]
    assert [group["group_key"] for group in body["time_groups"]] == [
        "13:00",
        "17:00",
        "20:00",
    ]


@pytest.mark.page("F15", 16)
def test_hour_total_counts_every_eligible_game_not_just_the_loaded_batch(
    clock, db, browse
):
    make_games(db, 3, first_start=chicago(14))
    make_games(db, 1, first_start=chicago(16))

    body = browse(limit=2)

    assert len(body["games"]) == 2
    assert body["time_groups"] == [
        {"group_key": "14:00", "total_games": 3},
        {"group_key": "16:00", "total_games": 1},
    ]


@pytest.mark.page("F15", 18)
def test_load_more_returns_the_rest_in_order_without_duplicates(clock, db, browse):
    games = make_games(db, 41, first_start=chicago(13))

    first = browse()
    second = browse(cursor=first["next_cursor"])

    assert game_ids(first) == [str(game.id) for game in games[:40]]
    assert first["has_more"] is True
    assert first["next_cursor"]
    assert game_ids(second) == [str(games[40].id)]
    assert second["has_more"] is False
    assert second["next_cursor"] is None


@pytest.mark.page("F15", 23)
def test_exactly_forty_games_fit_in_one_batch_with_nothing_more(clock, db, browse):
    make_games(db, 40, first_start=chicago(13))

    body = browse()

    assert len(body["games"]) == 40
    assert body["has_more"] is False
    assert body["next_cursor"] is None


@pytest.mark.page("F15", 26)
@pytest.mark.parametrize(
    "change",
    [
        pytest.param({"public_visibility_status": "hidden"}, id="hidden"),
        pytest.param(
            {
                "game_status": "cancelled",
                "cancelled_at": datetime(2026, 6, 15, 16, tzinfo=UTC),
                "cancellation_source": "host",
            },
            id="cancelled",
        ),
        pytest.param(
            {"deleted_at": datetime(2026, 6, 15, 16, tzinfo=UTC)}, id="deleted"
        ),
    ],
)
def test_game_that_becomes_unlisted_is_skipped_by_load_more(clock, db, browse, change):
    games = make_games(db, 4, first_start=chicago(14))
    first = browse(limit=2)

    for field, value in change.items():
        setattr(games[2], field, value)
    db.commit()
    second = browse(limit=2, cursor=first["next_cursor"])

    assert game_ids(second) == [str(games[3].id)]
    assert second["time_groups"] == [{"group_key": "14:00", "total_games": 3}]


@pytest.mark.page("F15", 26)
def test_game_past_its_cutoff_is_skipped_by_load_more(clock, db, browse):
    venue = make_venue(db)
    creator = make_user(db)
    starts = [chicago(12, 30), chicago(12, 40), chicago(12, 50), chicago(14)]
    games = [
        make_game(db, starts_at=start, venue=venue, created_by=creator)
        for start in starts
    ]
    first = browse(limit=2)

    # 12:56 local: registration has closed for the 12:50 game, not the 14:00 one.
    clock.move_to(chicago(12, 56))
    second = browse(limit=2, cursor=first["next_cursor"])

    assert game_ids(first) == [str(games[0].id), str(games[1].id)]
    assert game_ids(second) == [str(games[3].id)]
    assert second["time_groups"] == [{"group_key": "14:00", "total_games": 1}]
