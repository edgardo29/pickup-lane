from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.tests.support.artifacts import (
    REDACTION,
    artifact_text_contains_forbidden_material,
    sanitize_artifact_payload,
    sanitize_artifact_text,
)
from backend.tests.support.browser_quality import BROWSER_QUALITY_RULES


pytestmark = [
    pytest.mark.no_db_cleanup,
    pytest.mark.requirement("EN01-R1", "EN01-R7", "EN01-R9"),
]


def test_artifact_sanitizer_redacts_secret_tokens_database_urls_and_signed_values():
    secret_value = "sk_" + "live_123"
    raw = (
        "Authorization: Bearer abc.def.ghi "
        f"secret={secret_value} "
        "database=postgresql+psycopg://user:password@localhost:5432/pickup_lane_test_db "
        "https://example.invalid/object?X-Amz-Signature=abcdef"
    )

    sanitized = sanitize_artifact_text(raw)

    assert "Bearer abc.def.ghi" not in sanitized
    assert secret_value not in sanitized
    assert "postgresql+psycopg://user:password" not in sanitized
    assert "X-Amz-Signature=abcdef" not in sanitized
    assert REDACTION in sanitized


def test_artifact_payload_sanitizer_redacts_sensitive_keys_recursively():
    payload = {
        "authorization": "Bearer token-value",
        "nested": {
            "cookie": "session=abc",
            "safe_count": 3,
        },
        "items": [{"api_key": "secret"}, "Bearer another-token"],
    }

    sanitized = sanitize_artifact_payload(payload)

    assert sanitized["authorization"] == REDACTION
    assert sanitized["nested"] == {"cookie": REDACTION, "safe_count": 3}
    assert sanitized["items"] == [{"api_key": REDACTION}, f"Bearer {REDACTION}"]


def test_forbidden_artifact_material_is_detectable_before_publishing_failure_artifacts():
    assert artifact_text_contains_forbidden_material("Authorization: Bearer token-value")
    assert not artifact_text_contains_forbidden_material("safe synthetic failure summary")


def test_browser_quality_foundation_records_machine_checkable_rules_without_browser_coverage():
    assert "semantic_or_stable_locators" in BROWSER_QUALITY_RULES
    assert "deterministic_state" in BROWSER_QUALITY_RULES
    assert "controlled_time" in BROWSER_QUALITY_RULES
    assert "no_sleep_synchronization" in BROWSER_QUALITY_RULES
    assert "sanitized_failure_artifacts" in BROWSER_QUALITY_RULES
    assert "deterministic_isolation_cleanup" in BROWSER_QUALITY_RULES
