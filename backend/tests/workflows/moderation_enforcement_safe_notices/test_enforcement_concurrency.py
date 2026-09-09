from __future__ import annotations

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select

from backend.models import (
    AdminAction,
    AdminReviewCase,
    AdminReviewCaseEvent,
    AdminTargetNotice,
    ChatMessage,
    Game,
    Notification,
    SubPost,
    User,
)
from backend.schemas.admin_chat_moderation_schema import (
    AdminChatModerationActionCreate,
)
from backend.schemas.admin_community_schema import (
    AdminCommunityGameEnforcementActionCreate,
)
from backend.schemas.admin_need_a_sub_schema import (
    AdminNeedASubEnforcementActionCreate,
)
from backend.schemas.admin_user_schema import (
    AdminUserRestoreHostingCreate,
    AdminUserRestrictHostingCreate,
)
from backend.services import community_game_enforcement_service
from backend.services.admin_user_hosting_service import (
    preview_admin_user_hosting_restriction,
    restore_admin_user_hosting,
    restrict_admin_user_hosting,
)
from backend.services.chat_moderation_admin_service import (
    remove_game_chat_message,
    restore_game_chat_message,
)
from backend.services.community_game_enforcement_service import (
    hide_community_game,
    pause_community_game_joining,
    restore_community_game,
    resume_community_game_joining,
)
from backend.services.game_service import delete_game_workflow
from backend.services.need_a_sub_enforcement_service import (
    hide_need_a_sub_post,
    restore_need_a_sub_post,
)
from backend.tests.workflows.admin_route_list_high_risk_function_authorization.test_admin_game_roster_moderation_contract import (
    _persist_community_game_fixture,
    _persist_game_chat_message_fixture,
    _persist_game_fixture,
    _persist_sub_post_fixture,
)
from backend.tests.workflows.admin_route_list_high_risk_function_authorization.test_admin_matrix_scope_and_dependencies_contract import (
    _add_users,
    _session,
    _user,
)
from backend.tests.workflows.moderation_review_case_lifecycle.conftest import (
    create_content_case,
    run_with_target_lock_barrier,
)

pytestmark = pytest.mark.suite_type("ordinary")


def _count(db, model, *conditions) -> int:
    return db.scalar(select(func.count(model.id)).where(*conditions)) or 0


def _assert_action_side_effects(
    db,
    *,
    action_conditions: tuple,
    expected_action_types: set[str],
    expected_notice_types: set[str],
    expected_review_case_id: uuid.UUID | None = None,
) -> None:
    actions = list(db.scalars(select(AdminAction).where(*action_conditions)).all())
    action_ids = {action.id for action in actions}
    notices = list(
        db.scalars(
            select(AdminTargetNotice).where(
                AdminTargetNotice.admin_action_id.in_(action_ids)
            )
        ).all()
    )
    assert {action.action_type for action in actions} == expected_action_types
    assert {notice.notice_type for notice in notices} == expected_notice_types
    assert len(actions) == len(expected_action_types)
    assert len(notices) == len(expected_notice_types)
    if expected_review_case_id is None:
        assert all(action.target_review_case_id is None for action in actions)
    else:
        assert {action.target_review_case_id for action in actions} == {
            expected_review_case_id
        }
        review_case = db.get(AdminReviewCase, expected_review_case_id)
        assert review_case.case_status == "open"
        assert review_case.case_version == 3
        events = list(
            db.scalars(
                select(AdminReviewCaseEvent)
                .where(AdminReviewCaseEvent.review_case_id == expected_review_case_id)
                .order_by(AdminReviewCaseEvent.case_version.asc())
            ).all()
        )
        assert [event.event_type for event in events] == [
            "case_created",
            "finding_attached",
            "enforcement_action_linked",
        ]
        assert events[-1].admin_action_id in action_ids
    assert all(notice.user_safe_reason is None for notice in notices)
    assert _count(
        db,
        Notification,
        Notification.aggregation_key.in_(
            [f"admin_target_notice:{notice.id}" for notice in notices]
        ),
    ) == len(notices)


def test_same_community_hide_race_commits_once_and_replays_once() -> None:
    admin = _user("05c-race-same-admin", role="admin")
    host = _user("05c-race-same-host")
    _add_users(admin, host)
    game_id, _ = _persist_community_game_fixture(
        "05c-race-same",
        admin=admin,
        host=host,
    )
    with _session() as db:
        game = db.get(Game, game_id)
        game.description = "Text me at 312-555-1212"
        db.commit()
        review_case = create_content_case(db, game)
        assert review_case is not None
        review_case_id = review_case.id
    payload = AdminCommunityGameEnforcementActionCreate(
        reason="Concurrent exact hide",
        idempotency_key="05c-race-same-hide",
    )

    def hide():
        with _session() as db:
            return hide_community_game(
                db,
                game_id=game_id,
                admin_user=db.get(User, admin.id),
                payload=payload,
            )

    first, second = run_with_target_lock_barrier(hide, hide, table_name="games")
    assert first.audit_action_id == second.audit_action_id
    assert sorted((first.idempotent_replay, second.idempotent_replay)) == [False, True]
    with _session() as db:
        assert db.get(Game, game_id).public_visibility_status == "hidden"
        _assert_action_side_effects(
            db,
            action_conditions=(AdminAction.target_game_id == game_id,),
            expected_action_types={"hide_community_game"},
            expected_notice_types={"community_game_hidden"},
            expected_review_case_id=review_case_id,
        )


def test_community_hide_rejects_delete_committed_after_initial_resolution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = _user("05c-race-delete-first-admin", role="admin")
    host = _user("05c-race-delete-first-host")
    _add_users(admin, host)
    game_id, _ = _persist_community_game_fixture(
        "05c-race-delete-first",
        admin=admin,
        host=host,
    )
    resolved = threading.Event()
    deleted = threading.Event()
    original_resolver = community_game_enforcement_service.get_community_game_or_404

    def pause_after_initial_resolution(db, resolved_game_id):
        game = original_resolver(db, resolved_game_id)
        resolved.set()
        assert deleted.wait(timeout=10)
        return game

    monkeypatch.setattr(
        community_game_enforcement_service,
        "get_community_game_or_404",
        pause_after_initial_resolution,
    )

    def hide():
        with _session() as db:
            try:
                return hide_community_game(
                    db,
                    game_id=game_id,
                    admin_user=db.get(User, admin.id),
                    payload=AdminCommunityGameEnforcementActionCreate(
                        reason="Delete-first private reason",
                        idempotency_key="05c-race-delete-first-hide",
                    ),
                )
            except HTTPException as exc:
                return exc

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(hide)
        assert resolved.wait(timeout=5)
        try:
            with _session() as db:
                delete_game_workflow(
                    db,
                    game_id,
                    db.get(User, admin.id),
                )
        finally:
            deleted.set()
        rejected = future.result(timeout=15)

    assert isinstance(rejected, HTTPException)
    assert rejected.status_code == 409
    assert rejected.detail == "Community game is no longer available for this action."
    with _session() as db:
        game = db.get(Game, game_id)
        assert game.deleted_at is not None
        assert game.public_visibility_status == "visible"
        assert _count(db, AdminAction, AdminAction.target_game_id == game_id) == 0
        assert (
            _count(db, AdminTargetNotice, AdminTargetNotice.target_game_id == game_id)
            == 0
        )
        assert _count(db, Notification, Notification.user_id == host.id) == 0
        assert (
            _count(db, AdminReviewCase, AdminReviewCase.target_game_id == game_id) == 0
        )


def test_hosting_restriction_restoration_race_serializes_history() -> None:
    admin = _user("05c-race-hosting-admin", role="admin")
    target = _user("05c-race-hosting-target")
    _add_users(admin, target)
    with _session() as db:
        preview = preview_admin_user_hosting_restriction(db, user_id=target.id)

    def restrict():
        with _session() as db:
            return restrict_admin_user_hosting(
                db,
                admin_user=db.get(User, admin.id),
                user_id=target.id,
                payload=AdminUserRestrictHostingCreate(
                    preview_token=preview.preview_token,
                    reason="Concurrent hosting restriction",
                    idempotency_key="05c-race-hosting-restrict",
                ),
            )

    def restore():
        with _session() as db:
            return restore_admin_user_hosting(
                db,
                admin_user=db.get(User, admin.id),
                user_id=target.id,
                payload=AdminUserRestoreHostingCreate(
                    reason="Concurrent hosting restoration",
                    idempotency_key="05c-race-hosting-restore",
                ),
            )

    first, second = run_with_target_lock_barrier(
        restrict,
        restore,
        table_name="users",
    )
    assert first.hosting_status == "restricted"
    assert second.hosting_status == "eligible"
    with _session() as db:
        assert db.get(User, target.id).hosting_status == "eligible"
        actions = list(
            db.scalars(
                select(AdminAction).where(AdminAction.target_user_id == target.id)
            ).all()
        )
        assert {action.action_type for action in actions} == {
            "restrict_hosting",
            "restore_hosting",
        }
        assert len(actions) == 2
        assert all(action.target_review_case_id is None for action in actions)
        notification_ids = {action.target_notification_id for action in actions}
        assert None not in notification_ids
        assert _count(db, Notification, Notification.id.in_(notification_ids)) == 2
        assert _count(db, AdminTargetNotice) == 0


def test_community_hide_restore_race_serializes_notices_and_final_state() -> None:
    admin = _user("05c-race-visibility-admin", role="admin")
    host = _user("05c-race-visibility-host")
    _add_users(admin, host)
    game_id, _ = _persist_community_game_fixture(
        "05c-race-visibility",
        admin=admin,
        host=host,
    )

    def hide():
        with _session() as db:
            return hide_community_game(
                db,
                game_id=game_id,
                admin_user=db.get(User, admin.id),
                payload=AdminCommunityGameEnforcementActionCreate(
                    reason="Concurrent visibility hide",
                    idempotency_key="05c-race-visibility-hide",
                ),
            )

    def restore():
        with _session() as db:
            return restore_community_game(
                db,
                game_id=game_id,
                admin_user=db.get(User, admin.id),
                payload=AdminCommunityGameEnforcementActionCreate(
                    reason="Concurrent visibility restore",
                    idempotency_key="05c-race-visibility-restore",
                ),
            )

    run_with_target_lock_barrier(hide, restore, table_name="games")
    with _session() as db:
        assert db.get(Game, game_id).public_visibility_status == "visible"
        _assert_action_side_effects(
            db,
            action_conditions=(AdminAction.target_game_id == game_id,),
            expected_action_types={"hide_community_game", "restore_community_game"},
            expected_notice_types={
                "community_game_hidden",
                "community_game_restored",
            },
        )


def test_joining_pause_resume_race_serializes_notices_and_final_state() -> None:
    admin = _user("05c-race-joining-admin", role="admin")
    host = _user("05c-race-joining-host")
    _add_users(admin, host)
    game_id, _ = _persist_community_game_fixture(
        "05c-race-joining",
        admin=admin,
        host=host,
    )

    def pause():
        with _session() as db:
            return pause_community_game_joining(
                db,
                game_id=game_id,
                admin_user=db.get(User, admin.id),
                payload=AdminCommunityGameEnforcementActionCreate(
                    reason="Concurrent joining pause",
                    idempotency_key="05c-race-joining-pause",
                ),
            )

    def resume():
        with _session() as db:
            return resume_community_game_joining(
                db,
                game_id=game_id,
                admin_user=db.get(User, admin.id),
                payload=AdminCommunityGameEnforcementActionCreate(
                    reason="Concurrent joining resume",
                    idempotency_key="05c-race-joining-resume",
                ),
            )

    run_with_target_lock_barrier(pause, resume, table_name="games")
    with _session() as db:
        assert db.get(Game, game_id).join_enforcement_status == "open"
        _assert_action_side_effects(
            db,
            action_conditions=(AdminAction.target_game_id == game_id,),
            expected_action_types={
                "pause_community_game_joining",
                "resume_community_game_joining",
            },
            expected_notice_types={
                "community_game_joining_paused",
                "community_game_joining_resumed",
            },
        )


def test_need_sub_hide_restore_race_serializes_notices_and_final_state() -> None:
    admin = _user("05c-race-sub-admin", role="admin")
    owner = _user("05c-race-sub-owner")
    _add_users(admin, owner)
    post_id = _persist_sub_post_fixture("05c-race-sub", owner=owner)

    def hide():
        with _session() as db:
            return hide_need_a_sub_post(
                db,
                post_id=post_id,
                admin_user=db.get(User, admin.id),
                payload=AdminNeedASubEnforcementActionCreate(
                    reason="Concurrent post hide",
                    idempotency_key="05c-race-sub-hide",
                ),
            )

    def restore():
        with _session() as db:
            return restore_need_a_sub_post(
                db,
                post_id=post_id,
                admin_user=db.get(User, admin.id),
                payload=AdminNeedASubEnforcementActionCreate(
                    reason="Concurrent post restore",
                    idempotency_key="05c-race-sub-restore",
                ),
            )

    run_with_target_lock_barrier(hide, restore, table_name="sub_posts")
    with _session() as db:
        assert db.get(SubPost, post_id).public_visibility_status == "visible"
        _assert_action_side_effects(
            db,
            action_conditions=(AdminAction.target_sub_post_id == post_id,),
            expected_action_types={"hide_need_sub_post", "restore_need_sub_post"},
            expected_notice_types={
                "need_sub_post_hidden",
                "need_sub_post_restored",
            },
        )


def test_chat_remove_restore_race_serializes_notices_and_final_state() -> None:
    admin = _user("05c-race-chat-admin", role="admin")
    creator = _user("05c-race-chat-creator")
    sender = _user("05c-race-chat-sender")
    _add_users(admin, creator, sender)
    game_id, _ = _persist_game_fixture(
        "05c-race-chat",
        admin=admin,
        creator=creator,
    )
    message_id = _persist_game_chat_message_fixture(
        game_id=game_id,
        sender_user_id=sender.id,
    )

    def remove():
        with _session() as db:
            return remove_game_chat_message(
                db,
                game_id=game_id,
                message_id=message_id,
                admin_user=db.get(User, admin.id),
                payload=AdminChatModerationActionCreate(
                    reason="Concurrent chat removal",
                    idempotency_key="05c-race-chat-remove",
                ),
                expected_game_type="official",
            )

    def restore():
        with _session() as db:
            return restore_game_chat_message(
                db,
                game_id=game_id,
                message_id=message_id,
                admin_user=db.get(User, admin.id),
                payload=AdminChatModerationActionCreate(
                    reason="Concurrent chat restoration",
                    idempotency_key="05c-race-chat-restore",
                ),
                expected_game_type="official",
            )

    run_with_target_lock_barrier(remove, restore, table_name="games")
    with _session() as db:
        message = db.get(ChatMessage, message_id)
        assert message.visibility_status == "visible"
        assert message.removed_source == "admin"
        _assert_action_side_effects(
            db,
            action_conditions=(AdminAction.target_message_id == message_id,),
            expected_action_types={"remove_chat_message", "restore_chat_message"},
            expected_notice_types={
                "game_chat_message_removed",
                "game_chat_message_restored",
            },
        )
