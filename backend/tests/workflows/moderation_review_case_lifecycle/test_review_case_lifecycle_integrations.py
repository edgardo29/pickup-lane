from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select

from backend.models import (
    AdminAction,
    AdminReviewCase,
    AdminReviewCaseEvent,
    Game,
    SubPost,
    User,
)
from backend.services.account_deletion_service import (
    cancel_future_community_hosted_games,
    cancel_future_user_activity,
    cancel_owned_need_a_sub_posts,
)
from backend.services.game_rules import VALID_GAME_STATUSES
from backend.services.game_service import delete_game_workflow
from backend.services.need_a_sub_post_service import remove_sub_post
from backend.services.need_a_sub_rules import POST_STATUSES
from backend.tests.workflows.moderation_review_case_lifecycle.conftest import (
    BASE_TIME,
    create_chat_case,
    create_content_case,
    create_sub_chat_case,
    create_sub_content_case,
    seed_admin,
    seed_game,
    seed_sub_post,
    session,
)

pytestmark = pytest.mark.suite_type("ordinary")

GAME_TERMINAL_DELETE_STATES = {"cancelled", "completed", "expired", "removed"}
SUB_POST_TERMINAL_REMOVE_STATES = {"cancelled", "completed", "expired"}


def event_rows(db, review_case_id: uuid.UUID) -> list[AdminReviewCaseEvent]:
    return list(
        db.scalars(
            select(AdminReviewCaseEvent)
            .where(AdminReviewCaseEvent.review_case_id == review_case_id)
            .order_by(AdminReviewCaseEvent.case_version.asc())
        ).all()
    )


def count_rows(db, model, *conditions) -> int:
    return db.scalar(select(func.count(model.id)).where(*conditions)) or 0


def assert_automatic_closed_event(
    db,
    *,
    review_case_id: uuid.UUID,
    closure_outcome: str,
    closed_by_user_id: uuid.UUID | None,
    lifecycle_action: str,
    trigger_actor_user_id: uuid.UUID,
    trigger_actor_type: str,
    new_target_state: str,
) -> None:
    review_case = db.get(AdminReviewCase, review_case_id)
    events = event_rows(db, review_case_id)
    assert review_case.case_status == "closed"
    assert review_case.case_version == 3
    assert review_case.closure_outcome == closure_outcome
    assert review_case.closed_by_user_id == closed_by_user_id
    assert [event.case_version for event in events] == [1, 2, 3]
    assert [event.event_type for event in events] == [
        "case_created",
        "finding_attached",
        "closed",
    ]
    assert events[-1].event_metadata == {
        "closure_source": "target_lifecycle",
        "lifecycle_action": lifecycle_action,
        "previous_target_state": "active",
        "new_target_state": new_target_state,
        "trigger_actor_type": trigger_actor_type,
    }
    assert events[-1].actor_user_id == trigger_actor_user_id


def test_account_deletion_closes_game_content_case_once_and_preserves_chat_case() -> None:
    now = BASE_TIME - timedelta(days=1)
    with session() as db:
        game = seed_game(db)
        owner = db.get(User, game.host_user_id)
        content_case = create_content_case(db, game)
        chat_case = create_chat_case(db, game)
        game_id = game.id
        content_case_id = content_case.id
        chat_case_id = chat_case.id

        cancel_future_community_hosted_games(db, user=owner, now=now)
        db.commit()
        cancel_future_community_hosted_games(db, user=owner, now=now)
        db.commit()

        assert db.get(Game, game_id).game_status == "cancelled"
        assert_automatic_closed_event(
            db,
            review_case_id=content_case_id,
            closure_outcome="no_action_needed",
            closed_by_user_id=None,
            lifecycle_action="host_account_deleted",
            trigger_actor_user_id=owner.id,
            trigger_actor_type="owner",
            new_target_state="cancelled",
        )
        chat_case = db.get(AdminReviewCase, chat_case_id)
        assert chat_case.case_status == "open"
        assert chat_case.case_version == 2
        assert count_rows(
            db,
            AdminReviewCaseEvent,
            AdminReviewCaseEvent.review_case_id == content_case_id,
            AdminReviewCaseEvent.event_type == "closed",
        ) == 1


def test_account_deletion_closes_sub_post_content_case_once_and_preserves_chat_case() -> None:
    now = BASE_TIME - timedelta(days=1)
    with session() as db:
        post = seed_sub_post(db)
        content_case = create_sub_content_case(db, post)
        chat_case = create_sub_chat_case(db, post)
        post_id = post.id
        owner_id = post.owner_user_id
        content_case_id = content_case.id
        chat_case_id = chat_case.id

        cancel_owned_need_a_sub_posts(
            db,
            user_id=owner_id,
            changed_by_user_id=owner_id,
            now=now,
        )
        db.commit()
        cancel_owned_need_a_sub_posts(
            db,
            user_id=owner_id,
            changed_by_user_id=owner_id,
            now=now,
        )
        db.commit()

        assert db.get(SubPost, post_id).post_status == "cancelled"
        assert_automatic_closed_event(
            db,
            review_case_id=content_case_id,
            closure_outcome="no_action_needed",
            closed_by_user_id=None,
            lifecycle_action="owner_account_deleted",
            trigger_actor_user_id=owner_id,
            trigger_actor_type="owner",
            new_target_state="cancelled",
        )
        chat_case = db.get(AdminReviewCase, chat_case_id)
        assert chat_case.case_status == "open"
        assert chat_case.case_version == 2
        assert count_rows(
            db,
            AdminReviewCaseEvent,
            AdminReviewCaseEvent.review_case_id == content_case_id,
            AdminReviewCaseEvent.event_type == "closed",
        ) == 1


def test_admin_account_deletion_attributes_game_case_closure_to_admin() -> None:
    now = BASE_TIME - timedelta(days=1)
    with session() as db:
        game = seed_game(db)
        owner = db.get(User, game.host_user_id)
        admin = seed_admin(db, "admin-game-account-deletion")
        content_case = create_content_case(db, game)
        chat_case = create_chat_case(db, game)
        content_case_id = content_case.id
        chat_case_id = chat_case.id

        cancel_future_user_activity(
            owner,
            db,
            now,
            changed_by_user_id=admin.id,
        )
        db.commit()

        assert_automatic_closed_event(
            db,
            review_case_id=content_case_id,
            closure_outcome="no_action_needed",
            closed_by_user_id=admin.id,
            lifecycle_action="host_account_deleted",
            trigger_actor_user_id=admin.id,
            trigger_actor_type="admin",
            new_target_state="cancelled",
        )
        assert db.get(AdminReviewCase, chat_case_id).case_status == "open"


def test_admin_account_deletion_attributes_sub_post_case_closure_to_admin() -> None:
    now = BASE_TIME - timedelta(days=1)
    with session() as db:
        post = seed_sub_post(db)
        owner = db.get(User, post.owner_user_id)
        admin = seed_admin(db, "admin-sub-account-deletion")
        content_case = create_sub_content_case(db, post)
        chat_case = create_sub_chat_case(db, post)
        content_case_id = content_case.id
        chat_case_id = chat_case.id

        cancel_future_user_activity(
            owner,
            db,
            now,
            changed_by_user_id=admin.id,
        )
        db.commit()

        assert_automatic_closed_event(
            db,
            review_case_id=content_case_id,
            closure_outcome="no_action_needed",
            closed_by_user_id=admin.id,
            lifecycle_action="owner_account_deleted",
            trigger_actor_user_id=admin.id,
            trigger_actor_type="admin",
            new_target_state="cancelled",
        )
        assert db.get(AdminReviewCase, chat_case_id).case_status == "open"


def test_account_deletion_rollback_leaves_targets_and_review_cases_unchanged() -> None:
    now = BASE_TIME - timedelta(days=1)
    with session() as db:
        game = seed_game(db)
        post = seed_sub_post(db)
        owner = db.get(User, game.host_user_id)
        game_content_case = create_content_case(db, game)
        game_chat_case = create_chat_case(db, game)
        post_content_case = create_sub_content_case(db, post)
        post_chat_case = create_sub_chat_case(db, post)
        identities = {
            "game": game.id,
            "post": post.id,
            "game_content": game_content_case.id,
            "game_chat": game_chat_case.id,
            "post_content": post_content_case.id,
            "post_chat": post_chat_case.id,
        }

        with pytest.raises(
            RuntimeError,
            match="synthetic final account-cleanup failure",
        ):
            cancel_future_community_hosted_games(db, user=owner, now=now)
            cancel_owned_need_a_sub_posts(
                db,
                user_id=post.owner_user_id,
                changed_by_user_id=post.owner_user_id,
                now=now,
            )
            raise RuntimeError("synthetic final account-cleanup failure")
        db.rollback()

        assert db.get(Game, identities["game"]).game_status == "active"
        assert db.get(SubPost, identities["post"]).post_status == "active"
        for key in ("game_content", "game_chat", "post_content", "post_chat"):
            review_case = db.get(AdminReviewCase, identities[key])
            assert review_case.case_status == "open"
            assert review_case.case_version == 2
            assert len(event_rows(db, review_case.id)) == 2


def test_active_game_delete_closes_only_the_content_case() -> None:
    with session() as db:
        game = seed_game(db)
        admin = seed_admin(db)
        content_case = create_content_case(db, game)
        chat_case = create_chat_case(db, game)
        game_id = game.id
        content_case_id = content_case.id
        chat_case_id = chat_case.id

        deleted_game = delete_game_workflow(db, game_id, admin)

        assert deleted_game.deleted_at is not None
        assert_automatic_closed_event(
            db,
            review_case_id=content_case_id,
            closure_outcome="no_action_needed",
            closed_by_user_id=admin.id,
            lifecycle_action="admin_soft_deleted",
            trigger_actor_user_id=admin.id,
            trigger_actor_type="admin",
            new_target_state="soft_deleted",
        )
        chat_case = db.get(AdminReviewCase, chat_case_id)
        assert chat_case.case_status == "open"
        assert chat_case.case_version == 2


@pytest.mark.parametrize("game_status", sorted(GAME_TERMINAL_DELETE_STATES))
def test_terminal_game_delete_without_content_case_remains_valid(game_status: str) -> None:
    assert GAME_TERMINAL_DELETE_STATES | {"active"} == VALID_GAME_STATUSES
    with session() as db:
        game = seed_game(db)
        admin = seed_admin(db)
        transition_time = datetime.now(timezone.utc)
        game.game_status = game_status
        if game_status == "cancelled":
            game.cancelled_at = transition_time
        if game_status == "completed":
            game.completed_at = transition_time
        db.commit()

        deleted_game = delete_game_workflow(db, game.id, admin)

        assert deleted_game.game_status == game_status
        assert deleted_game.deleted_at is not None
        assert count_rows(
            db,
            AdminReviewCase,
            AdminReviewCase.target_game_id == game.id,
        ) == 0


def test_active_sub_post_removal_closes_only_the_content_case() -> None:
    with session() as db:
        post = seed_sub_post(db)
        admin = seed_admin(db)
        content_case = create_sub_content_case(db, post)
        chat_case = create_sub_chat_case(db, post)
        post_id = post.id
        content_case_id = content_case.id
        chat_case_id = chat_case.id

        removed_post = remove_sub_post(
            db,
            admin,
            post_id,
            reason="Remove unsafe saved content.",
            idempotency_key_value="remove-active-reviewed-post",
        )

        assert removed_post.post_status == "removed"
        assert_automatic_closed_event(
            db,
            review_case_id=content_case_id,
            closure_outcome="enforcement_applied",
            closed_by_user_id=admin.id,
            lifecycle_action="admin_removed",
            trigger_actor_user_id=admin.id,
            trigger_actor_type="admin",
            new_target_state="removed",
        )
        chat_case = db.get(AdminReviewCase, chat_case_id)
        assert chat_case.case_status == "open"
        assert chat_case.case_version == 2
        action = db.scalar(
            select(AdminAction).where(
                AdminAction.target_sub_post_id == post_id,
                AdminAction.action_type == "remove_sub_post",
            )
        )
        assert action.target_review_case_id == content_case_id


@pytest.mark.parametrize("post_status", sorted(SUB_POST_TERMINAL_REMOVE_STATES))
def test_terminal_sub_post_removal_without_content_case_remains_valid(
    post_status: str,
) -> None:
    assert SUB_POST_TERMINAL_REMOVE_STATES | {"active", "removed"} == POST_STATUSES
    with session() as db:
        post = seed_sub_post(db)
        admin = seed_admin(db)
        transition_time = datetime.now(timezone.utc)
        post.post_status = post_status
        if post_status == "cancelled":
            post.canceled_at = transition_time
        if post_status == "completed":
            post.filled_at = transition_time
        db.commit()

        removed_post = remove_sub_post(
            db,
            admin,
            post.id,
            reason="Remove terminal saved content.",
            idempotency_key_value=f"remove-terminal-{post_status}",
        )

        assert removed_post.post_status == "removed"
        assert removed_post.removed_at is not None
        assert count_rows(
            db,
            AdminReviewCase,
            AdminReviewCase.target_sub_post_id == post.id,
        ) == 0


def test_already_removed_sub_post_retains_existing_removal_rejection() -> None:
    with session() as db:
        post = seed_sub_post(db)
        admin = seed_admin(db)
        post.post_status = "removed"
        post.removed_at = datetime.now(timezone.utc)
        db.commit()

        with pytest.raises(HTTPException) as rejected:
            remove_sub_post(
                db,
                admin,
                post.id,
                reason="Do not broaden existing removal behavior.",
                idempotency_key_value="remove-already-removed",
            )

        assert rejected.value.status_code == 409
        assert count_rows(
            db,
            AdminAction,
            AdminAction.target_sub_post_id == post.id,
            AdminAction.action_type == "remove_sub_post",
        ) == 0
