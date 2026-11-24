"""Which games the public Browse read includes."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from backend.models import Booking, GameParticipant, Notification
from backend.tests.factories import make_participant, make_user


def ids(body):
    return [card["id"] for card in body["games"]]


@pytest.mark.page("F15", 1)
@pytest.mark.parametrize("relationship", ["confirmed", "waitlisted", "host"])
def test_signed_in_and_signed_out_visitors_get_the_same_games(
    clock, db, client, firebase, browse_game, relationship
):
    user = make_user(db, hosting_status="eligible")
    game = browse_game(
        starts_at=clock.now + timedelta(hours=6),
        game_type="community",
        host=user if relationship == "host" else None,
    )
    if relationship != "host":
        make_participant(db, game=game, user=user, participant_status=relationship)
    headers = firebase.sign_in(user)
    signed_out = client.get("/games/browse")
    signed_in = client.get("/games/browse", headers=headers)
    assert signed_out.status_code == 200, signed_out.text
    assert signed_in.status_code == 200, signed_in.text
    assert ids(signed_out.json()) == [str(game.id)]
    assert signed_in.json() == signed_out.json()


@pytest.mark.page("F15", 1)
def test_cards_omit_viewer_participation_and_hosting_state(
    clock, db, client, firebase, browse_game
):
    host = make_user(db, hosting_status="eligible")
    browse_game(
        starts_at=clock.now + timedelta(hours=6), game_type="community", host=host
    )
    response = client.get("/games/browse", headers=firebase.sign_in(host))
    assert response.status_code == 200, response.text
    card = response.json()["games"][0]
    assert {
        "is_host",
        "participant_id",
        "participant_status",
        "bucket",
        "is_joined",
        "is_waitlisted",
    }.isdisjoint(card)


@pytest.mark.page("F15", 6)
def test_official_and_community_games_for_the_date_appear_together(
    clock, browse, browse_game
):
    official = browse_game(starts_at=clock.now + timedelta(hours=6))
    community = browse_game(
        starts_at=clock.now + timedelta(hours=7), game_type="community"
    )
    assert ids(browse()) == [str(official.id), str(community.id)]


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
        pytest.param(
            {"starts_at": datetime(2026, 6, 16, 23, 30, tzinfo=UTC)}, id="wrong-date"
        ),
    ],
)
def test_ineligible_games_are_not_listed(clock, browse_game, browse, overrides):
    listed = browse_game(starts_at=clock.now + timedelta(hours=6))
    browse_game(
        **{"starts_at": clock.now + timedelta(hours=6, minutes=30), **overrides}
    )
    body = browse()
    assert ids(body) == [str(listed.id)]


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
        pytest.param(
            {"starts_at": datetime(2026, 6, 16, 23, 30, tzinfo=UTC)}, id="wrong-date"
        ),
    ],
)
def test_ineligible_games_are_not_counted_in_hour_totals(
    clock, browse_game, browse, overrides
):
    browse_game(starts_at=clock.now + timedelta(hours=6))
    browse_game(
        **{"starts_at": clock.now + timedelta(hours=6, minutes=30), **overrides}
    )
    body = browse()
    assert body["time_groups"] == [{"group_key": "18:00", "total_games": 1}]


@pytest.mark.page("F15", 7)
def test_game_stays_listed_until_just_before_the_cutoff(clock, browse_game, browse):
    game = browse_game(starts_at=clock.now - timedelta(minutes=4, seconds=59))
    assert ids(browse()) == [str(game.id)]


@pytest.mark.page("F15", 7)
def test_game_disappears_exactly_at_the_registration_cutoff(clock, browse_game, browse):
    browse_game(starts_at=clock.now - timedelta(minutes=5))
    assert browse()["games"] == []


@pytest.mark.page("F15", 7)
def test_game_is_absent_after_the_registration_cutoff(clock, browse_game, browse):
    browse_game(starts_at=clock.now - timedelta(minutes=5, seconds=1))
    assert browse()["games"] == []


@pytest.mark.page("F15", 8)
@pytest.mark.parametrize("waitlist_enabled", [True, False])
def test_full_game_stays_listed_with_no_spots_remaining(
    clock, db, browse_game, browse, waitlist_enabled
):
    game = browse_game(
        starts_at=clock.now + timedelta(hours=6),
        total_spots=6,
        waitlist_enabled=waitlist_enabled,
    )
    for _ in range(6):
        make_participant(db, game=game)
    body = browse()
    assert ids(body) == [str(game.id)]
    assert body["games"][0]["availability"]["spots_remaining"] == 0


@pytest.mark.page("F15", 14)
def test_browsing_creates_no_booking_roster_or_notification(
    clock, db, browse_game, browse
):
    game = browse_game(starts_at=clock.now + timedelta(hours=6))
    tables = [Booking.__table__, GameParticipant.__table__, Notification.__table__]
    before = {t.name: db.execute(select(t)).all() for t in tables}
    assert ids(browse()) == [str(game.id)]
    after = {t.name: db.execute(select(t)).all() for t in tables}
    assert after == before


@pytest.mark.page("F15", 17)
def test_day_without_eligible_games_returns_no_games(clock, browse_game, browse):
    browse_game(starts_at=clock.now + timedelta(days=1, hours=6))
    assert browse()["games"] == []


@pytest.mark.page("F15", 33)
def test_game_beyond_the_window_is_not_listed(clock, browse_game, browse):
    future = clock.now + timedelta(days=14, hours=6)
    browse_game(starts_at=future)
    assert browse(starts_on=future.date().isoformat())["games"] == []


@pytest.mark.page("F15", 33)
def test_future_game_appears_when_its_date_enters_the_window(
    clock, browse_game, browse
):
    future = clock.now + timedelta(days=14, hours=6)
    game = browse_game(starts_at=future)
    clock.advance(timedelta(days=1))
    assert ids(browse(starts_on=game.starts_on_local.isoformat())) == [str(game.id)]


@pytest.mark.page("F15", 35)
def test_game_is_listed_under_its_own_local_start_date(clock, browse_game, browse):
    game = browse_game(
        starts_at=datetime(2026, 6, 17, 4, 30, tzinfo=UTC), timezone="America/New_York"
    )
    assert ids(browse(starts_on="2026-06-17")) == [str(game.id)]
    assert browse(starts_on="2026-06-16")["games"] == []
