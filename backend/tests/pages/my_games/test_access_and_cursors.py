"""F19 who can open My Games, and how its Load More cursors are protected."""

import json
from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import date, timedelta

import pytest

from backend.tests.factories import (
    make_booking,
    make_game,
    make_participant,
    make_sub_post,
    make_sub_post_request,
    make_user,
)

LISTS = ["/my-games", "/my-games/need-a-sub"]


def player(db, **overrides):
    return make_user(db, date_of_birth=date(1990, 1, 1), **overrides)


def joined_games(db, joiner, first_start, count):
    """Official games the player booked, one hour apart."""
    games = []
    for index in range(count):
        game = make_game(db, starts_at=first_start + timedelta(hours=index))
        booking = make_booking(db, game=game, buyer=joiner)
        make_participant(db, game=game, booking=booking, user=joiner)
        games.append(game)
    return games


def next_cursor(client, headers, path="/my-games", view="upcoming"):
    response = client.get(path, params={"view": view, "limit": 1}, headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["has_more"] is True
    return response.json()["next_cursor"]


@pytest.mark.page("F19", 12)
@pytest.mark.parametrize("path", LISTS)
def test_signed_out_visitors_cannot_open_my_games(db, client, path):
    response = client.get(path, params={"view": "upcoming"})

    assert response.status_code == 401


@pytest.mark.page("F19", 12)
@pytest.mark.parametrize("path", LISTS)
@pytest.mark.parametrize(
    "account",
    [
        {"account_status": "pending_deletion"},
        {"account_status": "deleted", "deleted_at": "now"},
    ],
)
def test_a_deleted_or_deleting_account_cannot_open_my_games(
    clock, db, client, firebase, path, account
):
    if account.get("deleted_at") == "now":
        account = {**account, "deleted_at": clock.now}
    user = player(db, **account)

    response = client.get(
        path, params={"view": "upcoming"}, headers=firebase.sign_in(user)
    )

    # Sign-in treats a deleted or deleting account as no longer existing.
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found."


@pytest.mark.page("F19", 12)
def test_one_accounts_cursor_cannot_be_used_by_another(clock, db, client, firebase):
    first, second = player(db), player(db)
    joined_games(db, first, clock.now + timedelta(days=1), 2)
    joined_games(db, second, clock.now + timedelta(days=1), 2)
    cursor = next_cursor(client, firebase.sign_in(first))

    response = client.get(
        "/my-games",
        params={"view": "upcoming", "cursor": cursor},
        headers=firebase.sign_in(second),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "cursor does not match the current query."


@pytest.mark.page("F19", 9)
def test_a_cursor_from_another_view_is_rejected(clock, db, client, firebase):
    me = player(db)
    joined_games(db, me, clock.now + timedelta(days=1), 2)
    headers = firebase.sign_in(me)
    upcoming_cursor = next_cursor(client, headers)

    response = client.get(
        "/my-games",
        params={"view": "history", "cursor": upcoming_cursor},
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "cursor does not match the current query."


@pytest.mark.page("F19", 9)
def test_a_cursor_from_the_other_list_is_rejected(clock, db, client, firebase):
    me = player(db)
    joined_games(db, me, clock.now + timedelta(days=1), 2)
    headers = firebase.sign_in(me)
    games_cursor = next_cursor(client, headers)

    response = client.get(
        "/my-games/need-a-sub",
        params={"view": "upcoming", "cursor": games_cursor},
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "cursor does not match the current query."


@pytest.mark.page("F19", 9)
def test_an_altered_cursor_is_rejected(clock, db, client, firebase):
    me = player(db)
    joined_games(db, me, clock.now + timedelta(days=1), 2)
    headers = firebase.sign_in(me)
    body, signature = next_cursor(client, headers).split(".")
    # Move the cursor back to the start of the list but keep its old signature,
    # so only the signature check can tell it was changed.
    envelope = json.loads(urlsafe_b64decode(body + "=" * (-len(body) % 4)))
    envelope["payload"]["starts_at"] = "2000-01-01T00:00:00+00:00"
    altered_body = urlsafe_b64encode(json.dumps(envelope).encode()).decode().rstrip("=")

    response = client.get(
        "/my-games",
        params={"view": "upcoming", "cursor": f"{altered_body}.{signature}"},
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "cursor is invalid."


def suspended_player_with_activity(db, clock):
    """A player with a hosted game, a joined game, an owned post, and a post
    they are confirmed for, who is then suspended."""
    me = player(db, hosting_status="eligible")
    hosted = make_game(
        db, game_type="community", host=me, starts_at=clock.now + timedelta(days=1)
    )
    make_participant(db, game=hosted, user=me, participant_type="host")
    [joined] = joined_games(db, me, clock.now + timedelta(days=2), 1)
    owned = make_sub_post(db, owner=me, starts_at=clock.now + timedelta(days=1))
    confirmed = make_sub_post(
        db, owner=player(db), starts_at=clock.now + timedelta(days=2)
    )
    make_sub_post_request(db, post=confirmed, requester=me)
    me.account_status = "suspended"
    db.commit()
    return me, [hosted, joined], [owned, confirmed]


def listed_ids(client, headers, path, view, key):
    response = client.get(path, params={"view": view}, headers=headers)
    assert response.status_code == 200, response.text
    return [item[key]["id"] for item in response.json()["items"]]


@pytest.mark.page("F19", 13)
def test_a_suspended_player_still_finds_their_hosted_and_confirmed_games(
    clock, db, client, firebase
):
    me, games, _posts = suspended_player_with_activity(db, clock)

    listed = listed_ids(client, firebase.sign_in(me), "/my-games", "upcoming", "game")

    assert listed == [str(game.id) for game in games]


@pytest.mark.page("F19", 13)
def test_a_suspended_player_still_finds_their_owned_and_confirmed_posts(
    clock, db, client, firebase
):
    me, _games, posts = suspended_player_with_activity(db, clock)

    listed = listed_ids(
        client, firebase.sign_in(me), "/my-games/need-a-sub", "upcoming", "post"
    )

    assert listed == [str(post.id) for post in posts]


@pytest.mark.page("F19", 13)
def test_suspension_alone_does_not_move_anything_to_history(
    clock, db, client, firebase
):
    me, _games, _posts = suspended_player_with_activity(db, clock)
    headers = firebase.sign_in(me)

    game_history = listed_ids(client, headers, "/my-games", "history", "game")
    post_history = listed_ids(
        client, headers, "/my-games/need-a-sub", "history", "post"
    )

    assert (game_history, post_history) == ([], [])
