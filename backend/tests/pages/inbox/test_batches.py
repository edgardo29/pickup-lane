"""Inbox batches: Load More order, overlap, and cursor binding."""

from datetime import timedelta

import pytest

from backend.tests.factories import make_notification, make_user


def item_ids(response):
    return [item["source_id"] for item in response.json()["items"]]


@pytest.mark.page("F25", 9)
def test_later_batches_continue_newest_first_without_duplicates_and_then_end(
    clock, db, client, inbox_user, inbox_headers
):
    notices = [
        make_notification(
            db, user=inbox_user, event_at=clock.now - timedelta(minutes=minutes)
        )
        for minutes in range(1, 6)
    ]

    first = client.get("/inbox/app-updates?limit=2", headers=inbox_headers)
    second = client.get(
        "/inbox/app-updates",
        params={"limit": 2, "cursor": first.json()["next_cursor"]},
        headers=inbox_headers,
    )
    third = client.get(
        "/inbox/app-updates",
        params={"limit": 2, "cursor": second.json()["next_cursor"]},
        headers=inbox_headers,
    )

    assert [first.status_code, second.status_code, third.status_code] == [200] * 3
    assert item_ids(first) + item_ids(second) + item_ids(third) == [
        str(notice.id) for notice in notices
    ]
    assert first.json()["has_more"] is True
    assert second.json()["has_more"] is True
    assert third.json()["has_more"] is False
    assert third.json()["next_cursor"] is None


@pytest.mark.page("F25", 9)
def test_items_added_after_the_first_batch_do_not_repeat_or_shift_later_batches(
    clock, db, client, inbox_user, inbox_headers
):
    notices = [
        make_notification(
            db, user=inbox_user, event_at=clock.now - timedelta(minutes=minutes)
        )
        for minutes in range(1, 5)
    ]
    first = client.get("/inbox/app-updates?limit=2", headers=inbox_headers)
    clock.advance(timedelta(minutes=1))
    make_notification(db, user=inbox_user, event_at=clock.now)

    second = client.get(
        "/inbox/app-updates",
        params={"limit": 2, "cursor": first.json()["next_cursor"]},
        headers=inbox_headers,
    )

    assert second.status_code == 200, second.text
    assert item_ids(first) == [str(notices[0].id), str(notices[1].id)]
    assert item_ids(second) == [str(notices[2].id), str(notices[3].id)]
    assert second.json()["has_more"] is False


@pytest.mark.page("F25", 11)
def test_a_cursor_from_another_filter_is_rejected(
    clock, db, client, inbox_user, inbox_headers
):
    for minutes in range(1, 4):
        make_notification(
            db, user=inbox_user, event_at=clock.now - timedelta(minutes=minutes)
        )
    cursor = client.get(
        "/inbox/app-updates?filter=all&limit=1", headers=inbox_headers
    ).json()["next_cursor"]

    response = client.get(
        "/inbox/app-updates",
        params={"filter": "new", "limit": 1, "cursor": cursor},
        headers=inbox_headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "cursor is invalid."


@pytest.mark.page("F25", 15)
def test_a_cursor_from_another_account_is_rejected(
    clock, db, client, firebase, inbox_user, inbox_headers
):
    for minutes in range(1, 4):
        make_notification(
            db, user=inbox_user, event_at=clock.now - timedelta(minutes=minutes)
        )
    cursor = client.get("/inbox/app-updates?limit=1", headers=inbox_headers).json()[
        "next_cursor"
    ]

    response = client.get(
        "/inbox/app-updates",
        params={"limit": 1, "cursor": cursor},
        headers=firebase.sign_in(make_user(db)),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "cursor is invalid."
