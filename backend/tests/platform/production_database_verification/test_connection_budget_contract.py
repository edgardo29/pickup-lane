from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from backend.tests.support.production_database_verification import (
    BUDGET_INPUT_FIELDS,
    MUTABLE_CAPACITY_INPUT_FIELDS,
    MUTABLE_CAPACITY_REQUIREMENTS,
    REQUIRED_LIMIT_BASIS_FIELDS,
    calculate_connection_budget,
    validate_budget_evidence,
)

pytestmark = pytest.mark.no_db_cleanup

_REPO_ROOT = Path(__file__).resolve().parents[4]
_CONTRACT_PATH = (
    "docs/production-readiness/planning/passes/ws04/"
    "ws04-01c-production-database-evidence-contract.json"
)


def _load_contract() -> dict:
    return json.loads((_REPO_ROOT / _CONTRACT_PATH).read_text())


def _source_metadata() -> dict[str, str]:
    return {
        "source_type": "synthetic test fixture",
        "date_collected": "2026-08-24",
        "reviewer": "ws04-01c-test",
        "purpose": "prove deterministic budget validator behavior",
        "supported_control_or_pass": "WS04-01C",
        "sanitized_evidence_reference": "synthetic-test-only",
    }


def _verified_stateful(value: str) -> dict:
    return {
        "state": "verified",
        "value": value,
        "evidence": _source_metadata(),
    }


def _budget_input(value: int, *, zero_reason: str | None = None) -> dict:
    entry = {
        "value": value,
        "evidence_state": "verified",
        "evidence": _source_metadata(),
    }
    if zero_reason is not None:
        entry["zero_reason"] = zero_reason
    return entry


def _verified_budget_record(values: dict[str, int]) -> dict:
    record = _load_contract()
    record["budget_model"]["inputs"] = {
        field: _budget_input(
            values[field],
            zero_reason="synthetic fixture proves this consumer is absent"
            if values[field] == 0
            else None,
        )
        for field in BUDGET_INPUT_FIELDS
    }
    record["budget_model"]["reported_calculations"] = calculate_connection_budget(values).as_dict()
    for field in REQUIRED_LIMIT_BASIS_FIELDS:
        record["budget_model"]["limit_basis"][field] = _verified_stateful(
            f"synthetic {field} basis"
        )
    for input_name in MUTABLE_CAPACITY_INPUT_FIELDS:
        record["budget_model"]["mutable_capacity_inputs"][input_name] = {
            requirement: _verified_stateful(f"synthetic {input_name} {requirement}")
            for requirement in MUTABLE_CAPACITY_REQUIREMENTS
        }
    record["budget_model"]["telemetry_plan"] = {
        "state": "verified",
        "required_signals": [
            "pool utilization",
            "connection errors",
            "database outcome class",
            "API correlation",
            "job correlation when jobs exist",
        ],
        "dashboard_alert_owner": "WS09",
        "evidence": _source_metadata(),
    }
    return record


@pytest.mark.requirement("WS04-01C-R3", "WS04-01C-R4")
def test_budget_formula_counts_incremental_rolling_overlap_once() -> None:
    values = {
        "DB_POOL_SIZE": 5,
        "DB_MAX_OVERFLOW": 2,
        "max_api_instances": 3,
        "api_processes_per_instance": 2,
        "additional_rolling_overlap_api_instances": 1,
        "api_processes_per_additional_overlap_instance": 2,
        "background_worker_connections": 4,
        "scheduler_or_job_runner_connections": 1,
        "migration_connections": 1,
        "monitoring_connections": 1,
        "reporting_or_support_connections": 1,
        "routine_human_access_connections": 1,
        "operational_reserve_connections": 5,
        "usable_provider_connection_capacity": 80,
    }

    budget = calculate_connection_budget(values)

    assert budget.per_process_application_connections == 7
    assert budget.api_steady_state_connections == 42
    assert budget.api_incremental_rolling_overlap_connections == 14
    assert budget.total_budgeted_peak_connections == 70
    assert budget.remaining_headroom == 10
    assert validate_budget_evidence(_verified_budget_record(values), require_final_values=True) == []


@pytest.mark.requirement("WS04-01C-R3", "WS04-01C-R4")
def test_budget_validation_rejects_missing_invalid_or_unattributed_inputs() -> None:
    values = {
        "DB_POOL_SIZE": 5,
        "DB_MAX_OVERFLOW": 2,
        "max_api_instances": 3,
        "api_processes_per_instance": 2,
        "additional_rolling_overlap_api_instances": 1,
        "api_processes_per_additional_overlap_instance": 2,
        "background_worker_connections": 4,
        "scheduler_or_job_runner_connections": 1,
        "migration_connections": 1,
        "monitoring_connections": 1,
        "reporting_or_support_connections": 1,
        "routine_human_access_connections": 1,
        "operational_reserve_connections": 5,
        "usable_provider_connection_capacity": 80,
    }
    base = _verified_budget_record(values)

    missing = deepcopy(base)
    del missing["budget_model"]["inputs"]["operational_reserve_connections"]
    assert any(
        "budget_model.inputs.operational_reserve_connections must be an object" in error
        or "missing budget input: operational_reserve_connections" in error
        for error in validate_budget_evidence(missing, require_final_values=True)
    )

    negative = deepcopy(base)
    negative["budget_model"]["inputs"]["background_worker_connections"]["value"] = -1
    assert any(
        "background_worker_connections verified value must be a non-negative integer" in error
        for error in validate_budget_evidence(negative, require_final_values=True)
    )

    unattributed = deepcopy(base)
    del unattributed["budget_model"]["inputs"]["DB_POOL_SIZE"]["evidence"]
    assert "DB_POOL_SIZE verified value requires source metadata" in validate_budget_evidence(
        unattributed,
        require_final_values=True,
    )


@pytest.mark.requirement("WS04-01C-R3", "WS04-01C-R4", "WS04-01C-R8")
def test_budget_validation_rejects_unknown_zero_mismatch_stale_and_over_capacity() -> None:
    values = {
        "DB_POOL_SIZE": 5,
        "DB_MAX_OVERFLOW": 0,
        "max_api_instances": 1,
        "api_processes_per_instance": 1,
        "additional_rolling_overlap_api_instances": 0,
        "api_processes_per_additional_overlap_instance": 0,
        "background_worker_connections": 0,
        "scheduler_or_job_runner_connections": 0,
        "migration_connections": 1,
        "monitoring_connections": 0,
        "reporting_or_support_connections": 0,
        "routine_human_access_connections": 0,
        "operational_reserve_connections": 1,
        "usable_provider_connection_capacity": 10,
    }
    base = _verified_budget_record(values)

    zero_without_reason = deepcopy(base)
    zero_without_reason["budget_model"]["inputs"]["DB_MAX_OVERFLOW"].pop("zero_reason")
    assert "DB_MAX_OVERFLOW zero value requires absence evidence" in validate_budget_evidence(
        zero_without_reason,
        require_final_values=True,
    )

    mismatch = deepcopy(base)
    mismatch["budget_model"]["reported_calculations"]["total_budgeted_peak_connections"] = 999
    assert any(
        "total_budgeted_peak_connections does not match calculated value" in error
        for error in validate_budget_evidence(mismatch, require_final_values=True)
    )

    stale = deepcopy(base)
    stale["budget_model"]["inputs"]["max_api_instances"]["evidence_state"] = "stale"
    assert "max_api_instances final verification cannot use state 'stale'" in validate_budget_evidence(
        stale,
        require_final_values=True,
    )

    over_capacity_values = dict(values, usable_provider_connection_capacity=5)
    over_capacity = _verified_budget_record(over_capacity_values)
    assert "remaining headroom must not be negative" in validate_budget_evidence(
        over_capacity,
        require_final_values=True,
    )


@pytest.mark.requirement("WS04-01C-R4")
def test_limit_basis_and_mutable_capacity_inputs_follow_fdn04_method() -> None:
    contract = _load_contract()

    assert validate_budget_evidence(contract, require_final_values=False) == []
    assert {
        "autoscaling_ceiling_or_disabled_evidence",
        "pooler_or_proxy_mode",
    } <= set(contract["budget_model"]["mutable_capacity_inputs"])

    missing_basis = deepcopy(contract)
    del missing_basis["budget_model"]["limit_basis"]["expected_workload_and_abuse_risk"]
    assert "missing budget_model.limit_basis.expected_workload_and_abuse_risk" in validate_budget_evidence(
        missing_basis,
        require_final_values=False,
    )

    missing_mutable_field = deepcopy(contract)
    del missing_mutable_field["budget_model"]["mutable_capacity_inputs"]["DB_POOL_SIZE"][
        "boundary_and_multi_instance_evidence"
    ]
    assert (
        "missing budget_model.mutable_capacity_inputs.DB_POOL_SIZE."
        "boundary_and_multi_instance_evidence"
    ) in validate_budget_evidence(missing_mutable_field, require_final_values=False)

    missing_autoscaling_metadata = deepcopy(contract)
    del missing_autoscaling_metadata["budget_model"]["mutable_capacity_inputs"][
        "autoscaling_ceiling_or_disabled_evidence"
    ]["rollback_or_abort_condition"]
    assert (
        "missing budget_model.mutable_capacity_inputs."
        "autoscaling_ceiling_or_disabled_evidence.rollback_or_abort_condition"
    ) in validate_budget_evidence(missing_autoscaling_metadata, require_final_values=False)

    missing_pooler_metadata = deepcopy(contract)
    del missing_pooler_metadata["budget_model"]["mutable_capacity_inputs"][
        "pooler_or_proxy_mode"
    ]["safe_adjustment_or_forward_fix"]
    assert (
        "missing budget_model.mutable_capacity_inputs."
        "pooler_or_proxy_mode.safe_adjustment_or_forward_fix"
    ) in validate_budget_evidence(missing_pooler_metadata, require_final_values=False)


@pytest.mark.requirement("WS04-01C-R4", "WS04-01C-R8")
def test_final_budget_evidence_rejects_deferred_basis_adjustment_and_telemetry() -> None:
    values = {
        "DB_POOL_SIZE": 5,
        "DB_MAX_OVERFLOW": 2,
        "max_api_instances": 3,
        "api_processes_per_instance": 2,
        "additional_rolling_overlap_api_instances": 1,
        "api_processes_per_additional_overlap_instance": 2,
        "background_worker_connections": 4,
        "scheduler_or_job_runner_connections": 1,
        "migration_connections": 1,
        "monitoring_connections": 1,
        "reporting_or_support_connections": 1,
        "routine_human_access_connections": 1,
        "operational_reserve_connections": 5,
        "usable_provider_connection_capacity": 80,
    }
    base = _verified_budget_record(values)

    deferred_basis = deepcopy(base)
    deferred_basis["budget_model"]["limit_basis"]["telemetry"] = {
        "state": "deferred_to_ws04_01d",
        "value": None,
        "reason": "not yet collected",
    }
    assert (
        "budget_model.limit_basis.telemetry must be verified for final evidence"
    ) in validate_budget_evidence(deferred_basis, require_final_values=True)

    unattributed_adjustment = deepcopy(base)
    del unattributed_adjustment["budget_model"]["mutable_capacity_inputs"]["DB_POOL_SIZE"][
        "rollback_or_abort_condition"
    ]["evidence"]
    assert (
        "budget_model.mutable_capacity_inputs.DB_POOL_SIZE.rollback_or_abort_condition "
        "verified evidence requires source metadata"
    ) in validate_budget_evidence(unattributed_adjustment, require_final_values=True)

    deferred_telemetry = deepcopy(base)
    deferred_telemetry["budget_model"]["telemetry_plan"]["state"] = "deferred_to_ws04_01d"
    assert "budget_model.telemetry_plan must be verified for final evidence" in validate_budget_evidence(
        deferred_telemetry,
        require_final_values=True,
    )
