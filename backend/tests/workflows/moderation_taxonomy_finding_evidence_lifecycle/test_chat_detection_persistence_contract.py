from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
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
        AdminReviewSignal,
        ChatMessage,
        Game,
        GameChat,
        GameChatMessageDetection,
        GameChatRead,
        SubPost,
        SubPostChat,
        SubPostChatMessage,
        SubPostChatMessageDetection,
        SubPostChatRead,
        User,
        Venue,
    )
    from backend.schemas.chat_message_schema import ChatMessageCreate
    from backend.schemas.sub_post_chat_message_schema import SubPostChatMessageCreate
    from backend.services import (
        game_chat_service,
        moderation_signal_service,
        moderation_surfacing_service,
        sub_post_chat_service,
    )
    from backend.services.chat_moderation_admin_service import serialize_detections
    from backend.services.moderation_evidence_service import exact_source_hash
    from backend.services.moderation_taxonomy import (
        TARGET_CONTEXT_GAME_CHAT,
        TARGET_CONTEXT_NEED_A_SUB_CHAT,
    )
finally:
    if not _DATABASE_URL_CONFIGURED_FOR_RUNTIME:
        os.environ.pop("DATABASE_URL", None)

pytestmark = pytest.mark.suite_type("ordinary")

_BASE_TIME = datetime(2037, 7, 1, 12, 0, tzinfo=timezone.utc)
_RISKY_BODY = "Text me at 312-555-1212"
_SENSITIVE_EXCEPTION_CANARY = "CANARY-MODERATION-EVIDENCE 312-555-1212"


def _session():
    from backend.database import SessionLocal

    return SessionLocal()


def _sensitive_database_error() -> OperationalError:
    return OperationalError(
        f"SELECT '{_SENSITIVE_EXCEPTION_CANARY}'",
        {"evidence": _SENSITIVE_EXCEPTION_CANARY},
        RuntimeError(_SENSITIVE_EXCEPTION_CANARY),
    )


def _user(index: int) -> User:
    token = uuid.uuid4()
    return User(
        id=uuid.uuid4(),
        auth_user_id=f"ws03-05a-chat-{index}-{token}",
        role="player",
        email=f"ws03-05a-chat-{index}-{token}@example.invalid",
        first_name="Chat",
        last_name=f"Owner{index}",
        account_status="active",
        hosting_status="eligible",
    )


def _venue() -> Venue:
    return Venue(
        id=uuid.uuid4(),
        name="Chat Evidence Field",
        address_line_1="1 Test Way",
        city="Austin",
        state="TX",
        postal_code="78701",
        country_code="US",
        venue_status="approved",
        is_active=True,
    )


def _game(host: User, venue: Venue, index: int = 1) -> Game:
    starts_at = _BASE_TIME + timedelta(days=index)
    return Game(
        id=uuid.uuid4(),
        game_type="community",
        payment_collection_type="none",
        publish_status="published",
        game_status="active",
        public_visibility_status="visible",
        join_enforcement_status="open",
        title=f"Chat Evidence Game {index}",
        venue_id=venue.id,
        venue_name_snapshot=venue.name,
        address_snapshot=venue.address_line_1,
        city_snapshot=venue.city,
        state_snapshot=venue.state,
        host_user_id=host.id,
        created_by_user_id=host.id,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=2),
        starts_on_local=starts_at.date(),
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


def _sub_post(owner: User, index: int = 1) -> SubPost:
    starts_at = _BASE_TIME + timedelta(days=index + 2)
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
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=2),
        starts_on_local=starts_at.date(),
        timezone="UTC",
        location_name=f"Chat Field {index}",
        address_line_1="1 Test Way",
        city="Austin",
        state="TX",
        postal_code="78701",
        country_code="US",
        subs_needed=1,
        price_due_at_venue_cents=0,
        currency="USD",
        expires_at=starts_at - timedelta(hours=1),
    )


def _seed_game_chat(db) -> tuple[User, GameChat]:
    owner = _user(1)
    venue = _venue()
    game = _game(owner, venue)
    chat = GameChat(id=uuid.uuid4(), game_id=game.id, chat_status="active")
    db.add_all([owner, venue])
    db.commit()
    db.add(game)
    db.commit()
    db.add(chat)
    db.commit()
    return owner, chat


def _seed_sub_chat(db) -> tuple[User, SubPost, SubPostChat]:
    owner = _user(2)
    post = _sub_post(owner)
    chat = SubPostChat(id=uuid.uuid4(), sub_post_id=post.id, chat_status="active")
    db.add(owner)
    db.commit()
    db.add(post)
    db.commit()
    db.add(chat)
    db.commit()
    return owner, post, chat


def _count(db, model, *where) -> int:
    return int(db.scalar(select(func.count()).select_from(model).where(*where)) or 0)


def _canary_integrity_error() -> IntegrityError:
    original = RuntimeError(
        "CANARY-MODERATION-EVIDENCE failing row contains private evidence"
    )
    original.diag = SimpleNamespace(
        constraint_name="ck_game_chat_message_detections_evidence_shape"
    )
    return IntegrityError("INSERT", {}, original)


def _assert_complete_detection_contract(
    detection: GameChatMessageDetection | SubPostChatMessageDetection,
    *,
    target_context: str,
) -> None:
    assert detection.scanner_id
    assert detection.scanner_version
    assert detection.taxonomy_version
    assert len(detection.configuration_hash) == 64
    assert detection.canonicalization_version
    assert detection.evidence_format_version
    assert detection.target_context == target_context
    assert detection.field_purpose == "chat"
    assert detection.source_field == "message_body"
    assert len(detection.source_content_hash) == 64
    assert detection.matched_rule_versions
    assert detection.declared_limits
    assert len(detection.evidence_fingerprint) == 64
    assert detection.execution_duration_us >= 0
    assert len(detection.detection_identity_hash) == 64


@pytest.mark.requirement("WS03-05A-R2", "WS03-05A-R3", "WS03-05A-R6")
def test_game_chat_persists_span_and_repeated_evidence_and_projects_provenance() -> (
    None
):
    with _session() as db:
        owner, chat = _seed_game_chat(db)
        first = game_chat_service.create_chat_message_record(
            db,
            ChatMessageCreate(chat_id=chat.id, message_body=_RISKY_BODY),
            owner,
        )
        second = game_chat_service.create_chat_message_record(
            db,
            ChatMessageCreate(chat_id=chat.id, message_body=_RISKY_BODY),
            owner,
        )

        detections = list(
            db.scalars(
                select(GameChatMessageDetection)
                .where(GameChatMessageDetection.message_id == second.id)
                .order_by(GameChatMessageDetection.category.asc())
            ).all()
        )
        assert len(detections) >= 2
        assert {detection.evidence["evidence_kind"] for detection in detections} == {
            "span",
            "context_predicate",
        }
        for detection in detections:
            _assert_complete_detection_contract(
                detection,
                target_context=TARGET_CONTEXT_GAME_CHAT,
            )
            assert detection.source_content_hash == exact_source_hash(_RISKY_BODY)

        repeated = next(
            detection
            for detection in detections
            if detection.category == "spam_or_repeated_message"
        )
        assert repeated.evidence == {
            "evidence_kind": "context_predicate",
            "predicate_key": "same_sender_same_body",
            "predicate_version": "1",
            "outcome": True,
            "reference_message_id": str(first.id),
            "reference_source_hash": exact_source_hash(_RISKY_BODY),
        }
        assert "312-555-1212" not in repeated.matched_preview
        assert "[phone]" in repeated.matched_preview

        span = next(
            detection
            for detection in detections
            if detection.evidence["evidence_kind"] == "span"
        )
        matched_text = _RISKY_BODY[span.evidence["start"] : span.evidence["end"]]
        assert span.evidence["matched_source_hash"] == exact_source_hash(matched_text)

        signal = db.scalar(
            select(AdminReviewSignal).where(
                AdminReviewSignal.metadata_["message_id"].as_string() == str(second.id)
            )
        )
        assert signal is not None
        assert signal.metadata_["scanner_id"] == repeated.scanner_id
        assert signal.metadata_["scanner_version"] == repeated.scanner_version
        assert signal.metadata_["taxonomy_version"] == repeated.taxonomy_version
        assert signal.metadata_["configuration_hash"] == repeated.configuration_hash
        assert signal.metadata_["target_context"] == TARGET_CONTEXT_GAME_CHAT


@pytest.mark.requirement("WS03-05A-R2", "WS03-05A-R3", "WS03-05A-R6")
def test_need_a_sub_chat_persists_the_same_provenance_and_non_span_contract() -> None:
    with _session() as db:
        owner, post, chat = _seed_sub_chat(db)
        first = sub_post_chat_service.create_sub_post_chat_message_workflow(
            db,
            post.id,
            SubPostChatMessageCreate(chat_id=chat.id, message_body=_RISKY_BODY),
            owner,
        )
        second = sub_post_chat_service.create_sub_post_chat_message_workflow(
            db,
            post.id,
            SubPostChatMessageCreate(chat_id=chat.id, message_body=_RISKY_BODY),
            owner,
        )
        second_id = second["id"]

        detections = list(
            db.scalars(
                select(SubPostChatMessageDetection).where(
                    SubPostChatMessageDetection.message_id == second_id
                )
            ).all()
        )
        assert len(detections) >= 2
        for detection in detections:
            _assert_complete_detection_contract(
                detection,
                target_context=TARGET_CONTEXT_NEED_A_SUB_CHAT,
            )
        repeated = next(
            detection
            for detection in detections
            if detection.category == "spam_or_repeated_message"
        )
        assert repeated.evidence["reference_message_id"] == str(first["id"])
        assert "start" not in repeated.evidence
        assert "end" not in repeated.evidence
        assert "matched_text" not in repeated.evidence

        signal = db.scalar(
            select(AdminReviewSignal).where(
                AdminReviewSignal.metadata_["message_id"].as_string() == str(second_id)
            )
        )
        assert signal.metadata_["target_context"] == TARGET_CONTEXT_NEED_A_SUB_CHAT
        assert signal.metadata_["configuration_hash"] == repeated.configuration_hash


@pytest.mark.requirement("WS03-05A-R1", "WS03-05A-R3", "WS03-05A-R6")
def test_stable_chat_rule_keys_persist_and_serialize_in_both_chat_domains() -> None:
    body = "You are worthless. Go back to your country."
    expected = {
        "harassment_or_abuse": "harassment_or_abuse.phrase",
        "slur_or_hate": "slur_or_hate.phrase",
    }
    with _session() as db:
        game_owner, game_chat = _seed_game_chat(db)
        game_message = game_chat_service.create_chat_message_record(
            db,
            ChatMessageCreate(chat_id=game_chat.id, message_body=body),
            game_owner,
        )
        sub_owner, sub_post, sub_chat = _seed_sub_chat(db)
        sub_message = sub_post_chat_service.create_sub_post_chat_message_workflow(
            db,
            sub_post.id,
            SubPostChatMessageCreate(chat_id=sub_chat.id, message_body=body),
            sub_owner,
        )

        persisted_groups = (
            list(
                db.scalars(
                    select(GameChatMessageDetection).where(
                        GameChatMessageDetection.message_id == game_message.id
                    )
                ).all()
            ),
            list(
                db.scalars(
                    select(SubPostChatMessageDetection).where(
                        SubPostChatMessageDetection.message_id == sub_message["id"]
                    )
                ).all()
            ),
        )
        for persisted in persisted_groups:
            selected = {
                detection.category: detection
                for detection in persisted
                if detection.category in expected
            }
            assert {
                category: detection.rule_key for category, detection in selected.items()
            } == expected
            assert {
                item.category: item.rule_key
                for item in serialize_detections(persisted)
                if item.category in expected
            } == expected


@pytest.mark.requirement("WS03-05A-R1", "WS03-05A-R3")
def test_game_repeated_query_uses_latest_visible_same_sender_text_with_id_tiebreak() -> (
    None
):
    with _session() as db:
        owner, chat = _seed_game_chat(db)
        other = _user(3)
        other_game = _game(owner, db.scalar(select(Venue)), 2)
        other_chat = GameChat(
            id=uuid.uuid4(), game_id=other_game.id, chat_status="active"
        )
        db.add(other)
        db.commit()
        db.add(other_game)
        db.commit()
        db.add(other_chat)
        db.commit()

        tied_at = _BASE_TIME
        eligible = ChatMessage(
            id=uuid.UUID(int=100),
            chat_id=chat.id,
            sender_user_id=owner.id,
            message_type="text",
            message_body="candidate",
            visibility_status="visible",
            review_status="clear",
            created_at=tied_at,
            updated_at=tied_at,
        )
        newer_id = ChatMessage(
            id=uuid.UUID(int=101),
            chat_id=chat.id,
            sender_user_id=owner.id,
            message_type="text",
            message_body="different",
            visibility_status="visible",
            review_status="clear",
            created_at=tied_at,
            updated_at=tied_at,
        )
        excluded = [
            ChatMessage(
                id=uuid.uuid4(),
                chat_id=chat.id,
                sender_user_id=other.id,
                message_type="text",
                message_body="candidate",
                visibility_status="visible",
                review_status="clear",
                created_at=tied_at + timedelta(minutes=3),
                updated_at=tied_at + timedelta(minutes=3),
            ),
            ChatMessage(
                id=uuid.uuid4(),
                chat_id=other_chat.id,
                sender_user_id=owner.id,
                message_type="text",
                message_body="candidate",
                visibility_status="visible",
                review_status="clear",
                created_at=tied_at + timedelta(minutes=2),
                updated_at=tied_at + timedelta(minutes=2),
            ),
            ChatMessage(
                id=uuid.uuid4(),
                chat_id=chat.id,
                sender_user_id=owner.id,
                message_type="system",
                message_body="candidate",
                visibility_status="visible",
                review_status="clear",
                created_at=tied_at + timedelta(minutes=1),
                updated_at=tied_at + timedelta(minutes=1),
            ),
        ]
        db.add_all([eligible, newer_id, *excluded])
        db.commit()

        assert (
            game_chat_service.sender_repeated_message(
                db, chat.id, owner.id, "candidate"
            )
            is None
        )
        newer_id.visibility_status = "removed"
        newer_id.removed_at = tied_at
        newer_id.removed_source = "sender"
        db.commit()
        fact = game_chat_service.sender_repeated_message(
            db, chat.id, owner.id, " CANDIDATE "
        )
        assert fact.reference_message_id == str(eligible.id)

        persisted_candidate = ChatMessage(
            id=uuid.uuid4(),
            chat_id=chat.id,
            sender_user_id=owner.id,
            message_type="text",
            message_body="candidate",
            visibility_status="visible",
            review_status="clear",
            created_at=tied_at + timedelta(minutes=4),
            updated_at=tied_at + timedelta(minutes=4),
        )
        db.add(persisted_candidate)
        db.commit()
        fact = game_chat_service.sender_repeated_message(
            db,
            chat.id,
            owner.id,
            "candidate",
            exclude_message_id=persisted_candidate.id,
        )
        assert fact.reference_message_id == str(eligible.id)


@pytest.mark.requirement("WS03-05A-R1", "WS03-05A-R3")
def test_need_a_sub_repeated_query_uses_latest_visible_same_sender_text_with_id_tiebreak() -> (
    None
):
    with _session() as db:
        owner, _post, chat = _seed_sub_chat(db)
        other = _user(4)
        other_post = _sub_post(owner, 2)
        other_chat = SubPostChat(
            id=uuid.uuid4(), sub_post_id=other_post.id, chat_status="active"
        )
        db.add(other)
        db.commit()
        db.add(other_post)
        db.commit()
        db.add(other_chat)
        db.commit()

        tied_at = _BASE_TIME
        eligible = SubPostChatMessage(
            id=uuid.UUID(int=100),
            chat_id=chat.id,
            sender_user_id=owner.id,
            sender_display_name_snapshot="Chat Owner",
            sender_initials_snapshot="CO",
            message_type="text",
            message_body="candidate",
            visibility_status="visible",
            review_status="clear",
            created_at=tied_at,
            updated_at=tied_at,
        )
        newer_id = SubPostChatMessage(
            id=uuid.UUID(int=101),
            chat_id=chat.id,
            sender_user_id=owner.id,
            sender_display_name_snapshot="Chat Owner",
            sender_initials_snapshot="CO",
            message_type="text",
            message_body="different",
            visibility_status="visible",
            review_status="clear",
            created_at=tied_at,
            updated_at=tied_at,
        )
        excluded = [
            SubPostChatMessage(
                id=uuid.uuid4(),
                chat_id=chat.id,
                sender_user_id=other.id,
                sender_display_name_snapshot="Other User",
                sender_initials_snapshot="OU",
                message_type="text",
                message_body="candidate",
                visibility_status="visible",
                review_status="clear",
                created_at=tied_at + timedelta(minutes=3),
                updated_at=tied_at + timedelta(minutes=3),
            ),
            SubPostChatMessage(
                id=uuid.uuid4(),
                chat_id=other_chat.id,
                sender_user_id=owner.id,
                sender_display_name_snapshot="Chat Owner",
                sender_initials_snapshot="CO",
                message_type="text",
                message_body="candidate",
                visibility_status="visible",
                review_status="clear",
                created_at=tied_at + timedelta(minutes=2),
                updated_at=tied_at + timedelta(minutes=2),
            ),
        ]
        db.add_all([eligible, newer_id, *excluded])
        db.commit()

        assert (
            sub_post_chat_service.sender_repeated_sub_chat_message(
                db, chat.id, owner.id, "candidate"
            )
            is None
        )
        newer_id.visibility_status = "removed"
        newer_id.removed_at = tied_at
        newer_id.removed_source = "sender"
        db.commit()
        fact = sub_post_chat_service.sender_repeated_sub_chat_message(
            db, chat.id, owner.id, " CANDIDATE "
        )
        assert fact.reference_message_id == str(eligible.id)

        persisted_candidate = SubPostChatMessage(
            id=uuid.uuid4(),
            chat_id=chat.id,
            sender_user_id=owner.id,
            sender_display_name_snapshot="Chat Owner",
            sender_initials_snapshot="CO",
            message_type="text",
            message_body="candidate",
            visibility_status="visible",
            review_status="clear",
            created_at=tied_at + timedelta(minutes=4),
            updated_at=tied_at + timedelta(minutes=4),
        )
        db.add(persisted_candidate)
        db.commit()
        fact = sub_post_chat_service.sender_repeated_sub_chat_message(
            db,
            chat.id,
            owner.id,
            "candidate",
            exclude_message_id=persisted_candidate.id,
        )
        assert fact.reference_message_id == str(eligible.id)

        persisted_candidate.visibility_status = "removed"
        persisted_candidate.removed_at = tied_at
        persisted_candidate.removed_source = "sender"
        eligible.visibility_status = "removed"
        eligible.removed_at = tied_at
        eligible.removed_source = "sender"
        db.commit()
        assert (
            sub_post_chat_service.sender_repeated_sub_chat_message(
                db, chat.id, owner.id, "candidate"
            )
            is None
        )


@pytest.mark.requirement("WS03-05A-R1", "WS03-05A-R3")
def test_need_a_sub_repeated_query_explicitly_filters_non_text_rows() -> None:
    class RecordingSession:
        statement = None

        def scalar(self, statement):
            self.statement = statement

    db = RecordingSession()
    assert (
        sub_post_chat_service.sender_repeated_sub_chat_message(
            db,
            uuid.uuid4(),
            uuid.uuid4(),
            "candidate",
        )
        is None
    )

    compiled = db.statement.compile()
    assert "sub_post_chat_messages.message_type" in str(compiled)
    assert "text" in compiled.params.values()


@pytest.mark.requirement("WS03-05A-R3", "WS03-05A-R5")
def test_game_chat_detection_failure_rolls_back_all_message_side_effects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _session() as db:
        owner, chat = _seed_game_chat(db)

        def fail_evidence(**kwargs):
            del kwargs
            raise ValueError("synthetic evidence validation failure")

        monkeypatch.setattr(
            game_chat_service,
            "chat_detection_record_values",
            fail_evidence,
        )
        with pytest.raises(ValueError, match="synthetic evidence"):
            game_chat_service.create_chat_message_record(
                db,
                ChatMessageCreate(chat_id=chat.id, message_body=_RISKY_BODY),
                owner,
            )

        assert _count(db, ChatMessage, ChatMessage.chat_id == chat.id) == 0
        assert _count(db, GameChatMessageDetection) == 0
        assert _count(db, GameChatRead, GameChatRead.chat_id == chat.id) == 0
        assert _count(db, AdminReviewSignal) == 0
        db.refresh(chat)
        assert chat.message_count == 0
        assert chat.latest_message_id is None


@pytest.mark.requirement("WS03-05A-R3", "WS03-05A-R5")
def test_need_a_sub_detection_failure_rolls_back_all_message_side_effects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _session() as db:
        owner, post, chat = _seed_sub_chat(db)

        def fail_evidence(**kwargs):
            del kwargs
            raise ValueError("synthetic evidence validation failure")

        monkeypatch.setattr(
            sub_post_chat_service,
            "chat_detection_record_values",
            fail_evidence,
        )
        with pytest.raises(ValueError, match="synthetic evidence"):
            sub_post_chat_service.create_sub_post_chat_message_workflow(
                db,
                post.id,
                SubPostChatMessageCreate(chat_id=chat.id, message_body=_RISKY_BODY),
                owner,
            )

        assert (
            _count(db, SubPostChatMessage, SubPostChatMessage.chat_id == chat.id) == 0
        )
        assert _count(db, SubPostChatMessageDetection) == 0
        assert _count(db, SubPostChatRead, SubPostChatRead.chat_id == chat.id) == 0
        assert _count(db, AdminReviewSignal) == 0
        db.refresh(chat)
        assert chat.message_count == 0
        assert chat.latest_message_id is None


@pytest.mark.requirement("WS03-05A-R3", "WS03-05A-R5", "WS03-05A-R6")
def test_game_chat_integrity_failure_is_sanitized_and_rolls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _session() as db:
        owner, chat = _seed_game_chat(db)

        def fail_with_canary(*args, **kwargs):
            del args, kwargs
            raise _canary_integrity_error()

        monkeypatch.setattr(
            game_chat_service,
            "replace_game_chat_message_detections",
            fail_with_canary,
        )
        with pytest.raises(HTTPException) as exc_info:
            game_chat_service.create_chat_message_record(
                db,
                ChatMessageCreate(chat_id=chat.id, message_body=_RISKY_BODY),
                owner,
            )

        assert exc_info.value.status_code == 409
        assert "CANARY-MODERATION-EVIDENCE" not in str(exc_info.value.detail)
        assert _count(db, ChatMessage, ChatMessage.chat_id == chat.id) == 0
        assert _count(db, GameChatMessageDetection) == 0


@pytest.mark.requirement("WS03-05A-R3", "WS03-05A-R5", "WS03-05A-R6")
def test_need_a_sub_chat_integrity_failure_is_sanitized_and_rolls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _session() as db:
        owner, post, chat = _seed_sub_chat(db)

        def fail_with_canary(*args, **kwargs):
            del args, kwargs
            raise _canary_integrity_error()

        monkeypatch.setattr(
            sub_post_chat_service,
            "replace_sub_chat_message_detections",
            fail_with_canary,
        )
        with pytest.raises(HTTPException) as exc_info:
            sub_post_chat_service.create_sub_post_chat_message_workflow(
                db,
                post.id,
                SubPostChatMessageCreate(chat_id=chat.id, message_body=_RISKY_BODY),
                owner,
            )

        assert exc_info.value.status_code == 409
        assert "CANARY-MODERATION-EVIDENCE" not in str(exc_info.value.detail)
        assert (
            _count(db, SubPostChatMessage, SubPostChatMessage.chat_id == chat.id) == 0
        )
        assert _count(db, SubPostChatMessageDetection) == 0


@pytest.mark.requirement("WS03-05A-R3", "WS03-05A-R6")
def test_integrity_error_logging_never_renders_evidence_canary(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    error = _canary_integrity_error()
    target_id = uuid.uuid4()
    moderation_surfacing_service.log_moderation_integrity_failure(
        operation="Synthetic moderation reconciliation",
        target_id=target_id,
        error=error,
    )

    class FakeSession:
        def rollback(self) -> None:
            return None

    def fail_surfacing(*args, **kwargs):
        del args, kwargs
        raise error

    monkeypatch.setattr(
        moderation_signal_service,
        "surface_moderation_findings",
        fail_surfacing,
    )
    moderation_signal_service.run_moderation_surfacing_safely(
        FakeSession(),
        target_type="community_game_chat",
        target_data={"target_game_id": target_id},
        findings=[],
        scanned_field_hashes={"message_body": "0" * 64},
    )

    assert "CANARY-MODERATION-EVIDENCE" not in caplog.text


@pytest.mark.requirement("WS03-05A-R3", "WS03-05A-R6")
def test_chat_signal_exception_log_excludes_sensitive_evidence(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    class FakeSession:
        def rollback(self) -> None:
            return None

    def fail_with_sensitive_evidence(*args, **kwargs):
        del args, kwargs
        raise _sensitive_database_error()

    monkeypatch.setattr(
        moderation_signal_service,
        "surface_moderation_findings",
        fail_with_sensitive_evidence,
    )
    moderation_signal_service.run_moderation_surfacing_safely(
        FakeSession(),
        target_type="community_game_chat",
        target_data={"target_game_id": uuid.uuid4()},
        findings=[],
        scanned_field_hashes={"message_body": "0" * 64},
    )

    assert _SENSITIVE_EXCEPTION_CANARY not in caplog.text
    assert "OperationalError" in caplog.text
    assert all(record.exc_info is None for record in caplog.records)


@pytest.mark.requirement("WS03-05A-R5", "WS03-05A-R6")
def test_postgresql_rejects_malformed_and_duplicate_chat_detection_identity() -> None:
    with _session() as db:
        owner, chat = _seed_game_chat(db)
        message = game_chat_service.create_chat_message_record(
            db,
            ChatMessageCreate(chat_id=chat.id, message_body=_RISKY_BODY),
            owner,
        )
        valid = db.scalar(
            select(GameChatMessageDetection).where(
                GameChatMessageDetection.message_id == message.id
            )
        )
        values = {
            column.key: getattr(valid, column.key)
            for column in GameChatMessageDetection.__table__.columns
        }

        bad_hash = dict(values, id=uuid.uuid4(), source_content_hash="invalid")
        with pytest.raises(IntegrityError) as bad_hash_exc, db.begin_nested():
            db.execute(GameChatMessageDetection.__table__.insert(), [bad_hash])
        assert (
            bad_hash_exc.value.orig.diag.constraint_name
            == "ck_game_chat_message_detections_source_hash"
        )

        mixed_evidence = dict(
            values,
            id=uuid.uuid4(),
            detection_identity_hash="b" * 64,
            evidence={"start": 0},
        )
        with pytest.raises(IntegrityError) as evidence_exc, db.begin_nested():
            db.execute(GameChatMessageDetection.__table__.insert(), [mixed_evidence])
        assert (
            evidence_exc.value.orig.diag.constraint_name
            == "ck_game_chat_message_detections_evidence_shape"
        )

        duplicate = dict(values, id=uuid.uuid4())
        with pytest.raises(IntegrityError) as duplicate_exc, db.begin_nested():
            db.execute(GameChatMessageDetection.__table__.insert(), [duplicate])
        assert (
            duplicate_exc.value.orig.diag.constraint_name
            == "uq_game_chat_message_detections_message_identity"
        )


@pytest.mark.requirement("WS03-05A-R3", "WS03-05A-R6")
def test_postgresql_rejects_json_null_discriminators_and_blank_rule_keys() -> None:
    with _session() as db:
        game_owner, game_chat = _seed_game_chat(db)
        game_message = game_chat_service.create_chat_message_record(
            db,
            ChatMessageCreate(chat_id=game_chat.id, message_body=_RISKY_BODY),
            game_owner,
        )
        sub_owner, sub_post, sub_chat = _seed_sub_chat(db)
        sub_message = sub_post_chat_service.create_sub_post_chat_message_workflow(
            db,
            sub_post.id,
            SubPostChatMessageCreate(chat_id=sub_chat.id, message_body=_RISKY_BODY),
            sub_owner,
        )
        rows = (
            (
                GameChatMessageDetection,
                db.scalar(
                    select(GameChatMessageDetection).where(
                        GameChatMessageDetection.message_id == game_message.id
                    )
                ),
                "ck_game_chat_message_detections_evidence_shape",
                "ck_game_chat_message_detections_rule_key_present",
            ),
            (
                SubPostChatMessageDetection,
                db.scalar(
                    select(SubPostChatMessageDetection).where(
                        SubPostChatMessageDetection.message_id == sub_message["id"]
                    )
                ),
                "ck_sub_post_chat_message_detections_evidence_shape",
                "ck_sub_post_chat_message_detections_rule_key_present",
            ),
        )

        for model, valid, evidence_constraint, key_constraint in rows:
            values = {
                column.key: getattr(valid, column.key)
                for column in model.__table__.columns
            }
            null_kind = dict(
                values,
                id=uuid.uuid4(),
                detection_identity_hash=uuid.uuid4().hex * 2,
                evidence={"evidence_kind": None},
            )
            with pytest.raises(IntegrityError) as null_exc, db.begin_nested():
                db.execute(model.__table__.insert(), [null_kind])
            assert null_exc.value.orig.diag.constraint_name == evidence_constraint

            blank_key = dict(
                values,
                id=uuid.uuid4(),
                detection_identity_hash=uuid.uuid4().hex * 2,
                rule_key="   ",
            )
            with pytest.raises(IntegrityError) as key_exc, db.begin_nested():
                db.execute(model.__table__.insert(), [blank_key])
            assert key_exc.value.orig.diag.constraint_name == key_constraint
