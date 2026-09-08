from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from fastapi.routing import APIRoute
from pydantic import ValidationError
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import DBAPIError, IntegrityError

from backend.models import (
    AdminAction,
    AdminReviewCase,
    AdminReviewCaseEvent,
    AdminReviewCaseNote,
    AdminReviewSignal,
)
from backend.schemas.admin_review_schema import (
    AdminReviewCaseClose,
    AdminReviewCaseNoteCreate,
)
from backend.services import admin_review_service
from backend.services.admin_action_service import record_admin_action
from backend.services.admin_review_service import (
    add_review_case_note,
    close_open_content_moderation_case_for_game_lifecycle,
    close_review_case,
    link_admin_action_to_open_review_case,
    validate_automatic_content_lifecycle_transition,
)
from backend.tests.workflows.moderation_review_case_lifecycle.conftest import (
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


def test_final_api_and_request_schema_exclude_rejected_workflows() -> None:
    from backend.main import app

    routes = {
        (method, route.path)
        for route in app.routes
        if isinstance(route, APIRoute) and route.path.startswith("/admin/review-cases")
        for method in route.methods
    }
    assert routes == {
        ("GET", "/admin/review-cases"),
        ("GET", "/admin/review-cases/{review_case_id}"),
        ("POST", "/admin/review-cases/{review_case_id}/notes"),
        ("POST", "/admin/review-cases/{review_case_id}/close"),
    }
    assert set(AdminReviewCaseNoteCreate.model_fields) == {"body", "idempotency_key"}
    assert set(AdminReviewCaseClose.model_fields) == {
        "outcome",
        "reason",
        "expected_case_version",
        "idempotency_key",
    }

    valid_close = {
        "outcome": "no_action_needed",
        "reason": "Reviewed.",
        "expected_case_version": 2,
        "idempotency_key": "close-contract",
    }
    for invalid_version in (0, -1, True, "2", 2.0, None, [2], {"value": 2}):
        with pytest.raises(ValidationError):
            AdminReviewCaseClose(
                **{**valid_close, "expected_case_version": invalid_version}
            )
    for extra in (
        "assigned_to_user_id",
        "corrects_note_id",
        "creation_reason",
        "event_sequence",
        "merge_case_id",
        "resolution_references",
    ):
        with pytest.raises(ValidationError):
            AdminReviewCaseNoteCreate(
                body="No expanded workflow.",
                idempotency_key="note-contract",
                **{extra: "unexpected"},
            )


def test_all_four_moderation_identities_remain_distinct_and_versioned() -> None:
    with session() as db:
        game = seed_game(db)
        post = seed_sub_post(db)
        cases = (
            create_content_case(db, game),
            create_chat_case(db, game),
            create_sub_content_case(db, post),
            create_sub_chat_case(db, post),
        )

        assert {(item.case_type, item.case_category) for item in cases} == {
            ("community_game", "content_moderation"),
            ("community_game", "chat_moderation"),
            ("need_a_sub", "content_moderation"),
            ("need_a_sub", "chat_moderation"),
        }
        for review_case in cases:
            events = event_rows(db, review_case.id)
            assert review_case.case_version == 2
            assert [item.case_version for item in events] == [1, 2]
            assert events[0].event_type == "case_created"
            assert events[0].event_metadata is None
            assert events[1].event_type in {"finding_attached", "signal_attached"}
            assert events[1].event_metadata is None


def test_source_attachment_ignores_wrong_type_sibling_cases() -> None:
    with session() as db:
        game = seed_game(db)
        post = seed_sub_post(db)
        wrong_game = AdminReviewCase(
            id=uuid.uuid4(),
            case_type="system",
            case_status="open",
            case_category="content_moderation",
            case_version=1,
            priority="attention",
            title="Wrong type",
            summary="Must not receive game findings.",
            target_game_id=game.id,
        )
        wrong_post = AdminReviewCase(
            id=uuid.uuid4(),
            case_type="system",
            case_status="open",
            case_category="chat_moderation",
            case_version=1,
            priority="attention",
            title="Wrong type",
            summary="Must not receive post signals.",
            target_sub_post_id=post.id,
        )
        db.add_all([wrong_game, wrong_post])
        db.commit()

        content_case = create_content_case(db, game)
        chat_case = create_sub_chat_case(db, post)
        assert content_case.case_type == "community_game"
        assert chat_case.case_type == "need_a_sub"
        assert (
            count_rows(
                db,
                AdminReviewSignal,
                AdminReviewSignal.review_case_id == wrong_post.id,
            )
            == 0
        )


def test_note_close_idempotency_stale_state_and_enforcement_precondition() -> None:
    with session() as db:
        game = seed_game(db)
        admin = seed_admin(db)
        review_case = create_content_case(db, game)

        note_payload = AdminReviewCaseNoteCreate(
            body="Review completed against current evidence.",
            idempotency_key="note-idempotent",
        )
        first_note = add_review_case_note(
            db,
            review_case_id=review_case.id,
            admin_user=admin,
            payload=note_payload,
        )
        replay = add_review_case_note(
            db,
            review_case_id=review_case.id,
            admin_user=admin,
            payload=note_payload,
        )
        assert replay.idempotent_replay is True
        assert replay.note.id == first_note.note.id
        assert replay.review_case.case_version == 3

        with pytest.raises(HTTPException) as mismatch:
            add_review_case_note(
                db,
                review_case_id=review_case.id,
                admin_user=admin,
                payload=AdminReviewCaseNoteCreate(
                    body="Different normalized note.",
                    idempotency_key="note-idempotent",
                ),
            )
        assert mismatch.value.status_code == 409
        assert mismatch.value.detail["code"] == "review_case_idempotency_conflict"
        db.rollback()

        with pytest.raises(HTTPException) as stale:
            close_review_case(
                db,
                review_case_id=review_case.id,
                admin_user=admin,
                payload=AdminReviewCaseClose(
                    outcome="no_action_needed",
                    reason="This view is stale.",
                    expected_case_version=2,
                    idempotency_key="close-stale",
                ),
            )
        assert stale.value.detail == {
            "code": "review_case_version_conflict",
            "current": {"case_status": "open", "case_version": 3},
        }
        db.rollback()

        with pytest.raises(HTTPException) as no_enforcement:
            close_review_case(
                db,
                review_case_id=review_case.id,
                admin_user=admin,
                payload=AdminReviewCaseClose(
                    outcome="enforcement_applied",
                    reason="No linked action exists.",
                    expected_case_version=3,
                    idempotency_key="close-no-action",
                ),
            )
        assert no_enforcement.value.detail["code"] == "review_case_transition_conflict"
        db.rollback()

        close_payload = AdminReviewCaseClose(
            outcome="no_action_needed",
            reason="Review completed.",
            expected_case_version=3,
            idempotency_key="close-idempotent",
        )
        closed = close_review_case(
            db,
            review_case_id=review_case.id,
            admin_user=admin,
            payload=close_payload,
        )
        close_replay = close_review_case(
            db,
            review_case_id=review_case.id,
            admin_user=admin,
            payload=close_payload,
        )
        assert close_replay.idempotent_replay is True
        assert close_replay.audit_action_id == closed.audit_action_id
        assert close_replay.review_case.case_version == 4
        with pytest.raises(HTTPException) as closed_note:
            add_review_case_note(
                db,
                review_case_id=review_case.id,
                admin_user=admin,
                payload=AdminReviewCaseNoteCreate(
                    body="Must not append after closure.",
                    idempotency_key="closed-note",
                ),
            )
        assert closed_note.value.detail["code"] == "review_case_transition_conflict"


def test_linked_enforcement_is_category_correct_and_allows_enforcement_closure() -> (
    None
):
    with session() as db:
        game = seed_game(db)
        admin = seed_admin(db)
        content_case = create_content_case(db, game)
        chat_case = create_chat_case(db, game)
        action = record_admin_action(
            db,
            admin_user_id=admin.id,
            action_type="hide_community_game",
            target_game_id=game.id,
            target_user_id=game.host_user_id,
            reason="Hide unsafe content.",
            metadata={"source": "contract-test"},
            idempotency_key="enforcement-link",
        )
        linked = link_admin_action_to_open_review_case(db, action)
        db.commit()
        assert linked.id == content_case.id
        assert action.target_review_case_id == content_case.id
        assert chat_case.case_version == 2
        assert content_case.case_version == 3

        result = close_review_case(
            db,
            review_case_id=content_case.id,
            admin_user=admin,
            payload=AdminReviewCaseClose(
                outcome="enforcement_applied",
                reason="Eligible action is directly linked.",
                expected_case_version=3,
                idempotency_key="enforcement-close",
            ),
        )
        assert result.review_case.case_status == "closed"
        assert result.review_case.case_version == 4


def test_enforcement_linking_rejects_financial_restorative_and_wrong_targets() -> None:
    with session() as db:
        game = seed_game(db)
        other_game = seed_game(db)
        admin = seed_admin(db)
        content_case = create_content_case(db, game)
        chat_case = create_chat_case(db, game)

        rejected_actions = (
            record_admin_action(
                db,
                admin_user_id=admin.id,
                action_type="issue_credit",
                target_user_id=game.host_user_id,
                target_game_id=game.id,
                reason="Financial remedy is not moderation enforcement.",
                idempotency_key="financial-not-enforcement",
            ),
            record_admin_action(
                db,
                admin_user_id=admin.id,
                action_type="restore_community_game",
                target_game_id=game.id,
                target_user_id=game.host_user_id,
                reason="Restoration is not restrictive enforcement.",
                idempotency_key="restore-not-enforcement",
            ),
            record_admin_action(
                db,
                admin_user_id=admin.id,
                action_type="hide_community_game",
                target_game_id=other_game.id,
                target_user_id=other_game.host_user_id,
                reason="Action belongs to another game.",
                idempotency_key="wrong-target-enforcement",
            ),
        )

        for action in rejected_actions:
            assert link_admin_action_to_open_review_case(db, action) is None
            assert action.target_review_case_id is None

        db.commit()
        assert content_case.case_version == 2
        assert chat_case.case_version == 2
        assert [event.event_type for event in event_rows(db, content_case.id)] == [
            "case_created",
            "finding_attached",
        ]

        with pytest.raises(HTTPException) as rejected_close:
            close_review_case(
                db,
                review_case_id=content_case.id,
                admin_user=admin,
                payload=AdminReviewCaseClose(
                    outcome="enforcement_applied",
                    reason="No eligible action is linked.",
                    expected_case_version=2,
                    idempotency_key="reject-ineligible-enforcement",
                ),
            )
        assert rejected_close.value.detail["code"] == "review_case_transition_conflict"


def test_need_sub_restrictive_enforcement_links_only_to_content_case() -> None:
    with session() as db:
        post = seed_sub_post(db)
        admin = seed_admin(db)
        content_case = create_sub_content_case(db, post)
        chat_case = create_sub_chat_case(db, post)
        action = record_admin_action(
            db,
            admin_user_id=admin.id,
            action_type="hide_need_sub_post",
            target_sub_post_id=post.id,
            target_user_id=post.owner_user_id,
            reason="Hide unsafe post content.",
            metadata={"source": "contract-test"},
            idempotency_key="sub-enforcement-link",
        )

        linked = link_admin_action_to_open_review_case(db, action)
        db.commit()
        assert linked.id == content_case.id
        assert action.target_review_case_id == content_case.id
        assert content_case.case_version == 3
        assert chat_case.case_version == 2

        result = close_review_case(
            db,
            review_case_id=content_case.id,
            admin_user=admin,
            payload=AdminReviewCaseClose(
                outcome="enforcement_applied",
                reason="Eligible Need a Sub enforcement is linked.",
                expected_case_version=3,
                idempotency_key="sub-enforcement-close",
            ),
        )
        assert result.review_case.case_status == "closed"
        assert result.review_case.case_version == 4


def test_automatic_closure_validates_transition_and_closes_only_content() -> None:
    with session() as db:
        game = seed_game(db)
        admin = seed_admin(db)
        content_case = create_content_case(db, game)
        chat_case = create_chat_case(db, game)
        game.deleted_at = datetime.now(timezone.utc)
        db.commit()

        closed = close_open_content_moderation_case_for_game_lifecycle(
            db,
            game_id=game.id,
            closure_outcome="no_action_needed",
            closure_reason="Target was soft deleted.",
            lifecycle_action="admin_soft_deleted",
            trigger_actor_type="admin",
            trigger_actor_user_id=admin.id,
            closed_by_user_id=admin.id,
            previous_game_status="active",
            new_game_status="soft_deleted",
        )
        db.commit()
        assert closed.id == content_case.id
        assert closed.case_version == 3
        assert db.get(AdminReviewCase, chat_case.id).case_status == "open"
        closure_event = event_rows(db, content_case.id)[-1]
        assert closure_event.event_type == "closed"
        assert closure_event.event_metadata == {
            "closure_source": "target_lifecycle",
            "lifecycle_action": "admin_soft_deleted",
            "previous_target_state": "active",
            "new_target_state": "soft_deleted",
            "trigger_actor_type": "admin",
        }
        assert (
            close_open_content_moderation_case_for_game_lifecycle(
                db,
                game_id=game.id,
                closure_outcome="no_action_needed",
                closure_reason="Repeated callback.",
                lifecycle_action="admin_soft_deleted",
                trigger_actor_type="admin",
                trigger_actor_user_id=admin.id,
                closed_by_user_id=admin.id,
                previous_game_status="active",
                new_game_status="soft_deleted",
            )
            is None
        )

    valid = {
        "target_type": "community_game",
        "lifecycle_action": "admin_soft_deleted",
        "previous_target_state": "active",
        "new_target_state": "soft_deleted",
        "trigger_actor_type": "admin",
        "trigger_actor_user_id": uuid.uuid4(),
        "closure_outcome": "no_action_needed",
        "admin_action": None,
    }
    valid["closed_by_user_id"] = valid["trigger_actor_user_id"]
    for field_name, invalid in (
        ("target_type", "need_a_sub"),
        ("lifecycle_action", "host_cancelled"),
        ("previous_target_state", "completed"),
        ("new_target_state", "cancelled"),
        ("trigger_actor_type", "system"),
        ("trigger_actor_user_id", None),
        ("closed_by_user_id", None),
        ("closure_outcome", "enforcement_applied"),
    ):
        with pytest.raises(ValueError):
            validate_automatic_content_lifecycle_transition(
                **{**valid, field_name: invalid}
            )


def test_automatic_enforcement_closure_requires_exact_action_target_and_case() -> None:
    with session() as db:
        game = seed_game(db)
        admin = seed_admin(db)
        content_case = create_content_case(db, game)
        chat_case = create_chat_case(db, game)
        action = record_admin_action(
            db,
            admin_user_id=admin.id,
            action_type="admin_cancel_community_game",
            target_game_id=game.id,
            target_user_id=game.host_user_id,
            reason="Moderation cancellation.",
            idempotency_key="automatic-enforcement",
        )
        game.game_status = "cancelled"
        game.cancelled_at = datetime.now(timezone.utc)
        game.cancellation_source = "admin"
        db.commit()

        closed = close_open_content_moderation_case_for_game_lifecycle(
            db,
            game_id=game.id,
            closure_outcome="enforcement_applied",
            closure_reason="Game cancelled for moderation.",
            lifecycle_action="admin_moderation_cancelled",
            trigger_actor_type="admin",
            trigger_actor_user_id=admin.id,
            closed_by_user_id=admin.id,
            admin_action=action,
            previous_game_status="active",
            new_game_status="cancelled",
        )
        db.commit()
        assert closed.id == content_case.id
        assert action.target_review_case_id == content_case.id
        assert chat_case.case_status == "open"

    with session() as db:
        game = seed_game(db)
        other_game = seed_game(db)
        admin = seed_admin(db)
        content_case = create_content_case(db, game)
        wrong_target_action = record_admin_action(
            db,
            admin_user_id=admin.id,
            action_type="admin_cancel_community_game",
            target_game_id=other_game.id,
            target_user_id=other_game.host_user_id,
            reason="Different game cancellation.",
            idempotency_key="automatic-wrong-target",
        )
        game.game_status = "cancelled"
        game.cancelled_at = datetime.now(timezone.utc)
        game.cancellation_source = "admin"
        db.commit()

        with pytest.raises(ValueError, match="target is invalid"):
            close_open_content_moderation_case_for_game_lifecycle(
                db,
                game_id=game.id,
                closure_outcome="enforcement_applied",
                closure_reason="Wrong action must not qualify.",
                lifecycle_action="admin_moderation_cancelled",
                trigger_actor_type="admin",
                trigger_actor_user_id=admin.id,
                closed_by_user_id=admin.id,
                admin_action=wrong_target_action,
                previous_game_status="active",
                new_game_status="cancelled",
            )
        db.rollback()
        assert db.get(AdminReviewCase, content_case.id).case_status == "open"

    with session() as db:
        game = seed_game(db)
        admin = seed_admin(db)
        content_case = create_content_case(db, game)
        chat_case = create_chat_case(db, game)
        action = record_admin_action(
            db,
            admin_user_id=admin.id,
            action_type="admin_cancel_community_game",
            target_game_id=game.id,
            target_user_id=game.host_user_id,
            reason="Wrong review-case relationship.",
            idempotency_key="automatic-wrong-case",
        )
        action.target_review_case_id = chat_case.id
        game.game_status = "cancelled"
        game.cancelled_at = datetime.now(timezone.utc)
        game.cancellation_source = "admin"
        db.commit()

        with pytest.raises(ValueError, match="target is invalid"):
            close_open_content_moderation_case_for_game_lifecycle(
                db,
                game_id=game.id,
                closure_outcome="enforcement_applied",
                closure_reason="Wrong case link must not qualify.",
                lifecycle_action="admin_moderation_cancelled",
                trigger_actor_type="admin",
                trigger_actor_user_id=admin.id,
                closed_by_user_id=admin.id,
                admin_action=action,
                previous_game_status="active",
                new_game_status="cancelled",
            )
        db.rollback()
        assert db.get(AdminReviewCase, content_case.id).case_status == "open"


def test_postgresql_identity_uniqueness_versions_and_immutability() -> None:
    with session() as db:
        game = seed_game(db)
        other_game = seed_game(db)
        admin = seed_admin(db)
        content_case = create_content_case(db, game)
        chat_case = create_chat_case(db, game)

        duplicate = AdminReviewCase(
            id=uuid.uuid4(),
            case_type="community_game",
            case_status="open",
            case_category="content_moderation",
            case_version=1,
            priority="attention",
            title="Duplicate",
            summary="Database must reject this row.",
            target_game_id=game.id,
        )
        db.add(duplicate)
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()
        assert db.get(AdminReviewCase, chat_case.id) is not None

        for values in (
            {"target_game_id": other_game.id},
            {"case_type": "system"},
            {"case_category": "chat_moderation"},
            {"case_version": 0},
        ):
            with pytest.raises(DBAPIError):
                db.execute(
                    update(AdminReviewCase)
                    .where(AdminReviewCase.id == content_case.id)
                    .values(**values)
                )
                db.flush()
            db.rollback()

        note = add_review_case_note(
            db,
            review_case_id=content_case.id,
            admin_user=admin,
            payload=AdminReviewCaseNoteCreate(
                body="Immutable note.",
                idempotency_key="immutable-note",
            ),
        ).note
        event = event_rows(db, content_case.id)[-1]
        for statement in (
            update(AdminReviewCaseNote)
            .where(AdminReviewCaseNote.id == note.id)
            .values(body="Changed"),
            delete(AdminReviewCaseNote).where(AdminReviewCaseNote.id == note.id),
            update(AdminReviewCaseEvent)
            .where(AdminReviewCaseEvent.id == event.id)
            .values(event_type="case_created"),
            delete(AdminReviewCaseEvent).where(AdminReviewCaseEvent.id == event.id),
        ):
            with pytest.raises(DBAPIError):
                db.execute(statement)
                db.flush()
            db.rollback()

        closed = close_review_case(
            db,
            review_case_id=content_case.id,
            admin_user=admin,
            payload=AdminReviewCaseClose(
                outcome="no_action_needed",
                reason="Seal projection.",
                expected_case_version=3,
                idempotency_key="seal-case",
            ),
        ).review_case
        with pytest.raises(DBAPIError):
            db.execute(
                update(AdminReviewCase)
                .where(AdminReviewCase.id == closed.id)
                .values(priority="critical")
            )
            db.flush()


def test_event_reference_shape_and_transaction_rollback_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with session() as db:
        game = seed_game(db)
        admin = seed_admin(db)
        review_case = create_content_case(db, game)
        malformed = AdminReviewCaseEvent(
            id=uuid.uuid4(),
            review_case_id=review_case.id,
            case_version=review_case.case_version + 1,
            event_type="note_added",
            actor_user_id=admin.id,
        )
        db.add(malformed)
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()

        before_notes = count_rows(db, AdminReviewCaseNote)
        before_actions = count_rows(db, AdminAction)
        before_events = count_rows(
            db,
            AdminReviewCaseEvent,
            AdminReviewCaseEvent.review_case_id == review_case.id,
        )
        original_create_event = admin_review_service.create_case_event

        def fail_event(*args, **kwargs):
            del args, kwargs
            raise RuntimeError("synthetic event failure")

        monkeypatch.setattr(admin_review_service, "create_case_event", fail_event)
        with pytest.raises(RuntimeError, match="synthetic event failure"):
            add_review_case_note(
                db,
                review_case_id=review_case.id,
                admin_user=admin,
                payload=AdminReviewCaseNoteCreate(
                    body="Must roll back completely.",
                    idempotency_key="rollback-note",
                ),
            )
        db.rollback()
        monkeypatch.setattr(
            admin_review_service,
            "create_case_event",
            original_create_event,
        )
        assert count_rows(db, AdminReviewCaseNote) == before_notes
        assert count_rows(db, AdminAction) == before_actions
        assert (
            count_rows(
                db,
                AdminReviewCaseEvent,
                AdminReviewCaseEvent.review_case_id == review_case.id,
            )
            == before_events
        )
        assert db.get(AdminReviewCase, review_case.id).case_version == 2
