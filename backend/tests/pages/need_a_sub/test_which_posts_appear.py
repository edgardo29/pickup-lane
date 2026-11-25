"""F20 which posts a date lists, in what order, and how the list stays current."""

from datetime import UTC, date, datetime, timedelta

import pytest

from backend.tests.factories import make_sub_post_request, make_user

TODAY = date(2026, 6, 15)
TOMORROW = date(2026, 6, 16)
DAY_AFTER = date(2026, 6, 17)


def chicago(day: date, hour: int, minute: int = 0) -> datetime:
    """A wall-clock time in America/Chicago on ``day`` (UTC-5 in June)."""
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=UTC) + (
        timedelta(hours=5)
    )


def ids(body):
    return [card["id"] for card in body["posts"]]


# Every post status other than active, with the timestamp the app stamps with it.
ENDED_POST_STATUSES = {
    "completed": "filled_at",
    "cancelled": "canceled_at",
    "expired": None,
    "removed": "removed_at",
}


@pytest.mark.page("F20", 3)
def test_a_date_lists_the_posts_filed_under_that_chicago_date(
    clock, db, new_post, cards
):
    late_tomorrow = new_post(chicago(TOMORROW, 23, 30))
    early_day_after = new_post(chicago(DAY_AFTER, 0, 30))

    assert ids(cards(TOMORROW)) == [str(late_tomorrow.id)]
    assert ids(cards(DAY_AFTER)) == [str(early_day_after.id)]


@pytest.mark.page("F20", 5)
@pytest.mark.parametrize("post_status", list(ENDED_POST_STATUSES))
def test_a_post_that_is_not_active_does_not_appear(
    clock, db, new_post, cards, post_status
):
    shown = new_post(chicago(TOMORROW, 18))
    stamp = ENDED_POST_STATUSES[post_status]
    new_post(
        chicago(TOMORROW, 19),
        post_status=post_status,
        **({stamp: clock.now} if stamp else {}),
    )

    assert ids(cards(TOMORROW)) == [str(shown.id)]


@pytest.mark.page("F20", 5)
def test_a_hidden_post_does_not_appear(clock, db, new_post, cards):
    shown = new_post(chicago(TOMORROW, 18))
    new_post(chicago(TOMORROW, 19), public_visibility_status="hidden")

    assert ids(cards(TOMORROW)) == [str(shown.id)]


@pytest.mark.page("F20", 5)
def test_a_post_on_another_date_does_not_appear(clock, db, new_post, cards):
    shown = new_post(chicago(TOMORROW, 18))
    new_post(chicago(DAY_AFTER, 18))

    assert ids(cards(TOMORROW)) == [str(shown.id)]


@pytest.mark.page("F20", 5)
def test_a_post_that_has_started_does_not_appear(clock, db, new_post, cards):
    new_post(clock.now)
    upcoming = new_post(clock.now + timedelta(minutes=1))

    assert ids(cards(TODAY)) == [str(upcoming.id)]


@pytest.mark.page("F20", 5)
def test_posts_are_sorted_by_start_time(clock, db, new_post, cards):
    at_seven = new_post(
        chicago(TOMORROW, 19), created_at=clock.now - timedelta(hours=3)
    )
    at_six = new_post(chicago(TOMORROW, 18), created_at=clock.now - timedelta(hours=1))
    at_eight = new_post(
        chicago(TOMORROW, 20), created_at=clock.now - timedelta(hours=2)
    )

    assert ids(cards(TOMORROW)) == [str(at_six.id), str(at_seven.id), str(at_eight.id)]


@pytest.mark.page("F20", 5)
def test_posts_with_the_same_start_time_follow_creation_order(
    clock, db, new_post, cards
):
    at_six = chicago(TOMORROW, 18)
    created_last = new_post(at_six, created_at=clock.now - timedelta(minutes=1))
    created_first = new_post(at_six, created_at=clock.now - timedelta(hours=3))
    created_second = new_post(at_six, created_at=clock.now - timedelta(hours=2))

    assert ids(cards(TOMORROW)) == [
        str(created_first.id),
        str(created_second.id),
        str(created_last.id),
    ]


@pytest.mark.page("F20", 4)
def test_my_posts_shows_only_the_owners_eligible_posts_that_day(
    clock, db, firebase, new_post, cards
):
    viewer = make_user(db, date_of_birth=date(1990, 1, 1))
    mine = new_post(chicago(TOMORROW, 18), owner=viewer)
    new_post(
        chicago(TOMORROW, 19),
        owner=viewer,
        post_status="cancelled",
        canceled_at=clock.now,
    )
    new_post(chicago(DAY_AFTER, 18), owner=viewer)
    new_post(chicago(TOMORROW, 20))

    body = cards(TOMORROW, view="mine", headers=firebase.sign_in(viewer))

    assert ids(body) == [str(mine.id)]


@pytest.mark.page("F20", 9)
def test_a_date_with_no_eligible_posts_returns_an_empty_list(
    clock, db, new_post, cards
):
    new_post(chicago(TOMORROW, 19), post_status="cancelled", canceled_at=clock.now)

    body = cards(TOMORROW)

    assert body == {"posts": [], "next_cursor": None, "has_more": False, "limit": 40}


@pytest.mark.page("F20", 9)
def test_my_posts_is_empty_when_the_account_has_no_posts_that_day(
    clock, db, firebase, new_post, cards
):
    viewer = make_user(db, date_of_birth=date(1990, 1, 1))
    new_post(chicago(TOMORROW, 19))
    new_post(chicago(DAY_AFTER, 19), owner=viewer)

    body = cards(TOMORROW, view="mine", headers=firebase.sign_in(viewer))

    assert body == {"posts": [], "next_cursor": None, "has_more": False, "limit": 40}


@pytest.mark.page("F20", 13)
def test_a_new_first_batch_reflects_a_status_change(
    clock, db, client, firebase, new_post, cards
):
    owner = make_user(db, date_of_birth=date(1990, 1, 1))
    cancelled = new_post(chicago(TOMORROW, 18), owner=owner)
    kept = new_post(chicago(TOMORROW, 19))
    assert ids(cards(TOMORROW)) == [str(cancelled.id), str(kept.id)]

    response = client.patch(
        f"/need-a-sub/posts/{cancelled.id}/cancel",
        headers=firebase.sign_in(owner),
        json={"cancel_reason": None},
    )
    assert response.status_code == 200, response.text

    assert ids(cards(TOMORROW)) == [str(kept.id)]


@pytest.mark.page("F20", 13)
def test_a_new_first_batch_reflects_a_changed_confirmed_count(
    clock, db, new_post, cards
):
    filling = new_post(chicago(TOMORROW, 19))
    assert cards(TOMORROW)["posts"][0]["confirmed_count"] == 0

    make_sub_post_request(db, post=filling, requester=make_user(db))

    card = cards(TOMORROW)["posts"][0]
    assert (card["confirmed_count"], card["positions"][0]["confirmed_count"]) == (1, 1)
