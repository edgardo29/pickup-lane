"""Inbox modal actions: available, absent, and disabled destinations."""

from datetime import timedelta

import pytest

from backend.services.sub_post_chat_service import get_or_create_active_sub_post_chat
from backend.tests.factories import (
    make_booking,
    make_game,
    make_notification,
    make_participant,
    make_sub_post,
    make_sub_post_request,
    make_user,
)


def first_action(client, headers, path):
    response = client.get(path, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()["items"][0]


def view_game_action(game):
    return {
        "key": "view_game",
        "label": "View game",
        "path": f"/games/{game.id}",
        "disabled": False,
        "disabled_reason": None,
        "state": None,
    }


def still_available(clock):
    """Each game state that keeps its link, as the app stores it."""
    return {
        "active": {"starts_at": clock.now + timedelta(days=3)},
        "completed": {
            "starts_at": clock.now - timedelta(hours=3),
            "game_status": "completed",
            "completed_at": clock.now - timedelta(hours=1),
        },
    }


def no_longer_available(clock):
    """Each way a game stops being available, as the app stores it."""
    return {
        "cancelled": {
            "game_status": "cancelled",
            "cancelled_at": clock.now,
            "cancellation_source": "admin",
        },
        "expired": {"game_status": "expired"},
        "removed": {"game_status": "removed"},
        "deleted": {"deleted_at": clock.now},
        "draft": {"publish_status": "draft", "published_at": None},
        "archived": {"publish_status": "archived"},
    }


@pytest.mark.page("F25", 5)
@pytest.mark.parametrize("game_state", ["active", "completed"])
def test_a_notification_for_an_available_game_returns_an_action_to_that_game(
    clock, db, client, inbox_user, inbox_headers, game_state
):
    game = make_game(db, **still_available(clock)[game_state])
    make_notification(
        db,
        user=inbox_user,
        event_at=clock.now - timedelta(minutes=1),
        notification_type="booking_confirmed",
        game=game,
    )

    item = first_action(client, inbox_headers, "/inbox/game-activity")

    assert item["action"] == view_game_action(game)


@pytest.mark.page("F25", 6)
@pytest.mark.parametrize(
    "gone", ["cancelled", "expired", "removed", "deleted", "draft", "archived"]
)
def test_a_notification_for_a_game_that_is_gone_keeps_its_text_and_has_no_action(
    clock, db, client, inbox_user, inbox_headers, gone
):
    game = make_game(
        db,
        starts_at=clock.now + timedelta(days=3),
        **no_longer_available(clock)[gone],
    )
    notice = make_notification(
        db,
        user=inbox_user,
        event_at=clock.now - timedelta(minutes=1),
        notification_type="booking_confirmed",
        game=game,
    )

    item = first_action(client, inbox_headers, "/inbox/game-activity")

    assert item["action"] is None
    assert item["title"] == notice.title
    assert item["message"] == notice.body


@pytest.mark.page("F25", 5)
def test_a_hidden_game_the_user_can_still_open_keeps_its_action(
    clock, db, client, inbox_user, inbox_headers
):
    game = make_game(
        db,
        starts_at=clock.now + timedelta(days=3),
        public_visibility_status="hidden",
    )
    booking = make_booking(db, game=game, buyer=inbox_user)
    make_participant(db, game=game, booking=booking, user=inbox_user)
    make_notification(
        db,
        user=inbox_user,
        event_at=clock.now - timedelta(minutes=1),
        notification_type="booking_confirmed",
        game=game,
    )

    item = first_action(client, inbox_headers, "/inbox/game-activity")

    assert item["action"] == view_game_action(game)


@pytest.mark.page("F25", 6)
def test_a_hidden_game_the_user_can_no_longer_open_has_a_disabled_action(
    clock, db, client, inbox_user, inbox_headers
):
    game = make_game(
        db,
        starts_at=clock.now + timedelta(days=3),
        public_visibility_status="hidden",
    )
    make_notification(
        db,
        user=inbox_user,
        event_at=clock.now - timedelta(minutes=1),
        notification_type="booking_confirmed",
        game=game,
    )

    item = first_action(client, inbox_headers, "/inbox/game-activity")

    assert item["action"] == {
        "key": "view_game",
        "label": "View game",
        "path": None,
        "disabled": True,
        "disabled_reason": "You no longer have access to this game.",
        "state": None,
    }


@pytest.mark.page("F25", 5)
def test_a_notification_for_an_active_upcoming_post_returns_an_action_to_that_post(
    clock, db, client, inbox_user, inbox_headers
):
    post = make_sub_post(
        db, owner=make_user(db), starts_at=clock.now + timedelta(days=2)
    )
    make_notification(
        db,
        user=inbox_user,
        event_at=clock.now - timedelta(minutes=1),
        notification_type="sub_request_confirmed",
        sub_post=post,
    )

    item = first_action(client, inbox_headers, "/inbox/game-activity")

    assert item["action"] == {
        "key": "view_sub_post",
        "label": "View post",
        "path": f"/need-a-sub/posts/{post.id}",
        "disabled": False,
        "disabled_reason": None,
        "state": None,
    }


def posts_no_longer_open(clock):
    """Each way a Need a Sub post stops being open, as the app stores it."""
    upcoming = clock.now + timedelta(days=2)
    return {
        "completed": {
            "starts_at": upcoming,
            "post_status": "completed",
            "filled_at": clock.now,
        },
        "cancelled": {
            "starts_at": upcoming,
            "post_status": "cancelled",
            "canceled_at": clock.now,
        },
        "expired": {"starts_at": upcoming, "post_status": "expired"},
        "removed": {
            "starts_at": upcoming,
            "post_status": "removed",
            "removed_at": clock.now,
        },
        "started": {"starts_at": clock.now - timedelta(minutes=30)},
    }


@pytest.mark.page("F25", 6)
@pytest.mark.parametrize(
    "gone", ["completed", "cancelled", "expired", "removed", "started"]
)
def test_a_notification_for_a_post_that_is_gone_keeps_its_text_and_has_no_action(
    clock, db, client, inbox_user, inbox_headers, gone
):
    post = make_sub_post(db, owner=make_user(db), **posts_no_longer_open(clock)[gone])
    notice = make_notification(
        db,
        user=inbox_user,
        event_at=clock.now - timedelta(hours=1),
        notification_type="sub_request_confirmed",
        sub_post=post,
    )

    item = first_action(client, inbox_headers, "/inbox/game-activity")

    assert item["action"] is None
    assert item["title"] == notice.title
    assert item["message"] == notice.body


@pytest.mark.page("F25", 6)
def test_a_need_a_sub_chat_notice_after_losing_chat_access_has_a_disabled_action(
    clock, db, client, inbox_user, inbox_headers
):
    post = make_sub_post(
        db, owner=make_user(db), starts_at=clock.now + timedelta(days=2)
    )
    chat = get_or_create_active_sub_post_chat(db, post)
    make_sub_post_request(
        db, post=post, requester=inbox_user, request_status="canceled_by_player"
    )
    make_notification(
        db,
        user=inbox_user,
        event_at=clock.now - timedelta(minutes=1),
        notification_type="sub_chat_message",
        sub_post=post,
        related_sub_post_chat_id=chat.id,
    )

    item = first_action(client, inbox_headers, "/inbox/game-activity")

    assert item["action"] == {
        "key": "view_sub_post",
        "label": "View post",
        "path": None,
        "disabled": True,
        "disabled_reason": "You no longer have access to this chat.",
        "state": None,
    }


@pytest.mark.page("F25", 6)
def test_a_policy_notice_action_is_not_chosen_from_its_message_text(
    clock, db, client, inbox_user, inbox_headers
):
    make_notification(
        db,
        user=inbox_user,
        event_at=clock.now - timedelta(minutes=1),
        notification_type="policy_update",
        action_key="view_policy",
        title="Privacy policy update",
        body="Our privacy policy changed.",
    )

    item = first_action(client, inbox_headers, "/inbox/app-updates")

    assert item["action"] is None
