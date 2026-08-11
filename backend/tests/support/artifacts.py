from __future__ import annotations

import re
from collections.abc import Mapping


REDACTION = "[REDACTED]"
_SENSITIVE_KEY_RE = re.compile(
    r"(authorization|cookie|token|secret|password|api[_-]?key|webhook|signature)",
    flags=re.IGNORECASE,
)
_BEARER_RE = re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]+", flags=re.IGNORECASE)
_STRIPE_SECRET_RE = re.compile(r"\b(?:sk|rk|whsec)_(?:test|live)?_[A-Za-z0-9_]+\b")
_FIREBASE_TOKEN_RE = re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b")
_DATABASE_URL_RE = re.compile(r"\bpostgres(?:ql)?(?:\+\w+)?://[^\s'\"<>]+", flags=re.IGNORECASE)
_SIGNED_URL_RE = re.compile(r"([?&](?:X-Amz-Signature|Signature|sig)=)[^&\s]+", flags=re.IGNORECASE)


def sanitize_artifact_text(text: str) -> str:
    sanitized = _BEARER_RE.sub(f"Bearer {REDACTION}", text)
    sanitized = _STRIPE_SECRET_RE.sub(REDACTION, sanitized)
    sanitized = _FIREBASE_TOKEN_RE.sub(REDACTION, sanitized)
    sanitized = _DATABASE_URL_RE.sub(REDACTION, sanitized)
    sanitized = _SIGNED_URL_RE.sub(rf"\1{REDACTION}", sanitized)
    return sanitized


def sanitize_artifact_payload(payload: Mapping[str, object]) -> dict[str, object]:
    sanitized: dict[str, object] = {}
    for key, value in payload.items():
        if _SENSITIVE_KEY_RE.search(key):
            sanitized[key] = REDACTION
        elif isinstance(value, str):
            sanitized[key] = sanitize_artifact_text(value)
        elif isinstance(value, Mapping):
            sanitized[key] = sanitize_artifact_payload(value)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_artifact_payload(item) if isinstance(item, Mapping)
                else sanitize_artifact_text(item) if isinstance(item, str)
                else item
                for item in value
            ]
        else:
            sanitized[key] = value
    return sanitized


def artifact_text_contains_forbidden_material(text: str) -> bool:
    return sanitize_artifact_text(text) != text or bool(_SENSITIVE_KEY_RE.search(text))
