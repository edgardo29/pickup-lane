from __future__ import annotations

import pytest
from sqlalchemy import func, select

from backend.tests.workflows.game_community_roster_chat_need_a_sub_relationship_authorization.test_matrix_scope_and_dependencies_contract import (
    _Identity,
    _auth_headers,
    _install_auth_identities,
    _recent_time,
    _session,
    _sub_chat,
    _sub_chat_message,
    _sub_position,
    _sub_post,
    _sub_request,
    _user,
)

pytestmark = pytest.mark.suite_type("ordinary")


def _sub_message_count(db, chat_id) -> int:
    from backend.models import SubPostChatMessage

    return (
        db.scalar(
            select(func.count())
            .select_from(SubPostChatMessage)
            .where(SubPostChatMessage.chat_id == chat_id)
        )
        or 0
    )


@pytest.mark.requirement("WS03-04C-R8", "WS03-04C-R10")
def test_need_a_sub_owner_requester_lifecycle_and_public_position_boundaries(
    client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _session() as db:
        owner = _user("sub-owner")
        requester = _user("sub-requester")
        unrelated = _user("sub-unrelated")
        visible_post = _sub_post(owner_user_id=owner.id, label="visible")
        hidden_post = _sub_post(
            owner_user_id=owner.id,
            label="hidden",
            public_visibility_status="hidden",
            starts_delta_days=6,
        )
        visible_position = _sub_position(visible_post.id, "visible")
        hidden_position = _sub_position(hidden_post.id, "hidden")
        pending_request = _sub_request(
            sub_post_id=visible_post.id,
            position_id=visible_position.id,
            requester_user_id=requester.id,
            request_status="pending",
        )
        db.add_all([owner, requester, unrelated])
        db.flush()
        db.add_all([visible_post, hidden_post])
        db.flush()
        db.add_all([visible_position, hidden_position])
        db.flush()
        db.add(pending_request)
        db.commit()
        owner_auth_id = owner.auth_user_id
        owner_email = owner.email
        requester_auth_id = requester.auth_user_id
        requester_email = requester.email
        unrelated_auth_id = unrelated.auth_user_id
        unrelated_email = unrelated.email
        visible_post_id = visible_post.id
        hidden_post_id = hidden_post.id
        visible_position_id = visible_position.id
        pending_request_id = pending_request.id

    _install_auth_identities(
        monkeypatch,
        {
            "owner-token": _Identity(
                auth_user_id=owner_auth_id,
                email=owner_email,
                email_verified=True,
                authenticated_at=_recent_time(),
            ),
            "requester-token": _Identity(
                auth_user_id=requester_auth_id,
                email=requester_email,
                email_verified=True,
                authenticated_at=_recent_time(),
            ),
            "unrelated-token": _Identity(
                auth_user_id=unrelated_auth_id,
                email=unrelated_email,
                email_verified=True,
                authenticated_at=_recent_time(),
            ),
        },
    )

    positions = client.get(f"/need-a-sub/posts/{visible_post_id}/positions")
    assert positions.status_code == 200
    assert {item["id"] for item in positions.json()} == {str(visible_position_id)}
    assert client.get(f"/need-a-sub/posts/{hidden_post_id}/positions").status_code == 404

    owner_requests = client.get(
        f"/need-a-sub/posts/{visible_post_id}/requests",
        headers=_auth_headers("owner-token"),
    )
    assert owner_requests.status_code == 200
    assert {item["id"] for item in owner_requests.json()} == {str(pending_request_id)}
    assert (
        client.get(
            f"/need-a-sub/posts/{visible_post_id}/requests",
            headers=_auth_headers("unrelated-token"),
        ).status_code
        == 403
    )

    wrong_owner_accept = client.patch(
        f"/need-a-sub/requests/{pending_request_id}/accept",
        headers=_auth_headers("unrelated-token"),
    )
    assert wrong_owner_accept.status_code == 403
    with _session() as db:
        from backend.models import SubPostRequest

        assert db.get(SubPostRequest, pending_request_id).request_status == "pending"

    accepted = client.patch(
        f"/need-a-sub/requests/{pending_request_id}/accept",
        headers=_auth_headers("owner-token"),
    )
    assert accepted.status_code == 200
    assert accepted.json()["request_status"] == "confirmed"

    canceled = client.patch(
        f"/need-a-sub/requests/{pending_request_id}/cancel",
        headers=_auth_headers("requester-token"),
    )
    assert canceled.status_code == 200
    assert canceled.json()["request_status"] == "canceled_by_player"


@pytest.mark.requirement("WS03-04C-R8", "WS03-04C-R9", "WS03-04C-R10")
def test_need_a_sub_chat_requires_confirmed_relationship_and_binds_sender_read_state(
    client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _session() as db:
        owner = _user("sub-chat-owner")
        confirmed = _user("sub-chat-confirmed")
        pending = _user("sub-chat-pending")
        unrelated = _user("sub-chat-unrelated")
        post = _sub_post(owner_user_id=owner.id, label="chat")
        position = _sub_position(post.id, "chat")
        confirmed_request = _sub_request(
            sub_post_id=post.id,
            position_id=position.id,
            requester_user_id=confirmed.id,
            request_status="confirmed",
        )
        pending_request = _sub_request(
            sub_post_id=post.id,
            position_id=position.id,
            requester_user_id=pending.id,
            request_status="pending",
        )
        chat = _sub_chat(post.id)
        visible_message = _sub_chat_message(
            chat_id=chat.id,
            sender_user_id=owner.id,
            label="visible",
            visibility_status="visible",
        )
        removed_message = _sub_chat_message(
            chat_id=chat.id,
            sender_user_id=owner.id,
            label="removed",
            visibility_status="removed",
        )
        db.add_all([owner, confirmed, pending, unrelated])
        db.flush()
        db.add(post)
        db.flush()
        db.add(position)
        db.flush()
        db.add_all([confirmed_request, pending_request, chat])
        db.flush()
        db.add_all([visible_message, removed_message])
        db.commit()
        owner_auth_id = owner.auth_user_id
        owner_email = owner.email
        confirmed_auth_id = confirmed.auth_user_id
        confirmed_email = confirmed.email
        confirmed_id = confirmed.id
        pending_auth_id = pending.auth_user_id
        pending_email = pending.email
        unrelated_auth_id = unrelated.auth_user_id
        unrelated_email = unrelated.email
        post_id = post.id
        chat_id = chat.id
        visible_message_id = visible_message.id
        before_messages = _sub_message_count(db, chat_id)

    _install_auth_identities(
        monkeypatch,
        {
            "owner-token": _Identity(
                auth_user_id=owner_auth_id,
                email=owner_email,
                email_verified=True,
                authenticated_at=_recent_time(),
            ),
            "confirmed-token": _Identity(
                auth_user_id=confirmed_auth_id,
                email=confirmed_email,
                email_verified=True,
                authenticated_at=_recent_time(),
            ),
            "pending-token": _Identity(
                auth_user_id=pending_auth_id,
                email=pending_email,
                email_verified=True,
                authenticated_at=_recent_time(),
            ),
            "unrelated-token": _Identity(
                auth_user_id=unrelated_auth_id,
                email=unrelated_email,
                email_verified=True,
                authenticated_at=_recent_time(),
            ),
        },
    )

    owner_chat = client.get(
        f"/need-a-sub/posts/{post_id}/chat",
        headers=_auth_headers("owner-token"),
    )
    assert owner_chat.status_code == 200
    assert owner_chat.json()["id"] == str(chat_id)
    assert (
        client.get(
            f"/need-a-sub/posts/{post_id}/chat",
            headers=_auth_headers("pending-token"),
        ).status_code
        == 403
    )

    messages = client.get(
        f"/need-a-sub/posts/{post_id}/chat/messages",
        headers=_auth_headers("confirmed-token"),
    )
    assert messages.status_code == 200
    assert {item["id"] for item in messages.json()} == {str(visible_message_id)}

    read_state = client.get(
        f"/need-a-sub/posts/{post_id}/chat/read-state",
        headers=_auth_headers("confirmed-token"),
    )
    assert read_state.status_code == 200
    assert read_state.json()["user_id"] == str(confirmed_id)

    marked_read = client.post(
        f"/need-a-sub/posts/{post_id}/chat/read",
        headers=_auth_headers("confirmed-token"),
        json={},
    )
    assert marked_read.status_code == 200
    assert marked_read.json()["user_id"] == str(confirmed_id)

    created = client.post(
        f"/need-a-sub/posts/{post_id}/chat/messages",
        headers=_auth_headers("confirmed-token"),
        json={"chat_id": str(chat_id), "message_body": "confirmed player message"},
    )
    assert created.status_code == 201
    assert created.json()["sender_user_id"] == str(confirmed_id)

    wrong_chat_id = client.post(
        f"/need-a-sub/posts/{post_id}/chat/messages",
        headers=_auth_headers("confirmed-token"),
        json={"chat_id": str(visible_message_id), "message_body": "wrong chat"},
    )
    assert wrong_chat_id.status_code == 400

    unrelated_message = client.post(
        f"/need-a-sub/posts/{post_id}/chat/messages",
        headers=_auth_headers("unrelated-token"),
        json={"chat_id": str(chat_id), "message_body": "blocked"},
    )
    assert unrelated_message.status_code == 403

    with _session() as db:
        from backend.models import SubPostChatMessage, SubPostChatRead

        persisted = db.get(SubPostChatMessage, created.json()["id"])
        assert persisted.sender_user_id == confirmed_id
        assert _sub_message_count(db, chat_id) == before_messages + 1
        assert db.scalar(
            select(func.count())
            .select_from(SubPostChatRead)
            .where(
                SubPostChatRead.chat_id == chat_id,
                SubPostChatRead.user_id == confirmed_id,
            )
        )
        assert db.get(SubPostChatMessage, visible_message_id).visibility_status == "visible"
