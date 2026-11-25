"""F19 which games a player sees in My Games, and in which view."""

from datetime import UTC, date, datetime, timedelta

import pytest

from backend.services.account_deletion_service import (
    cancel_future_community_hosted_games,
)
from backend.tests.factories import make_booking, make_game, make_participant, make_user

PARTICIPANT_STATUSES_THAT_DO_NOT_QUALIFY = [
    "pending_payment",
    "waitlisted",
    "cancelled",
    "late_cancelled",
    "removed",
    "refunded",
]


def player(db, **overrides):
    return make_user(db, date_of_birth=date(1990, 1, 1), **overrides)


def hosted_game(db, host, starts_at, **overrides):
    """A community game whose host holds a confirmed roster place, as publishing creates it."""
    game = make_game(
        db, game_type="community", host=host, starts_at=starts_at, **overrides
    )
    make_participant(db, game=game, user=host, participant_type="host")
    return game


def joined_game(db, joiner, starts_at, participant_status="confirmed", **overrides):
    """An official game the player booked, with their roster place."""
    game = make_game(db, starts_at=starts_at, **overrides)
    booking = make_booking(db, game=game, buyer=joiner)
    make_participant(
        db,
        game=game,
        booking=booking,
        user=joiner,
        participant_status=participant_status,
    )
    return game


def list_games(client, firebase, user, view="upcoming", **params):
    response = client.get(
        "/my-games", params={"view": view, **params}, headers=firebase.sign_in(user)
    )
    assert response.status_code == 200, response.text
    return response.json()


def game_ids(client, firebase, user, view="upcoming"):
    return [
        item["game"]["id"] for item in list_games(client, firebase, user, view)["items"]
    ]


def cancelled_by_host(client, firebase, db, clock):
    """A community game with a confirmed player and a waitlisted player, which
    its host then cancels."""
    host = player(db, hosting_status="eligible")
    game = hosted_game(db, host, clock.now + timedelta(days=2))
    confirmed = player(db)
    make_participant(
        db,
        game=game,
        booking=make_booking(db, game=game, buyer=confirmed),
        user=confirmed,
    )
    waitlisted = player(db)
    make_participant(db, game=game, user=waitlisted, participant_status="waitlisted")
    cancel = client.post(
        f"/games/{game.id}/cancel", headers=firebase.sign_in(host), json={}
    )
    assert cancel.status_code == 200, cancel.text
    return game, host, confirmed, waitlisted


@pytest.mark.page("F19", 1)
def test_a_hosted_game_is_listed_in_upcoming(clock, db, client, firebase):
    me = player(db, hosting_status="eligible")
    hosted = hosted_game(db, me, clock.now + timedelta(days=1))

    assert game_ids(client, firebase, me, "upcoming") == [str(hosted.id)]


@pytest.mark.page("F19", 1)
def test_a_confirmed_game_is_listed_in_upcoming(clock, db, client, firebase):
    me = player(db)
    joined = joined_game(db, me, clock.now + timedelta(days=1))

    assert game_ids(client, firebase, me, "upcoming") == [str(joined.id)]


@pytest.mark.page("F19", 1)
def test_another_players_game_is_not_listed(clock, db, client, firebase):
    me = player(db)
    mine = joined_game(db, me, clock.now + timedelta(days=1))
    joined_game(db, player(db), clock.now + timedelta(days=2))
    hosted_game(
        db, player(db, hosting_status="eligible"), clock.now + timedelta(days=3)
    )

    assert game_ids(client, firebase, me, "upcoming") == [str(mine.id)]


@pytest.mark.page("F19", 1)
def test_a_game_card_shows_the_hosting_or_confirmed_status(clock, db, client, firebase):
    me = player(db, hosting_status="eligible")
    hosted_game(db, me, clock.now + timedelta(days=1))
    joined_game(db, me, clock.now + timedelta(days=2))

    items = list_games(client, firebase, me, "upcoming")["items"]

    assert [(item["is_host"], item["status_label"]) for item in items] == [
        (True, "Hosting"),
        (False, "Confirmed"),
    ]


@pytest.mark.page("F19", 1)
def test_a_hosted_games_history_card_shows_the_hosting_status(
    clock, db, client, firebase
):
    me = player(db, hosting_status="eligible")
    hosted_game(db, me, clock.now - timedelta(days=1))
    joined_game(db, me, clock.now - timedelta(days=2))

    items = list_games(client, firebase, me, "history")["items"]

    assert [(item["is_host"], item["status_label"]) for item in items] == [
        (True, "Hosted"),
        (False, "Completed"),
    ]


@pytest.mark.page("F19", 4)
@pytest.mark.parametrize("participant_status", PARTICIPANT_STATUSES_THAT_DO_NOT_QUALIFY)
def test_a_game_the_player_is_not_confirmed_for_is_not_listed(
    clock, db, client, firebase, participant_status
):
    me = player(db)
    joined_game(
        db,
        me,
        clock.now + timedelta(days=1),
        participant_status=participant_status,
    )

    assert game_ids(client, firebase, me, "upcoming") == []


@pytest.mark.page("F19", 4)
def test_a_game_the_player_only_brought_guests_to_is_not_listed(
    clock, db, client, firebase
):
    me = player(db)
    game = make_game(db, starts_at=clock.now + timedelta(days=1))
    booking = make_booking(db, game=game, buyer=me, participant_count=2)
    make_participant(
        db, game=game, booking=booking, user=me, participant_status="cancelled"
    )
    make_participant(db, game=game, booking=booking, user=me, participant_type="guest")

    assert game_ids(client, firebase, me, "upcoming") == []


@pytest.mark.page("F19", 5)
def test_a_game_stays_upcoming_while_in_progress(clock, db, client, firebase):
    me = player(db)
    game = joined_game(db, me, clock.now - timedelta(minutes=30))

    in_progress = game_ids(client, firebase, me, "upcoming")
    clock.move_to(game.ends_at - timedelta(seconds=1))
    just_before_end = game_ids(client, firebase, me, "upcoming")

    assert in_progress == [str(game.id)]
    assert just_before_end == [str(game.id)]


@pytest.mark.page("F19", 5)
def test_a_game_moves_to_history_at_its_scheduled_end(clock, db, client, firebase):
    me = player(db)
    game = joined_game(db, me, clock.now - timedelta(minutes=30))
    clock.move_to(game.ends_at)

    assert game_ids(client, firebase, me, "upcoming") == []
    assert game_ids(client, firebase, me, "history") == [str(game.id)]


@pytest.mark.page("F19", 6)
def test_a_cancelled_game_moves_to_history_for_its_host(clock, db, client, firebase):
    game, host, _confirmed, _waitlisted = cancelled_by_host(client, firebase, db, clock)

    assert game_ids(client, firebase, host, "upcoming") == []
    assert game_ids(client, firebase, host, "history") == [str(game.id)]


@pytest.mark.page("F19", 6)
def test_a_cancelled_game_moves_to_history_for_a_confirmed_player(
    clock, db, client, firebase
):
    game, _host, confirmed, _waitlisted = cancelled_by_host(client, firebase, db, clock)

    assert game_ids(client, firebase, confirmed, "upcoming") == []
    assert game_ids(client, firebase, confirmed, "history") == [str(game.id)]


@pytest.mark.page("F19", 6)
def test_a_waitlisted_only_player_does_not_see_the_cancelled_game(
    clock, db, client, firebase
):
    _game, _host, _confirmed, waitlisted = cancelled_by_host(
        client, firebase, db, clock
    )

    assert game_ids(client, firebase, waitlisted, "upcoming") == []
    assert game_ids(client, firebase, waitlisted, "history") == []


@pytest.mark.page("F19", 6)
def test_a_game_cancelled_because_the_host_deleted_their_account_stays_in_player_history(
    clock, db, client, firebase
):
    host = player(db, hosting_status="eligible")
    game = hosted_game(db, host, clock.now + timedelta(days=2))
    confirmed = player(db)
    make_participant(
        db,
        game=game,
        booking=make_booking(db, game=game, buyer=confirmed),
        user=confirmed,
    )

    cancel_future_community_hosted_games(db, user=host, now=datetime.now(UTC))
    db.commit()

    db.refresh(game)
    assert game.game_status == "cancelled"
    assert game_ids(client, firebase, confirmed, "history") == [str(game.id)]


@pytest.mark.page("F19", 6)
def test_a_game_staff_cancel_stays_in_the_confirmed_players_history(
    clock, db, client, firebase
):
    game = make_game(db, starts_at=clock.now + timedelta(days=2))
    confirmed = player(db)
    make_participant(
        db,
        game=game,
        booking=make_booking(db, game=game, buyer=confirmed),
        user=confirmed,
    )
    staff = player(db, role="admin")
    staff_headers = firebase.sign_in(staff)
    preview = client.post(
        f"/admin/official-games/{game.id}/cancel-preview", headers=staff_headers
    )
    assert preview.status_code == 200, preview.text

    cancel = client.post(
        f"/admin/official-games/{game.id}/cancel",
        headers=staff_headers,
        json={
            "preview_token": preview.json()["preview_token"],
            "reason": "Field closed.",
        },
    )

    assert cancel.status_code == 200, cancel.text
    assert game_ids(client, firebase, confirmed, "upcoming") == []
    assert game_ids(client, firebase, confirmed, "history") == [str(game.id)]


@pytest.mark.page("F19", 6)
def test_a_cancelled_game_card_shows_the_cancellation_status(
    clock, db, client, firebase
):
    _game, _host, confirmed, _waitlisted = cancelled_by_host(
        client, firebase, db, clock
    )

    (item,) = list_games(client, firebase, confirmed, "history")["items"]

    assert item["status_label"] == "Cancelled"


@pytest.mark.page("F19", 7)
def test_a_hidden_game_stays_listed(clock, db, client, firebase):
    me = player(db)
    hidden = joined_game(
        db, me, clock.now + timedelta(days=1), public_visibility_status="hidden"
    )

    assert game_ids(client, firebase, me, "upcoming") == [str(hidden.id)]


@pytest.mark.page("F19", 7)
def test_a_removed_game_is_not_listed(clock, db, client, firebase):
    me = player(db)
    kept = joined_game(db, me, clock.now + timedelta(days=1))
    joined_game(db, me, clock.now + timedelta(days=2), game_status="removed")

    assert game_ids(client, firebase, me, "upcoming") == [str(kept.id)]


@pytest.mark.page("F19", 7)
def test_a_deleted_game_is_not_listed(clock, db, client, firebase):
    me = player(db)
    kept = joined_game(db, me, clock.now + timedelta(days=1))
    joined_game(db, me, clock.now + timedelta(days=2), deleted_at=clock.now)

    assert game_ids(client, firebase, me, "upcoming") == [str(kept.id)]


# Each game lasts an hour, so a game starting an hour before the window start
# ended exactly 60 days ago.
def history_window_start(clock):
    return clock.now - timedelta(days=60)


@pytest.mark.page("F19", 8)
def test_a_game_that_ended_within_60_days_stays_in_history(clock, db, client, firebase):
    me = player(db)
    at_boundary = joined_game(db, me, history_window_start(clock) - timedelta(hours=1))

    assert game_ids(client, firebase, me, "history") == [str(at_boundary.id)]


@pytest.mark.page("F19", 8)
def test_a_game_that_ended_more_than_60_days_ago_is_not_in_history(
    clock, db, client, firebase
):
    me = player(db)
    joined_game(db, me, history_window_start(clock) - timedelta(hours=1, seconds=1))

    assert game_ids(client, firebase, me, "history") == []


@pytest.mark.page("F19", 8)
def test_a_cancelled_games_60_days_count_from_its_scheduled_end(
    clock, db, client, firebase
):
    me = player(db, hosting_status="eligible")
    window_start = history_window_start(clock)
    # Cancelled long before the window, but scheduled to end exactly 60 days
    # ago, so it stays.
    kept = hosted_game(
        db,
        me,
        window_start - timedelta(hours=1),
        game_status="cancelled",
        cancelled_at=window_start - timedelta(days=5),
    )
    # A host has one active community game per date, but cancelled games do
    # not count toward that limit.
    hosted_game(
        db,
        me,
        window_start - timedelta(hours=1, seconds=1),
        game_status="cancelled",
        cancelled_at=window_start - timedelta(days=5),
    )

    assert game_ids(client, firebase, me, "history") == [str(kept.id)]


@pytest.mark.page("F19", 3)
def test_upcoming_runs_earliest_first(clock, db, client, firebase):
    me = player(db)
    later = joined_game(db, me, clock.now + timedelta(days=3))
    earliest = joined_game(db, me, clock.now + timedelta(days=1))
    middle = joined_game(db, me, clock.now + timedelta(days=2))

    assert game_ids(client, firebase, me, "upcoming") == [
        str(earliest.id),
        str(middle.id),
        str(later.id),
    ]


@pytest.mark.page("F19", 3)
def test_history_runs_newest_first(clock, db, client, firebase):
    me = player(db)
    older = joined_game(db, me, clock.now - timedelta(days=5))
    newer = joined_game(db, me, clock.now - timedelta(days=2))

    assert game_ids(client, firebase, me, "history") == [str(newer.id), str(older.id)]


@pytest.mark.page("F19", 3)
def test_load_more_continues_games_without_duplicates(clock, db, client, firebase):
    me = player(db)
    games = [
        joined_game(db, me, clock.now + timedelta(days=1, hours=index))
        for index in range(45)
    ]

    first = list_games(client, firebase, me, "upcoming")
    second = list_games(client, firebase, me, "upcoming", cursor=first["next_cursor"])

    assert (len(first["items"]), first["has_more"]) == (40, True)
    assert (len(second["items"]), second["has_more"]) == (5, False)
    assert second["next_cursor"] is None
    listed = [item["game"]["id"] for item in first["items"] + second["items"]]
    assert listed == [str(game.id) for game in games]


@pytest.mark.page("F19", 4)
def test_a_game_staff_added_the_player_to_is_listed(clock, db, client, firebase):
    me = player(db)
    game = make_game(db, starts_at=clock.now + timedelta(days=1))
    make_participant(db, game=game, user=me, participant_type="admin_added")

    assert game_ids(client, firebase, me, "upcoming") == [str(game.id)]


@pytest.mark.page("F19", 5)
@pytest.mark.parametrize("game_status", ["completed", "expired"])
def test_an_ended_completed_or_expired_game_is_in_history(
    clock, db, client, firebase, game_status
):
    me = player(db)
    starts_at = clock.now - timedelta(days=2)
    # A completed game records when it was completed.
    finished = {"completed_at": starts_at + timedelta(hours=1)}
    game = joined_game(
        db,
        me,
        starts_at,
        game_status=game_status,
        **(finished if game_status == "completed" else {}),
    )

    assert game_ids(client, firebase, me, "history") == [str(game.id)]


@pytest.mark.page("F19", 6)
def test_a_player_who_left_before_the_cancellation_does_not_see_the_game(
    clock, db, client, firebase
):
    host = player(db, hosting_status="eligible")
    game = hosted_game(db, host, clock.now + timedelta(days=2))
    left = player(db)
    make_participant(
        db, game=game, booking=make_booking(db, game=game, buyer=left), user=left
    )
    leave = client.post(
        f"/games/{game.id}/leave", headers=firebase.sign_in(left), json={}
    )
    assert leave.status_code == 200, leave.text

    cancel = client.post(
        f"/games/{game.id}/cancel", headers=firebase.sign_in(host), json={}
    )

    assert cancel.status_code == 200, cancel.text
    assert game_ids(client, firebase, left, "history") == []
