from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from backend.tests.support.production_database_verification import (
    APPLICATION_RUNTIME_FORBIDDEN_FLAGS,
    FINAL_ROLE_EVIDENCE_CHECKS,
    ROLE_CHECKS,
    ROLE_CLASSES,
    validate_final_role_grant_evidence,
    validate_role_grant_contract,
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
        "purpose": "prove deterministic role/grant validator behavior",
        "supported_control_or_pass": "WS04-01C",
        "sanitized_evidence_reference": "synthetic-test-only",
    }


def _verified_role(alias: str) -> dict:
    return {
        "state": "verified",
        "safe_alias": alias,
        "completed_checks": list(FINAL_ROLE_EVIDENCE_CHECKS),
        "evidence": _source_metadata(),
    }


def _final_role_record() -> dict:
    record = _load_contract()
    record["role_grant_contract"]["final_evidence"] = {
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
    return record


@pytest.mark.requirement("WS04-01C-R2", "WS04-01C-R6", "WS04-01C-R8")
def test_role_grant_contract_requires_complete_role_and_privilege_inventory() -> None:
    contract = _load_contract()

    assert validate_role_grant_contract(contract) == []
    assert set(ROLE_CLASSES) == set(contract["role_grant_contract"]["role_classes"])
    assert set(ROLE_CHECKS) == set(contract["role_grant_contract"]["required_checks"])
    assert contract["role_grant_contract"]["migration_role_separation_required"] is True


@pytest.mark.requirement("WS04-01C-R6")
def test_final_role_evidence_rejects_broad_application_privilege() -> None:
    record = _final_role_record()
    privileged = deepcopy(record)
    privileged["role_grant_contract"]["final_evidence"]["application_runtime"]["superuser"] = True

    assert "application runtime role must not have superuser" in validate_final_role_grant_evidence(
        privileged
    )


@pytest.mark.requirement("WS04-01C-R6")
def test_final_role_evidence_rejects_shared_application_and_migration_role() -> None:
    record = _final_role_record()
    shared = deepcopy(record)
    shared["role_grant_contract"]["final_evidence"]["migration_execution"][
        "safe_alias"
    ] = "production_app_runtime_role"

    assert "application and migration effective roles must be distinct" in validate_final_role_grant_evidence(
        shared
    )


@pytest.mark.requirement("WS04-01C-R6")
def test_final_role_evidence_requires_ownership_search_path_and_default_privileges() -> None:
    record = _final_role_record()
    incomplete = deepcopy(record)
    incomplete["role_grant_contract"]["final_evidence"]["application_runtime"][
        "completed_checks"
    ].remove("default_privileges")

    assert (
        "application_runtime final role evidence missing completed check: "
        "default_privileges"
    ) in validate_final_role_grant_evidence(
        incomplete
    )


@pytest.mark.requirement("WS04-01C-R6", "WS04-01C-R8")
def test_final_role_evidence_requires_every_role_class_disposition() -> None:
    record = _final_role_record()
    missing_reporting = deepcopy(record)
    del missing_reporting["role_grant_contract"]["final_evidence"][
        "read_only_reporting_or_support"
    ]

    assert (
        "role_grant_contract.final_evidence.read_only_reporting_or_support "
        "must be an object"
    ) in validate_final_role_grant_evidence(missing_reporting)

    missing_schema_owner = deepcopy(record)
    missing_schema_owner["role_grant_contract"]["final_evidence"]["schema_or_object_owner"] = {
        "state": "not_applicable",
        "reason": "synthetic invalid absence",
    }
    assert (
        "schema_or_object_owner final role evidence cannot be not_applicable"
    ) in validate_final_role_grant_evidence(missing_schema_owner)


@pytest.mark.requirement("WS04-01C-R6")
def test_final_role_evidence_requires_migration_grant_search_path_and_default_proof() -> None:
    record = _final_role_record()
    incomplete_migration = deepcopy(record)
    incomplete_migration["role_grant_contract"]["final_evidence"]["migration_execution"][
        "completed_checks"
    ].remove("search_path")

    assert (
        "migration_execution final role evidence missing completed check: search_path"
    ) in validate_final_role_grant_evidence(incomplete_migration)
