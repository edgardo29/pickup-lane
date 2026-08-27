"""Provider-independent migration safety policy for WS04-03A.

This module is declarative. It names the repository-owned migration safety
contract without opening database connections, reading provider state, or
executing Alembic.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MigrationSafetyFamily:
    family_id: str
    owner: str
    requirements: tuple[str, ...]
    accepted_mechanisms: tuple[str, ...]
    representative_sources: tuple[str, ...]
    later_owner: str | None = None


@dataclass(frozen=True)
class MigrationOperationClassification:
    operation_id: str
    requirements: tuple[str, ...]
    current_disposition: str
    required_policy: str


REQUIREMENT_IDS: tuple[str, ...] = tuple(f"WS04-03A-R{index}" for index in range(1, 9))


MIGRATION_SAFETY_FAMILIES: tuple[MigrationSafetyFamily, ...] = (
    MigrationSafetyFamily(
        family_id="development_to_production_history_policy",
        owner="Database owner and Alembic revision history",
        requirements=("WS04-03A-R1", "WS04-03A-R8"),
        accepted_mechanisms=(
            "pre-production clean rebuild remains allowed for current development schema work",
            "production data preservation switches applied migrations to immutable history",
            "future production changes use new forward migrations rather than editing applied history",
            "the transition to immutable history requires an explicit project decision",
        ),
        representative_sources=(
            "docs/agent-notes/database.md",
            "backend/alembic/versions/",
        ),
    ),
    MigrationSafetyFamily(
        family_id="expand_contract_compatibility_window",
        owner="Future schema-change planning and old/new application compatibility",
        requirements=("WS04-03A-R1", "WS04-03A-R5", "WS04-03A-R8"),
        accepted_mechanisms=(
            "compatible expansion before readers or writers require the new shape",
            "application rollout before contraction removes or changes old shape",
            "contraction only after old application behavior is no longer live",
            "unsafe one-step table, column, status, default, and constraint changes fail closed",
        ),
        representative_sources=(
            "backend/alembic/versions/",
            "backend/models/",
            "backend/services/",
            "backend/schemas/",
        ),
        later_owner="WS04-03B owns final rolling-overlap topology proof.",
    ),
    MigrationSafetyFamily(
        family_id="operation_classification",
        owner="Alembic upgrade and downgrade operation inventory",
        requirements=("WS04-03A-R2", "WS04-03A-R8"),
        accepted_mechanisms=(
            "current migration operation inventory is derived from source",
            "upgrade-side destructive and special operations require explicit classification",
            "data-affecting migrations require batching, interruption, resume, and verification design",
            "unclassified risky patterns fail closed",
        ),
        representative_sources=("backend/alembic/versions/",),
    ),
    MigrationSafetyFamily(
        family_id="graph_and_drift_verification",
        owner="Alembic script directory, revision graph, and SQLAlchemy metadata",
        requirements=("WS04-03A-R3", "WS04-03A-R8"),
        accepted_mechanisms=(
            "one expected base and one expected head for the current chain",
            "revision metadata has no duplicates, missing links, orphaned revisions, or unexpected branches",
            "model metadata imports before drift comparison",
            "drift verification runs as trusted test evidence",
        ),
        representative_sources=(
            "backend/alembic/env.py",
            "backend/alembic/versions/",
            "backend/models/",
        ),
    ),
    MigrationSafetyFamily(
        family_id="empty_and_prior_schema_upgrades",
        owner="Dedicated migration lifecycle test database",
        requirements=("WS04-03A-R4", "WS04-03A-R7", "WS04-03A-R8"),
        accepted_mechanisms=(
            "ordinary backend tests use pickup_lane_test_db through DATABASE_URL",
            "migration lifecycle tests use pickup_lane_migration_test_db through MIGRATION_DATABASE_URL",
            "migration test database is reset to a genuine empty migration state",
            "controlled prior revision is built from repository-owned migrations before upgrade to head",
            "upgrade-to-head rerun is idempotent on an already-upgraded migration database",
        ),
        representative_sources=(
            "backend/settings.py",
            "backend/tests/support/environment_safety.py",
            "backend/tests/migrations/",
        ),
    ),
    MigrationSafetyFamily(
        family_id="timeout_lock_interruption_resume_forward_fix",
        owner="Provider-independent migration execution rehearsal",
        requirements=("WS04-03A-R6", "WS04-03A-R7", "WS04-03A-R8"),
        accepted_mechanisms=(
            "migration runs use Alembic migration connections rather than the application request pool",
            "destructive migration test setup validates exact database identity before connecting",
            "migration lifecycle tests serialize with a dedicated advisory lock",
            "interrupted rehearsal state is inspectable and recoverable in the dedicated migration database",
            "forward-fix remains the preferred production recovery posture for data-preserving environments",
        ),
        representative_sources=(
            "backend/alembic/env.py",
            "backend/tests/support/migration_test_database.py",
            "backend/tests/migrations/",
        ),
        later_owner="WS04-03B owns final provider lock behavior and runtime ceilings.",
    ),
    MigrationSafetyFamily(
        family_id="controlled_rehearsal_evidence",
        owner="Trusted migration tests and testing record",
        requirements=("WS04-03A-R7", "WS04-03A-R8"),
        accepted_mechanisms=(
            "controlled PostgreSQL evidence records provider-independent observations",
            "synthetic fixtures exercise safe and unsafe migration policy examples",
            "large-data migration requirements fail closed when future migrations introduce them",
            "testing record separates local evidence from final provider/runtime proof",
        ),
        representative_sources=(
            "backend/tests/migrations/migration_policy_compatibility_rehearsal/",
            "backend/tests/support/requirements/ws04_03a.json",
        ),
    ),
    MigrationSafetyFamily(
        family_id="deferred_final_provider_runtime_rehearsal",
        owner="Mandatory deferred WS04-03B follow-up",
        requirements=("WS04-03A-R1", "WS04-03A-R8"),
        accepted_mechanisms=(
            "final provider/runtime migration ceilings remain deferred",
            "production-equivalent volume remains deferred",
            "final migration runner and rolling-overlap topology remain deferred",
            "final provider lock/runtime behavior and rollout evidence remain deferred",
        ),
        representative_sources=(
            "docs/production-readiness/planning/passes/ws04/ws04-03-intake.md",
            "docs/production-readiness/planning/program/PASS-EXECUTION-REGISTER.md",
        ),
        later_owner="WS04-03B after final production database provider, deployment topology, migration runner, and production-equivalent rehearsal inputs are selected.",
    ),
)


MIGRATION_OPERATION_CLASSIFICATIONS: tuple[MigrationOperationClassification, ...] = (
    MigrationOperationClassification(
        operation_id="extension_setup",
        requirements=("WS04-03A-R2", "WS04-03A-R7"),
        current_disposition="allowed when fixed and reviewed",
        required_policy="classify extension setup and preserve provider-specific permission proof for WS04-03B or WS04-01D when final infrastructure is selected",
    ),
    MigrationOperationClassification(
        operation_id="sequence_setup",
        requirements=("WS04-03A-R2", "WS04-03A-R7"),
        current_disposition="allowed when fixed and owned by the current schema chain",
        required_policy="classify sequence setup and verify empty/prior-schema upgrade behavior",
    ),
    MigrationOperationClassification(
        operation_id="table_creation",
        requirements=("WS04-03A-R2", "WS04-03A-R5"),
        current_disposition="allowed for current canonical table migrations",
        required_policy="new table creation remains compatible when it does not remove or change old application-visible schema",
    ),
    MigrationOperationClassification(
        operation_id="ordinary_index_and_constraint_creation",
        requirements=("WS04-03A-R2", "WS04-03A-R5", "WS04-03A-R6"),
        current_disposition="allowed when non-destructive and reviewed",
        required_policy="blocking or special index/constraint behavior requires explicit classification before merge",
    ),
    MigrationOperationClassification(
        operation_id="raw_sql_expression",
        requirements=("WS04-03A-R2", "WS04-03A-R8"),
        current_disposition="allowed only when fixed and reviewed",
        required_policy="dynamic SQL, interpolated values, and unallowlisted identifiers fail closed",
    ),
    MigrationOperationClassification(
        operation_id="destructive_schema_change",
        requirements=("WS04-03A-R2", "WS04-03A-R5", "WS04-03A-R8"),
        current_disposition="not present in current upgrade-side inventory",
        required_policy="drop, rename, type-change, and narrowing changes require expand/contract design or Gate A redesign",
    ),
    MigrationOperationClassification(
        operation_id="data_rewrite_or_backfill",
        requirements=("WS04-03A-R2", "WS04-03A-R6", "WS04-03A-R7"),
        current_disposition="not present in current upgrade-side inventory",
        required_policy="data-affecting migrations require batching, interruption, resume, verification, and forward-fix design before merge",
    ),
    MigrationOperationClassification(
        operation_id="special_transaction_or_concurrent_operation",
        requirements=("WS04-03A-R2", "WS04-03A-R6", "WS04-03A-R8"),
        current_disposition="not present in current upgrade-side inventory",
        required_policy="manual transaction handling, concurrent indexes, NOT VALID, and VALIDATE flows require explicit policy and proof",
    ),
)


UNSAFE_ONE_STEP_SCHEMA_CHANGES: tuple[str, ...] = (
    "drop_currently_used_table",
    "drop_currently_used_column",
    "rename_currently_used_table_or_column",
    "change_currently_used_column_type",
    "add_non_null_requirement_without_expansion",
    "change_status_default_without_old_new_compatibility",
    "data_rewrite_without_batching_interruption_resume_and_verification",
)


LATER_OWNED_MIGRATION_EVIDENCE: dict[str, str] = {
    "WS04-01D": (
        "Final production PostgreSQL topology, connection budget, concrete "
        "roles/grants, and final migration-role evidence."
    ),
    "WS04-03B": (
        "Final provider/runtime migration rehearsal, production-equivalent "
        "volume, runtime ceilings, migration runner, rolling-overlap topology, "
        "provider lock behavior, and rollout evidence."
    ),
    "WS05": "Durable jobs, payment/provider lifecycle, worker execution, and reconciliation.",
    "WS09": "Deployed logs, metrics, dashboards, alerts, and operational visibility.",
    "WS10": "Backup/PITR, restore exercises, incident response, and recovery operations.",
}
