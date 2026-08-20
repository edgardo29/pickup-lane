from __future__ import annotations

import pytest
from sqlalchemy import func, select

from backend.tests.workflows.game_community_roster_chat_need_a_sub_relationship_authorization.test_matrix_scope_and_dependencies_contract import (
    _Identity,
    _auth_headers,
    _chat_message,
    _game,
    _game_chat,
    _install_auth_identities,
    _participant,
    _recent_time,
    _session,
    _user,
    _venue,
)

pytestmark = pytest.mark.suite_type("ordinary")


def _message_count(db, chat_id) -> int:
    from backend.models import ChatMessage

    return (
        db.scalar(
            select(func.count())
            .select_from(ChatMessage)
            .where(ChatMessage.chat_id == chat_id)
        )
        or 0
    )


def _read_state_count(db, chat_id) -> int:
    from backend.models import GameChatRead

    return (
        db.scalar(
            select(func.count())
            .select_from(GameChatRead)
            .where(GameChatRead.chat_id == chat_id)
        )
        or 0
    )


@pytest.mark.requirement("WS03-04C-R7", "WS03-04C-R9", "WS03-04C-R10")
def test_game_chat_membership_sender_read_state_and_removed_message_boundaries(
    client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _session() as db:
        host = _user("chat-host")
        player = _user("chat-player")
        nonmember = _user("chat-nonmember")
        venue = _venue(host.id, "chat")
        game = _game(host_user_id=host.id, venue_id=venue.id, label="chat")
        closed_game = _game(
            host_user_id=host.id,
            venue_id=venue.id,
            label="closed-chat",
            starts_delta_days=31,
        )
        participant = _participant(
            game_id=game.id,
            user_id=player.id,
            booking_id=None,
            label="chat-player",
        )
        closed_participant = _participant(
            game_id=closed_game.id,
            user_id=player.id,
            booking_id=None,
            label="closed-chat-player",
        )
        chat = _game_chat(game.id)
        visible_message = _chat_message(
            chat_id=chat.id,
            sender_user_id=host.id,
            label="visible",
            visibility_status="visible",
        )
        removed_message = _chat_message(
            chat_id=chat.id,
            sender_user_id=host.id,
            label="removed",
            visibility_status="removed",
        )
        closed_chat = _game_chat(closed_game.id, chat_status="closed")
        db.add_all([host, player, nonmember])
        db.flush()
        db.add(venue)
        db.flush()
        db.add_all([game, closed_game])
        db.flush()
        db.add_all([participant, closed_participant, chat, closed_chat])
        db.flush()
        db.add_all([visible_message, removed_message])
        db.commit()
        host_auth_id = host.auth_user_id
        host_email = host.email
        player_auth_id = player.auth_user_id
        player_email = player.email
        player_id = player.id
        nonmember_auth_id = nonmember.auth_user_id
        nonmember_email = nonmember.email
        nonmember_id = nonmember.id
        game_id = game.id
        chat_id = chat.id
        closed_chat_id = closed_chat.id
        visible_message_id = visible_message.id
        removed_message_id = removed_message.id
        before_nonmember = _message_count(db, chat_id)
        before_closed = _message_count(db, closed_chat_id)

    _install_auth_identities(
        monkeypatch,
        {
            "host-token": _Identity(
                auth_user_id=host_auth_id,
                email=host_email,
                email_verified=True,
                authenticated_at=_recent_time(),
            ),
            "player-token": _Identity(
                auth_user_id=player_auth_id,
                email=player_email,
                email_verified=True,
                authenticated_at=_recent_time(),
            ),
            "nonmember-token": _Identity(
                auth_user_id=nonmember_auth_id,
                email=nonmember_email,
                email_verified=True,
                authenticated_at=_recent_time(),
            ),
        },
    )

    ensured = client.post(
        f"/game-chats/for-game/{game_id}",
        headers=_auth_headers("host-token"),
        json={},
    )
    assert ensured.status_code == 200
    assert ensured.json()["id"] == str(chat_id)
    assert (
        client.post(
            f"/game-chats/for-game/{game_id}",
            headers=_auth_headers("nonmember-token"),
            json={},
        ).status_code
        == 403
    )

    visible_list = client.get(
        "/chat-messages",
        headers=_auth_headers("player-token"),
        params={"chat_id": str(chat_id)},
    )
    assert visible_list.status_code == 200
    assert {item["id"] for item in visible_list.json()} == {str(visible_message_id)}
    assert client.get(f"/chat-messages/{visible_message_id}", headers=_auth_headers("player-token")).status_code == 200
    assert (
        client.get(
            f"/chat-messages/{removed_message_id}",
            headers=_auth_headers("player-token"),
        ).status_code
        == 404
    )
    assert (
        client.get(
            "/chat-messages",
            headers=_auth_headers("player-token"),
            params={"chat_id": str(chat_id), "visibility_status": "removed"},
        ).status_code
        == 403
    )

    read_state = client.get(
        f"/game-chats/{chat_id}/read-state",
        headers=_auth_headers("player-token"),
        params={"acting_user_id": str(nonmember_id)},
    )
    assert read_state.status_code == 200
    assert read_state.json()["user_id"] == str(player_id)

    marked_read = client.post(
        f"/game-chats/{chat_id}/read",
        headers=_auth_headers("player-token"),
        json={"acting_user_id": str(nonmember_id)},
    )
    assert marked_read.status_code == 200
    assert marked_read.json()["user_id"] == str(player_id)

    created = client.post(
        "/chat-messages",
        headers=_auth_headers("player-token"),
        json={"chat_id": str(chat_id), "message_body": "hello from player"},
    )
    assert created.status_code == 201
    assert created.json()["sender_user_id"] == str(player_id)

    nonmember_message = client.post(
        "/chat-messages",
        headers=_auth_headers("nonmember-token"),
        json={"chat_id": str(chat_id), "message_body": "blocked nonmember"},
    )
    assert nonmember_message.status_code == 403

    closed_message = client.post(
        "/chat-messages",
        headers=_auth_headers("player-token"),
        json={"chat_id": str(closed_chat_id), "message_body": "blocked closed"},
    )
    assert closed_message.status_code == 400

    with _session() as db:
        from backend.models import ChatMessage, GameChatRead

        persisted = db.get(ChatMessage, created.json()["id"])
        assert persisted.sender_user_id == player_id
        assert _message_count(db, chat_id) == before_nonmember + 1
        assert _message_count(db, closed_chat_id) == before_closed
        read_state_row = db.scalar(
            select(GameChatRead).where(
                GameChatRead.chat_id == chat_id,
                GameChatRead.user_id == player_id,
            )
        )
        assert read_state_row is not None
        assert _read_state_count(db, chat_id) == 1
