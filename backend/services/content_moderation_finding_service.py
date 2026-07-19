"""Persist and reconcile content moderation findings for review cases."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import (
    AdminContentModerationFinding,
    AdminReviewCase,
)
from backend.services.admin_review_service import (
    CASE_ACTIVE_STATUSES,
    CONTENT_MODERATION_CASE_CATEGORY,
    PRIORITY_RANK,
    build_content_moderation_case_summary,
    build_content_moderation_case_title,
    copy_targets,
    create_case_event,
    find_open_case_for_signal,
    infer_case_type,
    primary_target,
    validate_target_references,
)
from backend.services.content_moderation_evidence_service import (
    ContentModerationFinding,
)
from backend.services.content_moderation_scanner_service import content_hash

logger = logging.getLogger(__name__)

VALID_CONTENT_REVIEW_CASE_TYPES = {"community_game", "need_a_sub"}


def validate_content_moderation_case_for_findings(review_case: AdminReviewCase) -> None:
    if (
        review_case.case_category != CONTENT_MODERATION_CASE_CATEGORY
        or review_case.case_type not in VALID_CONTENT_REVIEW_CASE_TYPES
        or review_case.case_status not in CASE_ACTIVE_STATUSES
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Review case is not open for content moderation findings.",
        )


def get_or_create_open_content_moderation_case(
    db: Session,
    *,
    target_data: dict[str, uuid.UUID | None],
    priority: str,
    now: datetime,
) -> tuple[AdminReviewCase | None, bool]:
    review_case = find_open_case_for_signal(
        db,
        target_data=target_data,
        case_category=CONTENT_MODERATION_CASE_CATEGORY,
    )
    if review_case is not None:
        validate_content_moderation_case_for_findings(review_case)
        return review_case, False

    case_type = infer_case_type(db, target_data)
    if case_type not in VALID_CONTENT_REVIEW_CASE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Content moderation findings require a Community Game or Need a Sub target.",
        )

    review_case = AdminReviewCase(
        id=uuid.uuid4(),
        case_type=case_type,
        case_status="open",
        case_category=CONTENT_MODERATION_CASE_CATEGORY,
        priority=priority,
        title=build_content_moderation_case_title(case_type),
        summary=build_content_moderation_case_summary(case_type),
        opened_by_user_id=None,
        created_at=now,
        updated_at=now,
        **copy_targets(target_data),
    )
    db.add(review_case)
    db.flush()
    create_case_event(
        db,
        review_case_id=review_case.id,
        event_type="case_created",
        actor_user_id=None,
        event_metadata={"source": "content_moderation_scanner"},
        created_at=now,
    )
    return review_case, True


def finding_identity(
    finding: ContentModerationFinding | AdminContentModerationFinding,
) -> tuple[str, str, str]:
    return (
        finding.source_field,
        finding.finding_type,
        finding.evidence_fingerprint,
    )


def build_finding_metadata(finding: ContentModerationFinding) -> dict:
    return {
        "matched_rule_ids": list(finding.matched_rule_ids),
        "scanner_version": finding.scanner_version,
        "source": "content_moderation_scanner",
    }


def priority_for_current_findings(
    findings: list[AdminContentModerationFinding],
) -> str:
    current_priorities = [
        finding.priority for finding in findings if finding.current_match
    ]
    if not current_priorities:
        return "attention"
    return max(current_priorities, key=lambda priority: PRIORITY_RANK[priority])


def apply_content_moderation_findings(
    db: Session,
    *,
    review_case: AdminReviewCase,
    findings: list[ContentModerationFinding],
    scanned_field_hashes: dict[str, str],
    now: datetime,
) -> None:
    validate_content_moderation_case_for_findings(review_case)
    existing_findings = list(
        db.scalars(
            select(AdminContentModerationFinding)
            .where(AdminContentModerationFinding.review_case_id == review_case.id)
            .order_by(
                AdminContentModerationFinding.created_at.asc(),
                AdminContentModerationFinding.id.asc(),
            )
            .with_for_update()
        ).all()
    )
    current_by_identity = {
        finding_identity(finding): finding
        for finding in existing_findings
        if finding.current_match
    }
    incoming_by_identity = {finding_identity(finding): finding for finding in findings}
    changed_case = False

    for identity, finding in incoming_by_identity.items():
        existing = current_by_identity.get(identity)
        if existing is not None:
            existing.risk_area = finding.risk_area
            existing.priority = finding.priority
            existing.source_content_hash = finding.source_content_hash
            existing.evidence = finding.evidence
            existing.last_detected_at = now
            existing.scanner_version = finding.scanner_version
            existing.metadata_ = build_finding_metadata(finding)
            existing.updated_at = now
            db.add(existing)
            continue

        created = AdminContentModerationFinding(
            id=uuid.uuid4(),
            review_case_id=review_case.id,
            risk_area=finding.risk_area,
            finding_type=finding.finding_type,
            priority=finding.priority,
            source_field=finding.source_field,
            source_content_hash=finding.source_content_hash,
            evidence_fingerprint=finding.evidence_fingerprint,
            evidence=finding.evidence,
            current_match=True,
            first_detected_at=now,
            last_detected_at=now,
            cleared_at=None,
            scanner_version=finding.scanner_version,
            metadata_=build_finding_metadata(finding),
            created_at=now,
            updated_at=now,
        )
        db.add(created)
        db.flush()
        existing_findings.append(created)
        create_case_event(
            db,
            review_case_id=review_case.id,
            event_type="finding_attached",
            content_moderation_finding_id=created.id,
            event_metadata={
                "finding_type": created.finding_type,
                "risk_area": created.risk_area,
                "source_field": created.source_field,
            },
            created_at=now,
        )
        changed_case = True

    scanned_fields = set(scanned_field_hashes)
    for existing in existing_findings:
        if not existing.current_match:
            continue
        if existing.source_field not in scanned_fields:
            continue
        if finding_identity(existing) in incoming_by_identity:
            continue
        existing.current_match = False
        existing.cleared_at = now
        existing.updated_at = now
        db.add(existing)
        create_case_event(
            db,
            review_case_id=review_case.id,
            event_type="finding_cleared",
            content_moderation_finding_id=existing.id,
            event_metadata={
                "finding_type": existing.finding_type,
                "risk_area": existing.risk_area,
                "source_field": existing.source_field,
            },
            created_at=now,
        )
        changed_case = True

    recalculated_priority = priority_for_current_findings(existing_findings)
    if review_case.priority != recalculated_priority:
        review_case.priority = recalculated_priority
        changed_case = True
    if changed_case:
        review_case.updated_at = now
        db.add(review_case)


def reconcile_content_moderation_findings(
    db: Session,
    *,
    target_data: dict[str, uuid.UUID | None],
    findings: list[ContentModerationFinding],
    scanned_field_values: dict[str, str | None],
    _retrying_after_conflict: bool = False,
) -> AdminReviewCase | None:
    primary = primary_target(target_data)
    if primary is None:
        return None
    normalized_targets = copy_targets(target_data)
    validate_target_references(db, normalized_targets)

    scanned_field_hashes = {
        field_name: content_hash(value)
        for field_name, value in scanned_field_values.items()
    }
    now = datetime.now(timezone.utc)
    initial_priority = (
        priority_for_content_moderation_candidates(findings)
        if findings
        else "attention"
    )

    try:
        review_case = find_open_case_for_signal(
            db,
            target_data=normalized_targets,
            case_category=CONTENT_MODERATION_CASE_CATEGORY,
        )
        if review_case is None and not findings:
            return None
        if review_case is None:
            review_case, _created_case = get_or_create_open_content_moderation_case(
                db,
                target_data=normalized_targets,
                priority=initial_priority,
                now=now,
            )
        if review_case is None:
            return None

        apply_content_moderation_findings(
            db,
            review_case=review_case,
            findings=findings,
            scanned_field_hashes=scanned_field_hashes,
            now=now,
        )
        db.commit()
        db.refresh(review_case)
        return review_case
    except IntegrityError:
        db.rollback()
        if not _retrying_after_conflict:
            return reconcile_content_moderation_findings(
                db,
                target_data=target_data,
                findings=findings,
                scanned_field_values=scanned_field_values,
                _retrying_after_conflict=True,
            )
        raise


def priority_for_content_moderation_candidates(
    findings: list[ContentModerationFinding],
) -> str:
    return max(findings, key=lambda finding: PRIORITY_RANK[finding.priority]).priority


def run_content_moderation_finding_reconciliation_safely(
    db: Session,
    *,
    target_data: dict[str, uuid.UUID | None],
    findings: list[ContentModerationFinding],
    scanned_field_values: dict[str, str | None],
) -> None:
    try:
        reconcile_content_moderation_findings(
            db,
            target_data=target_data,
            findings=findings,
            scanned_field_values=scanned_field_values,
        )
    except Exception:
        db.rollback()
        logger.exception(
            "Content moderation finding reconciliation failed for target %s.",
            target_data,
        )
