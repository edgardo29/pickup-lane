from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select

from backend.models import AdminReviewCase, AdminReviewCaseEvent, AdminReviewSignal
from backend.schemas.admin_review_schema import AdminReviewCaseClose
from backend.services import moderation_signal_service
from backend.services.admin_review_service import close_review_case
from backend.services.content_moderation_scanner_service import (
    ModerationFinding,
    ScanProvenance,
)
from backend.services.moderation_signal_service import surface_moderation_findings
from backend.tests.workflows.moderation_review_case_lifecycle.conftest import (
    seed_admin,
    seed_game,
    session,
)

pytestmark = pytest.mark.suite_type("ordinary")

SCAN_TIME = datetime(2038, 3, 1, 18, tzinfo=timezone.utc)


def build_chat_finding(
    *,
    content_hash: str = "original-hash",
    priority: str = "urgent",
) -> ModerationFinding:
    return ModerationFinding(
        signal_category="chat_moderation",
        moderation_domain="chat_risk",
        detected_categories=("harassment_or_abuse",),
        severity=priority,
        priority=priority,
        field_name="message_body",
        field_label="Message",
        excerpt="Synthetic moderation evidence.",
        content_hash=content_hash,
        matched_rule_ids=("chat-harassment",),
        matched_rule_versions=(
            {"rule_id": "chat-harassment", "rule_version": "1"},
        ),
        provenance=ScanProvenance(
            scanner_id="moderation-taxonomy",
            scanner_version="1",
            taxonomy_version="1",
            configuration_hash="synthetic-configuration",
            canonicalization_version="1",
            evidence_format_version="1",
            target_context="game_chat_message",
            declared_limits=(),
            scanned_at=SCAN_TIME,
            execution_duration_us=1,
        ),
    )


def event_rows(db, review_case_id: uuid.UUID) -> list[AdminReviewCaseEvent]:
    return list(
        db.scalars(
            select(AdminReviewCaseEvent)
            .where(AdminReviewCaseEvent.review_case_id == review_case_id)
            .order_by(AdminReviewCaseEvent.case_version.asc())
        ).all()
    )


def seed_current_signal(db):
    game = seed_game(db)
    surface_moderation_findings(
        db,
        target_type="community_game_chat",
        target_data={"target_game_id": game.id},
        findings=[build_chat_finding()],
        scanned_field_hashes={"message_body": "original-hash"},
    )
    review_case = db.scalar(
        select(AdminReviewCase).where(
            AdminReviewCase.target_game_id == game.id,
            AdminReviewCase.case_category == "chat_moderation",
            AdminReviewCase.case_status == "open",
        )
    )
    signal = db.scalar(
        select(AdminReviewSignal).where(
            AdminReviewSignal.review_case_id == review_case.id,
        )
    )
    return game, review_case, signal


def reconcile_signal_state(
    db,
    *,
    game_id: uuid.UUID,
    findings: list[ModerationFinding],
    latest_hash: str,
) -> None:
    surface_moderation_findings(
        db,
        target_type="community_game_chat",
        target_data={"target_game_id": game_id},
        findings=findings,
        scanned_field_hashes={"message_body": latest_hash},
    )


def test_signal_supersede_and_unchanged_rescan_update_once() -> None:
    with session() as db:
        game, review_case, signal = seed_current_signal(db)
        case_id = review_case.id
        signal_id = signal.id

        reconcile_signal_state(
            db,
            game_id=game.id,
            findings=[],
            latest_hash="replacement-hash",
        )

        review_case = db.get(AdminReviewCase, case_id)
        signal = db.get(AdminReviewSignal, signal_id)
        events = event_rows(db, case_id)
        assert review_case.case_category == "chat_moderation"
        assert review_case.target_game_id == game.id
        assert review_case.case_status == "open"
        assert review_case.case_version == 3
        assert review_case.priority == "attention"
        assert signal.review_case_id == case_id
        assert signal.metadata_["current_match"] is False
        assert signal.metadata_["superseded_by_content_change"] is True
        assert signal.metadata_["latest_content_hash"] == "replacement-hash"
        assert [event.case_version for event in events] == [1, 2, 3]
        assert [event.event_type for event in events] == [
            "case_created",
            "signal_attached",
            "signal_superseded",
        ]
        assert events[-1].signal_id == signal_id

        reconcile_signal_state(
            db,
            game_id=game.id,
            findings=[],
            latest_hash="replacement-hash",
        )
        assert db.get(AdminReviewCase, case_id).case_version == 3
        assert db.get(AdminReviewCase, case_id).priority == "attention"
        assert len(event_rows(db, case_id)) == 3


def test_signal_reactivation_and_unchanged_rescan_update_once() -> None:
    with session() as db:
        game, review_case, signal = seed_current_signal(db)
        case_id = review_case.id
        signal_id = signal.id
        reconcile_signal_state(
            db,
            game_id=game.id,
            findings=[],
            latest_hash="replacement-hash",
        )

        reconcile_signal_state(
            db,
            game_id=game.id,
            findings=[build_chat_finding()],
            latest_hash="original-hash",
        )

        review_case = db.get(AdminReviewCase, case_id)
        signal = db.get(AdminReviewSignal, signal_id)
        events = event_rows(db, case_id)
        assert review_case.case_category == "chat_moderation"
        assert review_case.case_status == "open"
        assert review_case.case_version == 4
        assert review_case.priority == "urgent"
        assert signal.metadata_["current_match"] is True
        assert signal.metadata_["superseded_by_content_change"] is False
        assert signal.metadata_["latest_content_hash"] == "original-hash"
        assert [event.case_version for event in events] == [1, 2, 3, 4]
        assert [event.event_type for event in events] == [
            "case_created",
            "signal_attached",
            "signal_superseded",
            "signal_reactivated",
        ]
        assert events[-1].signal_id == signal_id

        reconcile_signal_state(
            db,
            game_id=game.id,
            findings=[build_chat_finding()],
            latest_hash="original-hash",
        )
        assert db.get(AdminReviewCase, case_id).case_version == 4
        assert db.get(AdminReviewCase, case_id).priority == "urgent"
        assert len(event_rows(db, case_id)) == 4


def test_dismissed_signal_does_not_hold_reconciled_case_priority() -> None:
    with session() as db:
        game = seed_game(db)
        dismissed_message_id = uuid.uuid4()
        current_message_id = uuid.uuid4()

        def surface_message_finding(
            *,
            content_hash: str,
            message_id: uuid.UUID,
            priority: str,
        ) -> None:
            surface_moderation_findings(
                db,
                target_type="community_game_chat",
                target_data={"target_game_id": game.id},
                findings=[
                    build_chat_finding(
                        content_hash=content_hash,
                        priority=priority,
                    )
                ],
                scanned_field_hashes={"message_body": content_hash},
                extra_metadata={"message_id": str(message_id)},
                metadata_filters={"message_id": str(message_id)},
            )

        surface_message_finding(
            content_hash="dismissed-critical-hash",
            message_id=dismissed_message_id,
            priority="critical",
        )
        review_case = db.scalar(
            select(AdminReviewCase).where(
                AdminReviewCase.target_game_id == game.id,
                AdminReviewCase.case_category == "chat_moderation",
                AdminReviewCase.case_status == "open",
            )
        )
        case_id = review_case.id
        dismissed_signal = db.scalar(
            select(AdminReviewSignal).where(
                AdminReviewSignal.review_case_id == review_case.id,
                AdminReviewSignal.priority == "critical",
            )
        )

        surface_message_finding(
            content_hash="current-urgent-hash",
            message_id=current_message_id,
            priority="urgent",
        )
        dismissed_signal.signal_status = "dismissed"
        db.commit()

        surface_message_finding(
            content_hash="current-attention-hash",
            message_id=current_message_id,
            priority="attention",
        )

        db.expire_all()
        review_case = db.get(AdminReviewCase, case_id)
        signals = list(
            db.scalars(
                select(AdminReviewSignal)
                .where(AdminReviewSignal.review_case_id == review_case.id)
            ).all()
        )
        events = event_rows(db, review_case.id)
        signals_by_priority = {signal.priority: signal for signal in signals}

        assert review_case.case_version == 5
        assert review_case.priority == "attention"
        assert set(signals_by_priority) == {"attention", "critical", "urgent"}
        assert signals_by_priority["critical"].signal_status == "dismissed"
        assert signals_by_priority["critical"].metadata_["current_match"] is True
        assert signals_by_priority["urgent"].metadata_["current_match"] is False
        assert signals_by_priority["attention"].metadata_["current_match"] is True
        assert [event.case_version for event in events] == [1, 2, 3, 4, 5]
        assert [event.event_type for event in events] == [
            "case_created",
            "signal_attached",
            "signal_attached",
            "signal_attached",
            "signal_superseded",
        ]


def test_closed_chat_case_is_not_mutated_by_later_signal_rescan() -> None:
    with session() as db:
        game, review_case, signal = seed_current_signal(db)
        admin = seed_admin(db)
        case_id = review_case.id
        signal_id = signal.id
        close_review_case(
            db,
            review_case_id=case_id,
            admin_user=admin,
            payload=AdminReviewCaseClose(
                outcome="no_action_needed",
                reason="Close the historical chat case.",
                expected_case_version=2,
                idempotency_key="close-signal-history",
            ),
        )
        before_metadata = dict(db.get(AdminReviewSignal, signal_id).metadata_)

        reconcile_signal_state(
            db,
            game_id=game.id,
            findings=[],
            latest_hash="replacement-hash",
        )

        historical_case = db.get(AdminReviewCase, case_id)
        historical_signal = db.get(AdminReviewSignal, signal_id)
        assert historical_case.case_status == "closed"
        assert historical_case.case_category == "chat_moderation"
        assert historical_case.case_version == 3
        assert historical_case.priority == "urgent"
        assert historical_signal.metadata_ == before_metadata
        assert [event.event_type for event in event_rows(db, case_id)] == [
            "case_created",
            "signal_attached",
            "closed",
        ]


def test_signal_reconciliation_failure_rolls_back_attach_and_supersede(
    monkeypatch,
) -> None:
    with session() as db:
        game, review_case, signal = seed_current_signal(db)
        game_id = game.id
        case_id = review_case.id
        signal_id = signal.id

    def fail_before_supersede(*_args, **_kwargs):
        raise RuntimeError("synthetic reconciliation failure")

    monkeypatch.setattr(
        moderation_signal_service,
        "mark_superseded_signals",
        fail_before_supersede,
    )

    with session() as db, pytest.raises(
        RuntimeError,
        match="synthetic reconciliation failure",
    ):
        surface_moderation_findings(
            db,
            target_type="community_game_chat",
            target_data={"target_game_id": game_id},
            findings=[
                build_chat_finding(
                    content_hash="replacement-hash",
                    priority="critical",
                )
            ],
            scanned_field_hashes={"message_body": "replacement-hash"},
        )

    with session() as db:
        review_case = db.get(AdminReviewCase, case_id)
        signal = db.get(AdminReviewSignal, signal_id)
        assert review_case.case_version == 2
        assert review_case.priority == "urgent"
        assert signal.metadata_["current_match"] is True
        assert signal.metadata_["latest_content_hash"] == "original-hash"
        assert [event.event_type for event in event_rows(db, case_id)] == [
            "case_created",
            "signal_attached",
        ]
        assert db.scalar(
            select(func.count(AdminReviewSignal.id)).where(
                AdminReviewSignal.review_case_id == case_id,
            )
        ) == 1
