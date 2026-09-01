"""Moderation surfacing adapters for saved Community Game and Need a Sub text."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import (
    ChatMessage,
    CommunityGameDetail,
    Game,
    GameChat,
    GameChatMessageDetection,
    SubPost,
    SubPostChat,
    SubPostChatMessage,
    SubPostChatMessageDetection,
)
from backend.services.admin_review_actionability_service import (
    is_game_content_review_actionable,
    is_sub_post_content_review_actionable,
)
from backend.services.content_moderation_evidence_service import (
    build_content_moderation_findings,
)
from backend.services.content_moderation_finding_service import (
    reconcile_content_moderation_findings,
)
from backend.services.content_moderation_scanner_service import (
    MODERATION_DOMAIN_CHAT,
    ModerationFinding,
    ModerationTextField,
    ScanProvenance,
    build_review_excerpt,
)
from backend.services.moderation_evidence_service import validate_chat_evidence
from backend.services.moderation_signal_service import (
    CHAT_MODERATION_SOURCE,
    run_moderation_surfacing_safely,
)
from backend.services.moderation_taxonomy import (
    FIELD_PURPOSE_GENERAL,
    FIELD_PURPOSE_LOCATION,
    FIELD_PURPOSE_PAYMENT,
    FIELD_PURPOSE_PAYMENT_METHOD,
    TARGET_CONTEXT_COMMUNITY_GAME,
    TARGET_CONTEXT_GAME_CHAT,
    TARGET_CONTEXT_NEED_A_SUB,
    TARGET_CONTEXT_NEED_A_SUB_CHAT,
)

logger = logging.getLogger(__name__)

RETRYABLE_MODERATION_CONSTRAINTS = frozenset(
    {
        "uq_admin_review_cases_open_community_game_content_moderation",
        "uq_admin_review_cases_open_need_sub_content_moderation",
        "uq_admin_content_moderation_findings_current_identity",
    }
)


def integrity_error_constraint_name(error: IntegrityError) -> str | None:
    diagnostic = getattr(getattr(error, "orig", None), "diag", None)
    constraint_name = getattr(diagnostic, "constraint_name", None)
    return constraint_name if isinstance(constraint_name, str) else None


def is_retryable_moderation_creation_race(error: IntegrityError) -> bool:
    return integrity_error_constraint_name(error) in RETRYABLE_MODERATION_CONSTRAINTS


def log_moderation_integrity_failure(
    *,
    operation: str,
    target_id: uuid.UUID,
    error: IntegrityError,
) -> None:
    logger.error(
        "%s failed for target %s (constraint=%s).",
        operation,
        target_id,
        integrity_error_constraint_name(error) or "unknown",
    )


def compact_snapshot_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        parts = [
            compact_snapshot_text(item)
            for key, item in sorted(value.items())
            if key
            in {"type", "label", "name", "value", "note", "details", "instructions"}
        ]
        return " ".join(part for part in parts if part)
    if isinstance(value, list):
        parts = [compact_snapshot_text(item) for item in value]
        return " ".join(part for part in parts if part)
    return None


def get_community_game_detail(
    db: Session,
    game_id: uuid.UUID,
) -> CommunityGameDetail | None:
    return db.scalar(
        select(CommunityGameDetail)
        .where(CommunityGameDetail.game_id == game_id)
        .with_for_update()
    )


def build_community_game_moderation_fields(
    game: Game,
    detail: CommunityGameDetail | None,
) -> list[ModerationTextField]:
    return [
        ModerationTextField("title", "Title", game.title, FIELD_PURPOSE_GENERAL),
        ModerationTextField(
            "description",
            "Description",
            game.description,
            FIELD_PURPOSE_GENERAL,
        ),
        ModerationTextField(
            "game_notes",
            "Game notes",
            game.game_notes,
            FIELD_PURPOSE_GENERAL,
        ),
        ModerationTextField(
            "parking_notes",
            "Parking notes",
            game.parking_notes,
            FIELD_PURPOSE_LOCATION,
        ),
        ModerationTextField(
            "custom_rules_text",
            "Custom rules",
            game.custom_rules_text,
            FIELD_PURPOSE_GENERAL,
        ),
        ModerationTextField(
            "payment_instructions_snapshot",
            "Payment instructions",
            detail.payment_instructions_snapshot if detail is not None else None,
            FIELD_PURPOSE_PAYMENT,
        ),
        ModerationTextField(
            "payment_methods_snapshot",
            "Payment methods",
            compact_snapshot_text(
                detail.payment_methods_snapshot if detail is not None else None
            ),
            FIELD_PURPOSE_PAYMENT_METHOD,
        ),
    ]


def surface_community_game_text(
    db: Session,
    *,
    game_id: uuid.UUID,
) -> None:
    for attempt in range(2):
        try:
            game = db.scalar(select(Game).where(Game.id == game_id).with_for_update())
            if (
                game is None
                or game.game_type != "community"
                or not is_game_content_review_actionable(game)
            ):
                db.rollback()
                return
            detail = get_community_game_detail(db, game.id)
            fields = build_community_game_moderation_fields(game, detail)
            scan_result = build_content_moderation_findings(
                fields,
                target_context=TARGET_CONTEXT_COMMUNITY_GAME,
            )
            reconcile_content_moderation_findings(
                db,
                target_data={"target_game_id": game.id},
                scan_result=scan_result,
            )
            return
        except IntegrityError as exc:
            db.rollback()
            if attempt == 0 and is_retryable_moderation_creation_race(exc):
                continue
            log_moderation_integrity_failure(
                operation="Community game moderation reconciliation",
                target_id=game_id,
                error=exc,
            )
            return
        except Exception as exc:  # noqa: BLE001 - fail-safe moderation boundary
            db.rollback()
            logger.error(
                "Community game moderation reconciliation failed for game %s "
                "(error_type=%s).",
                game_id,
                type(exc).__name__,
            )
            return


def build_need_a_sub_moderation_fields(sub_post: SubPost) -> list[ModerationTextField]:
    return [
        ModerationTextField(
            "team_name",
            "Team name",
            sub_post.team_name,
            FIELD_PURPOSE_GENERAL,
        ),
        ModerationTextField(
            "location_name",
            "Location name",
            sub_post.location_name,
            FIELD_PURPOSE_LOCATION,
        ),
        ModerationTextField(
            "neighborhood",
            "Neighborhood",
            sub_post.neighborhood,
            FIELD_PURPOSE_LOCATION,
        ),
        ModerationTextField(
            "payment_note",
            "Payment note",
            sub_post.payment_note,
            FIELD_PURPOSE_PAYMENT,
        ),
        ModerationTextField(
            "notes",
            "Notes",
            sub_post.notes,
            FIELD_PURPOSE_GENERAL,
        ),
    ]


def surface_need_a_sub_post_text(
    db: Session,
    *,
    sub_post_id: uuid.UUID,
) -> None:
    for attempt in range(2):
        try:
            sub_post = db.scalar(
                select(SubPost).where(SubPost.id == sub_post_id).with_for_update()
            )
            if not is_sub_post_content_review_actionable(sub_post):
                db.rollback()
                return
            fields = build_need_a_sub_moderation_fields(sub_post)
            scan_result = build_content_moderation_findings(
                fields,
                target_context=TARGET_CONTEXT_NEED_A_SUB,
            )
            reconcile_content_moderation_findings(
                db,
                target_data={"target_sub_post_id": sub_post.id},
                scan_result=scan_result,
            )
            return
        except IntegrityError as exc:
            db.rollback()
            if attempt == 0 and is_retryable_moderation_creation_race(exc):
                continue
            log_moderation_integrity_failure(
                operation="Need a Sub moderation reconciliation",
                target_id=sub_post_id,
                error=exc,
            )
            return
        except Exception as exc:  # noqa: BLE001 - fail-safe moderation boundary
            db.rollback()
            logger.error(
                "Need a Sub moderation reconciliation failed for post %s "
                "(error_type=%s).",
                sub_post_id,
                type(exc).__name__,
            )
            return


def detection_priority(severity: str) -> str:
    return "urgent" if severity == "high" else "attention"


def aggregate_chat_detections(
    *,
    message_body: str,
    detections: list[GameChatMessageDetection | SubPostChatMessageDetection],
    expected_target_context: str,
) -> list[ModerationFinding]:
    if not detections:
        return []

    severity_rank = {"low": 0, "medium": 1, "high": 2}
    highest = max(
        detections,
        key=lambda detection: severity_rank.get(detection.severity, 0),
    )
    excerpt = build_review_excerpt(message_body)
    first = detections[0]
    provenance_fields = (
        "scanner_id",
        "scanner_version",
        "taxonomy_version",
        "configuration_hash",
        "canonicalization_version",
        "evidence_format_version",
        "target_context",
        "declared_limits",
        "scanned_at",
        "execution_duration_us",
        "source_content_hash",
        "source_field",
        "field_purpose",
    )
    if any(
        getattr(detection, field) != getattr(first, field)
        for detection in detections[1:]
        for field in provenance_fields
    ):
        raise ValueError("Chat detections do not share one scan provenance.")
    if first.target_context != expected_target_context:
        raise ValueError("Chat detection target context is not authoritative.")
    for detection in detections:
        matched_versions = detection.matched_rule_versions
        if not isinstance(matched_versions, list) or len(matched_versions) != 1:
            raise ValueError("Chat detection rule attribution is not canonical.")
        matched_version = matched_versions[0]
        if not isinstance(matched_version, dict):
            raise TypeError("Chat detection rule attribution is not canonical.")
        registry_rule_id = matched_version.get("rule_id")
        rule_version = matched_version.get("rule_version")
        if not isinstance(registry_rule_id, str) or not isinstance(rule_version, str):
            raise TypeError("Chat detection rule attribution is not canonical.")
        validate_chat_evidence(
            source_text=message_body,
            category=detection.category,
            severity=detection.severity,
            target_context=detection.target_context,
            source_field=detection.source_field,
            field_purpose=detection.field_purpose,
            source_content_hash=detection.source_content_hash,
            evidence_fingerprint=detection.evidence_fingerprint,
            evidence=detection.evidence,
            public_rule_key=detection.rule_key,
            registry_rule_id=registry_rule_id,
            rule_version=rule_version,
            matched_rule_versions=matched_versions,
            matched_preview=detection.matched_preview,
            canonicalization_version=detection.canonicalization_version,
        )
    provenance = ScanProvenance(
        scanner_id=first.scanner_id,
        scanner_version=first.scanner_version,
        taxonomy_version=first.taxonomy_version,
        configuration_hash=first.configuration_hash,
        canonicalization_version=first.canonicalization_version,
        evidence_format_version=first.evidence_format_version,
        target_context=first.target_context,
        declared_limits=tuple(first.declared_limits),
        scanned_at=first.scanned_at,
        execution_duration_us=first.execution_duration_us,
    )
    return [
        ModerationFinding(
            signal_category="chat_moderation",
            moderation_domain=MODERATION_DOMAIN_CHAT,
            detected_categories=tuple(
                dict.fromkeys(detection.category for detection in detections)
            ),
            severity=highest.severity,
            priority=detection_priority(highest.severity),
            field_name="message_body",
            field_label="Chat message",
            excerpt=excerpt,
            content_hash=first.source_content_hash,
            matched_rule_ids=tuple(
                dict.fromkeys(detection.rule_key for detection in detections)
            ),
            matched_rule_versions=tuple(
                item
                for detection in detections
                for item in detection.matched_rule_versions
            ),
            provenance=provenance,
        )
    ]


def surface_game_chat_message_text(
    db: Session,
    *,
    message_id: uuid.UUID,
) -> None:
    row = db.execute(
        select(ChatMessage, GameChat, Game)
        .join(GameChat, GameChat.id == ChatMessage.chat_id)
        .join(Game, Game.id == GameChat.game_id)
        .where(ChatMessage.id == message_id)
    ).one_or_none()
    if row is None:
        return

    message, chat, game = row
    if game.game_type != "community":
        return

    detections = list(
        db.scalars(
            select(GameChatMessageDetection)
            .where(GameChatMessageDetection.message_id == message.id)
            .order_by(GameChatMessageDetection.created_at.asc())
        ).all()
    )
    if not detections:
        return
    findings = aggregate_chat_detections(
        message_body=message.message_body,
        detections=detections,
        expected_target_context=TARGET_CONTEXT_GAME_CHAT,
    )
    message_id_text = str(message.id)
    run_moderation_surfacing_safely(
        db,
        target_type="community_game_chat",
        target_data={"target_game_id": chat.game_id},
        findings=findings,
        scanned_field_hashes={"message_body": detections[0].source_content_hash},
        source=CHAT_MODERATION_SOURCE,
        extra_metadata={
            "chat_scope": "community_game",
            "chat_id": str(chat.id),
            "message_id": message_id_text,
            "sender_user_id": str(message.sender_user_id),
        },
        metadata_filters={"message_id": message_id_text},
    )


def surface_need_a_sub_chat_message_text(
    db: Session,
    *,
    message_id: uuid.UUID,
) -> None:
    row = db.execute(
        select(SubPostChatMessage, SubPostChat)
        .join(SubPostChat, SubPostChat.id == SubPostChatMessage.chat_id)
        .where(SubPostChatMessage.id == message_id)
    ).one_or_none()
    if row is None:
        return

    message, chat = row
    detections = list(
        db.scalars(
            select(SubPostChatMessageDetection)
            .where(SubPostChatMessageDetection.message_id == message.id)
            .order_by(SubPostChatMessageDetection.created_at.asc())
        ).all()
    )
    if not detections:
        return
    findings = aggregate_chat_detections(
        message_body=message.message_body,
        detections=detections,
        expected_target_context=TARGET_CONTEXT_NEED_A_SUB_CHAT,
    )
    message_id_text = str(message.id)
    run_moderation_surfacing_safely(
        db,
        target_type="need_a_sub_chat",
        target_data={"target_sub_post_id": chat.sub_post_id},
        findings=findings,
        scanned_field_hashes={"message_body": detections[0].source_content_hash},
        source=CHAT_MODERATION_SOURCE,
        extra_metadata={
            "chat_scope": "need_a_sub",
            "chat_id": str(chat.id),
            "message_id": message_id_text,
            "sender_user_id": str(message.sender_user_id),
        },
        metadata_filters={"message_id": message_id_text},
    )
