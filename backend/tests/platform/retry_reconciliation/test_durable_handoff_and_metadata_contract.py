from __future__ import annotations

from pathlib import Path

import pytest

import backend.services.provider_retry_policy as retry_policy

pytestmark = pytest.mark.no_db_cleanup

_REPO_ROOT = Path(__file__).resolve().parents[4]
_SENSITIVE_STATIC_MARKERS = (
    "".join(("sk", "_", "live", "_")),
    "".join(("rk", "_", "live", "_")),
    "".join(("pk", "_", "live", "_")),
    "".join(("wh", "sec", "_")),
    "postgresql" + "://",
    "postgresql+psycopg" + "://",
    "Bearer ",
    "DATABASE" + "_URL",
    "Traceback",
)


@pytest.mark.requirement("WS02-04C2-R9")
def test_durable_handoffs_are_ws05_owned_and_record_required_properties() -> None:
    handoffs = {
        handoff.workflow: handoff
        for handoff in retry_policy.DURABLE_WORK_HANDOFFS
    }

    assert handoffs.keys() == {
        "provider_unknown_outcome_reconciliation",
        "checkout_post_expiry_provider_reconciliation",
        "account_deletion_cleanup_recovery",
        "future_external_notification_delivery",
        "future_platform_notice_external_delivery",
        "durable_financial_reconciliation",
    }
    assert "persisted provider identity" in handoffs[
        "checkout_post_expiry_provider_reconciliation"
    ].required_durable_properties
    assert "credit/capacity compensation rules" in handoffs[
        "checkout_post_expiry_provider_reconciliation"
    ].required_durable_properties

    for handoff in handoffs.values():
        assert handoff.owner_pass == "WS05"
        assert handoff.approved_worker_retry_attempts is None
        assert handoff.approved_worker_concurrency is None
        assert handoff.approved_lease_seconds is None
        assert handoff.approved_scheduler_cadence_seconds is None
        assert handoff.approved_poison_threshold is None


@pytest.mark.requirement("WS02-04C2-R10")
def test_c2_emits_no_retry_policy_telemetry_directly() -> None:
    source = (_REPO_ROOT / "backend/services/provider_retry_policy.py").read_text()

    assert "telemetry_labels" not in source
    assert "record_event" not in source
    assert "emit" not in source
    assert "logger." not in source


@pytest.mark.requirement("WS02-04C2-R10")
def test_future_runtime_metadata_is_bounded_to_policy_classes() -> None:
    policy = retry_policy.policy_by_operation_context(
        "stripe.payment_intent.confirm",
        "checkout_initial_confirm_after_checkpoint",
    )

    assert policy.provider == "stripe"
    assert policy.operation == "stripe.payment_intent.confirm"
    assert policy.safety_class.value == "RECONCILE_BEFORE_RETRY"
    assert policy.dependency_retry_owner.value == "DEPENDENCY_OWNED"
    assert policy.workflow_context == "checkout_initial_confirm_after_checkpoint"


@pytest.mark.requirement("WS02-04C2-R10")
def test_static_policy_prose_contains_no_real_sensitive_values() -> None:
    rendered = repr(retry_policy.PROVIDER_OPERATION_RETRY_POLICIES)
    rendered += repr(retry_policy.FANOUT_EXECUTION_POLICIES)
    rendered += repr(retry_policy.DURABLE_WORK_HANDOFFS)

    for marker in _SENSITIVE_STATIC_MARKERS:
        assert marker not in rendered


@pytest.mark.requirement("WS02-04C2-R9", "WS02-04C2-R10")
def test_deferred_external_runtime_facts_are_not_claimed_by_c2_source() -> None:
    source = (_REPO_ROOT / "backend/services/provider_retry_policy.py").read_text()

    for forbidden in (
        "provider dashboard is configured",
        "live redelivery schedule",
        "worker retry count is",
        "lease duration is",
        "provider concurrency cap is",
        "telemetry dashboard is configured",
    ):
        assert forbidden not in source.lower()
