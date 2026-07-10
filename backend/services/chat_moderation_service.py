"""Shared chat moderation detection and preview helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass


CHAT_DETECTION_CATEGORIES = {
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


@dataclass(frozen=True)
class ChatDetection:
    category: str
    severity: str
    rule_key: str
    matched_preview: str | None = None


PHONE_PATTERN = re.compile(
    r"(?<!\d)(?:\+?1[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}(?!\d)"
)
EMAIL_PATTERN = re.compile(
    r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
    re.IGNORECASE,
)
LINK_PATTERN = re.compile(
    r"\b(?:https?://|www\.)\S+|\b[a-z0-9.-]+\.(?:com|net|org|io|co|app)\b",
    re.IGNORECASE,
)
OFF_PLATFORM_PATTERN = re.compile(
    r"\b(?:text me|txt me|call me|dm me|message me|whatsapp|telegram|signal|"
    r"instagram|snapchat|phone number|my number)\b",
    re.IGNORECASE,
)
PAYMENT_PATTERN = re.compile(
    r"\b(?:zelle|venmo|cash ?app|paypal|apple cash|deposit|send me money|"
    r"pay me|payment|pay before|pay upfront)\b",
    re.IGNORECASE,
)
THREAT_PATTERN = re.compile(
    r"\b(?:i(?:'|’)ll hurt|i will hurt|i(?:'|’)ll kill|i will kill|"
    r"beat you up|hurt you|kill you|threat)\b",
    re.IGNORECASE,
)
HARASSMENT_PATTERN = re.compile(
    r"\b(?:kill yourself|go die|nobody wants you|you are worthless)\b",
    re.IGNORECASE,
)
HATE_PATTERN = re.compile(
    r"\b(?:go back to your country|racial slur|homophobic slur)\b",
    re.IGNORECASE,
)


def build_safe_message_preview(message_body: str, *, limit: int = 160) -> str:
    preview = " ".join(message_body.strip().split())
    preview = PHONE_PATTERN.sub("[phone]", preview)
    preview = EMAIL_PATTERN.sub("[email]", preview)
    preview = LINK_PATTERN.sub("[link]", preview)
    if len(preview) <= limit:
        return preview
    return preview[: max(0, limit - 3)].rstrip() + "..."


def build_matched_preview(message_body: str, match: re.Match[str]) -> str:
    start = max(match.start() - 28, 0)
    end = min(match.end() + 28, len(message_body))
    return build_safe_message_preview(message_body[start:end], limit=120)


def _append_detection(
    detections: list[ChatDetection],
    *,
    category: str,
    severity: str,
    rule_key: str,
    message_body: str,
    match: re.Match[str] | None = None,
) -> None:
    detections.append(
        ChatDetection(
            category=category,
            severity=severity,
            rule_key=rule_key,
            matched_preview=(
                build_matched_preview(message_body, match)
                if match is not None
                else build_safe_message_preview(message_body, limit=120)
            ),
        )
    )


def detect_chat_message(
    message_body: str,
    *,
    is_repeated_message: bool = False,
) -> list[ChatDetection]:
    detections: list[ChatDetection] = []
    rules = (
        ("phone_number", "medium", "phone_number.pattern", PHONE_PATTERN),
        ("email", "medium", "email.pattern", EMAIL_PATTERN),
        ("link", "medium", "link.pattern", LINK_PATTERN),
        (
            "off_platform_contact",
            "medium",
            "off_platform_contact.phrase",
            OFF_PLATFORM_PATTERN,
        ),
        ("payment_discussion", "medium", "payment_discussion.phrase", PAYMENT_PATTERN),
        ("threat_or_safety", "high", "threat_or_safety.phrase", THREAT_PATTERN),
        (
            "harassment_or_abuse",
            "high",
            "harassment_or_abuse.phrase",
            HARASSMENT_PATTERN,
        ),
        ("slur_or_hate", "high", "slur_or_hate.phrase", HATE_PATTERN),
    )
    for category, severity, rule_key, pattern in rules:
        match = pattern.search(message_body)
        if match is not None:
            _append_detection(
                detections,
                category=category,
                severity=severity,
                rule_key=rule_key,
                message_body=message_body,
                match=match,
            )

    if is_repeated_message:
        _append_detection(
            detections,
            category="spam_or_repeated_message",
            severity="low",
            rule_key="spam_or_repeated_message.same_sender_same_body",
            message_body=message_body,
        )

    return detections
