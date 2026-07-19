"""Deterministic moderation scanning for user-entered game and post text."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone

SCANNER_VERSION = "pickup-lane-moderation-v2"
EXCERPT_MAX_LENGTH = 220

FIELD_PURPOSE_GENERAL = "general"
FIELD_PURPOSE_PAYMENT = "payment"
FIELD_PURPOSE_PAYMENT_METHOD = "payment_method"
FIELD_PURPOSE_LOCATION = "location"
FIELD_PURPOSE_ADDRESS = "address"
FIELD_PURPOSE_CHAT = "chat"

RISK_AREA_UNSAFE_PAYMENT = "unsafe_payment_text"
RISK_AREA_UNSAFE_POST = "unsafe_post_text"

SIGNAL_CATEGORY_UNSAFE_PAYMENT = RISK_AREA_UNSAFE_PAYMENT
SIGNAL_CATEGORY_UNSAFE_POST = RISK_AREA_UNSAFE_POST

MODERATION_DOMAIN_CHAT = "chat_risk"

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

PHONE_PATTERN = re.compile(
    r"(?<!\d)(?:\+?1[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}(?!\d)"
)
EMAIL_PATTERN = re.compile(
    r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
    re.IGNORECASE,
)
LINK_PATTERN = re.compile(
    r"\b(?:https?://[^\s<>()]+|www\.[^\s<>()]+|"
    r"[a-z0-9][a-z0-9.-]*\.(?:com|net|org|io|co|app)(?:/[^\s<>()]*)?)",
    re.IGNORECASE,
)
SOCIAL_HANDLE_PATTERN = re.compile(r"(?<!\w)@[A-Z][A-Z0-9_.]{1,29}\b", re.IGNORECASE)
OFF_APP_CONTACT_PATTERN = re.compile(
    r"\b(?:text\s+me|txt\s+me|call\s+me|dm\s+me|whatsapp|telegram|signal|"
    r"instagram|snapchat|phone\s+number|my\s+number)\b",
    re.IGNORECASE,
)
PAYMENT_METHOD_PATTERN = re.compile(
    r"\b(?:venmo|zelle|cash\s?app|paypal|apple\s+cash|apple\s+pay|chime)\b",
    re.IGNORECASE,
)
PAYMENT_HANDLE_PATTERN = re.compile(r"(?<!\w)\$[A-Z][A-Z0-9_]{1,29}\b", re.IGNORECASE)
PAYMENT_PRESSURE_PATTERN = re.compile(
    r"\b(?:deposit\s+required|send\s+(?:a\s+)?deposit|pay\s+first|pay\s+before|"
    r"send\s+money\s+before|pay\s+upfront|upfront\s+payment|no\s+refunds?|"
    r"hold\s+your\s+spot|before\s+(?:i\s+)?(?:approve|accept)|before\s+approval|"
    r"before\s+accepted|payment\s+required\s+before)\b",
    re.IGNORECASE,
)
PAYMENT_CONTACT_PATTERN = re.compile(
    r"\b(?:dm|text|txt|call|message)\s+me\s+(?:for|to)\s+(?:pay|payment)\b",
    re.IGNORECASE,
)
SCAM_SPAM_PATTERN = re.compile(
    r"\b(?:crypto|bitcoin|investment|promo\s+code|click\s+(?:this\s+)?link|"
    r"guaranteed\s+money|limited\s+offer)\b",
    re.IGNORECASE,
)
THREAT_PATTERN = re.compile(
    r"\b(?:i(?:'|’)ll\s+hurt|i\s+will\s+hurt|i(?:'|’)ll\s+kill|i\s+will\s+kill|"
    r"hurt\s+you|kill\s+you|beat\s+you\s+up|bring\s+a\s+weapon)\b",
    re.IGNORECASE,
)
HARASSMENT_PATTERN = re.compile(
    r"\b(?:kill\s+yourself|go\s+die|nobody\s+wants\s+you|you\s+are\s+worthless)\b",
    re.IGNORECASE,
)
HATE_PATTERN = re.compile(
    r"\b(?:go\s+back\s+to\s+your\s+country|racial\s+slur|homophobic\s+slur)\b",
    re.IGNORECASE,
)
SEXUAL_PATTERN = re.compile(
    r"\b(?:explicit\s+sexual|sexual\s+favors?|hookups?)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ModerationTextField:
    field_name: str
    field_label: str
    value: str | None
    purpose: str = FIELD_PURPOSE_GENERAL


@dataclass(frozen=True)
class ContentModerationRule:
    rule_id: str
    risk_area: str
    finding_type: str
    evidence_type: str
    priority: str
    pattern: re.Pattern[str]
    supporting_only: bool = False


@dataclass(frozen=True)
class ContentModerationRuleMatch:
    rule_id: str
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
    scanner_version: str = SCANNER_VERSION


CONTENT_MODERATION_RULES: tuple[ContentModerationRule, ...] = (
    ContentModerationRule(
        "personal_info.phone_number",
        RISK_AREA_UNSAFE_POST,
        FINDING_TYPE_OFF_APP_CONTACT,
        EVIDENCE_TYPE_PHONE,
        "attention",
        PHONE_PATTERN,
    ),
    ContentModerationRule(
        "personal_info.email",
        RISK_AREA_UNSAFE_POST,
        FINDING_TYPE_OFF_APP_CONTACT,
        EVIDENCE_TYPE_EMAIL,
        "attention",
        EMAIL_PATTERN,
    ),
    ContentModerationRule(
        "personal_info.link",
        RISK_AREA_UNSAFE_POST,
        FINDING_TYPE_OFF_APP_CONTACT,
        EVIDENCE_TYPE_URL,
        "attention",
        LINK_PATTERN,
    ),
    ContentModerationRule(
        "off_app_contact.social_handle",
        RISK_AREA_UNSAFE_POST,
        FINDING_TYPE_OFF_APP_CONTACT,
        EVIDENCE_TYPE_SOCIAL_HANDLE,
        "attention",
        SOCIAL_HANDLE_PATTERN,
    ),
    ContentModerationRule(
        "off_app_contact.phrase",
        RISK_AREA_UNSAFE_POST,
        FINDING_TYPE_OFF_APP_CONTACT,
        EVIDENCE_TYPE_CONTACT_PHRASE,
        "attention",
        OFF_APP_CONTACT_PATTERN,
    ),
    ContentModerationRule(
        "payment_method.phrase",
        RISK_AREA_UNSAFE_PAYMENT,
        FINDING_TYPE_PAYMENT_PRESSURE,
        EVIDENCE_TYPE_PAYMENT_METHOD,
        "attention",
        PAYMENT_METHOD_PATTERN,
        supporting_only=True,
    ),
    ContentModerationRule(
        "payment_handle.cash_app",
        RISK_AREA_UNSAFE_PAYMENT,
        FINDING_TYPE_PAYMENT_PRESSURE,
        EVIDENCE_TYPE_PAYMENT_HANDLE,
        "attention",
        PAYMENT_HANDLE_PATTERN,
        supporting_only=True,
    ),
    ContentModerationRule(
        "payment_pressure.phrase",
        RISK_AREA_UNSAFE_PAYMENT,
        FINDING_TYPE_PAYMENT_PRESSURE,
        EVIDENCE_TYPE_PAYMENT_PRESSURE_PHRASE,
        "attention",
        PAYMENT_PRESSURE_PATTERN,
    ),
    ContentModerationRule(
        "payment_contact.phrase",
        RISK_AREA_UNSAFE_PAYMENT,
        FINDING_TYPE_PAYMENT_PRESSURE,
        EVIDENCE_TYPE_PAYMENT_PRESSURE_PHRASE,
        "attention",
        PAYMENT_CONTACT_PATTERN,
    ),
    ContentModerationRule(
        "spam_or_scam.phrase",
        RISK_AREA_UNSAFE_POST,
        FINDING_TYPE_SPAM_OR_SCAM,
        EVIDENCE_TYPE_PHRASE,
        "attention",
        SCAM_SPAM_PATTERN,
    ),
    ContentModerationRule(
        "threat_or_violence.phrase",
        RISK_AREA_UNSAFE_POST,
        FINDING_TYPE_THREAT_OR_VIOLENCE,
        EVIDENCE_TYPE_PHRASE,
        "urgent",
        THREAT_PATTERN,
    ),
    ContentModerationRule(
        "harassment_or_abuse.phrase",
        RISK_AREA_UNSAFE_POST,
        FINDING_TYPE_HARASSMENT_OR_ABUSE,
        EVIDENCE_TYPE_PHRASE,
        "attention",
        HARASSMENT_PATTERN,
    ),
    ContentModerationRule(
        "slur_or_hate.phrase",
        RISK_AREA_UNSAFE_POST,
        FINDING_TYPE_SLUR_OR_HATE,
        EVIDENCE_TYPE_PHRASE,
        "urgent",
        HATE_PATTERN,
    ),
    ContentModerationRule(
        "sexual_or_explicit.phrase",
        RISK_AREA_UNSAFE_POST,
        FINDING_TYPE_SEXUAL_OR_EXPLICIT,
        EVIDENCE_TYPE_PHRASE,
        "urgent",
        SEXUAL_PATTERN,
    ),
)

STANDALONE_FINDING_TYPES = {
    FINDING_TYPE_OFF_APP_CONTACT,
    FINDING_TYPE_SPAM_OR_SCAM,
    FINDING_TYPE_THREAT_OR_VIOLENCE,
    FINDING_TYPE_HARASSMENT_OR_ABUSE,
    FINDING_TYPE_SLUR_OR_HATE,
    FINDING_TYPE_SEXUAL_OR_EXPLICIT,
}


def normalize_scan_text(value: str | None) -> str:
    return " ".join(str(value or "").strip().split())


def content_hash(value: str | None) -> str:
    normalized = normalize_scan_text(value).casefold()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def build_review_excerpt(
    value: str,
    *,
    match: re.Match[str] | None = None,
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
    match: re.Match[str],
    *,
    trim_chars: str = ".,;:!?)]}",
) -> tuple[int, int, str]:
    start = match.start()
    end = match.end()
    text = match.group(0)
    trimmed = text.rstrip(trim_chars)
    end -= len(text) - len(trimmed)
    return start, end, trimmed


def scan_text_field_matches(field: ModerationTextField) -> list[ContentModerationRuleMatch]:
    original_text = str(field.value or "")
    if not normalize_scan_text(original_text):
        return []

    matches: list[ContentModerationRuleMatch] = []
    for rule in CONTENT_MODERATION_RULES:
        for regex_match in rule.pattern.finditer(original_text):
            start, end, matched_text = trimmed_match_span(regex_match)
            if not matched_text:
                continue
            matches.append(
                ContentModerationRuleMatch(
                    rule_id=rule.rule_id,
                    risk_area=rule.risk_area,
                    finding_type=rule.finding_type,
                    evidence_type=rule.evidence_type,
                    priority=rule.priority,
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
) -> list[ContentModerationRuleMatch]:
    matches: list[ContentModerationRuleMatch] = []
    for field in fields:
        matches.extend(scan_text_field_matches(field))
    return matches


def scanner_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()
