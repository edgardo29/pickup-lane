"""Build admin-facing content moderation evidence from scanner matches."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from time import monotonic_ns

from backend.services.content_moderation_scanner_service import (
    ContentModerationRuleMatch,
    ModerationTextField,
    ScanProvenance,
    build_scan_provenance,
    content_hash,
    is_utc_datetime,
    normalize_scan_text,
    scan_text_field_matches,
    validate_field_inventory,
)
from backend.services.moderation_evidence_service import (
    ModerationEvidenceError,
    bounded_saved_evidence_display,
    span_evidence_fingerprint,
    validate_saved_span_evidence,
)
from backend.services.moderation_taxonomy import (
    EVIDENCE_TYPE_CONTACT_PHRASE,
    EVIDENCE_TYPE_EMAIL,
    EVIDENCE_TYPE_PAYMENT_HANDLE,
    EVIDENCE_TYPE_PAYMENT_METHOD,
    EVIDENCE_TYPE_PAYMENT_PRESSURE_PHRASE,
    EVIDENCE_TYPE_PHONE,
    EVIDENCE_TYPE_PHRASE,
    EVIDENCE_TYPE_SOCIAL_HANDLE,
    EVIDENCE_TYPE_URL,
    FIELD_PURPOSE_ADDRESS,
    FIELD_PURPOSE_PAYMENT,
    FIELD_PURPOSE_PAYMENT_METHOD,
    FINDING_TYPE_OFF_APP_CONTACT,
    FINDING_TYPE_PAYMENT_PRESSURE,
    SAVED_CONTENT_PROFILE,
    TARGET_CONTEXT_COMMUNITY_GAME,
    profile_configuration_hash,
    profile_for_context,
)

ENTITY_EVIDENCE_TYPES = {
    EVIDENCE_TYPE_EMAIL,
    EVIDENCE_TYPE_PAYMENT_HANDLE,
    EVIDENCE_TYPE_PHONE,
    EVIDENCE_TYPE_SOCIAL_HANDLE,
    EVIDENCE_TYPE_URL,
}
OFF_APP_ENTITY_EVIDENCE_TYPES = {
    EVIDENCE_TYPE_EMAIL,
    EVIDENCE_TYPE_PHONE,
    EVIDENCE_TYPE_SOCIAL_HANDLE,
    EVIDENCE_TYPE_URL,
}
PAYMENT_SUPPORT_EVIDENCE_TYPES = {
    EVIDENCE_TYPE_PAYMENT_HANDLE,
    EVIDENCE_TYPE_PAYMENT_METHOD,
}
CLAUSE_BOUNDARIES = ".!?;\n,"
PRIORITY_RANK = {"attention": 0, "urgent": 1, "critical": 2}


@dataclass(frozen=True)
class ContentModerationFinding:
    risk_area: str
    finding_type: str
    priority: str
    source_field: str
    field_purpose: str
    source_content_hash: str
    evidence_fingerprint: str
    evidence: list[dict]
    matched_rule_ids: tuple[str, ...]
    matched_rule_versions: tuple[dict[str, str], ...]


@dataclass(frozen=True)
class ContentModerationScanResult:
    scanned_fields: tuple[ModerationTextField, ...]
    findings: tuple[ContentModerationFinding, ...]
    provenance: ScanProvenance


def validate_content_moderation_scan_result(
    scan_result: ContentModerationScanResult,
) -> None:
    profile = profile_for_context(scan_result.provenance.target_context)
    if profile.profile_id != SAVED_CONTENT_PROFILE.profile_id:
        raise ModerationEvidenceError(
            "Saved-content scan uses the wrong scanner profile."
        )
    validate_field_inventory(
        list(scan_result.scanned_fields),
        target_context=scan_result.provenance.target_context,
        profile=profile,
    )
    provenance = scan_result.provenance
    if (
        provenance.scanner_id != profile.scanner_id
        or provenance.scanner_version != profile.scanner_version
        or provenance.taxonomy_version != profile.taxonomy_version
        or provenance.configuration_hash != profile_configuration_hash(profile)
        or provenance.canonicalization_version != profile.canonicalization_version
        or provenance.evidence_format_version != profile.evidence_format_version
        or provenance.declared_limits != profile.declared_limits
        or provenance.execution_duration_us < 0
        or not is_utc_datetime(provenance.scanned_at)
    ):
        raise ModerationEvidenceError("Saved-content scan provenance is not canonical.")
    fields_by_name = {
        field.field_name: str(field.value or "") for field in scan_result.scanned_fields
    }
    for finding in scan_result.findings:
        source_text = fields_by_name.get(finding.source_field)
        if source_text is None:
            raise ModerationEvidenceError(
                "Finding source field is outside the scanned inventory."
            )
        validate_saved_span_evidence(
            source_text=source_text,
            source_content_hash=finding.source_content_hash,
            evidence_fingerprint=finding.evidence_fingerprint,
            finding_type=finding.finding_type,
            risk_area=finding.risk_area,
            priority=finding.priority,
            target_context=provenance.target_context,
            source_field=finding.source_field,
            field_purpose=finding.field_purpose,
            evidence=finding.evidence,
            matched_rule_ids=finding.matched_rule_ids,
            matched_rule_versions=finding.matched_rule_versions,
            canonicalization_version=provenance.canonicalization_version,
            maximum_items=SAVED_CONTENT_PROFILE.evidence_limits["items"],
        )
    expected_findings = tuple(
        canonical_findings_for_fields(
            list(scan_result.scanned_fields),
            target_context=provenance.target_context,
        )
    )
    if scan_result.findings != expected_findings:
        raise ModerationEvidenceError(
            "Saved-content findings are not the canonical result for the source."
        )


def priority_max(matches: list[ContentModerationRuleMatch]) -> str:
    return max(matches, key=lambda item: PRIORITY_RANK[item.priority]).priority


def normalize_fingerprint_value(value: str) -> str:
    return normalize_scan_text(value).casefold()


def trim_span_whitespace(text: str, start: int, end: int) -> tuple[int, int]:
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


def previous_boundary(text: str, index: int) -> int:
    position = index
    while position > 0 and text[position - 1] not in CLAUSE_BOUNDARIES:
        position -= 1
    return position


def next_boundary(text: str, index: int) -> int:
    position = index
    while position < len(text) and text[position] not in CLAUSE_BOUNDARIES:
        position += 1
    return position


def matches_overlap(
    left: ContentModerationRuleMatch, right: ContentModerationRuleMatch
) -> bool:
    return left.start < right.end and right.start < left.end


def same_clause(
    text: str,
    left: ContentModerationRuleMatch,
    right: ContentModerationRuleMatch,
) -> bool:
    return previous_boundary(text, left.start) == previous_boundary(text, right.start)


def build_evidence_match(match: ContentModerationRuleMatch) -> dict:
    return {
        "rule_id": match.rule_id,
        "rule_version": match.rule_version,
        "evidence_type": match.evidence_type,
        "matched_text": match.matched_text,
        "start": match.start,
        "end": match.end,
    }


def build_evidence_item(
    *,
    text: str,
    evidence_type: str,
    start: int,
    end: int,
    matches: list[ContentModerationRuleMatch],
    limit: int,
) -> dict:
    start, end = trim_span_whitespace(text, start, end)
    required_start = max(min(match.start for match in matches), start)
    required_end = min(max(match.end for match in matches), end)
    display_text, truncated_before, truncated_after = bounded_saved_evidence_display(
        text,
        start=start,
        end=end,
        required_start=required_start,
        required_end=required_end,
        limit=limit,
    )

    return {
        "evidence_type": evidence_type,
        "display_text": display_text,
        "start": start,
        "end": end,
        "matches": [build_evidence_match(match) for match in unique_matches(matches)],
        "truncated_before": truncated_before,
        "truncated_after": truncated_after,
        "additional_match_count": 0,
    }


def unique_matches(
    matches: list[ContentModerationRuleMatch],
) -> list[ContentModerationRuleMatch]:
    unique: dict[tuple[str, str, str, int, int], ContentModerationRuleMatch] = {}
    for match in sorted(
        matches,
        key=lambda item: (
            item.start,
            item.end,
            item.rule_id,
            item.rule_version,
            item.evidence_type,
        ),
    ):
        key = (
            match.rule_id,
            match.rule_version,
            match.evidence_type,
            match.start,
            match.end,
        )
        unique.setdefault(key, match)
    return list(unique.values())


def remove_contained_link_matches(
    matches: list[ContentModerationRuleMatch],
) -> list[ContentModerationRuleMatch]:
    email_matches = [
        match for match in matches if match.evidence_type == EVIDENCE_TYPE_EMAIL
    ]
    filtered: list[ContentModerationRuleMatch] = []
    for match in matches:
        if match.evidence_type == EVIDENCE_TYPE_URL and any(
            email.start <= match.start and match.end <= email.end
            for email in email_matches
        ):
            continue
        filtered.append(match)
    return filtered


def nearby_contact_phrase(
    text: str,
    entity: ContentModerationRuleMatch,
    phrases: list[ContentModerationRuleMatch],
) -> ContentModerationRuleMatch | None:
    phrase_candidates = [
        phrase
        for phrase in phrases
        if same_clause(text, entity, phrase) and abs(entity.start - phrase.end) <= 48
    ]
    if not phrase_candidates:
        return None
    return min(phrase_candidates, key=lambda phrase: abs(entity.start - phrase.end))


def build_off_app_contact_evidence(
    text: str,
    matches: list[ContentModerationRuleMatch],
) -> list[dict]:
    phrases = [
        match
        for match in matches
        if match.evidence_type == EVIDENCE_TYPE_CONTACT_PHRASE
    ]
    entities = [
        match
        for match in matches
        if match.evidence_type in OFF_APP_ENTITY_EVIDENCE_TYPES
    ]
    evidence_items: list[dict] = []
    used_phrase_ids: set[tuple[int, int, str]] = set()

    for entity in entities:
        phrase = nearby_contact_phrase(text, entity, phrases)
        item_matches = [entity]
        if phrase is not None:
            item_matches.insert(0, phrase)
            used_phrase_ids.add((phrase.start, phrase.end, phrase.rule_id))
        if entity.evidence_type == EVIDENCE_TYPE_URL:
            start, end = entity.start, entity.end
        elif phrase is not None:
            start = min(phrase.start, entity.start)
            end = max(phrase.end, entity.end)
        else:
            start, end = entity.start, entity.end
        evidence_items.append(
            build_evidence_item(
                text=text,
                evidence_type=entity.evidence_type,
                start=start,
                end=end,
                matches=item_matches,
                limit=SAVED_CONTENT_PROFILE.evidence_limits["entity"],
            )
        )

    for phrase in phrases:
        if (phrase.start, phrase.end, phrase.rule_id) in used_phrase_ids:
            continue
        start = previous_boundary(text, phrase.start)
        end = next_boundary(text, phrase.end)
        evidence_items.append(
            build_evidence_item(
                text=text,
                evidence_type=EVIDENCE_TYPE_CONTACT_PHRASE,
                start=start,
                end=end,
                matches=[phrase],
                limit=SAVED_CONTENT_PROFILE.evidence_limits["entity"],
            )
        )

    return dedupe_evidence_items(evidence_items)


def payment_support_matches_for_context(
    text: str,
    core: ContentModerationRuleMatch,
    matches: list[ContentModerationRuleMatch],
) -> list[ContentModerationRuleMatch]:
    return [
        match
        for match in matches
        if match.evidence_type in PAYMENT_SUPPORT_EVIDENCE_TYPES
        and same_clause(text, core, match)
        and abs(match.start - core.end) <= 96
    ]


def payment_pressure_contributing_matches(
    text: str,
    matches: list[ContentModerationRuleMatch],
) -> list[ContentModerationRuleMatch]:
    core_matches = [
        match
        for match in matches
        if match.evidence_type == EVIDENCE_TYPE_PAYMENT_PRESSURE_PHRASE
    ]
    attached_support = [
        support
        for core in core_matches
        for support in payment_support_matches_for_context(text, core, matches)
    ]
    return unique_matches([*core_matches, *attached_support])


def build_payment_pressure_evidence(
    text: str,
    matches: list[ContentModerationRuleMatch],
) -> list[dict]:
    core_matches = [
        match
        for match in matches
        if match.evidence_type == EVIDENCE_TYPE_PAYMENT_PRESSURE_PHRASE
    ]
    evidence_items: list[dict] = []
    for core in core_matches:
        support = payment_support_matches_for_context(text, core, matches)
        item_matches = [core, *support]
        start = previous_boundary(text, core.start)
        end = max(match.end for match in item_matches)
        evidence_items.append(
            build_evidence_item(
                text=text,
                evidence_type=EVIDENCE_TYPE_PAYMENT_PRESSURE_PHRASE,
                start=start,
                end=end,
                matches=item_matches,
                limit=SAVED_CONTENT_PROFILE.evidence_limits["phrase"],
            )
        )
    return dedupe_evidence_items(evidence_items)


def build_phrase_evidence(
    text: str,
    matches: list[ContentModerationRuleMatch],
) -> list[dict]:
    evidence_items: list[dict] = []
    for match in matches:
        start = previous_boundary(text, match.start)
        end = next_boundary(text, match.end)
        evidence_items.append(
            build_evidence_item(
                text=text,
                evidence_type=EVIDENCE_TYPE_PHRASE,
                start=start,
                end=end,
                matches=[match],
                limit=SAVED_CONTENT_PROFILE.evidence_limits["phrase"],
            )
        )
    return dedupe_evidence_items(evidence_items)


def dedupe_evidence_items(items: list[dict]) -> list[dict]:
    maximum_items = SAVED_CONTENT_PROFILE.evidence_limits["items"]
    unique: dict[tuple, dict] = {}
    for item in sorted(
        items,
        key=lambda row: (
            row["start"],
            row["end"],
            row["evidence_type"],
            tuple(
                (
                    match["start"],
                    match["end"],
                    match["rule_id"],
                    match["rule_version"],
                )
                for match in row["matches"]
            ),
        ),
    ):
        key = (
            item["start"],
            item["end"],
            item["evidence_type"],
            tuple(
                (
                    match["start"],
                    match["end"],
                    match["rule_id"],
                    match["rule_version"],
                    match["evidence_type"],
                    match["matched_text"],
                )
                for match in item["matches"]
            ),
        )
        unique.setdefault(key, item)

    deduped = list(unique.values())
    if len(deduped) <= maximum_items:
        return deduped

    all_rule_pairs = evidence_rule_pairs(deduped)
    selected_indexes: list[int] = []
    represented: set[tuple[str, str]] = set()
    for index, item in enumerate(deduped):
        item_pairs = evidence_rule_pairs([item])
        if item_pairs - represented:
            selected_indexes.append(index)
            represented.update(item_pairs)
    if len(selected_indexes) > maximum_items:
        raise ModerationEvidenceError(
            "The evidence item cap cannot retain complete rule attribution."
        )
    for index in range(len(deduped)):
        if len(selected_indexes) == maximum_items:
            break
        if index not in selected_indexes:
            selected_indexes.append(index)
    selected_indexes.sort()
    visible = [dict(deduped[index]) for index in selected_indexes]
    if evidence_rule_pairs(visible) != all_rule_pairs:
        raise ModerationEvidenceError(
            "Bounded evidence lost contributing rule attribution."
        )
    for item in visible:
        item["additional_match_count"] = 0
    visible[-1]["additional_match_count"] = len(deduped) - len(visible)
    return visible


def fingerprint_matches(
    finding_type: str,
    source_field: str,
    evidence: list[dict],
) -> str:
    atomic_values: list[tuple[str, str]] = []
    for item in evidence:
        for match in item["matches"]:
            atomic_values.append(
                (
                    str(match["evidence_type"]),
                    normalize_fingerprint_value(str(match["matched_text"])),
                )
            )
    return span_evidence_fingerprint(
        outcome=finding_type,
        source_field=source_field,
        atomic_values=atomic_values,
    )


def matched_rule_ids(matches: list[ContentModerationRuleMatch]) -> tuple[str, ...]:
    return tuple(sorted({match.rule_id for match in matches}))


def matched_rule_versions(
    matches: list[ContentModerationRuleMatch],
) -> tuple[dict[str, str], ...]:
    return tuple(
        {"rule_id": rule_id, "rule_version": rule_version}
        for rule_id, rule_version in sorted(
            {(match.rule_id, match.rule_version) for match in matches}
        )
    )


def evidence_rule_pairs(evidence: list[dict]) -> set[tuple[str, str]]:
    return {
        (str(match["rule_id"]), str(match["rule_version"]))
        for item in evidence
        for match in item["matches"]
    }


def should_include_match(match: ContentModerationRuleMatch) -> bool:
    if (
        match.finding_type == FINDING_TYPE_OFF_APP_CONTACT
        and match.source_field_purpose
        in {FIELD_PURPOSE_ADDRESS, FIELD_PURPOSE_PAYMENT, FIELD_PURPOSE_PAYMENT_METHOD}
    ):
        return False
    return not (
        match.finding_type == FINDING_TYPE_PAYMENT_PRESSURE
        and match.source_field_purpose == FIELD_PURPOSE_PAYMENT_METHOD
    )


def _build_field_findings(
    field: ModerationTextField,
    *,
    target_context: str = TARGET_CONTEXT_COMMUNITY_GAME,
) -> list[ContentModerationFinding]:
    text = str(field.value or "")
    matches = [
        match
        for match in remove_contained_link_matches(
            scan_text_field_matches(field, target_context=target_context)
        )
        if should_include_match(match)
    ]
    if not matches:
        return []

    source_content_hash = content_hash(text)
    findings: list[ContentModerationFinding] = []
    finding_types = tuple(dict.fromkeys(match.finding_type for match in matches))
    for finding_type in finding_types:
        finding_matches = [
            match for match in matches if match.finding_type == finding_type
        ]
        if finding_type == FINDING_TYPE_OFF_APP_CONTACT:
            evidence = build_off_app_contact_evidence(text, finding_matches)
        elif finding_type == FINDING_TYPE_PAYMENT_PRESSURE:
            finding_matches = payment_pressure_contributing_matches(
                text,
                finding_matches,
            )
            if not finding_matches:
                continue
            evidence = build_payment_pressure_evidence(text, finding_matches)
        else:
            evidence = build_phrase_evidence(text, finding_matches)

        if not evidence:
            continue
        if evidence_rule_pairs(evidence) != {
            (match.rule_id, match.rule_version) for match in finding_matches
        }:
            raise ModerationEvidenceError(
                "Bounded evidence does not retain every contributing rule."
            )
        findings.append(
            ContentModerationFinding(
                risk_area=finding_matches[0].risk_area,
                finding_type=finding_type,
                priority=priority_max(finding_matches),
                source_field=field.field_name,
                field_purpose=field.purpose,
                source_content_hash=source_content_hash,
                evidence_fingerprint=fingerprint_matches(
                    finding_type,
                    field.field_name,
                    evidence,
                ),
                evidence=evidence,
                matched_rule_ids=matched_rule_ids(finding_matches),
                matched_rule_versions=matched_rule_versions(finding_matches),
            )
        )
    return findings


def build_field_findings(
    field: ModerationTextField,
    *,
    target_context: str = TARGET_CONTEXT_COMMUNITY_GAME,
) -> list[ContentModerationFinding]:
    findings = _build_field_findings(field, target_context=target_context)
    text = str(field.value or "")
    for finding in findings:
        validate_saved_span_evidence(
            source_text=text,
            source_content_hash=finding.source_content_hash,
            evidence_fingerprint=finding.evidence_fingerprint,
            finding_type=finding.finding_type,
            risk_area=finding.risk_area,
            priority=finding.priority,
            target_context=target_context,
            source_field=finding.source_field,
            field_purpose=finding.field_purpose,
            evidence=finding.evidence,
            matched_rule_ids=finding.matched_rule_ids,
            matched_rule_versions=finding.matched_rule_versions,
            canonicalization_version=SAVED_CONTENT_PROFILE.canonicalization_version,
            maximum_items=SAVED_CONTENT_PROFILE.evidence_limits["items"],
        )
    return findings


def canonical_findings_for_fields(
    fields: list[ModerationTextField],
    *,
    target_context: str,
) -> list[ContentModerationFinding]:
    findings: list[ContentModerationFinding] = []
    seen_keys: set[tuple[str, str, str, str]] = set()
    for field in fields:
        for finding in _build_field_findings(field, target_context=target_context):
            key = (
                finding.risk_area,
                finding.source_field,
                finding.finding_type,
                finding.evidence_fingerprint,
            )
            if key not in seen_keys:
                seen_keys.add(key)
                findings.append(finding)
    return findings


def build_content_moderation_findings(
    fields: list[ModerationTextField],
    *,
    target_context: str = TARGET_CONTEXT_COMMUNITY_GAME,
    wall_clock: Callable[[], datetime] | None = None,
    monotonic_clock: Callable[[], int] = monotonic_ns,
) -> ContentModerationScanResult:
    validate_field_inventory(fields, target_context=target_context)
    started_ns = monotonic_clock()
    findings = canonical_findings_for_fields(fields, target_context=target_context)
    provenance_kwargs = {}
    if wall_clock is not None:
        provenance_kwargs["wall_clock"] = wall_clock
    provenance = build_scan_provenance(
        profile=SAVED_CONTENT_PROFILE,
        target_context=target_context,
        started_ns=started_ns,
        monotonic_clock=monotonic_clock,
        **provenance_kwargs,
    )
    result = ContentModerationScanResult(
        scanned_fields=tuple(fields),
        findings=tuple(findings),
        provenance=provenance,
    )
    validate_content_moderation_scan_result(result)
    return result
