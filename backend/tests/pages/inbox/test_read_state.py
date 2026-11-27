"""Inbox read state: individual reads and the global seen marker."""

from datetime import timedelta

import pytest
from sqlalchemy import func, select

from backend.models import PlatformNoticeGlobalSeenState, PlatformNoticeSelectedRead
from backend.tests.factories import (
    make_game,
    make_notification,
    make_platform_notice,
    make_user,
)


def selected_read_count(db):
    return db.scalar(select(func.count()).select_from(PlatformNoticeSelectedRead))


@pytest.mark.page("F25", 3)
def test_marking_a_notification_read_saves_it_and_lowers_the_unread_count(
    clock, db, client, inbox_user, inbox_headers
):
    game = make_game(db, starts_at=clock.now + timedelta(days=3))
    notice = make_notification(
        db,
        user=inbox_user,
        event_at=clock.now - timedelta(minutes=1),
        notification_type="booking_confirmed",
        game=game,
    )
    before = client.get("/inbox/counts", headers=inbox_headers).json()
    assert before["game_activity_unread_count"] == 1

    response = client.patch(f"/notifications/{notice.id}/read", headers=inbox_headers)

    assert response.status_code == 200, response.text
    db.refresh(notice)
    assert notice.is_read is True
    assert notice.read_at is not None
    counts = client.get("/inbox/counts", headers=inbox_headers).json()
    assert counts["game_activity_unread_count"] == 0


@pytest.mark.page("F25", 3)
def test_marking_a_selected_notice_read_saves_it_and_lowers_the_new_count(
    clock, db, client, inbox_user, inbox_headers
):
    notice = make_platform_notice(
        db, published_at=clock.now - timedelta(minutes=1), recipient=inbox_user
    )
    before = client.get("/inbox/counts", headers=inbox_headers).json()
    assert before["app_updates_new_count"] == 1

    response = client.put(
        f"/inbox/app-updates/platform-notices/{notice.id}/read",
        headers=inbox_headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["is_new"] is False
    read = db.get(
        PlatformNoticeSelectedRead, {"notice_id": notice.id, "user_id": inbox_user.id}
    )
    assert read is not None
    counts = client.get("/inbox/counts", headers=inbox_headers).json()
    assert counts["app_updates_new_count"] == 0


@pytest.mark.page("F25", 3)
@pytest.mark.page("F25", 7)
def test_another_user_cannot_mark_the_notification_read(
    clock, db, client, firebase, inbox_user
):
    notice = make_notification(
        db, user=inbox_user, event_at=clock.now - timedelta(minutes=1)
    )

    response = client.patch(
        f"/notifications/{notice.id}/read", headers=firebase.sign_in(make_user(db))
    )

    assert response.status_code == 404
    db.refresh(notice)
    assert notice.is_read is False
    assert notice.read_at is None


@pytest.mark.page("F25", 3)
def test_another_user_cannot_mark_a_selected_notice_read(
    clock, db, client, firebase, inbox_user, inbox_headers
):
    notice = make_platform_notice(
        db, published_at=clock.now - timedelta(minutes=1), recipient=inbox_user
    )

    response = client.put(
        f"/inbox/app-updates/platform-notices/{notice.id}/read",
        headers=firebase.sign_in(make_user(db)),
    )

    assert response.status_code == 404
    assert selected_read_count(db) == 0
    feed = client.get("/inbox/app-updates", headers=inbox_headers).json()
    assert feed["items"][0]["is_new"] is True


@pytest.mark.page("F25", 4)
def test_saving_the_global_seen_marker_clears_the_new_count_without_an_item_read(
    clock, db, client, inbox_user, inbox_headers
):
    make_platform_notice(
        db, published_at=clock.now - timedelta(minutes=1), global_sequence=1
    )
    token = client.get("/inbox/app-updates", headers=inbox_headers).json()[
        "global_seen_token"
    ]
    before = client.get("/inbox/counts", headers=inbox_headers).json()
    assert before["app_updates_new_count"] == 1

    response = client.put(
        "/inbox/app-updates/global-seen",
        json={"seen_token": token},
        headers=inbox_headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["app_updates_new_count"] == 0
    state = db.get(PlatformNoticeGlobalSeenState, inbox_user.id)
    assert state.last_seen_global_sequence == 1
    assert selected_read_count(db) == 0


@pytest.mark.page("F25", 4)
def test_a_global_seen_marker_issued_to_another_user_is_rejected(
    clock, db, client, firebase, inbox_user, inbox_headers
):
    make_platform_notice(
        db, published_at=clock.now - timedelta(minutes=1), global_sequence=1
    )
    other_token = client.get(
        "/inbox/app-updates", headers=firebase.sign_in(make_user(db))
    ).json()["global_seen_token"]

    response = client.put(
        "/inbox/app-updates/global-seen",
        json={"seen_token": other_token},
        headers=inbox_headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "seen_token is invalid."
    assert db.get(PlatformNoticeGlobalSeenState, inbox_user.id) is None


@pytest.mark.page("F25", 8)
def test_a_rejected_global_seen_marker_leaves_the_notice_new_until_a_later_save(
    clock, db, client, inbox_user, inbox_headers
):
    make_platform_notice(
        db, published_at=clock.now - timedelta(minutes=1), global_sequence=1
    )
    token = client.get("/inbox/app-updates", headers=inbox_headers).json()[
        "global_seen_token"
    ]

    rejected = client.put(
        "/inbox/app-updates/global-seen",
        json={"seen_token": f"{token}tampered"},
        headers=inbox_headers,
    )

    assert rejected.status_code == 400
    assert db.get(PlatformNoticeGlobalSeenState, inbox_user.id) is None
    retry_feed = client.get("/inbox/app-updates", headers=inbox_headers).json()
    assert retry_feed["items"][0]["is_new"] is True
    retried = client.put(
        "/inbox/app-updates/global-seen",
        json={"seen_token": retry_feed["global_seen_token"]},
        headers=inbox_headers,
    )
    assert retried.status_code == 200, retried.text
    assert (
        db.get(PlatformNoticeGlobalSeenState, inbox_user.id).last_seen_global_sequence
        == 1
    )
