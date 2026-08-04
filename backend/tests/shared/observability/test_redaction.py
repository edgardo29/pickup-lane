from copy import deepcopy

import pytest

from backend.observability.redaction import REDACTION_MARKER, redact_value


pytestmark = pytest.mark.no_db_cleanup


def test_nested_dictionaries_and_lists_are_redacted_without_mutation():
    original = {
        "safe": "kept",
        "nested": {
            "Authorization": "Bearer abc123",
            "items": [
                {"email": "player@example.com"},
                {"safe_value": "still kept"},
            ],
        },
    }
    snapshot = deepcopy(original)

    redacted = redact_value(original)

    assert original == snapshot
    assert redacted == {
        "safe": "kept",
        "nested": {
            "Authorization": REDACTION_MARKER,
            "items": [
                {"email": REDACTION_MARKER},
                {"safe_value": "still kept"},
            ],
        },
    }


@pytest.mark.parametrize(
    "key",
    [
        "authorization",
        "COOKIE",
        "Set-Cookie",
        "accessToken",
        "refresh_token",
        "id_token",
        "apiKey",
        "password",
        "client_secret",
        "database_URL",
        "Stripe-Signature",
        "firebase_credentials",
        "R2_SECRET_ACCESS_KEY",
        "signed_url",
        "recovery_code",
        "guestEmail",
        "message_body",
        "admin_note",
        "card_fingerprint",
        "storage_object_key",
        "raw_payload",
    ],
)
def test_mixed_case_sensitive_keys_are_redacted(key):
    assert redact_value({key: "secret"}) == {key: REDACTION_MARKER}


@pytest.mark.parametrize(
    "value",
    [
        "postgresql://user:password@localhost:5432/pickup_lane",
        "https://r2.example.com/bucket/object?X-Amz-Signature=abc",
        "seti_123_secret_456",
        "whsec_123456",
        "Traceback (most recent call last): File \"/tmp/app.py\", line 1",
        "venues/00000000-0000-4000-8000-000000000001/card.jpg",
        "Call me at 312-555-1212.",
        "player@example.com",
    ],
)
def test_sensitive_string_values_are_redacted(value):
    assert redact_value({"safe_key": value}) == {"safe_key": REDACTION_MARKER}


def test_tuple_structure_is_preserved():
    redacted = redact_value(("safe", {"Cookie": "session=abc"}))

    assert redacted == ("safe", {"Cookie": REDACTION_MARKER})


def test_unexpected_object_is_redacted_without_repr_leakage():
    class UnexpectedObject:
        def __repr__(self):
            return "UnexpectedObject(secret='abc')"

    assert redact_value({"object": UnexpectedObject()}) == {
        "object": REDACTION_MARKER
    }


def test_recursive_mapping_fails_safely():
    cyclic = {"safe": "kept"}
    cyclic["self"] = cyclic

    assert redact_value(cyclic) == {
        "safe": "kept",
        "self": REDACTION_MARKER,
    }
