from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import event, func, select, update

from backend.models import AdminAction, GameChat, SubPostChat, User
from backend.schemas.admin_chat_moderation_schema import (
    AdminChatDetectionRead,
    AdminChatMessageRead,
    AdminChatSummaryRead,
)
from backend.schemas.admin_review_schema import (
    AdminReviewCaseClose,
    AdminReviewCaseDetailRead,
    AdminReviewCaseNoteCreate,
    AdminReviewCaseRead,
)
from backend.services.chat_moderation_service import build_safe_message_preview
from backend.tests.workflows.admin_route_list_high_risk_function_authorization.test_admin_matrix_scope_and_dependencies_contract import (
    _add_users,
    _auth_headers,
    _client,
    _install_tokens_for_users,
    _user,
)
from backend.tests.workflows.moderation_review_case_lifecycle.conftest import (
    create_content_case,
    seed_admin,
    seed_game,
    session,
)
from backend.tests.workflows.source_owned_boundaries.test_chat_boundary_contract import (
    _game,
    _game_message,
    _sub_message,
    _sub_post,
    _venue,
)

pytestmark = pytest.mark.suite_type("ordinary")


def _seed_chat_surfaces():
    admin = _user("minimum-admin", role="admin")
    sender = _user("minimum-sender")
    _add_users(admin, sender)

    venue = _venue()
    community_game = _game(sender, venue)
    official_game = _game(sender, venue)
    official_game.game_type = "official"
    official_game.policy_mode = "official_standard"
    official_game.payment_collection_type = "in_app"
    sub_post = _sub_post(sender)
    other_sub_post = _sub_post(sender)
    other_sub_post.starts_at += timedelta(days=1)
    other_sub_post.ends_at += timedelta(days=1)
    other_sub_post.starts_on_local += timedelta(days=1)
    other_sub_post.expires_at += timedelta(days=1)

    with session() as db:
        db.add(venue)
        db.commit()
        db.add_all([community_game, official_game, sub_post, other_sub_post])
        db.commit()

        community_chat = GameChat(
            id=uuid.uuid4(),
            game_id=community_game.id,
            chat_status="active",
            message_count=1,
            needs_review_count=1,
        )
        official_chat = GameChat(
            id=uuid.uuid4(),
            game_id=official_game.id,
            chat_status="active",
            message_count=1,
            needs_review_count=1,
        )
        sub_chat = SubPostChat(
            id=uuid.uuid4(),
            sub_post_id=sub_post.id,
            chat_status="active",
            message_count=1,
            needs_review_count=1,
        )
        db.add_all([community_chat, official_chat, sub_chat])
        db.commit()

        community_message = _game_message(community_chat, sender, 1)
        official_message = _game_message(official_chat, sender, 2)
        sub_message = _sub_message(sub_chat, sender, 3)
        for message in (community_message, official_message, sub_message):
            message.review_status = "needs_review"
        community_message.message_body = (
            "  Contact me at admin@example.com or 312-555-1212 and "
            "https://example.com/private  " + "x" * 180
        )
        official_message.message_body = (
            "Official private message at official@example.com " + "y" * 180
        )
        sub_message.message_body = (
            "Need a Sub private message at 312-555-0100 " + "z" * 180
        )
        db.add_all([community_message, official_message, sub_message])
        db.commit()
        seeded = {
            "admin": admin,
            "community_game_id": community_game.id,
            "community_chat_id": community_chat.id,
            "community_message_id": community_message.id,
            "community_body": community_message.message_body,
            "official_game_id": official_game.id,
            "official_message_id": official_message.id,
            "official_body": official_message.message_body,
            "post_id": sub_post.id,
            "other_post_id": other_sub_post.id,
            "sub_message_id": sub_message.id,
            "sub_body": sub_message.message_body,
        }

    return seeded


def test_legacy_game_chat_reads_do_not_bypass_scoped_admin_disclosure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seeded = _seed_chat_surfaces()
    _install_tokens_for_users(monkeypatch, {"admin-token": seeded["admin"]})
    client = _client()
    headers = _auth_headers()

    for path in (
        f"/game-chats?game_id={seeded['community_game_id']}",
        f"/game-chats/{seeded['community_chat_id']}",
    ):
        response = client.get(path, headers=headers)
        assert response.status_code == 405
        assert seeded["community_body"] not in response.text

    for path in (
        f"/chat-messages?chat_id={seeded['community_chat_id']}",
        f"/chat-messages/{seeded['community_message_id']}",
    ):
        response = client.get(path, headers=headers)
        assert response.status_code == 403
        assert seeded["community_body"] not in response.text

    assert _count_sensitive_actions() == 0


def _count_sensitive_actions() -> int:
    with session() as db:
        return int(
            db.scalar(
                select(func.count(AdminAction.id)).where(
                    AdminAction.action_type.in_(
                        {
                            "read_game_chat_moderation",
                            "reveal_game_chat_message_content",
                            "read_need_sub_chat_moderation",
                            "reveal_need_sub_chat_message_content",
                        }
                    )
                )
            )
            or 0
        )


def test_chat_surfaces_are_excerpt_first_resource_bound_and_audited(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seeded = _seed_chat_surfaces()
    _install_tokens_for_users(monkeypatch, {"admin-token": seeded["admin"]})
    client = _client()
    headers = _auth_headers()

    summary_paths = (
        f"/admin/community-games/{seeded['community_game_id']}/chat/summary",
        f"/admin/official-games/{seeded['official_game_id']}/chat/summary",
        f"/admin/need-a-sub/{seeded['post_id']}/chat/summary",
    )
    for path in summary_paths:
        response = client.get(path, headers=headers)
        assert response.status_code == 200, response.text
        assert set(response.json()) == set(AdminChatSummaryRead.model_fields)
        assert response.headers["Cache-Control"] == "private, no-store"

    list_specs = (
        (
            f"/admin/community-games/{seeded['community_game_id']}/chat/messages?view=all",
            seeded["community_body"],
        ),
        (
            f"/admin/official-games/{seeded['official_game_id']}/chat/messages?view=all",
            seeded["official_body"],
        ),
        (
            f"/admin/need-a-sub/{seeded['post_id']}/chat/messages?view=all",
            seeded["sub_body"],
        ),
    )
    for path, body in list_specs:
        response = client.get(path, headers=headers)
        assert response.status_code == 200, response.text
        assert set(response.json()) == {"messages", "total_count", "offset", "limit"}
        row = response.json()["messages"][0]
        assert set(row) == set(AdminChatMessageRead.model_fields)
        assert row["message_excerpt"] == build_safe_message_preview(body)
        assert body not in response.text
        assert response.headers["Cache-Control"] == "private, no-store"
    assert set(AdminChatDetectionRead.model_fields) == {"category", "severity"}
    assert _count_sensitive_actions() == 3

    empty_page = client.get(
        f"/admin/community-games/{seeded['community_game_id']}/chat/messages"
        "?view=all&offset=20",
        headers=headers,
    )
    assert empty_page.status_code == 200
    assert empty_page.json()["messages"] == []
    assert _count_sensitive_actions() == 3

    reveal_specs = (
        (
            (
                f"/admin/community-games/{seeded['community_game_id']}/chat/messages/"
                f"{seeded['community_message_id']}/content"
            ),
            seeded["community_message_id"],
            seeded["community_body"],
        ),
        (
            (
                f"/admin/official-games/{seeded['official_game_id']}/chat/messages/"
                f"{seeded['official_message_id']}/content"
            ),
            seeded["official_message_id"],
            seeded["official_body"],
        ),
        (
            (
                f"/admin/need-a-sub/{seeded['post_id']}/chat/messages/"
                f"{seeded['sub_message_id']}/content"
            ),
            seeded["sub_message_id"],
            seeded["sub_body"],
        ),
    )
    for path, message_id, body in reveal_specs:
        response = client.get(path, headers=headers)
        assert response.status_code == 200, response.text
        assert response.json() == {"id": str(message_id), "message_body": body}
        assert response.headers["Cache-Control"] == "private, no-store"
    assert _count_sensitive_actions() == 6

    wrong_type = client.get(
        f"/admin/official-games/{seeded['community_game_id']}/chat/messages/"
        f"{seeded['community_message_id']}/content",
        headers=headers,
    )
    wrong_parent = client.get(
        f"/admin/community-games/{seeded['community_game_id']}/chat/messages/"
        f"{seeded['official_message_id']}/content",
        headers=headers,
    )
    wrong_need_a_sub_parent = client.get(
        f"/admin/need-a-sub/{seeded['other_post_id']}/chat/messages/"
        f"{seeded['sub_message_id']}/content",
        headers=headers,
    )
    assert wrong_type.status_code == 404
    assert wrong_parent.status_code == 404
    assert wrong_need_a_sub_parent.status_code == 404
    assert seeded["community_body"] not in wrong_type.text
    assert seeded["official_body"] not in wrong_parent.text
    assert seeded["sub_body"] not in wrong_need_a_sub_parent.text
    assert _count_sensitive_actions() == 6


def test_empty_chat_identity_pages_short_circuit_before_payload_queries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services import chat_moderation_admin_service

    seeded = _seed_chat_surfaces()

    def fail_payload_query(*args, **kwargs):
        del args, kwargs
        raise AssertionError("an empty identity page must not load message bodies")

    monkeypatch.setattr(
        chat_moderation_admin_service,
        "game_chat_page_has_messages",
        lambda *args, **kwargs: False,
    )
    monkeypatch.setattr(
        chat_moderation_admin_service,
        "need_a_sub_chat_page_has_messages",
        lambda *args, **kwargs: False,
    )
    monkeypatch.setattr(
        chat_moderation_admin_service,
        "list_game_chat_messages",
        fail_payload_query,
    )
    monkeypatch.setattr(
        chat_moderation_admin_service,
        "list_need_a_sub_chat_messages",
        fail_payload_query,
    )

    with session() as db:
        game_page = chat_moderation_admin_service.list_admin_game_chat_messages(
            db,
            viewer_user=seeded["admin"],
            game_id=seeded["community_game_id"],
            view="all",
            offset=20,
            expected_game_type="community",
        )
        sub_page = chat_moderation_admin_service.list_admin_need_a_sub_chat_messages(
            db,
            viewer_user=seeded["admin"],
            post_id=seeded["post_id"],
            view="all",
            offset=20,
        )

    assert game_page.messages == []
    assert sub_page.messages == []
    assert game_page.total_count == 1
    assert sub_page.total_count == 1
    assert _count_sensitive_actions() == 0


def test_audit_failure_prevents_chat_payload_loading_and_disclosure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.database import engine
    from backend.services import chat_moderation_admin_service

    seeded = _seed_chat_surfaces()
    _install_tokens_for_users(monkeypatch, {"admin-token": seeded["admin"]})
    monkeypatch.setattr(
        chat_moderation_admin_service,
        "record_sensitive_admin_read",
        lambda **kwargs: (_ for _ in ()).throw(
            HTTPException(status_code=503, detail="Audit service unavailable.")
        ),
    )
    statements: list[str] = []

    def capture_statement(conn, cursor, statement, parameters, context, executemany):
        del conn, cursor, parameters, context, executemany
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", capture_statement)
    try:
        client = _client()
        list_response = client.get(
            f"/admin/community-games/{seeded['community_game_id']}/chat/messages"
            "?view=all",
            headers=_auth_headers(),
        )
        reveal_responses = (
            client.get(
                f"/admin/community-games/{seeded['community_game_id']}/chat/messages/"
                f"{seeded['community_message_id']}/content",
                headers=_auth_headers(),
            ),
            client.get(
                f"/admin/need-a-sub/{seeded['post_id']}/chat/messages/"
                f"{seeded['sub_message_id']}/content",
                headers=_auth_headers(),
            ),
        )
    finally:
        event.remove(engine, "before_cursor_execute", capture_statement)

    assert list_response.status_code == 503
    assert seeded["community_body"] not in list_response.text
    for response, body in zip(
        reveal_responses,
        (seeded["community_body"], seeded["sub_body"]),
        strict=True,
    ):
        assert response.status_code == 503
        assert body not in response.text
    assert not any("chat_messages.message_body" in statement for statement in statements)
    assert not any(
        "sub_post_chat_messages.message_body" in statement for statement in statements
    )


def test_audit_failure_prevents_review_detail_serialization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services import admin_review_service

    with session() as db:
        game = seed_game(db)
        admin = seed_admin(db, "minimum-review-failure")
        review_case = create_content_case(db, game)
        db.commit()
        review_case_id = review_case.id

        monkeypatch.setattr(
            admin_review_service,
            "record_sensitive_admin_read",
            lambda **kwargs: (_ for _ in ()).throw(
                HTTPException(status_code=503, detail="Audit service unavailable.")
            ),
        )
        monkeypatch.setattr(
            admin_review_service,
            "serialize_review_case_detail",
            lambda *args, **kwargs: (_ for _ in ()).throw(
                AssertionError("sensitive review detail was serialized before audit")
            ),
        )

        with pytest.raises(HTTPException) as exc_info:
            admin_review_service.get_review_case_detail(
                db,
                review_case_id=review_case_id,
                viewer_user=admin,
            )

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Audit service unavailable."


def test_sensitive_services_reject_direct_and_stale_admin_callers() -> None:
    from backend.services.admin_review_service import get_review_case_detail
    from backend.services.chat_moderation_admin_service import (
        list_admin_game_chat_messages,
        list_admin_need_a_sub_chat_messages,
        reveal_admin_game_chat_message_content,
        reveal_admin_need_a_sub_chat_message_content,
    )

    seeded = _seed_chat_surfaces()
    ordinary = _user("minimum-ordinary")
    suspended = _user("minimum-suspended", role="admin", account_status="suspended")
    pending_deletion = _user(
        "minimum-pending-deletion",
        role="admin",
        account_status="pending_deletion",
    )
    deleted = _user("minimum-deleted", role="admin", account_status="deleted")
    _add_users(ordinary, suspended, pending_deletion, deleted)
    with session() as db:
        review_game = seed_game(db)
        review_case = create_content_case(db, review_game)
        db.commit()
        review_case_id = review_case.id

    def calls(db, viewer_user):
        return (
            lambda: list_admin_game_chat_messages(
                db,
                game_id=seeded["community_game_id"],
                viewer_user=viewer_user,
                expected_game_type="community",
            ),
            lambda: reveal_admin_game_chat_message_content(
                db,
                game_id=seeded["community_game_id"],
                message_id=seeded["community_message_id"],
                viewer_user=viewer_user,
                expected_game_type="community",
            ),
            lambda: list_admin_need_a_sub_chat_messages(
                db,
                post_id=seeded["post_id"],
                viewer_user=viewer_user,
            ),
            lambda: reveal_admin_need_a_sub_chat_message_content(
                db,
                post_id=seeded["post_id"],
                message_id=seeded["sub_message_id"],
                viewer_user=viewer_user,
            ),
            lambda: get_review_case_detail(
                db,
                review_case_id=review_case_id,
                viewer_user=viewer_user,
            ),
        )

    with session() as db:
        for denied_user in (ordinary, suspended, pending_deletion, deleted):
            for call in calls(db, denied_user):
                with pytest.raises(HTTPException) as exc_info:
                    call()
                assert exc_info.value.status_code == 403

    with session() as db:
        db.execute(
            update(User)
            .where(User.id == seeded["admin"].id)
            .values(role="player")
        )
        db.commit()

    with session() as db:
        for call in calls(db, seeded["admin"]):
            with pytest.raises(HTTPException) as exc_info:
                call()
            assert exc_info.value.status_code == 403

    assert _count_sensitive_actions() == 0


def test_review_detail_is_audited_and_mutations_return_acknowledgements() -> None:
    from backend.services.admin_review_service import (
        add_review_case_note,
        close_review_case,
        get_review_case_detail,
    )

    with session() as db:
        game = seed_game(db)
        admin = seed_admin(db, "minimum-detail")
        review_case = create_content_case(db, game)
        db.commit()
        original_detail_fields = set(AdminReviewCaseDetailRead.model_fields)
        assert original_detail_fields == set(AdminReviewCaseRead.model_fields) | {
            "signals",
            "findings",
            "events",
            "notes",
        }

        detail = get_review_case_detail(
            db,
            review_case_id=review_case.id,
            viewer_user=admin,
        )
        assert detail.id == review_case.id
        audit = db.scalar(
            select(AdminAction).where(
                AdminAction.action_type == "read_review_case_sensitive_detail",
                AdminAction.target_review_case_id == review_case.id,
            )
        )
        assert audit is not None
        assert audit.reason is None
        assert audit.metadata_ is None

        note = add_review_case_note(
            db,
            review_case_id=review_case.id,
            admin_user=admin,
            payload=AdminReviewCaseNoteCreate(
                body="Private note canary.",
                idempotency_key="minimum-note-key",
            ),
        )
        assert set(note.model_dump()) == {
            "review_case_id",
            "case_version",
            "note_id",
            "audit_action_id",
            "idempotent_replay",
        }
        assert "Private note canary." not in str(note.model_dump())
        replay = add_review_case_note(
            db,
            review_case_id=review_case.id,
            admin_user=admin,
            payload=AdminReviewCaseNoteCreate(
                body="Private note canary.",
                idempotency_key="minimum-note-key",
            ),
        )
        assert replay.note_id == note.note_id
        assert replay.audit_action_id == note.audit_action_id
        assert replay.idempotent_replay is True

        closed = close_review_case(
            db,
            review_case_id=review_case.id,
            admin_user=admin,
            payload=AdminReviewCaseClose(
                outcome="no_action_needed",
                reason="Reviewed current bounded evidence.",
                expected_case_version=note.case_version,
                idempotency_key="minimum-close-key",
            ),
        )
        assert set(closed.model_dump()) == {
            "review_case_id",
            "case_version",
            "case_status",
            "closure_outcome",
            "audit_action_id",
            "idempotent_replay",
        }
        close_replay = close_review_case(
            db,
            review_case_id=review_case.id,
            admin_user=admin,
            payload=AdminReviewCaseClose(
                outcome="no_action_needed",
                reason="Reviewed current bounded evidence.",
                expected_case_version=note.case_version,
                idempotency_key="minimum-close-key",
            ),
        )
        assert close_replay.audit_action_id == closed.audit_action_id
        assert close_replay.idempotent_replay is True


def test_add_note_replay_rejects_note_linked_to_another_case() -> None:
    from backend.services.admin_review_service import (
        add_review_case_note,
        review_case_request_fingerprint,
    )

    body = "Replay linkage must remain case-bound."
    replay_key = "minimum-note-inconsistent"
    with session() as db:
        first_case = create_content_case(db, seed_game(db))
        second_case = create_content_case(db, seed_game(db))
        admin = seed_admin(db, "minimum-note-replay")
        db.commit()

        other_note = add_review_case_note(
            db,
            review_case_id=second_case.id,
            admin_user=admin,
            payload=AdminReviewCaseNoteCreate(
                body=body,
                idempotency_key="minimum-other-note",
            ),
        )
        db.add(
            AdminAction(
                id=uuid.uuid4(),
                admin_user_id=admin.id,
                action_type="add_review_case_note",
                outcome="succeeded",
                correlation_id=uuid.uuid4(),
                target_review_case_id=first_case.id,
                reason="Internal review note added.",
                metadata_={
                    "source": "review_case",
                    "note_id": str(other_note.note_id),
                    "request_fingerprint": review_case_request_fingerprint(
                        {"body": body}
                    ),
                    "note_length": len(body),
                },
                idempotency_key=replay_key,
            )
        )
        db.commit()

        with pytest.raises(HTTPException) as exc_info:
            add_review_case_note(
                db,
                review_case_id=first_case.id,
                admin_user=admin,
                payload=AdminReviewCaseNoteCreate(
                    body=body,
                    idempotency_key=replay_key,
                ),
            )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "review_case_transition_conflict"


def test_close_replay_rejects_inconsistent_open_case_state() -> None:
    from backend.services.admin_review_service import (
        close_review_case,
        review_case_request_fingerprint,
    )

    reason = "Replay state must remain closed."
    replay_key = "minimum-close-inconsistent"
    with session() as db:
        review_case = create_content_case(db, seed_game(db))
        admin = seed_admin(db, "minimum-close-replay")
        db.commit()
        expected_case_version = review_case.case_version
        outcome = "no_action_needed"
        db.add(
            AdminAction(
                id=uuid.uuid4(),
                admin_user_id=admin.id,
                action_type="close_review_case",
                outcome="succeeded",
                correlation_id=uuid.uuid4(),
                target_review_case_id=review_case.id,
                reason=reason,
                metadata_={
                    "source": "review_case_closure",
                    "closure_outcome": outcome,
                    "request_fingerprint": review_case_request_fingerprint(
                        {
                            "expected_case_version": expected_case_version,
                            "outcome": outcome,
                            "reason": reason,
                        }
                    ),
                },
                idempotency_key=replay_key,
            )
        )
        db.commit()

        with pytest.raises(HTTPException) as exc_info:
            close_review_case(
                db,
                review_case_id=review_case.id,
                admin_user=admin,
                payload=AdminReviewCaseClose(
                    outcome=outcome,
                    reason=reason,
                    expected_case_version=expected_case_version,
                    idempotency_key=replay_key,
                ),
            )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "review_case_transition_conflict"


def test_sensitive_read_policy_and_audit_minimization_are_exact() -> None:
    from backend.schemas.admin_action_schema import (
        AdminActionDetailRead,
        AdminActionLogItemRead,
        AdminActionLogListRead,
        AdminActionTargetSummaryRead,
    )
    from backend.schemas.admin_chat_moderation_schema import (
        AdminChatModerationActionResultRead,
    )
    from backend.schemas.admin_community_schema import (
        AdminCommunityGameAuditActionSummaryRead,
    )
    from backend.schemas.admin_money_context_schema import (
        AdminMoneyAuditActionSummaryRead,
    )
    from backend.schemas.admin_need_a_sub_schema import AdminNeedASubAuditActionRead
    from backend.schemas.admin_notification_schema import (
        AdminNotificationLookupDetailRead,
    )
    from backend.schemas.admin_user_schema import AdminUserAuditActionSummaryRead
    from backend.services.admin_action_policy import ADMIN_ACTION_POLICIES
    from backend.services.admin_action_service import build_action_metadata

    expected = {
        "read_game_chat_moderation",
        "reveal_game_chat_message_content",
        "read_need_sub_chat_moderation",
        "reveal_need_sub_chat_message_content",
        "read_review_case_sensitive_detail",
    }
    for action_type in expected:
        policy = ADMIN_ACTION_POLICIES[action_type]
        assert policy.category == "sensitive_read"
        assert policy.requires_reason is False
        assert policy.metadata_builder_key == "none"
        assert policy.allows_audit_note is False
        assert build_action_metadata(policy, None) is None
        with pytest.raises(HTTPException):
            build_action_metadata(policy, {})

    assert set(AdminActionLogItemRead.model_fields) == {
        "id",
        "action_label",
        "admin_label",
        "target_label",
        "reason_preview",
        "created_at",
    }
    assert set(AdminActionLogListRead.model_fields) == {
        "actions",
        "action_type_options",
        "limit",
        "next_cursor",
        "has_more",
    }
    assert set(AdminActionDetailRead.model_fields) == {
        "id",
        "action_type",
        "action_label",
        "admin_label",
        "admin_email",
        "created_at",
        "reason",
        "primary_target",
    }
    assert set(AdminActionTargetSummaryRead.model_fields) == {
        "target_type_label",
        "label",
        "destination_path",
    }
    assert set(AdminChatModerationActionResultRead.model_fields) == {
        "message_id",
        "audit_action_id",
        "idempotent_replay",
    }
    assert set(AdminCommunityGameAuditActionSummaryRead.model_fields) == {
        "id",
        "action_label",
        "reason_preview",
        "created_at",
    }
    assert set(AdminNeedASubAuditActionRead.model_fields) == {
        "id",
        "action_label",
        "reason_preview",
        "created_at",
    }
    for schema in (AdminMoneyAuditActionSummaryRead, AdminUserAuditActionSummaryRead):
        assert set(schema.model_fields) == {
            "id",
            "action_label",
            "admin_label",
            "reason_preview",
            "created_at",
        }
    assert "audit_actions" not in AdminNotificationLookupDetailRead.model_fields
    assert "audit_action_count" not in AdminNotificationLookupDetailRead.model_fields


def test_official_game_activity_cursor_is_bound_to_game_filter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seeded = _seed_chat_surfaces()
    with session() as db:
        db.add_all(
            [
                AdminAction(
                    id=uuid.uuid4(),
                    admin_user_id=seeded["admin"].id,
                    action_type="update_game",
                    outcome="succeeded",
                    correlation_id=uuid.uuid4(),
                    target_game_id=seeded["official_game_id"],
                    reason=f"Activity row {index}.",
                )
                for index in range(51)
            ]
        )
        db.commit()

    _install_tokens_for_users(monkeypatch, {"admin-token": seeded["admin"]})
    client = _client()
    headers = _auth_headers()
    first_page = client.get(
        "/admin/actions/log",
        params={"target_game_id": str(seeded["official_game_id"])},
        headers=headers,
    )
    assert first_page.status_code == 200, first_page.text
    first_body = first_page.json()
    assert set(first_body) == {
        "actions",
        "action_type_options",
        "limit",
        "next_cursor",
        "has_more",
    }
    assert len(first_body["actions"]) == 50
    assert first_body["action_type_options"] == []
    assert first_body["has_more"] is True
    assert first_body["next_cursor"]

    second_page = client.get(
        "/admin/actions/log",
        params={
            "target_game_id": str(seeded["official_game_id"]),
            "cursor": first_body["next_cursor"],
        },
        headers=headers,
    )
    assert second_page.status_code == 200, second_page.text
    assert len(second_page.json()["actions"]) == 1
    assert second_page.json()["next_cursor"] is None

    for params in (
        {"cursor": first_body["next_cursor"]},
        {
            "target_game_id": str(seeded["community_game_id"]),
            "cursor": first_body["next_cursor"],
        },
    ):
        mismatched = client.get("/admin/actions/log", params=params, headers=headers)
        assert mismatched.status_code == 400
