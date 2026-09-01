from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from backend.services.chat_moderation_service import (
    CHAT_DETECTION_CATEGORIES,
    ContextPredicateFact,
    chat_detection_record_values,
    detect_chat_message,
    repeated_message_fact,
)
from backend.services.content_moderation_evidence_service import (
    build_content_moderation_findings,
    validate_content_moderation_scan_result,
)
from backend.services.content_moderation_scanner_service import ModerationTextField
from backend.services.moderation_evidence_service import (
    ModerationEvidenceError,
    context_predicate_fingerprint,
    exact_source_hash,
    validate_chat_evidence,
    validate_saved_span_evidence,
)
from backend.services.moderation_surfacing_service import aggregate_chat_detections
from backend.services.moderation_taxonomy import (
    CHAT_CONTEXTS,
    CHAT_DETECTION_OUTCOMES,
    CHAT_PROFILE,
    EVIDENCE_TYPES,
    EXECUTION_KIND_CONTEXT_PREDICATE,
    EXECUTION_KIND_REGEX,
    FIELD_PURPOSE_CHAT,
    FIELD_PURPOSE_GENERAL,
    REPEATED_MESSAGE_RULE_ID,
    RULES,
    RULES_BY_ID,
    SAVED_CONTENT_PROFILE,
    SAVED_FINDING_TYPES,
    SAVED_PRIORITIES,
    TARGET_CONTEXT_COMMUNITY_GAME,
    TARGET_CONTEXT_GAME_CHAT,
    TARGET_CONTEXT_NEED_A_SUB_CHAT,
    ModerationTaxonomyError,
    profile_configuration_hash,
    validate_registry,
)

pytestmark = [pytest.mark.suite_type("ordinary"), pytest.mark.no_db_cleanup]

_INVALID_NESTED_IDENTIFIER_VALUES = (
    pytest.param(1, id="numeric"),
    pytest.param(True, id="boolean"),
    pytest.param(None, id="null"),
    pytest.param(["1"], id="list"),
    pytest.param({"value": "1"}, id="object"),
)


def _community_fields(**values: str | None) -> list[ModerationTextField]:
    return [
        ModerationTextField(name, name, values.get(name), purpose)
        for name, purpose in SAVED_CONTENT_PROFILE.context_field_inventory[
            TARGET_CONTEXT_COMMUNITY_GAME
        ]
    ]


@pytest.mark.requirement("WS03-05A-R1", "WS03-05A-R2")
def test_registry_is_finite_unique_attributable_and_profile_complete() -> None:
    validate_registry()
    assert len(RULES) == len(RULES_BY_ID) == 23
    assert set(CHAT_PROFILE.context_field_inventory) == set(CHAT_CONTEXTS)
    assert set(SAVED_CONTENT_PROFILE.context_field_inventory) == {
        "community_game",
        "need_a_sub",
    }
    assert {
        RULES_BY_ID[rule_id].outcome for rule_id in CHAT_PROFILE.enabled_rule_ids
    } == CHAT_DETECTION_CATEGORIES
    assert {rule.execution_kind for rule in RULES} == {
        EXECUTION_KIND_REGEX,
        EXECUTION_KIND_CONTEXT_PREDICATE,
    }
    assert all(rule.rule_version and rule.language_scope for rule in RULES)
    assert all(
        profile_configuration_hash(profile)
        for profile in (SAVED_CONTENT_PROFILE, CHAT_PROFILE)
    )


@pytest.mark.requirement("WS03-05A-R1")
def test_registry_rejects_duplicate_and_mixed_execution_kind_definitions() -> None:
    with pytest.raises(ModerationTaxonomyError, match="unique"):
        validate_registry(rules=(*RULES, RULES[0]))

    predicate = RULES_BY_ID[REPEATED_MESSAGE_RULE_ID]
    mixed = replace(predicate, expression_source="unsafe")
    changed = tuple(mixed if rule.rule_id == mixed.rule_id else rule for rule in RULES)
    with pytest.raises(ModerationTaxonomyError, match="mixed"):
        validate_registry(rules=changed)


@pytest.mark.requirement("WS03-05A-R1", "WS03-05A-R6")
@pytest.mark.parametrize(
    ("attribute", "invalid_value"),
    (
        ("outcome", "not_a_finding"),
        ("priority_or_severity", "not_a_priority"),
        ("evidence_type", "not_evidence"),
        ("risk_area", "not_a_risk_area"),
        ("language_scope", "not_a_language"),
        ("target_contexts", ("not_a_context",)),
        ("allowed_field_purposes", ("not_a_purpose",)),
        ("profile_id", "not_a_profile"),
        ("execution_kind", "not_an_execution_kind"),
        ("supporting_only", "not_a_boolean"),
    ),
)
def test_registry_rejects_mutated_saved_rule_finite_values(
    attribute: str,
    invalid_value: object,
) -> None:
    rule = RULES_BY_ID["personal_info.phone_number"]
    mutated = replace(rule, **{attribute: invalid_value})
    changed = tuple(mutated if item.rule_id == rule.rule_id else item for item in RULES)
    with pytest.raises(ModerationTaxonomyError):
        validate_registry(rules=changed)


@pytest.mark.requirement("WS03-05A-R1", "WS03-05A-R6")
def test_registry_rejects_mutated_chat_outcome_severity_and_external_key() -> None:
    rule = RULES_BY_ID["chat.harassment_or_abuse.phrase"]
    for changed_rule in (
        replace(rule, outcome="not_a_category"),
        replace(rule, priority_or_severity="not_a_severity"),
        replace(rule, external_rule_key="phone_number.pattern"),
    ):
        changed = tuple(
            changed_rule if item.rule_id == rule.rule_id else item for item in RULES
        )
        with pytest.raises(ModerationTaxonomyError):
            validate_registry(rules=changed)


@pytest.mark.requirement("WS03-05A-R1")
@pytest.mark.parametrize(
    ("rule_id", "purposes"),
    (
        ("personal_info.phone_number", (FIELD_PURPOSE_CHAT,)),
        ("personal_info.phone_number", ("address",)),
        ("phone_number.pattern", (FIELD_PURPOSE_GENERAL,)),
    ),
)
def test_registry_rejects_cross_profile_or_unreachable_field_purposes(
    rule_id: str,
    purposes: tuple[str, ...],
) -> None:
    rule = RULES_BY_ID[rule_id]
    mutated = replace(rule, allowed_field_purposes=purposes)
    changed = tuple(mutated if item.rule_id == rule_id else item for item in RULES)

    with pytest.raises(ModerationTaxonomyError):
        validate_registry(rules=changed)


@pytest.mark.requirement("WS03-05A-R1", "WS03-05A-R6")
def test_registry_rejects_incomplete_duplicate_or_invalid_profile_relationships() -> (
    None
):
    duplicate_enabled = replace(
        CHAT_PROFILE,
        enabled_rule_ids=(
            *CHAT_PROFILE.enabled_rule_ids,
            CHAT_PROFILE.enabled_rule_ids[0],
        ),
    )
    missing_enabled = replace(
        CHAT_PROFILE,
        enabled_rule_ids=CHAT_PROFILE.enabled_rule_ids[:-1],
    )
    invalid_inventory = replace(
        CHAT_PROFILE,
        context_field_inventory={
            **CHAT_PROFILE.context_field_inventory,
            "not_a_context": (("message_body", "chat"),),
        },
    )
    invalid_limits = replace(CHAT_PROFILE, evidence_limits={"preview": 120})
    for changed_profile in (
        duplicate_enabled,
        missing_enabled,
        invalid_inventory,
        invalid_limits,
    ):
        with pytest.raises(ModerationTaxonomyError):
            validate_registry(profiles=(SAVED_CONTENT_PROFILE, changed_profile))


@pytest.mark.requirement("WS03-05A-R1", "WS03-05A-R6")
def test_registry_finite_outcomes_and_priorities_match_persistence_contract() -> None:
    assert CHAT_DETECTION_CATEGORIES == set(CHAT_DETECTION_OUTCOMES)
    assert {
        RULES_BY_ID[rule_id].outcome
        for rule_id in SAVED_CONTENT_PROFILE.enabled_rule_ids
    } == set(SAVED_FINDING_TYPES)
    assert {
        RULES_BY_ID[rule_id].priority_or_severity
        for rule_id in SAVED_CONTENT_PROFILE.enabled_rule_ids
    } <= set(SAVED_PRIORITIES)
    assert {rule.evidence_type for rule in RULES} <= set(EVIDENCE_TYPES)


@pytest.mark.requirement("WS03-05A-R1", "WS03-05A-R2")
def test_repeated_message_behavior_changes_configuration_hash() -> None:
    original = profile_configuration_hash(CHAT_PROFILE)
    predicate = RULES_BY_ID[REPEATED_MESSAGE_RULE_ID]
    changed = replace(
        predicate,
        predicate_comparison_contract="candidate == reference",
    )
    changed_rules = dict(RULES_BY_ID)
    changed_rules[changed.rule_id] = changed
    assert (
        profile_configuration_hash(CHAT_PROFILE, rules_by_id=changed_rules) != original
    )


_REGEX_RULE_EXAMPLES = {
    "personal_info.phone_number": "312-555-1212",
    "personal_info.email": "player@example.invalid",
    "personal_info.link": "https://example.invalid/path",
    "off_app_contact.social_handle": "@pickup_player",
    "off_app_contact.phrase": "text me",
    "payment_method.phrase": "Venmo",
    "payment_handle.cash_app": "$pickup_player",
    "payment_pressure.phrase": "pay upfront",
    "payment_contact.phrase": "message me to pay",
    "spam_or_scam.phrase": "guaranteed money",
    "threat_or_violence.phrase": "I will hurt you",
    "harassment_or_abuse.phrase": "you are worthless",
    "slur_or_hate.phrase": "go back to your country",
    "sexual_or_explicit.phrase": "explicit sexual",
    "phone_number.pattern": "312-555-1212",
    "email.pattern": "player@example.invalid",
    "link.pattern": "https://example.invalid",
    "off_platform_contact.phrase": "text me",
    "payment_discussion.phrase": "send me money",
    "threat_or_safety.phrase": "I will hurt you",
    "chat.harassment_or_abuse.phrase": "you are worthless",
    "chat.slur_or_hate.phrase": "go back to your country",
}


@pytest.mark.requirement("WS03-05A-R1")
def test_every_registered_regex_rule_has_a_finite_behavior_example() -> None:
    regex_rules = {
        rule.rule_id: rule
        for rule in RULES
        if rule.execution_kind == EXECUTION_KIND_REGEX
    }
    assert set(_REGEX_RULE_EXAMPLES) == set(regex_rules)
    for rule_id, rule in regex_rules.items():
        assert rule.compile_expression().search(_REGEX_RULE_EXAMPLES[rule_id])


@pytest.mark.requirement("WS03-05A-R1", "WS03-05A-R3")
def test_chat_empty_overlap_and_punctuation_boundaries_are_deterministic() -> None:
    assert (
        detect_chat_message(
            "",
            target_context=TARGET_CONTEXT_GAME_CHAT,
        ).detections
        == ()
    )

    source = "Email player@example.com or visit https://example.com/path)."
    result = detect_chat_message(source, target_context=TARGET_CONTEXT_GAME_CHAT)
    categories = {detection.category for detection in result.detections}
    assert {"email", "link"} <= categories
    for detection in result.detections:
        start = detection.evidence["start"]
        end = detection.evidence["end"]
        assert source[start:end]
        assert not source[start:end].endswith((")", "."))


@pytest.mark.requirement("WS03-05A-R2", "WS03-05A-R3")
def test_saved_scan_uses_controlled_time_exact_hashes_and_raw_unicode_offsets() -> None:
    source = "🏀 Text me at 312-555-1212"
    ticks = iter((1_000_000, 1_009_000))
    scanned_at = datetime(2035, 5, 1, 12, 0, tzinfo=timezone.utc)
    result = build_content_moderation_findings(
        _community_fields(description=source),
        target_context=TARGET_CONTEXT_COMMUNITY_GAME,
        wall_clock=lambda: scanned_at,
        monotonic_clock=lambda: next(ticks),
    )

    finding = result.findings[0]
    phone_match = next(
        match
        for item in finding.evidence
        for match in item["matches"]
        if match["evidence_type"] == "phone"
    )
    assert source[phone_match["start"] : phone_match["end"]] == "312-555-1212"
    assert finding.source_content_hash == exact_source_hash(source)
    assert result.provenance.scanned_at == scanned_at
    assert result.provenance.execution_duration_us == 9


@pytest.mark.requirement("WS03-05A-R2", "WS03-05A-R3")
def test_saved_atomic_matches_keep_exact_spans_while_display_is_bounded() -> None:
    long_url = "https://example.com/" + "a" * 180
    long_email = f"{'b' * 180}@example.com"

    for source, evidence_type in ((long_url, "url"), (long_email, "email")):
        finding = build_content_moderation_findings(
            _community_fields(description=source),
            target_context=TARGET_CONTEXT_COMMUNITY_GAME,
        ).findings[0]
        item = next(
            item
            for item in finding.evidence
            if any(match["evidence_type"] == evidence_type for match in item["matches"])
        )
        match = next(
            match
            for match in item["matches"]
            if match["evidence_type"] == evidence_type
        )
        assert source[match["start"] : match["end"]] == source
        assert match["matched_text"] == source
        assert item["start"] <= match["start"] < match["end"] <= item["end"]
        assert len(item["display_text"]) <= (
            SAVED_CONTENT_PROFILE.evidence_limits["entity"] + 6
        )
        assert item["truncated_after"] is True


@pytest.mark.requirement("WS03-05A-R2", "WS03-05A-R3")
def test_over_cap_evidence_retains_every_contributing_rule_version() -> None:
    phones = " ".join(f"312-555-{1200 + index}" for index in range(8))
    source = f"{phones} player@example.com"
    finding = build_content_moderation_findings(
        _community_fields(description=source),
        target_context=TARGET_CONTEXT_COMMUNITY_GAME,
    ).findings[0]

    assert len(finding.evidence) == SAVED_CONTENT_PROFILE.evidence_limits["items"]
    assert finding.evidence[-1]["additional_match_count"] == 1
    assert set(finding.matched_rule_ids) == {
        "personal_info.email",
        "personal_info.phone_number",
    }
    assert {
        match["rule_id"] for item in finding.evidence for match in item["matches"]
    } == set(finding.matched_rule_ids)


@pytest.mark.requirement("WS03-05A-R1", "WS03-05A-R3")
@pytest.mark.parametrize(
    "target_context",
    (TARGET_CONTEXT_GAME_CHAT, TARGET_CONTEXT_NEED_A_SUB_CHAT),
)
def test_chat_public_rule_keys_remain_stable_with_unique_registry_ids(
    target_context: str,
) -> None:
    detections = detect_chat_message(
        "You are worthless. Go back to your country.",
        target_context=target_context,
    ).detections
    by_category = {detection.category: detection for detection in detections}

    assert by_category["harassment_or_abuse"].rule_key == ("harassment_or_abuse.phrase")
    assert by_category["slur_or_hate"].rule_key == "slur_or_hate.phrase"
    assert by_category["harassment_or_abuse"].registry_rule_id == (
        "chat.harassment_or_abuse.phrase"
    )
    assert by_category["slur_or_hate"].registry_rule_id == ("chat.slur_or_hate.phrase")


def _replace_first_finding(scan, **changes):
    return replace(scan, findings=(replace(scan.findings[0], **changes),))


@pytest.mark.requirement("WS03-05A-R2", "WS03-05A-R3", "WS03-05A-R5")
@pytest.mark.parametrize(
    "tamper",
    (
        "item_fields",
        "item_type",
        "display_text",
        "truncation",
        "nested_fields",
        "nested_evidence_type",
        "nested_rule_version",
        "nested_offsets",
        "declared_versions",
        "source_field",
        "field_purpose",
        "priority",
        "risk_area",
        "target_context",
    ),
)
def test_saved_evidence_rejects_complete_tampering_matrix(tamper: str) -> None:
    scan = build_content_moderation_findings(
        _community_fields(description="Text me at 312-555-1212"),
        target_context=TARGET_CONTEXT_COMMUNITY_GAME,
    )
    finding = scan.findings[0]
    evidence = deepcopy(finding.evidence)
    changes = {}

    if tamper == "item_fields":
        evidence[0]["unexpected"] = True
    elif tamper == "item_type":
        evidence[0]["evidence_type"] = "context_predicate"
    elif tamper == "display_text":
        evidence[0]["display_text"] = "fabricated"
    elif tamper == "truncation":
        evidence[0]["truncated_before"] = not evidence[0]["truncated_before"]
    elif tamper == "nested_fields":
        evidence[0]["matches"][0]["unexpected"] = True
    elif tamper == "nested_evidence_type":
        evidence[0]["matches"][0]["evidence_type"] = "url"
    elif tamper == "nested_rule_version":
        evidence[0]["matches"][0]["rule_version"] = "999"
    elif tamper == "nested_offsets":
        evidence[0]["matches"][0]["end"] = len("Text me at 312-555-1212") + 1
    elif tamper == "declared_versions":
        changes["matched_rule_versions"] = (
            *finding.matched_rule_versions,
            {"rule_id": "spam_or_scam.phrase", "rule_version": "1"},
        )
        changes["matched_rule_ids"] = (
            *finding.matched_rule_ids,
            "spam_or_scam.phrase",
        )
    elif tamper == "source_field":
        changes["source_field"] = "title"
    elif tamper == "field_purpose":
        changes["field_purpose"] = "payment_method"
    elif tamper == "priority":
        changes["priority"] = "critical"
    elif tamper == "risk_area":
        changes["risk_area"] = "unsafe_payment_text"
    elif tamper == "target_context":
        scan = replace(
            scan,
            provenance=replace(
                scan.provenance, target_context=TARGET_CONTEXT_GAME_CHAT
            ),
        )

    if tamper not in {"target_context"}:
        changes.setdefault("evidence", evidence)
        scan = _replace_first_finding(scan, **changes)
    with pytest.raises(ModerationEvidenceError):
        validate_content_moderation_scan_result(scan)


@pytest.mark.requirement("WS03-05A-R2", "WS03-05A-R3", "WS03-05A-R4")
@pytest.mark.parametrize(
    "tamper",
    (
        "duplicate_item",
        "duplicate_nested_match",
        "reordered_items",
        "noncanonical_item_owner",
        "fabricated_additional_count",
        "reordered_rule_attribution",
    ),
)
def test_saved_evidence_rejects_noncanonical_identity_and_count_tampering(
    tamper: str,
) -> None:
    phones = " ".join(f"312-555-{1200 + index}" for index in range(8))
    scan = build_content_moderation_findings(
        _community_fields(description=f"Text me {phones} player@example.com"),
        target_context=TARGET_CONTEXT_COMMUNITY_GAME,
    )
    finding = scan.findings[0]
    evidence = deepcopy(finding.evidence)
    changes = {"evidence": evidence}

    if tamper == "duplicate_item":
        evidence[-1] = deepcopy(evidence[0])
    elif tamper == "duplicate_nested_match":
        evidence[0]["matches"].append(deepcopy(evidence[0]["matches"][0]))
    elif tamper == "reordered_items":
        evidence[0], evidence[1] = evidence[1], evidence[0]
    elif tamper == "noncanonical_item_owner":
        evidence[0]["evidence_type"] = "contact_phrase"
    elif tamper == "fabricated_additional_count":
        evidence[-1]["additional_match_count"] = 999
    elif tamper == "reordered_rule_attribution":
        changes["matched_rule_ids"] = tuple(reversed(finding.matched_rule_ids))
        changes["matched_rule_versions"] = tuple(
            reversed(finding.matched_rule_versions)
        )

    with pytest.raises(ModerationEvidenceError):
        validate_content_moderation_scan_result(_replace_first_finding(scan, **changes))


@pytest.mark.requirement("WS03-05A-R2", "WS03-05A-R3")
@pytest.mark.parametrize(
    "field_name",
    ("rule_id", "rule_version", "evidence_type"),
)
@pytest.mark.parametrize("invalid_value", _INVALID_NESTED_IDENTIFIER_VALUES)
def test_saved_evidence_direct_validator_rejects_non_string_nested_identifiers(
    field_name: str,
    invalid_value: object,
) -> None:
    source_text = "Text me at 312-555-1212"
    scan = build_content_moderation_findings(
        _community_fields(description=source_text),
        target_context=TARGET_CONTEXT_COMMUNITY_GAME,
    )
    finding = scan.findings[0]
    evidence = deepcopy(finding.evidence)
    evidence[0]["matches"][0][field_name] = deepcopy(invalid_value)

    with pytest.raises(ModerationEvidenceError):
        validate_saved_span_evidence(
            source_text=source_text,
            source_content_hash=finding.source_content_hash,
            evidence_fingerprint=finding.evidence_fingerprint,
            finding_type=finding.finding_type,
            risk_area=finding.risk_area,
            priority=finding.priority,
            target_context=scan.provenance.target_context,
            source_field=finding.source_field,
            field_purpose=finding.field_purpose,
            evidence=evidence,
            matched_rule_ids=finding.matched_rule_ids,
            matched_rule_versions=finding.matched_rule_versions,
            canonicalization_version=scan.provenance.canonicalization_version,
            maximum_items=SAVED_CONTENT_PROFILE.evidence_limits["items"],
        )


@pytest.mark.requirement("WS03-05A-R3", "WS03-05A-R4")
def test_case_or_whitespace_edit_changes_exact_hash_but_preserves_span_fingerprint() -> (
    None
):
    first = build_content_moderation_findings(
        _community_fields(description="Text me at 312-555-1212"),
        target_context=TARGET_CONTEXT_COMMUNITY_GAME,
    ).findings[0]
    edited = build_content_moderation_findings(
        _community_fields(description="  TEXT   ME AT 312-555-1212  "),
        target_context=TARGET_CONTEXT_COMMUNITY_GAME,
    ).findings[0]

    assert first.source_content_hash != edited.source_content_hash
    assert first.evidence_fingerprint == edited.evidence_fingerprint


@pytest.mark.requirement("WS03-05A-R1", "WS03-05A-R3")
def test_payment_support_and_field_purpose_exclusions_are_preserved() -> None:
    support_only = build_content_moderation_findings(
        _community_fields(description="Use Venmo $pickup"),
        target_context=TARGET_CONTEXT_COMMUNITY_GAME,
    )
    payment_method_field = build_content_moderation_findings(
        _community_fields(payment_methods_snapshot="Venmo 312-555-1212"),
        target_context=TARGET_CONTEXT_COMMUNITY_GAME,
    )
    pressured = build_content_moderation_findings(
        _community_fields(payment_instructions_snapshot="Pay upfront with Venmo"),
        target_context=TARGET_CONTEXT_COMMUNITY_GAME,
    )

    assert support_only.findings == ()
    assert payment_method_field.findings == ()
    assert [finding.finding_type for finding in pressured.findings] == [
        "payment_pressure"
    ]


@pytest.mark.requirement("WS03-05A-R1", "WS03-05A-R3")
@pytest.mark.parametrize(
    ("source", "expected_rule_ids", "expected_match_count"),
    (
        ("Deposit required", {"payment_pressure.phrase"}, 1),
        (
            "Venmo deposit required",
            {"payment_method.phrase", "payment_pressure.phrase"},
            2,
        ),
        (
            f"Venmo {'x' * 120} deposit required",
            {"payment_pressure.phrase"},
            1,
        ),
        (
            "Venmo is accepted. Deposit required",
            {"payment_pressure.phrase"},
            1,
        ),
        (
            "Deposit required. Pay upfront.",
            {"payment_pressure.phrase"},
            2,
        ),
    ),
)
def test_payment_pressure_attribution_uses_only_contextual_contributors(
    source: str,
    expected_rule_ids: set[str],
    expected_match_count: int,
) -> None:
    result = build_content_moderation_findings(
        _community_fields(description=source),
        target_context=TARGET_CONTEXT_COMMUNITY_GAME,
    )

    assert len(result.findings) == 1
    finding = result.findings[0]
    evidence_rule_ids = {
        match["rule_id"] for item in finding.evidence for match in item["matches"]
    }
    version_rule_ids = {item["rule_id"] for item in finding.matched_rule_versions}
    assert finding.finding_type == "payment_pressure"
    assert finding.priority == "attention"
    assert set(finding.matched_rule_ids) == expected_rule_ids
    assert evidence_rule_ids == expected_rule_ids
    assert version_rule_ids == expected_rule_ids
    assert sum(len(item["matches"]) for item in finding.evidence) == (
        expected_match_count
    )


@pytest.mark.requirement("WS03-05A-R1", "WS03-05A-R3")
def test_repeated_message_requires_complete_true_fact_and_has_no_span_fields() -> None:
    absent = detect_chat_message("same", target_context=TARGET_CONTEXT_GAME_CHAT)
    false_fact = ContextPredicateFact(
        predicate_key="same_sender_same_body",
        predicate_version="1",
        outcome=False,
        reference_message_id="prior",
        reference_source_hash=exact_source_hash("same"),
    )
    false_result = detect_chat_message(
        "same",
        target_context=TARGET_CONTEXT_GAME_CHAT,
        predicate_facts=(false_fact,),
    )
    true_result = detect_chat_message(
        "same",
        target_context=TARGET_CONTEXT_GAME_CHAT,
        predicate_facts=(
            repeated_message_fact(
                reference_message_id="prior",
                reference_message_body="same",
            ),
        ),
    )

    assert absent.detections == false_result.detections == ()
    evidence = true_result.detections[0].evidence
    assert evidence["evidence_kind"] == "context_predicate"
    assert not {"start", "end", "matched_text", "matched_source_hash"} & set(evidence)


@pytest.mark.requirement("WS03-05A-R3")
def test_repeated_message_fingerprint_binds_reference_id_and_exact_hash() -> None:
    first = detect_chat_message(
        "same",
        target_context=TARGET_CONTEXT_GAME_CHAT,
        predicate_facts=(
            repeated_message_fact(
                reference_message_id="prior-a",
                reference_message_body="same",
            ),
        ),
    ).detections[0]
    changed_id = detect_chat_message(
        "same",
        target_context=TARGET_CONTEXT_GAME_CHAT,
        predicate_facts=(
            repeated_message_fact(
                reference_message_id="prior-b",
                reference_message_body="same",
            ),
        ),
    ).detections[0]
    changed_hash = detect_chat_message(
        "same",
        target_context=TARGET_CONTEXT_GAME_CHAT,
        predicate_facts=(
            repeated_message_fact(
                reference_message_id="prior-a",
                reference_message_body="SAME",
            ),
        ),
    ).detections[0]

    assert (
        len(
            {
                first.evidence_fingerprint,
                changed_id.evidence_fingerprint,
                changed_hash.evidence_fingerprint,
            }
        )
        == 3
    )


@pytest.mark.requirement("WS03-05A-R3")
def test_repeated_message_rejects_blank_context_reference() -> None:
    with pytest.raises(ValueError, match="reference message ID"):
        repeated_message_fact(
            reference_message_id="   ",
            reference_message_body="same",
        )


@pytest.mark.requirement("WS03-05A-R2")
def test_scan_provenance_normalizes_to_utc_and_rejects_non_utc_tampering() -> None:
    offset_zone = timezone(timedelta(hours=5))
    result = build_content_moderation_findings(
        _community_fields(description="Text me at 312-555-1212"),
        target_context=TARGET_CONTEXT_COMMUNITY_GAME,
        wall_clock=lambda: datetime(2035, 5, 1, 17, 0, tzinfo=offset_zone),
    )
    assert result.provenance.scanned_at == datetime(
        2035, 5, 1, 12, 0, tzinfo=timezone.utc
    )
    tampered = replace(
        result,
        provenance=replace(
            result.provenance,
            scanned_at=result.provenance.scanned_at.astimezone(offset_zone),
        ),
    )
    with pytest.raises(ModerationEvidenceError, match="provenance"):
        validate_content_moderation_scan_result(tampered)


def _persisted_detection(scan, detection):
    return SimpleNamespace(
        **chat_detection_record_values(
            message_id="00000000-0000-0000-0000-000000000001",
            source_text="call 312-555-1212",
            detection=detection,
            provenance=scan.provenance,
        )
    )


@pytest.mark.requirement("WS03-05A-R2", "WS03-05A-R3")
def test_chat_projection_uses_and_validates_persisted_source_provenance() -> None:
    source = "call 312-555-1212"
    scan = detect_chat_message(source, target_context=TARGET_CONTEXT_GAME_CHAT)
    persisted = _persisted_detection(scan, scan.detections[0])
    finding = aggregate_chat_detections(
        message_body=source,
        detections=[persisted],
        expected_target_context=TARGET_CONTEXT_GAME_CHAT,
    )[0]
    assert finding.content_hash == persisted.source_content_hash

    for field_name, value in (
        ("source_content_hash", "0" * 64),
        ("source_field", "body"),
        ("field_purpose", "general"),
        ("target_context", TARGET_CONTEXT_NEED_A_SUB_CHAT),
    ):
        tampered = SimpleNamespace(**vars(persisted))
        setattr(tampered, field_name, value)
        with pytest.raises((ModerationEvidenceError, ValueError)):
            aggregate_chat_detections(
                message_body=source,
                detections=[tampered],
                expected_target_context=TARGET_CONTEXT_GAME_CHAT,
            )


@pytest.mark.requirement("WS03-05A-R3", "WS03-05A-R5")
def test_tampered_or_mixed_chat_evidence_is_rejected() -> None:
    result = detect_chat_message(
        "call 312-555-1212",
        target_context=TARGET_CONTEXT_GAME_CHAT,
    )
    detection = result.detections[0]
    mixed = dict(detection.evidence)
    mixed["predicate_key"] = "fake"

    with pytest.raises(ModerationEvidenceError, match="fields"):
        validate_chat_evidence(
            source_text="call 312-555-1212",
            category=detection.category,
            severity=detection.severity,
            target_context=result.provenance.target_context,
            source_field=detection.source_field,
            field_purpose=detection.field_purpose,
            source_content_hash=detection.source_content_hash,
            evidence_fingerprint=detection.evidence_fingerprint,
            evidence=mixed,
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
            canonicalization_version=result.provenance.canonicalization_version,
        )


@pytest.mark.requirement("WS03-05A-R2", "WS03-05A-R3", "WS03-05A-R5")
@pytest.mark.parametrize(
    "tamper",
    (
        "evidence_type",
        "category",
        "matched_hash",
        "offset",
        "public_rule_key",
        "registry_rule_id",
        "rule_version",
        "severity",
        "source_field",
        "field_purpose",
        "preview",
        "matched_versions",
        "target_context",
        "source_hash",
        "fingerprint",
        "canonicalization",
    ),
)
def test_chat_evidence_rejects_complete_tampering_matrix(tamper: str) -> None:
    source = "call 312-555-1212"
    result = detect_chat_message(source, target_context=TARGET_CONTEXT_GAME_CHAT)
    detection = result.detections[0]
    evidence = dict(detection.evidence)
    kwargs = {
        "source_text": source,
        "category": detection.category,
        "severity": detection.severity,
        "target_context": result.provenance.target_context,
        "source_field": detection.source_field,
        "field_purpose": detection.field_purpose,
        "source_content_hash": detection.source_content_hash,
        "evidence_fingerprint": detection.evidence_fingerprint,
        "evidence": evidence,
        "public_rule_key": detection.rule_key,
        "registry_rule_id": detection.registry_rule_id,
        "rule_version": detection.rule_version,
        "matched_rule_versions": (
            {
                "rule_id": detection.registry_rule_id,
                "rule_version": detection.rule_version,
            },
        ),
        "matched_preview": detection.matched_preview,
        "canonicalization_version": result.provenance.canonicalization_version,
    }
    if tamper == "evidence_type":
        evidence["evidence_type"] = "url"
    elif tamper == "category":
        kwargs["category"] = "email"
    elif tamper == "matched_hash":
        evidence["matched_source_hash"] = "0" * 64
    elif tamper == "offset":
        evidence["end"] = len(source) + 1
    elif tamper == "public_rule_key":
        kwargs["public_rule_key"] = "email.pattern"
    elif tamper == "registry_rule_id":
        kwargs["registry_rule_id"] = "email.pattern"
    elif tamper == "rule_version":
        kwargs["rule_version"] = "999"
    elif tamper == "severity":
        kwargs["severity"] = "high"
    elif tamper == "source_field":
        kwargs["source_field"] = "body"
    elif tamper == "field_purpose":
        kwargs["field_purpose"] = "general"
    elif tamper == "preview":
        kwargs["matched_preview"] = source
    elif tamper == "matched_versions":
        kwargs["matched_rule_versions"] = (
            *kwargs["matched_rule_versions"],
            {"rule_id": "email.pattern", "rule_version": "1"},
        )
    elif tamper == "target_context":
        kwargs["target_context"] = TARGET_CONTEXT_COMMUNITY_GAME
    elif tamper == "source_hash":
        kwargs["source_content_hash"] = "0" * 64
    elif tamper == "fingerprint":
        kwargs["evidence_fingerprint"] = "0" * 64
    elif tamper == "canonicalization":
        kwargs["canonicalization_version"] = "not-canonical"

    with pytest.raises(ModerationEvidenceError):
        validate_chat_evidence(**kwargs)


@pytest.mark.requirement("WS03-05A-R1", "WS03-05A-R3", "WS03-05A-R5")
@pytest.mark.parametrize(
    "tamper",
    (
        "missing_reference",
        "false_outcome",
        "predicate_key",
        "predicate_version",
        "reference_hash",
        "span_field",
    ),
)
def test_context_predicate_evidence_rejects_incomplete_or_mixed_shapes(
    tamper: str,
) -> None:
    source = "same"
    result = detect_chat_message(
        source,
        target_context=TARGET_CONTEXT_GAME_CHAT,
        predicate_facts=(
            repeated_message_fact(
                reference_message_id="prior",
                reference_message_body=source,
            ),
        ),
    )
    detection = result.detections[0]
    evidence = dict(detection.evidence)
    if tamper == "missing_reference":
        evidence.pop("reference_message_id")
    elif tamper == "false_outcome":
        evidence["outcome"] = False
    elif tamper == "predicate_key":
        evidence["predicate_key"] = "not_the_predicate"
    elif tamper == "predicate_version":
        evidence["predicate_version"] = "999"
    elif tamper == "reference_hash":
        evidence["reference_source_hash"] = "0" * 64
    elif tamper == "span_field":
        evidence["start"] = 0

    with pytest.raises(ModerationEvidenceError):
        validate_chat_evidence(
            source_text=source,
            category=detection.category,
            severity=detection.severity,
            target_context=result.provenance.target_context,
            source_field=detection.source_field,
            field_purpose=detection.field_purpose,
            source_content_hash=detection.source_content_hash,
            evidence_fingerprint=detection.evidence_fingerprint,
            evidence=evidence,
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
            canonicalization_version=result.provenance.canonicalization_version,
        )


def _context_detection_with_invalid_reference(field_name: str, value: object):
    source = "same"
    result = detect_chat_message(
        source,
        target_context=TARGET_CONTEXT_GAME_CHAT,
        predicate_facts=(
            repeated_message_fact(
                reference_message_id="prior",
                reference_message_body=source,
            ),
        ),
    )
    detection = result.detections[0]
    evidence = dict(detection.evidence)
    evidence[field_name] = value
    fingerprint = context_predicate_fingerprint(
        category=detection.category,
        source_field=detection.source_field,
        source_content_hash=detection.source_content_hash,
        predicate_key=evidence["predicate_key"],
        predicate_version=evidence["predicate_version"],
        reference_message_id=str(evidence["reference_message_id"]),
        reference_source_hash=str(evidence["reference_source_hash"]),
    )
    return (
        source,
        result,
        replace(
            detection,
            evidence=evidence,
            evidence_fingerprint=fingerprint,
        ),
    )


@pytest.mark.requirement("WS03-05A-R3", "WS03-05A-R5")
@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    (
        ("reference_message_id", 123),
        ("reference_message_id", "   "),
        ("reference_source_hash", int("1" * 64)),
        ("reference_source_hash", "A" * 64),
    ),
)
def test_chat_record_builder_rejects_noncanonical_context_reference_fields(
    field_name: str,
    invalid_value: object,
) -> None:
    source, result, detection = _context_detection_with_invalid_reference(
        field_name,
        invalid_value,
    )

    with pytest.raises(ModerationEvidenceError):
        chat_detection_record_values(
            message_id="message",
            source_text=source,
            detection=detection,
            provenance=result.provenance,
        )


@pytest.mark.requirement("WS03-05A-R3", "WS03-05A-R5")
@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    (
        ("reference_message_id", 123),
        ("reference_message_id", "   "),
        ("reference_source_hash", int("1" * 64)),
        ("reference_source_hash", "A" * 64),
    ),
)
def test_chat_projection_rejects_noncanonical_persisted_context_reference_fields(
    field_name: str,
    invalid_value: object,
) -> None:
    source, result, tampered_detection = _context_detection_with_invalid_reference(
        field_name,
        invalid_value,
    )
    valid_detection = result.detections[0]
    persisted_values = chat_detection_record_values(
        message_id="00000000-0000-0000-0000-000000000001",
        source_text=source,
        detection=valid_detection,
        provenance=result.provenance,
    )
    persisted_values["evidence"] = tampered_detection.evidence
    persisted_values["evidence_fingerprint"] = tampered_detection.evidence_fingerprint

    with pytest.raises(ModerationEvidenceError):
        aggregate_chat_detections(
            message_body=source,
            detections=[SimpleNamespace(**persisted_values)],
            expected_target_context=TARGET_CONTEXT_GAME_CHAT,
        )


@pytest.mark.requirement("WS03-05A-R2", "WS03-05A-R3", "WS03-05A-R5")
def test_chat_record_builder_rejects_tampered_safe_preview() -> None:
    source = "call 312-555-1212"
    result = detect_chat_message(source, target_context=TARGET_CONTEXT_GAME_CHAT)
    tampered = replace(result.detections[0], matched_preview=source)
    with pytest.raises(ModerationEvidenceError, match="preview"):
        chat_detection_record_values(
            message_id="message",
            source_text=source,
            detection=tampered,
            provenance=result.provenance,
        )
