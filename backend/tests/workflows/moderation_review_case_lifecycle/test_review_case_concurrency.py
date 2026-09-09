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
    AdminReviewSignal,
    User,
)
from backend.schemas.admin_review_schema import (
    AdminReviewCaseClose,
    AdminReviewCaseNoteCreate,
)
from backend.services.admin_action_service import record_admin_action
from backend.services.admin_review_service import (
    add_review_case_note,
    close_open_content_moderation_case_for_game_lifecycle,
    close_review_case,
    create_internal_review_signal,
    link_admin_action_to_open_review_case,
)
from backend.services.content_moderation_scanner_service import (
    ModerationFinding,
    ScanProvenance,
)
from backend.services.moderation_signal_service import surface_moderation_findings
from backend.services.moderation_surfacing_service import surface_community_game_text
from backend.tests.workflows.moderation_review_case_lifecycle.conftest import (
    create_chat_case,
    create_content_case,
    run_with_target_lock_barrier,
    seed_admin,
    seed_game,
    session,
)

pytestmark = pytest.mark.suite_type("ordinary")


def capture_conflict(operation):
    try:
        return operation()
    except HTTPException as exc:
        return exc


def build_concurrent_chat_finding(content_hash: str) -> ModerationFinding:
    return ModerationFinding(
        signal_category="chat_moderation",
        moderation_domain="chat_risk",
        detected_categories=("harassment_or_abuse",),
        severity="critical",
        priority="critical",
        field_name="message_body",
        field_label="Message",
        excerpt="Synthetic concurrent moderation evidence.",
        content_hash=content_hash,
        matched_rule_ids=("chat-harassment",),
        matched_rule_versions=({"rule_id": "chat-harassment", "rule_version": "1"},),
        provenance=ScanProvenance(
            scanner_id="moderation-taxonomy",
            scanner_version="1",
            taxonomy_version="1",
            configuration_hash="synthetic-configuration",
            canonicalization_version="1",
            evidence_format_version="1",
            target_context="game_chat_message",
            declared_limits=(),
            scanned_at=datetime(2038, 3, 1, 18, tzinfo=timezone.utc),
            execution_duration_us=1,
        ),
    )


def event_types(db, case_id: uuid.UUID) -> list[str]:
    return list(
        db.scalars(
            select(AdminReviewCaseEvent.event_type)
            .where(AdminReviewCaseEvent.review_case_id == case_id)
            .order_by(AdminReviewCaseEvent.case_version.asc())
        ).all()
    )


def event_rows(db, case_id: uuid.UUID) -> list[AdminReviewCaseEvent]:
    return list(
        db.scalars(
            select(AdminReviewCaseEvent)
            .where(AdminReviewCaseEvent.review_case_id == case_id)
            .order_by(AdminReviewCaseEvent.case_version.asc())
        ).all()
    )


def row_count(db, model, *conditions) -> int:
    return db.scalar(select(func.count(model.id)).where(*conditions)) or 0


@pytest.mark.parametrize("source_kind", ("content", "chat"))
def test_concurrent_case_creation_reuses_one_open_identity(source_kind: str) -> None:
    with session() as db:
        game_id = seed_game(db).id

    def create_source():
        with session() as db:
            if source_kind == "content":
                surface_community_game_text(db, game_id=game_id)
                return None
            return create_internal_review_signal(
                db,
                signal_category="chat_moderation",
                source="chat_moderation",
                priority="urgent",
                title="Concurrent signal",
                summary="Same deterministic source.",
                target_data={"target_game_id": game_id},
                metadata={"current_match": True},
                idempotency_key="concurrent-chat-creation",
            )

    first, second = run_with_target_lock_barrier(create_source, create_source)
    if source_kind == "chat":
        assert first[0].id == second[0].id
        assert first[1].id == second[1].id
        assert sorted((first[3], second[3])) == [False, True]

    with session() as db:
        category = f"{source_kind}_moderation"
        review_case = db.scalar(
            select(AdminReviewCase).where(
                AdminReviewCase.target_game_id == game_id,
                AdminReviewCase.case_category == category,
                AdminReviewCase.case_status == "open",
            )
        )
        assert review_case.case_version == 2
        assert review_case.case_status == "open"
        assert review_case.case_type == "community_game"
        assert review_case.case_category == category
        assert (
            row_count(
                db,
                AdminReviewCase,
                AdminReviewCase.target_game_id == game_id,
                AdminReviewCase.case_category == category,
            )
            == 1
        )
        assert event_types(db, review_case.id) == [
            "case_created",
            "finding_attached" if source_kind == "content" else "signal_attached",
        ]
        events = event_rows(db, review_case.id)
        assert [event.case_version for event in events] == [1, 2]
        assert len(events) == 2
        source_model = (
            AdminContentModerationFinding
            if source_kind == "content"
            else AdminReviewSignal
        )
        assert (
            row_count(
                db,
                source_model,
                source_model.review_case_id == review_case.id,
            )
            == 1
        )
        source = db.scalar(
            select(source_model).where(source_model.review_case_id == review_case.id)
        )
        assert source.review_case_id == review_case.id
        assert (
            row_count(
                db,
                AdminAction,
                AdminAction.target_review_case_id == review_case.id,
            )
            == 0
        )
        other_source_model = (
            AdminReviewSignal
            if source_kind == "content"
            else AdminContentModerationFinding
        )
        assert (
            row_count(
                db,
                other_source_model,
                other_source_model.review_case_id == review_case.id,
            )
            == 0
        )


def test_concurrent_different_notes_both_append_in_serial_version_order() -> None:
    with session() as db:
        game = seed_game(db)
        first_admin = seed_admin(db, "note-first")
        second_admin = seed_admin(db, "note-second")
        case_id = create_content_case(db, game).id
        first_admin_id = first_admin.id
        second_admin_id = second_admin.id

    def add_note(admin_id: uuid.UUID, body: str, key: str):
        with session() as db:
            return add_review_case_note(
                db,
                review_case_id=case_id,
                admin_user=db.get(User, admin_id),
                payload=AdminReviewCaseNoteCreate(body=body, idempotency_key=key),
            )

    first, second = run_with_target_lock_barrier(
        lambda: add_note(first_admin_id, "First independent note.", "note-first-key"),
        lambda: add_note(
            second_admin_id, "Second independent note.", "note-second-key"
        ),
    )
    assert first.review_case.case_version == 3
    assert second.review_case.case_version == 4
    with session() as db:
        review_case = db.get(AdminReviewCase, case_id)
        assert review_case.case_status == "open"
        assert review_case.case_version == 4
        assert (
            row_count(
                db,
                AdminReviewCaseNote,
                AdminReviewCaseNote.review_case_id == case_id,
            )
            == 2
        )
        assert event_types(db, case_id) == [
            "case_created",
            "finding_attached",
            "note_added",
            "note_added",
        ]
        events = event_rows(db, case_id)
        notes = list(
            db.scalars(
                select(AdminReviewCaseNote)
                .where(AdminReviewCaseNote.review_case_id == case_id)
                .order_by(AdminReviewCaseNote.created_at.asc())
            ).all()
        )
        assert review_case.case_category == "content_moderation"
        assert [event.case_version for event in events] == [1, 2, 3, 4]
        assert {event.note_id for event in events if event.note_id} == {
            note.id for note in notes
        }
        assert (
            row_count(
                db,
                AdminAction,
                AdminAction.target_review_case_id == case_id,
                AdminAction.action_type == "add_review_case_note",
            )
            == 2
        )
        assert (
            row_count(
                db,
                AdminAction,
                AdminAction.target_review_case_id == case_id,
                AdminAction.action_type == "close_review_case",
            )
            == 0
        )
        assert (
            row_count(
                db,
                AdminContentModerationFinding,
                AdminContentModerationFinding.review_case_id == case_id,
            )
            == 1
        )
        assert (
            row_count(
                db,
                AdminReviewSignal,
                AdminReviewSignal.review_case_id == case_id,
            )
            == 0
        )


@pytest.mark.parametrize("winner", ("note", "close"))
def test_note_and_manual_close_have_one_serial_winner(winner: str) -> None:
    with session() as db:
        game = seed_game(db)
        admin = seed_admin(db, f"note-close-{winner}")
        case_id = create_content_case(db, game).id
        admin_id = admin.id

    def write_note():
        with session() as db:
            return capture_conflict(
                lambda: add_review_case_note(
                    db,
                    review_case_id=case_id,
                    admin_user=db.get(User, admin_id),
                    payload=AdminReviewCaseNoteCreate(
                        body="Concurrent note.",
                        idempotency_key=f"note-close-note-{winner}",
                    ),
                )
            )

    def close_case():
        with session() as db:
            return capture_conflict(
                lambda: close_review_case(
                    db,
                    review_case_id=case_id,
                    admin_user=db.get(User, admin_id),
                    payload=AdminReviewCaseClose(
                        outcome="no_action_needed",
                        reason="Concurrent closure.",
                        expected_case_version=2,
                        idempotency_key=f"note-close-close-{winner}",
                    ),
                )
            )

    first_op, second_op = (
        (write_note, close_case) if winner == "note" else (close_case, write_note)
    )
    first, second = run_with_target_lock_barrier(first_op, second_op)
    assert not isinstance(first, HTTPException)
    assert isinstance(second, HTTPException)
    assert second.detail["code"] == (
        "review_case_version_conflict"
        if winner == "note"
        else "review_case_transition_conflict"
    )
    with session() as db:
        review_case = db.get(AdminReviewCase, case_id)
        assert review_case.case_version == 3
        assert review_case.case_status == ("open" if winner == "note" else "closed")
        assert row_count(
            db,
            AdminReviewCaseNote,
            AdminReviewCaseNote.review_case_id == case_id,
        ) == (1 if winner == "note" else 0)
        expected_final_event = "note_added" if winner == "note" else "closed"
        assert event_types(db, case_id) == [
            "case_created",
            "finding_attached",
            expected_final_event,
        ]
        events = event_rows(db, case_id)
        assert [event.case_version for event in events] == [1, 2, 3]
        assert review_case.case_category == "content_moderation"
        assert row_count(
            db,
            AdminAction,
            AdminAction.target_review_case_id == case_id,
            AdminAction.action_type == "add_review_case_note",
        ) == (1 if winner == "note" else 0)
        assert row_count(
            db,
            AdminAction,
            AdminAction.target_review_case_id == case_id,
            AdminAction.action_type == "close_review_case",
        ) == (0 if winner == "note" else 1)
        assert (
            row_count(
                db,
                AdminContentModerationFinding,
                AdminContentModerationFinding.review_case_id == case_id,
            )
            == 1
        )
        assert (
            row_count(
                db,
                AdminReviewSignal,
                AdminReviewSignal.review_case_id == case_id,
            )
            == 0
        )
        if winner == "note":
            assert review_case.closed_at is None
        else:
            assert review_case.closed_at is not None


@pytest.mark.parametrize("winner", ("finding", "close"))
def test_finding_change_and_manual_close_preserve_historical_case(winner: str) -> None:
    with session() as db:
        game = seed_game(db)
        admin = seed_admin(db, f"finding-close-{winner}")
        old_case_id = create_content_case(db, game).id
        game_id = game.id
        admin_id = admin.id
        game.description = "Call 214-555-0199 instead."
        db.commit()

    def change_finding():
        with session() as db:
            return surface_community_game_text(db, game_id=game_id)

    def close_case():
        with session() as db:
            return capture_conflict(
                lambda: close_review_case(
                    db,
                    review_case_id=old_case_id,
                    admin_user=db.get(User, admin_id),
                    payload=AdminReviewCaseClose(
                        outcome="no_action_needed",
                        reason="Concurrent finding closure.",
                        expected_case_version=2,
                        idempotency_key=f"finding-close-{winner}",
                    ),
                )
            )

    first_op, second_op = (
        (change_finding, close_case)
        if winner == "finding"
        else (close_case, change_finding)
    )
    first, second = run_with_target_lock_barrier(first_op, second_op)
    assert not isinstance(first, HTTPException)
    if winner == "finding":
        assert isinstance(second, HTTPException)
        assert second.detail["code"] == "review_case_version_conflict"

    with session() as db:
        old_case = db.get(AdminReviewCase, old_case_id)
        if winner == "finding":
            assert old_case.case_status == "open"
            assert old_case.case_version == 4
            assert old_case.case_category == "content_moderation"
            assert (
                row_count(
                    db,
                    AdminReviewCase,
                    AdminReviewCase.target_game_id == game_id,
                    AdminReviewCase.case_category == "content_moderation",
                )
                == 1
            )
            assert event_types(db, old_case_id) == [
                "case_created",
                "finding_attached",
                "finding_attached",
                "finding_cleared",
            ]
            assert [event.case_version for event in event_rows(db, old_case_id)] == [
                1,
                2,
                3,
                4,
            ]
            assert (
                row_count(
                    db,
                    AdminContentModerationFinding,
                    AdminContentModerationFinding.review_case_id == old_case_id,
                )
                == 2
            )
            assert (
                row_count(
                    db,
                    AdminAction,
                    AdminAction.target_review_case_id == old_case_id,
                )
                == 0
            )
        else:
            assert old_case.case_status == "closed"
            assert old_case.case_version == 3
            assert old_case.case_category == "content_moderation"
            new_case = db.scalar(
                select(AdminReviewCase).where(
                    AdminReviewCase.target_game_id == game_id,
                    AdminReviewCase.case_category == "content_moderation",
                    AdminReviewCase.case_status == "open",
                )
            )
            assert new_case is not None
            assert new_case.id != old_case_id
            assert new_case.case_version == 2
            assert new_case.case_status == "open"
            assert new_case.case_category == "content_moderation"
            assert event_types(db, old_case_id) == [
                "case_created",
                "finding_attached",
                "closed",
            ]
            assert event_types(db, new_case.id) == [
                "case_created",
                "finding_attached",
            ]
            assert [event.case_version for event in event_rows(db, old_case_id)] == [
                1,
                2,
                3,
            ]
            assert [event.case_version for event in event_rows(db, new_case.id)] == [
                1,
                2,
            ]
            assert (
                row_count(
                    db,
                    AdminContentModerationFinding,
                    AdminContentModerationFinding.review_case_id == old_case_id,
                )
                == 1
            )
            assert (
                row_count(
                    db,
                    AdminContentModerationFinding,
                    AdminContentModerationFinding.review_case_id == new_case.id,
                )
                == 1
            )
            assert (
                row_count(
                    db,
                    AdminAction,
                    AdminAction.target_review_case_id == old_case_id,
                    AdminAction.action_type == "close_review_case",
                )
                == 1
            )
        assert (
            row_count(
                db,
                AdminReviewSignal,
                AdminReviewSignal.review_case_id.in_([old_case_id]),
            )
            == 0
        )


@pytest.mark.parametrize("winner", ("signal", "close"))
def test_signal_change_and_manual_close_preserve_category_and_history(
    winner: str,
) -> None:
    with session() as db:
        game = seed_game(db)
        admin = seed_admin(db, f"signal-close-{winner}")
        old_case_id = create_chat_case(db, game, key="initial-chat-signal").id
        game_id = game.id
        admin_id = admin.id

    def attach_signal():
        with session() as db:
            content_hash = f"signal-close-source-{winner}"
            return surface_moderation_findings(
                db,
                target_type="community_game_chat",
                target_data={"target_game_id": game_id},
                findings=[build_concurrent_chat_finding(content_hash)],
                scanned_field_hashes={"message_body": content_hash},
            )

    def close_case():
        with session() as db:
            return capture_conflict(
                lambda: close_review_case(
                    db,
                    review_case_id=old_case_id,
                    admin_user=db.get(User, admin_id),
                    payload=AdminReviewCaseClose(
                        outcome="no_action_needed",
                        reason="Concurrent signal closure.",
                        expected_case_version=2,
                        idempotency_key=f"signal-close-{winner}",
                    ),
                )
            )

    first_op, second_op = (
        (attach_signal, close_case)
        if winner == "signal"
        else (close_case, attach_signal)
    )
    first, second = run_with_target_lock_barrier(first_op, second_op)
    assert not isinstance(first, HTTPException)
    if winner == "signal":
        assert isinstance(second, HTTPException)
        assert second.detail["code"] == "review_case_version_conflict"

    with session() as db:
        old_case = db.get(AdminReviewCase, old_case_id)
        if winner == "signal":
            assert old_case.case_status == "open"
            assert old_case.case_version == 3
            assert old_case.case_category == "chat_moderation"
            assert (
                row_count(
                    db,
                    AdminReviewSignal,
                    AdminReviewSignal.review_case_id == old_case_id,
                )
                == 2
            )
            assert event_types(db, old_case_id) == [
                "case_created",
                "signal_attached",
                "signal_attached",
            ]
            assert [event.case_version for event in event_rows(db, old_case_id)] == [
                1,
                2,
                3,
            ]
            assert (
                row_count(
                    db,
                    AdminAction,
                    AdminAction.target_review_case_id == old_case_id,
                )
                == 0
            )
        else:
            assert old_case.case_status == "closed"
            assert old_case.case_version == 3
            assert old_case.case_category == "chat_moderation"
            new_case = db.scalar(
                select(AdminReviewCase).where(
                    AdminReviewCase.target_game_id == game_id,
                    AdminReviewCase.case_category == "chat_moderation",
                    AdminReviewCase.case_status == "open",
                )
            )
            assert new_case is not None
            assert new_case.id != old_case_id
            assert new_case.case_version == 2
            assert new_case.case_status == "open"
            assert new_case.case_category == "chat_moderation"
            assert (
                row_count(
                    db,
                    AdminReviewSignal,
                    AdminReviewSignal.review_case_id == old_case_id,
                )
                == 1
            )
            assert (
                row_count(
                    db,
                    AdminReviewSignal,
                    AdminReviewSignal.review_case_id == new_case.id,
                )
                == 1
            )
            assert event_types(db, old_case_id) == [
                "case_created",
                "signal_attached",
                "closed",
            ]
            assert event_types(db, new_case.id) == [
                "case_created",
                "signal_attached",
            ]
            assert [event.case_version for event in event_rows(db, old_case_id)] == [
                1,
                2,
                3,
            ]
            assert [event.case_version for event in event_rows(db, new_case.id)] == [
                1,
                2,
            ]
            assert (
                row_count(
                    db,
                    AdminAction,
                    AdminAction.target_review_case_id == old_case_id,
                    AdminAction.action_type == "close_review_case",
                )
                == 1
            )
        assert (
            row_count(
                db,
                AdminContentModerationFinding,
                AdminContentModerationFinding.review_case_id == old_case_id,
            )
            == 0
        )


@pytest.mark.parametrize("winner", ("manual", "automatic"))
def test_manual_and_automatic_close_commit_exactly_one_closure(winner: str) -> None:
    with session() as db:
        game = seed_game(db)
        admin = seed_admin(db, f"manual-auto-{winner}")
        case_id = create_content_case(db, game).id
        game_id = game.id
        admin_id = admin.id
        game.deleted_at = datetime.now(timezone.utc)
        db.commit()

    def manual_close():
        with session() as db:
            return capture_conflict(
                lambda: close_review_case(
                    db,
                    review_case_id=case_id,
                    admin_user=db.get(User, admin_id),
                    payload=AdminReviewCaseClose(
                        outcome="no_action_needed",
                        reason="Manual closure.",
                        expected_case_version=2,
                        idempotency_key=f"manual-auto-{winner}",
                    ),
                )
            )

    def automatic_close():
        with session() as db:
            result = close_open_content_moderation_case_for_game_lifecycle(
                db,
                game_id=game_id,
                closure_outcome="no_action_needed",
                closure_reason="Soft-deleted target.",
                lifecycle_action="admin_soft_deleted",
                trigger_actor_type="admin",
                trigger_actor_user_id=admin_id,
                closed_by_user_id=admin_id,
                previous_game_status="active",
                new_game_status="soft_deleted",
            )
            db.commit()
            return result

    first_op, second_op = (
        (manual_close, automatic_close)
        if winner == "manual"
        else (automatic_close, manual_close)
    )
    first, second = run_with_target_lock_barrier(first_op, second_op)
    assert first is not None and not isinstance(first, HTTPException)
    if winner == "manual":
        assert second is None
    else:
        assert isinstance(second, HTTPException)
        assert second.detail["code"] == "review_case_version_conflict"

    with session() as db:
        review_case = db.get(AdminReviewCase, case_id)
        assert review_case.case_status == "closed"
        assert review_case.case_version == 3
        assert (
            row_count(
                db,
                AdminReviewCaseEvent,
                AdminReviewCaseEvent.review_case_id == case_id,
                AdminReviewCaseEvent.event_type == "closed",
            )
            == 1
        )
        events = event_rows(db, case_id)
        assert [event.event_type for event in events] == [
            "case_created",
            "finding_attached",
            "closed",
        ]
        assert [event.case_version for event in events] == [1, 2, 3]
        assert review_case.case_category == "content_moderation"
        assert (
            row_count(
                db,
                AdminReviewCaseNote,
                AdminReviewCaseNote.review_case_id == case_id,
            )
            == 0
        )
        assert (
            row_count(
                db,
                AdminContentModerationFinding,
                AdminContentModerationFinding.review_case_id == case_id,
            )
            == 1
        )
        assert (
            row_count(
                db,
                AdminReviewSignal,
                AdminReviewSignal.review_case_id == case_id,
            )
            == 0
        )
        assert row_count(
            db,
            AdminAction,
            AdminAction.target_review_case_id == case_id,
            AdminAction.action_type == "close_review_case",
        ) == (1 if winner == "manual" else 0)
        if winner == "manual":
            assert events[-1].admin_action_id is not None
            assert events[-1].event_metadata is None
        else:
            assert events[-1].admin_action_id is None
            assert events[-1].event_metadata["closure_source"] == "target_lifecycle"


@pytest.mark.parametrize("winner", ("link", "close"))
def test_enforcement_link_and_close_never_cross_case_or_append_after_close(
    winner: str,
) -> None:
    with session() as db:
        game = seed_game(db)
        admin = seed_admin(db, f"link-close-{winner}")
        case_id = create_content_case(db, game).id
        chat_case_id = create_chat_case(db, game).id
        db.commit()
        admin_id = admin.id
        game_id = game.id
        host_user_id = game.host_user_id

    def link_action():
        with session() as db:
            action = record_admin_action(
                db,
                admin_user_id=admin_id,
                action_type="hide_community_game",
                outcome="succeeded",
                target_game_id=game_id,
                target_user_id=host_user_id,
                reason="Concurrent enforcement.",
                metadata={"source": "concurrency-test"},
                idempotency_key=f"link-action-{winner}",
            )
            linked = link_admin_action_to_open_review_case(db, action)
            db.commit()
            return linked.id if linked is not None else None, action.id

    def close_case():
        with session() as db:
            return capture_conflict(
                lambda: close_review_case(
                    db,
                    review_case_id=case_id,
                    admin_user=db.get(User, admin_id),
                    payload=AdminReviewCaseClose(
                        outcome=(
                            "enforcement_applied"
                            if winner == "link"
                            else "no_action_needed"
                        ),
                        reason="Concurrent enforcement closure.",
                        expected_case_version=2,
                        idempotency_key=f"link-close-{winner}",
                    ),
                )
            )

    first_op, second_op = (
        (link_action, close_case) if winner == "link" else (close_case, link_action)
    )
    first, second = run_with_target_lock_barrier(first_op, second_op)
    if winner == "link":
        linked_case_id, action_id = first
        assert linked_case_id == case_id
        assert isinstance(second, HTTPException)
        assert second.detail["code"] == "review_case_version_conflict"
    else:
        assert not isinstance(first, HTTPException)
        linked_case_id, action_id = second
        assert linked_case_id is None

    with session() as db:
        review_case = db.get(AdminReviewCase, case_id)
        action = db.get(AdminAction, action_id)
        assert db.get(AdminReviewCase, chat_case_id).case_version == 2
        assert event_types(db, chat_case_id) == ["case_created", "signal_attached"]
        assert (
            row_count(
                db,
                AdminReviewSignal,
                AdminReviewSignal.review_case_id == chat_case_id,
            )
            == 1
        )
        assert (
            row_count(
                db,
                AdminReviewCaseNote,
                AdminReviewCaseNote.review_case_id == case_id,
            )
            == 0
        )
        if winner == "link":
            assert review_case.case_status == "open"
            assert review_case.case_version == 3
            assert action.target_review_case_id == case_id
            assert event_types(db, case_id) == [
                "case_created",
                "finding_attached",
                "enforcement_action_linked",
            ]
            assert (
                row_count(
                    db,
                    AdminAction,
                    AdminAction.target_review_case_id == case_id,
                    AdminAction.action_type == "hide_community_game",
                )
                == 1
            )
            assert (
                row_count(
                    db,
                    AdminAction,
                    AdminAction.target_review_case_id == case_id,
                    AdminAction.action_type == "close_review_case",
                )
                == 0
            )
        else:
            assert review_case.case_status == "closed"
            assert review_case.case_version == 3
            assert action.target_review_case_id is None
            assert event_types(db, case_id) == [
                "case_created",
                "finding_attached",
                "closed",
            ]
            assert (
                row_count(
                    db,
                    AdminAction,
                    AdminAction.target_review_case_id == case_id,
                    AdminAction.action_type == "hide_community_game",
                )
                == 0
            )
            assert (
                row_count(
                    db,
                    AdminAction,
                    AdminAction.target_review_case_id == case_id,
                    AdminAction.action_type == "close_review_case",
                )
                == 1
            )
        events = event_rows(db, case_id)
        assert [event.case_version for event in events] == [1, 2, 3]
        assert review_case.case_category == "content_moderation"
        assert (
            row_count(
                db,
                AdminContentModerationFinding,
                AdminContentModerationFinding.review_case_id == case_id,
            )
            == 1
        )
