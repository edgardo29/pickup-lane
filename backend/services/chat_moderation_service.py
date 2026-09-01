"""Shared versioned chat moderation detection and evidence helpers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from time import monotonic_ns

from backend.services.content_moderation_scanner_service import (
    ScanProvenance,
    build_scan_provenance,
    is_utc_datetime,
)
from backend.services.moderation_evidence_service import (
    context_predicate_fingerprint,
    durable_identity_hash,
    exact_source_hash,
    safe_chat_message_preview,
    safe_chat_span_preview,
    span_evidence_fingerprint,
    validate_chat_evidence,
)
from backend.services.moderation_taxonomy import (
    CHAT_DETECTION_OUTCOMES,
    CHAT_PROFILE,
    EVIDENCE_KIND_CONTEXT_PREDICATE,
    EVIDENCE_KIND_SPAN,
    EXECUTION_KIND_CONTEXT_PREDICATE,
    EXECUTION_KIND_REGEX,
    FIELD_PURPOSE_CHAT,
    REPEATED_MESSAGE_PREDICATE_KEY,
    REPEATED_MESSAGE_PREDICATE_VERSION,
    TARGET_CONTEXT_GAME_CHAT,
    profile_configuration_hash,
    profile_for_context,
    rules_for_context,
    validate_registry,
)

CHAT_DETECTION_CATEGORIES = set(CHAT_DETECTION_OUTCOMES)
CHAT_MESSAGE_CONFLICT_DETAIL = "Unable to send the chat message due to a conflict."


@dataclass(frozen=True)
class ContextPredicateFact:
    predicate_key: str
    predicate_version: str
    outcome: bool
    reference_message_id: str
    reference_source_hash: str


@dataclass(frozen=True)
class ChatDetection:
    category: str
    severity: str
    rule_key: str
    registry_rule_id: str
    rule_version: str
    matched_preview: str
    source_field: str
    field_purpose: str
    source_content_hash: str
    evidence_fingerprint: str
    evidence: dict


@dataclass(frozen=True)
class ChatModerationScanResult:
    detections: tuple[ChatDetection, ...]
    provenance: ScanProvenance


def chat_detection_record_values(
    *,
    message_id: str,
    source_text: str,
    detection: ChatDetection,
    provenance: ScanProvenance,
) -> dict[str, object]:
    profile = profile_for_context(provenance.target_context)
    if (
        profile.profile_id != CHAT_PROFILE.profile_id
        or provenance.scanner_id != profile.scanner_id
        or provenance.scanner_version != profile.scanner_version
        or provenance.taxonomy_version != profile.taxonomy_version
        or provenance.configuration_hash != profile_configuration_hash(profile)
        or provenance.canonicalization_version != profile.canonicalization_version
        or provenance.evidence_format_version != profile.evidence_format_version
        or provenance.declared_limits != profile.declared_limits
        or provenance.execution_duration_us < 0
        or not is_utc_datetime(provenance.scanned_at)
    ):
        raise ValueError("Chat detection provenance is not canonical.")
    matched_rule_versions = [
        {
            "rule_id": detection.registry_rule_id,
            "rule_version": detection.rule_version,
        }
    ]
    validate_chat_evidence(
        source_text=source_text,
        category=detection.category,
        severity=detection.severity,
        target_context=provenance.target_context,
        source_field=detection.source_field,
        field_purpose=detection.field_purpose,
        source_content_hash=detection.source_content_hash,
        evidence_fingerprint=detection.evidence_fingerprint,
        evidence=detection.evidence,
        public_rule_key=detection.rule_key,
        registry_rule_id=detection.registry_rule_id,
        rule_version=detection.rule_version,
        matched_rule_versions=matched_rule_versions,
        matched_preview=detection.matched_preview,
        canonicalization_version=provenance.canonicalization_version,
    )
    identity_hash = durable_identity_hash(
        {
            "canonicalization_version": provenance.canonicalization_version,
            "category": detection.category,
            "configuration_hash": provenance.configuration_hash,
            "evidence_fingerprint": detection.evidence_fingerprint,
            "evidence_format_version": provenance.evidence_format_version,
            "matched_rule_versions": matched_rule_versions,
            "scanner_id": provenance.scanner_id,
            "scanner_version": provenance.scanner_version,
            "source_content_hash": detection.source_content_hash,
            "source_field": detection.source_field,
            "target_context": provenance.target_context,
            "target_scope": {"message_id": message_id},
            "taxonomy_version": provenance.taxonomy_version,
        }
    )
    return {
        "category": detection.category,
        "severity": detection.severity,
        "rule_key": detection.rule_key,
        "matched_preview": detection.matched_preview,
        "scanner_id": provenance.scanner_id,
        "scanner_version": provenance.scanner_version,
        "taxonomy_version": provenance.taxonomy_version,
        "configuration_hash": provenance.configuration_hash,
        "canonicalization_version": provenance.canonicalization_version,
        "evidence_format_version": provenance.evidence_format_version,
        "target_context": provenance.target_context,
        "field_purpose": detection.field_purpose,
        "source_field": detection.source_field,
        "source_content_hash": detection.source_content_hash,
        "matched_rule_versions": matched_rule_versions,
        "declared_limits": list(provenance.declared_limits),
        "evidence_fingerprint": detection.evidence_fingerprint,
        "evidence": detection.evidence,
        "scanned_at": provenance.scanned_at,
        "execution_duration_us": provenance.execution_duration_us,
        "detection_identity_hash": identity_hash,
    }


def build_safe_message_preview(message_body: str, *, limit: int = 160) -> str:
    return safe_chat_message_preview(message_body, limit=limit)


def build_matched_preview(message_body: str, start: int, end: int) -> str:
    return safe_chat_span_preview(
        message_body,
        start=start,
        end=end,
        limit=CHAT_PROFILE.evidence_limits["preview"],
    )


def _trimmed_span(match, *, trim_chars: str = ".,;:!?)]}") -> tuple[int, int]:
    matched = match.group(0)
    trimmed = matched.rstrip(trim_chars)
    return match.start(), match.end() - (len(matched) - len(trimmed))


def _span_detection(
    message_body: str, rule, match, *, target_context: str
) -> ChatDetection:
    start, end = _trimmed_span(match)
    matched_text = message_body[start:end]
    source_hash = exact_source_hash(message_body)
    evidence = {
        "evidence_kind": EVIDENCE_KIND_SPAN,
        "evidence_type": rule.evidence_type,
        "start": start,
        "end": end,
        "matched_source_hash": exact_source_hash(matched_text),
    }
    fingerprint = span_evidence_fingerprint(
        outcome=rule.outcome,
        source_field="message_body",
        atomic_values=[(rule.evidence_type, matched_text)],
        canonicalization_version=CHAT_PROFILE.canonicalization_version,
    )
    detection = ChatDetection(
        category=rule.outcome,
        severity=rule.priority_or_severity,
        rule_key=rule.persisted_rule_key,
        registry_rule_id=rule.rule_id,
        rule_version=rule.rule_version,
        matched_preview=build_matched_preview(message_body, start, end),
        source_field="message_body",
        field_purpose=FIELD_PURPOSE_CHAT,
        source_content_hash=source_hash,
        evidence_fingerprint=fingerprint,
        evidence=evidence,
    )
    validate_chat_evidence(
        source_text=message_body,
        category=detection.category,
        severity=detection.severity,
        target_context=target_context,
        source_field=detection.source_field,
        field_purpose=detection.field_purpose,
        source_content_hash=detection.source_content_hash,
        evidence_fingerprint=detection.evidence_fingerprint,
        evidence=detection.evidence,
        public_rule_key=detection.rule_key,
        registry_rule_id=detection.registry_rule_id,
        rule_version=detection.rule_version,
        matched_rule_versions=(
            {
                "rule_id": detection.registry_rule_id,
                "rule_version": detection.rule_version,
            },
        ),
        matched_preview=detection.matched_preview,
        canonicalization_version=CHAT_PROFILE.canonicalization_version,
    )
    return detection


def _predicate_detection(
    message_body: str,
    rule,
    fact: ContextPredicateFact,
    *,
    target_context: str,
) -> ChatDetection:
    source_hash = exact_source_hash(message_body)
    evidence = {
        "evidence_kind": EVIDENCE_KIND_CONTEXT_PREDICATE,
        "outcome": True,
        "predicate_key": fact.predicate_key,
        "predicate_version": fact.predicate_version,
        "reference_message_id": fact.reference_message_id,
        "reference_source_hash": fact.reference_source_hash,
    }
    fingerprint = context_predicate_fingerprint(
        category=rule.outcome,
        source_field="message_body",
        source_content_hash=source_hash,
        predicate_key=fact.predicate_key,
        predicate_version=fact.predicate_version,
        reference_message_id=fact.reference_message_id,
        reference_source_hash=fact.reference_source_hash,
    )
    detection = ChatDetection(
        category=rule.outcome,
        severity=rule.priority_or_severity,
        rule_key=rule.persisted_rule_key,
        registry_rule_id=rule.rule_id,
        rule_version=rule.rule_version,
        matched_preview=build_safe_message_preview(
            message_body,
            limit=CHAT_PROFILE.evidence_limits["preview"],
        ),
        source_field="message_body",
        field_purpose=FIELD_PURPOSE_CHAT,
        source_content_hash=source_hash,
        evidence_fingerprint=fingerprint,
        evidence=evidence,
    )
    validate_chat_evidence(
        source_text=message_body,
        category=detection.category,
        severity=detection.severity,
        target_context=target_context,
        source_field=detection.source_field,
        field_purpose=detection.field_purpose,
        source_content_hash=detection.source_content_hash,
        evidence_fingerprint=detection.evidence_fingerprint,
        evidence=detection.evidence,
        public_rule_key=detection.rule_key,
        registry_rule_id=detection.registry_rule_id,
        rule_version=detection.rule_version,
        matched_rule_versions=(
            {
                "rule_id": detection.registry_rule_id,
                "rule_version": detection.rule_version,
            },
        ),
        matched_preview=detection.matched_preview,
        canonicalization_version=CHAT_PROFILE.canonicalization_version,
    )
    return detection


def detect_chat_message(
    message_body: str,
    *,
    target_context: str = TARGET_CONTEXT_GAME_CHAT,
    predicate_facts: tuple[ContextPredicateFact, ...] = (),
    started_ns: int | None = None,
    wall_clock: Callable[[], datetime] | None = None,
    monotonic_clock: Callable[[], int] = monotonic_ns,
) -> ChatModerationScanResult:
    """Evaluate one message and return detections plus immutable provenance."""

    validate_registry()
    profile = profile_for_context(target_context)
    if profile.profile_id != CHAT_PROFILE.profile_id:
        raise ValueError("Chat moderation requires the chat scanner profile.")
    effective_started_ns = monotonic_clock() if started_ns is None else started_ns
    facts_by_key = {
        (fact.predicate_key, fact.predicate_version): fact
        for fact in predicate_facts
        if fact.outcome
    }
    detections: list[ChatDetection] = []
    for rule in rules_for_context(target_context):
        if rule.execution_kind == EXECUTION_KIND_REGEX:
            match = rule.compile_expression().search(message_body)
            if match is not None:
                detections.append(
                    _span_detection(
                        message_body,
                        rule,
                        match,
                        target_context=target_context,
                    )
                )
            continue
        if rule.execution_kind == EXECUTION_KIND_CONTEXT_PREDICATE:
            fact = facts_by_key.get(
                (str(rule.predicate_key), str(rule.predicate_version))
            )
            if fact is not None:
                detections.append(
                    _predicate_detection(
                        message_body,
                        rule,
                        fact,
                        target_context=target_context,
                    )
                )

    provenance_kwargs = {}
    if wall_clock is not None:
        provenance_kwargs["wall_clock"] = wall_clock
    provenance = build_scan_provenance(
        profile=profile,
        target_context=target_context,
        started_ns=effective_started_ns,
        monotonic_clock=monotonic_clock,
        **provenance_kwargs,
    )
    return ChatModerationScanResult(
        detections=tuple(detections),
        provenance=provenance,
    )


def repeated_message_fact(
    *,
    reference_message_id: str,
    reference_message_body: str,
) -> ContextPredicateFact:
    if not reference_message_id.strip():
        raise ValueError("Repeated-message evidence requires a reference message ID.")
    return ContextPredicateFact(
        predicate_key=REPEATED_MESSAGE_PREDICATE_KEY,
        predicate_version=REPEATED_MESSAGE_PREDICATE_VERSION,
        outcome=True,
        reference_message_id=reference_message_id,
        reference_source_hash=exact_source_hash(reference_message_body),
    )
