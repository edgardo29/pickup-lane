"""Persist and reconcile content moderation findings for review cases."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import (
    AdminContentModerationFinding,
    AdminReviewCase,
)
from backend.services.admin_review_service import (
    CASE_ACTIVE_STATUSES,
    CONTENT_MODERATION_CASE_CATEGORY,
    PRIORITY_RANK,
    SOURCE_RECONCILIATION_RULE_ID,
    SOURCE_RECONCILIATION_RULE_VERSION,
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
    ContentModerationScanResult,
    validate_content_moderation_scan_result,
)
from backend.services.content_moderation_scanner_service import ScanProvenance
from backend.services.moderation_evidence_service import durable_identity_hash

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
        allow_reference_inserts=True,
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
        case_version=1,
        creation_reason="content_moderation_finding",
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
        automation_rule_id=SOURCE_RECONCILIATION_RULE_ID,
        automation_rule_version=SOURCE_RECONCILIATION_RULE_VERSION,
        event_metadata={"source": "content_moderation_scanner"},
        created_at=now,
    )
    return review_case, True


def finding_identity_hash(
    finding: ContentModerationFinding,
    *,
    provenance: ScanProvenance,
    target_data: dict[str, uuid.UUID | None],
) -> str:
    target_scope = {
        key: str(value)
        for key, value in sorted(target_data.items())
        if value is not None
    }
    return durable_identity_hash(
        {
            "canonicalization_version": provenance.canonicalization_version,
            "configuration_hash": provenance.configuration_hash,
            "evidence_fingerprint": finding.evidence_fingerprint,
            "evidence_format_version": provenance.evidence_format_version,
            "finding_type": finding.finding_type,
            "matched_rule_versions": list(finding.matched_rule_versions),
            "scanner_id": provenance.scanner_id,
            "scanner_version": provenance.scanner_version,
            "source_content_hash": finding.source_content_hash,
            "source_field": finding.source_field,
            "target_context": provenance.target_context,
            "target_scope": target_scope,
            "taxonomy_version": provenance.taxonomy_version,
        }
    )


def build_finding_metadata(
    finding: ContentModerationFinding,
    provenance: ScanProvenance,
) -> dict:
    return {
        "matched_rule_ids": list(finding.matched_rule_ids),
        "scanner_version": provenance.scanner_version,
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
    scan_result: ContentModerationScanResult,
    target_data: dict[str, uuid.UUID | None],
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
            .execution_options(populate_existing=True)
            .with_for_update()
        ).all()
    )
    current_by_identity = {
        finding.finding_identity_hash: finding
        for finding in existing_findings
        if finding.current_match
    }
    incoming_by_identity = {
        finding_identity_hash(
            finding,
            provenance=scan_result.provenance,
            target_data=target_data,
        ): finding
        for finding in scan_result.findings
    }
    changed_case = False

    ordered_incoming = sorted(
        incoming_by_identity.items(),
        key=lambda item: PRIORITY_RANK[item[1].priority],
        reverse=True,
    )
    for identity, finding in ordered_incoming:
        existing = current_by_identity.get(identity)
        if existing is not None:
            existing.last_detected_at = now
            existing.updated_at = now
            db.add(existing)
            continue

        priority_before = review_case.priority
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
            scanner_id=scan_result.provenance.scanner_id,
            scanner_version=scan_result.provenance.scanner_version,
            taxonomy_version=scan_result.provenance.taxonomy_version,
            configuration_hash=scan_result.provenance.configuration_hash,
            canonicalization_version=scan_result.provenance.canonicalization_version,
            evidence_format_version=scan_result.provenance.evidence_format_version,
            target_context=scan_result.provenance.target_context,
            field_purpose=finding.field_purpose,
            matched_rule_versions=list(finding.matched_rule_versions),
            declared_limits=list(scan_result.provenance.declared_limits),
            scanned_at=scan_result.provenance.scanned_at,
            execution_duration_us=scan_result.provenance.execution_duration_us,
            finding_identity_hash=identity,
            current_match=True,
            first_detected_at=now,
            last_detected_at=now,
            cleared_at=None,
            metadata_=build_finding_metadata(finding, scan_result.provenance),
            created_at=now,
            updated_at=now,
        )
        db.add(created)
        db.flush()
        existing_findings.append(created)
        recalculated_priority = priority_for_current_findings(existing_findings)
        review_case.priority = recalculated_priority
        create_case_event(
            db,
            review_case_id=review_case.id,
            event_type="finding_attached",
            content_moderation_finding_id=created.id,
            automation_rule_id=SOURCE_RECONCILIATION_RULE_ID,
            automation_rule_version=SOURCE_RECONCILIATION_RULE_VERSION,
            event_metadata={
                "finding_type": created.finding_type,
                "risk_area": created.risk_area,
                "source_field": created.source_field,
                "priority_before": priority_before,
                "priority_after": recalculated_priority,
            },
            created_at=now,
        )
        changed_case = True

    scanned_fields = {field.field_name for field in scan_result.scanned_fields}
    for existing in existing_findings:
        if not existing.current_match:
            continue
        if existing.source_field not in scanned_fields:
            continue
        if existing.finding_identity_hash in incoming_by_identity:
            continue
        priority_before = review_case.priority
        existing.current_match = False
        existing.cleared_at = now
        existing.updated_at = now
        db.add(existing)
        recalculated_priority = priority_for_current_findings(existing_findings)
        review_case.priority = recalculated_priority
        db.flush()
        create_case_event(
            db,
            review_case_id=review_case.id,
            event_type="finding_cleared",
            content_moderation_finding_id=existing.id,
            automation_rule_id=SOURCE_RECONCILIATION_RULE_ID,
            automation_rule_version=SOURCE_RECONCILIATION_RULE_VERSION,
            event_metadata={
                "finding_type": existing.finding_type,
                "risk_area": existing.risk_area,
                "source_field": existing.source_field,
                "priority_before": priority_before,
                "priority_after": recalculated_priority,
            },
            created_at=now,
        )
        changed_case = True

    if changed_case:
        db.add(review_case)


def reconcile_content_moderation_findings(
    db: Session,
    *,
    target_data: dict[str, uuid.UUID | None],
    scan_result: ContentModerationScanResult,
) -> AdminReviewCase | None:
    primary = primary_target(target_data)
    if primary is None:
        return None
    normalized_targets = copy_targets(target_data)
    validate_target_references(db, normalized_targets)
    validate_content_moderation_scan_result(scan_result)

    now = scan_result.provenance.scanned_at
    initial_priority = (
        priority_for_content_moderation_candidates(list(scan_result.findings))
        if scan_result.findings
        else "attention"
    )

    review_case = find_open_case_for_signal(
        db,
        target_data=normalized_targets,
        case_category=CONTENT_MODERATION_CASE_CATEGORY,
        allow_reference_inserts=True,
    )
    if review_case is None and not scan_result.findings:
        db.commit()
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
        scan_result=scan_result,
        target_data=normalized_targets,
        now=now,
    )
    review_case_id = review_case.id
    db.commit()
    persisted_review_case = db.get(
        AdminReviewCase,
        review_case_id,
        populate_existing=True,
    )
    if persisted_review_case is None:
        raise RuntimeError("Moderation review case disappeared after commit.")
    return persisted_review_case


def priority_for_content_moderation_candidates(
    findings: list[ContentModerationFinding],
) -> str:
    return max(findings, key=lambda finding: PRIORITY_RANK[finding.priority]).priority


def run_content_moderation_finding_reconciliation_safely(
    db: Session,
    *,
    target_data: dict[str, uuid.UUID | None],
    scan_result: ContentModerationScanResult,
) -> None:
    try:
        reconcile_content_moderation_findings(
            db,
            target_data=target_data,
            scan_result=scan_result,
        )
    except Exception as exc:  # noqa: BLE001 - fail-safe moderation boundary
        db.rollback()
        logger.error(
            "Content moderation finding reconciliation failed for target %s "
            "(error_type=%s).",
            target_data,
            type(exc).__name__,
        )
