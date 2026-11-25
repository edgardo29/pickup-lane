"""F19 which Need a Sub posts a player sees in My Games, and in which view."""

from datetime import UTC, date, datetime, timedelta

import pytest

from backend.services.account_deletion_service import cancel_owned_need_a_sub_posts
from backend.tests.factories import make_sub_post, make_sub_post_request, make_user

REQUEST_STATUSES_THAT_DO_NOT_QUALIFY = [
    "pending",
    "declined",
    "sub_waitlist",
    "canceled_by_player",
    "canceled_by_owner",
    "no_show_reported",
    "expired",
    "closed_by_admin",
]


def player(db, **overrides):
    return make_user(db, date_of_birth=date(1990, 1, 1), **overrides)


def confirmed_post(db, requester, starts_at, **overrides):
    """Another owner's post the player is confirmed for. An owner has one
    active post per date, so each of these gets its own owner."""
    post = make_sub_post(db, owner=player(db), starts_at=starts_at, **overrides)
    make_sub_post_request(db, post=post, requester=requester)
    return post


def list_posts(client, firebase, user, view="upcoming", **params):
    response = client.get(
        "/my-games/need-a-sub",
        params={"view": view, **params},
        headers=firebase.sign_in(user),
    )
    assert response.status_code == 200, response.text
    return response.json()


def post_ids(client, firebase, user, view="upcoming"):
    return [
        item["post"]["id"] for item in list_posts(client, firebase, user, view)["items"]
    ]


def cancelled_by_owner(client, firebase, db, clock):
    """A post with a confirmed sub and a sub-waitlisted player, which its owner
    then cancels."""
    owner = player(db)
    post = make_sub_post(db, owner=owner, starts_at=clock.now + timedelta(days=2))
    confirmed = player(db)
    make_sub_post_request(db, post=post, requester=confirmed)
    waitlisted = player(db)
    make_sub_post_request(
        db, post=post, requester=waitlisted, request_status="sub_waitlist"
    )
    cancel = client.patch(
        f"/need-a-sub/posts/{post.id}/cancel", headers=firebase.sign_in(owner), json={}
    )
    assert cancel.status_code == 200, cancel.text
    return post, owner, confirmed, waitlisted


@pytest.mark.page("F19", 1)
def test_an_owned_post_is_listed_in_upcoming(clock, db, client, firebase):
    me = player(db)
    owned = make_sub_post(db, owner=me, starts_at=clock.now + timedelta(days=1))

    assert post_ids(client, firebase, me, "upcoming") == [str(owned.id)]


@pytest.mark.page("F19", 1)
def test_a_confirmed_post_is_listed_in_upcoming(clock, db, client, firebase):
    me = player(db)
    post = confirmed_post(db, me, clock.now + timedelta(days=1))

    assert post_ids(client, firebase, me, "upcoming") == [str(post.id)]


@pytest.mark.page("F19", 1)
def test_another_players_post_is_not_listed(clock, db, client, firebase):
    me = player(db)
    mine = make_sub_post(db, owner=me, starts_at=clock.now + timedelta(days=1))
    make_sub_post(db, owner=player(db), starts_at=clock.now + timedelta(days=2))
    confirmed_post(db, player(db), clock.now + timedelta(days=3))

    assert post_ids(client, firebase, me, "upcoming") == [str(mine.id)]


@pytest.mark.page("F19", 1)
def test_a_post_card_shows_the_owner_or_confirmed_status(clock, db, client, firebase):
    me = player(db)
    make_sub_post(db, owner=me, starts_at=clock.now + timedelta(days=1))
    confirmed_post(db, me, clock.now + timedelta(days=2))

    items = list_posts(client, firebase, me, "upcoming")["items"]

    assert [(item["is_owner"], item["status_label"]) for item in items] == [
        (True, "Your Post"),
        (False, "Confirmed"),
    ]


@pytest.mark.page("F19", 1)
def test_an_owned_posts_history_card_shows_the_owner_status(
    clock, db, client, firebase
):
    me = player(db)
    make_sub_post(db, owner=me, starts_at=clock.now - timedelta(days=1))
    confirmed_post(db, me, clock.now - timedelta(days=2))

    items = list_posts(client, firebase, me, "history")["items"]

    assert [(item["is_owner"], item["status_label"]) for item in items] == [
        (True, "Your Post"),
        (False, "Ended"),
    ]


@pytest.mark.page("F19", 4)
@pytest.mark.parametrize("request_status", REQUEST_STATUSES_THAT_DO_NOT_QUALIFY)
def test_a_post_the_player_is_not_confirmed_for_is_not_listed(
    clock, db, client, firebase, request_status
):
    me = player(db)
    post = make_sub_post(db, owner=player(db), starts_at=clock.now + timedelta(days=1))
    make_sub_post_request(db, post=post, requester=me, request_status=request_status)

    assert post_ids(client, firebase, me, "upcoming") == []


@pytest.mark.page("F19", 2)
def test_an_owners_post_card_can_open_its_post_while_the_detail_is_accessible(
    clock, db, client, firebase
):
    me = player(db)
    upcoming = make_sub_post(db, owner=me, starts_at=clock.now + timedelta(days=1))
    # Post detail stays open to its owner for 24 hours after the game ends.
    recent = make_sub_post(db, owner=me, starts_at=clock.now - timedelta(hours=3))

    upcoming_items = list_posts(client, firebase, me, "upcoming")["items"]
    history_items = list_posts(client, firebase, me, "history")["items"]

    assert [
        (item["post"]["id"], item["can_view_detail"])
        for item in upcoming_items + history_items
    ] == [(str(upcoming.id), True), (str(recent.id), True)]


@pytest.mark.page("F19", 2)
def test_an_owners_historical_post_whose_detail_is_closed_cannot_be_opened(
    clock, db, client, firebase
):
    me = player(db)
    older = make_sub_post(db, owner=me, starts_at=clock.now - timedelta(days=3))

    items = list_posts(client, firebase, me, "history")["items"]

    assert [(item["post"]["id"], item["can_view_detail"]) for item in items] == [
        (str(older.id), False)
    ]


@pytest.mark.page("F19", 2)
def test_a_confirmed_subs_post_card_can_open_its_post_while_the_detail_is_accessible(
    clock, db, client, firebase
):
    me = player(db)
    upcoming = confirmed_post(db, me, clock.now + timedelta(days=1))
    # Post detail stays open to a confirmed sub for 24 hours after the game ends.
    recent = confirmed_post(db, me, clock.now - timedelta(hours=3))

    upcoming_items = list_posts(client, firebase, me, "upcoming")["items"]
    history_items = list_posts(client, firebase, me, "history")["items"]

    assert [
        (item["post"]["id"], item["can_view_detail"])
        for item in upcoming_items + history_items
    ] == [(str(upcoming.id), True), (str(recent.id), True)]


@pytest.mark.page("F19", 2)
def test_a_confirmed_subs_historical_post_whose_detail_is_closed_cannot_be_opened(
    clock, db, client, firebase
):
    me = player(db)
    older = confirmed_post(db, me, clock.now - timedelta(days=3))

    items = list_posts(client, firebase, me, "history")["items"]

    assert [(item["post"]["id"], item["can_view_detail"]) for item in items] == [
        (str(older.id), False)
    ]


@pytest.mark.page("F19", 5)
def test_a_post_stays_upcoming_while_its_game_is_in_progress(
    clock, db, client, firebase
):
    me = player(db)
    post = make_sub_post(db, owner=me, starts_at=clock.now - timedelta(minutes=30))

    in_progress = post_ids(client, firebase, me, "upcoming")
    clock.move_to(post.ends_at - timedelta(seconds=1))
    just_before_end = post_ids(client, firebase, me, "upcoming")

    assert in_progress == [str(post.id)]
    assert just_before_end == [str(post.id)]


@pytest.mark.page("F19", 5)
def test_a_post_moves_to_history_at_its_scheduled_end(clock, db, client, firebase):
    me = player(db)
    post = make_sub_post(db, owner=me, starts_at=clock.now - timedelta(minutes=30))
    clock.move_to(post.ends_at)

    assert post_ids(client, firebase, me, "upcoming") == []
    assert post_ids(client, firebase, me, "history") == [str(post.id)]


@pytest.mark.page("F19", 6)
def test_a_cancelled_post_moves_to_history_for_its_owner(clock, db, client, firebase):
    post, owner, _confirmed, _waitlisted = cancelled_by_owner(
        client, firebase, db, clock
    )

    assert post_ids(client, firebase, owner, "upcoming") == []
    assert post_ids(client, firebase, owner, "history") == [str(post.id)]


@pytest.mark.page("F19", 6)
def test_a_cancelled_post_moves_to_history_for_a_confirmed_sub(
    clock, db, client, firebase
):
    post, _owner, confirmed, _waitlisted = cancelled_by_owner(
        client, firebase, db, clock
    )

    assert post_ids(client, firebase, confirmed, "upcoming") == []
    assert post_ids(client, firebase, confirmed, "history") == [str(post.id)]


@pytest.mark.page("F19", 6)
def test_a_sub_waitlisted_only_player_does_not_see_the_cancelled_post(
    clock, db, client, firebase
):
    _post, _owner, _confirmed, waitlisted = cancelled_by_owner(
        client, firebase, db, clock
    )

    assert post_ids(client, firebase, waitlisted, "upcoming") == []
    assert post_ids(client, firebase, waitlisted, "history") == []


@pytest.mark.page("F19", 6)
def test_a_post_cancelled_because_the_owner_deleted_their_account_stays_in_sub_history(
    clock, db, client, firebase
):
    owner = player(db)
    post = make_sub_post(db, owner=owner, starts_at=clock.now + timedelta(days=2))
    confirmed = player(db)
    make_sub_post_request(db, post=post, requester=confirmed)

    cancel_owned_need_a_sub_posts(
        db, user_id=owner.id, changed_by_user_id=None, now=datetime.now(UTC)
    )
    db.commit()

    db.refresh(post)
    assert post.post_status == "cancelled"
    assert post_ids(client, firebase, confirmed, "history") == [str(post.id)]


@pytest.mark.page("F19", 6)
def test_a_cancelled_post_card_shows_the_cancellation_status(
    clock, db, client, firebase
):
    _post, _owner, confirmed, _waitlisted = cancelled_by_owner(
        client, firebase, db, clock
    )

    (item,) = list_posts(client, firebase, confirmed, "history")["items"]

    assert item["status_label"] == "Cancelled"


@pytest.mark.page("F19", 7)
def test_a_hidden_post_stays_listed(clock, db, client, firebase):
    me = player(db)
    hidden = make_sub_post(
        db,
        owner=me,
        starts_at=clock.now + timedelta(days=1),
        public_visibility_status="hidden",
    )

    assert post_ids(client, firebase, me, "upcoming") == [str(hidden.id)]


@pytest.mark.page("F19", 7)
def test_a_removed_post_is_not_listed(clock, db, client, firebase):
    me = player(db)
    kept = make_sub_post(db, owner=me, starts_at=clock.now + timedelta(days=1))
    make_sub_post(
        db,
        owner=me,
        starts_at=clock.now + timedelta(days=2),
        post_status="removed",
        removed_at=clock.now,
    )

    assert post_ids(client, firebase, me, "upcoming") == [str(kept.id)]


# Each game lasts an hour, so a post starting an hour before the window start
# ended exactly 60 days ago.
def history_window_start(clock):
    return clock.now - timedelta(days=60)


@pytest.mark.page("F19", 8)
def test_a_post_that_ended_within_60_days_stays_in_history(clock, db, client, firebase):
    me = player(db)
    at_boundary = confirmed_post(
        db, me, history_window_start(clock) - timedelta(hours=1)
    )

    assert post_ids(client, firebase, me, "history") == [str(at_boundary.id)]


@pytest.mark.page("F19", 8)
def test_a_post_that_ended_more_than_60_days_ago_is_not_in_history(
    clock, db, client, firebase
):
    me = player(db)
    confirmed_post(db, me, history_window_start(clock) - timedelta(hours=1, seconds=1))

    assert post_ids(client, firebase, me, "history") == []


@pytest.mark.page("F19", 8)
def test_a_cancelled_posts_60_days_count_from_its_scheduled_end(
    clock, db, client, firebase
):
    me = player(db)
    window_start = history_window_start(clock)
    # Cancelled long before the window, but scheduled to end exactly 60 days
    # ago, so it stays.
    kept = make_sub_post(
        db,
        owner=me,
        starts_at=window_start - timedelta(hours=1),
        post_status="cancelled",
        canceled_at=window_start - timedelta(days=5),
    )
    # The one-active-post-per-date limit does not count cancelled posts.
    make_sub_post(
        db,
        owner=me,
        starts_at=window_start - timedelta(hours=1, seconds=1),
        post_status="cancelled",
        canceled_at=window_start - timedelta(days=5),
    )

    assert post_ids(client, firebase, me, "history") == [str(kept.id)]


@pytest.mark.page("F19", 3)
def test_need_a_sub_history_runs_newest_first(clock, db, client, firebase):
    me = player(db)
    older = confirmed_post(db, me, clock.now - timedelta(days=5))
    newest = confirmed_post(db, me, clock.now - timedelta(days=1))
    middle = confirmed_post(db, me, clock.now - timedelta(days=3))

    assert post_ids(client, firebase, me, "history") == [
        str(newest.id),
        str(middle.id),
        str(older.id),
    ]


@pytest.mark.page("F19", 3)
def test_load_more_continues_posts_without_duplicates(clock, db, client, firebase):
    me = player(db)
    posts = [
        confirmed_post(db, me, clock.now - timedelta(days=1, hours=index))
        for index in range(45)
    ]

    first = list_posts(client, firebase, me, "history")
    second = list_posts(client, firebase, me, "history", cursor=first["next_cursor"])

    assert (len(first["items"]), first["has_more"]) == (40, True)
    assert (len(second["items"]), second["has_more"]) == (5, False)
    listed = [item["post"]["id"] for item in first["items"] + second["items"]]
    assert listed == [str(post.id) for post in posts]


@pytest.mark.page("F19", 5)
@pytest.mark.parametrize("post_status", ["completed", "expired"])
def test_an_ended_completed_or_expired_post_is_in_history(
    clock, db, client, firebase, post_status
):
    me = player(db)
    starts_at = clock.now - timedelta(days=2)
    # A completed post records when it filled.
    filled = {"filled_at": starts_at - timedelta(days=1)}
    post = make_sub_post(
        db,
        owner=me,
        starts_at=starts_at,
        post_status=post_status,
        **(filled if post_status == "completed" else {}),
    )

    assert post_ids(client, firebase, me, "history") == [str(post.id)]


@pytest.mark.page("F19", 6)
def test_a_sub_who_left_before_the_cancellation_does_not_see_the_post(
    clock, db, client, firebase
):
    owner = player(db)
    post = make_sub_post(db, owner=owner, starts_at=clock.now + timedelta(days=2))
    left = player(db)
    request = make_sub_post_request(db, post=post, requester=left)
    withdraw = client.patch(
        f"/need-a-sub/requests/{request.id}/cancel", headers=firebase.sign_in(left)
    )
    assert withdraw.status_code == 200, withdraw.text

    cancel = client.patch(
        f"/need-a-sub/posts/{post.id}/cancel", headers=firebase.sign_in(owner), json={}
    )

    assert cancel.status_code == 200, cancel.text
    assert post_ids(client, firebase, left, "history") == []


@pytest.mark.page("F19", 3)
def test_need_a_sub_upcoming_runs_earliest_first(clock, db, client, firebase):
    me = player(db)
    later = confirmed_post(db, me, clock.now + timedelta(days=3))
    earliest = confirmed_post(db, me, clock.now + timedelta(days=1))
    middle = confirmed_post(db, me, clock.now + timedelta(days=2))

    assert post_ids(client, firebase, me, "upcoming") == [
        str(earliest.id),
        str(middle.id),
        str(later.id),
    ]
