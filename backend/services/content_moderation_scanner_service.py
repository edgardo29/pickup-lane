"""Deterministic saved-content moderation scanner primitives."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from time import monotonic_ns

from backend.services.moderation_evidence_service import exact_source_hash
from backend.services.moderation_taxonomy import (
    EXECUTION_KIND_REGEX,
    FIELD_PURPOSE_GENERAL,
    FINDING_TYPE_HARASSMENT_OR_ABUSE,
    FINDING_TYPE_OFF_APP_CONTACT,
    FINDING_TYPE_SEXUAL_OR_EXPLICIT,
    FINDING_TYPE_SLUR_OR_HATE,
    FINDING_TYPE_SPAM_OR_SCAM,
    FINDING_TYPE_THREAT_OR_VIOLENCE,
    RISK_AREA_UNSAFE_PAYMENT,
    RISK_AREA_UNSAFE_POST,
    RULES_BY_ID,
    SAVED_CONTENT_PROFILE,
    TARGET_CONTEXT_COMMUNITY_GAME,
    ModerationTaxonomyError,
    ScannerProfileDefinition,
    profile_configuration_hash,
    rules_for_context,
    validate_registry,
)

EXCERPT_MAX_LENGTH = 220
SIGNAL_CATEGORY_UNSAFE_PAYMENT = RISK_AREA_UNSAFE_PAYMENT
SIGNAL_CATEGORY_UNSAFE_POST = RISK_AREA_UNSAFE_POST
MODERATION_DOMAIN_CHAT = "chat_risk"

STANDALONE_FINDING_TYPES = {
    FINDING_TYPE_OFF_APP_CONTACT,
    FINDING_TYPE_SPAM_OR_SCAM,
    FINDING_TYPE_THREAT_OR_VIOLENCE,
    FINDING_TYPE_HARASSMENT_OR_ABUSE,
    FINDING_TYPE_SLUR_OR_HATE,
    FINDING_TYPE_SEXUAL_OR_EXPLICIT,
}


@dataclass(frozen=True)
class ModerationTextField:
    field_name: str
    field_label: str
    value: str | None
    purpose: str = FIELD_PURPOSE_GENERAL


@dataclass(frozen=True)
class ContentModerationRuleMatch:
    rule_id: str
    rule_version: str
    risk_area: str
    finding_type: str
    evidence_type: str
    priority: str
    source_field: str
    source_field_purpose: str
    start: int
    end: int
    matched_text: str
    original_text: str


@dataclass(frozen=True)
class ScanProvenance:
    scanner_id: str
    scanner_version: str
    taxonomy_version: str
    configuration_hash: str
    canonicalization_version: str
    evidence_format_version: str
    target_context: str
    declared_limits: tuple[str, ...]
    scanned_at: datetime
    execution_duration_us: int


@dataclass(frozen=True)
class ModerationFinding:
    signal_category: str
    moderation_domain: str
    detected_categories: tuple[str, ...]
    severity: str
    priority: str
    field_name: str
    field_label: str
    excerpt: str
    content_hash: str
    matched_rule_ids: tuple[str, ...]
    matched_rule_versions: tuple[dict[str, str], ...]
    provenance: ScanProvenance

    @property
    def scanner_version(self) -> str:
        return self.provenance.scanner_version


def normalize_scan_text(value: str | None) -> str:
    return " ".join(str(value or "").strip().split())


def content_hash(value: str | None) -> str:
    """Return the exact UTF-8 source hash retained by compatibility callers."""

    return exact_source_hash(value)


def is_utc_datetime(value: datetime) -> bool:
    return (
        value.tzinfo is not None
        and value.utcoffset() is not None
        and value.utcoffset() == timedelta(0)
    )


def build_review_excerpt(
    value: str,
    *,
    match=None,
    limit: int = EXCERPT_MAX_LENGTH,
) -> str:
    normalized = normalize_scan_text(value)
    if len(normalized) <= limit:
        return normalized
    if match is not None:
        start = max(match.start() - 60, 0)
        end = min(match.end() + 60, len(value))
        normalized = normalize_scan_text(value[start:end])
        if len(normalized) <= limit:
            return normalized
    return normalized[: max(0, limit - 3)].rstrip() + "..."


def trimmed_match_span(
    match,
    *,
    trim_chars: str = ".,;:!?)]}",
) -> tuple[int, int, str]:
    start = match.start()
    end = match.end()
    text = match.group(0)
    trimmed = text.rstrip(trim_chars)
    end -= len(text) - len(trimmed)
    return start, end, trimmed


def scan_text_field_matches(
    field: ModerationTextField,
    *,
    target_context: str = TARGET_CONTEXT_COMMUNITY_GAME,
) -> list[ContentModerationRuleMatch]:
    original_text = str(field.value or "")
    if not normalize_scan_text(original_text):
        return []

    matches: list[ContentModerationRuleMatch] = []
    for rule in rules_for_context(target_context):
        if (
            rule.execution_kind != EXECUTION_KIND_REGEX
            or field.purpose not in rule.allowed_field_purposes
        ):
            continue
        for regex_match in rule.compile_expression().finditer(original_text):
            start, end, matched_text = trimmed_match_span(regex_match)
            if not matched_text:
                continue
            matches.append(
                ContentModerationRuleMatch(
                    rule_id=rule.rule_id,
                    rule_version=rule.rule_version,
                    risk_area=str(rule.risk_area),
                    finding_type=rule.outcome,
                    evidence_type=rule.evidence_type,
                    priority=rule.priority_or_severity,
                    source_field=field.field_name,
                    source_field_purpose=field.purpose,
                    start=start,
                    end=end,
                    matched_text=matched_text,
                    original_text=original_text,
                )
            )
    return sorted(matches, key=lambda item: (item.start, item.end, item.rule_id))


def scan_text_fields_for_matches(
    fields: list[ModerationTextField],
    *,
    target_context: str = TARGET_CONTEXT_COMMUNITY_GAME,
) -> list[ContentModerationRuleMatch]:
    matches: list[ContentModerationRuleMatch] = []
    for field in fields:
        matches.extend(scan_text_field_matches(field, target_context=target_context))
    return matches


def validate_field_inventory(
    fields: list[ModerationTextField],
    *,
    target_context: str,
    profile: ScannerProfileDefinition = SAVED_CONTENT_PROFILE,
) -> None:
    expected = profile.context_field_inventory.get(target_context)
    actual = tuple((field.field_name, field.purpose) for field in fields)
    if expected is None or actual != expected:
        raise ModerationTaxonomyError(
            f"Moderation field inventory for {target_context!r} is not authoritative."
        )


def build_scan_provenance(
    *,
    profile: ScannerProfileDefinition,
    target_context: str,
    started_ns: int,
    wall_clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    monotonic_clock: Callable[[], int] = monotonic_ns,
) -> ScanProvenance:
    scanned_at = wall_clock()
    if scanned_at.tzinfo is None or scanned_at.utcoffset() is None:
        raise ValueError("Moderation scan wall clock must be timezone-aware.")
    scanned_at = scanned_at.astimezone(timezone.utc)
    duration_us = max(0, (monotonic_clock() - started_ns) // 1_000)
    return ScanProvenance(
        scanner_id=profile.scanner_id,
        scanner_version=profile.scanner_version,
        taxonomy_version=profile.taxonomy_version,
        configuration_hash=profile_configuration_hash(profile),
        canonicalization_version=profile.canonicalization_version,
        evidence_format_version=profile.evidence_format_version,
        target_context=target_context,
        declared_limits=profile.declared_limits,
        scanned_at=scanned_at,
        execution_duration_us=duration_us,
    )


def scanner_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


# Compatibility exports remain registry-owned rather than independently defined.
CONTENT_MODERATION_RULES = tuple(
    RULES_BY_ID[rule_id] for rule_id in SAVED_CONTENT_PROFILE.enabled_rule_ids
)
validate_registry()
