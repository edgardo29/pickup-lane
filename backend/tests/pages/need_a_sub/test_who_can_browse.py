"""F20 who can browse Need a Sub cards, and who can open My Posts."""

from datetime import UTC, date, datetime, timedelta

import pytest

from backend.tests.factories import make_user

TOMORROW = date(2026, 6, 16)


def chicago(day: date, hour: int, minute: int = 0) -> datetime:
    """A wall-clock time in America/Chicago on ``day`` (UTC-5 in June)."""
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=UTC) + (
        timedelta(hours=5)
    )


def player(db, **overrides):
    return make_user(db, date_of_birth=date(1990, 1, 1), **overrides)


BROWSING_ACCOUNTS = {
    "verified": ({}, True),
    "unverified": ({}, False),
    "suspended": ({"account_status": "suspended"}, True),
}


@pytest.mark.page("F20", 1)
def test_signed_out_visitors_get_all_posts(clock, db, new_post, cards):
    post = new_post(chicago(TOMORROW, 19))

    body = cards(TOMORROW)

    assert [card["id"] for card in body["posts"]] == [str(post.id)]


@pytest.mark.page("F20", 1)
def test_signed_out_visitors_cannot_open_my_posts(clock, db, client, new_post):
    new_post(chicago(TOMORROW, 19))

    response = client.get(
        "/need-a-sub/posts/cards",
        params={"view": "mine", "starts_on": TOMORROW.isoformat()},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Sign in to view your Need a Sub posts."


@pytest.mark.page("F20", 2)
@pytest.mark.parametrize("account", list(BROWSING_ACCOUNTS))
def test_signed_in_accounts_get_all_posts_including_unverified_and_suspended(
    clock, db, firebase, new_post, cards, account
):
    overrides, email_verified = BROWSING_ACCOUNTS[account]
    viewer = player(db, **overrides)
    post = new_post(chicago(TOMORROW, 19))

    body = cards(
        TOMORROW, headers=firebase.sign_in(viewer, email_verified=email_verified)
    )

    assert [card["id"] for card in body["posts"]] == [str(post.id)]


@pytest.mark.page("F20", 2, 4)
@pytest.mark.parametrize("account", list(BROWSING_ACCOUNTS))
def test_signed_in_accounts_open_my_posts_including_unverified_and_suspended(
    clock, db, firebase, new_post, cards, account
):
    overrides, email_verified = BROWSING_ACCOUNTS[account]
    viewer = player(db, **overrides)
    mine = new_post(chicago(TOMORROW, 19), owner=viewer)
    new_post(chicago(TOMORROW, 20))

    body = cards(
        TOMORROW,
        view="mine",
        headers=firebase.sign_in(viewer, email_verified=email_verified),
    )

    assert [card["id"] for card in body["posts"]] == [str(mine.id)]


@pytest.mark.page("F20", 4)
@pytest.mark.parametrize("account_status", ["pending_deletion", "deleted"])
def test_a_deleted_or_deleting_account_cannot_open_my_posts(
    clock, db, client, firebase, account_status
):
    deleted_at = clock.now if account_status == "deleted" else None
    viewer = player(db, account_status=account_status, deleted_at=deleted_at)

    response = client.get(
        "/need-a-sub/posts/cards",
        params={"view": "mine", "starts_on": TOMORROW.isoformat()},
        headers=firebase.sign_in(viewer),
    )

    # Sign-in treats a deleted or deleting account as no longer existing.
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found."
