"""Canonical deterministic moderation taxonomy and scanner profiles."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

EXECUTION_KIND_REGEX = "regex_search"
EXECUTION_KIND_CONTEXT_PREDICATE = "context_predicate"
EVIDENCE_KIND_SPAN = "span"
EVIDENCE_KIND_CONTEXT_PREDICATE = "context_predicate"

TARGET_CONTEXT_COMMUNITY_GAME = "community_game"
TARGET_CONTEXT_NEED_A_SUB = "need_a_sub"
TARGET_CONTEXT_GAME_CHAT = "game_chat"
TARGET_CONTEXT_NEED_A_SUB_CHAT = "need_a_sub_chat"

FIELD_PURPOSE_GENERAL = "general"
FIELD_PURPOSE_PAYMENT = "payment"
FIELD_PURPOSE_PAYMENT_METHOD = "payment_method"
FIELD_PURPOSE_LOCATION = "location"
FIELD_PURPOSE_ADDRESS = "address"
FIELD_PURPOSE_CHAT = "chat"

RISK_AREA_UNSAFE_PAYMENT = "unsafe_payment_text"
RISK_AREA_UNSAFE_POST = "unsafe_post_text"

FINDING_TYPE_OFF_APP_CONTACT = "off_app_contact"
FINDING_TYPE_PAYMENT_PRESSURE = "payment_pressure"
FINDING_TYPE_SPAM_OR_SCAM = "spam_or_scam"
FINDING_TYPE_THREAT_OR_VIOLENCE = "threat_or_violence"
FINDING_TYPE_HARASSMENT_OR_ABUSE = "harassment_or_abuse"
FINDING_TYPE_SLUR_OR_HATE = "slur_or_hate"
FINDING_TYPE_SEXUAL_OR_EXPLICIT = "sexual_or_explicit"

EVIDENCE_TYPE_CONTACT_PHRASE = "contact_phrase"
EVIDENCE_TYPE_EMAIL = "email"
EVIDENCE_TYPE_PAYMENT_HANDLE = "payment_handle"
EVIDENCE_TYPE_PAYMENT_METHOD = "payment_method"
EVIDENCE_TYPE_PAYMENT_PRESSURE_PHRASE = "payment_pressure_phrase"
EVIDENCE_TYPE_PHONE = "phone"
EVIDENCE_TYPE_PHRASE = "phrase"
EVIDENCE_TYPE_SOCIAL_HANDLE = "social_handle"
EVIDENCE_TYPE_URL = "url"
EVIDENCE_TYPE_CONTEXT_PREDICATE = "context_predicate"

SAVED_CONTENT_PROFILE_ID = "saved_content"
CHAT_PROFILE_ID = "chat_message"
SCANNER_ID = "pickup-lane-deterministic-moderation"
SCANNER_VERSION = "3"
TAXONOMY_VERSION = "1"
CANONICALIZATION_VERSION = "span-trim-collapse-casefold-v1"
EVIDENCE_FORMAT_VERSION = "1"

REPEATED_MESSAGE_RULE_ID = "spam_or_repeated_message.same_sender_same_body"
REPEATED_MESSAGE_RULE_VERSION = "1"
REPEATED_MESSAGE_PREDICATE_KEY = "same_sender_same_body"
REPEATED_MESSAGE_PREDICATE_VERSION = "1"

LANGUAGE_STRUCTURED = "language_independent_structured"
LANGUAGE_ENGLISH = "english_phrase_v1"

EXECUTION_KINDS: Final[frozenset[str]] = frozenset(
    {EXECUTION_KIND_REGEX, EXECUTION_KIND_CONTEXT_PREDICATE}
)
EVIDENCE_KINDS: Final[frozenset[str]] = frozenset(
    {EVIDENCE_KIND_SPAN, EVIDENCE_KIND_CONTEXT_PREDICATE}
)
TARGET_CONTEXTS: Final[frozenset[str]] = frozenset(
    {
        TARGET_CONTEXT_COMMUNITY_GAME,
        TARGET_CONTEXT_NEED_A_SUB,
        TARGET_CONTEXT_GAME_CHAT,
        TARGET_CONTEXT_NEED_A_SUB_CHAT,
    }
)
FIELD_PURPOSES: Final[frozenset[str]] = frozenset(
    {
        FIELD_PURPOSE_GENERAL,
        FIELD_PURPOSE_PAYMENT,
        FIELD_PURPOSE_PAYMENT_METHOD,
        FIELD_PURPOSE_LOCATION,
        FIELD_PURPOSE_ADDRESS,
        FIELD_PURPOSE_CHAT,
    }
)
RISK_AREAS: Final[frozenset[str]] = frozenset(
    {RISK_AREA_UNSAFE_PAYMENT, RISK_AREA_UNSAFE_POST}
)
SAVED_FINDING_TYPES: Final[frozenset[str]] = frozenset(
    {
        FINDING_TYPE_OFF_APP_CONTACT,
        FINDING_TYPE_PAYMENT_PRESSURE,
        FINDING_TYPE_SPAM_OR_SCAM,
        FINDING_TYPE_THREAT_OR_VIOLENCE,
        FINDING_TYPE_HARASSMENT_OR_ABUSE,
        FINDING_TYPE_SLUR_OR_HATE,
        FINDING_TYPE_SEXUAL_OR_EXPLICIT,
    }
)
CHAT_DETECTION_OUTCOMES: Final[frozenset[str]] = frozenset(
    {
        "phone_number",
        "email",
        "link",
        "off_platform_contact",
        "payment_discussion",
        "harassment_or_abuse",
        "threat_or_safety",
        "slur_or_hate",
        "spam_or_repeated_message",
    }
)
SAVED_PRIORITIES: Final[frozenset[str]] = frozenset({"attention", "urgent", "critical"})
CHAT_SEVERITIES: Final[frozenset[str]] = frozenset({"low", "medium", "high"})
EVIDENCE_TYPES: Final[frozenset[str]] = frozenset(
    {
        EVIDENCE_TYPE_CONTACT_PHRASE,
        EVIDENCE_TYPE_EMAIL,
        EVIDENCE_TYPE_PAYMENT_HANDLE,
        EVIDENCE_TYPE_PAYMENT_METHOD,
        EVIDENCE_TYPE_PAYMENT_PRESSURE_PHRASE,
        EVIDENCE_TYPE_PHONE,
        EVIDENCE_TYPE_PHRASE,
        EVIDENCE_TYPE_SOCIAL_HANDLE,
        EVIDENCE_TYPE_URL,
        EVIDENCE_TYPE_CONTEXT_PREDICATE,
    }
)
LANGUAGE_SCOPES: Final[frozenset[str]] = frozenset(
    {LANGUAGE_STRUCTURED, LANGUAGE_ENGLISH}
)

SAVED_CONTEXTS = (TARGET_CONTEXT_COMMUNITY_GAME, TARGET_CONTEXT_NEED_A_SUB)
CHAT_CONTEXTS = (TARGET_CONTEXT_GAME_CHAT, TARGET_CONTEXT_NEED_A_SUB_CHAT)
ALL_SAVED_PURPOSES = (
    FIELD_PURPOSE_GENERAL,
    FIELD_PURPOSE_PAYMENT,
    FIELD_PURPOSE_PAYMENT_METHOD,
    FIELD_PURPOSE_LOCATION,
    FIELD_PURPOSE_ADDRESS,
)

PHONE_EXPRESSION = (
    r"(?<!\d)(?:\+?1[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}(?!\d)"
)
EMAIL_EXPRESSION = r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"
SAVED_LINK_EXPRESSION = (
    r"\b(?:https?://[^\s<>()]+|www\.[^\s<>()]+|"
    r"[a-z0-9][a-z0-9.-]*\.(?:com|net|org|io|co|app)(?:/[^\s<>()]*)?)"
)
CHAT_LINK_EXPRESSION = (
    r"\b(?:https?://|www\.)\S+|\b[a-z0-9.-]+\.(?:com|net|org|io|co|app)\b"
)


class ModerationTaxonomyError(ValueError):
    """Raised when a scanner profile or rule definition is inconsistent."""


@dataclass(frozen=True)
class ModerationRuleDefinition:
    rule_id: str
    rule_version: str
    profile_id: str
    outcome: str
    priority_or_severity: str
    evidence_type: str
    execution_kind: str
    target_contexts: tuple[str, ...]
    allowed_field_purposes: tuple[str, ...]
    language_scope: str
    external_rule_key: str | None = None
    risk_area: str | None = None
    supporting_only: bool = False
    expression_source: str | None = None
    expression_flags: int = 0
    predicate_key: str | None = None
    predicate_version: str | None = None
    predicate_input_contract: str | None = None
    predicate_comparison_contract: str | None = None

    @property
    def persisted_rule_key(self) -> str:
        return self.external_rule_key or self.rule_id

    def compile_expression(self) -> re.Pattern[str]:
        if self.execution_kind != EXECUTION_KIND_REGEX or not self.expression_source:
            raise ModerationTaxonomyError(
                f"Rule {self.rule_id} does not define a regex expression."
            )
        return re.compile(self.expression_source, self.expression_flags)

    def behavior_payload(self) -> dict[str, object]:
        return {
            "allowed_field_purposes": list(self.allowed_field_purposes),
            "evidence_type": self.evidence_type,
            "external_rule_key": self.external_rule_key,
            "execution_kind": self.execution_kind,
            "expression_flags": self.expression_flags,
            "expression_source": self.expression_source,
            "language_scope": self.language_scope,
            "outcome": self.outcome,
            "predicate_comparison_contract": self.predicate_comparison_contract,
            "predicate_input_contract": self.predicate_input_contract,
            "predicate_key": self.predicate_key,
            "predicate_version": self.predicate_version,
            "priority_or_severity": self.priority_or_severity,
            "profile_id": self.profile_id,
            "risk_area": self.risk_area,
            "rule_id": self.rule_id,
            "rule_version": self.rule_version,
            "supporting_only": self.supporting_only,
            "target_contexts": list(self.target_contexts),
        }


@dataclass(frozen=True)
class ScannerProfileDefinition:
    profile_id: str
    scanner_id: str
    scanner_version: str
    taxonomy_version: str
    canonicalization_version: str
    evidence_format_version: str
    enabled_rule_ids: tuple[str, ...]
    context_field_inventory: Mapping[str, tuple[tuple[str, str], ...]]
    evidence_limits: Mapping[str, int]
    declared_limits: tuple[str, ...]


def _rule(
    rule_id: str,
    *,
    profile_id: str,
    outcome: str,
    priority: str,
    evidence_type: str,
    contexts: tuple[str, ...],
    purposes: tuple[str, ...],
    language: str,
    expression: str,
    flags: int = 0,
    risk_area: str | None = None,
    supporting_only: bool = False,
    external_rule_key: str | None = None,
) -> ModerationRuleDefinition:
    return ModerationRuleDefinition(
        rule_id=rule_id,
        rule_version="1",
        profile_id=profile_id,
        outcome=outcome,
        priority_or_severity=priority,
        evidence_type=evidence_type,
        execution_kind=EXECUTION_KIND_REGEX,
        target_contexts=contexts,
        allowed_field_purposes=purposes,
        language_scope=language,
        external_rule_key=external_rule_key,
        risk_area=risk_area,
        supporting_only=supporting_only,
        expression_source=expression,
        expression_flags=flags,
    )


_SAVED_RULES = (
    _rule(
        "personal_info.phone_number",
        profile_id=SAVED_CONTENT_PROFILE_ID,
        outcome=FINDING_TYPE_OFF_APP_CONTACT,
        priority="attention",
        evidence_type=EVIDENCE_TYPE_PHONE,
        contexts=SAVED_CONTEXTS,
        purposes=(FIELD_PURPOSE_GENERAL, FIELD_PURPOSE_LOCATION),
        language=LANGUAGE_STRUCTURED,
        expression=PHONE_EXPRESSION,
        risk_area=RISK_AREA_UNSAFE_POST,
    ),
    _rule(
        "personal_info.email",
        profile_id=SAVED_CONTENT_PROFILE_ID,
        outcome=FINDING_TYPE_OFF_APP_CONTACT,
        priority="attention",
        evidence_type=EVIDENCE_TYPE_EMAIL,
        contexts=SAVED_CONTEXTS,
        purposes=(FIELD_PURPOSE_GENERAL, FIELD_PURPOSE_LOCATION),
        language=LANGUAGE_STRUCTURED,
        expression=EMAIL_EXPRESSION,
        flags=re.IGNORECASE,
        risk_area=RISK_AREA_UNSAFE_POST,
    ),
    _rule(
        "personal_info.link",
        profile_id=SAVED_CONTENT_PROFILE_ID,
        outcome=FINDING_TYPE_OFF_APP_CONTACT,
        priority="attention",
        evidence_type=EVIDENCE_TYPE_URL,
        contexts=SAVED_CONTEXTS,
        purposes=(FIELD_PURPOSE_GENERAL, FIELD_PURPOSE_LOCATION),
        language=LANGUAGE_STRUCTURED,
        expression=SAVED_LINK_EXPRESSION,
        flags=re.IGNORECASE,
        risk_area=RISK_AREA_UNSAFE_POST,
    ),
    _rule(
        "off_app_contact.social_handle",
        profile_id=SAVED_CONTENT_PROFILE_ID,
        outcome=FINDING_TYPE_OFF_APP_CONTACT,
        priority="attention",
        evidence_type=EVIDENCE_TYPE_SOCIAL_HANDLE,
        contexts=SAVED_CONTEXTS,
        purposes=(FIELD_PURPOSE_GENERAL, FIELD_PURPOSE_LOCATION),
        language=LANGUAGE_STRUCTURED,
        expression=r"(?<!\w)@[A-Z][A-Z0-9_.]{1,29}\b",
        flags=re.IGNORECASE,
        risk_area=RISK_AREA_UNSAFE_POST,
    ),
    _rule(
        "off_app_contact.phrase",
        profile_id=SAVED_CONTENT_PROFILE_ID,
        outcome=FINDING_TYPE_OFF_APP_CONTACT,
        priority="attention",
        evidence_type=EVIDENCE_TYPE_CONTACT_PHRASE,
        contexts=SAVED_CONTEXTS,
        purposes=(FIELD_PURPOSE_GENERAL, FIELD_PURPOSE_LOCATION),
        language=LANGUAGE_ENGLISH,
        expression=r"\b(?:text\s+me|txt\s+me|call\s+me|dm\s+me|whatsapp|telegram|signal|instagram|snapchat|phone\s+number|my\s+number)\b",
        flags=re.IGNORECASE,
        risk_area=RISK_AREA_UNSAFE_POST,
    ),
    _rule(
        "payment_method.phrase",
        profile_id=SAVED_CONTENT_PROFILE_ID,
        outcome=FINDING_TYPE_PAYMENT_PRESSURE,
        priority="attention",
        evidence_type=EVIDENCE_TYPE_PAYMENT_METHOD,
        contexts=SAVED_CONTEXTS,
        purposes=(
            FIELD_PURPOSE_GENERAL,
            FIELD_PURPOSE_PAYMENT,
            FIELD_PURPOSE_LOCATION,
            FIELD_PURPOSE_ADDRESS,
        ),
        language=LANGUAGE_ENGLISH,
        expression=r"\b(?:venmo|zelle|cash\s?app|paypal|apple\s+cash|apple\s+pay|chime)\b",
        flags=re.IGNORECASE,
        risk_area=RISK_AREA_UNSAFE_PAYMENT,
        supporting_only=True,
    ),
    _rule(
        "payment_handle.cash_app",
        profile_id=SAVED_CONTENT_PROFILE_ID,
        outcome=FINDING_TYPE_PAYMENT_PRESSURE,
        priority="attention",
        evidence_type=EVIDENCE_TYPE_PAYMENT_HANDLE,
        contexts=SAVED_CONTEXTS,
        purposes=(
            FIELD_PURPOSE_GENERAL,
            FIELD_PURPOSE_PAYMENT,
            FIELD_PURPOSE_LOCATION,
            FIELD_PURPOSE_ADDRESS,
        ),
        language=LANGUAGE_STRUCTURED,
        expression=r"(?<!\w)\$[A-Z][A-Z0-9_]{1,29}\b",
        flags=re.IGNORECASE,
        risk_area=RISK_AREA_UNSAFE_PAYMENT,
        supporting_only=True,
    ),
    _rule(
        "payment_pressure.phrase",
        profile_id=SAVED_CONTENT_PROFILE_ID,
        outcome=FINDING_TYPE_PAYMENT_PRESSURE,
        priority="attention",
        evidence_type=EVIDENCE_TYPE_PAYMENT_PRESSURE_PHRASE,
        contexts=SAVED_CONTEXTS,
        purposes=(
            FIELD_PURPOSE_GENERAL,
            FIELD_PURPOSE_PAYMENT,
            FIELD_PURPOSE_LOCATION,
            FIELD_PURPOSE_ADDRESS,
        ),
        language=LANGUAGE_ENGLISH,
        expression=r"\b(?:deposit\s+required|send\s+(?:a\s+)?deposit|pay\s+first|pay\s+before|send\s+money\s+before|pay\s+upfront|upfront\s+payment|no\s+refunds?|hold\s+your\s+spot|before\s+(?:i\s+)?(?:approve|accept)|before\s+approval|before\s+accepted|payment\s+required\s+before)\b",
        flags=re.IGNORECASE,
        risk_area=RISK_AREA_UNSAFE_PAYMENT,
    ),
    _rule(
        "payment_contact.phrase",
        profile_id=SAVED_CONTENT_PROFILE_ID,
        outcome=FINDING_TYPE_PAYMENT_PRESSURE,
        priority="attention",
        evidence_type=EVIDENCE_TYPE_PAYMENT_PRESSURE_PHRASE,
        contexts=SAVED_CONTEXTS,
        purposes=(
            FIELD_PURPOSE_GENERAL,
            FIELD_PURPOSE_PAYMENT,
            FIELD_PURPOSE_LOCATION,
            FIELD_PURPOSE_ADDRESS,
        ),
        language=LANGUAGE_ENGLISH,
        expression=r"\b(?:dm|text|txt|call|message)\s+me\s+(?:for|to)\s+(?:pay|payment)\b",
        flags=re.IGNORECASE,
        risk_area=RISK_AREA_UNSAFE_PAYMENT,
    ),
    _rule(
        "spam_or_scam.phrase",
        profile_id=SAVED_CONTENT_PROFILE_ID,
        outcome=FINDING_TYPE_SPAM_OR_SCAM,
        priority="attention",
        evidence_type=EVIDENCE_TYPE_PHRASE,
        contexts=SAVED_CONTEXTS,
        purposes=ALL_SAVED_PURPOSES,
        language=LANGUAGE_ENGLISH,
        expression=r"\b(?:crypto|bitcoin|investment|promo\s+code|click\s+(?:this\s+)?link|guaranteed\s+money|limited\s+offer)\b",
        flags=re.IGNORECASE,
        risk_area=RISK_AREA_UNSAFE_POST,
    ),
    _rule(
        "threat_or_violence.phrase",
        profile_id=SAVED_CONTENT_PROFILE_ID,
        outcome=FINDING_TYPE_THREAT_OR_VIOLENCE,
        priority="urgent",
        evidence_type=EVIDENCE_TYPE_PHRASE,
        contexts=SAVED_CONTEXTS,
        purposes=ALL_SAVED_PURPOSES,
        language=LANGUAGE_ENGLISH,
        expression=r"\b(?:i(?:'|’)ll\s+hurt|i\s+will\s+hurt|i(?:'|’)ll\s+kill|i\s+will\s+kill|hurt\s+you|kill\s+you|beat\s+you\s+up|bring\s+a\s+weapon)\b",
        flags=re.IGNORECASE,
        risk_area=RISK_AREA_UNSAFE_POST,
    ),
    _rule(
        "harassment_or_abuse.phrase",
        profile_id=SAVED_CONTENT_PROFILE_ID,
        outcome=FINDING_TYPE_HARASSMENT_OR_ABUSE,
        priority="attention",
        evidence_type=EVIDENCE_TYPE_PHRASE,
        contexts=SAVED_CONTEXTS,
        purposes=ALL_SAVED_PURPOSES,
        language=LANGUAGE_ENGLISH,
        expression=r"\b(?:kill\s+yourself|go\s+die|nobody\s+wants\s+you|you\s+are\s+worthless)\b",
        flags=re.IGNORECASE,
        risk_area=RISK_AREA_UNSAFE_POST,
    ),
    _rule(
        "slur_or_hate.phrase",
        profile_id=SAVED_CONTENT_PROFILE_ID,
        outcome=FINDING_TYPE_SLUR_OR_HATE,
        priority="urgent",
        evidence_type=EVIDENCE_TYPE_PHRASE,
        contexts=SAVED_CONTEXTS,
        purposes=ALL_SAVED_PURPOSES,
        language=LANGUAGE_ENGLISH,
        expression=r"\b(?:go\s+back\s+to\s+your\s+country|racial\s+slur|homophobic\s+slur)\b",
        flags=re.IGNORECASE,
        risk_area=RISK_AREA_UNSAFE_POST,
    ),
    _rule(
        "sexual_or_explicit.phrase",
        profile_id=SAVED_CONTENT_PROFILE_ID,
        outcome=FINDING_TYPE_SEXUAL_OR_EXPLICIT,
        priority="urgent",
        evidence_type=EVIDENCE_TYPE_PHRASE,
        contexts=SAVED_CONTEXTS,
        purposes=ALL_SAVED_PURPOSES,
        language=LANGUAGE_ENGLISH,
        expression=r"\b(?:explicit\s+sexual|sexual\s+favors?|hookups?)\b",
        flags=re.IGNORECASE,
        risk_area=RISK_AREA_UNSAFE_POST,
    ),
)

_CHAT_RULES = (
    _rule(
        "phone_number.pattern",
        profile_id=CHAT_PROFILE_ID,
        outcome="phone_number",
        priority="medium",
        evidence_type=EVIDENCE_TYPE_PHONE,
        contexts=CHAT_CONTEXTS,
        purposes=(FIELD_PURPOSE_CHAT,),
        language=LANGUAGE_STRUCTURED,
        expression=PHONE_EXPRESSION,
    ),
    _rule(
        "email.pattern",
        profile_id=CHAT_PROFILE_ID,
        outcome="email",
        priority="medium",
        evidence_type=EVIDENCE_TYPE_EMAIL,
        contexts=CHAT_CONTEXTS,
        purposes=(FIELD_PURPOSE_CHAT,),
        language=LANGUAGE_STRUCTURED,
        expression=EMAIL_EXPRESSION,
        flags=re.IGNORECASE,
    ),
    _rule(
        "link.pattern",
        profile_id=CHAT_PROFILE_ID,
        outcome="link",
        priority="medium",
        evidence_type=EVIDENCE_TYPE_URL,
        contexts=CHAT_CONTEXTS,
        purposes=(FIELD_PURPOSE_CHAT,),
        language=LANGUAGE_STRUCTURED,
        expression=CHAT_LINK_EXPRESSION,
        flags=re.IGNORECASE,
    ),
    _rule(
        "off_platform_contact.phrase",
        profile_id=CHAT_PROFILE_ID,
        outcome="off_platform_contact",
        priority="medium",
        evidence_type=EVIDENCE_TYPE_CONTACT_PHRASE,
        contexts=CHAT_CONTEXTS,
        purposes=(FIELD_PURPOSE_CHAT,),
        language=LANGUAGE_ENGLISH,
        expression=r"\b(?:text me|txt me|call me|dm me|whatsapp|telegram|signal|instagram|snapchat|phone number|my number)\b",
        flags=re.IGNORECASE,
    ),
    _rule(
        "payment_discussion.phrase",
        profile_id=CHAT_PROFILE_ID,
        outcome="payment_discussion",
        priority="medium",
        evidence_type=EVIDENCE_TYPE_PAYMENT_METHOD,
        contexts=CHAT_CONTEXTS,
        purposes=(FIELD_PURPOSE_CHAT,),
        language=LANGUAGE_ENGLISH,
        expression=r"\b(?:zelle|venmo|cash ?app|paypal|apple cash|deposit|send me money|pay me|payment|pay before|pay upfront)\b",
        flags=re.IGNORECASE,
    ),
    _rule(
        "threat_or_safety.phrase",
        profile_id=CHAT_PROFILE_ID,
        outcome="threat_or_safety",
        priority="high",
        evidence_type=EVIDENCE_TYPE_PHRASE,
        contexts=CHAT_CONTEXTS,
        purposes=(FIELD_PURPOSE_CHAT,),
        language=LANGUAGE_ENGLISH,
        expression=r"\b(?:i(?:'|’)ll hurt|i will hurt|i(?:'|’)ll kill|i will kill|beat you up|hurt you|kill you|threat)\b",
        flags=re.IGNORECASE,
    ),
    _rule(
        "chat.harassment_or_abuse.phrase",
        profile_id=CHAT_PROFILE_ID,
        outcome="harassment_or_abuse",
        priority="high",
        evidence_type=EVIDENCE_TYPE_PHRASE,
        contexts=CHAT_CONTEXTS,
        purposes=(FIELD_PURPOSE_CHAT,),
        language=LANGUAGE_ENGLISH,
        expression=r"\b(?:kill yourself|go die|nobody wants you|you are worthless)\b",
        flags=re.IGNORECASE,
        external_rule_key="harassment_or_abuse.phrase",
    ),
    _rule(
        "chat.slur_or_hate.phrase",
        profile_id=CHAT_PROFILE_ID,
        outcome="slur_or_hate",
        priority="high",
        evidence_type=EVIDENCE_TYPE_PHRASE,
        contexts=CHAT_CONTEXTS,
        purposes=(FIELD_PURPOSE_CHAT,),
        language=LANGUAGE_ENGLISH,
        expression=r"\b(?:go back to your country|racial slur|homophobic slur)\b",
        flags=re.IGNORECASE,
        external_rule_key="slur_or_hate.phrase",
    ),
    ModerationRuleDefinition(
        rule_id=REPEATED_MESSAGE_RULE_ID,
        rule_version=REPEATED_MESSAGE_RULE_VERSION,
        profile_id=CHAT_PROFILE_ID,
        outcome="spam_or_repeated_message",
        priority_or_severity="low",
        evidence_type=EVIDENCE_TYPE_CONTEXT_PREDICATE,
        execution_kind=EXECUTION_KIND_CONTEXT_PREDICATE,
        target_contexts=CHAT_CONTEXTS,
        allowed_field_purposes=(FIELD_PURPOSE_CHAT,),
        language_scope=LANGUAGE_STRUCTURED,
        predicate_key=REPEATED_MESSAGE_PREDICATE_KEY,
        predicate_version=REPEATED_MESSAGE_PREDICATE_VERSION,
        predicate_input_contract="latest visible text message from same sender and chat; exclude candidate when persisted; order created_at desc then id desc",
        predicate_comparison_contract="candidate.strip().casefold() == reference.strip().casefold()",
    ),
)

RULES: Final[tuple[ModerationRuleDefinition, ...]] = (*_SAVED_RULES, *_CHAT_RULES)
RULES_BY_ID: Final[dict[str, ModerationRuleDefinition]] = {
    rule.rule_id: rule for rule in RULES
}

SAVED_CONTENT_PROFILE = ScannerProfileDefinition(
    profile_id=SAVED_CONTENT_PROFILE_ID,
    scanner_id=SCANNER_ID,
    scanner_version=SCANNER_VERSION,
    taxonomy_version=TAXONOMY_VERSION,
    canonicalization_version=CANONICALIZATION_VERSION,
    evidence_format_version=EVIDENCE_FORMAT_VERSION,
    enabled_rule_ids=tuple(rule.rule_id for rule in _SAVED_RULES),
    context_field_inventory={
        TARGET_CONTEXT_COMMUNITY_GAME: (
            ("title", FIELD_PURPOSE_GENERAL),
            ("description", FIELD_PURPOSE_GENERAL),
            ("game_notes", FIELD_PURPOSE_GENERAL),
            ("parking_notes", FIELD_PURPOSE_LOCATION),
            ("custom_rules_text", FIELD_PURPOSE_GENERAL),
            ("payment_instructions_snapshot", FIELD_PURPOSE_PAYMENT),
            ("payment_methods_snapshot", FIELD_PURPOSE_PAYMENT_METHOD),
        ),
        TARGET_CONTEXT_NEED_A_SUB: (
            ("team_name", FIELD_PURPOSE_GENERAL),
            ("location_name", FIELD_PURPOSE_LOCATION),
            ("neighborhood", FIELD_PURPOSE_LOCATION),
            ("payment_note", FIELD_PURPOSE_PAYMENT),
            ("notes", FIELD_PURPOSE_GENERAL),
        ),
    },
    evidence_limits={"entity": 120, "phrase": 200, "items": 8},
    declared_limits=(
        "deterministic regex taxonomy only",
        "structured matches are language independent",
        "phrase rules are English-only",
        "bounded current Community Game and Need a Sub text fields only",
    ),
)

CHAT_PROFILE = ScannerProfileDefinition(
    profile_id=CHAT_PROFILE_ID,
    scanner_id=SCANNER_ID,
    scanner_version=SCANNER_VERSION,
    taxonomy_version=TAXONOMY_VERSION,
    canonicalization_version=CANONICALIZATION_VERSION,
    evidence_format_version=EVIDENCE_FORMAT_VERSION,
    enabled_rule_ids=tuple(rule.rule_id for rule in _CHAT_RULES),
    context_field_inventory={
        TARGET_CONTEXT_GAME_CHAT: (("message_body", FIELD_PURPOSE_CHAT),),
        TARGET_CONTEXT_NEED_A_SUB_CHAT: (("message_body", FIELD_PURPOSE_CHAT),),
    },
    evidence_limits={"preview": 120, "evidence_items": 1},
    declared_limits=(
        "deterministic regex and same-sender repeated-message taxonomy only",
        "structured matches are language independent",
        "phrase rules are English-only",
        "latest visible text reference in the same sender and chat scope only",
    ),
)

PROFILES: Final[tuple[ScannerProfileDefinition, ...]] = (
    SAVED_CONTENT_PROFILE,
    CHAT_PROFILE,
)
PROFILES_BY_ID: Final[dict[str, ScannerProfileDefinition]] = {
    profile.profile_id: profile for profile in PROFILES
}


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def profile_configuration_hash(
    profile: ScannerProfileDefinition,
    *,
    rules_by_id: Mapping[str, ModerationRuleDefinition] = RULES_BY_ID,
) -> str:
    payload = {
        "canonicalization_version": profile.canonicalization_version,
        "context_field_inventory": {
            context: [list(item) for item in inventory]
            for context, inventory in sorted(profile.context_field_inventory.items())
        },
        "declared_limits": list(profile.declared_limits),
        "enabled_rules": [
            rules_by_id[rule_id].behavior_payload()
            for rule_id in profile.enabled_rule_ids
        ],
        "evidence_format_version": profile.evidence_format_version,
        "evidence_limits": dict(sorted(profile.evidence_limits.items())),
        "profile_id": profile.profile_id,
        "scanner_id": profile.scanner_id,
        "scanner_version": profile.scanner_version,
        "taxonomy_version": profile.taxonomy_version,
    }
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def validate_registry(
    *,
    rules: tuple[ModerationRuleDefinition, ...] = RULES,
    profiles: tuple[ScannerProfileDefinition, ...] = PROFILES,
) -> None:
    expected_profile_contracts = {
        SAVED_CONTENT_PROFILE_ID: {
            "contexts": frozenset(SAVED_CONTEXTS),
            "outcomes": SAVED_FINDING_TYPES,
            "priorities": SAVED_PRIORITIES,
            "field_purposes": frozenset(ALL_SAVED_PURPOSES),
            "evidence_limit_keys": frozenset({"entity", "phrase", "items"}),
        },
        CHAT_PROFILE_ID: {
            "contexts": frozenset(CHAT_CONTEXTS),
            "outcomes": CHAT_DETECTION_OUTCOMES,
            "priorities": CHAT_SEVERITIES,
            "field_purposes": frozenset({FIELD_PURPOSE_CHAT}),
            "evidence_limit_keys": frozenset({"preview", "evidence_items"}),
        },
    }

    rule_ids = [rule.rule_id for rule in rules]
    if len(rule_ids) != len(set(rule_ids)):
        raise ModerationTaxonomyError("Moderation rule IDs must be unique.")
    profile_ids = [profile.profile_id for profile in profiles]
    if len(profile_ids) != len(set(profile_ids)):
        raise ModerationTaxonomyError("Moderation profile IDs must be unique.")
    if set(profile_ids) != set(expected_profile_contracts):
        raise ModerationTaxonomyError("Moderation profile set is incomplete.")

    rules_by_id = {rule.rule_id: rule for rule in rules}
    profiles_by_id = {profile.profile_id: profile for profile in profiles}
    persisted_keys_by_profile: dict[str, set[str]] = {
        profile_id: set() for profile_id in profile_ids
    }
    for rule in rules:
        string_values = (
            rule.rule_id,
            rule.rule_version,
            rule.profile_id,
            rule.outcome,
            rule.priority_or_severity,
            rule.evidence_type,
            rule.language_scope,
            rule.persisted_rule_key,
        )
        if not all(isinstance(value, str) and value.strip() for value in string_values):
            raise ModerationTaxonomyError(f"Rule {rule.rule_id!r} is incomplete.")
        if rule.profile_id not in profiles_by_id:
            raise ModerationTaxonomyError(
                f"Rule {rule.rule_id} references an unknown profile."
            )
        contract = expected_profile_contracts[rule.profile_id]
        if rule.outcome not in contract["outcomes"]:
            raise ModerationTaxonomyError(
                f"Rule {rule.rule_id} has an unsupported outcome."
            )
        if rule.priority_or_severity not in contract["priorities"]:
            raise ModerationTaxonomyError(
                f"Rule {rule.rule_id} has an unsupported priority or severity."
            )
        if rule.evidence_type not in EVIDENCE_TYPES:
            raise ModerationTaxonomyError(
                f"Rule {rule.rule_id} has an unsupported evidence type."
            )
        if rule.language_scope not in LANGUAGE_SCOPES:
            raise ModerationTaxonomyError(
                f"Rule {rule.rule_id} has an unsupported language scope."
            )
        if (
            not rule.target_contexts
            or len(rule.target_contexts) != len(set(rule.target_contexts))
            or not set(rule.target_contexts) <= TARGET_CONTEXTS
            or not set(rule.target_contexts) <= contract["contexts"]
        ):
            raise ModerationTaxonomyError(
                f"Rule {rule.rule_id} has invalid target contexts."
            )
        if (
            not rule.allowed_field_purposes
            or len(rule.allowed_field_purposes) != len(set(rule.allowed_field_purposes))
            or not set(rule.allowed_field_purposes) <= contract["field_purposes"]
        ):
            raise ModerationTaxonomyError(
                f"Rule {rule.rule_id} has invalid field purposes."
            )
        if not isinstance(rule.supporting_only, bool):
            raise ModerationTaxonomyError(
                f"Rule {rule.rule_id} has invalid supporting-only semantics."
            )
        if rule.profile_id == SAVED_CONTENT_PROFILE_ID:
            if rule.risk_area not in RISK_AREAS:
                raise ModerationTaxonomyError(
                    f"Rule {rule.rule_id} has an unsupported risk area."
                )
        elif rule.risk_area is not None or rule.supporting_only:
            raise ModerationTaxonomyError(
                f"Chat rule {rule.rule_id} has invalid saved-content semantics."
            )
        persisted_keys = persisted_keys_by_profile[rule.profile_id]
        if rule.persisted_rule_key in persisted_keys:
            raise ModerationTaxonomyError(
                f"Profile {rule.profile_id} has duplicate persisted rule keys."
            )
        persisted_keys.add(rule.persisted_rule_key)

        if rule.execution_kind == EXECUTION_KIND_REGEX:
            if (
                rule.evidence_type == EVIDENCE_TYPE_CONTEXT_PREDICATE
                or not isinstance(rule.expression_source, str)
                or not rule.expression_source
                or not isinstance(rule.expression_flags, int)
                or any(
                    value is not None
                    for value in (
                        rule.predicate_key,
                        rule.predicate_version,
                        rule.predicate_input_contract,
                        rule.predicate_comparison_contract,
                    )
                )
            ):
                raise ModerationTaxonomyError(
                    f"Regex rule {rule.rule_id} has mixed or missing behavior."
                )
            rule.compile_expression()
        elif rule.execution_kind == EXECUTION_KIND_CONTEXT_PREDICATE:
            predicate_values = (
                rule.predicate_key,
                rule.predicate_version,
                rule.predicate_input_contract,
                rule.predicate_comparison_contract,
            )
            if (
                rule.evidence_type != EVIDENCE_TYPE_CONTEXT_PREDICATE
                or rule.expression_source is not None
                or rule.expression_flags != 0
                or not all(
                    isinstance(value, str) and value.strip()
                    for value in predicate_values
                )
            ):
                raise ModerationTaxonomyError(
                    f"Predicate rule {rule.rule_id} has mixed or missing behavior."
                )
        else:
            raise ModerationTaxonomyError(
                f"Rule {rule.rule_id} has unsupported execution kind."
            )

    for profile in profiles:
        contract = expected_profile_contracts[profile.profile_id]
        version_values = (
            profile.scanner_id,
            profile.scanner_version,
            profile.taxonomy_version,
            profile.canonicalization_version,
            profile.evidence_format_version,
        )
        if (
            not all(
                isinstance(value, str) and value.strip() for value in version_values
            )
            or not profile.context_field_inventory
            or not profile.declared_limits
            or not all(
                isinstance(value, str) and value.strip()
                for value in profile.declared_limits
            )
            or len(profile.declared_limits) != len(set(profile.declared_limits))
        ):
            raise ModerationTaxonomyError(
                f"Profile {profile.profile_id} lacks context or limit declarations."
            )
        if set(profile.context_field_inventory) != contract["contexts"]:
            raise ModerationTaxonomyError(
                f"Profile {profile.profile_id} has an invalid context inventory."
            )
        for context, inventory in profile.context_field_inventory.items():
            if (
                context not in TARGET_CONTEXTS
                or not inventory
                or len(inventory) != len(set(inventory))
                or any(
                    not isinstance(field_name, str)
                    or not field_name.strip()
                    or purpose not in FIELD_PURPOSES
                    for field_name, purpose in inventory
                )
            ):
                raise ModerationTaxonomyError(
                    f"Profile {profile.profile_id} has an invalid field inventory."
                )
        if set(profile.evidence_limits) != contract["evidence_limit_keys"] or any(
            type(value) is not int or value <= 0
            for value in profile.evidence_limits.values()
        ):
            raise ModerationTaxonomyError(
                f"Profile {profile.profile_id} has invalid evidence limits."
            )
        if len(profile.enabled_rule_ids) != len(set(profile.enabled_rule_ids)):
            raise ModerationTaxonomyError(
                f"Profile {profile.profile_id} enables a rule more than once."
            )
        owned_rule_ids = {
            rule.rule_id for rule in rules if rule.profile_id == profile.profile_id
        }
        if set(profile.enabled_rule_ids) != owned_rule_ids:
            raise ModerationTaxonomyError(
                f"Profile {profile.profile_id} enabled-rule set is incomplete."
            )
        for rule_id in profile.enabled_rule_ids:
            rule = rules_by_id.get(rule_id)
            if rule is None or rule.profile_id != profile.profile_id:
                raise ModerationTaxonomyError(
                    f"Profile {profile.profile_id} references invalid rule {rule_id}."
                )
            if not set(rule.target_contexts) <= set(profile.context_field_inventory):
                raise ModerationTaxonomyError(
                    f"Rule {rule_id} references an unknown target context."
                )
            if any(
                not set(rule.allowed_field_purposes)
                & {
                    purpose
                    for _field_name, purpose in profile.context_field_inventory[context]
                }
                for context in rule.target_contexts
            ):
                raise ModerationTaxonomyError(
                    f"Rule {rule_id} has no applicable field in a target context."
                )
        if {
            rules_by_id[rule_id].outcome for rule_id in profile.enabled_rule_ids
        } != contract["outcomes"]:
            raise ModerationTaxonomyError(
                f"Profile {profile.profile_id} has incomplete finite outcomes."
            )
        profile_configuration_hash(profile, rules_by_id=rules_by_id)


def profile_for_context(target_context: str) -> ScannerProfileDefinition:
    matches = [
        profile
        for profile in PROFILES
        if target_context in profile.context_field_inventory
    ]
    if len(matches) != 1:
        raise ModerationTaxonomyError(
            f"Target context {target_context!r} has no unique scanner profile."
        )
    return matches[0]


def rules_for_context(target_context: str) -> tuple[ModerationRuleDefinition, ...]:
    profile = profile_for_context(target_context)
    return tuple(
        RULES_BY_ID[rule_id]
        for rule_id in profile.enabled_rule_ids
        if target_context in RULES_BY_ID[rule_id].target_contexts
    )


validate_registry()
