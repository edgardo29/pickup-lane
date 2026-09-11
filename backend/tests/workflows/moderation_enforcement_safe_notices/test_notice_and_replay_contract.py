from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from backend.models import AdminAction, AdminTargetNotice, Game, Notification
from backend.schemas.admin_target_notice_schema import AdminTargetNoticeRead
from backend.services.community_game_enforcement_service import (
    COMMUNITY_GAME_ADMIN_CANCELLATION_PUBLIC_REASON,
)
from backend.services.need_a_sub_post_service import (
    ADMIN_SUB_POST_REMOVAL_PUBLIC_REASON,
)
from backend.tests.workflows.admin_route_list_high_risk_function_authorization.test_admin_game_roster_moderation_contract import (
    _persist_community_game_fixture,
    _persist_game_chat_message_fixture,
    _persist_game_fixture,
    _persist_sub_post_chat_message_fixture,
    _persist_sub_post_fixture,
    _persist_sub_post_request_fixture,
)
from backend.tests.workflows.admin_route_list_high_risk_function_authorization.test_admin_matrix_scope_and_dependencies_contract import (
    _add_users,
    _auth_headers,
    _client,
    _install_tokens_for_users,
    _session,
    _user,
)

pytestmark = pytest.mark.suite_type("ordinary")

PRIVATE_CANARY = "PRIVATE-CANARY-REPORTER-SECRET-7429"
SECOND_PRIVATE_CANARY = "PRIVATE-CANARY-ALTERNATE-DETAIL-9137"
RESTRICTIVE_NOTICE_TYPES = {
    "community_game_hidden",
    "community_game_joining_paused",
    "community_game_payment_info_hidden",
    "community_game_cancelled",
    "need_sub_post_hidden",
    "need_sub_post_removed",
    "game_chat_message_removed",
    "need_sub_chat_message_removed",
}


def _post_action(client, path: str, key: str):
    response = client.post(
        path,
        json={"reason": PRIVATE_CANARY, "idempotency_key": key},
        headers=_auth_headers("admin-token"),
    )
    assert response.status_code == 200, response.text
    return response


def _assert_safe_target_notice(db, notice: AdminTargetNotice) -> None:
    serialized = AdminTargetNoticeRead.model_validate(notice).model_dump(mode="json")
    assert serialized["user_safe_reason"] is None
    assert PRIVATE_CANARY not in json.dumps(serialized, sort_keys=True)
    target_copy = f"{notice.title} {notice.body}"
    assert PRIVATE_CANARY not in target_copy
    assert notice.admin_action_id is not None
    assert notice.recipient_user_id == notice.target_user_id

    notification_id = uuid.UUID(notice.notice_metadata["notification_id"])
    notification = db.get(Notification, notification_id)
    assert notification is not None
    assert notification.user_id == notice.recipient_user_id
    assert notification.notification_type == "admin_enforcement_notice"
    visible_copy = f"{notification.title} {notification.summary} {notification.body}"
    assert PRIVATE_CANARY not in visible_copy
    if notice.notice_type in RESTRICTIVE_NOTICE_TYPES:
        for copy in (target_copy, visible_copy):
            normalized_copy = copy.lower()
            assert "safety or policy reasons" in normalized_copy
            assert "contact support" in normalized_copy


def test_target_notice_families_are_safe_linked_and_replay_from_authoritative_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = _user("05c-notice-admin", role="admin")
    host = _user("05c-notice-host")
    owner = _user("05c-notice-owner")
    game_sender = _user("05c-game-sender")
    sub_sender = _user("05c-sub-sender")
    creator = _user("05c-game-creator")
    _add_users(admin, host, owner, game_sender, sub_sender, creator)
    community_game_id, _ = _persist_community_game_fixture(
        "05c-notices",
        admin=admin,
        host=host,
    )
    official_game_id, _ = _persist_game_fixture(
        "05c-chat-notices",
        admin=admin,
        creator=creator,
    )
    post_id = _persist_sub_post_fixture("05c-notices", owner=owner)
    game_message_id = _persist_game_chat_message_fixture(
        game_id=official_game_id,
        sender_user_id=game_sender.id,
    )
    sub_message_id = _persist_sub_post_chat_message_fixture(
        post_id=post_id,
        sender_user_id=sub_sender.id,
    )
    _install_tokens_for_users(monkeypatch, {"admin-token": admin})
    client = _client()

    calls = [
        (f"/admin/community-games/{community_game_id}/hide", "05c-community-hide"),
        (
            f"/admin/community-games/{community_game_id}/restore",
            "05c-community-restore",
        ),
        (
            f"/admin/community-games/{community_game_id}/pause-joining",
            "05c-community-pause",
        ),
        (
            f"/admin/community-games/{community_game_id}/resume-joining",
            "05c-community-resume",
        ),
        (
            f"/admin/community-games/{community_game_id}/hide-payment-text",
            "05c-payment-hide",
        ),
        (
            f"/admin/community-games/{community_game_id}/restore-payment-text",
            "05c-payment-restore",
        ),
        (f"/admin/need-a-sub/{post_id}/hide", "05c-sub-hide"),
        (f"/admin/need-a-sub/{post_id}/restore", "05c-sub-restore"),
        (
            (
                f"/admin/official-games/{official_game_id}/chat/messages/"
                f"{game_message_id}/remove"
            ),
            "05c-game-chat-remove",
        ),
        (
            (
                f"/admin/official-games/{official_game_id}/chat/messages/"
                f"{game_message_id}/restore"
            ),
            "05c-game-chat-restore",
        ),
        (
            f"/admin/need-a-sub/{post_id}/chat/messages/{sub_message_id}/remove",
            "05c-sub-chat-remove",
        ),
        (
            f"/admin/need-a-sub/{post_id}/chat/messages/{sub_message_id}/restore",
            "05c-sub-chat-restore",
        ),
    ]
    responses = {key: _post_action(client, path, key) for path, key in calls}

    with _session() as db:
        actions = list(
            db.scalars(
                select(AdminAction).where(AdminAction.admin_user_id == admin.id)
            ).all()
        )
        notices = list(
            db.scalars(
                select(AdminTargetNotice)
                .join(AdminAction, AdminAction.id == AdminTargetNotice.admin_action_id)
                .where(AdminAction.admin_user_id == admin.id)
            ).all()
        )
        assert len(actions) == 12
        assert len(notices) == 12
        assert {notice.notice_type for notice in notices} == {
            "community_game_hidden",
            "community_game_restored",
            "community_game_joining_paused",
            "community_game_joining_resumed",
            "community_game_payment_info_hidden",
            "community_game_payment_info_restored",
            "need_sub_post_hidden",
            "need_sub_post_restored",
            "game_chat_message_removed",
            "game_chat_message_restored",
            "need_sub_chat_message_removed",
            "need_sub_chat_message_restored",
        }
        for action in actions:
            assert action.reason == PRIVATE_CANARY
            assert "notice_ids" not in (action.metadata_ or {})
            assert "notice_suppression_reason" not in (action.metadata_ or {})
        for notice in notices:
            _assert_safe_target_notice(db, notice)

    replay_cases = [
        (calls[0], "enforcement_state", "public_visibility_status", "visible"),
        (calls[4], "moderation_state", "unsafe_payment_text_hidden", False),
        (calls[6], None, "public_visibility_status", "visible"),
    ]
    for (path, key), container, field, expected in replay_cases:
        replay = _post_action(client, path, key)
        assert replay.json()["idempotent_replay"] is True
        payload = replay.json()[container] if container else replay.json()
        assert payload[field] == expected
        assert (
            replay.json()["audit_action_id"] == responses[key].json()["audit_action_id"]
        )

    game_remove_path, game_remove_key = calls[8]
    chat_replay = _post_action(client, game_remove_path, game_remove_key)
    assert chat_replay.json()["idempotent_replay"] is True
    assert set(chat_replay.json()) == {
        "message_id",
        "audit_action_id",
        "idempotent_replay",
    }
    assert (
        chat_replay.json()["audit_action_id"]
        == responses[game_remove_key].json()["audit_action_id"]
    )

    with _session() as db:
        assert (
            db.query(AdminAction).filter(AdminAction.admin_user_id == admin.id).count()
            == 12
        )
        assert (
            db.query(AdminTargetNotice)
            .join(AdminAction, AdminAction.id == AdminTargetNotice.admin_action_id)
            .filter(AdminAction.admin_user_id == admin.id)
            .count()
            == 12
        )


def test_account_and_hosting_replay_reuses_safe_notification_and_current_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = _user("05c-direct-admin", role="admin")
    target = _user("05c-direct-target")
    _add_users(admin, target)
    _install_tokens_for_users(monkeypatch, {"admin-token": admin})
    client = _client()

    suspend_preview = client.post(
        f"/admin/users/{target.id}/suspension-preview",
        headers=_auth_headers("admin-token"),
    )
    assert suspend_preview.status_code == 200
    suspend_payload = {
        "preview_token": suspend_preview.json()["preview_token"],
        "reason": PRIVATE_CANARY,
        "idempotency_key": "05c-suspend-direct",
    }
    suspended = client.post(
        f"/admin/users/{target.id}/suspend",
        json=suspend_payload,
        headers=_auth_headers("admin-token"),
    )
    assert suspended.status_code == 200
    unsuspended = _post_action(
        client,
        f"/admin/users/{target.id}/unsuspend",
        "05c-unsuspend-direct",
    )
    suspend_replay = client.post(
        f"/admin/users/{target.id}/suspend",
        json=suspend_payload,
        headers=_auth_headers("admin-token"),
    )
    assert suspend_replay.status_code == 200
    assert suspend_replay.json()["account_status"] == "active"
    assert (
        suspend_replay.json()["admin_action_id"] == suspended.json()["admin_action_id"]
    )
    assert (
        suspend_replay.json()["notification_id"] == suspended.json()["notification_id"]
    )

    hosting_preview = client.post(
        f"/admin/users/{target.id}/hosting-restriction-preview",
        headers=_auth_headers("admin-token"),
    )
    assert hosting_preview.status_code == 200
    restrict_payload = {
        "preview_token": hosting_preview.json()["preview_token"],
        "reason": PRIVATE_CANARY,
        "idempotency_key": "05c-restrict-direct",
    }
    restricted = client.post(
        f"/admin/users/{target.id}/restrict-hosting",
        json=restrict_payload,
        headers=_auth_headers("admin-token"),
    )
    assert restricted.status_code == 200
    restored = _post_action(
        client,
        f"/admin/users/{target.id}/restore-hosting",
        "05c-restore-direct",
    )
    restrict_replay = client.post(
        f"/admin/users/{target.id}/restrict-hosting",
        json=restrict_payload,
        headers=_auth_headers("admin-token"),
    )
    assert restrict_replay.status_code == 200
    assert restrict_replay.json()["hosting_status"] == "eligible"
    assert (
        restrict_replay.json()["admin_action_id"]
        == restricted.json()["admin_action_id"]
    )
    assert (
        restrict_replay.json()["notification_id"]
        == restricted.json()["notification_id"]
    )

    action_ids = {
        uuid.UUID(response.json()["admin_action_id"])
        for response in (suspended, unsuspended, restricted, restored)
    }
    with _session() as db:
        actions = list(
            db.scalars(select(AdminAction).where(AdminAction.id.in_(action_ids))).all()
        )
        assert len(actions) == 4
        notifications = [
            db.get(Notification, action.target_notification_id) for action in actions
        ]
        assert all(notification is not None for notification in notifications)
        assert len({notification.id for notification in notifications}) == 4
        for action, notification in zip(actions, notifications, strict=True):
            assert action.reason == PRIVATE_CANARY
            visible_copy = (
                f"{notification.title} {notification.summary} {notification.body}"
            )
            assert PRIVATE_CANARY not in visible_copy
            if action.action_type in {"suspend_user", "restrict_hosting"}:
                normalized_copy = visible_copy.lower()
                assert "safety or policy reasons" in normalized_copy
                assert "contact support" in normalized_copy


def test_null_chat_senders_record_only_suppression_and_never_notify_on_replay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import ChatMessage, SubPostChatMessage

    admin = _user("05c-null-admin", role="admin")
    creator = _user("05c-null-creator")
    original_sender = _user("05c-null-sender")
    owner = _user("05c-null-owner")
    _add_users(admin, creator, original_sender, owner)
    game_id, _ = _persist_game_fixture(
        "05c-null-chat",
        admin=admin,
        creator=creator,
    )
    post_id = _persist_sub_post_fixture("05c-null-chat", owner=owner)
    game_message_id = _persist_game_chat_message_fixture(
        game_id=game_id,
        sender_user_id=original_sender.id,
    )
    sub_message_id = _persist_sub_post_chat_message_fixture(
        post_id=post_id,
        sender_user_id=original_sender.id,
    )
    with _session() as db:
        game_message = db.get(ChatMessage, game_message_id)
        sub_message = db.get(SubPostChatMessage, sub_message_id)
        game_message.message_type = "system"
        game_message.sender_user_id = None
        sub_message.sender_user_id = None
        db.commit()

    _install_tokens_for_users(monkeypatch, {"admin-token": admin})
    client = _client()
    calls = [
        (
            f"/admin/official-games/{game_id}/chat/messages/{game_message_id}/remove",
            "05c-null-game-remove",
        ),
        (
            f"/admin/official-games/{game_id}/chat/messages/{game_message_id}/restore",
            "05c-null-game-restore",
        ),
        (
            f"/admin/need-a-sub/{post_id}/chat/messages/{sub_message_id}/remove",
            "05c-null-sub-remove",
        ),
        (
            f"/admin/need-a-sub/{post_id}/chat/messages/{sub_message_id}/restore",
            "05c-null-sub-restore",
        ),
    ]
    responses = [_post_action(client, path, key) for path, key in calls]

    action_ids = {
        uuid.UUID(response.json()["audit_action_id"]) for response in responses
    }
    with _session() as db:
        actions = list(
            db.scalars(select(AdminAction).where(AdminAction.id.in_(action_ids))).all()
        )
        assert len(actions) == 4
        for action in actions:
            assert action.target_user_id is None
            assert action.metadata_["notice_suppression_reason"] == (
                "recipient_unavailable"
            )
        assert (
            db.query(AdminTargetNotice)
            .filter(AdminTargetNotice.admin_action_id.in_(action_ids))
            .count()
            == 0
        )

    for (path, key), original in zip(calls, responses, strict=True):
        replay = _post_action(client, path, key)
        assert replay.json()["idempotent_replay"] is True
        assert replay.json()["audit_action_id"] == original.json()["audit_action_id"]
        assert set(replay.json()) == {
            "message_id",
            "audit_action_id",
            "idempotent_replay",
        }

    with _session() as db:
        assert (
            db.query(AdminTargetNotice)
            .filter(AdminTargetNotice.admin_action_id.in_(action_ids))
            .count()
            == 0
        )


def test_cancellation_and_sub_removal_use_exact_nonduplicate_recipient_sets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import GameParticipant, GameStatusHistory, SubPost

    admin = _user("05c-recipient-admin", role="admin")
    host = _user("05c-recipient-host")
    participant_user = _user("05c-recipient-player")
    owner = _user("05c-recipient-owner")
    requester = _user("05c-recipient-requester")
    _add_users(admin, host, participant_user, owner, requester)
    game_id, _ = _persist_community_game_fixture(
        "05c-recipients",
        admin=admin,
        host=host,
    )
    post_id = _persist_sub_post_fixture("05c-recipients", owner=owner)
    request = _persist_sub_post_request_fixture(
        post_id=post_id,
        requester_user_id=requester.id,
    )
    with _session() as db:
        now = datetime.now(timezone.utc)
        db.add(
            GameParticipant(
                id=uuid.uuid4(),
                game_id=game_id,
                participant_type="registered_user",
                user_id=participant_user.id,
                display_name_snapshot="Recipient player",
                participant_status="confirmed",
                attendance_status="unknown",
                cancellation_type="none",
                price_cents=0,
                currency="USD",
                joined_at=now,
                confirmed_at=now,
                created_at=now,
                updated_at=now,
            )
        )
        db.commit()

    _install_tokens_for_users(
        monkeypatch,
        {
            "admin-token": admin,
            "host-token": host,
            "owner-token": owner,
            "requester-token": requester,
        },
    )
    client = _client()
    cancelled = _post_action(
        client,
        f"/admin/community-games/{game_id}/cancel",
        "05c-recipient-cancel",
    )
    removed = _post_action(
        client,
        f"/admin/need-a-sub/{post_id}/remove",
        "05c-recipient-remove",
    )
    assert len(cancelled.json()["notice_ids"]) == 1
    assert len(removed.json()["notice_ids"]) == 2
    assert removed.json()["closed_request_ids"] == [str(request["request_id"])]

    game_detail = client.get(
        f"/games/{game_id}",
        headers=_auth_headers("host-token"),
    )
    assert game_detail.status_code == 200, game_detail.text
    assert PRIVATE_CANARY not in game_detail.text
    assert (
        game_detail.json()["cancel_reason"]
        == COMMUNITY_GAME_ADMIN_CANCELLATION_PUBLIC_REASON
    )

    post_history = client.get(
        f"/need-a-sub/posts/{post_id}/status-history",
        headers=_auth_headers("owner-token"),
    )
    assert post_history.status_code == 200, post_history.text
    assert PRIVATE_CANARY not in post_history.text
    assert post_history.json()[-1]["change_reason"] == (
        ADMIN_SUB_POST_REMOVAL_PUBLIC_REASON
    )

    request_history = client.get(
        f"/need-a-sub/requests/{request['request_id']}/status-history",
        headers=_auth_headers("requester-token"),
    )
    assert request_history.status_code == 200, request_history.text
    assert PRIVATE_CANARY not in request_history.text
    assert request_history.json()[-1]["change_reason"] == (
        ADMIN_SUB_POST_REMOVAL_PUBLIC_REASON
    )

    with _session() as db:
        cancellation_action = db.get(
            AdminAction,
            uuid.UUID(cancelled.json()["audit_action_id"]),
        )
        removal_action = db.get(
            AdminAction,
            uuid.UUID(removed.json()["audit_action_id"]),
        )
        cancellation_history = db.scalar(
            select(GameStatusHistory)
            .where(GameStatusHistory.game_id == game_id)
            .order_by(GameStatusHistory.created_at.desc())
            .limit(1)
        )
        removed_post = db.get(SubPost, post_id)
        assert cancellation_action.reason == PRIVATE_CANARY
        assert removal_action.reason == PRIVATE_CANARY
        assert cancellation_history.change_reason == (
            COMMUNITY_GAME_ADMIN_CANCELLATION_PUBLIC_REASON
        )
        assert removed_post.remove_reason == ADMIN_SUB_POST_REMOVAL_PUBLIC_REASON
        cancellation_notices = list(
            db.scalars(
                select(AdminTargetNotice).where(
                    AdminTargetNotice.admin_action_id == cancellation_action.id
                )
            ).all()
        )
        removal_notices = list(
            db.scalars(
                select(AdminTargetNotice).where(
                    AdminTargetNotice.admin_action_id == removal_action.id
                )
            ).all()
        )
        assert [
            (notice.notice_type, notice.recipient_user_id)
            for notice in cancellation_notices
        ] == [("community_game_cancelled", host.id)]
        assert {
            (notice.notice_type, notice.recipient_user_id) for notice in removal_notices
        } == {
            ("need_sub_post_removed", owner.id),
            ("need_sub_post_removed", requester.id),
        }
        for notice in cancellation_notices + removal_notices:
            _assert_safe_target_notice(db, notice)

        notification_types = {
            user_id: list(
                db.scalars(
                    select(Notification.notification_type).where(
                        Notification.user_id == user_id
                    )
                ).all()
            )
            for user_id in (host.id, participant_user.id, owner.id, requester.id)
        }
        assert notification_types[host.id] == ["admin_enforcement_notice"]
        assert notification_types[participant_user.id] == ["game_cancelled"]
        assert notification_types[owner.id] == ["admin_enforcement_notice"]
        assert notification_types[requester.id] == ["admin_enforcement_notice"]
        assert "notice_ids" not in (cancellation_action.metadata_ or {})
        assert "notice_ids" not in (removal_action.metadata_ or {})


def test_cancelled_community_game_cannot_be_restored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = _user("05c-cancelled-restore-admin", role="admin")
    host = _user("05c-cancelled-restore-host")
    _add_users(admin, host)
    game_id, _ = _persist_community_game_fixture(
        "05c-cancelled-restore",
        admin=admin,
        host=host,
    )
    _install_tokens_for_users(monkeypatch, {"admin-token": admin})
    client = _client()

    cancelled = _post_action(
        client,
        f"/admin/community-games/{game_id}/cancel",
        "05c-cancelled-restore-cancel",
    )
    rejected = client.post(
        f"/admin/community-games/{game_id}/restore",
        json={
            "reason": PRIVATE_CANARY,
            "idempotency_key": "05c-cancelled-restore-rejected",
        },
        headers=_auth_headers("admin-token"),
    )

    assert rejected.status_code == 409
    assert rejected.json()["detail"] == (
        "Cancelled or removed community games cannot be restored."
    )
    with _session() as db:
        game = db.get(Game, game_id)
        assert game.game_status == "cancelled"
        actions = list(
            db.scalars(
                select(AdminAction).where(AdminAction.target_game_id == game_id)
            ).all()
        )
        assert [(action.id, action.action_type) for action in actions] == [
            (
                uuid.UUID(cancelled.json()["audit_action_id"]),
                "admin_cancel_community_game",
            )
        ]
        assert (
            db.query(AdminTargetNotice)
            .filter(AdminTargetNotice.target_game_id == game_id)
            .count()
            == 1
        )


def test_missing_authoritative_notice_makes_replay_incomplete_without_recreation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = _user("05c-incomplete-admin", role="admin")
    host = _user("05c-incomplete-host")
    _add_users(admin, host)
    game_id, _ = _persist_community_game_fixture(
        "05c-incomplete",
        admin=admin,
        host=host,
    )
    _install_tokens_for_users(monkeypatch, {"admin-token": admin})
    client = _client()
    path = f"/admin/community-games/{game_id}/hide"
    key = "05c-incomplete-replay"
    initial = _post_action(client, path, key)
    action_id = uuid.UUID(initial.json()["audit_action_id"])

    with _session() as db:
        notice = db.scalar(
            select(AdminTargetNotice).where(
                AdminTargetNotice.admin_action_id == action_id
            )
        )
        db.delete(notice)
        db.commit()

    replay = client.post(
        path,
        json={"reason": PRIVATE_CANARY, "idempotency_key": key},
        headers=_auth_headers("admin-token"),
    )
    assert replay.status_code == 409
    assert replay.json()["detail"] == (
        "The prior Community Game action result is incomplete."
    )
    with _session() as db:
        assert (
            db.query(AdminTargetNotice)
            .filter(AdminTargetNotice.admin_action_id == action_id)
            .count()
            == 0
        )


def test_chat_wrong_removal_source_and_mismatched_replay_have_no_side_effects(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    from backend.models import ChatMessage

    admin = _user("05c-chat-reject-admin", role="admin")
    creator = _user("05c-chat-reject-creator")
    sender = _user("05c-chat-reject-sender")
    _add_users(admin, creator, sender)
    game_id, _ = _persist_game_fixture(
        "05c-chat-reject",
        admin=admin,
        creator=creator,
    )
    message_id = _persist_game_chat_message_fixture(
        game_id=game_id,
        sender_user_id=sender.id,
    )
    _install_tokens_for_users(monkeypatch, {"admin-token": admin})
    client = _client()
    remove_path = f"/admin/official-games/{game_id}/chat/messages/{message_id}/remove"
    key = "05c-chat-reject-key"
    removed = _post_action(client, remove_path, key)
    with caplog.at_level(logging.DEBUG):
        mismatched = client.post(
            remove_path,
            json={"reason": SECOND_PRIVATE_CANARY, "idempotency_key": key},
            headers=_auth_headers("admin-token"),
        )
    assert mismatched.status_code == 409
    assert PRIVATE_CANARY not in mismatched.text
    assert SECOND_PRIVATE_CANARY not in mismatched.text
    assert PRIVATE_CANARY not in caplog.text
    assert SECOND_PRIVATE_CANARY not in caplog.text

    action_id = uuid.UUID(removed.json()["audit_action_id"])
    with _session() as db:
        message = db.get(ChatMessage, message_id)
        message.removed_source = "sender"
        db.commit()
        action_count = (
            db.query(AdminAction)
            .filter(AdminAction.target_message_id == message_id)
            .count()
        )
        notice_count = (
            db.query(AdminTargetNotice)
            .filter(AdminTargetNotice.admin_action_id == action_id)
            .count()
        )

    restore = client.post(
        f"/admin/official-games/{game_id}/chat/messages/{message_id}/restore",
        json={
            "reason": PRIVATE_CANARY,
            "idempotency_key": "05c-chat-wrong-source",
        },
        headers=_auth_headers("admin-token"),
    )
    assert restore.status_code == 409
    with _session() as db:
        message = db.get(ChatMessage, message_id)
        assert message.visibility_status == "removed"
        assert message.removed_source == "sender"
        assert (
            db.query(AdminAction)
            .filter(AdminAction.target_message_id == message_id)
            .count()
            == action_count
        )
        assert (
            db.query(AdminTargetNotice)
            .filter(AdminTargetNotice.admin_action_id == action_id)
            .count()
            == notice_count
        )
