"""Current database value/default and SQL-safety policy for WS04-02C.

This module is declarative. It names the current repository-owned database
value surface, accepted SQL construction patterns, and later-owned evidence
boundaries without opening database connections, reading provider state, or
executing runtime workflows.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DatabaseValueSqlSafetyFamily:
    family_id: str
    owner: str
    requirements: tuple[str, ...]
    accepted_mechanisms: tuple[str, ...]
    representative_sources: tuple[str, ...]
    later_owner: str | None = None


@dataclass(frozen=True)
class RawSqlAllowance:
    source_path: str
    constructor: str
    expression: str
    safety_basis: str


REQUIREMENT_IDS: tuple[str, ...] = tuple(f"WS04-02C-R{index}" for index in range(1, 9))

DATABASE_VALUE_SQL_SAFETY_FAMILIES: tuple[DatabaseValueSqlSafetyFamily, ...] = (
    DatabaseValueSqlSafetyFamily(
        family_id="timestamp_and_update_timestamps",
        owner="SQLAlchemy models, PostgreSQL defaults, and service-owned state transitions",
        requirements=("WS04-02C-R1", "WS04-02C-R2", "WS04-02C-R8"),
        accepted_mechanisms=(
            "DateTime(timezone=True) for persisted datetimes",
            "PostgreSQL now() server defaults for creation and initial update timestamps",
            "datetime.now(timezone.utc) for deliberate service-owned updates",
            "no datetime.utcnow(), naive datetime.now(), bare DateTime(), or implicit onupdate",
        ),
        representative_sources=(
            "backend/models/",
            "backend/alembic/versions/",
            "backend/services/",
            "backend/schemas/",
        ),
    ),
    DatabaseValueSqlSafetyFamily(
        family_id="money_currency_and_amounts",
        owner="Money-bearing models, services, schemas, and Stripe adapter boundary",
        requirements=("WS04-02C-R1", "WS04-02C-R3", "WS04-02C-R8"),
        accepted_mechanisms=(
            "integer cents for programmatic money values",
            "USD-only database constraints or service validation for current money tables",
            "Stripe adapter receives integer cents and lower-case provider currency",
            "no float conversion for provider-facing amounts",
        ),
        representative_sources=(
            "backend/models/booking_model.py",
            "backend/models/payment_model.py",
            "backend/models/refund_model.py",
            "backend/models/game_credit_model.py",
            "backend/models/game_credit_usage_model.py",
            "backend/models/host_publish_fee_model.py",
            "backend/models/money_issue_model.py",
            "backend/services/stripe_service.py",
        ),
    ),
    DatabaseValueSqlSafetyFamily(
        family_id="status_defaults_and_state_machines",
        owner="Model defaults, check constraints, service constants, and response schemas",
        requirements=("WS04-02C-R1", "WS04-02C-R4", "WS04-02C-R8"),
        accepted_mechanisms=(
            "database status defaults are values accepted by current constraints",
            "service-set lifecycle states stay within current model constraints",
            "schemas expose current state values without creating new product states",
        ),
        representative_sources=(
            "backend/models/",
            "backend/alembic/versions/",
            "backend/services/",
            "backend/schemas/",
        ),
    ),
    DatabaseValueSqlSafetyFamily(
        family_id="json_defaults_and_payload_shapes",
        owner="JSON/JSONB models, service payload builders, and Pydantic schema defaults",
        requirements=("WS04-02C-R1", "WS04-02C-R5", "WS04-02C-R7", "WS04-02C-R8"),
        accepted_mechanisms=(
            "server-side JSON defaults only where the database owns row creation defaults",
            "Pydantic default_factory for mutable request defaults",
            "raw provider payload storage limited to accepted current event surfaces",
            "no raw JSON payload logging or unrelated exposure",
        ),
        representative_sources=(
            "backend/models/community_game_detail_model.py",
            "backend/models/payment_event_model.py",
            "backend/models/admin_action_model.py",
            "backend/schemas/community_game_detail_schema.py",
            "backend/services/payment_event_service.py",
        ),
        later_owner="WS05 owns full provider event lifecycle and reconciliation proof.",
    ),
    DatabaseValueSqlSafetyFamily(
        family_id="production_raw_sql",
        owner="Repository-owned production source that executes raw SQL expressions",
        requirements=("WS04-02C-R1", "WS04-02C-R6", "WS04-02C-R8"),
        accepted_mechanisms=(
            "fixed health-check SQL",
            "fixed PostgreSQL timeout/advisory-lock/sequence calls with bound parameters or fixed identifiers",
            "fixed platform-notice search expression with no user-controlled identifiers",
            "SQLAlchemy expression APIs for ordinary filters, ordering, indexes, and constraints",
        ),
        representative_sources=(
            "backend/database.py",
            "backend/services/chat_rate_limit_service.py",
            "backend/services/platform_notice_service.py",
        ),
    ),
    DatabaseValueSqlSafetyFamily(
        family_id="migration_sql_expressions",
        owner="Canonical Alembic migrations where SQL affects values, defaults, or SQL safety",
        requirements=("WS04-02C-R1", "WS04-02C-R6", "WS04-02C-R8"),
        accepted_mechanisms=(
            "fixed extension setup",
            "fixed sequence setup",
            "fixed SQLAlchemy/Alembic expressions for defaults, checks, and indexes",
            "no interpolated migration SQL or production-like migration rehearsal claim",
        ),
        representative_sources=("backend/alembic/versions/",),
        later_owner="WS04-03 owns migration graph, drift, interruption, expand/contract policy, and production-like rehearsal.",
    ),
    DatabaseValueSqlSafetyFamily(
        family_id="sql_and_value_logging_safety",
        owner="Application logging around database, provider, admin, payment, and moderation workflows",
        requirements=("WS04-02C-R1", "WS04-02C-R7", "WS04-02C-R8"),
        accepted_mechanisms=(
            "no SQLAlchemy echo=True in production source",
            "no intentional logging of raw SQL bound values",
            "no raw provider payload, credential, payment card, personal-data, or unbounded text logging",
            "safe event envelopes, stable error codes, IDs, categories, and sanitized metadata remain allowed",
        ),
        representative_sources=(
            "backend/database.py",
            "backend/settings.py",
            "backend/services/",
            "backend/routes/",
            "backend/observability/",
        ),
        later_owner="WS09 and WS10 own deployed log aggregation, provider logs, dashboard, alert, and operational access evidence.",
    ),
    DatabaseValueSqlSafetyFamily(
        family_id="accepted_database_contract_boundaries",
        owner="Accepted WS04-01A/B/C and WS04-02A/B database contracts",
        requirements=("WS04-02C-R8",),
        accepted_mechanisms=(
            "no change to request-session cleanup, pool/timeout settings, or credential boundary",
            "no change to query/cursor behavior or production database verification deferrals",
            "no change to transaction checkpoints, provider unknown-outcome handling, row locks, or concurrency invariants",
            "no final production infrastructure value claimed by WS04-02C",
        ),
        representative_sources=(
            "backend/services/transaction_boundary_policy.py",
            "backend/services/database_invariant_policy.py",
            "backend/tests/workflows/application_database_lifecycle_pool_settings_role_credential_boundaries/",
            "backend/tests/workflows/query_cursor_database_access_behavior/",
            "backend/tests/platform/production_database_verification/",
            "backend/tests/workflows/transaction_boundary_external_side_effect_safety/",
            "backend/tests/workflows/database_invariants_locks_deterministic_concurrency/",
        ),
        later_owner="WS04-01D owns final production PostgreSQL topology, numeric connection budget, concrete roles, and final provider/runtime proof.",
    ),
)

PRODUCTION_RAW_SQL_ALLOWLIST: tuple[RawSqlAllowance, ...] = (
    RawSqlAllowance(
        source_path="backend/database.py",
        constructor="dbapi.execute",
        expression="SELECT set_config('statement_timeout', %s, false)",
        safety_basis="fixed PostgreSQL setting name with a bound, typed timeout value",
    ),
    RawSqlAllowance(
        source_path="backend/database.py",
        constructor="dbapi.execute",
        expression="SELECT set_config('lock_timeout', %s, false)",
        safety_basis="fixed PostgreSQL setting name with a bound, typed timeout value",
    ),
    RawSqlAllowance(
        source_path="backend/database.py",
        constructor="sqlalchemy.text",
        expression="SELECT 1",
        safety_basis="fixed health-check expression with no identifiers or values from users",
    ),
    RawSqlAllowance(
        source_path="backend/services/chat_rate_limit_service.py",
        constructor="sqlalchemy.text",
        expression="SELECT pg_advisory_xact_lock(:lock_key)",
        safety_basis="fixed advisory-lock function with a named bound parameter",
    ),
    RawSqlAllowance(
        source_path="backend/services/platform_notice_service.py",
        constructor="sqlalchemy.literal_column",
        expression="NOTICE_HISTORY_SEARCH_EXPRESSION_SQL",
        safety_basis="fixed module constant using only platform-notice table columns",
    ),
    RawSqlAllowance(
        source_path="backend/services/platform_notice_service.py",
        constructor="sqlalchemy.text",
        expression="SELECT nextval('platform_notice_global_sequence_seq')",
        safety_basis="fixed sequence name owned by canonical migration",
    ),
)

MIGRATION_RAW_SQL_ALLOWLIST: tuple[RawSqlAllowance, ...] = (
    RawSqlAllowance(
        source_path="backend/alembic/versions/0001_enable_pg_trgm_extension.py",
        constructor="op.execute",
        expression="CREATE EXTENSION IF NOT EXISTS pg_trgm",
        safety_basis="fixed extension setup for search indexes",
    ),
    RawSqlAllowance(
        source_path="backend/alembic/versions/0001_enable_pg_trgm_extension.py",
        constructor="op.execute",
        expression="DROP EXTENSION IF EXISTS pg_trgm",
        safety_basis="fixed extension teardown in downgrade",
    ),
    RawSqlAllowance(
        source_path="backend/alembic/versions/0006_create_platform_notices_table.py",
        constructor="op.execute",
        expression="CREATE SEQUENCE platform_notice_global_sequence_seq",
        safety_basis="fixed sequence setup for platform-notice ordering",
    ),
    RawSqlAllowance(
        source_path="backend/alembic/versions/0006_create_platform_notices_table.py",
        constructor="op.execute",
        expression="DROP SEQUENCE platform_notice_global_sequence_seq",
        safety_basis="fixed sequence teardown in downgrade",
    ),
)

LATER_OWNED_EVIDENCE: dict[str, str] = {
    "WS04-01D": "final production PostgreSQL topology/provider, connection budget, concrete roles/grants, and runtime proof",
    "WS04-03": "migration graph, drift, interruption, expand/contract policy, and production-like migration rehearsal",
    "WS05": "durable jobs, payment/provider lifecycle, webhook authority, reconciliation, and worker execution",
    "WS09": "deployed structured logging, log aggregation, dashboards, alerts, metrics, and provider log access",
    "WS10": "operational privacy, retention, provider control-plane, incident, backup, restore, and access evidence",
}


def raw_sql_allowlist_keys() -> set[tuple[str, str, str]]:
    return {
        (entry.source_path, entry.constructor, entry.expression)
        for entry in PRODUCTION_RAW_SQL_ALLOWLIST
    }


def migration_raw_sql_allowlist_keys() -> set[tuple[str, str, str]]:
    return {
        (entry.source_path, entry.constructor, entry.expression)
        for entry in MIGRATION_RAW_SQL_ALLOWLIST
    }
