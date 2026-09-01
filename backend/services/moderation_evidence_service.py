"""Versioned moderation hashing, identity, and evidence validation helpers."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence

from backend.services.moderation_taxonomy import (
    CANONICALIZATION_VERSION,
    CHAT_PROFILE_ID,
    EVIDENCE_KIND_CONTEXT_PREDICATE,
    EVIDENCE_KIND_SPAN,
    EVIDENCE_TYPE_CONTACT_PHRASE,
    EVIDENCE_TYPE_EMAIL,
    EVIDENCE_TYPE_PAYMENT_PRESSURE_PHRASE,
    EVIDENCE_TYPE_PHONE,
    EVIDENCE_TYPE_SOCIAL_HANDLE,
    EVIDENCE_TYPE_URL,
    EVIDENCE_TYPES,
    EXECUTION_KIND_CONTEXT_PREDICATE,
    EXECUTION_KIND_REGEX,
    FINDING_TYPE_OFF_APP_CONTACT,
    RISK_AREAS,
    RULES_BY_ID,
    SAVED_CONTENT_PROFILE_ID,
    SAVED_FINDING_TYPES,
    SAVED_PRIORITIES,
    TARGET_CONTEXT_GAME_CHAT,
    canonical_json,
    profile_for_context,
    rules_for_context,
)

SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class ModerationEvidenceError(ValueError):
    """Raised when evidence is incomplete, inconsistent, or tampered."""


def exact_source_hash(value: str | None) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def canonicalize_span_value(
    value: str,
    *,
    canonicalization_version: str = CANONICALIZATION_VERSION,
) -> str:
    if canonicalization_version != CANONICALIZATION_VERSION:
        raise ModerationEvidenceError("Unsupported canonicalization version.")
    return " ".join(value.strip().split()).casefold()


def sha256_canonical(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def span_evidence_fingerprint(
    *,
    outcome: str,
    source_field: str,
    atomic_values: Sequence[tuple[str, str]],
    canonicalization_version: str = CANONICALIZATION_VERSION,
) -> str:
    normalized = sorted(
        {
            (
                evidence_type,
                canonicalize_span_value(
                    value,
                    canonicalization_version=canonicalization_version,
                ),
            )
            for evidence_type, value in atomic_values
        }
    )
    return sha256_canonical(
        {
            "matches": normalized,
            "outcome": outcome,
            "source_field": source_field,
        }
    )


def context_predicate_fingerprint(
    *,
    category: str,
    source_field: str,
    source_content_hash: str,
    predicate_key: str,
    predicate_version: str,
    reference_message_id: str,
    reference_source_hash: str,
) -> str:
    return sha256_canonical(
        {
            "category": category,
            "outcome": True,
            "predicate_key": predicate_key,
            "predicate_version": predicate_version,
            "reference_message_id": reference_message_id,
            "reference_source_hash": reference_source_hash,
            "source_content_hash": source_content_hash,
            "source_field": source_field,
        }
    )


def durable_identity_hash(payload: Mapping[str, object]) -> str:
    return sha256_canonical(dict(payload))


def validate_sha256(value: str, *, field_name: str) -> None:
    if not SHA256_PATTERN.fullmatch(value):
        raise ModerationEvidenceError(f"{field_name} must be lowercase SHA-256.")


def _validated_rule_versions(
    values: Sequence[Mapping[str, str]],
) -> tuple[tuple[str, str], ...]:
    pairs: list[tuple[str, str]] = []
    expected_fields = {"rule_id", "rule_version"}
    for value in values:
        if not isinstance(value, Mapping) or set(value) != expected_fields:
            raise ModerationEvidenceError("Matched rule-version fields are invalid.")
        rule_id = value.get("rule_id")
        rule_version = value.get("rule_version")
        if (
            not isinstance(rule_id, str)
            or not rule_id
            or not isinstance(rule_version, str)
            or not rule_version
        ):
            raise ModerationEvidenceError("Matched rule-version values are invalid.")
        pairs.append((rule_id, rule_version))
    if not pairs or len(pairs) != len(set(pairs)):
        raise ModerationEvidenceError(
            "Matched rule versions must be non-empty and unique."
        )
    return tuple(pairs)


def _validate_source_field_contract(
    *,
    target_context: str,
    expected_profile_id: str,
    source_field: str,
    field_purpose: str,
):
    profile = profile_for_context(target_context)
    if profile.profile_id != expected_profile_id:
        raise ModerationEvidenceError("Evidence target context uses the wrong profile.")
    if (source_field, field_purpose) not in profile.context_field_inventory.get(
        target_context, ()
    ):
        raise ModerationEvidenceError(
            "Evidence source field and purpose are outside the profile inventory."
        )
    return profile


def _chat_redaction_patterns():
    rules = {rule.rule_id: rule for rule in rules_for_context(TARGET_CONTEXT_GAME_CHAT)}
    return (
        (rules["phone_number.pattern"].compile_expression(), "[phone]"),
        (rules["email.pattern"].compile_expression(), "[email]"),
        (rules["link.pattern"].compile_expression(), "[link]"),
    )


def safe_chat_message_preview(message_body: str, *, limit: int) -> str:
    preview = " ".join(message_body.strip().split())
    for pattern, replacement in _chat_redaction_patterns():
        preview = pattern.sub(replacement, preview)
    if len(preview) <= limit:
        return preview
    return preview[: max(0, limit - 3)].rstrip() + "..."


def safe_chat_span_preview(
    message_body: str,
    *,
    start: int,
    end: int,
    limit: int,
) -> str:
    preview_start = max(start - 28, 0)
    preview_end = min(end + 28, len(message_body))
    return safe_chat_message_preview(
        message_body[preview_start:preview_end],
        limit=limit,
    )


def bounded_saved_evidence_display(
    source_text: str,
    *,
    start: int,
    end: int,
    required_start: int,
    required_end: int,
    limit: int,
) -> tuple[str, bool, bool]:
    """Return a bounded display while preserving the exact evidence span."""

    if not 0 <= start <= required_start < required_end <= end <= len(source_text):
        raise ModerationEvidenceError("Saved evidence display bounds are invalid.")
    if limit <= 0:
        raise ModerationEvidenceError("Saved evidence display limit is invalid.")

    if end - start <= limit:
        display_start, display_end = start, end
    elif required_end - required_start >= limit:
        display_start = required_start
        display_end = required_start + limit
    else:
        available_context = limit - (required_end - required_start)
        before = min(required_start - start, available_context // 2)
        after = min(end - required_end, available_context - before)
        unused = available_context - before - after
        if unused:
            extra_before = min(required_start - start - before, unused)
            before += extra_before
            unused -= extra_before
            after += min(end - required_end - after, unused)
        display_start = required_start - before
        display_end = required_end + after

    truncated_before = display_start > start
    truncated_after = display_end < end
    display_text = source_text[display_start:display_end].strip()
    if truncated_before:
        display_text = f"...{display_text}"
    if truncated_after:
        display_text = f"{display_text}..."
    return display_text, truncated_before, truncated_after


def canonical_saved_item_evidence_type(
    finding_type: str,
    nested_types: set[str],
) -> str:
    if finding_type == FINDING_TYPE_OFF_APP_CONTACT:
        entity_types = nested_types & {
            EVIDENCE_TYPE_EMAIL,
            EVIDENCE_TYPE_PHONE,
            EVIDENCE_TYPE_SOCIAL_HANDLE,
            EVIDENCE_TYPE_URL,
        }
        if len(entity_types) > 1:
            raise ModerationEvidenceError(
                "Saved evidence item has multiple primary entity types."
            )
        if entity_types:
            return next(iter(entity_types))
        if nested_types == {EVIDENCE_TYPE_CONTACT_PHRASE}:
            return EVIDENCE_TYPE_CONTACT_PHRASE
    elif EVIDENCE_TYPE_PAYMENT_PRESSURE_PHRASE in nested_types:
        return EVIDENCE_TYPE_PAYMENT_PRESSURE_PHRASE
    elif len(nested_types) == 1:
        return next(iter(nested_types))
    raise ModerationEvidenceError("Saved evidence item has no canonical owner type.")


def validate_saved_span_evidence(
    *,
    source_text: str,
    source_content_hash: str,
    evidence_fingerprint: str,
    finding_type: str,
    risk_area: str,
    priority: str,
    target_context: str,
    source_field: str,
    field_purpose: str,
    evidence: list[dict],
    matched_rule_ids: Sequence[str],
    matched_rule_versions: Sequence[Mapping[str, str]],
    canonicalization_version: str,
    maximum_items: int,
) -> None:
    profile = _validate_source_field_contract(
        target_context=target_context,
        expected_profile_id=SAVED_CONTENT_PROFILE_ID,
        source_field=source_field,
        field_purpose=field_purpose,
    )
    if canonicalization_version != profile.canonicalization_version:
        raise ModerationEvidenceError("Saved evidence canonicalization is invalid.")
    if (
        finding_type not in SAVED_FINDING_TYPES
        or priority not in SAVED_PRIORITIES
        or risk_area not in RISK_AREAS
    ):
        raise ModerationEvidenceError("Saved finding priority or risk area is invalid.")
    validate_sha256(source_content_hash, field_name="source_content_hash")
    validate_sha256(evidence_fingerprint, field_name="evidence_fingerprint")
    if source_content_hash != exact_source_hash(source_text):
        raise ModerationEvidenceError("Source content hash does not match source text.")
    if maximum_items != profile.evidence_limits["items"]:
        raise ModerationEvidenceError("Saved-content evidence cap is not canonical.")
    if not isinstance(evidence, list) or not evidence or len(evidence) > maximum_items:
        raise ModerationEvidenceError("Saved-content evidence count is invalid.")

    declared_version_pairs = _validated_rule_versions(matched_rule_versions)
    if declared_version_pairs != tuple(sorted(declared_version_pairs)):
        raise ModerationEvidenceError("Matched rule versions are not canonical.")
    declared_versions = set(declared_version_pairs)
    if (
        not all(isinstance(rule_id, str) and rule_id for rule_id in matched_rule_ids)
        or len(matched_rule_ids) != len(set(matched_rule_ids))
        or tuple(matched_rule_ids)
        != tuple(rule_id for rule_id, _rule_version in declared_version_pairs)
    ):
        raise ModerationEvidenceError("Matched rule IDs do not match rule versions.")

    expected_item_fields = {
        "evidence_type",
        "display_text",
        "start",
        "end",
        "matches",
        "truncated_before",
        "truncated_after",
        "additional_match_count",
    }
    expected_match_fields = {
        "rule_id",
        "rule_version",
        "evidence_type",
        "matched_text",
        "start",
        "end",
    }
    atomic_values: list[tuple[str, str]] = []
    evidence_versions: set[tuple[str, str]] = set()
    matched_priorities: list[str] = []
    for item_index, item in enumerate(evidence):
        if not isinstance(item, dict) or set(item) != expected_item_fields:
            raise ModerationEvidenceError("Saved evidence item fields are invalid.")
        item_evidence_type = item.get("evidence_type")
        if item_evidence_type not in EVIDENCE_TYPES:
            raise ModerationEvidenceError("Saved evidence item type is invalid.")
        start = item.get("start")
        end = item.get("end")
        if type(start) is not int or type(end) is not int:
            raise ModerationEvidenceError("Span evidence requires integer offsets.")
        if not 0 <= start < end <= len(source_text):
            raise ModerationEvidenceError("Span evidence offsets are out of range.")
        matches = item.get("matches")
        if not isinstance(matches, list) or not matches:
            raise ModerationEvidenceError("Span evidence requires nested matches.")
        truncated_before = item.get("truncated_before")
        truncated_after = item.get("truncated_after")
        additional_match_count = item.get("additional_match_count")
        if not isinstance(truncated_before, bool) or not isinstance(
            truncated_after, bool
        ):
            raise ModerationEvidenceError("Evidence truncation flags are invalid.")
        if type(additional_match_count) is not int or additional_match_count < 0:
            raise ModerationEvidenceError("Additional evidence count is invalid.")
        if additional_match_count and item_index != len(evidence) - 1:
            raise ModerationEvidenceError(
                "Only the final evidence item may record omitted matches."
            )
        if len(evidence) < maximum_items and additional_match_count:
            raise ModerationEvidenceError(
                "Evidence below the item cap cannot report omitted matches."
            )

        nested_types: set[str] = set()
        nested_keys: list[tuple[str, str, str, int, int, str]] = []
        for match in matches:
            if not isinstance(match, dict) or set(match) != expected_match_fields:
                raise ModerationEvidenceError("Nested evidence fields are invalid.")
            rule_id = match.get("rule_id")
            rule_version = match.get("rule_version")
            evidence_type = match.get("evidence_type")
            if (
                not isinstance(rule_id, str)
                or not rule_id
                or not isinstance(rule_version, str)
                or not rule_version
                or not isinstance(evidence_type, str)
                or not evidence_type
            ):
                raise ModerationEvidenceError(
                    "Nested evidence identifiers are invalid."
                )
            rule = RULES_BY_ID.get(rule_id)
            match_start = match.get("start")
            match_end = match.get("end")
            matched_text = match.get("matched_text")
            if (
                rule is None
                or rule.execution_kind != EXECUTION_KIND_REGEX
                or rule.rule_version != rule_version
                or rule.profile_id != SAVED_CONTENT_PROFILE_ID
                or rule.outcome != finding_type
                or rule.risk_area != risk_area
                or rule.evidence_type != evidence_type
                or target_context not in rule.target_contexts
                or field_purpose not in rule.allowed_field_purposes
                or (rule_id, rule_version) not in declared_versions
            ):
                raise ModerationEvidenceError("Evidence rule attribution is invalid.")
            if type(match_start) is not int or type(match_end) is not int:
                raise ModerationEvidenceError("Nested match offsets are invalid.")
            if not start <= match_start < match_end <= end:
                raise ModerationEvidenceError(
                    "Nested match lies outside evidence span."
                )
            if matched_text != source_text[match_start:match_end]:
                raise ModerationEvidenceError(
                    "Matched text does not equal source slice."
                )
            atomic_values.append((evidence_type, matched_text))
            nested_types.add(evidence_type)
            evidence_versions.add((rule_id, rule_version))
            matched_priorities.append(rule.priority_or_severity)
            nested_keys.append(
                (
                    rule_id,
                    rule_version,
                    evidence_type,
                    match_start,
                    match_end,
                    matched_text,
                )
            )
        canonical_nested_keys = sorted(
            nested_keys,
            key=lambda value: (value[3], value[4], value[0], value[1], value[2]),
        )
        if nested_keys != canonical_nested_keys or len(nested_keys) != len(
            set(nested_keys)
        ):
            raise ModerationEvidenceError(
                "Nested evidence matches are duplicated or noncanonical."
            )
        if item_evidence_type != canonical_saved_item_evidence_type(
            finding_type, nested_types
        ):
            raise ModerationEvidenceError("Saved evidence item type is not canonical.")

        required_start = min(key[3] for key in nested_keys)
        required_end = max(key[4] for key in nested_keys)
        source_display_limit = profile.evidence_limits[
            "entity" if finding_type == FINDING_TYPE_OFF_APP_CONTACT else "phrase"
        ]
        expected_display, expected_before, expected_after = (
            bounded_saved_evidence_display(
                source_text,
                start=start,
                end=end,
                required_start=required_start,
                required_end=required_end,
                limit=source_display_limit,
            )
        )
        display_text = item.get("display_text")
        if (
            not isinstance(display_text, str)
            or display_text != expected_display
            or truncated_before is not expected_before
            or truncated_after is not expected_after
            or len(display_text) > source_display_limit + 6
        ):
            raise ModerationEvidenceError("Saved evidence display text is invalid.")

    item_keys = [
        (
            int(item["start"]),
            int(item["end"]),
            str(item["evidence_type"]),
            canonical_json(item["matches"]),
        )
        for item in evidence
    ]
    if item_keys != sorted(item_keys) or len(item_keys) != len(set(item_keys)):
        raise ModerationEvidenceError(
            "Saved evidence items are duplicated or noncanonical."
        )

    if evidence_versions != declared_versions:
        raise ModerationEvidenceError(
            "Matched rule versions do not exactly equal evidence attribution."
        )
    priority_rank = {"attention": 0, "urgent": 1, "critical": 2}
    if max(matched_priorities, key=priority_rank.__getitem__) != priority:
        raise ModerationEvidenceError(
            "Saved finding priority does not match its rules."
        )

    expected = span_evidence_fingerprint(
        outcome=finding_type,
        source_field=source_field,
        atomic_values=atomic_values,
        canonicalization_version=canonicalization_version,
    )
    if expected != evidence_fingerprint:
        raise ModerationEvidenceError("Evidence fingerprint does not recompute.")


def validate_chat_evidence(
    *,
    source_text: str,
    category: str,
    severity: str,
    target_context: str,
    source_field: str,
    field_purpose: str,
    source_content_hash: str,
    evidence_fingerprint: str,
    evidence: dict,
    public_rule_key: str,
    registry_rule_id: str,
    rule_version: str,
    matched_rule_versions: Sequence[Mapping[str, str]],
    matched_preview: str,
    canonicalization_version: str,
) -> None:
    profile = _validate_source_field_contract(
        target_context=target_context,
        expected_profile_id=CHAT_PROFILE_ID,
        source_field=source_field,
        field_purpose=field_purpose,
    )
    if canonicalization_version != profile.canonicalization_version:
        raise ModerationEvidenceError("Chat evidence canonicalization is invalid.")
    validate_sha256(source_content_hash, field_name="source_content_hash")
    validate_sha256(evidence_fingerprint, field_name="evidence_fingerprint")
    if exact_source_hash(source_text) != source_content_hash:
        raise ModerationEvidenceError("Chat source hash does not match message body.")
    rule = RULES_BY_ID.get(registry_rule_id)
    declared_versions = _validated_rule_versions(matched_rule_versions)
    if (
        rule is None
        or rule.profile_id != CHAT_PROFILE_ID
        or rule.rule_version != rule_version
        or rule.outcome != category
        or rule.priority_or_severity != severity
        or rule.persisted_rule_key != public_rule_key
        or target_context not in rule.target_contexts
        or field_purpose not in rule.allowed_field_purposes
        or declared_versions != ((registry_rule_id, rule_version),)
    ):
        raise ModerationEvidenceError("Chat evidence rule attribution is invalid.")
    if not isinstance(evidence, dict):
        raise ModerationEvidenceError("Chat evidence must be an object.")

    evidence_kind = evidence.get("evidence_kind")
    if evidence_kind == EVIDENCE_KIND_SPAN:
        if rule.execution_kind != EXECUTION_KIND_REGEX:
            raise ModerationEvidenceError(
                "Predicate evidence cannot masquerade as a span."
            )
        allowed = {
            "evidence_kind",
            "evidence_type",
            "start",
            "end",
            "matched_source_hash",
        }
        if set(evidence) != allowed:
            raise ModerationEvidenceError("Span chat evidence fields are invalid.")
        if evidence.get("evidence_type") != rule.evidence_type:
            raise ModerationEvidenceError("Span chat evidence type is invalid.")
        start = evidence.get("start")
        end = evidence.get("end")
        if type(start) is not int or type(end) is not int:
            raise ModerationEvidenceError("Span chat evidence requires offsets.")
        if not 0 <= start < end <= len(source_text):
            raise ModerationEvidenceError(
                "Span chat evidence offsets are out of range."
            )
        source_slice = source_text[start:end]
        if evidence.get("matched_source_hash") != exact_source_hash(source_slice):
            raise ModerationEvidenceError("Matched chat evidence hash is invalid.")
        expected = span_evidence_fingerprint(
            outcome=category,
            source_field=source_field,
            atomic_values=[(str(evidence.get("evidence_type")), source_slice)],
            canonicalization_version=canonicalization_version,
        )
        expected_preview = safe_chat_span_preview(
            source_text,
            start=start,
            end=end,
            limit=profile.evidence_limits["preview"],
        )
    elif evidence_kind == EVIDENCE_KIND_CONTEXT_PREDICATE:
        if rule.execution_kind != EXECUTION_KIND_CONTEXT_PREDICATE:
            raise ModerationEvidenceError("Regex evidence cannot use predicate shape.")
        allowed = {
            "evidence_kind",
            "outcome",
            "predicate_key",
            "predicate_version",
            "reference_message_id",
            "reference_source_hash",
        }
        if set(evidence) != allowed or evidence.get("outcome") is not True:
            raise ModerationEvidenceError(
                "Context predicate evidence fields are invalid."
            )
        if (
            evidence.get("predicate_key") != rule.predicate_key
            or evidence.get("predicate_version") != rule.predicate_version
        ):
            raise ModerationEvidenceError("Context predicate version is invalid.")
        reference_id = evidence.get("reference_message_id")
        reference_hash = evidence.get("reference_source_hash")
        if not isinstance(reference_id, str) or not reference_id.strip():
            raise ModerationEvidenceError("Context predicate reference is missing.")
        if not isinstance(reference_hash, str):
            raise ModerationEvidenceError(
                "reference_source_hash must be lowercase SHA-256."
            )
        validate_sha256(reference_hash, field_name="reference_source_hash")
        expected = context_predicate_fingerprint(
            category=category,
            source_field=source_field,
            source_content_hash=source_content_hash,
            predicate_key=str(evidence["predicate_key"]),
            predicate_version=str(evidence["predicate_version"]),
            reference_message_id=reference_id,
            reference_source_hash=reference_hash,
        )
        expected_preview = safe_chat_message_preview(
            source_text,
            limit=profile.evidence_limits["preview"],
        )
    else:
        raise ModerationEvidenceError("Chat evidence discriminator is invalid.")

    if expected != evidence_fingerprint:
        raise ModerationEvidenceError("Chat evidence fingerprint does not recompute.")
    if (
        not isinstance(matched_preview, str)
        or matched_preview != expected_preview
        or len(matched_preview) > profile.evidence_limits["preview"]
    ):
        raise ModerationEvidenceError(
            "Chat evidence preview is not the safe source preview."
        )
