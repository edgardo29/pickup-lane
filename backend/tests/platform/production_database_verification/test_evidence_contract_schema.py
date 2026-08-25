from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from backend.tests.support.production_database_verification import (
    APPLICATION_RUNTIME_FORBIDDEN_FLAGS,
    BUDGET_INPUT_FIELDS,
    FINAL_METADATA_VALUE_FIELDS,
    FINAL_ROLE_EVIDENCE_CHECKS,
    MUTABLE_CAPACITY_INPUT_FIELDS,
    MUTABLE_CAPACITY_REQUIREMENTS,
    REQUIRED_METADATA_FIELDS,
    REQUIRED_LIMIT_BASIS_FIELDS,
    RUNTIME_TOPOLOGY_FIELDS,
    calculate_connection_budget,
    detect_sensitive_values,
    validate_evidence_contract,
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
        "purpose": "prove deterministic final-state validator behavior",
        "supported_control_or_pass": "WS04-01C",
        "sanitized_evidence_reference": "synthetic-test-only",
    }


def _verified_metadata(value: object) -> dict:
    return {
        "state": "verified",
        "value": value,
    }


def _verified_evidence_value(value: object) -> dict:
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


def _verified_role(alias: str) -> dict:
    return {
        "state": "verified",
        "safe_alias": alias,
        "completed_checks": list(FINAL_ROLE_EVIDENCE_CHECKS),
        "evidence": _source_metadata(),
    }


def _final_d_contract() -> dict:
    contract = _load_contract()
    contract["contract_state"] = "ws04_01d_final_evidence"

    for field in FINAL_METADATA_VALUE_FIELDS:
        contract["metadata"][field] = _verified_metadata(f"synthetic {field}")
    contract["metadata"]["supported_controls"] = _verified_metadata(
        ["DB-002", "DB-015", "GOV-006", "OPS-025"]
    )
    contract["metadata"]["supported_passes"] = _verified_metadata(
        ["WS04-01C", "WS04-01D"]
    )
    contract["metadata"]["open_gaps"] = _verified_metadata([])

    for field in RUNTIME_TOPOLOGY_FIELDS:
        contract["topology_contract"][field] = _verified_evidence_value(
            f"synthetic {field}"
        )
    contract["topology_contract"]["connection_mode"] = {
        **_verified_evidence_value("direct"),
        "allowed_values": ["direct", "provider_pooler", "proxy"],
    }
    contract["topology_contract"]["pooler_client_connection_ceiling"] = {
        "state": "not_applicable",
        "value": None,
        "reason": "synthetic direct connection mode has no provider pooler client ceiling",
    }
    contract["topology_contract"]["pooler_server_connection_ceiling"] = {
        "state": "not_applicable",
        "value": None,
        "reason": "synthetic direct connection mode has no provider pooler server ceiling",
    }

    values = {
        "DB_POOL_SIZE": 5,
        "DB_MAX_OVERFLOW": 1,
        "max_api_instances": 2,
        "api_processes_per_instance": 2,
        "additional_rolling_overlap_api_instances": 1,
        "api_processes_per_additional_overlap_instance": 1,
        "background_worker_connections": 1,
        "scheduler_or_job_runner_connections": 1,
        "migration_connections": 1,
        "monitoring_connections": 1,
        "reporting_or_support_connections": 1,
        "routine_human_access_connections": 1,
        "operational_reserve_connections": 4,
        "usable_provider_connection_capacity": 50,
    }
    contract["budget_model"]["inputs"] = {
        field: _budget_input(values[field])
        for field in BUDGET_INPUT_FIELDS
    }
    contract["budget_model"]["reported_calculations"] = calculate_connection_budget(
        values
    ).as_dict()
    contract["budget_model"]["limit_basis"] = {
        field: _verified_evidence_value(f"synthetic {field} basis")
        for field in REQUIRED_LIMIT_BASIS_FIELDS
    }
    contract["budget_model"]["mutable_capacity_inputs"] = {
        input_name: {
            requirement: _verified_evidence_value(
                f"synthetic {input_name} {requirement}"
            )
            for requirement in MUTABLE_CAPACITY_REQUIREMENTS
        }
        for input_name in MUTABLE_CAPACITY_INPUT_FIELDS
    }
    contract["budget_model"]["telemetry_plan"] = {
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

    contract["role_grant_contract"]["final_evidence"] = {
        "application_runtime": {
            **{flag: False for flag in APPLICATION_RUNTIME_FORBIDDEN_FLAGS},
            **_verified_role("production_app_runtime_role"),
        },
        "migration_execution": _verified_role("production_migration_role"),
        "background_worker_or_scheduler": _verified_role("production_worker_role"),
        "read_only_reporting_or_support": _verified_role("production_reporting_role"),
        "backup_or_restore_database_access": _verified_role("production_backup_role"),
        "routine_human_access": _verified_role("production_human_access_role"),
        "schema_or_object_owner": _verified_role("production_schema_owner_role"),
    }
    return contract


@pytest.mark.requirement("WS04-01C-R1", "WS04-01C-R2", "WS04-01C-R5", "WS04-01C-R8")
def test_ws04_01c_contract_is_complete_sanitized_and_provider_neutral() -> None:
    contract = _load_contract()

    assert validate_evidence_contract(contract) == []
    assert set(REQUIRED_METADATA_FIELDS) <= set(contract["metadata"])
    assert set(RUNTIME_TOPOLOGY_FIELDS) <= set(contract["topology_contract"])
    assert contract["owning_pass"] == "WS04-01C"
    assert contract["future_population_owner"] == "WS04-01D"
    assert contract["metadata"]["supported_controls"]["value"] == [
        "DB-002",
        "DB-015",
        "GOV-006",
        "OPS-025",
    ]
    assert contract["metadata"]["raw_evidence_location_reference"]["state"] == "not_applicable"
    assert "outside Git" in contract["metadata"]["raw_evidence_location_reference"]["reason"]
    assert contract["temporary_infrastructure_notice"]["disallowed_final_sources"] == [
        "temporary Neon values",
        "temporary Render values",
        "temporary Vercel values",
        "README examples",
        "local development settings",
        "free-tier limits",
    ]


@pytest.mark.requirement("WS04-01C-R1", "WS04-01C-R2", "WS04-01C-R8")
def test_deferred_c_template_does_not_populate_final_provider_or_budget_values() -> None:
    contract = _load_contract()

    for field in contract["budget_model"]["inputs"].values():
        assert field["evidence_state"] == "deferred_to_ws04_01d"
        assert field["value"] is None

    for field in contract["topology_contract"].values():
        assert field["state"] == "deferred_to_ws04_01d"
        assert field["value"] is None


@pytest.mark.requirement("WS04-01C-R1", "WS04-01C-R5", "WS04-01C-R8")
def test_provider_independent_template_rejects_populated_provider_topology_claims() -> None:
    contract = _load_contract()

    provider_claim = deepcopy(contract)
    provider_claim["metadata"]["provider_or_control_plane"] = {
        "state": "verified",
        "value": "temporary Neon project",
    }
    assert (
        "metadata.provider_or_control_plane must remain deferred to WS04-01D "
        "in provider-independent template"
    ) in validate_evidence_contract(provider_claim)

    topology_claim = deepcopy(contract)
    topology_claim["topology_contract"]["connection_mode"] = {
        "state": "verified",
        "value": "provider_pooler",
    }
    errors = validate_evidence_contract(topology_claim)
    assert (
        "topology_contract.connection_mode must remain deferred to WS04-01D "
        "in provider-independent template"
    ) in errors
    assert "topology_contract.connection_mode.value must be null before WS04-01D" in errors

    final_role_claim = deepcopy(contract)
    final_role_claim["role_grant_contract"]["final_evidence"] = {
        "application_runtime": {"safe_alias": "demo_app_role"}
    }
    assert (
        "role_grant_contract.final_evidence must not be populated before WS04-01D"
    ) in validate_evidence_contract(final_role_claim)


@pytest.mark.requirement("WS04-01C-R1", "WS04-01C-R2", "WS04-01C-R8")
def test_final_d_contract_state_rejects_absent_d_owned_evidence() -> None:
    contract = _load_contract()
    contract["contract_state"] = "ws04_01d_final_evidence"

    errors = validate_evidence_contract(contract)

    assert "metadata.provider_or_control_plane must be verified for final evidence" in errors
    assert "metadata.open_gaps must be empty for final evidence" in errors
    assert (
        "topology_contract.connection_mode must be verified for final evidence"
    ) in errors
    assert "DB_POOL_SIZE final verification cannot use state 'deferred_to_ws04_01d'" in errors
    assert (
        "role_grant_contract.final_evidence must be an object"
    ) in errors


@pytest.mark.requirement("WS04-01C-R1", "WS04-01C-R2", "WS04-01C-R8")
def test_final_d_contract_state_accepts_complete_synthetic_final_evidence() -> None:
    assert validate_evidence_contract(_final_d_contract()) == []


@pytest.mark.requirement("WS04-01C-R1", "WS04-01C-R5", "WS04-01C-R8")
def test_final_d_contract_state_rejects_missing_required_topology() -> None:
    final_contract = _final_d_contract()
    final_contract["topology_contract"]["connection_mode"] = {
        "state": "not_applicable",
        "value": None,
        "reason": "synthetic invalid bypass",
    }
    assert (
        "topology_contract.connection_mode must be verified for final evidence"
    ) in validate_evidence_contract(final_contract)

    pooled = _final_d_contract()
    pooled["topology_contract"]["connection_mode"]["value"] = "provider_pooler"
    pooled["topology_contract"]["pooler_client_connection_ceiling"] = {
        "state": "not_applicable",
        "value": None,
        "reason": "synthetic invalid bypass",
    }
    assert (
        "topology_contract.pooler_client_connection_ceiling must be verified "
        "for final evidence"
    ) in validate_evidence_contract(pooled)

    invalid_mode = _final_d_contract()
    invalid_mode["topology_contract"]["connection_mode"]["value"] = "unknown_pool_mode"
    assert (
        "topology_contract.connection_mode.value is not allowed"
    ) in validate_evidence_contract(invalid_mode)

    bad_not_applicable = _final_d_contract()
    bad_not_applicable["topology_contract"]["pooler_server_connection_ceiling"] = {
        "state": "not_applicable",
        "value": "hidden provider ceiling",
        "reason": "synthetic invalid non-applicable value",
    }
    assert (
        "topology_contract.pooler_server_connection_ceiling "
        "not_applicable value must be omitted"
    ) in validate_evidence_contract(bad_not_applicable)


@pytest.mark.requirement("WS04-01C-R2")
def test_sensitive_provider_or_credential_material_is_rejected() -> None:
    contract = _load_contract()
    unsafe = deepcopy(contract)

    unsafe["metadata"]["sanitized_evidence_reference"]["value"] = (
        "postgresql://app_user:secret@private-db.internal/pickup_lane"
    )
    unsafe["metadata"]["sanitized_evidence_reference"]["state"] = "verified"

    findings = detect_sensitive_values(unsafe)

    assert any("database URL" in finding for finding in findings)
    assert any("credential URL" in finding for finding in findings)


@pytest.mark.requirement("WS04-01C-R2")
def test_private_control_plane_references_and_raw_evidence_are_rejected() -> None:
    contract = _load_contract()
    unsafe = deepcopy(contract)

    unsafe["metadata"]["sanitized_evidence_reference"]["state"] = "verified"
    unsafe["metadata"]["sanitized_evidence_reference"]["value"] = (
        "https://dashboard.neon.tech/app/projects/private-project-123"
    )
    unsafe["metadata"]["raw_evidence_location_reference"] = {
        "state": "verified",
        "value": "raw-log-export.csv",
    }
    unsafe["topology_contract"]["provider_capacity_source"]["state"] = "verified"
    unsafe["topology_contract"]["provider_capacity_source"][
        "value"
    ] = "private-db.internal"
    unsafe["topology_contract"]["api_instance_ceiling"]["value"] = "10.1.2.3"

    findings = detect_sensitive_values(unsafe)

    assert any("private dashboard URL" in finding for finding in findings)
    assert any("provider project/account identifier" in finding for finding in findings)
    assert any("raw evidence reference" in finding for finding in findings)
    assert any("private hostname" in finding for finding in findings)
    assert any("IP address" in finding for finding in findings)


@pytest.mark.requirement("WS04-01C-R2")
def test_sanitized_evidence_references_are_not_flagged_as_sensitive() -> None:
    findings = detect_sensitive_values(
        {
            "provider_summary": "sanitized provider capacity summary",
            "safe_project_alias": "db-provider-alpha",
            "evidence_reference": "ws04-01d-sanitized-capacity-summary",
            "reviewer": "ws04-01d-reviewer",
        }
    )

    assert findings == []


@pytest.mark.requirement("WS04-01C-R2")
def test_personal_and_payment_data_patterns_are_rejected() -> None:
    findings = detect_sensitive_values(
        {
            "reviewer_email": "owner@example.com",
            "payment_card": "4242 4242 4242 4242",
        }
    )

    assert any("personal email" in finding for finding in findings)
    assert any("payment card number" in finding for finding in findings)


@pytest.mark.requirement("WS04-01C-R2")
def test_missing_en03_metadata_fails_contract_validation() -> None:
    contract = _load_contract()
    del contract["metadata"]["purpose"]

    assert "missing metadata.purpose" in validate_evidence_contract(contract)
