from __future__ import annotations

import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import event, func, select
from sqlalchemy.exc import IntegrityError, OperationalError

os.environ.setdefault("APP_ENV", "test")
from backend.tests.support.environment_safety import DEDICATED_TEST_DATABASE_NAME

_DATABASE_URL_CONFIGURED_FOR_RUNTIME = bool(os.getenv("DATABASE_URL"))
if not _DATABASE_URL_CONFIGURED_FOR_RUNTIME:
    os.environ["DATABASE_URL"] = (
        f"postgresql+psycopg://localhost:5432/{DEDICATED_TEST_DATABASE_NAME}"
    )

try:
    from backend.models import (
        AdminContentModerationFinding,
        AdminReviewCase,
        AdminReviewCaseEvent,
        Game,
        SubPost,
        User,
        Venue,
    )
    from backend.schemas.admin_review_schema import AdminReviewCaseClose
    from backend.services import (
        content_moderation_finding_service,
        moderation_surfacing_service,
    )
    from backend.services.admin_review_service import (
        close_review_case,
        serialize_review_case_detail,
    )
    from backend.services.content_moderation_evidence_service import (
        build_content_moderation_findings,
    )
    from backend.services.content_moderation_finding_service import (
        reconcile_content_moderation_findings,
        run_content_moderation_finding_reconciliation_safely,
    )
    from backend.services.moderation_evidence_service import ModerationEvidenceError
    from backend.services.moderation_surfacing_service import (
        build_community_game_moderation_fields,
        build_need_a_sub_moderation_fields,
        is_retryable_moderation_creation_race,
        surface_community_game_text,
        surface_need_a_sub_post_text,
    )
    from backend.services.moderation_taxonomy import (
        TARGET_CONTEXT_COMMUNITY_GAME,
        TARGET_CONTEXT_NEED_A_SUB,
    )
finally:
    if not _DATABASE_URL_CONFIGURED_FOR_RUNTIME:
        os.environ.pop("DATABASE_URL", None)

pytestmark = pytest.mark.suite_type("ordinary")

_BASE_TIME = datetime(2037, 6, 1, 12, 0, tzinfo=timezone.utc)
_SENSITIVE_EXCEPTION_CANARY = "CANARY-MODERATION-EVIDENCE 312-555-1212"
_INVALID_NESTED_IDENTIFIER_VALUES = (
    pytest.param(1, id="numeric"),
    pytest.param(True, id="boolean"),
    pytest.param(None, id="null"),
    pytest.param(["1"], id="list"),
    pytest.param({"value": "1"}, id="object"),
)


def _sensitive_database_error() -> OperationalError:
    return OperationalError(
        f"SELECT '{_SENSITIVE_EXCEPTION_CANARY}'",
        {"evidence": _SENSITIVE_EXCEPTION_CANARY},
        RuntimeError(_SENSITIVE_EXCEPTION_CANARY),
    )


def _session():
    from backend.database import SessionLocal

    return SessionLocal()


def _user(index: int) -> User:
    token = uuid.uuid4()
    return User(
        id=uuid.uuid4(),
        auth_user_id=f"ws03-05a-user-{index}-{token}",
        role="player",
        email=f"ws03-05a-{index}-{token}@example.invalid",
        first_name="Evidence",
        last_name=f"Owner{index}",
        account_status="active",
        hosting_status="eligible",
    )


def _venue() -> Venue:
    return Venue(
        id=uuid.uuid4(),
        name="Evidence Field",
        address_line_1="1 Test Way",
        city="Austin",
        state="TX",
        postal_code="78701",
        country_code="US",
        venue_status="approved",
        is_active=True,
    )


def _game(host: User, venue: Venue, *, description: str) -> Game:
    return Game(
        id=uuid.uuid4(),
        game_type="community",
        payment_collection_type="none",
        publish_status="published",
        game_status="active",
        public_visibility_status="visible",
        join_enforcement_status="open",
        title="Evidence Game",
        description=description,
        venue_id=venue.id,
        venue_name_snapshot=venue.name,
        address_snapshot=venue.address_line_1,
        city_snapshot=venue.city,
        state_snapshot=venue.state,
        host_user_id=host.id,
        created_by_user_id=host.id,
        starts_at=_BASE_TIME,
        ends_at=_BASE_TIME + timedelta(hours=2),
        starts_on_local=_BASE_TIME.date(),
        timezone="UTC",
        sport_type="soccer",
        format_label="5v5",
        game_player_group="coed",
        skill_level="any",
        environment_type="indoor",
        total_spots=10,
        price_per_player_cents=0,
        currency="USD",
        policy_mode="custom_hosted",
        published_at=_BASE_TIME - timedelta(days=1),
    )


def _sub_post(owner: User, *, notes: str) -> SubPost:
    return SubPost(
        id=uuid.uuid4(),
        owner_user_id=owner.id,
        post_status="active",
        public_visibility_status="visible",
        sport_type="soccer",
        format_label="5v5",
        environment_type="indoor",
        skill_level="any",
        game_player_group="coed",
        starts_at=_BASE_TIME + timedelta(days=2),
        ends_at=_BASE_TIME + timedelta(days=2, hours=2),
        starts_on_local=(_BASE_TIME + timedelta(days=2)).date(),
        timezone="UTC",
        location_name="Evidence Field",
        address_line_1="1 Test Way",
        city="Austin",
        state="TX",
        postal_code="78701",
        country_code="US",
        subs_needed=1,
        price_due_at_venue_cents=0,
        currency="USD",
        expires_at=_BASE_TIME + timedelta(days=1),
        notes=notes,
    )


def _seed_game(db, *, description: str = "Text me at 312-555-1212") -> Game:
    owner = _user(1)
    venue = _venue()
    game = _game(owner, venue, description=description)
    db.add_all([owner, venue])
    db.commit()
    db.add(game)
    db.commit()
    return game


def _findings(db, game_id: uuid.UUID) -> list[AdminContentModerationFinding]:
    return list(
        db.scalars(
            select(AdminContentModerationFinding)
            .join(AdminReviewCase)
            .where(AdminReviewCase.target_game_id == game_id)
            .order_by(AdminContentModerationFinding.created_at.asc())
        ).all()
    )


@pytest.mark.requirement("WS03-05A-R2", "WS03-05A-R3")
@pytest.mark.parametrize(
    ("description", "expected_rule_ids", "expected_match_count"),
    (
        ("Deposit required", {"payment_pressure.phrase"}, 1),
        (
            "Venmo deposit required",
            {"payment_method.phrase", "payment_pressure.phrase"},
            2,
        ),
        (
            f"Venmo {'x' * 120} deposit required",
            {"payment_pressure.phrase"},
            1,
        ),
        (
            "Venmo is accepted. Deposit required",
            {"payment_pressure.phrase"},
            1,
        ),
        (
            "Deposit required. Pay upfront.",
            {"payment_pressure.phrase"},
            2,
        ),
    ),
)
def test_payment_pressure_persists_only_contextual_contributors(
    description: str,
    expected_rule_ids: set[str],
    expected_match_count: int,
) -> None:
    with _session() as db:
        game = _seed_game(db, description=description)
        surface_community_game_text(db, game_id=game.id)

        findings = _findings(db, game.id)
        assert len(findings) == 1
        finding = findings[0]
        evidence_rule_ids = {
            match["rule_id"] for item in finding.evidence for match in item["matches"]
        }
        version_rule_ids = {item["rule_id"] for item in finding.matched_rule_versions}
        assert finding.finding_type == "payment_pressure"
        assert finding.priority == "attention"
        assert evidence_rule_ids == expected_rule_ids
        assert version_rule_ids == expected_rule_ids
        assert sum(len(item["matches"]) for item in finding.evidence) == (
            expected_match_count
        )


@pytest.mark.requirement("WS03-05A-R2", "WS03-05A-R3", "WS03-05A-R4")
def test_saved_finding_exact_repeat_edit_clear_and_reappearance_preserve_history() -> (
    None
):
    with _session() as db:
        game = _seed_game(db)
        surface_community_game_text(db, game_id=game.id)
        first = _findings(db, game.id)[0]
        original = {
            "id": first.id,
            "evidence": first.evidence,
            "configuration_hash": first.configuration_hash,
            "scanned_at": first.scanned_at,
            "first_detected_at": first.first_detected_at,
            "last_detected_at": first.last_detected_at,
        }

        surface_community_game_text(db, game_id=game.id)
        exact_repeat = _findings(db, game.id)
        assert len(exact_repeat) == 1
        assert exact_repeat[0].id == original["id"]
        assert exact_repeat[0].evidence == original["evidence"]
        assert exact_repeat[0].configuration_hash == original["configuration_hash"]
        assert exact_repeat[0].scanned_at == original["scanned_at"]
        assert exact_repeat[0].first_detected_at == original["first_detected_at"]
        assert exact_repeat[0].last_detected_at >= original["last_detected_at"]

        game = db.get(Game, game.id)
        game.description = "  TEXT   ME AT 312-555-1212  "
        db.commit()
        surface_community_game_text(db, game_id=game.id)
        edited = _findings(db, game.id)
        assert len(edited) == 2
        assert edited[0].current_match is False
        assert edited[0].cleared_at is not None
        assert edited[0].evidence == original["evidence"]
        assert edited[1].current_match is True
        assert edited[1].source_content_hash != edited[0].source_content_hash
        assert edited[1].evidence_fingerprint == edited[0].evidence_fingerprint

        game.description = "A clean description"
        db.commit()
        surface_community_game_text(db, game_id=game.id)
        cleared = _findings(db, game.id)
        assert all(finding.current_match is False for finding in cleared)

        game.description = "  TEXT   ME AT 312-555-1212  "
        db.commit()
        surface_community_game_text(db, game_id=game.id)
        reappeared = _findings(db, game.id)
        current = [finding for finding in reappeared if finding.current_match]
        assert len(reappeared) == 3
        assert len(current) == 1
        assert current[0].id not in {finding.id for finding in cleared}
        assert [finding.id for finding in reappeared[:2]] == [
            finding.id for finding in cleared
        ]

        event_types = list(
            db.scalars(
                select(AdminReviewCaseEvent.event_type)
                .join(
                    AdminReviewCase,
                    AdminReviewCase.id == AdminReviewCaseEvent.review_case_id,
                )
                .where(AdminReviewCase.target_game_id == game.id)
            ).all()
        )
        assert event_types.count("case_created") == 1
        assert event_types.count("finding_attached") == 3
        assert event_types.count("finding_cleared") == 2

        review_case = db.scalar(
            select(AdminReviewCase).where(AdminReviewCase.target_game_id == game.id)
        )
        detail = serialize_review_case_detail(db, review_case)
        assert detail.finding_summary.current_finding_count == 1
        assert detail.finding_summary.total_finding_count == 3
        assert detail.finding_summary.current_issue_labels
        assert detail.finding_summary.previous_issue_labels


@pytest.mark.requirement("WS03-05A-R2", "WS03-05A-R3", "WS03-05A-R4")
def test_long_atomic_url_and_email_matches_persist_complete_evidence() -> None:
    long_url = "https://example.com/" + "a" * 180
    long_email = f"{'b' * 180}@example.com"
    with _session() as db:
        game = _seed_game(db, description=long_url)
        surface_community_game_text(db, game_id=game.id)
        game_finding = _findings(db, game.id)[0]
        url_match = next(
            match
            for item in game_finding.evidence
            for match in item["matches"]
            if match["evidence_type"] == "url"
        )
        assert url_match["matched_text"] == long_url
        assert long_url[url_match["start"] : url_match["end"]] == long_url

        owner = _user(2)
        post = _sub_post(owner, notes=long_email)
        db.add(owner)
        db.commit()
        db.add(post)
        db.commit()
        surface_need_a_sub_post_text(db, sub_post_id=post.id)
        sub_finding = db.scalar(
            select(AdminContentModerationFinding)
            .join(AdminReviewCase)
            .where(AdminReviewCase.target_sub_post_id == post.id)
        )
        email_match = next(
            match
            for item in sub_finding.evidence
            for match in item["matches"]
            if match["evidence_type"] == "email"
        )
        assert email_match["matched_text"] == long_email
        assert long_email[email_match["start"] : email_match["end"]] == long_email


@pytest.mark.requirement("WS03-05A-R4", "WS03-05A-R6")
def test_priority_uses_only_current_findings_and_closed_case_stays_immutable() -> None:
    with _session() as db:
        game = _seed_game(
            db,
            description="Text me at 312-555-1212. I will hurt you.",
        )
        surface_community_game_text(db, game_id=game.id)
        first_case = db.scalar(
            select(AdminReviewCase).where(AdminReviewCase.target_game_id == game.id)
        )
        assert first_case.priority == "urgent"

        game.description = "Text me at 312-555-1212"
        db.commit()
        surface_community_game_text(db, game_id=game.id)
        db.refresh(first_case)
        assert first_case.priority == "attention"
        closed_finding_state = [
            (
                finding.id,
                finding.current_match,
                finding.evidence,
                finding.updated_at,
            )
            for finding in _findings(db, game.id)
        ]

        admin_user = db.get(User, game.host_user_id)
        admin_user.role = "admin"
        db.commit()
        close_review_case(
            db,
            review_case_id=first_case.id,
            admin_user=admin_user,
            payload=AdminReviewCaseClose(
                outcome="no_action_needed",
                reason="Synthetic closed-case lifecycle proof",
                expected_case_version=first_case.case_version,
                idempotency_key="ws03-05a-synthetic-close",
            ),
        )

        game.description = "Text me at 214-555-0100"
        db.commit()
        surface_community_game_text(db, game_id=game.id)

        cases = list(
            db.scalars(
                select(AdminReviewCase)
                .where(AdminReviewCase.target_game_id == game.id)
                .order_by(AdminReviewCase.created_at.asc())
            ).all()
        )
        assert len(cases) == 2
        assert cases[0].id == first_case.id
        assert cases[0].case_status == "closed"
        assert cases[1].case_status == "open"
        preserved = list(
            db.scalars(
                select(AdminContentModerationFinding)
                .where(AdminContentModerationFinding.review_case_id == first_case.id)
                .order_by(AdminContentModerationFinding.created_at.asc())
            ).all()
        )
        assert [
            (
                finding.id,
                finding.current_match,
                finding.evidence,
                finding.updated_at,
            )
            for finding in preserved
        ] == closed_finding_state


@pytest.mark.requirement("WS03-05A-R2", "WS03-05A-R4")
def test_configuration_change_creates_a_new_current_identity(monkeypatch) -> None:
    from backend.services import content_moderation_evidence_service

    with _session() as db:
        game = _seed_game(db)
        fields = build_community_game_moderation_fields(game, None)
        first_scan = build_content_moderation_findings(
            fields,
            target_context=TARGET_CONTEXT_COMMUNITY_GAME,
        )
        reconcile_content_moderation_findings(
            db,
            target_data={"target_game_id": game.id},
            scan_result=first_scan,
        )
        changed_scan = replace(
            first_scan,
            provenance=replace(
                first_scan.provenance,
                configuration_hash="a" * 64,
                scanned_at=first_scan.provenance.scanned_at + timedelta(seconds=1),
            ),
        )
        monkeypatch.setattr(
            content_moderation_evidence_service,
            "profile_configuration_hash",
            lambda profile: changed_scan.provenance.configuration_hash,
        )
        reconcile_content_moderation_findings(
            db,
            target_data={"target_game_id": game.id},
            scan_result=changed_scan,
        )

        findings = _findings(db, game.id)
        assert len(findings) == 2
        assert findings[0].current_match is False
        assert findings[1].current_match is True
        assert findings[0].configuration_hash != findings[1].configuration_hash
        assert findings[0].evidence == findings[1].evidence


@pytest.mark.requirement("WS03-05A-R2", "WS03-05A-R3", "WS03-05A-R4")
def test_need_a_sub_adapter_persists_its_frozen_context_and_field_purpose() -> None:
    with _session() as db:
        owner = _user(2)
        post = _sub_post(owner, notes="Text me at 312-555-1212")
        db.add(owner)
        db.commit()
        db.add(post)
        db.commit()

        surface_need_a_sub_post_text(db, sub_post_id=post.id)

        review_case = db.scalar(
            select(AdminReviewCase).where(AdminReviewCase.target_sub_post_id == post.id)
        )
        finding = db.scalar(
            select(AdminContentModerationFinding).where(
                AdminContentModerationFinding.review_case_id == review_case.id
            )
        )
        assert finding.target_context == TARGET_CONTEXT_NEED_A_SUB
        assert finding.source_field == "notes"
        assert finding.field_purpose == "general"
        assert finding.matched_rule_versions
        assert finding.declared_limits


@pytest.mark.requirement("WS03-05A-R3", "WS03-05A-R5")
def test_tampered_saved_evidence_rejects_without_partial_review_state() -> None:
    with _session() as db:
        game = _seed_game(db)
        scan = build_content_moderation_findings(
            build_community_game_moderation_fields(game, None),
            target_context=TARGET_CONTEXT_COMMUNITY_GAME,
        )
        tampered_finding = replace(
            scan.findings[0],
            source_content_hash="0" * 64,
        )
        tampered_scan = replace(scan, findings=(tampered_finding,))

        with pytest.raises(ModerationEvidenceError):
            reconcile_content_moderation_findings(
                db,
                target_data={"target_game_id": game.id},
                scan_result=tampered_scan,
            )
        db.rollback()

        assert db.scalar(select(func.count()).select_from(AdminReviewCase)) == 0
        assert (
            db.scalar(select(func.count()).select_from(AdminContentModerationFinding))
            == 0
        )
        assert db.scalar(select(func.count()).select_from(AdminReviewCaseEvent)) == 0


@pytest.mark.requirement("WS03-05A-R2", "WS03-05A-R3", "WS03-05A-R5")
@pytest.mark.parametrize(
    "field_name",
    ("rule_id", "rule_version", "evidence_type"),
)
@pytest.mark.parametrize("invalid_value", _INVALID_NESTED_IDENTIFIER_VALUES)
def test_persistence_rejects_non_string_nested_evidence_identifiers(
    field_name: str,
    invalid_value: object,
) -> None:
    with _session() as db:
        game = _seed_game(db)
        scan = build_content_moderation_findings(
            build_community_game_moderation_fields(game, None),
            target_context=TARGET_CONTEXT_COMMUNITY_GAME,
        )
        evidence = deepcopy(scan.findings[0].evidence)
        evidence[0]["matches"][0][field_name] = deepcopy(invalid_value)
        tampered_finding = replace(scan.findings[0], evidence=evidence)
        tampered_scan = replace(scan, findings=(tampered_finding,))

        with pytest.raises(ModerationEvidenceError):
            reconcile_content_moderation_findings(
                db,
                target_data={"target_game_id": game.id},
                scan_result=tampered_scan,
            )
        db.rollback()

        assert db.scalar(select(func.count()).select_from(AdminReviewCase)) == 0
        assert (
            db.scalar(select(func.count()).select_from(AdminContentModerationFinding))
            == 0
        )
        assert db.scalar(select(func.count()).select_from(AdminReviewCaseEvent)) == 0


@pytest.mark.requirement("WS03-05A-R3", "WS03-05A-R6")
@pytest.mark.parametrize("adapter", ("community_game", "need_a_sub"))
def test_saved_content_adapter_exception_logs_exclude_sensitive_evidence(
    adapter: str,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def fail_with_sensitive_evidence(*args, **kwargs):
        del args, kwargs
        raise _sensitive_database_error()

    monkeypatch.setattr(
        moderation_surfacing_service,
        "build_content_moderation_findings",
        fail_with_sensitive_evidence,
    )

    with _session() as db:
        if adapter == "community_game":
            target = _seed_game(db)
            surface_community_game_text(db, game_id=target.id)
        else:
            owner = _user(90)
            target = _sub_post(owner, notes="Safe notes")
            db.add(owner)
            db.commit()
            db.add(target)
            db.commit()
            surface_need_a_sub_post_text(db, sub_post_id=target.id)

    assert _SENSITIVE_EXCEPTION_CANARY not in caplog.text
    assert "OperationalError" in caplog.text
    assert all(record.exc_info is None for record in caplog.records)


@pytest.mark.requirement("WS03-05A-R3", "WS03-05A-R6")
def test_reconciliation_helper_exception_log_excludes_sensitive_evidence(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def fail_with_sensitive_evidence(*args, **kwargs):
        del args, kwargs
        raise _sensitive_database_error()

    monkeypatch.setattr(
        content_moderation_finding_service,
        "reconcile_content_moderation_findings",
        fail_with_sensitive_evidence,
    )

    with _session() as db:
        game = _seed_game(db)
        scan = build_content_moderation_findings(
            build_community_game_moderation_fields(game, None),
            target_context=TARGET_CONTEXT_COMMUNITY_GAME,
        )
        run_content_moderation_finding_reconciliation_safely(
            db,
            target_data={"target_game_id": game.id},
            scan_result=scan,
        )

    assert _SENSITIVE_EXCEPTION_CANARY not in caplog.text
    assert "OperationalError" in caplog.text
    assert all(record.exc_info is None for record in caplog.records)


@pytest.mark.requirement("WS03-05A-R4", "WS03-05A-R5")
def test_current_identity_reconciliation_serializes_on_the_locked_target() -> None:
    from backend.database import engine

    with _session() as db:
        game = _seed_game(db)
        game_id = game.id
        surface_community_game_text(db, game_id=game_id)
        game = db.get(Game, game_id)
        game.description = "Text me at 214-555-0100"
        db.commit()

    insert_started = threading.Event()
    loser_target_started = threading.Event()
    release_winner = threading.Event()
    target_reads: list[str] = []

    def observe_lock_path(
        conn, cursor, statement, parameters, context, executemany
    ) -> None:
        del conn, cursor, parameters, context, executemany
        thread_name = threading.current_thread().name
        if (
            thread_name.startswith(("moderation-winner", "moderation-loser"))
            and "FROM games" in statement
            and "FOR UPDATE" in statement
        ):
            target_reads.append(statement)
            if thread_name.startswith("moderation-loser"):
                loser_target_started.set()
        if (
            thread_name.startswith("moderation-winner")
            and "INSERT INTO admin_content_moderation_findings" in statement
        ):
            insert_started.set()
            assert release_winner.wait(timeout=10)

    def reconcile_in_independent_session() -> None:
        with _session() as worker_db:
            surface_community_game_text(worker_db, game_id=game_id)

    event.listen(engine, "before_cursor_execute", observe_lock_path)
    try:
        with (
            ThreadPoolExecutor(
                max_workers=1,
                thread_name_prefix="moderation-winner",
            ) as winner_executor,
            ThreadPoolExecutor(
                max_workers=1,
                thread_name_prefix="moderation-loser",
            ) as loser_executor,
        ):
            winner_future = winner_executor.submit(reconcile_in_independent_session)
            assert insert_started.wait(timeout=5)
            loser_future = loser_executor.submit(reconcile_in_independent_session)
            assert loser_target_started.wait(timeout=5)
            release_winner.set()
            winner_future.result(timeout=15)
            loser_future.result(timeout=15)
    finally:
        release_winner.set()
        event.remove(engine, "before_cursor_execute", observe_lock_path)

    with _session() as db:
        cases = list(
            db.scalars(
                select(AdminReviewCase).where(AdminReviewCase.target_game_id == game_id)
            ).all()
        )
        findings = list(
            db.scalars(
                select(AdminContentModerationFinding)
                .join(AdminReviewCase)
                .where(AdminReviewCase.target_game_id == game_id)
                .order_by(AdminContentModerationFinding.created_at.asc())
            ).all()
        )
        attachment_events = list(
            db.scalars(
                select(AdminReviewCaseEvent).where(
                    AdminReviewCaseEvent.review_case_id == cases[0].id,
                    AdminReviewCaseEvent.event_type == "finding_attached",
                )
            ).all()
        )

        assert len(target_reads) == 2
        assert len(cases) == 1
        assert len(findings) == 2
        assert len([finding for finding in findings if finding.current_match]) == 1
        assert len([finding for finding in findings if not finding.current_match]) == 1
        assert all(
            finding.cleared_at is not None
            for finding in findings
            if not finding.current_match
        )
        assert len(attachment_events) == 2
        assert cases[0].case_version == 4
        assert [event.event_sequence for event in attachment_events] == [2, 3]


def _integrity_error_for_constraint(constraint_name: str) -> IntegrityError:
    original = RuntimeError("synthetic integrity failure")
    original.diag = type("Diagnostic", (), {"constraint_name": constraint_name})()
    return IntegrityError("INSERT", {}, original)


@pytest.mark.requirement("WS03-05A-R5")
def test_retry_classification_is_limited_to_creation_race_constraints() -> None:
    for constraint_name in (
        "uq_admin_review_cases_open_community_game_moderation",
        "uq_admin_review_cases_open_need_sub_moderation",
        "uq_admin_content_moderation_findings_current_identity",
    ):
        assert is_retryable_moderation_creation_race(
            _integrity_error_for_constraint(constraint_name)
        )
    for constraint_name in (
        "ck_admin_content_moderation_findings_evidence_nonempty",
        "fk_admin_content_moderation_findings_review_case_id",
        "uq_unrelated_constraint",
    ):
        assert not is_retryable_moderation_creation_race(
            _integrity_error_for_constraint(constraint_name)
        )


@pytest.mark.requirement("WS03-05A-R5")
def test_non_retryable_integrity_error_is_rolled_back_without_retry(
    monkeypatch,
) -> None:
    from backend.services import moderation_surfacing_service

    with _session() as db:
        game_id = _seed_game(db).id
        calls = 0

        def fail_reconciliation(*args, **kwargs):
            nonlocal calls
            del args, kwargs
            calls += 1
            raise _integrity_error_for_constraint(
                "ck_admin_content_moderation_findings_evidence_nonempty"
            )

        monkeypatch.setattr(
            moderation_surfacing_service,
            "reconcile_content_moderation_findings",
            fail_reconciliation,
        )
        surface_community_game_text(db, game_id=game_id)

        assert calls == 1
        assert not db.in_transaction()


@pytest.mark.requirement("WS03-05A-R3", "WS03-05A-R5")
def test_source_edit_race_scans_the_post_lock_committed_value() -> None:
    from backend.database import engine

    with _session() as db:
        game_id = _seed_game(db).id

    reader_query_started = threading.Event()
    release_writer = threading.Event()

    def observe_reader_query(
        conn, cursor, statement, parameters, context, executemany
    ) -> None:
        del conn, cursor, parameters, context, executemany
        if (
            threading.current_thread().name.startswith("moderation-reader")
            and "FROM games" in statement
            and "FOR UPDATE" in statement
        ):
            reader_query_started.set()

    event.listen(engine, "before_cursor_execute", observe_reader_query)
    try:
        with _session() as writer:
            locked_game = writer.scalar(
                select(Game).where(Game.id == game_id).with_for_update()
            )
            locked_game.description = "A clean committed description"
            writer.flush()

            def reconcile_after_edit() -> None:
                with _session() as reader:
                    surface_community_game_text(reader, game_id=game_id)

            with ThreadPoolExecutor(
                max_workers=1,
                thread_name_prefix="moderation-reader",
            ) as executor:
                future = executor.submit(reconcile_after_edit)
                assert reader_query_started.wait(timeout=5)
                writer.commit()
                release_writer.set()
                future.result(timeout=10)
    finally:
        event.remove(engine, "before_cursor_execute", observe_reader_query)

    assert release_writer.is_set()
    with _session() as db:
        assert db.scalar(select(func.count()).select_from(AdminReviewCase)) == 0
        assert (
            db.scalar(select(func.count()).select_from(AdminContentModerationFinding))
            == 0
        )


@pytest.mark.requirement("WS03-05A-R1")
def test_need_a_sub_field_inventory_is_complete_before_scanning() -> None:
    owner = _user(3)
    post = _sub_post(owner, notes="Clean")
    fields = build_need_a_sub_moderation_fields(post)
    assert [field.field_name for field in fields] == [
        "team_name",
        "location_name",
        "neighborhood",
        "payment_note",
        "notes",
    ]
