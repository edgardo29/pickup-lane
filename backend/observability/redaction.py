"""Redaction helpers for sensitive fields before diagnostic use."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import re
from typing import Any
from urllib.parse import parse_qsl, urlsplit


REDACTION_MARKER = "[REDACTED]"

_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?1[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}(?!\d)")
_UUID_RE = re.compile(
    r"(?<![0-9A-Fa-f])"
    r"[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-"
    r"[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}"
    r"(?![0-9A-Fa-f])"
)
_DATABASE_URL_RE = re.compile(
    r"\b(?:postgresql|postgres|mysql|sqlite)(?:\+[a-z0-9_]+)?://",
    re.IGNORECASE,
)
_SECRET_VALUE_RE = re.compile(
    r"(?:"
    r"Bearer\s+[A-Za-z0-9._~+/=-]+|"
    r"(?:sk|rk)_(?:live|test)_[A-Za-z0-9]+|"
    r"whsec_[A-Za-z0-9]+|"
    r"(?:pi|seti)_[A-Za-z0-9]+_secret_[A-Za-z0-9]+|"
    r"xox[baprs]-[A-Za-z0-9-]+"
    r")",
    re.IGNORECASE,
)
_SECRET_NAME_RE = re.compile(
    r"\b(?:R2|FIREBASE|STRIPE|DATABASE|API)_[A-Z0-9_]*(?:SECRET|KEY|TOKEN|CREDENTIALS|URL)\b"
)
_URL_RE = re.compile(r"https?://[^\s<>'\"]+")
_INTERNAL_ERROR_RE = re.compile(
    r"(?:"
    r"Traceback \(most recent call last\)|"
    r"IntegrityError|ProgrammingError|OperationalError|SQLAlchemyError|"
    r"psycopg|duplicate key value|violates .*constraint|"
    r"File \"[^\"]+\", line \d+"
    r")",
    re.IGNORECASE,
)
_OBJECT_KEY_RE = re.compile(
    r"\b(?:venues|games|uploads|objects)/[A-Za-z0-9._~/-]+\b",
    re.IGNORECASE,
)
_SENSITIVE_QUERY_KEYS = {
    "access_token",
    "api-key",
    "api_key",
    "authorization",
    "awsaccesskeyid",
    "client_secret",
    "credential",
    "expires",
    "expiresin",
    "id_token",
    "key",
    "password",
    "refresh_token",
    "secret",
    "signature",
    "sig",
    "token",
    "x-amz-credential",
    "x-amz-security-token",
    "x-amz-signature",
    "x-api-key",
    "x_api_key",
}
_EXACT_SENSITIVE_KEYS = {
    "admin_note",
    "admin_notes",
    "admin_reason",
    "api_key_id",
    "api_secret_key",
    "api_token",
    "auth",
    "auth_header",
    "authentication",
    "api_key",
    "apikey",
    "authorization",
    "aws_access_key_id",
    "aws_secret_access_key",
    "aws_session_token",
    "bearer_token",
    "body",
    "card_fingerprint",
    "client_secret",
    "cloudflare_api_key",
    "cloudflare_api_token",
    "cookie",
    "database_url",
    "display_name",
    "email",
    "event_payload",
    "exception",
    "firebase_admin_credentials",
    "firebase_admin_credentials_json",
    "firebase_admin_key",
    "firebase_credentials",
    "first_name",
    "free_text",
    "full_name",
    "guest_contact",
    "guest_email",
    "guest_name",
    "guest_phone",
    "id_token",
    "last_name",
    "message",
    "message_body",
    "name",
    "note",
    "object_key",
    "password",
    "phone",
    "provider_api_key",
    "proxy_authorization",
    "raw_payload",
    "read_url",
    "reason",
    "recovery_code",
    "refresh_token",
    "r2_access_key",
    "request_body",
    "response_body",
    "r2_access_key_id",
    "r2_secret_key",
    "r2_secret_access_key",
    "secret",
    "set_cookie",
    "signed_url",
    "storage_object_key",
    "street_address",
    "stripe_client_secret",
    "stripe_secret_key",
    "stripe_signature",
    "stripe_webhook_secret",
    "upload_url",
    "user_generated_content",
    "webhook_payload",
    "x_api_key",
    "x_auth_token",
    "x_authorization",
}
_SENSITIVE_KEY_FRAGMENTS = {
    "access_token",
    "api_key",
    "authorization",
    "auth_token",
    "credentials_json",
    "client_secret",
    "firebase_credentials",
    "object_key",
    "private_key",
    "recovery_code",
    "refresh_token",
    "secret_key",
    "secret",
    "signed_url",
    "stripe_signature",
    "webhook_secret",
}


def redact_value(value: Any) -> Any:
    """Return a redacted copy of value without mutating the original object."""

    return _redact_value(value, seen=set())


def is_sensitive_key(key: object) -> bool:
    """Return whether a mapping key represents sensitive diagnostic data."""

    normalized = _normalize_key(key)
    if normalized in _EXACT_SENSITIVE_KEYS:
        return True
    if normalized.endswith("_token") or normalized.endswith("_secret"):
        return True
    return any(fragment in normalized for fragment in _SENSITIVE_KEY_FRAGMENTS)


def contains_sensitive_text(value: str) -> bool:
    """Detect sensitive text that must not be emitted in diagnostics."""

    if (
        _EMAIL_RE.search(value)
        or _contains_phone_outside_uuid(value)
        or _DATABASE_URL_RE.search(value)
        or _SECRET_VALUE_RE.search(value)
        or _SECRET_NAME_RE.search(value)
        or _INTERNAL_ERROR_RE.search(value)
        or _OBJECT_KEY_RE.search(value)
    ):
        return True

    return _url_has_sensitive_query(value)


def _contains_phone_outside_uuid(value: str) -> bool:
    uuid_spans = tuple(match.span() for match in _UUID_RE.finditer(value))
    return any(
        not any(
            phone_match.start() < uuid_end and phone_match.end() > uuid_start
            for uuid_start, uuid_end in uuid_spans
        )
        for phone_match in _PHONE_RE.finditer(value)
    )


def _redact_value(value: Any, *, seen: set[int]) -> Any:
    if isinstance(value, Mapping):
        value_id = id(value)
        if value_id in seen:
            return REDACTION_MARKER
        seen.add(value_id)
        try:
            return {
                key: (
                    REDACTION_MARKER
                    if is_sensitive_key(key)
                    else _redact_value(item, seen=seen)
                )
                for key, item in value.items()
            }
        finally:
            seen.remove(value_id)

    if _is_non_string_sequence(value):
        value_id = id(value)
        if value_id in seen:
            return REDACTION_MARKER
        seen.add(value_id)
        try:
            redacted_items = [_redact_value(item, seen=seen) for item in value]
        finally:
            seen.remove(value_id)

        if isinstance(value, tuple):
            return tuple(redacted_items)
        return redacted_items

    if isinstance(value, str):
        return REDACTION_MARKER if contains_sensitive_text(value) else value

    if value is None or isinstance(value, bool | int | float):
        return value

    return REDACTION_MARKER


def _is_non_string_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray)


def _normalize_key(key: object) -> str:
    text = str(key).strip()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", text)
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _url_has_sensitive_query(value: str) -> bool:
    embedded_urls = _URL_RE.findall(value)
    if embedded_urls:
        return any(_single_url_has_sensitive_query(url) for url in embedded_urls)

    return _single_url_has_sensitive_query(value)


def _single_url_has_sensitive_query(value: str) -> bool:
    try:
        parsed = urlsplit(value)
    except ValueError:
        return False

    if not parsed.scheme or not parsed.netloc or not parsed.query:
        return False

    return any(
        key.strip().lower() in _SENSITIVE_QUERY_KEYS
        for key, _item_value in parse_qsl(parsed.query, keep_blank_values=True)
    )
