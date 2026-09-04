from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select

from backend.models import (
    AdminAction,
    AdminContentModerationFinding,
    AdminReviewCase,
    AdminReviewCaseEvent,
    AdminReviewCaseNote,
    AdminReviewCaseResolutionReference,
    AdminReviewSignal,
)
from backend.schemas.admin_review_schema import (
    AdminReviewCaseAssignment,
    AdminReviewCaseClose,
    AdminReviewCaseMerge,
    AdminReviewCaseNoteCreate,
    AdminReviewCaseReopen,
)
from backend.services.admin_review_service import (
    SOURCE_RECONCILIATION_RULE_ID,
    SOURCE_RECONCILIATION_RULE_VERSION,
    TARGET_LIFECYCLE_RULE_ID,
    TARGET_LIFECYCLE_RULE_VERSION,
    add_review_case_note,
    assign_review_case,
    close_open_content_moderation_case_for_game_lifecycle,
    close_review_case,
    link_admin_action_to_open_review_case,
    merge_review_case,
    reopen_review_case,
    serialize_review_case_detail,
    validate_automatic_content_lifecycle_transition,
)
from backend.services.moderation_surfacing_service import surface_community_game_text
from backend.tests.workflows.conflict_safe_moderation_review_case_lifecycle.conftest import (
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


def event_rows(db, review_case_id):
    return list(
        db.scalars(
            select(AdminReviewCaseEvent)
            .where(AdminReviewCaseEvent.review_case_id == review_case_id)
            .order_by(AdminReviewCaseEvent.event_sequence.asc())
        ).all()
    )


def review_case_side_effect_snapshot(db, *review_case_ids):
    case_ids = tuple(review_case_ids)
    cases = list(
        db.scalars(
            select(AdminReviewCase)
            .where(AdminReviewCase.id.in_(case_ids))
            .order_by(AdminReviewCase.id.asc())
        ).all()
    )
    event_ids = select(AdminReviewCaseEvent.id).where(
        AdminReviewCaseEvent.review_case_id.in_(case_ids)
    )
    return {
        "cases": [
            (
                item.id,
                item.case_status,
                item.case_version,
                item.assigned_to_user_id,
                item.closure_outcome,
                item.merged_into_case_id,
            )
            for item in cases
        ],
        "notes": db.scalar(
            select(func.count(AdminReviewCaseNote.id)).where(
                AdminReviewCaseNote.review_case_id.in_(case_ids)
            )
        ),
        "actions": db.scalar(
            select(func.count(AdminAction.id)).where(
                AdminAction.target_review_case_id.in_(case_ids)
            )
        ),
        "events": db.scalar(
            select(func.count(AdminReviewCaseEvent.id)).where(
                AdminReviewCaseEvent.review_case_id.in_(case_ids)
            )
        ),
        "references": db.scalar(
            select(func.count(AdminReviewCaseResolutionReference.id)).where(
                AdminReviewCaseResolutionReference.closure_event_id.in_(event_ids)
            )
        ),
    }


def wrong_type_sibling(db, *, category: str, target_field: str, target_id):
    review_case = AdminReviewCase(
        id=uuid.uuid4(),
        case_type="system",
        case_status="open",
        case_category=category,
        priority="attention",
        title="Wrong-type sibling",
        summary="Must remain separate from the exact moderation identity.",
        case_version=1,
        creation_reason=(
            "content_moderation_finding"
            if category == "content_moderation"
            else "chat_moderation_detection"
        ),
        **{target_field: target_id},
    )
    db.add(review_case)
    db.commit()
    return review_case


def link_game_enforcement_action(db, *, admin, game, idempotency_key: str):
    action = AdminAction(
        id=uuid.uuid4(),
        admin_user_id=admin.id,
        action_type="hide_community_game",
        target_game_id=game.id,
        reason="Persist enforcement attribution for review.",
        metadata_={"source": "ws03_05b_test"},
        idempotency_key=idempotency_key,
        created_at=datetime.now(timezone.utc),
    )
    db.add(action)
    db.flush()
    linked_case = link_admin_action_to_open_review_case(
        db,
        action,
        case_category="content_moderation",
    )
    assert linked_case is not None
    db.commit()
    return action, linked_case


@pytest.mark.requirement("WS03-05B-R1", "WS03-05B-R3", "WS03-05B-R5")
def test_content_and_chat_keep_distinct_open_identities_and_ordered_history() -> None:
    with session() as db:
        game = seed_game(db)
        content_case = create_content_case(db, game)
        chat_case = create_chat_case(db, game)

        assert content_case.id != chat_case.id
        assert content_case.case_category == "content_moderation"
        assert content_case.creation_reason == "content_moderation_finding"
        assert chat_case.case_category == "chat_moderation"
        assert chat_case.creation_reason == "chat_moderation_detection"

        cases = list(
            db.scalars(
                select(AdminReviewCase)
                .where(AdminReviewCase.target_game_id == game.id)
                .order_by(AdminReviewCase.case_category.asc())
            ).all()
        )
        assert len(cases) == 2
        for review_case in cases:
            events = event_rows(db, review_case.id)
            assert review_case.case_version == len(events) == 2
            assert [event.event_sequence for event in events] == [1, 2]
            assert [event.case_version for event in events] == [1, 2]
            assert events[0].event_type == "case_created"
            assert events[0].actor_kind == "automation"
            assert events[0].automation_rule_id == SOURCE_RECONCILIATION_RULE_ID
            assert (
                events[0].automation_rule_version == SOURCE_RECONCILIATION_RULE_VERSION
            )


@pytest.mark.requirement("WS03-05B-R1", "WS03-05B-R3", "WS03-05B-R5")
def test_source_attachment_ignores_wrong_type_siblings_in_all_four_domains() -> None:
    with session() as db:
        game_content = seed_game(db)
        wrong_game_content = wrong_type_sibling(
            db,
            category="content_moderation",
            target_field="target_game_id",
            target_id=game_content.id,
        )
        game_content_case = create_content_case(db, game_content)

        game_chat = seed_game(db)
        wrong_game_chat = wrong_type_sibling(
            db,
            category="chat_moderation",
            target_field="target_game_id",
            target_id=game_chat.id,
        )
        game_chat_case = create_chat_case(db, game_chat)

        sub_content = seed_sub_post(db)
        wrong_sub_content = wrong_type_sibling(
            db,
            category="content_moderation",
            target_field="target_sub_post_id",
            target_id=sub_content.id,
        )
        sub_content_case = create_sub_content_case(db, sub_content)

        sub_chat = seed_sub_post(db)
        wrong_sub_chat = wrong_type_sibling(
            db,
            category="chat_moderation",
            target_field="target_sub_post_id",
            target_id=sub_chat.id,
        )
        sub_chat_case = create_sub_chat_case(db, sub_chat)

        for correct_case, expected_type in (
            (game_content_case, "community_game"),
            (game_chat_case, "community_game"),
            (sub_content_case, "need_a_sub"),
            (sub_chat_case, "need_a_sub"),
        ):
            assert correct_case.case_type == expected_type

        wrong_ids = {
            wrong_game_content.id,
            wrong_game_chat.id,
            wrong_sub_content.id,
            wrong_sub_chat.id,
        }
        assert (
            db.scalar(
                select(func.count(AdminContentModerationFinding.id)).where(
                    AdminContentModerationFinding.review_case_id.in_(wrong_ids)
                )
            )
            == 0
        )
        assert (
            db.scalar(
                select(func.count(AdminReviewSignal.id)).where(
                    AdminReviewSignal.review_case_id.in_(wrong_ids)
                )
            )
            == 0
        )


@pytest.mark.requirement("WS03-05B-R2", "WS03-05B-R3", "WS03-05B-R4")
def test_assignment_notes_resolution_replay_and_reopen_preserve_history() -> None:
    with session() as db:
        game = seed_game(db)
        reviewer = seed_admin(db, "reviewer")
        collaborator = seed_admin(db, "collaborator")
        review_case = create_content_case(db, game)

        assigned = assign_review_case(
            db,
            review_case_id=review_case.id,
            admin_user=reviewer,
            payload=AdminReviewCaseAssignment(
                assignee_user_id=reviewer.id,
                reason="Claim for review.",
                expected_case_version=2,
                idempotency_key="ws03-05b-assign-reviewer",
            ),
        )
        assert assigned.resulting_case_version == 3
        assert assigned.review_case.assigned_to_user_id == reviewer.id

        first_note = add_review_case_note(
            db,
            review_case_id=review_case.id,
            admin_user=collaborator,
            payload=AdminReviewCaseNoteCreate(
                body="Initial internal assessment.",
                expected_case_version=3,
                idempotency_key="ws03-05b-first-note",
            ),
        )
        correction = add_review_case_note(
            db,
            review_case_id=review_case.id,
            admin_user=collaborator,
            payload=AdminReviewCaseNoteCreate(
                body="Corrected internal assessment.",
                corrects_note_id=first_note.note.id,
                expected_case_version=4,
                idempotency_key="ws03-05b-correction-note",
            ),
        )
        assert correction.note.corrects_note_id == first_note.note.id

        with pytest.raises(HTTPException) as assignment_conflict:
            close_review_case(
                db,
                review_case_id=review_case.id,
                admin_user=collaborator,
                payload=AdminReviewCaseClose(
                    outcome="no_action_needed",
                    reason="A different active assignee owns this decision.",
                    expected_case_version=5,
                    idempotency_key="ws03-05b-wrong-reviewer-close",
                ),
            )
        assert assignment_conflict.value.status_code == 409
        assert assignment_conflict.value.detail["code"] == (
            "review_case_assignment_conflict"
        )
        db.rollback()

        reassigned = assign_review_case(
            db,
            review_case_id=review_case.id,
            admin_user=collaborator,
            payload=AdminReviewCaseAssignment(
                assignee_user_id=collaborator.id,
                reason="Take over the active review.",
                expected_case_version=5,
                idempotency_key="ws03-05b-reassign-collaborator",
            ),
        )
        assert reassigned.resulting_case_version == 6

        close_payload = AdminReviewCaseClose(
            outcome="no_action_needed",
            reason="Evidence does not require enforcement.",
            expected_case_version=6,
            idempotency_key="ws03-05b-manual-close",
        )
        closed = close_review_case(
            db,
            review_case_id=review_case.id,
            admin_user=collaborator,
            payload=close_payload,
        )
        assert closed.resulting_case_version == 7
        assert closed.review_case.closure_mode == "manual"
        assert closed.review_case.assigned_to_user_id is None
        assert len(closed.review_case.resolution_references) == 1
        assert closed.review_case.resolution_references[0].reference_type == "finding"
        assert len(closed.review_case.resolution_history) == 1
        manual_history = closed.review_case.resolution_history[0]
        assert manual_history.mode == "manual"
        assert manual_history.outcome == "no_action_needed"
        assert manual_history.reason == close_payload.reason
        assert manual_history.actor_user_id == collaborator.id
        assert manual_history.references == closed.review_case.resolution_references

        replay = close_review_case(
            db,
            review_case_id=review_case.id,
            admin_user=collaborator,
            payload=close_payload,
        )
        assert replay.idempotent_replay is True
        assert replay.applied_case_version == 6
        assert replay.resulting_case_version == 7
        assert replay.review_case.case_version == 7

        reopened = reopen_review_case(
            db,
            review_case_id=review_case.id,
            admin_user=reviewer,
            payload=AdminReviewCaseReopen(
                reason="New review context requires reconsideration.",
                expected_case_version=7,
                idempotency_key="ws03-05b-reopen-case",
            ),
        )
        assert reopened.resulting_case_version == 8
        assert reopened.review_case.case_status == "open"
        assert reopened.review_case.closure_outcome is None
        assert reopened.review_case.assigned_to_user_id is None
        assert reopened.review_case.resolution_history == [manual_history]

        events = reopened.review_case.events
        assert [event.event_sequence for event in events] == list(range(1, 9))
        assert [event.event_type for event in events][-6:] == [
            "assignment_changed",
            "note_added",
            "note_added",
            "assignment_changed",
            "closed",
            "reopened",
        ]
        assert events[-1].related_event_id == events[-2].id
        assert len(reopened.review_case.resolution_references) == 1


@pytest.mark.requirement("WS03-05B-R2", "WS03-05B-R3", "WS03-05B-R4")
def test_closed_case_rejects_note_assignment_and_second_close_without_writes() -> None:
    with session() as db:
        game = seed_game(db)
        admin = seed_admin(db)
        review_case = create_content_case(db, game)
        closed = close_review_case(
            db,
            review_case_id=review_case.id,
            admin_user=admin,
            payload=AdminReviewCaseClose(
                outcome="no_action_needed",
                reason="Prepare prohibited closed-case transitions.",
                expected_case_version=2,
                idempotency_key="ws03-05b-prohibited-prepare-close",
            ),
        )
        before = review_case_side_effect_snapshot(db, review_case.id)
        operations = (
            lambda: add_review_case_note(
                db,
                review_case_id=review_case.id,
                admin_user=admin,
                payload=AdminReviewCaseNoteCreate(
                    body="This closed case must reject the note.",
                    expected_case_version=closed.resulting_case_version,
                    idempotency_key="ws03-05b-prohibited-closed-note",
                ),
            ),
            lambda: assign_review_case(
                db,
                review_case_id=review_case.id,
                admin_user=admin,
                payload=AdminReviewCaseAssignment(
                    assignee_user_id=admin.id,
                    reason="This closed case must reject assignment.",
                    expected_case_version=closed.resulting_case_version,
                    idempotency_key="ws03-05b-prohibited-closed-assignment",
                ),
            ),
            lambda: close_review_case(
                db,
                review_case_id=review_case.id,
                admin_user=admin,
                payload=AdminReviewCaseClose(
                    outcome="no_action_needed",
                    reason="This closed case must reject a second closure.",
                    expected_case_version=closed.resulting_case_version,
                    idempotency_key="ws03-05b-prohibited-second-close",
                ),
            ),
        )
        for operation in operations:
            with pytest.raises(HTTPException) as conflict:
                operation()
            assert conflict.value.status_code == 409
            assert conflict.value.detail["code"] == "review_case_transition_conflict"
            assert review_case_side_effect_snapshot(db, review_case.id) == before


@pytest.mark.requirement("WS03-05B-R2", "WS03-05B-R3", "WS03-05B-R4")
def test_open_case_rejects_reopen_and_same_assignment_without_writes() -> None:
    with session() as db:
        game = seed_game(db)
        admin = seed_admin(db)
        review_case = create_content_case(db, game)

        before_reopen = review_case_side_effect_snapshot(db, review_case.id)
        with pytest.raises(HTTPException) as reopen_conflict:
            reopen_review_case(
                db,
                review_case_id=review_case.id,
                admin_user=admin,
                payload=AdminReviewCaseReopen(
                    reason="An open case cannot reopen.",
                    expected_case_version=2,
                    idempotency_key="ws03-05b-prohibited-open-reopen",
                ),
            )
        assert reopen_conflict.value.status_code == 409
        assert reopen_conflict.value.detail["code"] == "review_case_transition_conflict"
        assert review_case_side_effect_snapshot(db, review_case.id) == before_reopen

        assigned = assign_review_case(
            db,
            review_case_id=review_case.id,
            admin_user=admin,
            payload=AdminReviewCaseAssignment(
                assignee_user_id=admin.id,
                reason="Initial assignment.",
                expected_case_version=2,
                idempotency_key="ws03-05b-prohibited-assignment-prepare",
            ),
        )
        before_noop = review_case_side_effect_snapshot(db, review_case.id)
        with pytest.raises(HTTPException) as assignment_conflict:
            assign_review_case(
                db,
                review_case_id=review_case.id,
                admin_user=admin,
                payload=AdminReviewCaseAssignment(
                    assignee_user_id=admin.id,
                    reason="A new key cannot turn an unchanged assignment into an event.",
                    expected_case_version=assigned.resulting_case_version,
                    idempotency_key="ws03-05b-prohibited-assignment-noop",
                ),
            )
        assert assignment_conflict.value.status_code == 409
        assert assignment_conflict.value.detail["code"] == (
            "review_case_transition_conflict"
        )
        assert review_case_side_effect_snapshot(db, review_case.id) == before_noop


@pytest.mark.requirement("WS03-05B-R2", "WS03-05B-R3", "WS03-05B-R4")
def test_merge_rejects_incompatible_identity_without_writes() -> None:
    with session() as db:
        source_game = seed_game(db)
        destination_game = seed_game(db)
        admin = seed_admin(db)
        source = create_content_case(db, source_game)
        destination = create_content_case(db, destination_game)
        before = review_case_side_effect_snapshot(db, source.id, destination.id)

        with pytest.raises(HTTPException) as conflict:
            merge_review_case(
                db,
                source_case_id=source.id,
                admin_user=admin,
                payload=AdminReviewCaseMerge(
                    destination_case_id=destination.id,
                    reason="Different target identities cannot merge.",
                    expected_source_version=2,
                    expected_destination_version=2,
                    idempotency_key="ws03-05b-prohibited-incompatible-merge",
                ),
            )
        assert conflict.value.status_code == 409
        assert conflict.value.detail["code"] == "review_case_transition_conflict"
        assert review_case_side_effect_snapshot(db, source.id, destination.id) == before


@pytest.mark.requirement("WS03-05B-R2", "WS03-05B-R3")
def test_note_correction_cannot_cross_case_boundary() -> None:
    with session() as db:
        game = seed_game(db)
        admin = seed_admin(db)
        content_case = create_content_case(db, game)
        chat_case = create_chat_case(db, game)
        note = add_review_case_note(
            db,
            review_case_id=content_case.id,
            admin_user=admin,
            payload=AdminReviewCaseNoteCreate(
                body="Content-case note.",
                expected_case_version=2,
                idempotency_key="ws03-05b-content-note",
            ),
        )
        before_notes = db.scalar(select(func.count(AdminReviewCaseNote.id)))
        before_actions = db.scalar(select(func.count(AdminAction.id)))
        before_events = len(event_rows(db, chat_case.id))

        with pytest.raises(HTTPException) as conflict:
            add_review_case_note(
                db,
                review_case_id=chat_case.id,
                admin_user=admin,
                payload=AdminReviewCaseNoteCreate(
                    body="Invalid cross-case correction.",
                    corrects_note_id=note.note.id,
                    expected_case_version=2,
                    idempotency_key="ws03-05b-cross-case-note",
                ),
            )
        assert conflict.value.status_code == 400
        db.rollback()
        assert db.scalar(select(func.count(AdminReviewCaseNote.id))) == before_notes
        assert db.scalar(select(func.count(AdminAction.id))) == before_actions
        assert len(event_rows(db, chat_case.id)) == before_events


@pytest.mark.requirement("WS03-05B-R2", "WS03-05B-R3", "WS03-05B-R5")
def test_automatic_enforcement_closure_requires_a_genuine_linked_action() -> None:
    with session() as db:
        game = seed_game(db)
        review_case = create_content_case(db, game)
        game.deleted_at = datetime.now(timezone.utc)
        db.add(game)
        before = review_case_side_effect_snapshot(db, review_case.id)

        with pytest.raises(ValueError, match="lifecycle transition is invalid"):
            close_open_content_moderation_case_for_game_lifecycle(
                db,
                game_id=game.id,
                closure_outcome="enforcement_applied",
                closure_reason="An unattributed deletion cannot claim enforcement.",
                lifecycle_action="admin_soft_deleted",
                trigger_actor_type="admin",
                trigger_actor_user_id=game.host_user_id,
                closed_by_user_id=game.host_user_id,
                previous_game_status="active",
                new_game_status="soft_deleted",
            )

        assert review_case_side_effect_snapshot(db, review_case.id) == before


@pytest.mark.requirement("WS03-05B-R2", "WS03-05B-R3", "WS03-05B-R5")
@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    (
        ("lifecycle_action", "host_cancelled"),
        ("previous_target_state", "completed"),
        ("new_target_state", "cancelled"),
        ("trigger_actor_type", "system"),
        ("trigger_actor_user_id", None),
        ("closed_by_user_id", None),
        ("closure_outcome", "enforcement_applied"),
    ),
)
def test_automatic_lifecycle_service_matrix_rejects_each_contradictory_dimension(
    field_name: str,
    invalid_value: object,
) -> None:
    actor_id = uuid.uuid4()
    values = {
        "target_type": "community_game",
        "lifecycle_action": "admin_soft_deleted",
        "previous_target_state": "active",
        "new_target_state": "soft_deleted",
        "trigger_actor_type": "admin",
        "trigger_actor_user_id": actor_id,
        "closed_by_user_id": actor_id,
        "closure_outcome": "no_action_needed",
        "admin_action": None,
    }
    values[field_name] = invalid_value

    with pytest.raises(ValueError, match="Automatic closure"):
        validate_automatic_content_lifecycle_transition(**values)


@pytest.mark.requirement("WS03-05B-R2", "WS03-05B-R3", "WS03-05B-R5")
def test_automatic_target_lifecycle_closure_is_attributed_and_idempotent() -> None:
    with session() as db:
        game = seed_game(db)
        admin = seed_admin(db)
        review_case = create_content_case(db, game)
        assign_review_case(
            db,
            review_case_id=review_case.id,
            admin_user=admin,
            payload=AdminReviewCaseAssignment(
                assignee_user_id=admin.id,
                reason="Claim before lifecycle transition.",
                expected_case_version=2,
                idempotency_key="ws03-05b-auto-close-assign",
            ),
        )

        game = db.get(type(game), game.id)
        game.deleted_at = datetime.now(timezone.utc)
        db.add(game)
        closed = close_open_content_moderation_case_for_game_lifecycle(
            db,
            game_id=game.id,
            closure_outcome="no_action_needed",
            closure_reason="Game was cancelled before review completed.",
            lifecycle_action="admin_soft_deleted",
            trigger_actor_type="admin",
            trigger_actor_user_id=admin.id,
            closed_by_user_id=admin.id,
            previous_game_status="active",
            new_game_status="soft_deleted",
        )
        db.commit()
        assert closed is not None
        assert closed.case_status == "closed"
        assert closed.case_version == 4
        assert closed.closure_mode == "automatic"
        assert closed.closure_rule_id == TARGET_LIFECYCLE_RULE_ID
        assert closed.closure_rule_version == TARGET_LIFECYCLE_RULE_VERSION
        assert closed.assigned_to_user_id is None

        events = event_rows(db, review_case.id)
        assert events[-1].event_type == "closed"
        assert events[-1].actor_kind == "automation"
        assert events[-1].automation_rule_id == TARGET_LIFECYCLE_RULE_ID
        assert events[-1].event_metadata["previous_assignee_id"] == str(admin.id)
        assert events[-1].event_metadata["new_target_state"] == "soft_deleted"
        detail = serialize_review_case_detail(db, closed)
        assert len(detail.resolution_history) == 1
        automatic_history = detail.resolution_history[0]
        assert automatic_history.mode == "automatic"
        assert automatic_history.reason == "Game was cancelled before review completed."
        assert automatic_history.automation_rule_id == TARGET_LIFECYCLE_RULE_ID
        assert (
            automatic_history.automation_rule_version == TARGET_LIFECYCLE_RULE_VERSION
        )
        references = list(
            db.scalars(
                select(AdminReviewCaseResolutionReference).where(
                    AdminReviewCaseResolutionReference.closure_event_id == events[-1].id
                )
            ).all()
        )
        assert [
            (reference.reference_type, reference.was_current)
            for reference in references
        ] == [("finding", True)]

        assert (
            close_open_content_moderation_case_for_game_lifecycle(
                db,
                game_id=game.id,
                closure_outcome="no_action_needed",
                closure_reason="Repeated lifecycle callback.",
                lifecycle_action="admin_soft_deleted",
                trigger_actor_type="admin",
                trigger_actor_user_id=admin.id,
                closed_by_user_id=admin.id,
                previous_game_status="active",
                new_game_status="soft_deleted",
            )
            is None
        )
        assert len(event_rows(db, review_case.id)) == 4


@pytest.mark.requirement("WS03-05B-R2", "WS03-05B-R3", "WS03-05B-R4")
def test_merge_preserves_source_resolution_and_child_ownership() -> None:
    with session() as db:
        game = seed_game(db)
        admin = seed_admin(db)
        source = create_content_case(db, game)
        source_finding_ids = set(
            db.scalars(
                select(AdminContentModerationFinding.id).where(
                    AdminContentModerationFinding.review_case_id == source.id
                )
            ).all()
        )
        close_review_case(
            db,
            review_case_id=source.id,
            admin_user=admin,
            payload=AdminReviewCaseClose(
                outcome="no_action_needed",
                reason="Close the first historical case.",
                expected_case_version=2,
                idempotency_key="ws03-05b-close-merge-source",
            ),
        )
        source_closure = db.scalar(
            select(AdminReviewCaseEvent).where(
                AdminReviewCaseEvent.review_case_id == source.id,
                AdminReviewCaseEvent.event_type == "closed",
            )
        )
        source_resolution = (
            source.closure_outcome,
            source.closure_reason,
            source.closure_mode,
            source.closure_rule_id,
            source.closure_rule_version,
            source.closed_by_user_id,
            source.closed_at,
        )

        game.description = "Text me at 214-555-0100"
        db.commit()
        surface_community_game_text(db, game_id=game.id)
        destination = db.scalar(
            select(AdminReviewCase).where(
                AdminReviewCase.target_game_id == game.id,
                AdminReviewCase.case_status == "open",
                AdminReviewCase.case_category == "content_moderation",
            )
        )
        result = merge_review_case(
            db,
            source_case_id=source.id,
            admin_user=admin,
            payload=AdminReviewCaseMerge(
                destination_case_id=destination.id,
                reason="Link duplicate historical work.",
                expected_source_version=3,
                expected_destination_version=2,
                idempotency_key="ws03-05b-merge-history",
            ),
        )
        assert result.resulting_source_version == 4
        assert result.resulting_destination_version == 3
        assert result.source_case.closure_mode == "manual"
        assert result.source_case.closure_outcome == "no_action_needed"
        assert result.source_case.merged_into_case_id == destination.id
        assert result.destination_case.case_status == "open"
        assert result.source_case.linked_cases[0].relation == "merged_into"
        assert result.destination_case.linked_cases[0].relation == "merged_from"
        assert (
            result.source_case.closure_outcome,
            result.source_case.closure_reason,
            result.source_case.closure_mode,
            result.source_case.closure_rule_id,
            result.source_case.closure_rule_version,
            result.source_case.closed_by_user_id,
            result.source_case.closed_at,
        ) == source_resolution
        assert len(result.source_case.resolution_history) == 1
        assert (
            result.source_case.resolution_history[0].closure_event_id
            == source_closure.id
        )
        assert result.source_case.resolution_history[0].reason == source_resolution[1]

        assert (
            set(
                db.scalars(
                    select(AdminContentModerationFinding.id).where(
                        AdminContentModerationFinding.review_case_id == source.id
                    )
                ).all()
            )
            == source_finding_ids
        )
        source_merge_event = result.source_case.events[-1]
        destination_merge_event = result.destination_case.events[-1]
        assert source_merge_event.event_type == "merged_into"
        assert source_merge_event.related_case_id == destination.id
        assert source_merge_event.related_event_id == source_closure.id
        assert destination_merge_event.event_type == "merged_from"
        assert destination_merge_event.related_case_id == source.id
        assert destination_merge_event.related_event_id == source_merge_event.id
        assert source_merge_event.event_metadata == {
            "source_resolution_mode": "manual",
            "source_resolution_outcome": "no_action_needed",
        }
        assert (
            destination_merge_event.event_metadata == source_merge_event.event_metadata
        )

        with pytest.raises(HTTPException) as reopen_conflict:
            reopen_review_case(
                db,
                review_case_id=source.id,
                admin_user=admin,
                payload=AdminReviewCaseReopen(
                    reason="Merged sources are terminal.",
                    expected_case_version=4,
                    idempotency_key="ws03-05b-reopen-merged-source",
                ),
            )
        assert reopen_conflict.value.status_code == 409


@pytest.mark.requirement("WS03-05B-R2", "WS03-05B-R4")
def test_merge_rejects_chains_and_cycles_without_persisting_partial_state() -> None:
    with session() as db:
        game = seed_game(db)
        admin = seed_admin(db)
        first = create_content_case(db, game)
        close_review_case(
            db,
            review_case_id=first.id,
            admin_user=admin,
            payload=AdminReviewCaseClose(
                outcome="no_action_needed",
                reason="Close first source.",
                expected_case_version=2,
                idempotency_key="ws03-05b-chain-close-first",
            ),
        )
        game.description = "Text me at 214-555-0100"
        db.commit()
        surface_community_game_text(db, game_id=game.id)
        middle = db.scalar(
            select(AdminReviewCase).where(
                AdminReviewCase.target_game_id == game.id,
                AdminReviewCase.case_status == "open",
                AdminReviewCase.case_category == "content_moderation",
            )
        )
        merge_review_case(
            db,
            source_case_id=first.id,
            admin_user=admin,
            payload=AdminReviewCaseMerge(
                destination_case_id=middle.id,
                reason="Establish one source link.",
                expected_source_version=3,
                expected_destination_version=2,
                idempotency_key="ws03-05b-chain-first-middle",
            ),
        )
        close_review_case(
            db,
            review_case_id=middle.id,
            admin_user=admin,
            payload=AdminReviewCaseClose(
                outcome="no_action_needed",
                reason="Close destination before new evidence.",
                expected_case_version=3,
                idempotency_key="ws03-05b-chain-close-middle",
            ),
        )
        game.description = "Call 312-555-1212"
        db.commit()
        surface_community_game_text(db, game_id=game.id)
        destination = db.scalar(
            select(AdminReviewCase).where(
                AdminReviewCase.target_game_id == game.id,
                AdminReviewCase.case_status == "open",
                AdminReviewCase.case_category == "content_moderation",
            )
        )
        action_count = db.scalar(select(func.count(AdminAction.id)))
        event_count = db.scalar(select(func.count(AdminReviewCaseEvent.id)))

        with pytest.raises(HTTPException) as chain_conflict:
            merge_review_case(
                db,
                source_case_id=middle.id,
                admin_user=admin,
                payload=AdminReviewCaseMerge(
                    destination_case_id=destination.id,
                    reason="A destination with sources cannot become a source.",
                    expected_source_version=4,
                    expected_destination_version=2,
                    idempotency_key="ws03-05b-reject-merge-chain",
                ),
            )
        assert chain_conflict.value.status_code == 409

        with pytest.raises(HTTPException) as cycle_conflict:
            merge_review_case(
                db,
                source_case_id=first.id,
                admin_user=admin,
                payload=AdminReviewCaseMerge(
                    destination_case_id=destination.id,
                    reason="A merged source cannot merge again.",
                    expected_source_version=4,
                    expected_destination_version=2,
                    idempotency_key="ws03-05b-reject-merge-cycle",
                ),
            )
        assert cycle_conflict.value.status_code == 409
        assert db.get(AdminReviewCase, first.id).merged_into_case_id == middle.id
        assert db.get(AdminReviewCase, middle.id).merged_into_case_id is None
        assert db.get(AdminReviewCase, destination.id).case_status == "open"
        assert db.scalar(select(func.count(AdminAction.id))) == action_count
        assert db.scalar(select(func.count(AdminReviewCaseEvent.id))) == event_count


@pytest.mark.requirement("WS03-05B-R2", "WS03-05B-R3")
def test_enforcement_resolution_uses_direct_and_merged_source_actions() -> None:
    with session() as db:
        admin = seed_admin(db)

        direct_game = seed_game(db)
        direct_case = create_content_case(db, direct_game)
        direct_action, direct_case = link_game_enforcement_action(
            db,
            admin=admin,
            game=direct_game,
            idempotency_key="ws03-05b-direct-enforcement-action",
        )
        direct_result = close_review_case(
            db,
            review_case_id=direct_case.id,
            admin_user=admin,
            payload=AdminReviewCaseClose(
                outcome="enforcement_applied",
                reason="Resolve from direct enforcement.",
                expected_case_version=3,
                idempotency_key="ws03-05b-close-direct-enforcement",
            ),
        )
        assert direct_action.id in {
            reference.admin_action_id
            for reference in direct_result.review_case.resolution_references
        }

        merged_game = seed_game(db)
        source = create_content_case(db, merged_game)
        source_action, source = link_game_enforcement_action(
            db,
            admin=admin,
            game=merged_game,
            idempotency_key="ws03-05b-source-enforcement-action",
        )
        close_review_case(
            db,
            review_case_id=source.id,
            admin_user=admin,
            payload=AdminReviewCaseClose(
                outcome="no_action_needed",
                reason="Close source before merge.",
                expected_case_version=3,
                idempotency_key="ws03-05b-close-source-before-merge",
            ),
        )
        merged_game.description = "Text me at 214-555-0100"
        db.commit()
        surface_community_game_text(db, game_id=merged_game.id)
        destination = db.scalar(
            select(AdminReviewCase).where(
                AdminReviewCase.target_game_id == merged_game.id,
                AdminReviewCase.case_status == "open",
                AdminReviewCase.case_category == "content_moderation",
            )
        )
        merge_result = merge_review_case(
            db,
            source_case_id=source.id,
            admin_user=admin,
            payload=AdminReviewCaseMerge(
                destination_case_id=destination.id,
                reason="Preserve source enforcement attribution.",
                expected_source_version=4,
                expected_destination_version=2,
                idempotency_key="ws03-05b-merge-enforcement-source",
            ),
        )
        merged_result = close_review_case(
            db,
            review_case_id=destination.id,
            admin_user=admin,
            payload=AdminReviewCaseClose(
                outcome="enforcement_applied",
                reason="Resolve from merged-source enforcement.",
                expected_case_version=merge_result.resulting_destination_version,
                idempotency_key="ws03-05b-close-merged-enforcement",
            ),
        )
        assert source_action.id in {
            reference.admin_action_id
            for reference in merged_result.review_case.resolution_references
        }

        absent_game = seed_game(db)
        absent_case = create_content_case(db, absent_game)
        with pytest.raises(HTTPException) as absent_conflict:
            close_review_case(
                db,
                review_case_id=absent_case.id,
                admin_user=admin,
                payload=AdminReviewCaseClose(
                    outcome="enforcement_applied",
                    reason="Must reject without enforcement.",
                    expected_case_version=2,
                    idempotency_key="ws03-05b-close-absent-enforcement",
                ),
            )
        assert absent_conflict.value.status_code == 409
        assert db.get(AdminReviewCase, absent_case.id).case_status == "open"


@pytest.mark.requirement("WS03-05B-R2", "WS03-05B-R4")
def test_ineligible_assignment_cannot_strand_an_open_case() -> None:
    with session() as db:
        game = seed_game(db)
        resolver = seed_admin(db, "resolver")
        former_admin = seed_admin(db, "former")
        review_case = create_content_case(db, game)
        assign_review_case(
            db,
            review_case_id=review_case.id,
            admin_user=resolver,
            payload=AdminReviewCaseAssignment(
                assignee_user_id=former_admin.id,
                reason="Initial assignment.",
                expected_case_version=2,
                idempotency_key="ws03-05b-former-admin-assignment",
            ),
        )
        former_admin.role = "player"
        db.commit()

        result = close_review_case(
            db,
            review_case_id=review_case.id,
            admin_user=resolver,
            payload=AdminReviewCaseClose(
                outcome="no_action_needed",
                reason="Resolve after assignee lost eligibility.",
                expected_case_version=3,
                idempotency_key="ws03-05b-ineligible-assignee-close",
            ),
        )
        assert result.review_case.case_status == "closed"
        assert result.review_case.assigned_to_user_id is None
        assert result.review_case.events[-1].event_metadata[
            "previous_assignee_id"
        ] == str(former_admin.id)
        assert result.review_case.events[-1].event_metadata["after"] == {
            "case_status": "closed",
            "closure_outcome": "no_action_needed",
        }


@pytest.mark.requirement("WS03-05B-R3", "WS03-05B-R6")
def test_detail_serializes_durable_note_corrections_and_resolution_history() -> None:
    with session() as db:
        game = seed_game(db)
        admin = seed_admin(db)
        review_case = create_content_case(db, game)
        first = add_review_case_note(
            db,
            review_case_id=review_case.id,
            admin_user=admin,
            payload=AdminReviewCaseNoteCreate(
                body="Original note.",
                expected_case_version=2,
                idempotency_key="ws03-05b-detail-note-one",
            ),
        )
        add_review_case_note(
            db,
            review_case_id=review_case.id,
            admin_user=admin,
            payload=AdminReviewCaseNoteCreate(
                body="Correction note.",
                corrects_note_id=first.note.id,
                expected_case_version=3,
                idempotency_key="ws03-05b-detail-note-two",
            ),
        )
        close_review_case(
            db,
            review_case_id=review_case.id,
            admin_user=admin,
            payload=AdminReviewCaseClose(
                outcome="no_action_needed",
                reason="Close after correction.",
                expected_case_version=4,
                idempotency_key="ws03-05b-detail-close",
            ),
        )

        detail = serialize_review_case_detail(
            db, db.get(AdminReviewCase, review_case.id)
        )
        assert detail.notes[1].corrects_note_id == detail.notes[0].id
        assert [event.event_sequence for event in detail.events] == list(range(1, 6))
        assert detail.resolution_references
        assert len(detail.resolution_history) == 1
        assert detail.resolution_history[0].reason == "Close after correction."
        assert detail.resolution_history[0].references == detail.resolution_references
        assert all(
            reference.closure_event_id == detail.events[-1].id
            for reference in detail.resolution_references
        )
