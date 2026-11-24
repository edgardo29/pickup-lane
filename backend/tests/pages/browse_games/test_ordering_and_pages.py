"""Browse order, complete hour totals, and cursor pages."""

import uuid
from datetime import timedelta

import pytest

from backend.tests.factories import make_game, make_user, make_venue


def ids(body):
    return [game["id"] for game in body["games"]]


def make_games(db, count, *, first_start):
    venue = make_venue(db)
    creator = make_user(db)
    return [
        make_game(
            db,
            starts_at=first_start + timedelta(minutes=i),
            venue=venue,
            created_by=creator,
        )
        for i in range(count)
    ]


@pytest.mark.page("F15", 15)
def test_cards_run_earliest_first(clock, browse_game, browse):
    latest = browse_game(starts_at=clock.now + timedelta(hours=8))
    earliest = browse_game(
        starts_at=clock.now + timedelta(hours=1), game_type="community"
    )
    middle = browse_game(starts_at=clock.now + timedelta(hours=5))
    assert ids(browse()) == [str(earliest.id), str(middle.id), str(latest.id)]


@pytest.mark.page("F15", 15)
def test_equal_start_times_follow_creation_order(clock, browse_game, browse):
    first = browse_game(
        starts_at=clock.now + timedelta(hours=5),
        id=uuid.UUID("ffffffff-ffff-4fff-bfff-ffffffffffff"),
        created_at=clock.now - timedelta(hours=2),
    )
    second = browse_game(
        starts_at=clock.now + timedelta(hours=5),
        id=uuid.UUID("00000000-0000-4000-8000-000000000001"),
        created_at=clock.now - timedelta(hours=1),
    )
    assert ids(browse()) == [str(first.id), str(second.id)]


@pytest.mark.page("F15", 15)
def test_hour_groups_run_earliest_first(clock, browse_game, browse):
    for hours in [8, 1, 5]:
        browse_game(starts_at=clock.now + timedelta(hours=hours))
    assert [group["group_key"] for group in browse()["time_groups"]] == [
        "13:00",
        "17:00",
        "20:00",
    ]


@pytest.mark.page("F15", 16)
def test_hour_total_counts_every_eligible_game_not_just_the_loaded_batch(
    clock, db, browse
):
    make_games(db, 3, first_start=clock.now + timedelta(hours=2))
    make_games(db, 1, first_start=clock.now + timedelta(hours=4))
    body = browse(limit=2)
    assert body["time_groups"] == [
        {"group_key": "14:00", "total_games": 3},
        {"group_key": "16:00", "total_games": 1},
    ]


@pytest.mark.page("F15", 18)
def test_first_batch_contains_the_first_forty_games(clock, db, browse):
    games = make_games(db, 41, first_start=clock.now + timedelta(hours=1))
    first = browse()
    assert ids(first) == [str(game.id) for game in games[:40]]
    assert first["has_more"] is True


@pytest.mark.page("F15", 18)
def test_load_more_returns_later_games_in_order_without_duplicates(clock, db, browse):
    games = make_games(db, 42, first_start=clock.now + timedelta(hours=1))
    first = browse()
    second = browse(cursor=first["next_cursor"])
    assert ids(second) == [str(game.id) for game in games[40:]]
    assert set(ids(first)).isdisjoint(ids(second))


@pytest.mark.page("F15", 18)
def test_last_batch_has_no_more_games_to_load(clock, db, browse):
    make_games(db, 41, first_start=clock.now + timedelta(hours=1))
    first = browse()
    last = browse(cursor=first["next_cursor"])
    assert len(last["games"]) == 1
    assert last["has_more"] is False
    assert last["next_cursor"] is None


@pytest.mark.page("F15", 23)
def test_exactly_forty_games_fit_in_one_batch_with_nothing_more(clock, db, browse):
    games = make_games(db, 40, first_start=clock.now + timedelta(hours=1))
    body = browse()
    assert ids(body) == [str(game.id) for game in games]
    assert body["has_more"] is False
    assert body["next_cursor"] is None


@pytest.fixture
def changed_later_page(clock, db):
    def prepare():
        games = [
            make_game(db, starts_at=clock.now + timedelta(minutes=m))
            for m in [30, 40, 50, 120]
        ]
        return games

    return prepare


@pytest.mark.page("F15", 26)
@pytest.mark.parametrize("change", ["hidden", "cancelled", "deleted", "cutoff"])
def test_load_more_excludes_a_game_that_became_ineligible(
    clock, db, browse, changed_later_page, change
):
    games = changed_later_page()
    first = browse(limit=2)
    if change == "hidden":
        games[2].public_visibility_status = "hidden"
    elif change == "cancelled":
        games[2].game_status = "cancelled"
        games[2].cancelled_at = clock.now
        games[2].cancellation_source = "host"
    elif change == "deleted":
        games[2].deleted_at = clock.now
    else:
        clock.advance(timedelta(minutes=56))
    db.commit()
    second = browse(limit=2, cursor=first["next_cursor"])
    assert ids(second) == [str(games[3].id)]


@pytest.mark.page("F15", 26)
@pytest.mark.parametrize("change", ["hidden", "cancelled", "deleted", "cutoff"])
def test_load_more_updates_totals_after_a_game_became_ineligible(
    clock, db, browse, changed_later_page, change
):
    games = changed_later_page()
    first = browse(limit=2)
    if change == "hidden":
        games[2].public_visibility_status = "hidden"
    elif change == "cancelled":
        games[2].game_status = "cancelled"
        games[2].cancelled_at = clock.now
        games[2].cancellation_source = "host"
    elif change == "deleted":
        games[2].deleted_at = clock.now
    else:
        clock.advance(timedelta(minutes=56))
    db.commit()
    second = browse(limit=2, cursor=first["next_cursor"])
    expected = [{"group_key": "14:00", "total_games": 1}]
    if change != "cutoff":
        expected.insert(0, {"group_key": "12:00", "total_games": 2})
    assert second["time_groups"] == expected
