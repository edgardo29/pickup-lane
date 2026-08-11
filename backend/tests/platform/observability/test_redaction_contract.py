from __future__ import annotations

import pytest

from backend.observability.redaction import REDACTION_MARKER, is_sensitive_key, redact_value


pytestmark = pytest.mark.no_db_cleanup


@pytest.mark.requirement("EN02-REDACT-001")
@pytest.mark.parametrize(
    "key",
    [
        "Authorization",
        "authorization",
        "proxy-authorization",
        "proxy_authorization",
        "X-Api-Key",
        "x_api_key",
        "provider_api_key",
        "Cloudflare-Api-Token",
        "STRIPE_WEBHOOK_SECRET",
        "aws_secret_access_key",
        "firebase_admin_credentials_json",
        "R2SecretAccessKey",
    ],
)
def test_redaction_recognizes_sensitive_key_and_header_spellings(key: str):
    payload = {key: "synthetic-secret-value"}

    assert is_sensitive_key(key)
    assert redact_value(payload) == {key: REDACTION_MARKER}


@pytest.mark.requirement("EN02-REDACT-001")
@pytest.mark.parametrize(
    "value",
    [
        "Authorization: Bearer synthetic-token-value",
        "postgresql+psycopg://user:pass@example.invalid:5432/db",
        "https://example.invalid/object?x-api-key=synthetic-secret",
        "https://example.invalid/object?X-Amz-Signature=synthetic-signature",
    ],
)
def test_redaction_protects_sensitive_values_embedded_in_strings(value: str):
    assert redact_value(value) == REDACTION_MARKER


@pytest.mark.requirement("EN02-REDACT-001")
def test_redaction_is_recursive_non_mutating_and_preserves_safe_structure():
    original = {
        "record_id": "booking_123",
        "count": 2,
        "nested": {
            "safe_status": "accepted",
            "x-api-key": "synthetic-secret",
        },
        "items": [
            {"authorization": "Bearer synthetic-token"},
            ("safe_label", "sk_test_synthetic"),
        ],
    }

    redacted = redact_value(original)

    assert redacted == {
        "record_id": "booking_123",
        "count": 2,
        "nested": {
            "safe_status": "accepted",
            "x-api-key": REDACTION_MARKER,
        },
        "items": [
            {"authorization": REDACTION_MARKER},
            ("safe_label", REDACTION_MARKER),
        ],
    }
    assert original["nested"]["x-api-key"] == "synthetic-secret"
    assert original["items"][0]["authorization"] == "Bearer synthetic-token"


@pytest.mark.requirement("EN02-REDACT-001")
def test_redaction_does_not_redact_safe_structural_identifiers_without_authority():
    payload = {
        "booking_id": "booking_123",
        "game_id": "game_456",
        "venue_id": "venue_789",
        "safe_count": 3,
    }

    assert redact_value(payload) == payload


@pytest.mark.requirement("EN02-REDACT-001")
def test_redaction_handles_recursive_structures_without_leaking_values():
    payload: dict[str, object] = {"safe": "metadata"}
    payload["self"] = payload

    redacted = redact_value(payload)

    assert redacted == {"safe": "metadata", "self": REDACTION_MARKER}


@pytest.mark.requirement("EN02-REDACT-001")
def test_redaction_never_uses_unknown_object_repr():
    class UnsafeRepr:
        def __repr__(self) -> str:
            return "Bearer synthetic-token-value"

    assert redact_value(UnsafeRepr()) == REDACTION_MARKER
