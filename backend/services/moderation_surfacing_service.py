"""Moderation surfacing adapters for saved Community Game and Need a Sub text."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
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
from backend.services.content_moderation_scanner_service import (
    FIELD_PURPOSE_GENERAL,
    FIELD_PURPOSE_LOCATION,
    FIELD_PURPOSE_PAYMENT,
    FIELD_PURPOSE_PAYMENT_METHOD,
    MODERATION_DOMAIN_CHAT,
    ModerationTextField,
    ModerationFinding,
    SCANNER_VERSION,
    build_review_excerpt,
    content_hash,
)
from backend.services.content_moderation_evidence_service import (
    build_content_moderation_findings,
)
from backend.services.admin_review_actionability_service import (
    is_game_content_review_actionable,
    is_sub_post_content_review_actionable,
)
from backend.services.content_moderation_finding_service import (
    run_content_moderation_finding_reconciliation_safely,
)
from backend.services.moderation_signal_service import (
    CHAT_MODERATION_SOURCE,
    run_moderation_surfacing_safely,
)

logger = logging.getLogger(__name__)


def compact_snapshot_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        parts = [
            compact_snapshot_text(item)
            for key, item in sorted(value.items())
            if key in {"type", "label", "name", "value", "note", "details", "instructions"}
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
        select(CommunityGameDetail).where(CommunityGameDetail.game_id == game_id)
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
    game = db.get(Game, game_id)
    if game is None or game.game_type != "community":
        return
    if not is_game_content_review_actionable(game):
        return

    detail = get_community_game_detail(db, game.id)
    fields = build_community_game_moderation_fields(game, detail)
    scanned_field_values = {field.field_name: field.value for field in fields}
    try:
        findings = build_content_moderation_findings(fields)
    except Exception:
        db.rollback()
        logger.exception(
            "Community game moderation scanner failed for game %s.",
            game.id,
        )
        return
    current_game = db.get(Game, game_id, populate_existing=True)
    if (
        current_game is None
        or current_game.game_type != "community"
        or not is_game_content_review_actionable(current_game)
    ):
        return
    current_detail = get_community_game_detail(db, current_game.id)
    current_fields = build_community_game_moderation_fields(
        current_game,
        current_detail,
    )
    if scanned_field_values != {
        field.field_name: field.value for field in current_fields
    }:
        return
    run_content_moderation_finding_reconciliation_safely(
        db,
        target_data={"target_game_id": current_game.id},
        findings=findings,
        scanned_field_values=scanned_field_values,
    )


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
    sub_post = db.get(SubPost, sub_post_id)
    if not is_sub_post_content_review_actionable(sub_post):
        return

    fields = build_need_a_sub_moderation_fields(sub_post)
    scanned_field_values = {field.field_name: field.value for field in fields}
    try:
        findings = build_content_moderation_findings(fields)
    except Exception:
        db.rollback()
        logger.exception(
            "Need a Sub moderation scanner failed for post %s.",
            sub_post.id,
        )
        return
    current_sub_post = db.get(SubPost, sub_post_id, populate_existing=True)
    if not is_sub_post_content_review_actionable(current_sub_post):
        return
    current_fields = build_need_a_sub_moderation_fields(current_sub_post)
    if scanned_field_values != {
        field.field_name: field.value for field in current_fields
    }:
        return
    run_content_moderation_finding_reconciliation_safely(
        db,
        target_data={"target_sub_post_id": current_sub_post.id},
        findings=findings,
        scanned_field_values=scanned_field_values,
    )


def detection_priority(severity: str) -> str:
    return "urgent" if severity == "high" else "attention"


def aggregate_chat_detections(
    *,
    message_body: str,
    detections: list[GameChatMessageDetection | SubPostChatMessageDetection],
) -> list[ModerationFinding]:
    if not detections:
        return []

    severity_rank = {"low": 0, "medium": 1, "high": 2}
    highest = max(
        detections,
        key=lambda detection: severity_rank.get(detection.severity, 0),
    )
    excerpt = build_review_excerpt(message_body)
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
            content_hash=content_hash(message_body),
            matched_rule_ids=tuple(
                dict.fromkeys(detection.rule_key for detection in detections)
            ),
            scanner_version=SCANNER_VERSION,
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
    findings = aggregate_chat_detections(
        message_body=message.message_body,
        detections=detections,
    )
    message_id_text = str(message.id)
    run_moderation_surfacing_safely(
        db,
        target_type="community_game_chat",
        target_data={"target_game_id": chat.game_id},
        findings=findings,
        scanned_field_values={"message_body": message.message_body},
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
    findings = aggregate_chat_detections(
        message_body=message.message_body,
        detections=detections,
    )
    message_id_text = str(message.id)
    run_moderation_surfacing_safely(
        db,
        target_type="need_a_sub_chat",
        target_data={"target_sub_post_id": chat.sub_post_id},
        findings=findings,
        scanned_field_values={"message_body": message.message_body},
        source=CHAT_MODERATION_SOURCE,
        extra_metadata={
            "chat_scope": "need_a_sub",
            "chat_id": str(chat.id),
            "message_id": message_id_text,
            "sender_user_id": str(message.sender_user_id),
        },
        metadata_filters={"message_id": message_id_text},
    )
