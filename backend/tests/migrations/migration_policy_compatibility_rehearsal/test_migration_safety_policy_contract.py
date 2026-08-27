from __future__ import annotations

import json
from pathlib import Path

import pytest

import backend.services.database_migration_safety_policy as migration_policy

pytestmark = pytest.mark.no_db_cleanup

_REPO_ROOT = Path(__file__).resolve().parents[4]
_REQUIREMENT_IDS = {f"WS04-03A-R{index}" for index in range(1, 9)}


def _source(relative_path: str) -> str:
    return (_REPO_ROOT / relative_path).read_text()


@pytest.mark.requirement("WS04-03A-R1", "WS04-03A-R8")
def test_migration_safety_policy_declares_complete_provider_independent_scope() -> None:
    families = migration_policy.MIGRATION_SAFETY_FAMILIES
    family_ids = [family.family_id for family in families]

    assert family_ids == [
        "development_to_production_history_policy",
        "expand_contract_compatibility_window",
        "operation_classification",
        "graph_and_drift_verification",
        "empty_and_prior_schema_upgrades",
        "timeout_lock_interruption_resume_forward_fix",
        "controlled_rehearsal_evidence",
        "deferred_final_provider_runtime_rehearsal",
    ]
    assert len(family_ids) == len(set(family_ids))

    covered_requirements = {
        requirement_id
        for family in families
        for requirement_id in family.requirements
    }
    assert covered_requirements == _REQUIREMENT_IDS

    for family in families:
        assert family.owner
        assert family.accepted_mechanisms
        assert family.representative_sources
        assert all(requirement_id in _REQUIREMENT_IDS for requirement_id in family.requirements)


@pytest.mark.requirement("WS04-03A-R2", "WS04-03A-R5", "WS04-03A-R6", "WS04-03A-R7")
def test_operation_policy_classifies_current_and_future_migration_risks() -> None:
    classifications = migration_policy.MIGRATION_OPERATION_CLASSIFICATIONS
    operation_ids = [classification.operation_id for classification in classifications]

    assert operation_ids == [
        "extension_setup",
        "sequence_setup",
        "table_creation",
        "ordinary_index_and_constraint_creation",
        "raw_sql_expression",
        "destructive_schema_change",
        "data_rewrite_or_backfill",
        "special_transaction_or_concurrent_operation",
    ]
    assert len(operation_ids) == len(set(operation_ids))

    required_unsafe_changes = {
        "drop_currently_used_table",
        "drop_currently_used_column",
        "rename_currently_used_table_or_column",
        "change_currently_used_column_type",
        "add_non_null_requirement_without_expansion",
        "change_status_default_without_old_new_compatibility",
        "data_rewrite_without_batching_interruption_resume_and_verification",
    }
    assert set(migration_policy.UNSAFE_ONE_STEP_SCHEMA_CHANGES) == required_unsafe_changes

    for classification in classifications:
        assert classification.current_disposition
        assert classification.required_policy
        assert all(
            requirement_id in _REQUIREMENT_IDS
            for requirement_id in classification.requirements
        )


@pytest.mark.requirement("WS04-03A-R1", "WS04-03A-R8")
def test_policy_preserves_final_provider_and_later_owner_boundaries() -> None:
    rendered_policy = repr(migration_policy.MIGRATION_SAFETY_FAMILIES)
    later_evidence = migration_policy.LATER_OWNED_MIGRATION_EVIDENCE

    assert set(later_evidence) == {"WS04-01D", "WS04-03B", "WS05", "WS09", "WS10"}
    assert "Final production PostgreSQL topology" in later_evidence["WS04-01D"]
    assert "Final provider/runtime migration rehearsal" in later_evidence["WS04-03B"]
    assert "Durable jobs" in later_evidence["WS05"]
    assert "Deployed logs" in later_evidence["WS09"]
    assert "Backup/PITR" in later_evidence["WS10"]

    assert "postgresql" + "://" not in rendered_policy
    assert "Neon" not in rendered_policy
    assert "Render" not in rendered_policy
    assert "Vercel" not in rendered_policy


@pytest.mark.requirement("WS04-03A-R1", "WS04-03A-R8")
def test_requirement_declaration_matches_frozen_ws04_03a_scope() -> None:
    declaration = json.loads(
        _source("backend/tests/support/requirements/ws04_03a.json")
    )

    requirements = declaration["requirements"]
    assert declaration["schema_version"] == 1
    assert {requirement["id"] for requirement in requirements} == _REQUIREMENT_IDS
    assert {requirement["owning_pass"] for requirement in requirements} == {"WS04-03A"}
    assert {requirement["state"] for requirement in requirements} == {"required"}
    assert {
        requirement["scope"]
        for requirement in requirements
    } == {"migrations/migration_policy_compatibility_rehearsal"}
