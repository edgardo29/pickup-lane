from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from backend.models import (
    AdminAction,
    AdminReviewCase,
    AdminReviewCaseEvent,
    AdminReviewCaseResolutionReference,
    SubPostPosition,
    SubPostRequest,
    User,
)
from backend.schemas.admin_community_schema import (
    AdminCommunityGameEnforcementActionCreate,
)
from backend.schemas.admin_review_schema import AdminReviewCaseAssignment
from backend.schemas.game_schema import GameCancelCreate
from backend.services.account_deletion_service import (
    cancel_future_community_hosted_games,
    cancel_owned_need_a_sub_posts,
)
from backend.services.admin_review_service import (
    TARGET_LIFECYCLE_RULE_ID,
    TARGET_LIFECYCLE_RULE_VERSION,
    assign_review_case,
    close_open_content_moderation_case_for_game_lifecycle,
)
from backend.services.community_game_enforcement_service import (
    admin_cancel_community_game,
)
from backend.services.game_cancellation_service import cancel_game_state_workflow
from backend.services.game_service import delete_game_workflow
from backend.services.need_a_sub_lifecycle_service import expire_due_posts_and_requests
from backend.services.need_a_sub_post_service import cancel_sub_post, remove_sub_post
from backend.tests.workflows.conflict_safe_moderation_review_case_lifecycle.conftest import (
    create_chat_case,
    create_content_case,
    create_sub_chat_case,
    create_sub_content_case,
    make_user,
    seed_admin,
    seed_game,
    seed_sub_post,
    session,
)

pytestmark = pytest.mark.suite_type("ordinary")


def create_wrong_type_content_sibling(db, *, target_field: str, target_id):
    review_case = AdminReviewCase(
        id=uuid.uuid4(),
        case_type="system",
        case_status="open",
        case_category="content_moderation",
        priority="attention",
        title="Wrong-type sibling",
        summary="Must not be selected by target lifecycle closure.",
        case_version=1,
        creation_reason="content_moderation_finding",
        **{target_field: target_id},
    )
    db.add(review_case)
    db.commit()
    return review_case


def assert_automatic_content_closure(
    db,
    *,
    review_case_id,
    lifecycle_action: str,
    previous_state: str,
    new_state: str,
):
    review_case = db.get(AdminReviewCase, review_case_id)
    assert review_case.case_status == "closed"
    assert review_case.closure_mode == "automatic"
    assert review_case.closure_rule_id == TARGET_LIFECYCLE_RULE_ID
    assert review_case.closure_rule_version == TARGET_LIFECYCLE_RULE_VERSION
    assert review_case.assigned_to_user_id is None
    closure_events = list(
        db.scalars(
            select(AdminReviewCaseEvent).where(
                AdminReviewCaseEvent.review_case_id == review_case_id,
                AdminReviewCaseEvent.event_type == "closed",
            )
        ).all()
    )
    assert len(closure_events) == 1
    closure_event = closure_events[0]
    assert closure_event.actor_kind == "automation"
    assert closure_event.automation_rule_id == TARGET_LIFECYCLE_RULE_ID
    assert closure_event.automation_rule_version == TARGET_LIFECYCLE_RULE_VERSION
    assert closure_event.event_metadata["lifecycle_action"] == lifecycle_action
    assert closure_event.event_metadata["previous_target_state"] == previous_state
    assert closure_event.event_metadata["new_target_state"] == new_state
    assert (
        db.scalars(
            select(AdminReviewCaseResolutionReference).where(
                AdminReviewCaseResolutionReference.closure_event_id == closure_event.id
            )
        ).first()
        is not None
    )
    return review_case, closure_event


@pytest.mark.requirement("WS03-05B-R2", "WS03-05B-R3", "WS03-05B-R5")
def test_host_game_cancellation_closes_only_the_content_case() -> None:
    with session() as db:
        game = seed_game(db)
        wrong_type_case_id = create_wrong_type_content_sibling(
            db,
            target_field="target_game_id",
            target_id=game.id,
        ).id
        content_case_id = create_content_case(db, game).id
        chat_case_id = create_chat_case(db, game).id
        host = db.get(User, game.host_user_id)

        cancelled = cancel_game_state_workflow(
            db,
            game.id,
            GameCancelCreate(cancel_reason="Host cancelled the game."),
            host,
        )
        assert cancelled.game_status == "cancelled"
        content_case, event = assert_automatic_content_closure(
            db,
            review_case_id=content_case_id,
            lifecycle_action="host_cancelled",
            previous_state="active",
            new_state="cancelled",
        )
        assert content_case.closure_outcome == "no_action_needed"
        assert event.event_metadata["trigger_actor_type"] == "host"
        assert event.trigger_actor_user_id == host.id
        assert db.get(AdminReviewCase, chat_case_id).case_status == "open"
        assert db.get(AdminReviewCase, wrong_type_case_id).case_status == "open"


@pytest.mark.requirement("WS03-05B-R2", "WS03-05B-R3", "WS03-05B-R5")
@pytest.mark.parametrize(
    ("enforcement", "expected_action", "expected_outcome", "expected_lifecycle"),
    (
        (
            False,
            "cancel_game",
            "no_action_needed",
            "admin_operational_cancelled",
        ),
        (
            True,
            "admin_cancel_community_game",
            "enforcement_applied",
            "admin_moderation_cancelled",
        ),
    ),
    ids=("operational", "enforcement"),
)
def test_admin_game_cancellation_branches_preserve_exact_case_attribution(
    enforcement: bool,
    expected_action: str,
    expected_outcome: str,
    expected_lifecycle: str,
) -> None:
    with session() as db:
        game = seed_game(db)
        admin = seed_admin(db)
        content_case = create_content_case(db, game)
        chat_case_id = create_chat_case(db, game).id
        assign_review_case(
            db,
            review_case_id=content_case.id,
            admin_user=admin,
            payload=AdminReviewCaseAssignment(
                assignee_user_id=admin.id,
                reason="Claim before admin cancellation.",
                expected_case_version=2,
                idempotency_key=f"ws03-05b-admin-cancel-assign-{enforcement}",
            ),
        )

        if enforcement:
            admin_cancel_community_game(
                db,
                game_id=game.id,
                admin_user=admin,
                payload=AdminCommunityGameEnforcementActionCreate(
                    reason="Cancel unsafe Community Game.",
                    idempotency_key="ws03-05b-admin-enforcement-cancel",
                ),
            )
        else:
            cancel_game_state_workflow(
                db,
                game.id,
                GameCancelCreate(cancel_reason="Operational cancellation."),
                admin,
            )

        content_case, event = assert_automatic_content_closure(
            db,
            review_case_id=content_case.id,
            lifecycle_action=expected_lifecycle,
            previous_state="active",
            new_state="cancelled",
        )
        assert content_case.closure_outcome == expected_outcome
        assert content_case.assigned_to_user_id is None
        assert event.event_metadata["trigger_actor_type"] == "admin"
        assert event.trigger_actor_user_id == admin.id
        assert event.admin_action_id is not None
        action = db.get(AdminAction, event.admin_action_id)
        assert action.action_type == expected_action
        assert event.event_metadata["linked_admin_action_id"] == str(action.id)
        assert db.get(AdminReviewCase, chat_case_id).case_status == "open"


@pytest.mark.requirement("WS03-05B-R2", "WS03-05B-R3", "WS03-05B-R5")
def test_account_deletion_game_cancellation_closes_only_the_content_case() -> None:
    with session() as db:
        game = seed_game(db)
        admin = seed_admin(db)
        host = db.get(User, game.host_user_id)
        content_case = create_content_case(db, game)
        chat_case_id = create_chat_case(db, game).id
        assign_review_case(
            db,
            review_case_id=content_case.id,
            admin_user=admin,
            payload=AdminReviewCaseAssignment(
                assignee_user_id=admin.id,
                reason="Claim before host account deletion.",
                expected_case_version=2,
                idempotency_key="ws03-05b-account-delete-game-assign",
            ),
        )
        now = datetime.now(timezone.utc)

        cancel_future_community_hosted_games(db, user=host, now=now)
        db.commit()

        content_case, event = assert_automatic_content_closure(
            db,
            review_case_id=content_case.id,
            lifecycle_action="host_account_deleted",
            previous_state="active",
            new_state="cancelled",
        )
        assert content_case.closure_outcome == "no_action_needed"
        assert content_case.assigned_to_user_id is None
        assert event.event_metadata["trigger_actor_type"] == "owner"
        assert event.trigger_actor_user_id == host.id
        assert event.admin_action_id is None
        assert db.get(AdminReviewCase, chat_case_id).case_status == "open"


@pytest.mark.requirement("WS03-05B-R2", "WS03-05B-R3", "WS03-05B-R5")
def test_admin_game_deletion_closes_only_the_content_case() -> None:
    with session() as db:
        game = seed_game(db)
        admin = seed_admin(db)
        content_case_id = create_content_case(db, game).id
        chat_case_id = create_chat_case(db, game).id

        deleted = delete_game_workflow(db, game.id, admin)
        assert deleted.deleted_at is not None
        content_case, event = assert_automatic_content_closure(
            db,
            review_case_id=content_case_id,
            lifecycle_action="admin_soft_deleted",
            previous_state="active",
            new_state="soft_deleted",
        )
        assert content_case.closure_outcome == "no_action_needed"
        assert event.event_metadata["trigger_actor_type"] == "admin"
        assert event.trigger_actor_user_id == admin.id
        assert event.admin_action_id is None
        assert event.event_metadata["linked_admin_action_id"] is None
        assert db.get(AdminReviewCase, chat_case_id).case_status == "open"


@pytest.mark.requirement("WS03-05B-R2", "WS03-05B-R3", "WS03-05B-R5")
@pytest.mark.parametrize("new_status", ("completed", "expired"))
@pytest.mark.parametrize("trigger_actor_type", ("admin", "system"))
def test_game_terminal_status_closure_accepts_each_production_actor_path(
    new_status: str,
    trigger_actor_type: str,
) -> None:
    with session() as db:
        game = seed_game(db)
        admin = seed_admin(db)
        content_case_id = create_content_case(db, game).id
        chat_case_id = create_chat_case(db, game).id
        closed_at = datetime.now(timezone.utc)
        game.game_status = new_status
        if new_status == "completed":
            game.completed_at = closed_at
        game.updated_at = closed_at
        db.add(game)

        actor_id = admin.id if trigger_actor_type == "admin" else None
        closed = close_open_content_moderation_case_for_game_lifecycle(
            db,
            game_id=game.id,
            closure_outcome="no_action_needed",
            closure_reason=f"Community Game became {new_status}.",
            lifecycle_action=f"game_{new_status}",
            trigger_actor_type=trigger_actor_type,
            trigger_actor_user_id=actor_id,
            closed_by_user_id=actor_id,
            previous_game_status="active",
            new_game_status=new_status,
            closed_at=closed_at,
        )
        db.commit()

        assert closed is not None
        _, event = assert_automatic_content_closure(
            db,
            review_case_id=content_case_id,
            lifecycle_action=f"game_{new_status}",
            previous_state="active",
            new_state=new_status,
        )
        assert event.event_metadata["trigger_actor_type"] == trigger_actor_type
        assert event.trigger_actor_user_id == actor_id
        assert db.get(AdminReviewCase, chat_case_id).case_status == "open"


@pytest.mark.requirement("WS03-05B-R2", "WS03-05B-R3", "WS03-05B-R5")
def test_owner_sub_post_cancellation_closes_only_the_content_case() -> None:
    with session() as db:
        post = seed_sub_post(db)
        wrong_type_case_id = create_wrong_type_content_sibling(
            db,
            target_field="target_sub_post_id",
            target_id=post.id,
        ).id
        content_case_id = create_sub_content_case(db, post).id
        chat_case_id = create_sub_chat_case(db, post).id
        owner = db.get(User, post.owner_user_id)

        cancelled = cancel_sub_post(db, owner, post.id, "Owner cancelled the post.")
        assert cancelled.post_status == "cancelled"
        content_case, event = assert_automatic_content_closure(
            db,
            review_case_id=content_case_id,
            lifecycle_action="owner_cancelled",
            previous_state="active",
            new_state="cancelled",
        )
        assert content_case.closure_outcome == "no_action_needed"
        assert event.event_metadata["trigger_actor_type"] == "owner"
        assert event.trigger_actor_user_id == owner.id
        assert db.get(AdminReviewCase, chat_case_id).case_status == "open"
        assert db.get(AdminReviewCase, wrong_type_case_id).case_status == "open"


@pytest.mark.requirement("WS03-05B-R2", "WS03-05B-R3", "WS03-05B-R5")
def test_account_deletion_sub_post_cancellation_closes_only_the_content_case() -> None:
    with session() as db:
        post = seed_sub_post(db)
        admin = seed_admin(db)
        content_case = create_sub_content_case(db, post)
        chat_case_id = create_sub_chat_case(db, post).id
        assign_review_case(
            db,
            review_case_id=content_case.id,
            admin_user=admin,
            payload=AdminReviewCaseAssignment(
                assignee_user_id=admin.id,
                reason="Claim before owner account deletion.",
                expected_case_version=2,
                idempotency_key="ws03-05b-account-delete-sub-assign",
            ),
        )
        now = datetime.now(timezone.utc)

        cancel_owned_need_a_sub_posts(
            db,
            user_id=post.owner_user_id,
            changed_by_user_id=post.owner_user_id,
            now=now,
        )
        db.commit()

        content_case, event = assert_automatic_content_closure(
            db,
            review_case_id=content_case.id,
            lifecycle_action="owner_account_deleted",
            previous_state="active",
            new_state="cancelled",
        )
        assert content_case.closure_outcome == "no_action_needed"
        assert content_case.assigned_to_user_id is None
        assert event.event_metadata["trigger_actor_type"] == "owner"
        assert event.trigger_actor_user_id == post.owner_user_id
        assert event.admin_action_id is None
        assert db.get(AdminReviewCase, chat_case_id).case_status == "open"


@pytest.mark.requirement("WS03-05B-R2", "WS03-05B-R3", "WS03-05B-R5")
def test_admin_sub_post_removal_links_the_enforcement_action() -> None:
    with session() as db:
        post = seed_sub_post(db)
        admin = seed_admin(db)
        content_case_id = create_sub_content_case(db, post).id
        chat_case_id = create_sub_chat_case(db, post).id

        removed = remove_sub_post(
            db,
            admin,
            post.id,
            "Remove unsafe saved content.",
            "ws03-05b-remove-sub-post",
        )
        assert removed.post_status == "removed"
        content_case, event = assert_automatic_content_closure(
            db,
            review_case_id=content_case_id,
            lifecycle_action="admin_removed",
            previous_state="active",
            new_state="removed",
        )
        assert content_case.closure_outcome == "enforcement_applied"
        assert event.admin_action_id is not None
        assert event.event_metadata["linked_admin_action_id"] == str(
            event.admin_action_id
        )
        assert db.get(AdminReviewCase, chat_case_id).case_status == "open"


@pytest.mark.requirement("WS03-05B-R2", "WS03-05B-R3", "WS03-05B-R5")
@pytest.mark.parametrize("filled", (False, True), ids=("expired", "completed"))
def test_scheduled_sub_post_terminal_transition_closes_content_case(
    filled: bool,
) -> None:
    with session() as db:
        post = seed_sub_post(db)
        content_case_id = create_sub_content_case(db, post).id
        chat_case_id = create_sub_chat_case(db, post).id
        post.expires_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
        if filled:
            requester = make_user("scheduled-requester")
            db.add(requester)
            db.flush()
            position = SubPostPosition(
                id=uuid.uuid4(),
                sub_post_id=post.id,
                position_label="field_player",
                player_group="open",
                spots_needed=1,
                sort_order=0,
            )
            db.add(position)
            db.flush()
            request = SubPostRequest(
                id=uuid.uuid4(),
                sub_post_id=post.id,
                sub_post_position_id=position.id,
                requester_user_id=requester.id,
                request_status="confirmed",
                confirmed_at=datetime.now(timezone.utc),
            )
            db.add(request)
        db.add(post)
        db.commit()

        counts = expire_due_posts_and_requests(db)
        expected_status = "completed" if filled else "expired"
        expected_action = f"post_{expected_status}"
        assert counts[f"posts_{expected_status}"] == 1
        content_case, event = assert_automatic_content_closure(
            db,
            review_case_id=content_case_id,
            lifecycle_action=expected_action,
            previous_state="active",
            new_state=expected_status,
        )
        assert content_case.closure_outcome == "no_action_needed"
        assert event.event_metadata["trigger_actor_type"] == "scheduled_job"
        assert db.get(AdminReviewCase, chat_case_id).case_status == "open"
