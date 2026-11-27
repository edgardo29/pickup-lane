"""Inbox feeds: which items each feed returns, its filters, counts, and access."""

from datetime import datetime, timedelta

import pytest

from backend.models import PlatformNoticeGlobalSeenState
from backend.tests.factories import (
    make_game,
    make_notification,
    make_platform_notice,
    make_sub_post,
    make_user,
)


def item_ids(response):
    return [item["source_id"] for item in response.json()["items"]]


@pytest.mark.page("F25", 1)
def test_app_updates_returns_platform_notices_and_account_and_admin_notices(
    clock, db, client, inbox_user, inbox_headers
):
    game = make_game(db, starts_at=clock.now + timedelta(days=3))
    global_notice = make_platform_notice(
        db, published_at=clock.now - timedelta(minutes=1), global_sequence=1
    )
    selected_notice = make_platform_notice(
        db, published_at=clock.now - timedelta(minutes=2), recipient=inbox_user
    )
    account_notice = make_notification(
        db, user=inbox_user, event_at=clock.now - timedelta(minutes=3)
    )
    admin_notice = make_notification(
        db,
        user=inbox_user,
        event_at=clock.now - timedelta(minutes=4),
        notification_type="admin_enforcement_notice",
    )
    make_notification(
        db,
        user=inbox_user,
        event_at=clock.now - timedelta(minutes=5),
        notification_type="booking_confirmed",
        game=game,
    )

    response = client.get("/inbox/app-updates", headers=inbox_headers)

    assert response.status_code == 200, response.text
    assert item_ids(response) == [
        str(global_notice.id),
        str(selected_notice.id),
        str(account_notice.id),
        str(admin_notice.id),
    ]


@pytest.mark.page("F25", 1)
def test_game_activity_returns_game_and_need_a_sub_updates(
    clock, db, client, inbox_user, inbox_headers
):
    game = make_game(db, starts_at=clock.now + timedelta(days=3))
    post = make_sub_post(
        db, owner=make_user(db), starts_at=clock.now + timedelta(days=2)
    )
    game_notice = make_notification(
        db,
        user=inbox_user,
        event_at=clock.now - timedelta(minutes=1),
        notification_type="booking_confirmed",
        game=game,
    )
    sub_notice = make_notification(
        db,
        user=inbox_user,
        event_at=clock.now - timedelta(minutes=2),
        notification_type="sub_request_confirmed",
        sub_post=post,
    )
    make_notification(db, user=inbox_user, event_at=clock.now - timedelta(minutes=3))
    make_platform_notice(
        db, published_at=clock.now - timedelta(minutes=4), global_sequence=1
    )

    response = client.get("/inbox/game-activity", headers=inbox_headers)

    assert response.status_code == 200, response.text
    assert item_ids(response) == [str(game_notice.id), str(sub_notice.id)]


@pytest.mark.page("F25", 1)
def test_each_feed_returns_only_the_signed_in_users_items(
    clock, db, client, inbox_headers
):
    other = make_user(db)
    game = make_game(db, starts_at=clock.now + timedelta(days=3))
    make_notification(db, user=other, event_at=clock.now - timedelta(minutes=1))
    make_notification(
        db,
        user=other,
        event_at=clock.now - timedelta(minutes=2),
        notification_type="booking_confirmed",
        game=game,
    )
    make_platform_notice(
        db, published_at=clock.now - timedelta(minutes=3), recipient=other
    )

    app_response = client.get("/inbox/app-updates", headers=inbox_headers)
    game_response = client.get("/inbox/game-activity", headers=inbox_headers)

    assert app_response.status_code == 200, app_response.text
    assert game_response.status_code == 200, game_response.text
    assert app_response.json()["items"] == []
    assert game_response.json()["items"] == []


@pytest.mark.page("F25", 1)
def test_counts_return_the_app_updates_new_and_game_activity_unread_counts(
    clock, db, client, inbox_user, inbox_headers
):
    game = make_game(db, starts_at=clock.now + timedelta(days=3))
    make_platform_notice(
        db, published_at=clock.now - timedelta(minutes=1), global_sequence=1
    )
    make_platform_notice(
        db, published_at=clock.now - timedelta(minutes=2), recipient=inbox_user
    )
    make_notification(db, user=inbox_user, event_at=clock.now - timedelta(minutes=3))
    make_notification(
        db, user=inbox_user, event_at=clock.now - timedelta(minutes=4), is_read=True
    )
    for minutes, is_read in ((5, False), (6, False), (7, True)):
        make_notification(
            db,
            user=inbox_user,
            event_at=clock.now - timedelta(minutes=minutes),
            notification_type="booking_confirmed",
            game=game,
            is_read=is_read,
        )

    response = client.get("/inbox/counts", headers=inbox_headers)

    assert response.status_code == 200, response.text
    assert response.json() == {
        "app_updates_new_count": 3,
        "game_activity_unread_count": 2,
    }


@pytest.mark.page("F25", 1)
def test_an_item_returns_its_source_title_subject_and_event_time(
    clock, db, client, inbox_user, inbox_headers
):
    game = make_game(db, starts_at=clock.now + timedelta(days=3))
    event_at = clock.now - timedelta(minutes=5)
    make_notification(
        db,
        user=inbox_user,
        event_at=event_at,
        notification_type="booking_confirmed",
        game=game,
    )

    response = client.get("/inbox/game-activity", headers=inbox_headers)

    assert response.status_code == 200, response.text
    item = response.json()["items"][0]
    assert item["source_label"] == "Official Game"
    assert item["title"] == "Booking confirmed"
    assert item["subject_label"] == game.title
    assert item["row_subject"].startswith(f"{game.title} · ")
    assert datetime.fromisoformat(item["occurred_at"]) == event_at


@pytest.mark.page("F25", 2)
def test_app_updates_new_filter_returns_only_new_items(
    clock, db, client, inbox_user, inbox_headers
):
    db.add(
        PlatformNoticeGlobalSeenState(
            user_id=inbox_user.id,
            last_seen_global_sequence=1,
            created_at=clock.now,
            updated_at=clock.now,
        )
    )
    db.commit()
    seen_global = make_platform_notice(
        db, published_at=clock.now - timedelta(minutes=4), global_sequence=1
    )
    new_global = make_platform_notice(
        db, published_at=clock.now - timedelta(minutes=1), global_sequence=2
    )
    unread = make_notification(
        db, user=inbox_user, event_at=clock.now - timedelta(minutes=2)
    )
    read = make_notification(
        db, user=inbox_user, event_at=clock.now - timedelta(minutes=3), is_read=True
    )

    new_response = client.get("/inbox/app-updates?filter=new", headers=inbox_headers)
    all_response = client.get("/inbox/app-updates?filter=all", headers=inbox_headers)

    assert new_response.status_code == 200, new_response.text
    assert all_response.status_code == 200, all_response.text
    assert item_ids(new_response) == [str(new_global.id), str(unread.id)]
    assert item_ids(all_response) == [
        str(new_global.id),
        str(unread.id),
        str(read.id),
        str(seen_global.id),
    ]


@pytest.mark.page("F25", 2)
def test_game_activity_unread_filter_returns_only_unread_items(
    clock, db, client, inbox_user, inbox_headers
):
    game = make_game(db, starts_at=clock.now + timedelta(days=3))
    unread = make_notification(
        db,
        user=inbox_user,
        event_at=clock.now - timedelta(minutes=1),
        notification_type="booking_confirmed",
        game=game,
    )
    make_notification(
        db,
        user=inbox_user,
        event_at=clock.now - timedelta(minutes=2),
        notification_type="booking_confirmed",
        game=game,
        is_read=True,
    )

    response = client.get("/inbox/game-activity?filter=unread", headers=inbox_headers)

    assert response.status_code == 200, response.text
    assert item_ids(response) == [str(unread.id)]


@pytest.mark.page("F25", 2)
def test_game_activity_read_filter_returns_only_read_items(
    clock, db, client, inbox_user, inbox_headers
):
    game = make_game(db, starts_at=clock.now + timedelta(days=3))
    unread = make_notification(
        db,
        user=inbox_user,
        event_at=clock.now - timedelta(minutes=1),
        notification_type="booking_confirmed",
        game=game,
    )
    read = make_notification(
        db,
        user=inbox_user,
        event_at=clock.now - timedelta(minutes=2),
        notification_type="booking_confirmed",
        game=game,
        is_read=True,
    )

    read_response = client.get(
        "/inbox/game-activity?filter=read", headers=inbox_headers
    )
    all_response = client.get("/inbox/game-activity?filter=all", headers=inbox_headers)

    assert read_response.status_code == 200, read_response.text
    assert all_response.status_code == 200, all_response.text
    assert item_ids(read_response) == [str(read.id)]
    assert item_ids(all_response) == [str(unread.id), str(read.id)]


@pytest.mark.page("F25", 2)
@pytest.mark.parametrize(
    ("path", "unoffered_filter"),
    [("/inbox/app-updates", "unread"), ("/inbox/game-activity", "new")],
)
def test_each_feed_rejects_a_filter_it_does_not_offer(
    client, inbox_headers, path, unoffered_filter
):
    response = client.get(
        path, params={"filter": unoffered_filter}, headers=inbox_headers
    )

    assert response.status_code == 422


@pytest.mark.page("F25", 12)
@pytest.mark.parametrize(
    "path", ["/inbox/app-updates", "/inbox/game-activity", "/inbox/counts"]
)
def test_signed_out_requests_to_the_feeds_and_counts_are_rejected(client, path):
    response = client.get(path)

    assert response.status_code == 401


@pytest.mark.page("F25", 12)
def test_a_user_with_no_updates_gets_empty_feeds_and_zero_counts(client, inbox_headers):
    app_response = client.get("/inbox/app-updates", headers=inbox_headers)
    game_response = client.get("/inbox/game-activity", headers=inbox_headers)
    counts_response = client.get("/inbox/counts", headers=inbox_headers)

    assert app_response.status_code == 200, app_response.text
    assert game_response.status_code == 200, game_response.text
    assert counts_response.status_code == 200, counts_response.text
    assert app_response.json()["items"] == []
    assert app_response.json()["has_more"] is False
    assert game_response.json()["items"] == []
    assert game_response.json()["has_more"] is False
    assert counts_response.json() == {
        "app_updates_new_count": 0,
        "game_activity_unread_count": 0,
    }
