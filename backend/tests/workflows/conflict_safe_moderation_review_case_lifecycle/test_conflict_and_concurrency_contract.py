from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import event, func, select

from backend.models import (
    AdminAction,
    AdminContentModerationFinding,
    AdminReviewCase,
    AdminReviewCaseEvent,
    AdminReviewCaseNote,
    AdminReviewCaseResolutionReference,
    AdminReviewSignal,
    User,
)
from backend.schemas.admin_review_schema import (
    AdminReviewCaseAssignment,
    AdminReviewCaseClose,
    AdminReviewCaseMerge,
    AdminReviewCaseNoteCreate,
    AdminReviewCaseReopen,
)
from backend.services.admin_review_service import (
    add_review_case_note,
    assign_review_case,
    close_open_content_moderation_case_for_game_lifecycle,
    close_review_case,
    create_internal_review_signal,
    is_retryable_chat_review_case_creation_race,
    lock_eligible_admin_ids,
    merge_review_case,
    reopen_review_case,
    review_integrity_constraint_name,
)
from backend.services.moderation_surfacing_service import surface_community_game_text
from backend.tests.workflows.conflict_safe_moderation_review_case_lifecycle.conftest import (
    create_content_case,
    seed_admin,
    seed_game,
    session,
)

pytestmark = pytest.mark.suite_type("ordinary")


def run_with_target_lock_barrier(first, second):
    from backend.database import engine

    first_locked = threading.Event()
    second_attempted = threading.Event()
    release_first = threading.Event()

    def before_cursor_execute(
        conn, cursor, statement, parameters, context, executemany
    ) -> None:
        del conn, cursor, parameters, context, executemany
        if (
            threading.current_thread().name.startswith("review-second")
            and "FROM games" in statement
            and "FOR UPDATE" in statement
        ):
            second_attempted.set()

    def after_cursor_execute(
        conn, cursor, statement, parameters, context, executemany
    ) -> None:
        del conn, cursor, parameters, context, executemany
        if (
            threading.current_thread().name.startswith("review-first")
            and not first_locked.is_set()
            and "FROM games" in statement
            and "FOR UPDATE" in statement
        ):
            first_locked.set()
            assert release_first.wait(timeout=10)

    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    event.listen(engine, "after_cursor_execute", after_cursor_execute)
    try:
        with (
            ThreadPoolExecutor(
                max_workers=1,
                thread_name_prefix="review-first",
            ) as first_executor,
            ThreadPoolExecutor(
                max_workers=1,
                thread_name_prefix="review-second",
            ) as second_executor,
        ):
            first_future = first_executor.submit(first)
            assert first_locked.wait(timeout=5)
            second_future = second_executor.submit(second)
            assert second_attempted.wait(timeout=5)
            release_first.set()
            return first_future.result(timeout=15), second_future.result(timeout=15)
    finally:
        release_first.set()
        event.remove(engine, "before_cursor_execute", before_cursor_execute)
        event.remove(engine, "after_cursor_execute", after_cursor_execute)


def run_with_assignee_lock_barrier(first, second):
    from backend.database import engine

    first_locked = threading.Event()
    second_attempted = threading.Event()
    release_first = threading.Event()

    def before_cursor_execute(
        conn, cursor, statement, parameters, context, executemany
    ) -> None:
        del conn, cursor, parameters, context, executemany
        if (
            threading.current_thread().name.startswith("assignee-second")
            and "FROM users" in statement
            and "FOR UPDATE" in statement
        ):
            second_attempted.set()

    def after_cursor_execute(
        conn, cursor, statement, parameters, context, executemany
    ) -> None:
        del conn, cursor, parameters, context, executemany
        if (
            threading.current_thread().name.startswith("assignee-first")
            and not first_locked.is_set()
            and "FROM users" in statement
            and "FOR UPDATE" in statement
        ):
            first_locked.set()
            assert release_first.wait(timeout=10)

    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    event.listen(engine, "after_cursor_execute", after_cursor_execute)
    try:
        with (
            ThreadPoolExecutor(
                max_workers=1,
                thread_name_prefix="assignee-first",
            ) as first_executor,
            ThreadPoolExecutor(
                max_workers=1,
                thread_name_prefix="assignee-second",
            ) as second_executor,
        ):
            first_future = first_executor.submit(first)
            assert first_locked.wait(timeout=5)
            second_future = second_executor.submit(second)
            assert second_attempted.wait(timeout=5)
            release_first.set()
            return first_future.result(timeout=15), second_future.result(timeout=15)
    finally:
        release_first.set()
        event.remove(engine, "before_cursor_execute", before_cursor_execute)
        event.remove(engine, "after_cursor_execute", after_cursor_execute)


def capture_conflict(operation):
    try:
        return operation()
    except HTTPException as exc:
        return exc


@pytest.mark.requirement("WS03-05B-R3", "WS03-05B-R4")
def test_reversed_assignee_inputs_lock_in_one_database_order() -> None:
    with session() as db:
        first_admin = seed_admin(db, "lock-first")
        second_admin = seed_admin(db, "lock-second")
        first_admin_id = first_admin.id
        second_admin_id = second_admin.id

    def lock_assignees(first_id, second_id):
        with session() as db:
            locked_ids = lock_eligible_admin_ids(db, {first_id, second_id})
            db.commit()
            return locked_ids

    forward, reversed_ = run_with_assignee_lock_barrier(
        lambda: lock_assignees(first_admin_id, second_admin_id),
        lambda: lock_assignees(second_admin_id, first_admin_id),
    )
    expected = {first_admin_id, second_admin_id}
    assert forward == expected
    assert reversed_ == expected


@pytest.mark.requirement("WS03-05B-R4")
def test_stale_and_mismatched_idempotency_conflicts_have_no_side_effects() -> None:
    with session() as db:
        game = seed_game(db)
        admin = seed_admin(db)
        review_case = create_content_case(db, game)
        assignment_payload = AdminReviewCaseAssignment(
            assignee_user_id=admin.id,
            reason="Claim the review.",
            expected_case_version=2,
            idempotency_key="ws03-05b-conflict-assignment",
        )
        assign_review_case(
            db,
            review_case_id=review_case.id,
            admin_user=admin,
            payload=assignment_payload,
        )
        before_notes = db.scalar(select(func.count(AdminReviewCaseNote.id)))
        before_actions = db.scalar(select(func.count(AdminAction.id)))
        before_events = db.scalar(
            select(func.count(AdminReviewCaseEvent.id)).where(
                AdminReviewCaseEvent.review_case_id == review_case.id
            )
        )

        sensitive_note = "PRIVATE NOTE CONTENT MUST NOT APPEAR"
        with pytest.raises(HTTPException) as stale:
            add_review_case_note(
                db,
                review_case_id=review_case.id,
                admin_user=admin,
                payload=AdminReviewCaseNoteCreate(
                    body=sensitive_note,
                    expected_case_version=2,
                    idempotency_key="ws03-05b-stale-note",
                ),
            )
        assert stale.value.status_code == 409
        assert stale.value.detail["code"] == "review_case_version_conflict"
        assert set(stale.value.detail["current"]) == {
            "id",
            "case_status",
            "case_version",
            "priority",
            "assigned_to_user_id",
            "closure_outcome",
            "merged_into_case_id",
            "updated_at",
        }
        assert sensitive_note not in str(stale.value.detail)
        db.rollback()

        with pytest.raises(HTTPException) as mismatch:
            assign_review_case(
                db,
                review_case_id=review_case.id,
                admin_user=admin,
                payload=assignment_payload.model_copy(
                    update={"reason": "Reuse the key with different input."}
                ),
            )
        assert mismatch.value.detail["code"] == "review_case_idempotency_conflict"
        assert db.scalar(select(func.count(AdminReviewCaseNote.id))) == before_notes
        assert db.scalar(select(func.count(AdminAction.id))) == before_actions
        assert (
            db.scalar(
                select(func.count(AdminReviewCaseEvent.id)).where(
                    AdminReviewCaseEvent.review_case_id == review_case.id
                )
            )
            == before_events
        )


@pytest.mark.requirement("WS03-05B-R3", "WS03-05B-R4")
def test_note_and_resolution_race_has_one_versioned_winner() -> None:
    with session() as db:
        game = seed_game(db)
        admin = seed_admin(db)
        game_id = game.id
        admin_id = admin.id
        review_case_id = create_content_case(db, game).id

    def write_note():
        with session() as db:
            return add_review_case_note(
                db,
                review_case_id=review_case_id,
                admin_user=db.get(User, admin_id),
                payload=AdminReviewCaseNoteCreate(
                    body="Concurrent note wins first.",
                    expected_case_version=2,
                    idempotency_key="ws03-05b-race-note",
                ),
            )

    def resolve_case():
        with session() as db:
            return capture_conflict(
                lambda: close_review_case(
                    db,
                    review_case_id=review_case_id,
                    admin_user=db.get(User, admin_id),
                    payload=AdminReviewCaseClose(
                        outcome="no_action_needed",
                        reason="Concurrent close loses on version.",
                        expected_case_version=2,
                        idempotency_key="ws03-05b-race-close",
                    ),
                )
            )

    note_result, close_result = run_with_target_lock_barrier(write_note, resolve_case)
    assert note_result.resulting_case_version == 3
    assert isinstance(close_result, HTTPException)
    assert close_result.detail["code"] == "review_case_version_conflict"

    with session() as db:
        review_case = db.get(AdminReviewCase, review_case_id)
        assert review_case.target_game_id == game_id
        assert review_case.case_status == "open"
        assert review_case.case_version == 3
        assert db.scalar(select(func.count(AdminReviewCaseNote.id))) == 1
        assert (
            db.scalar(
                select(func.count(AdminAction.id)).where(
                    AdminAction.target_review_case_id == review_case_id
                )
            )
            == 1
        )
        events = list(
            db.scalars(
                select(AdminReviewCaseEvent)
                .where(AdminReviewCaseEvent.review_case_id == review_case_id)
                .order_by(AdminReviewCaseEvent.event_sequence.asc())
            ).all()
        )
        assert [item.event_sequence for item in events] == [1, 2, 3]
        assert events[-1].event_type == "note_added"


@pytest.mark.requirement("WS03-05B-R4")
def test_concurrent_exact_note_replay_creates_one_note_action_and_event() -> None:
    with session() as db:
        game = seed_game(db)
        admin = seed_admin(db)
        admin_id = admin.id
        review_case_id = create_content_case(db, game).id

    payload = AdminReviewCaseNoteCreate(
        body="Idempotent concurrent note.",
        expected_case_version=2,
        idempotency_key="ws03-05b-concurrent-note-replay",
    )

    def add_note():
        with session() as db:
            return add_review_case_note(
                db,
                review_case_id=review_case_id,
                admin_user=db.get(User, admin_id),
                payload=payload,
            )

    first, second = run_with_target_lock_barrier(add_note, add_note)
    assert sorted((first.idempotent_replay, second.idempotent_replay)) == [False, True]
    assert first.note.id == second.note.id
    assert first.resulting_case_version == second.resulting_case_version == 3

    with session() as db:
        assert db.scalar(select(func.count(AdminReviewCaseNote.id))) == 1
        assert (
            db.scalar(
                select(func.count(AdminAction.id)).where(
                    AdminAction.action_type == "add_review_case_note"
                )
            )
            == 1
        )
        assert (
            db.scalar(
                select(func.count(AdminReviewCaseEvent.id)).where(
                    AdminReviewCaseEvent.review_case_id == review_case_id,
                    AdminReviewCaseEvent.event_type == "note_added",
                )
            )
            == 1
        )


@pytest.mark.requirement("WS03-05B-R1", "WS03-05B-R4", "WS03-05B-R5")
def test_concurrent_chat_creation_converges_on_one_case_signal_and_history() -> None:
    with session() as db:
        game_id = seed_game(db).id

    idempotency_key = "ws03-05b-concurrent-chat-identity"

    def create_signal():
        with session() as db:
            return create_internal_review_signal(
                db,
                signal_category="chat_moderation",
                source="chat_moderation",
                priority="urgent",
                title="Concurrent chat signal",
                summary="One deterministic chat trigger.",
                target_data={"target_game_id": game_id},
                metadata={"current_match": True},
                idempotency_key=idempotency_key,
            )

    first, second = run_with_target_lock_barrier(create_signal, create_signal)
    assert first[0].id == second[0].id
    assert first[1].id == second[1].id
    assert sorted((first[3], second[3])) == [False, True]

    with session() as db:
        review_case = db.scalar(
            select(AdminReviewCase).where(
                AdminReviewCase.target_game_id == game_id,
                AdminReviewCase.case_category == "chat_moderation",
            )
        )
        assert review_case.case_version == 2
        assert db.scalar(select(func.count(AdminReviewCase.id))) == 1
        assert db.scalar(select(func.count(AdminReviewSignal.id))) == 1
        events = list(
            db.scalars(
                select(AdminReviewCaseEvent)
                .where(AdminReviewCaseEvent.review_case_id == review_case.id)
                .order_by(AdminReviewCaseEvent.event_sequence.asc())
            ).all()
        )
        assert [item.event_type for item in events] == [
            "case_created",
            "signal_attached",
        ]


@pytest.mark.requirement("WS03-05B-R1", "WS03-05B-R4", "WS03-05B-R5")
def test_concurrent_saved_content_creation_converges_on_one_case_and_finding() -> None:
    with session() as db:
        game_id = seed_game(db).id

    def surface_content():
        with session() as db:
            return surface_community_game_text(db, game_id=game_id)

    first, second = run_with_target_lock_barrier(surface_content, surface_content)
    assert first is None
    assert second is None

    with session() as db:
        review_case = db.scalar(
            select(AdminReviewCase).where(
                AdminReviewCase.target_game_id == game_id,
                AdminReviewCase.case_category == "content_moderation",
            )
        )
        assert review_case.case_version == 2
        assert db.scalar(select(func.count(AdminReviewCase.id))) == 1
        assert db.scalar(select(func.count(AdminContentModerationFinding.id))) == 1
        events = list(
            db.scalars(
                select(AdminReviewCaseEvent)
                .where(AdminReviewCaseEvent.review_case_id == review_case.id)
                .order_by(AdminReviewCaseEvent.event_sequence.asc())
            ).all()
        )
        assert [item.event_type for item in events] == [
            "case_created",
            "finding_attached",
        ]


@pytest.mark.requirement("WS03-05B-R3", "WS03-05B-R4", "WS03-05B-R5")
def test_finding_attachment_and_closure_race_has_no_post_close_attachment() -> None:
    with session() as db:
        game = seed_game(db)
        admin = seed_admin(db)
        game_id = game.id
        admin_id = admin.id
        review_case_id = create_content_case(db, game).id
        game.description = "Call 214-555-0199 instead."
        db.commit()

    def attach_new_finding():
        with session() as db:
            return surface_community_game_text(db, game_id=game_id)

    def resolve_case():
        with session() as db:
            return capture_conflict(
                lambda: close_review_case(
                    db,
                    review_case_id=review_case_id,
                    admin_user=db.get(User, admin_id),
                    payload=AdminReviewCaseClose(
                        outcome="no_action_needed",
                        reason="Concurrent close must reconsider new evidence.",
                        expected_case_version=2,
                        idempotency_key="ws03-05b-attachment-close-race",
                    ),
                )
            )

    surface_result, close_result = run_with_target_lock_barrier(
        attach_new_finding, resolve_case
    )
    assert surface_result is None
    assert isinstance(close_result, HTTPException)
    assert close_result.detail["code"] == "review_case_version_conflict"

    with session() as db:
        review_case = db.get(AdminReviewCase, review_case_id)
        assert review_case.case_status == "open"
        assert review_case.case_version == 4
        assert (
            db.scalar(
                select(func.count(AdminAction.id)).where(
                    AdminAction.action_type == "close_review_case",
                    AdminAction.target_review_case_id == review_case_id,
                )
            )
            == 0
        )
        events = list(
            db.scalars(
                select(AdminReviewCaseEvent)
                .where(AdminReviewCaseEvent.review_case_id == review_case_id)
                .order_by(AdminReviewCaseEvent.event_sequence.asc())
            ).all()
        )
        assert [item.event_sequence for item in events] == [1, 2, 3, 4]
        assert [item.event_type for item in events][-2:] == [
            "finding_attached",
            "finding_cleared",
        ]


@pytest.mark.requirement("WS03-05B-R3", "WS03-05B-R4")
def test_assignment_and_resolution_race_has_one_versioned_winner() -> None:
    with session() as db:
        game = seed_game(db)
        admin = seed_admin(db)
        admin_id = admin.id
        review_case_id = create_content_case(db, game).id

    def assign_case():
        with session() as db:
            return assign_review_case(
                db,
                review_case_id=review_case_id,
                admin_user=db.get(User, admin_id),
                payload=AdminReviewCaseAssignment(
                    assignee_user_id=admin_id,
                    reason="Claim before resolving.",
                    expected_case_version=2,
                    idempotency_key="ws03-05b-assignment-resolution-race",
                ),
            )

    def resolve_case():
        with session() as db:
            return capture_conflict(
                lambda: close_review_case(
                    db,
                    review_case_id=review_case_id,
                    admin_user=db.get(User, admin_id),
                    payload=AdminReviewCaseClose(
                        outcome="no_action_needed",
                        reason="Concurrent resolution must use the new version.",
                        expected_case_version=2,
                        idempotency_key="ws03-05b-assignment-close-race",
                    ),
                )
            )

    assignment_result, close_result = run_with_target_lock_barrier(
        assign_case, resolve_case
    )
    assert assignment_result.resulting_case_version == 3
    assert isinstance(close_result, HTTPException)
    assert close_result.detail["code"] == "review_case_version_conflict"

    with session() as db:
        review_case = db.get(AdminReviewCase, review_case_id)
        assert review_case.case_status == "open"
        assert review_case.case_version == 3
        assert review_case.assigned_to_user_id == admin_id
        assert (
            db.scalar(
                select(func.count(AdminAction.id)).where(
                    AdminAction.target_review_case_id == review_case_id
                )
            )
            == 1
        )
        assert (
            db.scalar(
                select(func.count(AdminReviewCaseEvent.id)).where(
                    AdminReviewCaseEvent.review_case_id == review_case_id,
                    AdminReviewCaseEvent.event_type == "assignment_changed",
                )
            )
            == 1
        )


@pytest.mark.requirement("WS03-05B-R2", "WS03-05B-R3", "WS03-05B-R4")
def test_merge_and_destination_assignment_race_has_one_versioned_winner() -> None:
    with session() as db:
        game = seed_game(db)
        admin = seed_admin(db)
        admin_id = admin.id
        source = create_content_case(db, game)
        close_review_case(
            db,
            review_case_id=source.id,
            admin_user=admin,
            payload=AdminReviewCaseClose(
                outcome="no_action_needed",
                reason="Prepare merge source.",
                expected_case_version=2,
                idempotency_key="ws03-05b-merge-race-source-close",
            ),
        )
        source_id = source.id
        game.description = "Call 214-555-0177."
        db.commit()
        surface_community_game_text(db, game_id=game.id)
        destination = db.scalar(
            select(AdminReviewCase).where(
                AdminReviewCase.target_game_id == game.id,
                AdminReviewCase.case_category == "content_moderation",
                AdminReviewCase.case_status == "open",
            )
        )
        destination_id = destination.id

    def merge_cases():
        with session() as db:
            return merge_review_case(
                db,
                source_case_id=source_id,
                admin_user=db.get(User, admin_id),
                payload=AdminReviewCaseMerge(
                    destination_case_id=destination_id,
                    reason="Merge historical review into current work.",
                    expected_source_version=3,
                    expected_destination_version=2,
                    idempotency_key="ws03-05b-merge-assignment-race",
                ),
            )

    def assign_destination():
        with session() as db:
            return capture_conflict(
                lambda: assign_review_case(
                    db,
                    review_case_id=destination_id,
                    admin_user=db.get(User, admin_id),
                    payload=AdminReviewCaseAssignment(
                        assignee_user_id=admin_id,
                        reason="Concurrent destination assignment.",
                        expected_case_version=2,
                        idempotency_key="ws03-05b-merge-race-assignment",
                    ),
                )
            )

    merge_result, assignment_result = run_with_target_lock_barrier(
        merge_cases, assign_destination
    )
    assert merge_result.resulting_source_version == 4
    assert merge_result.resulting_destination_version == 3
    assert isinstance(assignment_result, HTTPException)
    assert assignment_result.detail["code"] == "review_case_version_conflict"

    with session() as db:
        source = db.get(AdminReviewCase, source_id)
        destination = db.get(AdminReviewCase, destination_id)
        assert source.merged_into_case_id == destination_id
        assert source.case_version == 4
        assert destination.case_status == "open"
        assert destination.case_version == 3
        assert destination.assigned_to_user_id is None
        merge_actions = db.scalar(
            select(func.count(AdminAction.id)).where(
                AdminAction.action_type == "merge_review_case",
                AdminAction.target_review_case_id == source_id,
            )
        )
        assert merge_actions == 1
        assert (
            db.scalar(
                select(func.count(AdminReviewCaseEvent.id)).where(
                    AdminReviewCaseEvent.event_type.in_(("merged_into", "merged_from")),
                    AdminReviewCaseEvent.review_case_id.in_(
                        (source_id, destination_id)
                    ),
                )
            )
            == 2
        )


@pytest.mark.requirement("WS03-05B-R4", "WS03-05B-R5")
def test_manual_and_automatic_resolution_race_has_one_truthful_closure() -> None:
    with session() as db:
        game = seed_game(db)
        admin = seed_admin(db)
        game_id = game.id
        admin_id = admin.id
        review_case_id = create_content_case(db, game).id
        game.deleted_at = datetime.now(timezone.utc)
        db.commit()

    def manual_close():
        with session() as db:
            return close_review_case(
                db,
                review_case_id=review_case_id,
                admin_user=db.get(User, admin_id),
                payload=AdminReviewCaseClose(
                    outcome="no_action_needed",
                    reason="Manual decision wins the target lock.",
                    expected_case_version=2,
                    idempotency_key="ws03-05b-human-auto-race",
                ),
            )

    def automatic_close():
        with session() as db:
            result = close_open_content_moderation_case_for_game_lifecycle(
                db,
                game_id=game_id,
                closure_outcome="no_action_needed",
                closure_reason="Deleted target is no longer actionable.",
                lifecycle_action="admin_soft_deleted",
                trigger_actor_type="admin",
                trigger_actor_user_id=admin_id,
                closed_by_user_id=admin_id,
                previous_game_status="active",
                new_game_status="soft_deleted",
            )
            db.commit()
            return result

    manual_result, automatic_result = run_with_target_lock_barrier(
        manual_close, automatic_close
    )
    assert manual_result.review_case.closure_mode == "manual"
    assert automatic_result is None

    with session() as db:
        review_case = db.get(AdminReviewCase, review_case_id)
        assert review_case.case_status == "closed"
        assert review_case.case_version == 3
        assert review_case.closure_mode == "manual"
        closure_events = list(
            db.scalars(
                select(AdminReviewCaseEvent).where(
                    AdminReviewCaseEvent.review_case_id == review_case_id,
                    AdminReviewCaseEvent.event_type == "closed",
                )
            ).all()
        )
        assert len(closure_events) == 1
        assert closure_events[0].actor_kind == "admin"


@pytest.mark.requirement("WS03-05B-R4", "WS03-05B-R5")
@pytest.mark.parametrize("case_category", ("content_moderation", "chat_moderation"))
@pytest.mark.parametrize("winner", ("reopen", "source_creation"))
def test_reopen_and_source_creation_converge_for_both_winner_orders(
    case_category: str,
    winner: str,
) -> None:
    with session() as db:
        game = seed_game(db)
        admin = seed_admin(db)
        game_id = game.id
        admin_id = admin.id
        if case_category == "content_moderation":
            review_case = create_content_case(db, game)
            initial_source_id = db.scalar(
                select(AdminContentModerationFinding.id).where(
                    AdminContentModerationFinding.review_case_id == review_case.id
                )
            )
        else:
            review_case, signal, _created, _replayed = create_internal_review_signal(
                db,
                signal_category="chat_moderation",
                source="chat_moderation",
                priority="urgent",
                title="Initial chat review signal",
                summary="Initial deterministic chat signal.",
                target_data={"target_game_id": game.id},
                metadata={"current_match": True},
                idempotency_key=f"ws03-05b-{case_category}-initial-signal",
            )
            initial_source_id = signal.id
        close_review_case(
            db,
            review_case_id=review_case.id,
            admin_user=admin,
            payload=AdminReviewCaseClose(
                outcome="no_action_needed",
                reason="Prepare deterministic reopen race.",
                expected_case_version=2,
                idempotency_key=f"ws03-05b-{case_category}-{winner}-close",
            ),
        )
        review_case_id = review_case.id
        game.description = "Text me at 214-555-0100"
        db.commit()

    def reopen():
        with session() as db:
            return capture_conflict(
                lambda: reopen_review_case(
                    db,
                    review_case_id=review_case_id,
                    admin_user=db.get(User, admin_id),
                    payload=AdminReviewCaseReopen(
                        reason="Compete with a new source record.",
                        expected_case_version=3,
                        idempotency_key=(f"ws03-05b-{case_category}-{winner}-reopen"),
                    ),
                )
            )

    def create_from_source():
        with session() as db:
            if case_category == "content_moderation":
                surface_community_game_text(db, game_id=game_id)
                return None
            return create_internal_review_signal(
                db,
                signal_category="chat_moderation",
                source="chat_moderation",
                priority="critical",
                title="New chat review signal",
                summary="New deterministic chat signal.",
                target_data={"target_game_id": game_id},
                metadata={"current_match": True},
                idempotency_key=f"ws03-05b-{case_category}-{winner}-new-signal",
            )

    if winner == "reopen":
        reopen_result, source_result = run_with_target_lock_barrier(
            reopen, create_from_source
        )
        assert not isinstance(reopen_result, HTTPException)
    else:
        source_result, reopen_result = run_with_target_lock_barrier(
            create_from_source, reopen
        )
        assert isinstance(reopen_result, HTTPException)
        assert reopen_result.detail["code"] == "review_case_open_identity_conflict"

    with session() as db:
        cases = list(
            db.scalars(
                select(AdminReviewCase).where(
                    AdminReviewCase.target_game_id == game_id,
                    AdminReviewCase.case_category == case_category,
                )
            ).all()
        )
        open_cases = [item for item in cases if item.case_status == "open"]
        assert len(open_cases) == 1
        open_case = open_cases[0]
        if winner == "reopen":
            assert len(cases) == 1
            assert open_case.id == review_case_id
        else:
            assert len(cases) == 2
            assert open_case.id != review_case_id
            historical_case = db.get(AdminReviewCase, review_case_id)
            assert historical_case.case_status == "closed"
            assert historical_case.case_version == 3

        if case_category == "content_moderation":
            assert source_result is None
            findings = list(
                db.scalars(
                    select(AdminContentModerationFinding)
                    .where(
                        AdminContentModerationFinding.review_case_id.in_(
                            [item.id for item in cases]
                        )
                    )
                    .order_by(AdminContentModerationFinding.first_detected_at.asc())
                ).all()
            )
            assert len(findings) == 2
            assert findings[0].id == initial_source_id
            if winner == "reopen":
                assert {finding.review_case_id for finding in findings} == {
                    review_case_id
                }
                assert [finding.current_match for finding in findings].count(True) == 1
                assert findings[0].current_match is False
                assert findings[1].current_match is True
            else:
                assert {
                    (finding.review_case_id, finding.current_match)
                    for finding in findings
                } == {
                    (review_case_id, True),
                    (open_case.id, True),
                }
            assert (
                db.scalar(
                    select(func.count(AdminReviewSignal.id)).where(
                        AdminReviewSignal.review_case_id.in_(
                            [item.id for item in cases]
                        )
                    )
                )
                == 0
            )
        else:
            source_case, source_signal, created_case, replayed = source_result
            assert source_case.id == open_case.id
            assert source_signal.review_case_id == open_case.id
            assert created_case is (winner == "source_creation")
            assert replayed is False
            signals = list(
                db.scalars(
                    select(AdminReviewSignal)
                    .where(
                        AdminReviewSignal.review_case_id.in_(
                            [item.id for item in cases]
                        )
                    )
                    .order_by(
                        AdminReviewSignal.created_at.asc(), AdminReviewSignal.id.asc()
                    )
                ).all()
            )
            assert len(signals) == 2
            assert signals[0].id == initial_source_id
            expected_ownership = (
                {review_case_id}
                if winner == "reopen"
                else {review_case_id, open_case.id}
            )
            assert {signal.review_case_id for signal in signals} == expected_ownership
            assert all(
                signal.metadata_.get("current_match") is True for signal in signals
            )
            assert (
                db.scalar(
                    select(func.count(AdminContentModerationFinding.id)).where(
                        AdminContentModerationFinding.review_case_id.in_(
                            [item.id for item in cases]
                        )
                    )
                )
                == 0
            )

        reopen_actions = db.scalar(
            select(func.count(AdminAction.id)).where(
                AdminAction.target_review_case_id == review_case_id,
                AdminAction.action_type == "reopen_review_case",
            )
        )
        reopen_events = db.scalar(
            select(func.count(AdminReviewCaseEvent.id)).where(
                AdminReviewCaseEvent.review_case_id == review_case_id,
                AdminReviewCaseEvent.event_type == "reopened",
            )
        )
        assert reopen_actions == (1 if winner == "reopen" else 0)
        assert reopen_events == (1 if winner == "reopen" else 0)
        assert (
            db.scalar(
                select(func.count(AdminReviewCaseResolutionReference.id))
                .join(
                    AdminReviewCaseEvent,
                    AdminReviewCaseEvent.id
                    == AdminReviewCaseResolutionReference.closure_event_id,
                )
                .where(AdminReviewCaseEvent.review_case_id == review_case_id)
            )
            == 1
        )
        assert db.scalar(
            select(func.count(AdminAction.id)).where(
                AdminAction.target_review_case_id.in_([item.id for item in cases]),
                AdminAction.action_type == "reopen_review_case",
            )
        ) == (1 if winner == "reopen" else 0)
        assert db.scalar(
            select(func.count(AdminReviewCaseEvent.id)).where(
                AdminReviewCaseEvent.review_case_id.in_([item.id for item in cases]),
                AdminReviewCaseEvent.event_type == "reopened",
            )
        ) == (1 if winner == "reopen" else 0)
        expected_versions = (
            {"content_moderation": 6, "chat_moderation": 5}
            if winner == "reopen"
            else None
        )
        for case in cases:
            sequences = list(
                db.scalars(
                    select(AdminReviewCaseEvent.event_sequence)
                    .where(AdminReviewCaseEvent.review_case_id == case.id)
                    .order_by(AdminReviewCaseEvent.event_sequence.asc())
                ).all()
            )
            assert sequences == list(range(1, case.case_version + 1))
        if expected_versions is not None:
            assert open_case.case_version == expected_versions[case_category]
        else:
            assert open_case.case_version == 2


@pytest.mark.requirement("WS03-05B-R3", "WS03-05B-R4")
def test_assignment_and_reassignment_race_has_one_versioned_winner() -> None:
    with session() as db:
        game = seed_game(db)
        actor = seed_admin(db, "assignment-race-actor")
        first_assignee = seed_admin(db, "assignment-race-first")
        second_assignee = seed_admin(db, "assignment-race-second")
        third_assignee = seed_admin(db, "assignment-race-third")
        review_case = create_content_case(db, game)
        assigned = assign_review_case(
            db,
            review_case_id=review_case.id,
            admin_user=actor,
            payload=AdminReviewCaseAssignment(
                assignee_user_id=first_assignee.id,
                reason="Prepare competing reassignments.",
                expected_case_version=2,
                idempotency_key="ws03-05b-reassignment-race-prepare",
            ),
        )
        review_case_id = review_case.id
        actor_id = actor.id
        second_assignee_id = second_assignee.id
        third_assignee_id = third_assignee.id

    def reassign(assignee_id, idempotency_key):
        with session() as db:
            return capture_conflict(
                lambda: assign_review_case(
                    db,
                    review_case_id=review_case_id,
                    admin_user=db.get(User, actor_id),
                    payload=AdminReviewCaseAssignment(
                        assignee_user_id=assignee_id,
                        reason="Competing reassignment.",
                        expected_case_version=assigned.resulting_case_version,
                        idempotency_key=idempotency_key,
                    ),
                )
            )

    winner, loser = run_with_target_lock_barrier(
        lambda: reassign(second_assignee_id, "ws03-05b-reassignment-race-first"),
        lambda: reassign(third_assignee_id, "ws03-05b-reassignment-race-second"),
    )
    assert winner.resulting_case_version == 4
    assert isinstance(loser, HTTPException)
    assert loser.detail["code"] == "review_case_version_conflict"

    with session() as db:
        review_case = db.get(AdminReviewCase, review_case_id)
        assert review_case.case_version == 4
        assert review_case.assigned_to_user_id == second_assignee_id
        assert (
            db.scalar(
                select(func.count(AdminAction.id)).where(
                    AdminAction.target_review_case_id == review_case_id,
                    AdminAction.action_type == "assign_review_case",
                )
            )
            == 2
        )
        assert (
            db.scalar(
                select(func.count(AdminReviewCaseEvent.id)).where(
                    AdminReviewCaseEvent.review_case_id == review_case_id,
                    AdminReviewCaseEvent.event_type == "assignment_changed",
                )
            )
            == 2
        )


def seed_merge_race_fixture():
    with session() as db:
        game = seed_game(db)
        admin = seed_admin(db, "merge-race-admin")
        source = create_content_case(db, game)
        closed = close_review_case(
            db,
            review_case_id=source.id,
            admin_user=admin,
            payload=AdminReviewCaseClose(
                outcome="no_action_needed",
                reason="Prepare historical merge source.",
                expected_case_version=2,
                idempotency_key=f"ws03-05b-merge-race-close:{source.id}",
            ),
        )
        game.description = "Call 214-555-0177."
        db.commit()
        surface_community_game_text(db, game_id=game.id)
        destination = db.scalar(
            select(AdminReviewCase).where(
                AdminReviewCase.target_game_id == game.id,
                AdminReviewCase.case_category == "content_moderation",
                AdminReviewCase.case_status == "open",
            )
        )
        return (
            admin.id,
            source.id,
            closed.resulting_case_version,
            destination.id,
            destination.case_version,
        )


@pytest.mark.requirement("WS03-05B-R2", "WS03-05B-R3", "WS03-05B-R4")
def test_merge_and_reopen_race_has_one_versioned_winner() -> None:
    admin_id, source_id, source_version, destination_id, destination_version = (
        seed_merge_race_fixture()
    )

    def merge_cases():
        with session() as db:
            return merge_review_case(
                db,
                source_case_id=source_id,
                admin_user=db.get(User, admin_id),
                payload=AdminReviewCaseMerge(
                    destination_case_id=destination_id,
                    reason="Merge wins before reopen.",
                    expected_source_version=source_version,
                    expected_destination_version=destination_version,
                    idempotency_key="ws03-05b-merge-reopen-race-merge",
                ),
            )

    def reopen_source():
        with session() as db:
            return capture_conflict(
                lambda: reopen_review_case(
                    db,
                    review_case_id=source_id,
                    admin_user=db.get(User, admin_id),
                    payload=AdminReviewCaseReopen(
                        reason="Concurrent reopen must lose after merge.",
                        expected_case_version=source_version,
                        idempotency_key="ws03-05b-merge-reopen-race-reopen",
                    ),
                )
            )

    merge_result, reopen_result = run_with_target_lock_barrier(
        merge_cases, reopen_source
    )
    assert merge_result.resulting_source_version == source_version + 1
    assert isinstance(reopen_result, HTTPException)
    assert reopen_result.detail["code"] == "review_case_version_conflict"

    with session() as db:
        source = db.get(AdminReviewCase, source_id)
        assert source.merged_into_case_id == destination_id
        assert source.case_status == "closed"
        assert (
            db.scalar(
                select(func.count(AdminAction.id)).where(
                    AdminAction.target_review_case_id == source_id,
                    AdminAction.action_type == "reopen_review_case",
                )
            )
            == 0
        )
        assert (
            db.scalar(
                select(func.count(AdminReviewCaseEvent.id)).where(
                    AdminReviewCaseEvent.review_case_id == source_id,
                    AdminReviewCaseEvent.event_type == "reopened",
                )
            )
            == 0
        )


@pytest.mark.requirement("WS03-05B-R2", "WS03-05B-R3", "WS03-05B-R4")
def test_merge_and_destination_resolution_race_has_one_versioned_winner() -> None:
    admin_id, source_id, source_version, destination_id, destination_version = (
        seed_merge_race_fixture()
    )

    def merge_cases():
        with session() as db:
            return merge_review_case(
                db,
                source_case_id=source_id,
                admin_user=db.get(User, admin_id),
                payload=AdminReviewCaseMerge(
                    destination_case_id=destination_id,
                    reason="Merge wins before destination resolution.",
                    expected_source_version=source_version,
                    expected_destination_version=destination_version,
                    idempotency_key="ws03-05b-merge-close-race-merge",
                ),
            )

    def close_destination():
        with session() as db:
            return capture_conflict(
                lambda: close_review_case(
                    db,
                    review_case_id=destination_id,
                    admin_user=db.get(User, admin_id),
                    payload=AdminReviewCaseClose(
                        outcome="no_action_needed",
                        reason="Concurrent close must use the merged version.",
                        expected_case_version=destination_version,
                        idempotency_key="ws03-05b-merge-close-race-close",
                    ),
                )
            )

    merge_result, close_result = run_with_target_lock_barrier(
        merge_cases, close_destination
    )
    assert merge_result.resulting_destination_version == destination_version + 1
    assert isinstance(close_result, HTTPException)
    assert close_result.detail["code"] == "review_case_version_conflict"

    with session() as db:
        destination = db.get(AdminReviewCase, destination_id)
        assert destination.case_status == "open"
        assert destination.case_version == destination_version + 1
        assert (
            db.scalar(
                select(func.count(AdminAction.id)).where(
                    AdminAction.target_review_case_id == destination_id,
                    AdminAction.action_type == "close_review_case",
                )
            )
            == 0
        )
        assert (
            db.scalar(
                select(func.count(AdminReviewCaseEvent.id)).where(
                    AdminReviewCaseEvent.review_case_id == destination_id,
                    AdminReviewCaseEvent.event_type == "closed",
                )
            )
            == 0
        )


@pytest.mark.requirement("WS03-05B-R3", "WS03-05B-R4", "WS03-05B-R5")
def test_signal_attachment_and_closure_race_has_no_post_close_attachment() -> None:
    with session() as db:
        game = seed_game(db)
        admin = seed_admin(db, "signal-close-race-admin")
        review_case, _signal, _created, _replayed = create_internal_review_signal(
            db,
            signal_category="chat_moderation",
            source="chat_moderation",
            priority="urgent",
            title="Initial chat signal",
            summary="Initial deterministic chat signal.",
            target_data={"target_game_id": game.id},
            metadata={"current_match": True},
            idempotency_key="ws03-05b-signal-close-race-initial",
        )
        game_id = game.id
        admin_id = admin.id
        review_case_id = review_case.id
        expected_version = review_case.case_version

    def attach_signal():
        with session() as db:
            return create_internal_review_signal(
                db,
                signal_category="chat_moderation",
                source="chat_moderation",
                priority="urgent",
                title="Concurrent chat signal",
                summary="Attachment wins the target lock.",
                target_data={"target_game_id": game_id},
                metadata={"current_match": True},
                idempotency_key="ws03-05b-signal-close-race-attachment",
            )

    def close_case():
        with session() as db:
            return capture_conflict(
                lambda: close_review_case(
                    db,
                    review_case_id=review_case_id,
                    admin_user=db.get(User, admin_id),
                    payload=AdminReviewCaseClose(
                        outcome="no_action_needed",
                        reason="Concurrent close must reconsider the new signal.",
                        expected_case_version=expected_version,
                        idempotency_key="ws03-05b-signal-close-race-close",
                    ),
                )
            )

    signal_result, close_result = run_with_target_lock_barrier(
        attach_signal, close_case
    )
    assert signal_result[0].case_version == expected_version + 1
    assert isinstance(close_result, HTTPException)
    assert close_result.detail["code"] == "review_case_version_conflict"

    with session() as db:
        review_case = db.get(AdminReviewCase, review_case_id)
        assert review_case.case_status == "open"
        assert review_case.case_version == expected_version + 1
        assert (
            db.scalar(
                select(func.count(AdminReviewSignal.id)).where(
                    AdminReviewSignal.review_case_id == review_case_id
                )
            )
            == 2
        )
        assert (
            db.scalar(
                select(func.count(AdminAction.id)).where(
                    AdminAction.target_review_case_id == review_case_id,
                    AdminAction.action_type == "close_review_case",
                )
            )
            == 0
        )
        assert (
            db.scalar(
                select(func.count(AdminReviewCaseEvent.id)).where(
                    AdminReviewCaseEvent.review_case_id == review_case_id,
                    AdminReviewCaseEvent.event_type == "signal_attached",
                )
            )
            == 2
        )


def synthetic_integrity_error(constraint_name: str):
    from sqlalchemy.exc import IntegrityError

    original = RuntimeError("synthetic integrity failure")
    original.diag = type("Diagnostic", (), {"constraint_name": constraint_name})()
    return IntegrityError("INSERT", {}, original)


@pytest.mark.requirement("WS03-05B-R4")
def test_chat_creation_retry_classification_is_operation_specific() -> None:
    retryable = {
        "uq_admin_review_cases_open_community_game_moderation",
        "uq_admin_review_cases_open_need_sub_moderation",
        "uq_admin_review_signals_source_idempotency_key",
    }
    for name in retryable:
        error = synthetic_integrity_error(name)
        assert review_integrity_constraint_name(error) == name
        assert is_retryable_chat_review_case_creation_race(error)
    for name in (
        "uq_admin_actions_review_case_idempotency",
        "uq_admin_content_moderation_findings_current_identity",
        "ck_admin_review_case_events_reference_shape",
        "fk_admin_review_case_notes_review_case_id",
        "uq_admin_review_case_events_case_sequence",
        "uq_unrelated_constraint",
    ):
        assert not is_retryable_chat_review_case_creation_race(
            synthetic_integrity_error(name)
        )


@pytest.mark.requirement("WS03-05B-R4")
def test_chat_creation_does_not_retry_an_unrelated_integrity_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with session() as db:
        game = seed_game(db)
        commit_calls = 0

        def fail_commit() -> None:
            nonlocal commit_calls
            commit_calls += 1
            raise synthetic_integrity_error(
                "ck_admin_review_case_events_reference_shape"
            )

        monkeypatch.setattr(db, "commit", fail_commit)
        with pytest.raises(HTTPException) as conflict:
            create_internal_review_signal(
                db,
                signal_category="chat_moderation",
                source="chat_moderation",
                priority="urgent",
                title="Chat review signal",
                summary="Review persisted chat moderation evidence.",
                target_data={"target_game_id": game.id},
                metadata={"current_match": True},
                idempotency_key="ws03-05b-nonretryable-chat-integrity",
            )
        assert conflict.value.status_code == 409
        assert commit_calls == 1
        assert (
            db.scalar(
                select(func.count(AdminReviewCase.id)).where(
                    AdminReviewCase.target_game_id == game.id
                )
            )
            == 0
        )
