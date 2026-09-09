from __future__ import annotations

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from backend.models import (
    AdminAction,
    AdminTargetNotice,
    ChatMessage,
    Game,
    GameParticipant,
    Notification,
    SubPost,
    SubPostChatMessage,
    SubPostRequest,
    SubPostStatusHistory,
    User,
)
from backend.schemas.admin_chat_moderation_schema import (
    AdminChatModerationActionCreate,
)
from backend.schemas.admin_community_schema import (
    AdminCommunityGameEnforcementActionCreate,
)
from backend.schemas.admin_user_schema import (
    AdminUserRestoreHostingCreate,
    AdminUserRestrictHostingCreate,
    AdminUserSuspendCreate,
    AdminUserUnsuspendCreate,
)
from backend.services import (
    admin_target_notice_service,
    admin_user_account_service,
    admin_user_hosting_service,
    chat_moderation_admin_service,
    community_game_enforcement_service,
    game_cancellation_service,
    need_a_sub_post_service,
)
from backend.services.admin_user_account_service import (
    preview_admin_user_suspension,
    suspend_admin_user,
    unsuspend_admin_user,
)
from backend.services.admin_user_hosting_service import (
    preview_admin_user_hosting_restriction,
    restore_admin_user_hosting,
    restrict_admin_user_hosting,
)
from backend.services.chat_moderation_admin_service import (
    remove_game_chat_message,
    remove_need_a_sub_chat_message,
    restore_game_chat_message,
    restore_need_a_sub_chat_message,
)
from backend.services.community_game_enforcement_service import (
    admin_cancel_community_game,
    hide_community_game,
)
from backend.services.game_service import delete_game_workflow
from backend.services.need_a_sub_post_service import remove_sub_post
from backend.tests.workflows.admin_route_list_high_risk_function_authorization.test_admin_game_roster_moderation_contract import (
    _persist_community_game_fixture,
    _persist_game_chat_message_fixture,
    _persist_sub_post_chat_message_fixture,
    _persist_sub_post_fixture,
    _persist_sub_post_request_fixture,
)
from backend.tests.workflows.admin_route_list_high_risk_function_authorization.test_admin_matrix_scope_and_dependencies_contract import (
    _add_users,
    _session,
    _user,
)

pytestmark = pytest.mark.suite_type("ordinary")


def _count(db, model, *conditions) -> int:
    return db.scalar(select(func.count(model.id)).where(*conditions)) or 0


def test_target_notice_notification_failure_rolls_back_community_game_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = _user("05c-notice-fail-admin", role="admin")
    host = _user("05c-notice-fail-host")
    _add_users(admin, host)
    game_id, _ = _persist_community_game_fixture(
        "05c-notice-fail",
        admin=admin,
        host=host,
    )

    def fail_notification(*args, **kwargs):
        del args, kwargs
        raise RuntimeError("injected notice notification failure")

    monkeypatch.setattr(
        admin_target_notice_service,
        "create_admin_target_notice_notification",
        fail_notification,
    )
    with (
        _session() as db,
        pytest.raises(RuntimeError, match="injected notice notification failure"),
    ):
        hide_community_game(
            db,
            game_id=game_id,
            admin_user=db.get(User, admin.id),
            payload=AdminCommunityGameEnforcementActionCreate(
                reason="Private rollback reason",
                idempotency_key="05c-notice-failure",
            ),
        )

    with _session() as db:
        game = db.get(Game, game_id)
        assert game.public_visibility_status == "visible"
        assert _count(db, AdminAction, AdminAction.target_game_id == game_id) == 0
        assert (
            _count(db, AdminTargetNotice, AdminTargetNotice.target_game_id == game_id)
            == 0
        )
        assert _count(db, Notification, Notification.user_id == host.id) == 0


def test_direct_notification_staging_failure_rolls_back_account_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = _user("05c-account-fail-admin", role="admin")
    target = _user("05c-account-fail-target")
    _add_users(admin, target)
    with _session() as db:
        preview = preview_admin_user_suspension(db, user_id=target.id)

    def fail_after_notification(*args, **kwargs):
        del args, kwargs
        raise RuntimeError("injected action persistence failure")

    monkeypatch.setattr(
        admin_user_account_service,
        "record_admin_action",
        fail_after_notification,
    )
    with (
        _session() as db,
        pytest.raises(RuntimeError, match="injected action persistence failure"),
    ):
        suspend_admin_user(
            db,
            admin_user=db.get(User, admin.id),
            user_id=target.id,
            payload=AdminUserSuspendCreate(
                preview_token=preview.preview_token,
                reason="Private account rollback reason",
                idempotency_key="05c-account-failure",
            ),
        )

    with _session() as db:
        persisted = db.get(User, target.id)
        assert persisted.account_status == "active"
        assert _count(db, AdminAction, AdminAction.target_user_id == target.id) == 0
        assert _count(db, Notification, Notification.user_id == target.id) == 0


def test_need_sub_requester_notice_failure_rolls_back_post_and_child_closure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = _user("05c-sub-fail-admin", role="admin")
    owner = _user("05c-sub-fail-owner")
    requester = _user("05c-sub-fail-requester")
    _add_users(admin, owner, requester)
    post_id = _persist_sub_post_fixture("05c-sub-fail", owner=owner)
    request = _persist_sub_post_request_fixture(
        post_id=post_id,
        requester_user_id=requester.id,
    )
    original_create = need_a_sub_post_service.create_admin_target_notice
    call_count = 0

    def fail_requester_notice(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise RuntimeError("injected requester notice failure")
        return original_create(*args, **kwargs)

    monkeypatch.setattr(
        need_a_sub_post_service,
        "create_admin_target_notice",
        fail_requester_notice,
    )
    with _session() as db:
        before_history = _count(
            db,
            SubPostStatusHistory,
            SubPostStatusHistory.sub_post_id == post_id,
        )
        with pytest.raises(RuntimeError, match="injected requester notice failure"):
            remove_sub_post(
                db,
                db.get(User, admin.id),
                post_id,
                "Private removal rollback reason",
                "05c-sub-remove-failure",
            )

    with _session() as db:
        post = db.get(SubPost, post_id)
        sub_request = db.get(SubPostRequest, request["request_id"])
        assert post.post_status == "active"
        assert post.removed_at is None
        assert sub_request.request_status == "pending"
        assert (
            _count(
                db,
                SubPostStatusHistory,
                SubPostStatusHistory.sub_post_id == post_id,
            )
            == before_history
        )
        assert _count(db, AdminAction, AdminAction.target_sub_post_id == post_id) == 0
        assert (
            _count(
                db,
                AdminTargetNotice,
                AdminTargetNotice.target_sub_post_id == post_id,
            )
            == 0
        )
        assert _count(db, Notification, Notification.user_id == owner.id) == 0
        assert _count(db, Notification, Notification.user_id == requester.id) == 0


def test_cancellation_host_notice_failure_rolls_back_participant_and_notifications(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = _user("05c-cancel-fail-admin", role="admin")
    host = _user("05c-cancel-fail-host")
    participant_user = _user("05c-cancel-fail-player")
    _add_users(admin, host, participant_user)
    game_id, _ = _persist_community_game_fixture(
        "05c-cancel-fail",
        admin=admin,
        host=host,
    )
    with _session() as db:
        now = datetime.now(timezone.utc)
        participant = GameParticipant(
            id=uuid.uuid4(),
            game_id=game_id,
            participant_type="registered_user",
            user_id=participant_user.id,
            display_name_snapshot="Cancellation rollback player",
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
        db.add(participant)
        db.commit()
        participant_id = participant.id

    def fail_host_notice(*args, **kwargs):
        del args, kwargs
        raise RuntimeError("injected cancellation host notice failure")

    monkeypatch.setattr(
        community_game_enforcement_service,
        "create_host_notice",
        fail_host_notice,
    )
    with (
        _session() as db,
        pytest.raises(RuntimeError, match="injected cancellation host notice"),
    ):
        admin_cancel_community_game(
            db,
            game_id=game_id,
            admin_user=db.get(User, admin.id),
            payload=AdminCommunityGameEnforcementActionCreate(
                reason="Private cancellation rollback reason",
                idempotency_key="05c-cancel-failure",
            ),
        )

    with _session() as db:
        game = db.get(Game, game_id)
        participant = db.get(GameParticipant, participant_id)
        assert game.game_status == "active"
        assert participant.participant_status == "confirmed"
        assert participant.cancellation_type == "none"
        assert _count(db, AdminAction, AdminAction.target_game_id == game_id) == 0
        assert (
            _count(db, AdminTargetNotice, AdminTargetNotice.target_game_id == game_id)
            == 0
        )
        assert (
            _count(
                db,
                Notification,
                Notification.user_id.in_((host.id, participant_user.id)),
            )
            == 0
        )


def test_cancellation_domain_integrity_failure_is_sanitized_and_rolled_back(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    private_canary = "PRIVATE-CANCELLATION-INTEGRITY-REASON-05C"
    admin = _user("05c-cancel-integrity-admin", role="admin")
    host = _user("05c-cancel-integrity-host")
    participant_user = _user("05c-cancel-integrity-player")
    _add_users(admin, host, participant_user)
    game_id, _ = _persist_community_game_fixture(
        "05c-cancel-integrity",
        admin=admin,
        host=host,
    )
    with _session() as db:
        now = datetime.now(timezone.utc)
        participant = GameParticipant(
            id=uuid.uuid4(),
            game_id=game_id,
            participant_type="registered_user",
            user_id=participant_user.id,
            display_name_snapshot="Cancellation integrity player",
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
        db.add(participant)
        db.commit()
        participant_id = participant.id

    class OriginalFailure(Exception):
        class Diag:
            constraint_name = "ck_unrelated_private_cancellation_row"

        diag = Diag()

    def fail_review_case_closure(*args, **kwargs):
        del args, kwargs
        raise IntegrityError(
            "INSERT",
            {},
            OriginalFailure(f"failing row contains {private_canary}"),
        )

    monkeypatch.setattr(
        game_cancellation_service,
        "close_open_content_moderation_case_for_game_lifecycle",
        fail_review_case_closure,
    )
    with _session() as db, pytest.raises(HTTPException) as rejected:
        admin_cancel_community_game(
            db,
            game_id=game_id,
            admin_user=db.get(User, admin.id),
            payload=AdminCommunityGameEnforcementActionCreate(
                reason=private_canary,
                idempotency_key="05c-cancel-integrity",
            ),
        )

    assert rejected.value.status_code == 409
    assert rejected.value.detail == "Community game could not be cancelled."
    assert private_canary not in str(rejected.value.detail)
    assert private_canary not in caplog.text

    with _session() as db:
        game = db.get(Game, game_id)
        participant = db.get(GameParticipant, participant_id)
        assert game.game_status == "active"
        assert participant.participant_status == "confirmed"
        assert participant.cancellation_type == "none"
        assert _count(db, AdminAction, AdminAction.target_game_id == game_id) == 0
        assert (
            _count(db, AdminTargetNotice, AdminTargetNotice.target_game_id == game_id)
            == 0
        )
        assert (
            _count(
                db,
                Notification,
                Notification.user_id.in_((host.id, participant_user.id)),
            )
            == 0
        )


def test_unrelated_integrity_failure_is_not_accepted_as_idempotent_replay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = _user("05c-integrity-admin", role="admin")
    host = _user("05c-integrity-host")
    _add_users(admin, host)
    game_id, _ = _persist_community_game_fixture(
        "05c-integrity",
        admin=admin,
        host=host,
    )

    class OriginalFailure(Exception):
        class Diag:
            constraint_name = "ck_admin_target_notices_notice_type"

        diag = Diag()

    def fail_with_unrelated_constraint(*args, **kwargs):
        del args, kwargs
        raise IntegrityError("INSERT", {}, OriginalFailure("unrelated"))

    monkeypatch.setattr(
        community_game_enforcement_service,
        "create_host_notice",
        fail_with_unrelated_constraint,
    )
    with _session() as db:
        with pytest.raises(HTTPException) as rejected:
            hide_community_game(
                db,
                game_id=game_id,
                admin_user=db.get(User, admin.id),
                payload=AdminCommunityGameEnforcementActionCreate(
                    reason="Private unrelated-integrity reason",
                    idempotency_key="05c-unrelated-integrity",
                ),
            )
        assert rejected.value.status_code == 409
        assert rejected.value.detail == "Community game action could not be applied."

    with _session() as db:
        assert db.get(Game, game_id).public_visibility_status == "visible"
        assert _count(db, AdminAction, AdminAction.target_game_id == game_id) == 0
        assert (
            _count(db, AdminTargetNotice, AdminTargetNotice.target_game_id == game_id)
            == 0
        )


def test_account_and_hosting_integrity_errors_are_sanitized(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    private_canary = "PRIVATE-ADMIN-REASON-IN-POSTGRES-ERROR-05C"
    admin = _user("05c-safe-error-admin", role="admin")
    suspend_target = _user("05c-safe-error-suspend")
    unsuspend_target = _user("05c-safe-error-unsuspend", account_status="suspended")
    restrict_target = _user("05c-safe-error-restrict")
    restore_target = _user(
        "05c-safe-error-restore",
        hosting_status="restricted",
    )
    _add_users(
        admin,
        suspend_target,
        unsuspend_target,
        restrict_target,
        restore_target,
    )
    with _session() as db:
        suspension_preview = preview_admin_user_suspension(
            db,
            user_id=suspend_target.id,
        )
        hosting_preview = preview_admin_user_hosting_restriction(
            db,
            user_id=restrict_target.id,
        )

    class OriginalFailure(Exception):
        class Diag:
            constraint_name = "ck_unrelated_private_row"

        diag = Diag()

    def fail_with_private_database_detail(*args, **kwargs):
        del args, kwargs
        raise IntegrityError(
            "INSERT",
            {},
            OriginalFailure(f"failing row contains {private_canary}"),
        )

    monkeypatch.setattr(
        admin_user_account_service,
        "record_admin_action",
        fail_with_private_database_detail,
    )
    monkeypatch.setattr(
        admin_user_hosting_service,
        "record_admin_action",
        fail_with_private_database_detail,
    )

    cases = [
        (
            suspend_admin_user,
            suspend_target.id,
            AdminUserSuspendCreate(
                preview_token=suspension_preview.preview_token,
                reason=private_canary,
                idempotency_key="05c-safe-error-suspend",
            ),
            "Account enforcement action could not be saved.",
        ),
        (
            unsuspend_admin_user,
            unsuspend_target.id,
            AdminUserUnsuspendCreate(
                reason=private_canary,
                idempotency_key="05c-safe-error-unsuspend",
            ),
            "Account enforcement action could not be saved.",
        ),
        (
            restrict_admin_user_hosting,
            restrict_target.id,
            AdminUserRestrictHostingCreate(
                preview_token=hosting_preview.preview_token,
                reason=private_canary,
                idempotency_key="05c-safe-error-restrict",
            ),
            "Hosting enforcement action could not be saved.",
        ),
        (
            restore_admin_user_hosting,
            restore_target.id,
            AdminUserRestoreHostingCreate(
                reason=private_canary,
                idempotency_key="05c-safe-error-restore",
            ),
            "Hosting enforcement action could not be saved.",
        ),
    ]

    for service, target_id, payload, expected_detail in cases:
        with _session() as db, pytest.raises(HTTPException) as rejected:
            service(
                db,
                admin_user=db.get(User, admin.id),
                user_id=target_id,
                payload=payload,
            )
        assert rejected.value.status_code == 409
        assert rejected.value.detail == expected_detail
        assert private_canary not in str(rejected.value.detail)

    assert private_canary not in caplog.text

    with _session() as db:
        assert db.get(User, suspend_target.id).account_status == "active"
        assert db.get(User, unsuspend_target.id).account_status == "suspended"
        assert db.get(User, restrict_target.id).hosting_status == "eligible"
        assert db.get(User, restore_target.id).hosting_status == "restricted"
        target_ids = {
            suspend_target.id,
            unsuspend_target.id,
            restrict_target.id,
            restore_target.id,
        }
        assert _count(db, AdminAction, AdminAction.target_user_id.in_(target_ids)) == 0
        assert _count(db, Notification, Notification.user_id.in_(target_ids)) == 0


@pytest.mark.parametrize("game_status", ["completed", "expired"])
def test_admin_community_cancellation_rejects_nonactive_state_with_conflict(
    game_status: str,
) -> None:
    admin = _user(f"05c-cancel-{game_status}-admin", role="admin")
    host = _user(f"05c-cancel-{game_status}-host")
    _add_users(admin, host)
    game_id, _ = _persist_community_game_fixture(
        f"05c-cancel-{game_status}",
        admin=admin,
        host=host,
    )
    with _session() as db:
        game = db.get(Game, game_id)
        game.game_status = game_status
        if game_status == "completed":
            game.completed_at = datetime.now(timezone.utc)
        db.commit()

    with _session() as db, pytest.raises(HTTPException) as rejected:
        admin_cancel_community_game(
            db,
            game_id=game_id,
            admin_user=db.get(User, admin.id),
            payload=AdminCommunityGameEnforcementActionCreate(
                reason="Private invalid cancellation reason",
                idempotency_key=f"05c-cancel-{game_status}-conflict",
            ),
        )

    assert rejected.value.status_code == 409
    assert rejected.value.detail == "Only active games can be cancelled."
    with _session() as db:
        assert db.get(Game, game_id).game_status == game_status
        assert _count(db, AdminAction, AdminAction.target_game_id == game_id) == 0
        assert (
            _count(db, AdminTargetNotice, AdminTargetNotice.target_game_id == game_id)
            == 0
        )


def test_admin_community_cancellation_rejects_started_game_with_conflict() -> None:
    admin = _user("05c-cancel-started-admin", role="admin")
    host = _user("05c-cancel-started-host")
    _add_users(admin, host)
    game_id, _ = _persist_community_game_fixture(
        "05c-cancel-started",
        admin=admin,
        host=host,
    )
    with _session() as db:
        game = db.get(Game, game_id)
        now = datetime.now(timezone.utc)
        game.starts_at = now - timedelta(hours=1)
        game.ends_at = now + timedelta(hours=1)
        game.starts_on_local = game.starts_at.date()
        db.commit()

    with _session() as db, pytest.raises(HTTPException) as rejected:
        admin_cancel_community_game(
            db,
            game_id=game_id,
            admin_user=db.get(User, admin.id),
            payload=AdminCommunityGameEnforcementActionCreate(
                reason="Private started cancellation reason",
                idempotency_key="05c-cancel-started-conflict",
            ),
        )

    assert rejected.value.status_code == 409
    assert rejected.value.detail == "Games cannot be cancelled after start time."
    with _session() as db:
        assert db.get(Game, game_id).game_status == "active"
        assert _count(db, AdminAction, AdminAction.target_game_id == game_id) == 0
        assert (
            _count(db, AdminTargetNotice, AdminTargetNotice.target_game_id == game_id)
            == 0
        )


def test_chat_restore_rejects_cancelled_parent_without_side_effects() -> None:
    admin = _user("05c-terminal-chat-admin", role="admin")
    host = _user("05c-terminal-chat-host")
    sender = _user("05c-terminal-chat-sender")
    _add_users(admin, host, sender)
    game_id, _ = _persist_community_game_fixture(
        "05c-terminal-chat",
        admin=admin,
        host=host,
    )
    message_id = _persist_game_chat_message_fixture(
        game_id=game_id,
        sender_user_id=sender.id,
    )
    with _session() as db:
        remove_game_chat_message(
            db,
            game_id=game_id,
            message_id=message_id,
            admin_user=db.get(User, admin.id),
            payload=AdminChatModerationActionCreate(
                reason="Private original removal reason",
                idempotency_key="05c-terminal-chat-remove",
            ),
            expected_game_type="community",
        )
    with _session() as db:
        game = db.get(Game, game_id)
        game.game_status = "cancelled"
        game.cancelled_at = datetime.now(timezone.utc)
        game.cancelled_by_user_id = admin.id
        game.cancellation_source = "admin"
        db.commit()

    with _session() as db, pytest.raises(HTTPException) as rejected:
        restore_game_chat_message(
            db,
            game_id=game_id,
            message_id=message_id,
            admin_user=db.get(User, admin.id),
            payload=AdminChatModerationActionCreate(
                reason="Private terminal restoration reason",
                idempotency_key="05c-terminal-chat-restore",
            ),
            expected_game_type="community",
        )

    assert rejected.value.status_code == 409
    with _session() as db:
        assert db.get(ChatMessage, message_id).visibility_status == "removed"
        actions = list(
            db.scalars(
                select(AdminAction).where(AdminAction.target_message_id == message_id)
            ).all()
        )
        assert [action.action_type for action in actions] == ["remove_chat_message"]


def test_need_a_sub_chat_restore_rejects_cancelled_parent_without_side_effects() -> (
    None
):
    admin = _user("05c-terminal-sub-chat-admin", role="admin")
    owner = _user("05c-terminal-sub-chat-owner")
    sender = _user("05c-terminal-sub-chat-sender")
    _add_users(admin, owner, sender)
    post_id = _persist_sub_post_fixture("05c-terminal-sub-chat", owner=owner)
    message_id = _persist_sub_post_chat_message_fixture(
        post_id=post_id,
        sender_user_id=sender.id,
    )
    with _session() as db:
        remove_need_a_sub_chat_message(
            db,
            post_id=post_id,
            message_id=message_id,
            admin_user=db.get(User, admin.id),
            payload=AdminChatModerationActionCreate(
                reason="Private original sub-chat removal reason",
                idempotency_key="05c-terminal-sub-chat-remove",
            ),
        )
    with _session() as db:
        post = db.get(SubPost, post_id)
        post.post_status = "cancelled"
        post.canceled_at = datetime.now(timezone.utc)
        post.canceled_by_user_id = owner.id
        db.commit()

    with _session() as db, pytest.raises(HTTPException) as rejected:
        restore_need_a_sub_chat_message(
            db,
            post_id=post_id,
            message_id=message_id,
            admin_user=db.get(User, admin.id),
            payload=AdminChatModerationActionCreate(
                reason="Private terminal sub-chat restoration reason",
                idempotency_key="05c-terminal-sub-chat-restore",
            ),
        )

    assert rejected.value.status_code == 409
    with _session() as db:
        assert db.get(SubPostChatMessage, message_id).visibility_status == "removed"
        actions = list(
            db.scalars(
                select(AdminAction).where(
                    AdminAction.target_sub_chat_message_id == message_id
                )
            ).all()
        )
        assert [action.action_type for action in actions] == ["remove_chat_message"]


def test_chat_restore_revalidates_deleted_parent_before_message_lock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = _user("05c-deleted-chat-admin", role="admin")
    host = _user("05c-deleted-chat-host")
    sender = _user("05c-deleted-chat-sender")
    _add_users(admin, host, sender)
    game_id, _ = _persist_community_game_fixture(
        "05c-deleted-chat",
        admin=admin,
        host=host,
    )
    message_id = _persist_game_chat_message_fixture(
        game_id=game_id,
        sender_user_id=sender.id,
    )
    with _session() as db:
        remove_game_chat_message(
            db,
            game_id=game_id,
            message_id=message_id,
            admin_user=db.get(User, admin.id),
            payload=AdminChatModerationActionCreate(
                reason="Private original deletion-race reason",
                idempotency_key="05c-deleted-chat-remove",
            ),
            expected_game_type="community",
        )

    restore_ready = threading.Event()
    deleted = threading.Event()
    original_lock = chat_moderation_admin_service.lock_chat_action_parent

    def pause_before_parent_lock(*args, **kwargs):
        restore_ready.set()
        assert deleted.wait(timeout=10)
        return original_lock(*args, **kwargs)

    monkeypatch.setattr(
        chat_moderation_admin_service,
        "lock_chat_action_parent",
        pause_before_parent_lock,
    )

    def restore():
        with _session() as db:
            try:
                return restore_game_chat_message(
                    db,
                    game_id=game_id,
                    message_id=message_id,
                    admin_user=db.get(User, admin.id),
                    payload=AdminChatModerationActionCreate(
                        reason="Private deletion-race restoration reason",
                        idempotency_key="05c-deleted-chat-restore",
                    ),
                    expected_game_type="community",
                )
            except HTTPException as exc:
                return exc

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(restore)
        assert restore_ready.wait(timeout=5)
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
    with _session() as db:
        assert db.get(Game, game_id).deleted_at is not None
        assert db.get(ChatMessage, message_id).visibility_status == "removed"
        actions = list(
            db.scalars(
                select(AdminAction).where(AdminAction.target_message_id == message_id)
            ).all()
        )
        assert [action.action_type for action in actions] == ["remove_chat_message"]
