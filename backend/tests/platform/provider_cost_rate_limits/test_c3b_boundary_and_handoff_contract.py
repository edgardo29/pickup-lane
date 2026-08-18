from __future__ import annotations

from pathlib import Path

import pytest

import backend.services.provider_retry_policy as retry_policy

pytestmark = pytest.mark.no_db_cleanup

_REPO_ROOT = Path(__file__).resolve().parents[4]


def _read(relative_path: str) -> str:
    return (_REPO_ROOT / relative_path).read_text()


@pytest.mark.requirement("WS02-04C3B-R4", "WS02-04C3B-R7")
def test_c1_c2_c3a_and_b2a2b2_boundaries_remain_distinct_from_c3b_rate_control() -> None:
    c3b_plan = _read("docs/production-readiness/planning/passes/ws02/ws02-04c3b-provider-cost-rate-limit-deferral.md")
    c1_plan = _read("docs/production-readiness/planning/passes/ws02/ws02-04c1-operation-timeouts-cancellation.md")
    c2_plan = _read("docs/production-readiness/planning/passes/ws02/ws02-04c2-retry-reconciliation-backpressure.md")
    c3a_plan = _read("docs/production-readiness/planning/passes/ws02/ws02-04c3a-chat-rate-limit-contract.md")
    b2a2b2_plan = _read(
        "docs/production-readiness/planning/passes/ws02/ws02-04b2a2b2-opaque-provider-payment-inputs.md"
    )

    assert "C1 owns current source-configured operation timeouts" in c3b_plan
    assert "C2 owns retry/reconciliation/backpressure classification" in c3b_plan
    assert "C3A owns the approved source-owned authenticated chat limiter only" in c3b_plan
    assert "B2A2B2 owns provider/payment input ownership" in c3b_plan
    assert "rate limits, abuse controls, concurrency caps, or provider-cost controls" in c1_plan
    assert "C3B owns later provider-cost/action\nrate and abuse controls" in c2_plan
    assert "does not approve\nprovider-cost action limits" in c3a_plan
    assert "source-derived game-credit issuance and reversal bounds" in b2a2b2_plan
    assert "rate limits and abuse controls outside already accepted source-owned owners" in b2a2b2_plan


@pytest.mark.requirement("WS02-04C3B-R4", "WS02-04C3B-R7")
def test_current_provider_retry_and_handoff_metadata_preserves_later_owners() -> None:
    assert {handoff.workflow for handoff in retry_policy.DURABLE_WORK_HANDOFFS} == {
        "provider_unknown_outcome_reconciliation",
        "checkout_post_expiry_provider_reconciliation",
        "account_deletion_cleanup_recovery",
        "future_external_notification_delivery",
        "future_platform_notice_external_delivery",
        "durable_financial_reconciliation",
    }

    for handoff in retry_policy.DURABLE_WORK_HANDOFFS:
        assert handoff.owner_pass == "WS05"
        assert handoff.required_durable_properties
        assert handoff.approved_worker_retry_attempts is None
        assert handoff.approved_worker_concurrency is None
        assert handoff.approved_lease_seconds is None
        assert handoff.approved_scheduler_cadence_seconds is None
        assert handoff.approved_poison_threshold is None

    for fanout in retry_policy.FANOUT_EXECUTION_POLICIES:
        assert fanout.new_concurrency_allowed is False
        assert fanout.approved_concurrency_cap is None
        assert fanout.approved_batch_size is None


@pytest.mark.requirement("WS02-04C3B-R2", "WS02-04C3B-R7")
def test_external_runtime_provider_edge_and_api_m11_gaps_remain_open() -> None:
    c3b_plan = _read("docs/production-readiness/planning/passes/ws02/ws02-04c3b-provider-cost-rate-limit-deferral.md")
    source_owned_closeout = _read("docs/production-readiness/planning/passes/ws02/ws02-04-source-owned-closeout.md")
    audit_part_1 = _read("docs/production-readiness/audit-research/audit-part-1.md")

    for phrase in (
        "Provider dashboards",
        "real provider quotas/costs",
        "production request volume",
        "trusted client IP",
        "edge/WAF/CAPTCHA",
        "runtime/load behavior",
        "monitoring/alert thresholds",
        "full API-M11 closure",
    ):
        assert phrase in c3b_plan

    assert "claim API-M11 is closed" in c3b_plan
    assert "Authenticated chat throttling is source-owned and implemented" in source_owned_closeout
    assert "Provider-cost action rates" in source_owned_closeout
    assert "remain open or evidence-deferred" in source_owned_closeout
    assert "found only chat-scoped DB-count controls" in audit_part_1
    assert "No broad abuse-control policy or monitoring evidence" in audit_part_1
