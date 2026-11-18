"""F16 game chat access and message limits."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from backend.models import ChatMessage
from backend.tests.factories import make_game, make_participant, make_user


@pytest.mark.page("F16", 3)
def test_host_and_confirmed_player_can_open_chat_but_waitlisted_player_cannot(
    clock, db, client, firebase
):
    host = make_user(db, hosting_status="eligible")
    game = make_game(
        db,
        game_type="community",
        host=host,
        starts_at=clock.now + timedelta(days=2),
    )
    confirmed = make_user(db)
    waitlisted = make_user(db)
    make_participant(db, game=game, user=confirmed)
    make_participant(db, game=game, user=waitlisted, participant_status="waitlisted")
    path = f"/game-chats/for-game/{game.id}"

    host_response = client.post(path, headers=firebase.sign_in(host), json={})
    confirmed_response = client.post(path, headers=firebase.sign_in(confirmed), json={})
    waitlisted_response = client.post(
        path, headers=firebase.sign_in(waitlisted), json={}
    )

    assert host_response.status_code == 200, host_response.text
    assert confirmed_response.status_code == 200, confirmed_response.text
    assert waitlisted_response.status_code == 403
    assert host_response.json()["id"] == confirmed_response.json()["id"]


@pytest.mark.page("F16", 10)
def test_message_appears_and_opening_chat_clears_unread_state(db, client, firebase):
    host = make_user(db, hosting_status="eligible")
    player = make_user(db)
    game = make_game(
        db,
        game_type="community",
        host=host,
        starts_at=datetime.now(UTC) + timedelta(days=2),
    )
    make_participant(db, game=game, user=player)
    host_headers = firebase.sign_in(host)
    player_headers = firebase.sign_in(player)
    room = client.post(f"/game-chats/for-game/{game.id}", headers=host_headers, json={})
    assert room.status_code == 200, room.text
    chat_id = room.json()["id"]

    sent = client.post(
        "/chat-messages",
        headers=host_headers,
        json={"chat_id": chat_id, "message_body": "See you there"},
    )
    messages = client.get(
        f"/chat-messages?chat_id={chat_id}&visibility_status=visible",
        headers=player_headers,
    )
    read = client.post(f"/game-chats/{chat_id}/read", headers=player_headers, json={})
    after = client.get(f"/game-chats/{chat_id}/read-state", headers=player_headers)

    assert sent.status_code == 201, sent.text
    assert messages.status_code == 200, messages.text
    assert [row["message_body"] for row in messages.json()] == ["See you there"]
    assert read.status_code == 200, read.text
    assert after.status_code == 200, after.text
    assert after.json()["unread_count"] == 0


@pytest.mark.page("F16", 18)
def test_empty_oversized_and_rapid_messages_do_not_create_extra_rows(
    clock, db, client, firebase
):
    host = make_user(db, hosting_status="eligible")
    game = make_game(
        db,
        game_type="community",
        host=host,
        starts_at=clock.now + timedelta(days=2),
    )
    headers = firebase.sign_in(host)
    room = client.post(f"/game-chats/for-game/{game.id}", headers=headers, json={})
    assert room.status_code == 200, room.text
    chat_id = room.json()["id"]
    path = "/chat-messages"

    empty = client.post(
        path, headers=headers, json={"chat_id": chat_id, "message_body": "   "}
    )
    oversized = client.post(
        path, headers=headers, json={"chat_id": chat_id, "message_body": "x" * 301}
    )
    accepted = [
        client.post(
            path,
            headers=headers,
            json={"chat_id": chat_id, "message_body": f"Message {index}"},
        )
        for index in range(5)
    ]
    rapid = client.post(
        path,
        headers=headers,
        json={"chat_id": chat_id, "message_body": "Message six"},
    )

    assert empty.status_code in (400, 422)
    assert oversized.status_code in (400, 422)
    assert all(response.status_code == 201 for response in accepted)
    assert rapid.status_code == 429
    assert db.scalar(select(func.count(ChatMessage.id))) == 5
