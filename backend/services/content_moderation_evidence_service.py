"""Build admin-facing content moderation evidence from scanner matches."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from json import dumps

from backend.services.content_moderation_scanner_service import (
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
    ModerationTextField,
    ContentModerationRuleMatch,
    SCANNER_VERSION,
    content_hash,
    normalize_scan_text,
    scan_text_field_matches,
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
ENTITY_EVIDENCE_LIMIT = 120
PHRASE_EVIDENCE_LIMIT = 200
MAX_EVIDENCE_ITEMS = 8
PRIORITY_RANK = {"attention": 0, "urgent": 1, "critical": 2}


@dataclass(frozen=True)
class ContentModerationFinding:
    risk_area: str
    finding_type: str
    priority: str
    source_field: str
    source_content_hash: str
    evidence_fingerprint: str
    evidence: list[dict]
    matched_rule_ids: tuple[str, ...]
    scanner_version: str = SCANNER_VERSION


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


def matches_overlap(left: ContentModerationRuleMatch, right: ContentModerationRuleMatch) -> bool:
    return left.start < right.end and right.start < left.end


def same_clause(
    text: str,
    left: ContentModerationRuleMatch,
    right: ContentModerationRuleMatch,
) -> bool:
    return previous_boundary(text, left.start) == previous_boundary(text, right.start)


def cap_display_span(
    text: str,
    start: int,
    end: int,
    *,
    required_start: int,
    required_end: int,
    limit: int,
) -> tuple[int, int, bool, bool]:
    start, end = trim_span_whitespace(text, start, end)
    if end - start <= limit:
        return start, end, False, False

    required_start = max(required_start, start)
    required_end = min(required_end, end)
    available_context = max(0, limit - (required_end - required_start))
    before = min(required_start - start, available_context // 2)
    after = min(end - required_end, available_context - before)
    capped_start = required_start - before
    capped_end = required_end + after

    while capped_start > start and not text[capped_start - 1].isspace():
        capped_start += 1
        if capped_start >= required_start:
            capped_start = required_start
            break
    while capped_end < end and not text[capped_end].isspace():
        capped_end -= 1
        if capped_end <= required_end:
            capped_end = required_end
            break

    return capped_start, capped_end, capped_start > start, capped_end < end


def build_evidence_match(match: ContentModerationRuleMatch) -> dict:
    return {
        "rule_id": match.rule_id,
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
    required_start = min(match.start for match in matches)
    required_end = max(match.end for match in matches)
    start, end, truncated_before, truncated_after = cap_display_span(
        text,
        start,
        end,
        required_start=required_start,
        required_end=required_end,
        limit=limit,
    )
    display_text = text[start:end].strip()
    if truncated_before:
        display_text = f"...{display_text}"
    if truncated_after:
        display_text = f"{display_text}..."

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
    unique: dict[tuple[str, str, int, int], ContentModerationRuleMatch] = {}
    for match in sorted(matches, key=lambda item: (item.start, item.end, item.rule_id)):
        key = (match.evidence_type, normalize_fingerprint_value(match.matched_text), match.start, match.end)
        unique.setdefault(key, match)
    return list(unique.values())


def remove_contained_link_matches(
    matches: list[ContentModerationRuleMatch],
) -> list[ContentModerationRuleMatch]:
    email_matches = [match for match in matches if match.evidence_type == EVIDENCE_TYPE_EMAIL]
    filtered: list[ContentModerationRuleMatch] = []
    for match in matches:
        if match.evidence_type == EVIDENCE_TYPE_URL and any(
            email.start <= match.start and match.end <= email.end for email in email_matches
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
                limit=ENTITY_EVIDENCE_LIMIT,
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
                limit=ENTITY_EVIDENCE_LIMIT,
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
                limit=PHRASE_EVIDENCE_LIMIT,
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
                limit=PHRASE_EVIDENCE_LIMIT,
            )
        )
    return dedupe_evidence_items(evidence_items)


def dedupe_evidence_items(items: list[dict]) -> list[dict]:
    unique: dict[tuple[int, int, str], dict] = {}
    for item in sorted(items, key=lambda row: (row["start"], row["end"], row["evidence_type"])):
        key = (item["start"], item["end"], item["evidence_type"])
        unique.setdefault(key, item)

    deduped = list(unique.values())
    if len(deduped) <= MAX_EVIDENCE_ITEMS:
        return deduped

    visible = deduped[:MAX_EVIDENCE_ITEMS]
    visible[-1]["additional_match_count"] = len(deduped) - MAX_EVIDENCE_ITEMS
    return visible


def fingerprint_matches(
    finding_type: str,
    source_field: str,
    evidence: list[dict],
) -> str:
    atomic_values: list[tuple[str, str]] = []
    has_entity = any(
        match["evidence_type"] in ENTITY_EVIDENCE_TYPES
        for item in evidence
        for match in item["matches"]
    )
    for item in evidence:
        for match in item["matches"]:
            if has_entity and match["evidence_type"] == EVIDENCE_TYPE_CONTACT_PHRASE:
                continue
            atomic_values.append(
                (
                    str(match["evidence_type"]),
                    normalize_fingerprint_value(str(match["matched_text"])),
                )
            )
    payload = {
        "finding_type": finding_type,
        "source_field": source_field,
        "matches": sorted(dict.fromkeys(atomic_values)),
    }
    serialized = dumps(payload, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def matched_rule_ids(matches: list[ContentModerationRuleMatch]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(match.rule_id for match in matches))


def should_include_match(match: ContentModerationRuleMatch) -> bool:
    if (
        match.finding_type == FINDING_TYPE_OFF_APP_CONTACT
        and match.source_field_purpose
        in {FIELD_PURPOSE_ADDRESS, FIELD_PURPOSE_PAYMENT, FIELD_PURPOSE_PAYMENT_METHOD}
    ):
        return False
    if (
        match.finding_type == FINDING_TYPE_PAYMENT_PRESSURE
        and match.source_field_purpose == FIELD_PURPOSE_PAYMENT_METHOD
    ):
        return False
    return True


def build_field_findings(field: ModerationTextField) -> list[ContentModerationFinding]:
    text = str(field.value or "")
    matches = [
        match for match in remove_contained_link_matches(scan_text_field_matches(field))
        if should_include_match(match)
    ]
    if not matches:
        return []

    source_content_hash = content_hash(text)
    findings: list[ContentModerationFinding] = []
    finding_types = tuple(dict.fromkeys(match.finding_type for match in matches))
    for finding_type in finding_types:
        finding_matches = [match for match in matches if match.finding_type == finding_type]
        if finding_type == FINDING_TYPE_OFF_APP_CONTACT:
            evidence = build_off_app_contact_evidence(text, finding_matches)
        elif finding_type == FINDING_TYPE_PAYMENT_PRESSURE:
            if not any(
                match.evidence_type == EVIDENCE_TYPE_PAYMENT_PRESSURE_PHRASE
                for match in finding_matches
            ):
                continue
            evidence = build_payment_pressure_evidence(text, finding_matches)
        else:
            evidence = build_phrase_evidence(text, finding_matches)

        if not evidence:
            continue
        findings.append(
            ContentModerationFinding(
                risk_area=finding_matches[0].risk_area,
                finding_type=finding_type,
                priority=priority_max(finding_matches),
                source_field=field.field_name,
                source_content_hash=source_content_hash,
                evidence_fingerprint=fingerprint_matches(
                    finding_type,
                    field.field_name,
                    evidence,
                ),
                evidence=evidence,
                matched_rule_ids=matched_rule_ids(finding_matches),
            )
        )
    return findings


def build_content_moderation_findings(
    fields: list[ModerationTextField],
) -> list[ContentModerationFinding]:
    findings: list[ContentModerationFinding] = []
    seen_keys: set[tuple[str, str, str, str]] = set()
    for field in fields:
        for finding in build_field_findings(field):
            key = (
                finding.risk_area,
                finding.source_field,
                finding.finding_type,
                finding.evidence_fingerprint,
            )
            if key in seen_keys:
                continue
            seen_keys.add(key)
            findings.append(finding)
    return findings
