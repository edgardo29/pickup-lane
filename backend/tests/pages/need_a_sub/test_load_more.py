"""F20 batches of 40 with Load More, and how Load More positions are protected."""

import json
from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import UTC, date, datetime, timedelta

import pytest

from backend.tests.factories import make_user

TOMORROW = date(2026, 6, 16)
DAY_AFTER = date(2026, 6, 17)


def chicago(day: date, hour: int, minute: int = 0) -> datetime:
    """A wall-clock time in America/Chicago on ``day`` (UTC-5 in June)."""
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=UTC) + (
        timedelta(hours=5)
    )


def posts_five_minutes_apart(new_post, day, count):
    first = chicago(day, 8)
    return [new_post(first + timedelta(minutes=5 * index)) for index in range(count)]


def ids(body):
    return [card["id"] for card in body["posts"]]


@pytest.mark.page("F20", 8)
def test_more_than_40_posts_come_in_ordered_batches_that_end(
    clock, db, new_post, cards
):
    posts = posts_five_minutes_apart(new_post, TOMORROW, 41)

    first = cards(TOMORROW)
    second = cards(TOMORROW, cursor=first["next_cursor"])

    assert ids(first) == [str(post.id) for post in posts[:40]]
    assert (first["has_more"], first["limit"]) == (True, 40)
    assert ids(second) == [str(posts[40].id)]
    assert (second["has_more"], second["next_cursor"]) == (False, None)


@pytest.mark.page("F20", 8)
def test_exactly_40_posts_fit_in_one_batch(clock, db, new_post, cards):
    posts_five_minutes_apart(new_post, TOMORROW, 40)

    body = cards(TOMORROW)

    assert len(body["posts"]) == 40
    assert (body["has_more"], body["next_cursor"]) == (False, None)


@pytest.mark.page("F20", 8)
def test_a_changed_cursor_is_refused(clock, db, client, new_post, cards):
    posts_five_minutes_apart(new_post, TOMORROW, 41)
    body, signature = cards(TOMORROW)["next_cursor"].split(".")
    # Move the position back to the start of the day but keep its old
    # signature, so only the signature check can tell it was changed.
    envelope = json.loads(urlsafe_b64decode(body + "=" * (-len(body) % 4)))
    envelope["payload"]["starts_at"] = "2000-01-01T00:00:00+00:00"
    changed_body = urlsafe_b64encode(json.dumps(envelope).encode()).decode().rstrip("=")
    changed = f"{changed_body}.{signature}"

    response = client.get(
        "/need-a-sub/posts/cards",
        params={"starts_on": TOMORROW.isoformat(), "cursor": changed},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "cursor is invalid."


@pytest.mark.page("F20", 12)
def test_a_cursor_does_not_work_for_another_date(clock, db, client, new_post, cards):
    posts_five_minutes_apart(new_post, TOMORROW, 41)
    cursor = cards(TOMORROW)["next_cursor"]

    response = client.get(
        "/need-a-sub/posts/cards",
        params={"starts_on": DAY_AFTER.isoformat(), "cursor": cursor},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "cursor does not match the current query."


@pytest.mark.page("F20", 12)
def test_an_all_posts_cursor_does_not_work_for_my_posts(
    clock, db, client, firebase, new_post, cards
):
    posts_five_minutes_apart(new_post, TOMORROW, 41)
    cursor = cards(TOMORROW)["next_cursor"]
    viewer = make_user(db, date_of_birth=date(1990, 1, 1))

    response = client.get(
        "/need-a-sub/posts/cards",
        params={"view": "mine", "starts_on": TOMORROW.isoformat(), "cursor": cursor},
        headers=firebase.sign_in(viewer),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "cursor does not match the current query."
