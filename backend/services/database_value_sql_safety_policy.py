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
    RawSqlAllowance(
        source_path="backend/alembic/versions/0053_create_admin_review_cases_table.py",
        constructor="op.execute",
        expression="""
        CREATE FUNCTION reject_admin_review_case_identity_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF NEW.case_type IS DISTINCT FROM OLD.case_type
               OR NEW.case_category IS DISTINCT FROM OLD.case_category
               OR NEW.target_user_id IS DISTINCT FROM OLD.target_user_id
               OR NEW.target_game_id IS DISTINCT FROM OLD.target_game_id
               OR NEW.target_sub_post_id IS DISTINCT FROM OLD.target_sub_post_id
               OR NEW.target_sub_post_request_id
                    IS DISTINCT FROM OLD.target_sub_post_request_id
               OR NEW.target_payment_id IS DISTINCT FROM OLD.target_payment_id
               OR NEW.target_financial_outcome_id
                    IS DISTINCT FROM OLD.target_financial_outcome_id THEN
                RAISE EXCEPTION 'admin review case identity is immutable';
            END IF;
            RETURN NEW;
        END;
        $$
    """,
        safety_basis="fixed review-case identity immutability trigger function",
    ),
    RawSqlAllowance(
        source_path="backend/alembic/versions/0053_create_admin_review_cases_table.py",
        constructor="op.execute",
        expression="""
        CREATE TRIGGER trg_admin_review_cases_identity_immutable
        BEFORE UPDATE ON admin_review_cases
        FOR EACH ROW EXECUTE FUNCTION reject_admin_review_case_identity_mutation()
    """,
        safety_basis="fixed review-case identity immutability trigger",
    ),
    RawSqlAllowance(
        source_path="backend/alembic/versions/0053_create_admin_review_cases_table.py",
        constructor="op.execute",
        expression=(
            "DROP TRIGGER trg_admin_review_cases_identity_immutable "
            "ON admin_review_cases"
        ),
        safety_basis="fixed review-case identity trigger teardown",
    ),
    RawSqlAllowance(
        source_path="backend/alembic/versions/0053_create_admin_review_cases_table.py",
        constructor="op.execute",
        expression="DROP FUNCTION reject_admin_review_case_identity_mutation()",
        safety_basis="fixed review-case identity function teardown",
    ),
    RawSqlAllowance(
        source_path="backend/alembic/versions/0059_create_admin_review_case_events_table.py",
        constructor="op.execute",
        expression=r"""
        CREATE FUNCTION validate_admin_review_case_event_insert()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE
            metadata_keys text[];
            nested_keys text[];
            metadata_field text;
            child_case_id uuid;
            child_finding_type text;
            child_risk_area text;
            child_source_field text;
            child_priority text;
            child_current boolean;
            child_source text;
            child_signal_status text;
            child_signal_metadata jsonb;
            child_target_user_id uuid;
            child_target_game_id uuid;
            child_target_sub_post_id uuid;
            child_target_sub_post_request_id uuid;
            child_target_payment_id uuid;
            child_target_financial_outcome_id uuid;
            child_corrects_note_id uuid;
            child_note_author_id uuid;
            child_note_status text;
            child_note_edited_at timestamptz;
            child_note_deleted_at timestamptz;
            action_actor_id uuid;
            action_type_value text;
            action_case_id uuid;
            action_reason text;
            action_metadata jsonb;
            action_target_user_id uuid;
            action_target_game_id uuid;
            action_target_sub_post_id uuid;
            action_target_sub_post_request_id uuid;
            action_target_payment_id uuid;
            action_target_financial_outcome_id uuid;
            prior_event_sequence integer;
            prior_source_priority text;
            derived_priority text;
            prior_child_event_type text;
            prior_effective_assignee_id uuid;
            latest_lifecycle_event_id uuid;
            owner_case admin_review_cases%ROWTYPE;
            related_case admin_review_cases%ROWTYPE;
            related_event admin_review_case_events%ROWTYPE;
        BEGIN
            IF NEW.event_type NOT IN (
                'case_created', 'signal_attached', 'finding_attached',
                'finding_cleared', 'signal_superseded', 'signal_reactivated',
                'note_added', 'assignment_changed',
                'enforcement_action_linked', 'closed', 'reopened',
                'merged_into', 'merged_from'
            )
               OR NEW.actor_kind NOT IN ('admin', 'automation')
               OR (NEW.event_type = 'note_added' AND NEW.note_id IS NULL) THEN
                RETURN NEW;
            END IF;
            IF EXISTS (
                SELECT 1
                FROM admin_review_case_events
                WHERE review_case_id = NEW.review_case_id
                  AND event_sequence = NEW.event_sequence
            ) THEN
                RETURN NEW;
            END IF;
            IF NEW.event_metadata IS NULL
               OR jsonb_typeof(NEW.event_metadata) <> 'object' THEN
                RAISE EXCEPTION 'review case event metadata must be an object';
            END IF;

            SELECT array_agg(key ORDER BY key)
            INTO metadata_keys
            FROM jsonb_object_keys(NEW.event_metadata) AS key;

            IF NEW.event_type = 'case_created' THEN
                IF metadata_keys IS DISTINCT FROM ARRAY['source']
                   OR jsonb_typeof(NEW.event_metadata->'source') <> 'string'
                   OR btrim(NEW.event_metadata->>'source') = '' THEN
                    RAISE EXCEPTION 'invalid case_created event metadata';
                END IF;
            ELSIF NEW.event_type IN ('finding_attached', 'finding_cleared') THEN
                IF metadata_keys IS DISTINCT FROM ARRAY[
                    'finding_type', 'priority_after', 'priority_before',
                    'risk_area', 'source_field'
                ]
                   OR jsonb_typeof(NEW.event_metadata->'finding_type') <> 'string'
                   OR jsonb_typeof(NEW.event_metadata->'risk_area') <> 'string'
                   OR jsonb_typeof(NEW.event_metadata->'source_field') <> 'string'
                   OR jsonb_typeof(NEW.event_metadata->'priority_before') <> 'string'
                   OR jsonb_typeof(NEW.event_metadata->'priority_after') <> 'string'
                   OR NEW.event_metadata->>'priority_before'
                        NOT IN ('attention', 'urgent', 'critical')
                   OR NEW.event_metadata->>'priority_after'
                        NOT IN ('attention', 'urgent', 'critical') THEN
                    RAISE EXCEPTION 'invalid finding event metadata';
                END IF;
            ELSIF NEW.event_type = 'signal_attached' THEN
                IF metadata_keys IS DISTINCT FROM ARRAY[
                    'created_case', 'priority_after', 'priority_before', 'source'
                ]
                   OR jsonb_typeof(NEW.event_metadata->'created_case') <> 'boolean'
                   OR jsonb_typeof(NEW.event_metadata->'source') <> 'string'
                   OR btrim(NEW.event_metadata->>'source') = ''
                   OR jsonb_typeof(NEW.event_metadata->'priority_before') <> 'string'
                   OR jsonb_typeof(NEW.event_metadata->'priority_after') <> 'string'
                   OR NEW.event_metadata->>'priority_before'
                        NOT IN ('attention', 'urgent', 'critical')
                   OR NEW.event_metadata->>'priority_after'
                        NOT IN ('attention', 'urgent', 'critical') THEN
                    RAISE EXCEPTION 'invalid signal_attached event metadata';
                END IF;
            ELSIF NEW.event_type IN ('signal_superseded', 'signal_reactivated') THEN
                IF metadata_keys IS DISTINCT FROM ARRAY['priority_after', 'priority_before']
                   OR jsonb_typeof(NEW.event_metadata->'priority_before') <> 'string'
                   OR jsonb_typeof(NEW.event_metadata->'priority_after') <> 'string'
                   OR NEW.event_metadata->>'priority_before'
                        NOT IN ('attention', 'urgent', 'critical')
                   OR NEW.event_metadata->>'priority_after'
                        NOT IN ('attention', 'urgent', 'critical') THEN
                    RAISE EXCEPTION 'invalid signal state event metadata';
                END IF;
            ELSIF NEW.event_type = 'note_added' THEN
                IF metadata_keys IS DISTINCT FROM ARRAY['corrects_note_id']
                   OR (
                       jsonb_typeof(NEW.event_metadata->'corrects_note_id')
                            NOT IN ('null', 'string')
                       OR (
                           jsonb_typeof(NEW.event_metadata->'corrects_note_id') = 'string'
                           AND NEW.event_metadata->>'corrects_note_id'
                                !~ '^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
                       )
                   ) THEN
                    RAISE EXCEPTION 'invalid note_added event metadata';
                END IF;
            ELSIF NEW.event_type = 'assignment_changed' THEN
                IF metadata_keys IS DISTINCT FROM ARRAY['next_assignee_id', 'previous_assignee_id']
                   OR jsonb_typeof(NEW.event_metadata->'next_assignee_id')
                        NOT IN ('null', 'string')
                   OR jsonb_typeof(NEW.event_metadata->'previous_assignee_id')
                        NOT IN ('null', 'string')
                   OR (
                       jsonb_typeof(NEW.event_metadata->'next_assignee_id') = 'string'
                       AND NEW.event_metadata->>'next_assignee_id'
                            !~ '^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
                   )
                   OR (
                       jsonb_typeof(NEW.event_metadata->'previous_assignee_id') = 'string'
                       AND NEW.event_metadata->>'previous_assignee_id'
                            !~ '^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
                   )
                   OR (
                       jsonb_typeof(NEW.event_metadata->'next_assignee_id') = 'null'
                       AND jsonb_typeof(NEW.event_metadata->'previous_assignee_id') = 'null'
                   ) THEN
                    RAISE EXCEPTION 'invalid assignment_changed event metadata';
                END IF;
            ELSIF NEW.event_type = 'enforcement_action_linked' THEN
                IF metadata_keys IS DISTINCT FROM ARRAY['action_type']
                   OR jsonb_typeof(NEW.event_metadata->'action_type') <> 'string'
                   OR btrim(NEW.event_metadata->>'action_type') = '' THEN
                    RAISE EXCEPTION 'invalid enforcement action event metadata';
                END IF;
            ELSIF NEW.event_type = 'closed' THEN
                IF NEW.actor_kind = 'admin' THEN
                    IF metadata_keys IS DISTINCT FROM ARRAY[
                        'after', 'before', 'closed_by_user_id', 'closure_mode',
                        'previous_assignee_id', 'reason', 'target_id', 'target_type'
                    ]
                       OR jsonb_typeof(NEW.event_metadata->'closure_mode') <> 'string'
                       OR NEW.event_metadata->>'closure_mode'
                            IS DISTINCT FROM 'manual'
                       OR jsonb_typeof(NEW.event_metadata->'reason') <> 'string'
                       OR btrim(NEW.event_metadata->>'reason') = ''
                       OR jsonb_typeof(NEW.event_metadata->'target_type') <> 'string'
                       OR NEW.event_metadata->>'target_type'
                            NOT IN (
                                'community_game', 'need_a_sub', 'money',
                                'user', 'system'
                            )
                       OR jsonb_typeof(NEW.event_metadata->'target_id') <> 'string'
                       OR jsonb_typeof(NEW.event_metadata->'closed_by_user_id')
                            <> 'string' THEN
                        RAISE EXCEPTION 'invalid manual closure event metadata';
                    END IF;
                ELSE
                    IF metadata_keys IS DISTINCT FROM ARRAY[
                        'after', 'before', 'closed_by_user_id', 'closure_mode',
                        'closure_source', 'lifecycle_action',
                        'linked_admin_action_id', 'new_target_state',
                        'previous_assignee_id', 'previous_target_state',
                        'reason', 'target_id', 'target_type', 'trigger_actor_type',
                        'trigger_actor_user_id'
                    ]
                       OR jsonb_typeof(NEW.event_metadata->'closure_mode') <> 'string'
                       OR NEW.event_metadata->>'closure_mode'
                            IS DISTINCT FROM 'automatic'
                       OR jsonb_typeof(NEW.event_metadata->'closure_source') <> 'string'
                       OR NEW.event_metadata->>'closure_source'
                            IS DISTINCT FROM 'target_lifecycle'
                       OR jsonb_typeof(NEW.event_metadata->'lifecycle_action') <> 'string'
                       OR btrim(NEW.event_metadata->>'lifecycle_action') = ''
                       OR jsonb_typeof(NEW.event_metadata->'target_type') <> 'string'
                       OR NEW.event_metadata->>'target_type'
                            NOT IN (
                                'community_game', 'need_a_sub', 'money',
                                'user', 'system'
                            )
                       OR jsonb_typeof(NEW.event_metadata->'target_id') <> 'string'
                       OR jsonb_typeof(NEW.event_metadata->'reason') <> 'string'
                       OR btrim(NEW.event_metadata->>'reason') = ''
                       OR jsonb_typeof(NEW.event_metadata->'previous_target_state') <> 'string'
                       OR btrim(NEW.event_metadata->>'previous_target_state') = ''
                       OR jsonb_typeof(NEW.event_metadata->'new_target_state') <> 'string'
                       OR btrim(NEW.event_metadata->>'new_target_state') = ''
                       OR jsonb_typeof(NEW.event_metadata->'trigger_actor_type') <> 'string'
                       OR btrim(NEW.event_metadata->>'trigger_actor_type') = '' THEN
                        RAISE EXCEPTION 'invalid automatic closure event metadata';
                    END IF;
                END IF;
                FOREACH metadata_field IN ARRAY ARRAY[
                    'previous_assignee_id', 'trigger_actor_user_id',
                    'closed_by_user_id', 'linked_admin_action_id', 'target_id'
                ] LOOP
                    IF NEW.event_metadata ? metadata_field
                       AND (
                           jsonb_typeof(NEW.event_metadata->metadata_field)
                                NOT IN ('null', 'string')
                           OR (
                               jsonb_typeof(NEW.event_metadata->metadata_field)
                                    = 'string'
                               AND NEW.event_metadata->>metadata_field
                                    !~ '^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
                           )
                       ) THEN
                        RAISE EXCEPTION 'invalid closure UUID metadata';
                    END IF;
                END LOOP;
                IF jsonb_typeof(NEW.event_metadata->'before') <> 'object'
                   OR jsonb_typeof(NEW.event_metadata->'after') <> 'object' THEN
                    RAISE EXCEPTION 'invalid closure projection metadata';
                END IF;
                SELECT array_agg(key ORDER BY key)
                INTO nested_keys
                FROM jsonb_object_keys(NEW.event_metadata->'before') AS key;
                IF nested_keys IS DISTINCT FROM ARRAY['case_status', 'closure_outcome']
                   OR jsonb_typeof(
                       NEW.event_metadata->'before'->'case_status'
                   ) <> 'string'
                   OR NEW.event_metadata->'before'->>'case_status'
                        IS DISTINCT FROM 'open'
                   OR jsonb_typeof(
                       NEW.event_metadata->'before'->'closure_outcome'
                   ) <> 'null' THEN
                    RAISE EXCEPTION 'invalid closure before projection';
                END IF;
                SELECT array_agg(key ORDER BY key)
                INTO nested_keys
                FROM jsonb_object_keys(NEW.event_metadata->'after') AS key;
                IF nested_keys IS DISTINCT FROM ARRAY['case_status', 'closure_outcome']
                   OR jsonb_typeof(
                       NEW.event_metadata->'after'->'case_status'
                   ) <> 'string'
                   OR NEW.event_metadata->'after'->>'case_status'
                        IS DISTINCT FROM 'closed'
                   OR jsonb_typeof(
                       NEW.event_metadata->'after'->'closure_outcome'
                   ) <> 'string'
                   OR NEW.event_metadata->'after'->>'closure_outcome'
                        NOT IN (
                            'enforcement_applied', 'no_action_needed',
                            'invalid_signal'
                        ) THEN
                    RAISE EXCEPTION 'invalid closure after projection';
                END IF;
            ELSIF NEW.event_type = 'reopened' THEN
                IF metadata_keys IS DISTINCT FROM ARRAY[
                    'prior_resolution_mode', 'prior_resolution_outcome'
                ]
                   OR jsonb_typeof(
                       NEW.event_metadata->'prior_resolution_mode'
                   ) <> 'string'
                   OR jsonb_typeof(
                       NEW.event_metadata->'prior_resolution_outcome'
                   ) <> 'string'
                   OR NEW.event_metadata->>'prior_resolution_mode'
                        NOT IN ('manual', 'automatic')
                   OR NEW.event_metadata->>'prior_resolution_outcome'
                        NOT IN (
                            'enforcement_applied', 'no_action_needed',
                            'invalid_signal'
                        ) THEN
                    RAISE EXCEPTION 'invalid reopened event metadata';
                END IF;
            ELSIF NEW.event_type IN ('merged_into', 'merged_from') THEN
                IF metadata_keys IS DISTINCT FROM ARRAY[
                    'source_resolution_mode', 'source_resolution_outcome'
                ]
                   OR jsonb_typeof(
                       NEW.event_metadata->'source_resolution_mode'
                   ) <> 'string'
                   OR NEW.event_metadata->>'source_resolution_mode'
                        NOT IN ('manual', 'automatic')
                   OR jsonb_typeof(
                       NEW.event_metadata->'source_resolution_outcome'
                   ) <> 'string'
                   OR NEW.event_metadata->>'source_resolution_outcome'
                        NOT IN (
                            'enforcement_applied', 'no_action_needed',
                            'invalid_signal'
                        ) THEN
                    RAISE EXCEPTION 'invalid merge event metadata';
                END IF;
            END IF;

            SELECT * INTO owner_case
            FROM admin_review_cases
            WHERE id = NEW.review_case_id;
            IF NEW.event_type = 'closed' THEN
                IF owner_case.case_status IS DISTINCT FROM 'closed'
                   OR owner_case.closure_outcome IS DISTINCT FROM
                        NEW.event_metadata->'after'->>'closure_outcome'
                   OR owner_case.closure_reason IS DISTINCT FROM
                        NEW.event_metadata->>'reason'
                   OR owner_case.closed_at IS DISTINCT FROM NEW.created_at
                   OR owner_case.case_type IS DISTINCT FROM
                        NEW.event_metadata->>'target_type'
                   OR COALESCE(
                       owner_case.target_game_id,
                       owner_case.target_sub_post_id,
                       owner_case.target_sub_post_request_id,
                       owner_case.target_payment_id,
                       owner_case.target_financial_outcome_id,
                       owner_case.target_user_id
                   )::text IS DISTINCT FROM NEW.event_metadata->>'target_id' THEN
                    RAISE EXCEPTION 'closure event does not match case resolution';
                END IF;
                IF NEW.actor_kind = 'admin' AND (
                    owner_case.closure_mode IS DISTINCT FROM 'manual'
                    OR owner_case.closed_by_user_id IS DISTINCT FROM NEW.actor_user_id
                    OR NEW.event_metadata->>'closed_by_user_id'
                        IS DISTINCT FROM NEW.actor_user_id::text
                    OR owner_case.closure_rule_id IS NOT NULL
                    OR owner_case.closure_rule_version IS NOT NULL
                    OR NEW.trigger_actor_user_id IS NOT NULL
                ) THEN
                    RAISE EXCEPTION 'manual closure attribution does not match case';
                ELSIF NEW.actor_kind = 'automation' AND (
                    owner_case.closure_mode IS DISTINCT FROM 'automatic'
                    OR owner_case.closure_rule_id
                        IS DISTINCT FROM NEW.automation_rule_id
                    OR owner_case.closure_rule_version
                        IS DISTINCT FROM NEW.automation_rule_version
                    OR owner_case.closed_by_user_id IS DISTINCT FROM
                        NULLIF(
                            NEW.event_metadata->>'closed_by_user_id', ''
                        )::uuid
                    OR NEW.trigger_actor_user_id IS DISTINCT FROM
                        NULLIF(
                            NEW.event_metadata->>'trigger_actor_user_id', ''
                        )::uuid
                    OR NEW.admin_action_id IS DISTINCT FROM
                        NULLIF(
                            NEW.event_metadata->>'linked_admin_action_id', ''
                        )::uuid
                    OR (
                        owner_case.closure_outcome = 'enforcement_applied'
                        AND NEW.admin_action_id IS NULL
                    )
                ) THEN
                    RAISE EXCEPTION 'automatic closure attribution does not match case';
                END IF;
            END IF;
            SELECT max(event_sequence)
            INTO prior_event_sequence
            FROM admin_review_case_events
            WHERE review_case_id = NEW.review_case_id;
            IF NEW.case_version IS DISTINCT FROM owner_case.case_version
               OR NEW.event_sequence IS DISTINCT FROM owner_case.case_version
               OR (
                   NEW.event_type = 'case_created'
                   AND (NEW.event_sequence <> 1 OR prior_event_sequence IS NOT NULL)
               )
               OR (
                   NEW.event_type <> 'case_created'
                   AND prior_event_sequence IS DISTINCT FROM NEW.event_sequence - 1
               ) THEN
                RAISE EXCEPTION 'review case event sequence is not gap-free';
            END IF;

            IF NEW.content_moderation_finding_id IS NOT NULL THEN
                SELECT review_case_id, finding_type, risk_area, source_field,
                       priority, current_match
                INTO child_case_id, child_finding_type, child_risk_area,
                     child_source_field, child_priority, child_current
                FROM admin_content_moderation_findings
                WHERE id = NEW.content_moderation_finding_id;
                IF child_case_id IS DISTINCT FROM NEW.review_case_id
                   OR NEW.event_metadata->>'finding_type'
                        IS DISTINCT FROM child_finding_type
                   OR NEW.event_metadata->>'risk_area'
                        IS DISTINCT FROM child_risk_area
                   OR NEW.event_metadata->>'source_field'
                        IS DISTINCT FROM child_source_field THEN
                    RAISE EXCEPTION 'event finding ownership or attribution is invalid';
                END IF;
            END IF;

            IF NEW.signal_id IS NOT NULL THEN
                SELECT review_case_id, source, signal_status, priority, metadata,
                       target_user_id, target_game_id, target_sub_post_id,
                       target_sub_post_request_id, target_payment_id,
                       target_financial_outcome_id
                INTO child_case_id, child_source, child_signal_status,
                     child_priority, child_signal_metadata, child_target_user_id,
                     child_target_game_id, child_target_sub_post_id,
                     child_target_sub_post_request_id, child_target_payment_id,
                     child_target_financial_outcome_id
                FROM admin_review_signals
                WHERE id = NEW.signal_id;
                IF child_case_id IS DISTINCT FROM NEW.review_case_id
                   OR (
                       NEW.event_metadata ? 'source'
                       AND NEW.event_metadata->>'source' IS DISTINCT FROM child_source
                   ) THEN
                    RAISE EXCEPTION 'event signal ownership or attribution is invalid';
                END IF;
            END IF;

            IF NEW.note_id IS NOT NULL THEN
                SELECT review_case_id, corrects_note_id, author_user_id, note_status,
                       edited_at, deleted_at
                INTO child_case_id, child_corrects_note_id, child_note_author_id,
                     child_note_status, child_note_edited_at, child_note_deleted_at
                FROM admin_review_case_notes
                WHERE id = NEW.note_id;
                IF child_case_id IS DISTINCT FROM NEW.review_case_id
                   OR (
                       NULLIF(NEW.event_metadata->>'corrects_note_id', '')::uuid
                       IS DISTINCT FROM child_corrects_note_id
                   ) THEN
                    RAISE EXCEPTION 'event note ownership or correction is invalid';
                END IF;
            END IF;

            IF NEW.related_case_id IS NOT NULL THEN
                SELECT * INTO related_case
                FROM admin_review_cases
                WHERE id = NEW.related_case_id;
                IF related_case.id IS NULL
                   OR related_case.id = owner_case.id
                   OR related_case.case_type <> owner_case.case_type
                   OR related_case.case_category <> owner_case.case_category
                   OR related_case.target_user_id
                        IS DISTINCT FROM owner_case.target_user_id
                   OR related_case.target_game_id
                        IS DISTINCT FROM owner_case.target_game_id
                   OR related_case.target_sub_post_id
                        IS DISTINCT FROM owner_case.target_sub_post_id
                   OR related_case.target_sub_post_request_id
                        IS DISTINCT FROM owner_case.target_sub_post_request_id
                   OR related_case.target_payment_id
                        IS DISTINCT FROM owner_case.target_payment_id
                   OR related_case.target_financial_outcome_id
                        IS DISTINCT FROM owner_case.target_financial_outcome_id THEN
                    RAISE EXCEPTION 'merge event case relationship is invalid';
                END IF;
            END IF;

            IF NEW.related_event_id IS NOT NULL THEN
                SELECT * INTO related_event
                FROM admin_review_case_events
                WHERE id = NEW.related_event_id;
                IF related_event.id IS NULL THEN
                    RAISE EXCEPTION 'related review event does not exist';
                END IF;
            END IF;

            IF NEW.admin_action_id IS NOT NULL THEN
                SELECT admin_user_id, action_type, target_review_case_id, reason,
                       metadata,
                       target_user_id, target_game_id, target_sub_post_id,
                       target_sub_post_request_id, target_payment_id,
                       target_financial_outcome_id
                INTO action_actor_id, action_type_value, action_case_id, action_reason,
                     action_metadata,
                     action_target_user_id, action_target_game_id,
                     action_target_sub_post_id, action_target_sub_post_request_id,
                     action_target_payment_id, action_target_financial_outcome_id
                FROM admin_actions
                WHERE id = NEW.admin_action_id;
                IF action_actor_id IS NULL THEN
                    RAISE EXCEPTION 'event admin action does not exist';
                END IF;
                IF NEW.actor_kind = 'admin'
                   AND action_actor_id IS DISTINCT FROM NEW.actor_user_id THEN
                    RAISE EXCEPTION 'event actor does not match its admin action';
                END IF;
                IF NEW.actor_kind = 'automation'
                   AND action_actor_id IS DISTINCT FROM NEW.trigger_actor_user_id THEN
                    RAISE EXCEPTION 'automation trigger does not match its admin action';
                END IF;
                IF action_case_id IS DISTINCT FROM (
                    CASE
                        WHEN NEW.event_type = 'merged_from'
                        THEN NEW.related_case_id
                        ELSE NEW.review_case_id
                    END
                ) THEN
                    RAISE EXCEPTION 'event admin action targets another case';
                END IF;
                IF NEW.event_type = 'note_added'
                   AND action_type_value <> 'add_review_case_note'
                   OR NEW.event_type = 'assignment_changed'
                   AND action_type_value <> 'assign_review_case'
                   OR NEW.event_type = 'closed' AND NEW.actor_kind = 'admin'
                   AND action_type_value <> 'close_review_case'
                   OR NEW.event_type = 'reopened'
                   AND action_type_value <> 'reopen_review_case'
                   OR NEW.event_type IN ('merged_into', 'merged_from')
                   AND action_type_value <> 'merge_review_case' THEN
                    RAISE EXCEPTION 'event admin action type is invalid';
                END IF;
                IF NEW.event_type = 'enforcement_action_linked'
                   AND (
                       action_type_value IN (
                           'create_review_case', 'close_review_case',
                           'add_review_case_note', 'assign_review_case',
                           'reopen_review_case', 'merge_review_case'
                       )
                       OR NEW.event_metadata->>'action_type'
                            IS DISTINCT FROM action_type_value
                   ) THEN
                    RAISE EXCEPTION 'linked enforcement action is invalid';
                END IF;
                IF NEW.event_type = 'closed' AND NEW.actor_kind = 'automation'
                   AND (
                       action_type_value IN (
                           'create_review_case', 'close_review_case',
                           'add_review_case_note', 'assign_review_case',
                           'reopen_review_case', 'merge_review_case'
                       )
                       OR NEW.event_metadata->>'linked_admin_action_id'
                            IS DISTINCT FROM NEW.admin_action_id::text
                   ) THEN
                    RAISE EXCEPTION 'automatic closure action is invalid';
                END IF;
                IF NEW.event_type = 'closed' AND (
                    COALESCE(
                        action_target_game_id,
                        action_target_sub_post_id,
                        action_target_sub_post_request_id,
                        action_target_payment_id,
                        action_target_financial_outcome_id,
                        action_target_user_id
                    )::text IS DISTINCT FROM NEW.event_metadata->>'target_id'
                    OR (
                        NEW.actor_kind = 'admin'
                        AND action_reason IS DISTINCT FROM
                            NEW.event_metadata->>'reason'
                    )
                ) THEN
                    RAISE EXCEPTION 'closure action does not match transition';
                END IF;
            ELSIF NEW.event_type = 'closed' AND NEW.actor_kind = 'automation'
                  AND jsonb_typeof(
                      NEW.event_metadata->'linked_admin_action_id'
                  ) <> 'null' THEN
                RAISE EXCEPTION 'automatic closure references a missing action';
            END IF;

            IF NEW.event_type = 'case_created' THEN
                IF owner_case.case_status IS DISTINCT FROM 'open'
                   OR owner_case.case_version <> 1
                   OR owner_case.assigned_to_user_id IS NOT NULL
                   OR owner_case.merged_into_case_id IS NOT NULL
                   OR owner_case.closure_mode IS NOT NULL
                   OR owner_case.closure_outcome IS NOT NULL
                   OR NOT (
                       (
                           owner_case.creation_reason NOT IN (
                               'content_moderation_finding',
                               'chat_moderation_detection'
                           )
                           AND NEW.event_metadata->>'source'
                                = owner_case.creation_reason
                           AND NEW.signal_id IS NULL
                           AND NEW.content_moderation_finding_id IS NULL
                       ) OR
                       (
                           owner_case.creation_reason = 'content_moderation_finding'
                           AND owner_case.case_category = 'content_moderation'
                           AND NEW.event_metadata->>'source'
                                = 'content_moderation_scanner'
                           AND NEW.signal_id IS NULL
                           AND NEW.content_moderation_finding_id IS NULL
                       ) OR (
                           owner_case.creation_reason = 'chat_moderation_detection'
                           AND owner_case.case_category = 'chat_moderation'
                           AND NEW.event_metadata->>'source' = 'chat_moderation'
                           AND NEW.signal_id IS NOT NULL
                           AND child_signal_status = 'attached'
                           AND CASE
                               WHEN jsonb_typeof(
                                   child_signal_metadata->'current_match'
                               ) = 'boolean'
                               THEN (child_signal_metadata->>'current_match')::boolean
                               ELSE true
                           END
                           AND child_target_user_id
                                IS NOT DISTINCT FROM owner_case.target_user_id
                           AND child_target_game_id
                                IS NOT DISTINCT FROM owner_case.target_game_id
                           AND child_target_sub_post_id
                                IS NOT DISTINCT FROM owner_case.target_sub_post_id
                           AND child_target_sub_post_request_id IS NOT DISTINCT FROM
                                owner_case.target_sub_post_request_id
                           AND child_target_payment_id
                                IS NOT DISTINCT FROM owner_case.target_payment_id
                           AND child_target_financial_outcome_id IS NOT DISTINCT FROM
                                owner_case.target_financial_outcome_id
                       )
                   ) THEN
                    RAISE EXCEPTION 'case-created event does not match new case state';
                END IF;
            END IF;

            IF NEW.event_type IN (
                'finding_attached', 'finding_cleared', 'signal_attached',
                'signal_superseded', 'signal_reactivated'
            ) THEN
                SELECT event_metadata->>'priority_after'
                INTO prior_source_priority
                FROM admin_review_case_events
                WHERE review_case_id = NEW.review_case_id
                  AND event_type IN (
                      'finding_attached', 'finding_cleared', 'signal_attached',
                      'signal_superseded', 'signal_reactivated'
                  )
                ORDER BY event_sequence DESC
                LIMIT 1;
                prior_source_priority := COALESCE(
                    prior_source_priority,
                    owner_case.priority
                );

                IF owner_case.case_category = 'content_moderation' THEN
                    SELECT priority
                    INTO derived_priority
                    FROM admin_content_moderation_findings
                    WHERE review_case_id = NEW.review_case_id
                      AND current_match = true
                    ORDER BY CASE priority
                        WHEN 'critical' THEN 3
                        WHEN 'urgent' THEN 2
                        ELSE 1
                    END DESC
                    LIMIT 1;
                ELSIF owner_case.case_category = 'chat_moderation' THEN
                    SELECT priority
                    INTO derived_priority
                    FROM admin_review_signals
                    WHERE review_case_id = NEW.review_case_id
                      AND signal_status <> 'dismissed'
                      AND CASE
                          WHEN jsonb_typeof(metadata->'current_match') = 'boolean'
                          THEN (metadata->>'current_match')::boolean
                          ELSE true
                      END
                    ORDER BY CASE priority
                        WHEN 'critical' THEN 3
                        WHEN 'urgent' THEN 2
                        ELSE 1
                    END DESC
                    LIMIT 1;
                ELSE
                    RAISE EXCEPTION 'source event requires moderation case category';
                END IF;
                derived_priority := COALESCE(derived_priority, 'attention');

                IF owner_case.case_status IS DISTINCT FROM 'open'
                   OR NEW.event_metadata->>'priority_before'
                        IS DISTINCT FROM prior_source_priority
                   OR NEW.event_metadata->>'priority_after'
                        IS DISTINCT FROM owner_case.priority
                   OR owner_case.priority IS DISTINCT FROM derived_priority THEN
                    RAISE EXCEPTION 'source event priority does not match case state';
                END IF;
            END IF;

            IF NEW.event_type IN ('finding_attached', 'finding_cleared') THEN
                SELECT event_type
                INTO prior_child_event_type
                FROM admin_review_case_events
                WHERE review_case_id = NEW.review_case_id
                  AND content_moderation_finding_id
                        = NEW.content_moderation_finding_id
                  AND event_type IN ('finding_attached', 'finding_cleared')
                ORDER BY event_sequence DESC
                LIMIT 1;
                IF owner_case.case_category <> 'content_moderation'
                   OR (
                       NEW.event_type = 'finding_attached'
                       AND (child_current IS DISTINCT FROM true
                            OR prior_child_event_type IS NOT NULL)
                   )
                   OR (
                       NEW.event_type = 'finding_cleared'
                       AND (child_current IS DISTINCT FROM false
                            OR prior_child_event_type IS DISTINCT FROM
                                'finding_attached')
                   ) THEN
                    RAISE EXCEPTION 'finding event does not match finding state';
                END IF;
            END IF;

            IF NEW.event_type IN (
                'signal_attached', 'signal_superseded', 'signal_reactivated'
            ) THEN
                child_current := child_signal_status <> 'dismissed' AND CASE
                    WHEN jsonb_typeof(child_signal_metadata->'current_match') = 'boolean'
                    THEN (child_signal_metadata->>'current_match')::boolean
                    ELSE true
                END;
                SELECT event_type
                INTO prior_child_event_type
                FROM admin_review_case_events
                WHERE review_case_id = NEW.review_case_id
                  AND signal_id = NEW.signal_id
                  AND event_type IN (
                      'signal_attached', 'signal_superseded', 'signal_reactivated'
                  )
                ORDER BY event_sequence DESC
                LIMIT 1;
                IF owner_case.case_category <> 'chat_moderation'
                   OR child_signal_status IS DISTINCT FROM 'attached'
                   OR child_target_user_id
                        IS DISTINCT FROM owner_case.target_user_id
                   OR child_target_game_id
                        IS DISTINCT FROM owner_case.target_game_id
                   OR child_target_sub_post_id
                        IS DISTINCT FROM owner_case.target_sub_post_id
                   OR child_target_sub_post_request_id
                        IS DISTINCT FROM owner_case.target_sub_post_request_id
                   OR child_target_payment_id
                        IS DISTINCT FROM owner_case.target_payment_id
                   OR child_target_financial_outcome_id
                        IS DISTINCT FROM owner_case.target_financial_outcome_id
                   OR (
                       NEW.event_type = 'signal_attached'
                       AND (child_current IS DISTINCT FROM true
                            OR prior_child_event_type IS NOT NULL)
                   )
                   OR (
                       NEW.event_type = 'signal_superseded'
                       AND (child_current IS DISTINCT FROM false
                            OR prior_child_event_type IS NULL
                            OR prior_child_event_type NOT IN (
                                'signal_attached', 'signal_reactivated'
                            ))
                   )
                   OR (
                       NEW.event_type = 'signal_reactivated'
                       AND (child_current IS DISTINCT FROM true
                            OR prior_child_event_type IS DISTINCT FROM
                                'signal_superseded')
                   ) THEN
                    RAISE EXCEPTION 'signal event does not match signal state';
                END IF;
                IF NEW.event_type = 'signal_attached' AND (
                    (NEW.event_metadata->>'created_case')::boolean IS DISTINCT FROM
                    EXISTS (
                        SELECT 1
                        FROM admin_review_case_events
                        WHERE review_case_id = NEW.review_case_id
                          AND event_type = 'case_created'
                          AND signal_id = NEW.signal_id
                    )
                ) THEN
                    RAISE EXCEPTION 'signal attachment creation attribution is invalid';
                END IF;
            END IF;

            IF NEW.event_type = 'note_added' THEN
                IF owner_case.case_status IS DISTINCT FROM 'open'
                   OR child_note_author_id IS DISTINCT FROM NEW.actor_user_id
                   OR child_note_status IS DISTINCT FROM 'active'
                   OR child_note_edited_at IS NOT NULL
                   OR child_note_deleted_at IS NOT NULL
                   OR action_metadata->>'note_id' IS DISTINCT FROM NEW.note_id::text
                   OR action_metadata->>'corrects_note_id' IS DISTINCT FROM
                        NEW.event_metadata->>'corrects_note_id'
                   OR EXISTS (
                       SELECT 1 FROM admin_review_case_events
                       WHERE review_case_id = NEW.review_case_id
                         AND event_type = 'note_added'
                         AND note_id = NEW.note_id
                   ) THEN
                    RAISE EXCEPTION 'note event does not match eligible new note';
                END IF;
            END IF;

            IF NEW.event_type = 'assignment_changed' THEN
                SELECT CASE
                    WHEN event_type = 'assignment_changed'
                    THEN NULLIF(event_metadata->>'next_assignee_id', '')::uuid
                    ELSE NULL
                END
                INTO prior_effective_assignee_id
                FROM admin_review_case_events
                WHERE review_case_id = NEW.review_case_id
                  AND event_type IN (
                      'assignment_changed', 'closed', 'reopened', 'merged_into'
                  )
                ORDER BY event_sequence DESC
                LIMIT 1;
                IF owner_case.case_status IS DISTINCT FROM 'open'
                   OR NULLIF(
                       NEW.event_metadata->>'previous_assignee_id', ''
                   )::uuid IS NOT DISTINCT FROM NULLIF(
                       NEW.event_metadata->>'next_assignee_id', ''
                   )::uuid
                   OR NULLIF(
                       NEW.event_metadata->>'previous_assignee_id', ''
                   )::uuid IS DISTINCT FROM prior_effective_assignee_id
                   OR NULLIF(
                       NEW.event_metadata->>'next_assignee_id', ''
                   )::uuid IS DISTINCT FROM owner_case.assigned_to_user_id
                   OR (owner_case.assigned_to_user_id IS NULL)
                        IS DISTINCT FROM (owner_case.assigned_at IS NULL)
                   OR action_metadata->>'previous_assignee_id' IS DISTINCT FROM
                        NEW.event_metadata->>'previous_assignee_id'
                   OR action_metadata->>'next_assignee_id' IS DISTINCT FROM
                        NEW.event_metadata->>'next_assignee_id' THEN
                    RAISE EXCEPTION 'assignment event does not match case assignment';
                END IF;
            END IF;

            IF NEW.event_type = 'enforcement_action_linked' THEN
                IF owner_case.case_status IS DISTINCT FROM 'open'
                   OR (
                       owner_case.case_type = 'community_game'
                       AND action_target_game_id
                            IS DISTINCT FROM owner_case.target_game_id
                   )
                   OR (
                       owner_case.case_type = 'need_a_sub'
                       AND action_target_sub_post_id
                            IS DISTINCT FROM owner_case.target_sub_post_id
                   )
                   OR EXISTS (
                       SELECT 1 FROM admin_review_case_events
                       WHERE review_case_id = NEW.review_case_id
                         AND event_type = 'enforcement_action_linked'
                         AND admin_action_id = NEW.admin_action_id
                   ) THEN
                    RAISE EXCEPTION 'enforcement-link event does not match open case';
                END IF;
            END IF;

            IF NEW.event_type = 'reopened' THEN
                SELECT id
                INTO latest_lifecycle_event_id
                FROM admin_review_case_events
                WHERE review_case_id = NEW.review_case_id
                  AND event_type IN ('closed', 'reopened', 'merged_into')
                ORDER BY event_sequence DESC
                LIMIT 1;
                IF owner_case.case_status IS DISTINCT FROM 'open'
                   OR owner_case.closed_by_user_id IS NOT NULL
                   OR owner_case.closure_outcome IS NOT NULL
                   OR owner_case.closure_reason IS NOT NULL
                   OR owner_case.closure_mode IS NOT NULL
                   OR owner_case.closure_rule_id IS NOT NULL
                   OR owner_case.closure_rule_version IS NOT NULL
                   OR owner_case.closed_at IS NOT NULL
                   OR owner_case.assigned_to_user_id IS NOT NULL
                   OR owner_case.merged_into_case_id IS NOT NULL
                   OR latest_lifecycle_event_id IS DISTINCT FROM NEW.related_event_id
                   OR action_metadata->>'prior_closure_event_id'
                        IS DISTINCT FROM NEW.related_event_id::text
                   OR action_metadata->>'prior_resolution_mode'
                        IS DISTINCT FROM
                            NEW.event_metadata->>'prior_resolution_mode'
                   OR action_metadata->>'prior_resolution_outcome'
                        IS DISTINCT FROM
                            NEW.event_metadata->>'prior_resolution_outcome' THEN
                    RAISE EXCEPTION 'reopen event does not match resulting open case';
                END IF;
            END IF;

            IF NEW.event_type = 'merged_into' THEN
                IF related_case.case_status IS DISTINCT FROM 'open'
                   OR related_case.merged_into_case_id IS NOT NULL
                   OR EXISTS (
                       SELECT 1 FROM admin_review_case_events
                       WHERE review_case_id = NEW.review_case_id
                         AND event_type = 'merged_into'
                   ) THEN
                    RAISE EXCEPTION 'outgoing merge destination state is invalid';
                END IF;
            ELSIF NEW.event_type = 'merged_from' THEN
                IF owner_case.case_status IS DISTINCT FROM 'open'
                   OR owner_case.merged_into_case_id IS NOT NULL
                   OR EXISTS (
                       SELECT 1 FROM admin_review_case_events
                       WHERE review_case_id = NEW.review_case_id
                         AND event_type = 'merged_from'
                         AND related_case_id = NEW.related_case_id
                   ) THEN
                    RAISE EXCEPTION 'incoming merge destination state is invalid';
                END IF;
            END IF;

            IF NEW.event_type = 'closed' AND NEW.actor_kind = 'automation' THEN
                IF owner_case.case_category IS DISTINCT FROM 'content_moderation'
                   OR owner_case.case_type NOT IN ('community_game', 'need_a_sub')
                   OR NEW.automation_rule_id IS DISTINCT FROM
                        'moderation_review_case.target_lifecycle_resolution'
                   OR NEW.automation_rule_version IS DISTINCT FROM '1'
                   OR NEW.event_metadata->>'previous_target_state'
                        IS DISTINCT FROM 'active'
                   OR (
                       NEW.event_metadata->>'trigger_actor_type' IN (
                           'admin', 'host', 'owner'
                       )
                       AND NEW.trigger_actor_user_id IS NULL
                   )
                   OR (
                       NEW.event_metadata->>'trigger_actor_type' IN (
                           'system', 'scheduled_job'
                       )
                       AND NEW.trigger_actor_user_id IS NOT NULL
                   )
                   OR (
                       NEW.event_metadata->>'trigger_actor_type' = 'admin'
                       AND owner_case.closed_by_user_id
                            IS DISTINCT FROM NEW.trigger_actor_user_id
                   )
                   OR (
                       NEW.event_metadata->>'trigger_actor_type' <> 'admin'
                       AND owner_case.closed_by_user_id IS NOT NULL
                   )
                   OR NOT COALESCE((
                       (
                           owner_case.case_type = 'community_game'
                           AND NEW.event_metadata->>'lifecycle_action' = 'host_cancelled'
                           AND NEW.event_metadata->>'new_target_state' = 'cancelled'
                           AND NEW.event_metadata->>'trigger_actor_type' = 'host'
                           AND owner_case.closure_outcome = 'no_action_needed'
                           AND NEW.admin_action_id IS NULL
                       ) OR (
                           owner_case.case_type = 'community_game'
                           AND NEW.event_metadata->>'lifecycle_action'
                                = 'admin_operational_cancelled'
                           AND NEW.event_metadata->>'new_target_state' = 'cancelled'
                           AND NEW.event_metadata->>'trigger_actor_type' = 'admin'
                           AND owner_case.closure_outcome = 'no_action_needed'
                           AND action_type_value = 'cancel_game'
                       ) OR (
                           owner_case.case_type = 'community_game'
                           AND NEW.event_metadata->>'lifecycle_action'
                                = 'admin_moderation_cancelled'
                           AND NEW.event_metadata->>'new_target_state' = 'cancelled'
                           AND NEW.event_metadata->>'trigger_actor_type' = 'admin'
                           AND owner_case.closure_outcome = 'enforcement_applied'
                           AND action_type_value = 'admin_cancel_community_game'
                       ) OR (
                           owner_case.case_type = 'community_game'
                           AND NEW.event_metadata->>'lifecycle_action'
                                = 'host_account_deleted'
                           AND NEW.event_metadata->>'new_target_state' = 'cancelled'
                           AND NEW.event_metadata->>'trigger_actor_type' = 'owner'
                           AND owner_case.closure_outcome = 'no_action_needed'
                           AND NEW.admin_action_id IS NULL
                       ) OR (
                           owner_case.case_type = 'community_game'
                           AND NEW.event_metadata->>'lifecycle_action' = 'game_completed'
                           AND NEW.event_metadata->>'new_target_state' = 'completed'
                           AND NEW.event_metadata->>'trigger_actor_type'
                                IN ('admin', 'system')
                           AND owner_case.closure_outcome = 'no_action_needed'
                           AND NEW.admin_action_id IS NULL
                       ) OR (
                           owner_case.case_type = 'community_game'
                           AND NEW.event_metadata->>'lifecycle_action' = 'game_expired'
                           AND NEW.event_metadata->>'new_target_state' = 'expired'
                           AND NEW.event_metadata->>'trigger_actor_type'
                                IN ('admin', 'system')
                           AND owner_case.closure_outcome = 'no_action_needed'
                           AND NEW.admin_action_id IS NULL
                       ) OR (
                           owner_case.case_type = 'community_game'
                           AND NEW.event_metadata->>'lifecycle_action'
                                = 'admin_soft_deleted'
                           AND NEW.event_metadata->>'new_target_state' = 'soft_deleted'
                           AND NEW.event_metadata->>'trigger_actor_type' = 'admin'
                           AND owner_case.closure_outcome = 'no_action_needed'
                           AND NEW.admin_action_id IS NULL
                       ) OR (
                           owner_case.case_type = 'need_a_sub'
                           AND NEW.event_metadata->>'lifecycle_action' = 'owner_cancelled'
                           AND NEW.event_metadata->>'new_target_state' = 'cancelled'
                           AND NEW.event_metadata->>'trigger_actor_type' = 'owner'
                           AND owner_case.closure_outcome = 'no_action_needed'
                           AND NEW.admin_action_id IS NULL
                       ) OR (
                           owner_case.case_type = 'need_a_sub'
                           AND NEW.event_metadata->>'lifecycle_action'
                                = 'owner_account_deleted'
                           AND NEW.event_metadata->>'new_target_state' = 'cancelled'
                           AND NEW.event_metadata->>'trigger_actor_type' = 'owner'
                           AND owner_case.closure_outcome = 'no_action_needed'
                           AND NEW.admin_action_id IS NULL
                       ) OR (
                           owner_case.case_type = 'need_a_sub'
                           AND NEW.event_metadata->>'lifecycle_action' = 'admin_removed'
                           AND NEW.event_metadata->>'new_target_state' = 'removed'
                           AND NEW.event_metadata->>'trigger_actor_type' = 'admin'
                           AND owner_case.closure_outcome = 'enforcement_applied'
                           AND action_type_value = 'remove_sub_post'
                       ) OR (
                           owner_case.case_type = 'need_a_sub'
                           AND NEW.event_metadata->>'lifecycle_action' = 'post_completed'
                           AND NEW.event_metadata->>'new_target_state' = 'completed'
                           AND NEW.event_metadata->>'trigger_actor_type' = 'scheduled_job'
                           AND owner_case.closure_outcome = 'no_action_needed'
                           AND NEW.admin_action_id IS NULL
                       ) OR (
                           owner_case.case_type = 'need_a_sub'
                           AND NEW.event_metadata->>'lifecycle_action' = 'post_expired'
                           AND NEW.event_metadata->>'new_target_state' = 'expired'
                           AND NEW.event_metadata->>'trigger_actor_type' = 'scheduled_job'
                           AND owner_case.closure_outcome = 'no_action_needed'
                           AND NEW.admin_action_id IS NULL
                       )
                   ), false) THEN
                    RAISE EXCEPTION 'automatic closure lifecycle transition is invalid';
                END IF;

                IF owner_case.case_type = 'community_game' AND NOT EXISTS (
                    SELECT 1 FROM games
                    WHERE id = owner_case.target_game_id
                      AND game_type = 'community'
                      AND (
                          (
                              NEW.event_metadata->>'new_target_state' = 'soft_deleted'
                              AND deleted_at IS NOT NULL
                          )
                          OR game_status = NEW.event_metadata->>'new_target_state'
                      )
                ) THEN
                    RAISE EXCEPTION 'automatic closure target state is invalid';
                ELSIF owner_case.case_type = 'need_a_sub' AND NOT EXISTS (
                    SELECT 1 FROM sub_posts
                    WHERE id = owner_case.target_sub_post_id
                      AND post_status = NEW.event_metadata->>'new_target_state'
                ) THEN
                    RAISE EXCEPTION 'automatic closure target state is invalid';
                END IF;
            END IF;

            IF NEW.event_type <> 'closed' AND NEW.trigger_actor_user_id IS NOT NULL THEN
                RAISE EXCEPTION 'trigger actor is invalid for this event';
            END IF;
            IF NEW.event_type IN (
                'case_created', 'finding_attached', 'finding_cleared',
                'signal_attached', 'signal_superseded', 'signal_reactivated'
            ) AND NEW.admin_action_id IS NOT NULL THEN
                RAISE EXCEPTION 'source events cannot reference admin actions';
            END IF;

            IF NEW.event_type = 'reopened' THEN
                IF related_event.review_case_id IS DISTINCT FROM NEW.review_case_id
                   OR related_event.event_type <> 'closed'
                   OR related_event.event_sequence >= NEW.event_sequence
                   OR NEW.event_metadata->>'prior_resolution_mode'
                        IS DISTINCT FROM related_event.event_metadata->>'closure_mode'
                   OR NEW.event_metadata->>'prior_resolution_outcome'
                        IS DISTINCT FROM related_event.event_metadata->'after'
                            ->>'closure_outcome' THEN
                    RAISE EXCEPTION 'reopen prior closure relationship is invalid';
                END IF;
            ELSIF NEW.event_type = 'merged_into' THEN
                IF owner_case.merged_into_case_id
                        IS DISTINCT FROM NEW.related_case_id
                   OR owner_case.case_status <> 'closed'
                   OR owner_case.closure_mode NOT IN ('manual', 'automatic')
                   OR owner_case.closure_outcome NOT IN (
                       'enforcement_applied', 'no_action_needed', 'invalid_signal'
                   )
                   OR owner_case.closure_reason IS NULL
                   OR btrim(owner_case.closure_reason) = ''
                   OR owner_case.closed_at IS NULL
                   OR owner_case.assigned_to_user_id IS NOT NULL THEN
                    RAISE EXCEPTION 'outgoing merge case link is invalid';
                END IF;
                IF related_event.review_case_id
                        IS DISTINCT FROM NEW.review_case_id
                   OR related_event.event_type <> 'closed'
                   OR related_event.event_sequence >= NEW.event_sequence
                   OR related_event.created_at IS DISTINCT FROM owner_case.closed_at
                   OR related_event.event_metadata->>'closure_mode'
                        IS DISTINCT FROM owner_case.closure_mode
                   OR related_event.event_metadata->>'reason'
                        IS DISTINCT FROM owner_case.closure_reason
                   OR related_event.event_metadata->'after'->>'closure_outcome'
                        IS DISTINCT FROM owner_case.closure_outcome
                   OR NEW.event_metadata->>'source_resolution_mode'
                        IS DISTINCT FROM owner_case.closure_mode
                   OR NEW.event_metadata->>'source_resolution_outcome'
                        IS DISTINCT FROM owner_case.closure_outcome THEN
                    RAISE EXCEPTION 'closed merge source prior closure is invalid';
                END IF;
            ELSIF NEW.event_type = 'merged_from' THEN
                IF related_case.merged_into_case_id
                        IS DISTINCT FROM NEW.review_case_id
                   OR related_event.review_case_id
                        IS DISTINCT FROM NEW.related_case_id
                   OR related_event.event_type <> 'merged_into'
                   OR related_event.related_case_id
                        IS DISTINCT FROM NEW.review_case_id
                   OR related_event.admin_action_id
                        IS DISTINCT FROM NEW.admin_action_id
                   OR related_event.event_metadata
                        IS DISTINCT FROM NEW.event_metadata THEN
                    RAISE EXCEPTION 'incoming merge reciprocal relationship is invalid';
                END IF;
            END IF;

            RETURN NEW;
        END;
        $$
    """,
        safety_basis="fixed trigger function validating immutable review-case event semantics",
    ),
    RawSqlAllowance(
        source_path="backend/alembic/versions/0059_create_admin_review_case_events_table.py",
        constructor="op.execute",
        expression="""
        CREATE TRIGGER trg_admin_review_case_events_validate_insert
        BEFORE INSERT ON admin_review_case_events
        FOR EACH ROW EXECUTE FUNCTION validate_admin_review_case_event_insert()
    """,
        safety_basis="fixed review-case event insert-validation trigger",
    ),
    RawSqlAllowance(
        source_path="backend/alembic/versions/0059_create_admin_review_case_events_table.py",
        constructor="op.execute",
        expression="DROP TRIGGER trg_admin_review_case_events_validate_insert ON admin_review_case_events",
        safety_basis="fixed review-case event validation trigger teardown",
    ),
    RawSqlAllowance(
        source_path="backend/alembic/versions/0059_create_admin_review_case_events_table.py",
        constructor="op.execute",
        expression="DROP FUNCTION validate_admin_review_case_event_insert()",
        safety_basis="fixed review-case event validation function teardown",
    ),
    RawSqlAllowance(
        source_path="backend/alembic/versions/0059_create_admin_review_case_events_table.py",
        constructor="op.execute",
        expression="""
        CREATE FUNCTION reject_admin_review_case_event_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'admin review case events are immutable';
        END;
        $$
    """,
        safety_basis="fixed trigger function enforcing immutable review-case events",
    ),
    RawSqlAllowance(
        source_path="backend/alembic/versions/0059_create_admin_review_case_events_table.py",
        constructor="op.execute",
        expression="""
        CREATE TRIGGER trg_admin_review_case_events_immutable
        BEFORE UPDATE OR DELETE ON admin_review_case_events
        FOR EACH ROW EXECUTE FUNCTION reject_admin_review_case_event_mutation()
    """,
        safety_basis="fixed immutable review-case event trigger",
    ),
    RawSqlAllowance(
        source_path="backend/alembic/versions/0059_create_admin_review_case_events_table.py",
        constructor="op.execute",
        expression="DROP TRIGGER trg_admin_review_case_events_immutable ON admin_review_case_events",
        safety_basis="fixed immutable review-case event trigger teardown",
    ),
    RawSqlAllowance(
        source_path="backend/alembic/versions/0059_create_admin_review_case_events_table.py",
        constructor="op.execute",
        expression="DROP FUNCTION reject_admin_review_case_event_mutation()",
        safety_basis="fixed immutable review-case event function teardown",
    ),
    RawSqlAllowance(
        source_path="backend/alembic/versions/0066_create_admin_review_case_resolution_references_table.py",
        constructor="op.execute",
        expression="""
        CREATE FUNCTION validate_admin_review_case_resolution_ref_insert()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE
            owning_case_id uuid;
            owning_event_type text;
            owning_event_action_id uuid;
            owning_event_xmin xid;
            referenced_case_id uuid;
            referenced_current boolean;
            referenced_action_type text;
        BEGIN
            SELECT review_case_id, event_type, admin_action_id, xmin
            INTO owning_case_id, owning_event_type, owning_event_action_id,
                 owning_event_xmin
            FROM admin_review_case_events
            WHERE id = NEW.closure_event_id;

            IF owning_event_type IS NULL OR owning_event_type <> 'closed' THEN
                RAISE EXCEPTION 'resolution references require a closure event';
            END IF;
            IF NEW.reference_type = 'finding' THEN
                SELECT review_case_id, current_match
                INTO referenced_case_id, referenced_current
                FROM admin_content_moderation_findings
                WHERE id = NEW.content_moderation_finding_id;
                IF referenced_case_id IS NULL
                   OR (
                       referenced_case_id <> owning_case_id
                       AND NOT EXISTS (
                           SELECT 1 FROM admin_review_cases
                           WHERE id = referenced_case_id
                             AND merged_into_case_id = owning_case_id
                       )
                   )
                   OR NEW.was_current IS DISTINCT FROM referenced_current THEN
                    RAISE EXCEPTION 'resolution finding ownership is invalid';
                END IF;
            ELSIF NEW.reference_type = 'signal' THEN
                SELECT review_case_id,
                       CASE
                           WHEN jsonb_typeof(metadata->'current_match') = 'boolean'
                           THEN (metadata->>'current_match')::boolean
                           ELSE true
                       END
                INTO referenced_case_id, referenced_current
                FROM admin_review_signals
                WHERE id = NEW.signal_id;
                IF referenced_case_id IS NULL
                   OR (
                       referenced_case_id <> owning_case_id
                       AND NOT EXISTS (
                           SELECT 1 FROM admin_review_cases
                           WHERE id = referenced_case_id
                             AND merged_into_case_id = owning_case_id
                       )
                   )
                   OR NEW.was_current IS DISTINCT FROM referenced_current THEN
                    RAISE EXCEPTION 'resolution signal ownership is invalid';
                END IF;
            ELSIF NEW.reference_type = 'enforcement_action' THEN
                SELECT target_review_case_id, action_type
                INTO referenced_case_id, referenced_action_type
                FROM admin_actions
                WHERE id = NEW.admin_action_id;
                IF referenced_case_id IS NULL
                   OR referenced_action_type IN (
                       'create_review_case', 'close_review_case',
                       'add_review_case_note', 'assign_review_case',
                       'reopen_review_case', 'merge_review_case'
                   )
                   OR (
                       referenced_case_id <> owning_case_id
                       AND NOT EXISTS (
                           SELECT 1 FROM admin_review_cases
                           WHERE id = referenced_case_id
                             AND merged_into_case_id = owning_case_id
                       )
                   )
                   OR (
                       NEW.admin_action_id IS DISTINCT FROM owning_event_action_id
                       AND NOT EXISTS (
                           SELECT 1 FROM admin_review_case_events
                           WHERE review_case_id = referenced_case_id
                             AND event_type = 'enforcement_action_linked'
                             AND admin_action_id = NEW.admin_action_id
                       )
                   ) THEN
                    RAISE EXCEPTION 'resolution enforcement action ownership is invalid';
                END IF;
            ELSIF NEW.reference_type = 'source_case' THEN
                IF NEW.source_case_id = owning_case_id
                   OR NOT EXISTS (
                       SELECT 1 FROM admin_review_cases
                       WHERE id = NEW.source_case_id
                         AND merged_into_case_id = owning_case_id
                   ) THEN
                    RAISE EXCEPTION 'resolution source case ownership is invalid';
                END IF;
            END IF;
            IF owning_event_xmin IS DISTINCT FROM pg_current_xact_id()::xid THEN
                RAISE EXCEPTION 'closure resolution reference set is sealed';
            END IF;
            RETURN NEW;
        END;
        $$
    """,
        safety_basis="fixed trigger function validating resolution-reference ownership",
    ),
    RawSqlAllowance(
        source_path="backend/alembic/versions/0066_create_admin_review_case_resolution_references_table.py",
        constructor="op.execute",
        expression="""
        CREATE TRIGGER trg_admin_review_case_resolution_refs_validate_insert
        BEFORE INSERT ON admin_review_case_resolution_references
        FOR EACH ROW EXECUTE FUNCTION validate_admin_review_case_resolution_ref_insert()
    """,
        safety_basis="fixed resolution-reference insert-validation trigger",
    ),
    RawSqlAllowance(
        source_path="backend/alembic/versions/0066_create_admin_review_case_resolution_references_table.py",
        constructor="op.execute",
        expression="""
        CREATE FUNCTION reject_admin_review_case_resolution_ref_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'admin review case resolution references are immutable';
        END;
        $$
    """,
        safety_basis="fixed trigger function enforcing immutable resolution references",
    ),
    RawSqlAllowance(
        source_path="backend/alembic/versions/0066_create_admin_review_case_resolution_references_table.py",
        constructor="op.execute",
        expression="""
        CREATE TRIGGER trg_admin_review_case_resolution_refs_immutable
        BEFORE UPDATE OR DELETE ON admin_review_case_resolution_references
        FOR EACH ROW EXECUTE FUNCTION reject_admin_review_case_resolution_ref_mutation()
    """,
        safety_basis="fixed immutable resolution-reference trigger",
    ),
    RawSqlAllowance(
        source_path="backend/alembic/versions/0066_create_admin_review_case_resolution_references_table.py",
        constructor="op.execute",
        expression="DROP TRIGGER IF EXISTS trg_admin_review_case_resolution_refs_validate_insert ON admin_review_case_resolution_references",
        safety_basis="fixed resolution-reference validation trigger teardown",
    ),
    RawSqlAllowance(
        source_path="backend/alembic/versions/0066_create_admin_review_case_resolution_references_table.py",
        constructor="op.execute",
        expression="DROP FUNCTION IF EXISTS validate_admin_review_case_resolution_ref_insert()",
        safety_basis="fixed resolution-reference validation function teardown",
    ),
    RawSqlAllowance(
        source_path="backend/alembic/versions/0066_create_admin_review_case_resolution_references_table.py",
        constructor="op.execute",
        expression="DROP TRIGGER trg_admin_review_case_resolution_refs_immutable ON admin_review_case_resolution_references",
        safety_basis="fixed immutable resolution-reference trigger teardown",
    ),
    RawSqlAllowance(
        source_path="backend/alembic/versions/0066_create_admin_review_case_resolution_references_table.py",
        constructor="op.execute",
        expression="DROP FUNCTION reject_admin_review_case_resolution_ref_mutation()",
        safety_basis="fixed immutable resolution-reference function teardown",
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
