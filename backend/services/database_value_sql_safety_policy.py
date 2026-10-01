"""Semantic map of current database value/default and SQL safety.

The map names the repository-owned database value surface and accepted SQL
construction patterns without opening database connections, reading provider
state, or executing runtime workflows.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DatabaseValueSqlSafetyFamily:
    family_id: str
    owner: str
    accepted_mechanisms: tuple[str, ...]
    representative_sources: tuple[str, ...]


@dataclass(frozen=True)
class RawSqlAllowance:
    source_path: str
    constructor: str
    expression: str
    safety_basis: str


DATABASE_VALUE_SQL_SAFETY_FAMILIES: tuple[DatabaseValueSqlSafetyFamily, ...] = (
    DatabaseValueSqlSafetyFamily(
        family_id="timestamp_and_update_timestamps",
        owner="SQLAlchemy models, PostgreSQL defaults, and service-owned state transitions",
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
    ),
    DatabaseValueSqlSafetyFamily(
        family_id="production_raw_sql",
        owner="Repository-owned production source that executes raw SQL expressions",
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
        accepted_mechanisms=(
            "fixed extension setup",
            "fixed sequence setup",
            "fixed SQLAlchemy/Alembic expressions for defaults, checks, and indexes",
            "no interpolated migration SQL",
        ),
        representative_sources=("backend/alembic/versions/",),
    ),
    DatabaseValueSqlSafetyFamily(
        family_id="sql_and_value_logging_safety",
        owner="Application logging around database, provider, admin, payment, and moderation workflows",
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
    RawSqlAllowance(
        source_path="backend/alembic/versions/0004_create_admin_actions_table.py",
        constructor="op.execute",
        expression="""
        CREATE FUNCTION prevent_admin_actions_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION USING
                ERRCODE = '55000',
                MESSAGE = 'admin audit rows are immutable';
        END;
        $$
        """,
        safety_basis="fixed append-only guard function for administrative audit rows",
    ),
    RawSqlAllowance(
        source_path="backend/alembic/versions/0004_create_admin_actions_table.py",
        constructor="op.execute",
        expression="""
        CREATE TRIGGER trg_admin_actions_immutable
        BEFORE UPDATE OR DELETE ON admin_actions
        FOR EACH ROW
        EXECUTE FUNCTION prevent_admin_actions_mutation()
        """,
        safety_basis="fixed append-only trigger for administrative audit rows",
    ),
    RawSqlAllowance(
        source_path="backend/alembic/versions/0004_create_admin_actions_table.py",
        constructor="op.execute",
        expression="DROP TRIGGER trg_admin_actions_immutable ON admin_actions",
        safety_basis="fixed append-only trigger teardown in downgrade",
    ),
    RawSqlAllowance(
        source_path="backend/alembic/versions/0004_create_admin_actions_table.py",
        constructor="op.execute",
        expression="DROP FUNCTION prevent_admin_actions_mutation()",
        safety_basis="fixed append-only guard teardown in downgrade",
    ),
    RawSqlAllowance(
        source_path="backend/alembic/versions/0045_create_admin_rejected_attempts_table.py",
        constructor="op.execute",
        expression="""
        CREATE FUNCTION prevent_admin_rejected_attempts_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION USING
                ERRCODE = '55000',
                MESSAGE = 'admin audit rows are immutable';
        END;
        $$
        """,
        safety_basis="fixed append-only guard function for rejected audit attempts",
    ),
    RawSqlAllowance(
        source_path="backend/alembic/versions/0045_create_admin_rejected_attempts_table.py",
        constructor="op.execute",
        expression="""
        CREATE TRIGGER trg_admin_rejected_attempts_immutable
        BEFORE UPDATE OR DELETE ON admin_rejected_attempts
        FOR EACH ROW
        EXECUTE FUNCTION prevent_admin_rejected_attempts_mutation()
        """,
        safety_basis="fixed append-only trigger for rejected audit attempts",
    ),
    RawSqlAllowance(
        source_path="backend/alembic/versions/0045_create_admin_rejected_attempts_table.py",
        constructor="op.execute",
        expression="DROP TRIGGER trg_admin_rejected_attempts_immutable ON admin_rejected_attempts",
        safety_basis="fixed rejected-attempt trigger teardown in downgrade",
    ),
    RawSqlAllowance(
        source_path="backend/alembic/versions/0045_create_admin_rejected_attempts_table.py",
        constructor="op.execute",
        expression="DROP FUNCTION prevent_admin_rejected_attempts_mutation()",
        safety_basis="fixed rejected-attempt guard teardown in downgrade",
    ),
)

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
