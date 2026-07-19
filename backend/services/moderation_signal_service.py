"""Create internal review signals from deterministic moderation findings."""

from __future__ import annotations

import hashlib
import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import AdminReviewCase, AdminReviewSignal
from backend.services.admin_review_service import create_internal_review_signal
from backend.services.content_moderation_scanner_service import (
    ModerationFinding,
    content_hash,
    scanner_timestamp,
)

logger = logging.getLogger(__name__)

CHAT_MODERATION_SOURCE = "chat_moderation"
ACTIVE_REVIEW_CASE_STATUSES = ("open",)


def build_signal_idempotency_key(
    *,
    source: str,
    target_type: str,
    target_id: uuid.UUID,
    signal_category: str,
    field_name: str,
    moderation_domain: str,
    content_hash_value: str,
    extra_key: str | None = None,
) -> str:
    seed = "|".join(
        [
            source,
            target_type,
            str(target_id),
            signal_category,
            field_name,
            moderation_domain,
            content_hash_value,
            extra_key or "",
        ]
    )
    return f"moderation:{hashlib.sha256(seed.encode('utf-8')).hexdigest()}"


def primary_target_from_data(
    target_data: dict[str, uuid.UUID | None],
) -> tuple[str, uuid.UUID] | None:
    for field_name in (
        "target_game_id",
        "target_sub_post_id",
        "target_sub_post_request_id",
        "target_payment_id",
        "target_financial_outcome_id",
        "target_user_id",
    ):
        target_id = target_data.get(field_name)
        if target_id is not None:
            return field_name, target_id
    return None


def build_signal_metadata(
    finding: ModerationFinding,
    *,
    target_type: str,
    scanned_at: str,
    extra_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "target_type": target_type,
        "field_name": finding.field_name,
        "field_label": finding.field_label,
        "excerpt": finding.excerpt,
        "content_hash": finding.content_hash,
        "original_content_hash": finding.content_hash,
        "latest_content_hash": finding.content_hash,
        "detected_categories": list(finding.detected_categories),
        "moderation_domain": finding.moderation_domain,
        "severity": finding.severity,
        "scanner_version": finding.scanner_version,
        "matched_rule_ids": list(finding.matched_rule_ids),
        "current_match": True,
        "superseded_by_content_change": False,
        "last_scanned_at": scanned_at,
    }
    if extra_metadata:
        metadata.update(extra_metadata)
    return metadata


def build_signal_title(finding: ModerationFinding) -> str:
    return "Chat message needs review"


def build_signal_summary(finding: ModerationFinding) -> str:
    categories = ", ".join(finding.detected_categories)
    return f"{finding.field_label} matched {categories}."


def mark_superseded_signals(
    db: Session,
    *,
    target_data: dict[str, uuid.UUID | None],
    source: str,
    signal_categories: set[str],
    scanned_field_hashes: dict[str, str],
    current_keys: set[tuple[str, str, str, str]],
    scanned_at: str,
    metadata_filters: dict[str, str] | None = None,
) -> None:
    primary_target = primary_target_from_data(target_data)
    if primary_target is None:
        return

    target_field, target_id = primary_target
    signals = list(
        db.scalars(
            select(AdminReviewSignal)
            .join(
                AdminReviewCase,
                AdminReviewCase.id == AdminReviewSignal.review_case_id,
            )
            .where(
                AdminReviewCase.case_status.in_(ACTIVE_REVIEW_CASE_STATUSES),
                AdminReviewSignal.source == source,
                AdminReviewSignal.signal_category.in_(signal_categories),
                getattr(AdminReviewSignal, target_field) == target_id,
            )
            .order_by(AdminReviewSignal.created_at.asc(), AdminReviewSignal.id.asc())
        ).all()
    )

    changed = False
    for signal in signals:
        metadata = dict(signal.metadata_ or {})
        field_name = metadata.get("field_name")
        moderation_domain = metadata.get("moderation_domain")
        original_hash = metadata.get("content_hash") or metadata.get("original_content_hash")
        if not isinstance(field_name, str) or not isinstance(moderation_domain, str):
            continue
        if not isinstance(original_hash, str):
            continue
        if field_name not in scanned_field_hashes:
            continue
        if metadata_filters and any(
            str(metadata.get(key) or "") != str(value)
            for key, value in metadata_filters.items()
        ):
            continue

        signal_key = (
            signal.signal_category,
            field_name,
            moderation_domain,
            original_hash,
        )
        latest_hash = scanned_field_hashes[field_name]
        if signal_key in current_keys:
            if metadata.get("current_match") is not True:
                metadata["current_match"] = True
                metadata["superseded_by_content_change"] = False
                metadata["latest_content_hash"] = latest_hash
                metadata["last_scanned_at"] = scanned_at
                signal.metadata_ = metadata
                changed = True
            continue

        if metadata.get("current_match") is False and metadata.get("latest_content_hash") == latest_hash:
            continue

        metadata["current_match"] = False
        metadata["superseded_by_content_change"] = True
        metadata["latest_content_hash"] = latest_hash
        metadata["last_scanned_at"] = scanned_at
        signal.metadata_ = metadata
        changed = True

    if changed:
        db.commit()


def surface_moderation_findings(
    db: Session,
    *,
    target_type: str,
    target_data: dict[str, uuid.UUID | None],
    findings: list[ModerationFinding],
    scanned_field_hashes: dict[str, str],
    source: str = CHAT_MODERATION_SOURCE,
    extra_metadata: dict[str, Any] | None = None,
    metadata_filters: dict[str, str] | None = None,
) -> None:
    primary_target = primary_target_from_data(target_data)
    if primary_target is None:
        return

    _target_field, target_id = primary_target
    scanned_at = scanner_timestamp()
    current_keys: set[tuple[str, str, str, str]] = set()
    signal_categories = {"chat_moderation"}
    signal_categories.update(finding.signal_category for finding in findings)
    for finding in findings:
        current_keys.add(
            (
                finding.signal_category,
                finding.field_name,
                finding.moderation_domain,
                finding.content_hash,
            )
        )
        metadata = build_signal_metadata(
            finding,
            target_type=target_type,
            scanned_at=scanned_at,
            extra_metadata=extra_metadata,
        )
        create_internal_review_signal(
            db,
            signal_category=finding.signal_category,
            source=source,
            priority=finding.priority,
            title=build_signal_title(finding),
            summary=build_signal_summary(finding),
            target_data=target_data,
            metadata=metadata,
            idempotency_key=build_signal_idempotency_key(
                source=source,
                target_type=target_type,
                target_id=target_id,
                signal_category=finding.signal_category,
                field_name=finding.field_name,
                moderation_domain=finding.moderation_domain,
                content_hash_value=finding.content_hash,
                extra_key=(
                    str(extra_metadata.get("message_id"))
                    if extra_metadata and extra_metadata.get("message_id")
                    else None
                ),
            ),
        )

    mark_superseded_signals(
        db,
        target_data=target_data,
        source=source,
        signal_categories=signal_categories,
        scanned_field_hashes=scanned_field_hashes,
        current_keys=current_keys,
        scanned_at=scanned_at,
        metadata_filters=metadata_filters,
    )


def run_moderation_surfacing_safely(
    db: Session,
    *,
    target_type: str,
    target_data: dict[str, uuid.UUID | None],
    findings: list[ModerationFinding],
    scanned_field_values: dict[str, str | None],
    source: str = CHAT_MODERATION_SOURCE,
    extra_metadata: dict[str, Any] | None = None,
    metadata_filters: dict[str, str] | None = None,
) -> None:
    try:
        surface_moderation_findings(
            db,
            target_type=target_type,
            target_data=target_data,
            findings=findings,
            scanned_field_hashes={
                field_name: content_hash(value)
                for field_name, value in scanned_field_values.items()
            },
            source=source,
            extra_metadata=extra_metadata,
            metadata_filters=metadata_filters,
        )
    except Exception:
        db.rollback()
        logger.exception(
            "Moderation surfacing failed for %s target %s.",
            target_type,
            target_data,
        )
