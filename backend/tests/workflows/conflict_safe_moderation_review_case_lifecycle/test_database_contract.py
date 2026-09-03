from __future__ import annotations

import importlib.util
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import (
    CheckConstraint,
    ForeignKeyConstraint,
    UniqueConstraint,
    delete,
    func,
    inspect,
    select,
    text,
    update,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import DBAPIError, IntegrityError

from backend.models import (
    AdminAction,
    AdminContentModerationFinding,
    AdminReviewCase,
    AdminReviewCaseEvent,
    AdminReviewCaseNote,
    AdminReviewCaseResolutionReference,
    AdminReviewSignal,
)
from backend.schemas.admin_review_schema import (
    AdminReviewCaseAssignment,
    AdminReviewCaseClose,
    AdminReviewCaseMerge,
    AdminReviewCaseNoteCreate,
    AdminReviewCaseReopen,
)
from backend.services.admin_action_service import record_admin_action
from backend.services.admin_review_service import (
    SOURCE_RECONCILIATION_RULE_ID,
    SOURCE_RECONCILIATION_RULE_VERSION,
    TARGET_LIFECYCLE_RULE_ID,
    TARGET_LIFECYCLE_RULE_VERSION,
    add_review_case_note,
    apply_review_signal_current_state,
    assign_review_case,
    close_review_case,
    create_case_event,
    create_internal_review_signal,
    link_admin_action_to_open_review_case,
    merge_review_case,
    reopen_review_case,
    validate_case_event_metadata,
)
from backend.services.moderation_surfacing_service import surface_community_game_text
from backend.tests.workflows.conflict_safe_moderation_review_case_lifecycle.conftest import (
    create_chat_case,
    create_content_case,
    create_sub_content_case,
    seed_admin,
    seed_game,
    seed_sub_post,
    session,
)

pytestmark = pytest.mark.suite_type("ordinary")

ROOT = Path(__file__).resolve().parents[4]
TEST_TARGET_ID = "11111111-1111-4111-8111-111111111111"
TEST_ADMIN_ID = "22222222-2222-4222-8222-222222222222"
PASS_OWNED_MIGRATIONS = (
    "backend/alembic/versions/0004_create_admin_actions_table.py",
    "backend/alembic/versions/0053_create_admin_review_cases_table.py",
    "backend/alembic/versions/0057_create_admin_review_case_notes_table.py",
    "backend/alembic/versions/0059_create_admin_review_case_events_table.py",
    "backend/alembic/versions/0066_create_admin_review_case_resolution_references_table.py",
)

NON_CLOSURE_EVENT_TYPES = (
    "case_created",
    "finding_attached",
    "finding_cleared",
    "signal_attached",
    "signal_superseded",
    "signal_reactivated",
    "note_added",
    "assignment_changed",
    "enforcement_action_linked",
    "reopened",
    "merged_into",
    "merged_from",
)


def latest_case_event(
    db,
    review_case_id: uuid.UUID,
    event_type: str,
) -> AdminReviewCaseEvent:
    event = db.scalar(
        select(AdminReviewCaseEvent)
        .where(
            AdminReviewCaseEvent.review_case_id == review_case_id,
            AdminReviewCaseEvent.event_type == event_type,
        )
        .order_by(AdminReviewCaseEvent.event_sequence.desc())
        .limit(1)
    )
    assert event is not None
    return event


def normalize_schema_sql(value) -> str | None:
    if value is None:
        return None
    if hasattr(value, "arg"):
        value = value.arg
    normalized = re.sub(r"\s+", " ", str(value).strip().lower())
    return re.sub(r"\b[a-z_][a-z0-9_]*\.", "", normalized)


def column_signature(column) -> tuple[object, ...]:
    return (
        column.name,
        str(column.type.compile(dialect=postgresql.dialect())).lower(),
        bool(column.nullable),
        bool(column.primary_key),
        normalize_schema_sql(column.server_default),
    )


def check_signatures(items) -> dict[str, str | None]:
    return {
        item.name: normalize_schema_sql(item.sqltext)
        for item in items
        if isinstance(item, CheckConstraint)
    }


def foreign_key_signatures(items) -> set[tuple[object, ...]]:
    return {
        (
            tuple(item.column_keys),
            tuple(element.target_fullname for element in item.elements),
            item.ondelete,
        )
        for item in items
        if isinstance(item, ForeignKeyConstraint)
    }


def unique_signatures(items) -> set[tuple[object, ...]]:
    return {
        (
            item.name,
            tuple(item.columns.keys())
            or tuple(str(value) for value in item._pending_colargs),
        )
        for item in items
        if isinstance(item, UniqueConstraint) and item.name is not None
    }


def index_expression(value) -> str:
    if isinstance(value, str):
        return value
    return str(value.compile(dialect=postgresql.dialect()))


def index_signature(name, expressions, unique, where=None) -> tuple[object, ...]:
    return (
        name,
        tuple(normalize_schema_sql(index_expression(item)) for item in expressions),
        bool(unique),
        normalize_schema_sql(where),
    )


def quote_postgresql_identifier(value: str) -> str:
    return f'"{value.replace(chr(34), chr(34) * 2)}"'


def live_postgresql_check_definitions(connection, relation_name: str) -> dict[str, str]:
    return {
        name: normalize_schema_sql(definition) or ""
        for name, definition in connection.execute(
            text(
                "SELECT constraint_record.conname, "
                "pg_get_constraintdef(constraint_record.oid, false) "
                "FROM pg_constraint AS constraint_record "
                "WHERE constraint_record.conrelid = to_regclass(:relation_name) "
                "AND constraint_record.contype = 'c'"
            ),
            {"relation_name": relation_name},
        ).all()
    }


def live_postgresql_partial_index_predicates(
    connection, relation_name: str
) -> dict[str, str]:
    return {
        name: normalize_schema_sql(predicate) or ""
        for name, predicate in connection.execute(
            text(
                "SELECT index_class.relname, "
                "pg_get_expr(index_record.indpred, index_record.indrelid, false) "
                "FROM pg_index AS index_record "
                "JOIN pg_class AS index_class "
                "ON index_class.oid = index_record.indexrelid "
                "WHERE index_record.indrelid = to_regclass(:relation_name) "
                "AND index_record.indpred IS NOT NULL"
            ),
            {"relation_name": relation_name},
        ).all()
    }


def model_postgresql_semantic_definitions(
    connection, table_name: str, model_table
) -> tuple[dict[str, str], dict[str, str]]:
    temp_table_name = f"wsb_{table_name[:32]}_{uuid.uuid4().hex[:8]}"
    quoted_temp_table = quote_postgresql_identifier(temp_table_name)
    connection.execute(
        text(
            f"CREATE TEMP TABLE {quoted_temp_table} "
            f"(LIKE {quote_postgresql_identifier(table_name)} INCLUDING DEFAULTS)"
        )
    )
    temp_relation_name = f"pg_temp.{temp_table_name}"

    expected_checks: dict[str, str] = {}
    model_checks = sorted(
        (
            constraint
            for constraint in model_table.constraints
            if isinstance(constraint, CheckConstraint)
        ),
        key=lambda constraint: constraint.name,
    )
    for position, constraint in enumerate(model_checks):
        temporary_constraint_name = f"expected_check_{position}"
        connection.execute(
            text(
                f"ALTER TABLE {quoted_temp_table} ADD CONSTRAINT "
                f"{quote_postgresql_identifier(temporary_constraint_name)} "
                f"CHECK ({constraint.sqltext})"
            )
        )
        temporary_definitions = live_postgresql_check_definitions(
            connection, temp_relation_name
        )
        expected_checks[constraint.name] = temporary_definitions[
            temporary_constraint_name
        ]

    expected_predicates: dict[str, str] = {}
    partial_indexes = sorted(
        (
            index
            for index in model_table.indexes
            if index.dialect_options["postgresql"].get("where") is not None
        ),
        key=lambda index: index.name,
    )
    for position, index in enumerate(partial_indexes):
        temporary_index_name = f"expected_index_{position}"
        expressions = ", ".join(
            normalize_schema_sql(index_expression(expression)) or ""
            for expression in index.expressions
        )
        predicate = normalize_schema_sql(
            index.dialect_options["postgresql"].get("where")
        )
        assert predicate is not None
        connection.execute(
            text(
                f"CREATE INDEX {quote_postgresql_identifier(temporary_index_name)} "
                f"ON {quoted_temp_table} ({expressions}) WHERE {predicate}"
            )
        )
        temporary_predicates = live_postgresql_partial_index_predicates(
            connection, temp_relation_name
        )
        expected_predicates[index.name] = temporary_predicates[temporary_index_name]

    return expected_checks, expected_predicates


class MigrationOperationsRecorder:
    def __init__(self) -> None:
        self.tables: dict[str, tuple[object, ...]] = {}
        self.indexes: dict[str, list[tuple[object, ...]]] = {}
        self.uniques: dict[str, list[tuple[object, ...]]] = {}
        self.sql: list[str] = []

    def create_table(self, table_name, *items, **kwargs) -> None:
        del kwargs
        self.tables[table_name] = items

    def create_index(
        self, name, table_name, expressions, *, unique=False, **kwargs
    ) -> None:
        self.indexes.setdefault(table_name, []).append(
            index_signature(
                name,
                expressions,
                unique,
                kwargs.get("postgresql_where"),
            )
        )

    def create_unique_constraint(self, name, table_name, columns, **kwargs) -> None:
        del kwargs
        self.uniques.setdefault(table_name, []).append((name, tuple(columns)))

    def execute(self, statement, *args, **kwargs) -> None:
        del args, kwargs
        self.sql.append(str(statement))


def record_pass_owned_migrations() -> MigrationOperationsRecorder:
    recorder = MigrationOperationsRecorder()
    for index, relative_path in enumerate(PASS_OWNED_MIGRATIONS):
        path = ROOT / relative_path
        spec = importlib.util.spec_from_file_location(
            f"ws03_05b_migration_{index}", path
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.op = recorder
        module.upgrade()
    return recorder


def constraint_name(error: IntegrityError) -> str | None:
    return getattr(getattr(error.orig, "diag", None), "constraint_name", None)


def direct_case(*, case_type: str, category: str, target_field: str, target_id):
    return AdminReviewCase(
        id=uuid.uuid4(),
        case_type=case_type,
        case_status="open",
        case_category=category,
        priority="attention",
        title="Direct constraint fixture",
        summary="Direct PostgreSQL case identity proof.",
        case_version=1,
        creation_reason=(
            "content_moderation_finding"
            if category == "content_moderation"
            else "chat_moderation_detection"
        ),
        **{target_field: target_id},
    )


@pytest.mark.requirement("WS03-05B-R1", "WS03-05B-R7")
def test_four_moderation_identities_are_unique_without_conflating_categories() -> None:
    with session() as db:
        game = seed_game(db)
        post = seed_sub_post(db)
        rows = [
            direct_case(
                case_type="community_game",
                category=category,
                target_field="target_game_id",
                target_id=game.id,
            )
            for category in ("content_moderation", "chat_moderation")
        ] + [
            direct_case(
                case_type="need_a_sub",
                category=category,
                target_field="target_sub_post_id",
                target_id=post.id,
            )
            for category in ("content_moderation", "chat_moderation")
        ]
        db.add_all(rows)
        db.commit()
        assert (
            len(
                db.scalars(
                    select(AdminReviewCase).where(
                        AdminReviewCase.id.in_([row.id for row in rows])
                    )
                ).all()
            )
            == 4
        )

        for case_type, category, target_field, target_id, expected_constraint in (
            (
                "community_game",
                "content_moderation",
                "target_game_id",
                game.id,
                "uq_admin_review_cases_open_community_game_moderation",
            ),
            (
                "need_a_sub",
                "chat_moderation",
                "target_sub_post_id",
                post.id,
                "uq_admin_review_cases_open_need_sub_moderation",
            ),
        ):
            db.add(
                direct_case(
                    case_type=case_type,
                    category=category,
                    target_field=target_field,
                    target_id=target_id,
                )
            )
            with pytest.raises(IntegrityError) as duplicate:
                db.flush()
            assert constraint_name(duplicate.value) == expected_constraint
            db.rollback()

        unrelated_one = direct_case(
            case_type="user",
            category="content_moderation",
            target_field="target_user_id",
            target_id=game.host_user_id,
        )
        unrelated_two = direct_case(
            case_type="user",
            category="content_moderation",
            target_field="target_user_id",
            target_id=game.host_user_id,
        )
        db.add_all([unrelated_one, unrelated_two])
        db.commit()


@pytest.mark.requirement("WS03-05B-R1", "WS03-05B-R2", "WS03-05B-R7")
@pytest.mark.parametrize(
    ("values", "expected_constraint"),
    (
        (
            {
                "case_status": "closed",
                "closure_outcome": "no_action_needed",
                "closure_reason": "Missing mode.",
                "closed_at": "now()",
            },
            "ck_admin_review_cases_closure_state",
        ),
        (
            {
                "case_status": "closed",
                "closure_outcome": "no_action_needed",
                "closure_reason": "Missing automatic rule.",
                "closure_mode": "automatic",
                "closed_at": "now()",
            },
            "ck_admin_review_cases_resolution_shape",
        ),
    ),
)
def test_postgresql_rejects_incomplete_resolution_shapes(
    values, expected_constraint
) -> None:
    with session() as db:
        game = seed_game(db)
        review_case = create_content_case(db, game)
        assignments = []
        parameters = {"case_id": review_case.id}
        for index, (column, value) in enumerate(values.items()):
            if value == "now()":
                assignments.append(f"{column} = now()")
            else:
                key = f"value_{index}"
                assignments.append(f"{column} = :{key}")
                parameters[key] = value
        with pytest.raises(IntegrityError) as invalid:
            db.execute(
                text(
                    "UPDATE admin_review_cases SET "
                    + ", ".join(assignments)
                    + " WHERE id = :case_id"
                ),
                parameters,
            )
            db.commit()
        assert constraint_name(invalid.value) == expected_constraint


@pytest.mark.requirement("WS03-05B-R1", "WS03-05B-R2", "WS03-05B-R7")
def test_primary_moderation_target_identity_cannot_change_or_disappear() -> None:
    with session() as db:
        game = seed_game(db)
        other_game = seed_game(db)
        post = seed_sub_post(db)
        other_post = seed_sub_post(db)
        game_case = create_content_case(db, game)
        post_case = create_sub_content_case(db, post)

        mutations = (
            (game_case.id, {"target_game_id": other_game.id}),
            (post_case.id, {"target_sub_post_id": other_post.id}),
            (
                game_case.id,
                {"target_game_id": None, "target_sub_post_id": post.id},
            ),
            (game_case.id, {"case_type": "need_a_sub"}),
            (game_case.id, {"case_category": "chat_moderation"}),
        )
        for review_case_id, values in mutations:
            with pytest.raises(DBAPIError, match="identity is immutable"):
                db.execute(
                    update(AdminReviewCase)
                    .where(AdminReviewCase.id == review_case_id)
                    .values(**values)
                )
                db.flush()
            db.rollback()

        assert db.get(AdminReviewCase, game_case.id).target_game_id == game.id
        assert db.get(AdminReviewCase, post_case.id).target_sub_post_id == post.id


@pytest.mark.requirement("WS03-05B-R1", "WS03-05B-R2", "WS03-05B-R7")
def test_primary_target_hard_deletion_is_restricted_by_retained_case_identity() -> None:
    with session() as db:
        game = seed_game(db)
        post = seed_sub_post(db)
        game_case = create_content_case(db, game)
        post_case = create_sub_content_case(db, post)
        game_model = type(game)
        post_model = type(post)

        with pytest.raises(IntegrityError):
            db.execute(delete(game_model).where(game_model.id == game.id))
            db.flush()
        db.rollback()
        assert db.get(AdminReviewCase, game_case.id).target_game_id == game.id

        with pytest.raises(IntegrityError):
            db.execute(delete(post_model).where(post_model.id == post.id))
            db.flush()
        db.rollback()
        assert db.get(AdminReviewCase, post_case.id).target_sub_post_id == post.id


@pytest.mark.requirement("WS03-05B-R3", "WS03-05B-R7")
def test_event_builder_and_postgresql_reject_impossible_reference_shapes() -> None:
    with session() as db:
        game = seed_game(db)
        review_case = create_content_case(db, game)
        with pytest.raises(ValueError, match="missing its required reference"):
            create_case_event(
                db,
                review_case_id=review_case.id,
                event_type="finding_attached",
                automation_rule_id=SOURCE_RECONCILIATION_RULE_ID,
                automation_rule_version=SOURCE_RECONCILIATION_RULE_VERSION,
                event_metadata={
                    "priority_before": "attention",
                    "priority_after": "attention",
                },
            )
        db.rollback()

        review_case = db.get(AdminReviewCase, review_case.id)
        event = AdminReviewCaseEvent(
            id=uuid.uuid4(),
            review_case_id=review_case.id,
            event_type="note_added",
            event_sequence=review_case.case_version + 1,
            case_version=review_case.case_version + 1,
            actor_kind="automation",
            automation_rule_id="invalid.fixture",
            automation_rule_version="1",
        )
        db.add(event)
        with pytest.raises(IntegrityError) as invalid:
            db.flush()
        assert constraint_name(invalid.value) in {
            "ck_admin_review_case_events_reference_shape",
            "ck_admin_review_case_events_transition_actor",
        }


@pytest.mark.requirement("WS03-05B-R3", "WS03-05B-R7")
@pytest.mark.parametrize(
    ("event_type", "actor_kind", "metadata"),
    (
        ("case_created", "automation", {"source": 7}),
        (
            "assignment_changed",
            "admin",
            {"previous_assignee_id": None, "next_assignee_id": []},
        ),
        (
            "closed",
            "admin",
            {
                "closure_mode": "manual",
                "reason": "Invalid metadata fixture.",
                "target_type": "community_game",
                "target_id": TEST_TARGET_ID,
                "closed_by_user_id": TEST_ADMIN_ID,
                "previous_assignee_id": None,
                "before": {"case_status": "open", "closure_outcome": None},
                "after": {
                    "case_status": "closed",
                    "closure_outcome": "no_action_needed",
                },
                "unexpected": True,
            },
        ),
        ("reopened", "admin", {"prior_resolution_mode": "manual"}),
        (
            "merged_into",
            "admin",
            {
                "source_resolution_mode": "manual",
                "source_resolution_outcome": None,
            },
        ),
    ),
)
def test_event_metadata_contract_rejects_wrong_types_and_unexpected_fields(
    event_type: str,
    actor_kind: str,
    metadata: dict[str, object],
) -> None:
    with pytest.raises((TypeError, ValueError)):
        validate_case_event_metadata(
            event_type=event_type,
            actor_kind=actor_kind,
            event_metadata=metadata,
        )


EVENT_ACTOR_BY_TYPE = (
    ("case_created", "automation"),
    ("finding_attached", "automation"),
    ("finding_cleared", "automation"),
    ("signal_attached", "automation"),
    ("signal_superseded", "automation"),
    ("signal_reactivated", "automation"),
    ("note_added", "admin"),
    ("assignment_changed", "admin"),
    ("enforcement_action_linked", "admin"),
    ("closed", "admin"),
    ("reopened", "admin"),
    ("merged_into", "admin"),
    ("merged_from", "admin"),
)


@pytest.mark.requirement("WS03-05B-R3", "WS03-05B-R7")
@pytest.mark.parametrize(("event_type", "actor_kind"), EVENT_ACTOR_BY_TYPE)
@pytest.mark.parametrize(
    ("metadata_label", "metadata"),
    (("missing", None), ("empty", {})),
)
def test_every_event_validator_rejects_missing_or_empty_metadata(
    event_type: str,
    actor_kind: str,
    metadata_label: str,
    metadata: dict[str, object] | None,
) -> None:
    del metadata_label
    with pytest.raises(ValueError, match="metadata"):
        validate_case_event_metadata(
            event_type=event_type,
            actor_kind=actor_kind,
            event_metadata=metadata,
        )


@pytest.mark.requirement("WS03-05B-R3", "WS03-05B-R7")
@pytest.mark.parametrize(("event_type", "actor_kind"), EVENT_ACTOR_BY_TYPE)
@pytest.mark.parametrize(
    ("metadata_label", "metadata"),
    (("missing", None), ("empty", {})),
)
def test_postgresql_rejects_missing_or_empty_metadata_for_every_event_type(
    event_type: str,
    actor_kind: str,
    metadata_label: str,
    metadata: dict[str, object] | None,
) -> None:
    del metadata_label
    with session() as db:
        game = seed_game(db)
        review_case = create_content_case(db, game)
        actor_user_id = None
        automation_rule_id = SOURCE_RECONCILIATION_RULE_ID
        automation_rule_version = SOURCE_RECONCILIATION_RULE_VERSION
        if actor_kind == "admin":
            actor_user_id = seed_admin(db).id
            automation_rule_id = None
            automation_rule_version = None
        db.add(
            AdminReviewCaseEvent(
                id=uuid.uuid4(),
                review_case_id=review_case.id,
                event_type=event_type,
                event_sequence=review_case.case_version + 1,
                case_version=review_case.case_version + 1,
                actor_kind=actor_kind,
                actor_user_id=actor_user_id,
                automation_rule_id=automation_rule_id,
                automation_rule_version=automation_rule_version,
                event_metadata=metadata,
            )
        )
        with pytest.raises(DBAPIError, match="metadata"):
            db.flush()


@pytest.mark.requirement("WS03-05B-R3", "WS03-05B-R7")
@pytest.mark.parametrize(
    ("event_type", "actor_kind", "metadata"),
    (
        (
            "finding_attached",
            "automation",
            {
                "finding_type": "sensitive_text",
                "risk_area": "privacy",
                "source_field": "description",
                "priority_before": None,
                "priority_after": "attention",
            },
        ),
        (
            "finding_cleared",
            "automation",
            {
                "finding_type": "sensitive_text",
                "risk_area": "privacy",
                "source_field": "description",
                "priority_before": "attention",
                "priority_after": 7,
            },
        ),
        (
            "signal_attached",
            "automation",
            {
                "created_case": True,
                "source": "chat_moderation",
                "priority_before": "attention",
                "priority_after": None,
            },
        ),
        (
            "signal_superseded",
            "automation",
            {"priority_before": {}, "priority_after": "attention"},
        ),
        (
            "signal_reactivated",
            "automation",
            {"priority_before": "attention", "priority_after": "low"},
        ),
        (
            "closed",
            "admin",
            {
                "closure_mode": None,
                "reason": "Invalid metadata fixture.",
                "target_type": "community_game",
                "target_id": TEST_TARGET_ID,
                "closed_by_user_id": TEST_ADMIN_ID,
                "previous_assignee_id": None,
                "before": {"case_status": "open", "closure_outcome": None},
                "after": {
                    "case_status": "closed",
                    "closure_outcome": "no_action_needed",
                },
            },
        ),
        (
            "closed",
            "automation",
            {
                "closure_mode": "automatic",
                "closure_source": False,
                "lifecycle_action": "admin_soft_deleted",
                "target_type": "community_game",
                "target_id": TEST_TARGET_ID,
                "reason": "Invalid metadata fixture.",
                "previous_target_state": "active",
                "new_target_state": "soft_deleted",
                "trigger_actor_type": "admin",
                "trigger_actor_user_id": None,
                "closed_by_user_id": None,
                "previous_assignee_id": None,
                "linked_admin_action_id": None,
                "before": {"case_status": "open", "closure_outcome": None},
                "after": {
                    "case_status": "closed",
                    "closure_outcome": "no_action_needed",
                },
            },
        ),
        (
            "closed",
            "admin",
            {
                "closure_mode": "manual",
                "reason": "Invalid metadata fixture.",
                "target_type": "community_game",
                "target_id": TEST_TARGET_ID,
                "closed_by_user_id": TEST_ADMIN_ID,
                "previous_assignee_id": None,
                "before": {"case_status": None, "closure_outcome": None},
                "after": {
                    "case_status": "closed",
                    "closure_outcome": "no_action_needed",
                },
            },
        ),
        (
            "closed",
            "admin",
            {
                "closure_mode": "manual",
                "reason": "Invalid metadata fixture.",
                "target_type": "community_game",
                "target_id": TEST_TARGET_ID,
                "closed_by_user_id": TEST_ADMIN_ID,
                "previous_assignee_id": None,
                "before": {"case_status": "open", "closure_outcome": None},
                "after": {
                    "case_status": [],
                    "closure_outcome": "no_action_needed",
                },
            },
        ),
        (
            "closed",
            "admin",
            {
                "closure_mode": "manual",
                "reason": "Invalid metadata fixture.",
                "target_type": "community_game",
                "target_id": TEST_TARGET_ID,
                "closed_by_user_id": TEST_ADMIN_ID,
                "previous_assignee_id": None,
                "before": {"case_status": "open", "closure_outcome": None},
                "after": {
                    "case_status": "closed",
                    "closure_outcome": "unsupported",
                },
            },
        ),
        (
            "reopened",
            "admin",
            {
                "prior_resolution_mode": None,
                "prior_resolution_outcome": "no_action_needed",
            },
        ),
        (
            "reopened",
            "admin",
            {
                "prior_resolution_mode": "manual",
                "prior_resolution_outcome": {"value": "no_action_needed"},
            },
        ),
    ),
)
def test_postgresql_finite_event_metadata_scalars_fail_closed(
    event_type: str,
    actor_kind: str,
    metadata: dict[str, object],
) -> None:
    with session() as db:
        game = seed_game(db)
        review_case = create_content_case(db, game)
        admin = seed_admin(db)
        db.add(
            AdminReviewCaseEvent(
                id=uuid.uuid4(),
                review_case_id=review_case.id,
                event_type=event_type,
                event_sequence=review_case.case_version + 1,
                case_version=review_case.case_version + 1,
                actor_kind=actor_kind,
                actor_user_id=admin.id if actor_kind == "admin" else None,
                automation_rule_id=(
                    SOURCE_RECONCILIATION_RULE_ID
                    if actor_kind == "automation"
                    else None
                ),
                automation_rule_version=(
                    SOURCE_RECONCILIATION_RULE_VERSION
                    if actor_kind == "automation"
                    else None
                ),
                event_metadata=metadata,
            )
        )
        with pytest.raises(DBAPIError, match="metadata|projection"):
            db.flush()


@pytest.mark.requirement("WS03-05B-R3", "WS03-05B-R7")
@pytest.mark.parametrize("projection_field", ("before", "after"))
@pytest.mark.parametrize(
    ("projection_label", "projection"),
    (("omitted", None), ("null", None), ("empty", {})),
)
def test_event_validator_rejects_missing_or_empty_nested_closure_projections(
    projection_field: str,
    projection_label: str,
    projection: dict[str, object] | None,
) -> None:
    metadata: dict[str, object] = {
        "closure_mode": "manual",
        "reason": "Nested projection fixture.",
        "target_type": "community_game",
        "target_id": TEST_TARGET_ID,
        "closed_by_user_id": TEST_ADMIN_ID,
        "previous_assignee_id": None,
        "before": {"case_status": "open", "closure_outcome": None},
        "after": {
            "case_status": "closed",
            "closure_outcome": "no_action_needed",
        },
    }
    if projection_label == "omitted":
        metadata.pop(projection_field)
    else:
        metadata[projection_field] = projection

    with pytest.raises(ValueError, match="metadata|projection"):
        validate_case_event_metadata(
            event_type="closed",
            actor_kind="admin",
            event_metadata=metadata,
        )


@pytest.mark.requirement("WS03-05B-R3", "WS03-05B-R7")
@pytest.mark.parametrize("projection_field", ("before", "after"))
@pytest.mark.parametrize(
    ("projection_label", "projection"),
    (("omitted", None), ("null", None), ("empty", {})),
)
def test_postgresql_rejects_missing_or_empty_nested_closure_projections(
    projection_field: str,
    projection_label: str,
    projection: dict[str, object] | None,
) -> None:
    with session() as db:
        game = seed_game(db)
        review_case = create_content_case(db, game)
        admin = seed_admin(db)
        metadata: dict[str, object] = {
            "closure_mode": "manual",
            "reason": "Nested projection fixture.",
            "target_type": "community_game",
            "target_id": str(game.id),
            "closed_by_user_id": str(admin.id),
            "previous_assignee_id": None,
            "before": {"case_status": "open", "closure_outcome": None},
            "after": {
                "case_status": "closed",
                "closure_outcome": "no_action_needed",
            },
        }
        if projection_label == "omitted":
            metadata.pop(projection_field)
        else:
            metadata[projection_field] = projection
        db.add(
            AdminReviewCaseEvent(
                id=uuid.uuid4(),
                review_case_id=review_case.id,
                event_type="closed",
                event_sequence=review_case.case_version + 1,
                case_version=review_case.case_version + 1,
                actor_kind="admin",
                actor_user_id=admin.id,
                event_metadata=metadata,
            )
        )
        with pytest.raises(DBAPIError, match="closure"):
            db.flush()


@pytest.mark.requirement("WS03-05B-R3", "WS03-05B-R7")
def test_event_builder_rejects_cross_case_children_unrelated_actions_and_links() -> (
    None
):
    with session() as db:
        first_game = seed_game(db)
        second_game = seed_game(db)
        admin = seed_admin(db)
        first_case = create_content_case(db, first_game)
        second_case = create_content_case(db, second_game)
        second_finding = db.scalar(
            select(AdminContentModerationFinding).where(
                AdminContentModerationFinding.review_case_id == second_case.id
            )
        )

        with pytest.raises(ValueError, match="finding must belong"):
            create_case_event(
                db,
                review_case_id=first_case.id,
                event_type="finding_attached",
                content_moderation_finding_id=second_finding.id,
                automation_rule_id=SOURCE_RECONCILIATION_RULE_ID,
                automation_rule_version=SOURCE_RECONCILIATION_RULE_VERSION,
                event_metadata={
                    "finding_type": second_finding.finding_type,
                    "risk_area": second_finding.risk_area,
                    "source_field": second_finding.source_field,
                    "priority_before": "attention",
                    "priority_after": "attention",
                },
            )

        unrelated_action = AdminAction(
            id=uuid.uuid4(),
            admin_user_id=admin.id,
            action_type="assign_review_case",
            target_review_case_id=second_case.id,
            reason="Unrelated action fixture.",
            idempotency_key="ws03-05b-unrelated-event-action",
        )
        db.add(unrelated_action)
        with pytest.raises(ValueError, match="targets another review case"):
            create_case_event(
                db,
                review_case_id=first_case.id,
                event_type="assignment_changed",
                actor_user_id=admin.id,
                admin_action_id=unrelated_action.id,
                event_metadata={
                    "previous_assignee_id": None,
                    "next_assignee_id": str(admin.id),
                },
            )

        reopen_action = AdminAction(
            id=uuid.uuid4(),
            admin_user_id=admin.id,
            action_type="reopen_review_case",
            target_review_case_id=first_case.id,
            reason="Wrong related event fixture.",
            idempotency_key="ws03-05b-wrong-related-event",
        )
        db.add(reopen_action)
        unrelated_event_id = db.scalar(
            select(AdminReviewCaseEvent.id)
            .where(AdminReviewCaseEvent.review_case_id == second_case.id)
            .order_by(AdminReviewCaseEvent.event_sequence.asc())
            .limit(1)
        )
        with pytest.raises(ValueError, match="prior closure"):
            create_case_event(
                db,
                review_case_id=first_case.id,
                event_type="reopened",
                actor_user_id=admin.id,
                admin_action_id=reopen_action.id,
                related_event_id=unrelated_event_id,
                event_metadata={
                    "prior_resolution_mode": "manual",
                    "prior_resolution_outcome": "no_action_needed",
                },
            )

        merge_action = AdminAction(
            id=uuid.uuid4(),
            admin_user_id=admin.id,
            action_type="merge_review_case",
            target_review_case_id=first_case.id,
            reason="Self-link fixture.",
            idempotency_key="ws03-05b-self-link-event",
        )
        db.add(merge_action)
        with pytest.raises(ValueError, match="own case"):
            create_case_event(
                db,
                review_case_id=first_case.id,
                event_type="merged_into",
                actor_user_id=admin.id,
                admin_action_id=merge_action.id,
                related_case_id=first_case.id,
                related_event_id=unrelated_event_id,
                event_metadata={
                    "source_resolution_mode": "manual",
                    "source_resolution_outcome": "no_action_needed",
                },
            )


@pytest.mark.requirement("WS03-05B-R3", "WS03-05B-R7")
@pytest.mark.parametrize(
    ("scenario", "expected_message"),
    (
        ("cross_case_finding", "finding ownership"),
        ("malformed_metadata", "assignment_changed event metadata"),
        ("wrong_related_event", "reopen event does not match"),
        ("self_link", "merge event case relationship"),
        ("sequence_gap", "event sequence is not gap-free"),
    ),
)
def test_postgresql_rejects_semantically_false_immutable_events(
    scenario: str,
    expected_message: str,
) -> None:
    with session() as db:
        first_game = seed_game(db)
        second_game = seed_game(db)
        admin = seed_admin(db)
        first_case = create_content_case(db, first_game)
        second_case = create_content_case(db, second_game)
        second_finding = db.scalar(
            select(AdminContentModerationFinding).where(
                AdminContentModerationFinding.review_case_id == second_case.id
            )
        )
        unrelated_event_id = db.scalar(
            select(AdminReviewCaseEvent.id)
            .where(AdminReviewCaseEvent.review_case_id == second_case.id)
            .order_by(AdminReviewCaseEvent.event_sequence.asc())
            .limit(1)
        )

        action_type = {
            "malformed_metadata": "assign_review_case",
            "wrong_related_event": "reopen_review_case",
            "self_link": "merge_review_case",
        }.get(scenario)
        action = None
        if action_type is not None:
            action = AdminAction(
                id=uuid.uuid4(),
                admin_user_id=admin.id,
                action_type=action_type,
                target_review_case_id=first_case.id,
                reason="Direct immutable-event rejection fixture.",
                idempotency_key=f"ws03-05b-direct-event-{scenario}",
            )
            db.add(action)
            db.flush()

        if scenario != "sequence_gap":
            first_case.case_version += 1
            db.add(first_case)
            db.flush()
        event_sequence = (
            first_case.case_version + 2
            if scenario == "sequence_gap"
            else first_case.case_version
        )
        kwargs: dict[str, object] = {
            "id": uuid.uuid4(),
            "review_case_id": first_case.id,
            "event_sequence": event_sequence,
            "case_version": event_sequence,
            "created_at": datetime.now(timezone.utc),
        }
        if scenario == "cross_case_finding":
            kwargs.update(
                event_type="finding_attached",
                actor_kind="automation",
                automation_rule_id=SOURCE_RECONCILIATION_RULE_ID,
                automation_rule_version=SOURCE_RECONCILIATION_RULE_VERSION,
                content_moderation_finding_id=second_finding.id,
                event_metadata={
                    "finding_type": second_finding.finding_type,
                    "risk_area": second_finding.risk_area,
                    "source_field": second_finding.source_field,
                    "priority_before": "attention",
                    "priority_after": "attention",
                },
            )
        elif scenario == "malformed_metadata":
            kwargs.update(
                event_type="assignment_changed",
                actor_kind="admin",
                actor_user_id=admin.id,
                admin_action_id=action.id,
                event_metadata={
                    "previous_assignee_id": None,
                    "next_assignee_id": [],
                },
            )
        elif scenario == "wrong_related_event":
            kwargs.update(
                event_type="reopened",
                actor_kind="admin",
                actor_user_id=admin.id,
                admin_action_id=action.id,
                related_event_id=unrelated_event_id,
                event_metadata={
                    "prior_resolution_mode": "manual",
                    "prior_resolution_outcome": "no_action_needed",
                },
            )
        elif scenario == "self_link":
            kwargs.update(
                event_type="merged_into",
                actor_kind="admin",
                actor_user_id=admin.id,
                admin_action_id=action.id,
                related_case_id=first_case.id,
                related_event_id=unrelated_event_id,
                event_metadata={
                    "source_resolution_mode": "manual",
                    "source_resolution_outcome": "no_action_needed",
                },
            )
        else:
            kwargs.update(
                event_type="case_created",
                actor_kind="automation",
                automation_rule_id=SOURCE_RECONCILIATION_RULE_ID,
                automation_rule_version=SOURCE_RECONCILIATION_RULE_VERSION,
                event_metadata={"source": "content_moderation_scanner"},
            )

        db.add(AdminReviewCaseEvent(**kwargs))
        with pytest.raises(DBAPIError, match=expected_message):
            db.flush()


def finalized_nonclosure_event(
    db,
    event_type: str,
) -> AdminReviewCaseEvent:
    game = seed_game(db)
    admin = seed_admin(db)

    if event_type in {"case_created", "finding_attached", "finding_cleared"}:
        review_case = create_content_case(db, game)
        if event_type == "finding_cleared":
            game.description = "Ordinary game details without contact information."
            db.commit()
            surface_community_game_text(db, game_id=game.id)
        return latest_case_event(db, review_case.id, event_type)

    if event_type in {
        "signal_attached",
        "signal_superseded",
        "signal_reactivated",
    }:
        review_case = create_chat_case(db, game)
        signal = db.scalar(
            select(AdminReviewSignal).where(
                AdminReviewSignal.review_case_id == review_case.id
            )
        )
        assert signal is not None
        if event_type in {"signal_superseded", "signal_reactivated"}:
            assert apply_review_signal_current_state(
                db,
                signal_id=signal.id,
                metadata={**(signal.metadata_ or {}), "current_match": False},
                changed_at=datetime.now(timezone.utc),
            )
            db.commit()
        if event_type == "signal_reactivated":
            signal = db.get(AdminReviewSignal, signal.id)
            assert apply_review_signal_current_state(
                db,
                signal_id=signal.id,
                metadata={**(signal.metadata_ or {}), "current_match": True},
                changed_at=datetime.now(timezone.utc),
            )
            db.commit()
        return latest_case_event(db, review_case.id, event_type)

    review_case = create_content_case(db, game)
    if event_type == "note_added":
        add_review_case_note(
            db,
            review_case_id=review_case.id,
            admin_user=admin,
            payload=AdminReviewCaseNoteCreate(
                body="Establish the resulting note state.",
                expected_case_version=review_case.case_version,
                idempotency_key="ws03-05b-semantic-note",
            ),
        )
    elif event_type == "assignment_changed":
        assign_review_case(
            db,
            review_case_id=review_case.id,
            admin_user=admin,
            payload=AdminReviewCaseAssignment(
                assignee_user_id=admin.id,
                reason="Establish the resulting assignment state.",
                expected_case_version=review_case.case_version,
                idempotency_key="ws03-05b-semantic-assignment",
            ),
        )
    elif event_type == "enforcement_action_linked":
        action = record_admin_action(
            db,
            admin_user_id=admin.id,
            action_type="hide_community_game",
            target_game_id=game.id,
            target_user_id=game.host_user_id,
            reason="Establish the resulting enforcement-link state.",
            metadata={"source": "ws03-05b-nonclosure-semantics"},
            idempotency_key="ws03-05b-semantic-enforcement",
        )
        assert (
            link_admin_action_to_open_review_case(
                db,
                action,
                case_category="content_moderation",
            ).id
            == review_case.id
        )
        db.commit()
    elif event_type == "reopened":
        closed = close_review_case(
            db,
            review_case_id=review_case.id,
            admin_user=admin,
            payload=AdminReviewCaseClose(
                outcome="no_action_needed",
                reason="Establish prior closure for semantic replay.",
                expected_case_version=review_case.case_version,
                idempotency_key="ws03-05b-semantic-close",
            ),
        )
        reopen_review_case(
            db,
            review_case_id=review_case.id,
            admin_user=admin,
            payload=AdminReviewCaseReopen(
                reason="Establish the resulting reopened state.",
                expected_case_version=closed.resulting_case_version,
                idempotency_key="ws03-05b-semantic-reopen",
            ),
        )
    else:
        closed = close_review_case(
            db,
            review_case_id=review_case.id,
            admin_user=admin,
            payload=AdminReviewCaseClose(
                outcome="no_action_needed",
                reason="Establish a closed historical merge source.",
                expected_case_version=review_case.case_version,
                idempotency_key="ws03-05b-semantic-merge-close",
            ),
        )
        game.description = "Call 214-555-0100 for the updated game."
        db.commit()
        destination = create_content_case(db, game)
        merge_review_case(
            db,
            source_case_id=review_case.id,
            admin_user=admin,
            payload=AdminReviewCaseMerge(
                destination_case_id=destination.id,
                reason="Establish the resulting reciprocal merge state.",
                expected_source_version=closed.resulting_case_version,
                expected_destination_version=destination.case_version,
                idempotency_key="ws03-05b-semantic-merge",
            ),
        )
        review_case = review_case if event_type == "merged_into" else destination

    return latest_case_event(db, review_case.id, event_type)


@pytest.mark.requirement("WS03-05B-R2", "WS03-05B-R3", "WS03-05B-R7")
@pytest.mark.parametrize("event_type", NON_CLOSURE_EVENT_TYPES)
def test_nonclosure_events_must_match_the_actual_resulting_projection(
    event_type: str,
) -> None:
    with session() as db:
        event = finalized_nonclosure_event(db, event_type)
        event_kwargs = {
            "review_case_id": event.review_case_id,
            "event_type": event.event_type,
            "actor_user_id": event.actor_user_id,
            "admin_action_id": event.admin_action_id,
            "signal_id": event.signal_id,
            "content_moderation_finding_id": (event.content_moderation_finding_id),
            "note_id": event.note_id,
            "related_case_id": event.related_case_id,
            "related_event_id": event.related_event_id,
            "actor_kind": event.actor_kind,
            "automation_rule_id": event.automation_rule_id,
            "automation_rule_version": event.automation_rule_version,
            "trigger_actor_user_id": event.trigger_actor_user_id,
            "event_metadata": dict(event.event_metadata or {}),
        }

        with pytest.raises(ValueError):
            create_case_event(db, **event_kwargs)

        review_case = db.get(AdminReviewCase, event.review_case_id)
        event_count = db.scalar(
            select(func.count(AdminReviewCaseEvent.id)).where(
                AdminReviewCaseEvent.review_case_id == event.review_case_id
            )
        )
        review_case.case_version += 1
        db.flush()
        db.add(
            AdminReviewCaseEvent(
                id=uuid.uuid4(),
                event_sequence=review_case.case_version,
                case_version=review_case.case_version,
                created_at=datetime.now(timezone.utc),
                **event_kwargs,
            )
        )
        with pytest.raises(DBAPIError):
            db.flush()
        db.rollback()
        assert (
            db.scalar(
                select(func.count(AdminReviewCaseEvent.id)).where(
                    AdminReviewCaseEvent.review_case_id == event.review_case_id
                )
            )
            == event_count
        )


@pytest.mark.requirement("WS03-05B-R1", "WS03-05B-R2", "WS03-05B-R7")
@pytest.mark.parametrize(
    ("field_name", "invalid_value", "expected_constraint"),
    (
        ("case_type", "unsupported", "ck_admin_review_cases_case_type"),
        ("case_status", "pending", "ck_admin_review_cases_case_status"),
        ("case_category", "other", "ck_admin_review_cases_case_category"),
        ("priority", "low", "ck_admin_review_cases_priority"),
        (
            "closure_outcome",
            "unsupported",
            "ck_admin_review_cases_closure_outcome",
        ),
        ("closure_mode", "queued", "ck_admin_review_cases_closure_mode"),
        (
            "creation_reason",
            "   ",
            "ck_admin_review_cases_creation_reason_nonblank",
        ),
    ),
)
def test_postgresql_rejects_invalid_case_finite_values_and_blank_creation_reason(
    field_name: str,
    invalid_value: str,
    expected_constraint: str,
) -> None:
    with session() as db:
        game = seed_game(db)
        review_case = direct_case(
            case_type="community_game",
            category="content_moderation",
            target_field="target_game_id",
            target_id=game.id,
        )
        if field_name in {"closure_outcome", "closure_mode"}:
            review_case.case_status = "closed"
            review_case.closure_outcome = "no_action_needed"
            review_case.closure_reason = "Valid closure before finite mutation."
            review_case.closure_mode = "manual"
            review_case.closed_by_user_id = game.host_user_id
            review_case.closed_at = datetime.now(timezone.utc)
        setattr(review_case, field_name, invalid_value)
        db.add(review_case)
        with pytest.raises(IntegrityError) as invalid:
            db.flush()
        assert constraint_name(invalid.value) == expected_constraint


@pytest.mark.requirement("WS03-05B-R3", "WS03-05B-R7")
@pytest.mark.parametrize(
    ("kwargs", "message"),
    (
        ({"event_type": "unsupported"}, "event_type is not supported"),
        (
            {"event_type": "closed", "actor_kind": "worker"},
            "actor_kind is not supported",
        ),
        (
            {"event_type": "closed", "actor_kind": "automation"},
            "require automation_rule_id",
        ),
        (
            {
                "event_type": "closed",
                "actor_kind": "automation",
                "automation_rule_id": "rule",
            },
            "require automation_rule_version",
        ),
    ),
)
def test_event_builder_rejects_invalid_finite_and_provenance_shapes(
    kwargs: dict[str, object],
    message: str,
) -> None:
    with session() as db:
        game = seed_game(db)
        review_case = create_content_case(db, game)
        with pytest.raises(ValueError, match=message):
            create_case_event(db, review_case_id=review_case.id, **kwargs)


@pytest.mark.requirement("WS03-05B-R3", "WS03-05B-R7")
@pytest.mark.parametrize(
    ("kwargs", "message"),
    (
        (
            {
                "event_type": "case_created",
                "actor_kind": "automation",
                "actor_user_id": uuid.UUID("11111111-1111-4111-8111-111111111111"),
                "automation_rule_id": SOURCE_RECONCILIATION_RULE_ID,
                "automation_rule_version": SOURCE_RECONCILIATION_RULE_VERSION,
                "event_metadata": {"source": "content_moderation_scanner"},
            },
            "do not accept actor_user_id",
        ),
        (
            {
                "event_type": "closed",
                "actor_kind": "admin",
                "actor_user_id": uuid.UUID("22222222-2222-4222-8222-222222222222"),
                "automation_rule_id": "contradictory.rule",
                "automation_rule_version": "1",
            },
            "do not accept automation rule identity",
        ),
        (
            {
                "event_type": "closed",
                "actor_kind": "admin",
                "actor_user_id": uuid.UUID("33333333-3333-4333-8333-333333333333"),
                "admin_action_id": uuid.UUID("44444444-4444-4444-8444-444444444444"),
                "trigger_actor_user_id": uuid.UUID(
                    "55555555-5555-4555-8555-555555555555"
                ),
                "event_metadata": {
                    "closure_mode": "manual",
                    "reason": "Contradictory actor fixture.",
                    "target_type": "community_game",
                    "target_id": TEST_TARGET_ID,
                    "closed_by_user_id": TEST_ADMIN_ID,
                    "previous_assignee_id": None,
                    "before": {"case_status": "open", "closure_outcome": None},
                    "after": {
                        "case_status": "closed",
                        "closure_outcome": "no_action_needed",
                    },
                },
            },
            "do not accept a triggering user",
        ),
    ),
)
def test_event_builder_rejects_contradictory_actor_and_rule_inputs(
    kwargs: dict[str, object],
    message: str,
) -> None:
    with session() as db:
        game = seed_game(db)
        review_case = create_content_case(db, game)
        with pytest.raises(ValueError, match=message):
            create_case_event(db, review_case_id=review_case.id, **kwargs)


@pytest.mark.requirement("WS03-05B-R3", "WS03-05B-R7")
def test_event_builder_binds_automatic_closure_to_case_resolution_and_rule() -> None:
    with session() as db:
        game = seed_game(db)
        admin = seed_admin(db)
        review_case = create_content_case(db, game)
        game.deleted_at = datetime.now(timezone.utc)
        db.add(game)
        review_case.case_status = "closed"
        review_case.closure_outcome = "no_action_needed"
        review_case.closure_reason = "Automatic lifecycle closure fixture."
        review_case.closure_mode = "automatic"
        review_case.closure_rule_id = TARGET_LIFECYCLE_RULE_ID
        review_case.closure_rule_version = TARGET_LIFECYCLE_RULE_VERSION
        review_case.closed_by_user_id = admin.id
        review_case.closed_at = datetime.now(timezone.utc)
        db.add(review_case)
        db.flush()

        metadata = {
            "closure_mode": "automatic",
            "reason": review_case.closure_reason,
            "closure_source": "target_lifecycle",
            "lifecycle_action": "admin_soft_deleted",
            "target_type": "community_game",
            "target_id": str(game.id),
            "previous_target_state": "active",
            "new_target_state": "soft_deleted",
            "trigger_actor_type": "admin",
            "trigger_actor_user_id": str(admin.id),
            "closed_by_user_id": str(admin.id),
            "previous_assignee_id": None,
            "linked_admin_action_id": None,
            "before": {"case_status": "open", "closure_outcome": None},
            "after": {
                "case_status": "closed",
                "closure_outcome": "invalid_signal",
            },
        }
        with pytest.raises(ValueError, match="case resolution"):
            create_case_event(
                db,
                review_case_id=review_case.id,
                event_type="closed",
                actor_kind="automation",
                automation_rule_id=TARGET_LIFECYCLE_RULE_ID,
                automation_rule_version=TARGET_LIFECYCLE_RULE_VERSION,
                trigger_actor_user_id=admin.id,
                created_at=review_case.closed_at,
                event_metadata=metadata,
            )

        metadata["after"] = {
            "case_status": "closed",
            "closure_outcome": "no_action_needed",
        }
        with pytest.raises(ValueError, match="attribution"):
            create_case_event(
                db,
                review_case_id=review_case.id,
                event_type="closed",
                actor_kind="automation",
                automation_rule_id="wrong.rule",
                automation_rule_version=TARGET_LIFECYCLE_RULE_VERSION,
                trigger_actor_user_id=admin.id,
                created_at=review_case.closed_at,
                event_metadata=metadata,
            )


@pytest.mark.requirement("WS03-05B-R3", "WS03-05B-R7")
def test_postgresql_binds_automatic_closure_to_case_resolution_and_rule() -> None:
    with session() as db:
        game = seed_game(db)
        admin = seed_admin(db)
        review_case = create_content_case(db, game)
        game.deleted_at = datetime.now(timezone.utc)
        db.add(game)
        review_case.case_status = "closed"
        review_case.closure_outcome = "no_action_needed"
        review_case.closure_reason = "Direct database closure fixture."
        review_case.closure_mode = "automatic"
        review_case.closure_rule_id = TARGET_LIFECYCLE_RULE_ID
        review_case.closure_rule_version = TARGET_LIFECYCLE_RULE_VERSION
        review_case.closed_by_user_id = admin.id
        review_case.closed_at = datetime.now(timezone.utc)
        review_case.case_version += 1
        db.add(review_case)
        db.flush()

        db.add(
            AdminReviewCaseEvent(
                id=uuid.uuid4(),
                review_case_id=review_case.id,
                event_type="closed",
                event_sequence=review_case.case_version,
                case_version=review_case.case_version,
                actor_kind="automation",
                automation_rule_id="wrong.rule",
                automation_rule_version=TARGET_LIFECYCLE_RULE_VERSION,
                trigger_actor_user_id=admin.id,
                created_at=review_case.closed_at,
                event_metadata={
                    "closure_mode": "automatic",
                    "reason": review_case.closure_reason,
                    "closure_source": "target_lifecycle",
                    "lifecycle_action": "admin_soft_deleted",
                    "target_type": "community_game",
                    "target_id": str(game.id),
                    "previous_target_state": "active",
                    "new_target_state": "soft_deleted",
                    "trigger_actor_type": "admin",
                    "trigger_actor_user_id": str(admin.id),
                    "closed_by_user_id": str(admin.id),
                    "previous_assignee_id": None,
                    "linked_admin_action_id": None,
                    "before": {"case_status": "open", "closure_outcome": None},
                    "after": {
                        "case_status": "closed",
                        "closure_outcome": "no_action_needed",
                    },
                },
            )
        )
        with pytest.raises(DBAPIError, match="attribution"):
            db.flush()


@pytest.mark.requirement("WS03-05B-R2", "WS03-05B-R3", "WS03-05B-R7")
@pytest.mark.parametrize(
    "invalid_dimension",
    ("lifecycle", "before", "after", "actor", "outcome", "category", "target"),
)
def test_postgresql_rejects_invalid_automatic_lifecycle_matrix_dimensions(
    invalid_dimension: str,
) -> None:
    with session() as db:
        game = seed_game(db)
        admin = seed_admin(db)
        review_case = (
            create_chat_case(db, game)
            if invalid_dimension == "category"
            else create_content_case(db, game)
        )
        if invalid_dimension != "target":
            game.deleted_at = datetime.now(timezone.utc)
            db.add(game)

        review_case.case_status = "closed"
        review_case.closure_outcome = "no_action_needed"
        review_case.closure_reason = "Automatic lifecycle matrix fixture."
        review_case.closure_mode = "automatic"
        review_case.closure_rule_id = TARGET_LIFECYCLE_RULE_ID
        review_case.closure_rule_version = TARGET_LIFECYCLE_RULE_VERSION
        review_case.closed_by_user_id = admin.id
        review_case.closed_at = datetime.now(timezone.utc)
        review_case.case_version += 1
        metadata = {
            "closure_mode": "automatic",
            "reason": review_case.closure_reason,
            "closure_source": "target_lifecycle",
            "lifecycle_action": "admin_soft_deleted",
            "target_type": "community_game",
            "target_id": str(game.id),
            "previous_target_state": "active",
            "new_target_state": "soft_deleted",
            "trigger_actor_type": "admin",
            "trigger_actor_user_id": str(admin.id),
            "closed_by_user_id": str(admin.id),
            "previous_assignee_id": None,
            "linked_admin_action_id": None,
            "before": {"case_status": "open", "closure_outcome": None},
            "after": {
                "case_status": "closed",
                "closure_outcome": "no_action_needed",
            },
        }
        trigger_actor_user_id = admin.id
        if invalid_dimension == "lifecycle":
            metadata["lifecycle_action"] = "host_cancelled"
        elif invalid_dimension == "before":
            metadata["previous_target_state"] = "completed"
        elif invalid_dimension == "after":
            metadata["new_target_state"] = "cancelled"
        elif invalid_dimension == "actor":
            metadata["trigger_actor_type"] = "system"
            metadata["trigger_actor_user_id"] = None
            metadata["closed_by_user_id"] = None
            trigger_actor_user_id = None
            review_case.closed_by_user_id = None
        elif invalid_dimension == "outcome":
            review_case.closure_outcome = "invalid_signal"
            metadata["after"]["closure_outcome"] = "invalid_signal"

        db.add(review_case)
        db.flush()
        db.add(
            AdminReviewCaseEvent(
                id=uuid.uuid4(),
                review_case_id=review_case.id,
                event_type="closed",
                event_sequence=review_case.case_version,
                case_version=review_case.case_version,
                actor_kind="automation",
                automation_rule_id=TARGET_LIFECYCLE_RULE_ID,
                automation_rule_version=TARGET_LIFECYCLE_RULE_VERSION,
                trigger_actor_user_id=trigger_actor_user_id,
                event_metadata=metadata,
                created_at=review_case.closed_at,
            )
        )
        expected_message = (
            "target state" if invalid_dimension == "target" else "lifecycle transition"
        )
        with pytest.raises(DBAPIError, match=expected_message):
            db.flush()


@pytest.mark.requirement("WS03-05B-R3", "WS03-05B-R7")
@pytest.mark.parametrize(
    ("event_type", "actor_kind", "expected_constraint"),
    (
        (
            "unsupported",
            "automation",
            "ck_admin_review_case_events_event_type",
        ),
        ("closed", "worker", "ck_admin_review_case_events_actor_kind"),
    ),
)
def test_postgresql_rejects_invalid_event_finite_values(
    event_type: str,
    actor_kind: str,
    expected_constraint: str,
) -> None:
    with session() as db:
        game = seed_game(db)
        review_case = create_content_case(db, game)
        db.add(
            AdminReviewCaseEvent(
                id=uuid.uuid4(),
                review_case_id=review_case.id,
                event_type=event_type,
                event_sequence=review_case.case_version + 1,
                case_version=review_case.case_version + 1,
                actor_kind=actor_kind,
                automation_rule_id="finite.contract.test",
                automation_rule_version="1",
            )
        )
        with pytest.raises(IntegrityError) as invalid:
            db.flush()
        assert constraint_name(invalid.value) == expected_constraint


@pytest.mark.requirement("WS03-05B-R2", "WS03-05B-R3", "WS03-05B-R7")
def test_event_notes_and_resolution_references_enforce_immutable_shapes() -> None:
    with session() as db:
        game = seed_game(db)
        admin = seed_admin(db)
        review_case = create_content_case(db, game)
        note_result = add_review_case_note(
            db,
            review_case_id=review_case.id,
            admin_user=admin,
            payload=AdminReviewCaseNoteCreate(
                body="Immutable review note.",
                expected_case_version=2,
                idempotency_key="ws03-05b-immutable-note",
            ),
        )
        close_review_case(
            db,
            review_case_id=review_case.id,
            admin_user=admin,
            payload=AdminReviewCaseClose(
                outcome="no_action_needed",
                reason="Create immutable closure references.",
                expected_case_version=3,
                idempotency_key="ws03-05b-immutable-close",
            ),
        )
        events = list(
            db.scalars(
                select(AdminReviewCaseEvent)
                .where(AdminReviewCaseEvent.review_case_id == review_case.id)
                .order_by(AdminReviewCaseEvent.event_sequence.asc())
            ).all()
        )
        reference = db.scalar(select(AdminReviewCaseResolutionReference))
        assert reference is not None

        duplicate_reference = AdminReviewCaseResolutionReference(
            id=uuid.uuid4(),
            closure_event_id=reference.closure_event_id,
            reference_type=reference.reference_type,
            content_moderation_finding_id=reference.content_moderation_finding_id,
            was_current=reference.was_current,
        )
        db.add(duplicate_reference)
        with pytest.raises(DBAPIError, match="reference set is sealed"):
            db.flush()
        db.rollback()

        reference = db.scalar(select(AdminReviewCaseResolutionReference))
        closure_event = db.get(AdminReviewCaseEvent, reference.closure_event_id)
        invalid_reference = AdminReviewCaseResolutionReference(
            id=uuid.uuid4(),
            closure_event_id=reference.closure_event_id,
            reference_type="finding",
            content_moderation_finding_id=reference.content_moderation_finding_id,
            admin_action_id=closure_event.admin_action_id,
            was_current=True,
        )
        db.add(invalid_reference)
        with pytest.raises(DBAPIError, match="reference set is sealed"):
            db.flush()
        db.rollback()

        events = list(
            db.scalars(
                select(AdminReviewCaseEvent)
                .where(AdminReviewCaseEvent.review_case_id == review_case.id)
                .order_by(AdminReviewCaseEvent.event_sequence.asc())
            ).all()
        )
        first_event = events[0]
        db.add(
            AdminReviewCaseEvent(
                id=uuid.uuid4(),
                review_case_id=first_event.review_case_id,
                event_type=first_event.event_type,
                event_sequence=first_event.event_sequence,
                case_version=first_event.case_version,
                actor_kind=first_event.actor_kind,
                actor_user_id=first_event.actor_user_id,
                admin_action_id=first_event.admin_action_id,
                signal_id=first_event.signal_id,
                content_moderation_finding_id=(
                    first_event.content_moderation_finding_id
                ),
                note_id=first_event.note_id,
                automation_rule_id=first_event.automation_rule_id,
                automation_rule_version=first_event.automation_rule_version,
                event_metadata=first_event.event_metadata,
            )
        )
        with pytest.raises(IntegrityError) as duplicate_sequence:
            db.flush()
        assert constraint_name(duplicate_sequence.value) == (
            "uq_admin_review_case_events_case_sequence"
        )
        db.rollback()

        with pytest.raises(IntegrityError):
            db.execute(
                delete(AdminReviewCase).where(AdminReviewCase.id == review_case.id)
            )
            db.commit()
        db.rollback()

        with pytest.raises(DBAPIError, match="events are immutable"):
            db.execute(
                update(AdminReviewCaseEvent)
                .where(AdminReviewCaseEvent.id == events[0].id)
                .values(event_metadata={"changed": True})
            )
            db.commit()
        db.rollback()
        with pytest.raises(DBAPIError, match="events are immutable"):
            db.execute(
                delete(AdminReviewCaseEvent).where(
                    AdminReviewCaseEvent.id == events[0].id
                )
            )
            db.commit()
        db.rollback()
        with pytest.raises(DBAPIError, match="references are immutable"):
            db.execute(
                update(AdminReviewCaseResolutionReference)
                .where(AdminReviewCaseResolutionReference.id == reference.id)
                .values(was_current=False)
            )
            db.commit()
        db.rollback()
        with pytest.raises(DBAPIError, match="references are immutable"):
            db.execute(
                delete(AdminReviewCaseResolutionReference).where(
                    AdminReviewCaseResolutionReference.id == reference.id
                )
            )
            db.commit()
        db.rollback()

        with pytest.raises(DBAPIError, match="require a closure event"):
            db.add(
                AdminReviewCaseResolutionReference(
                    id=uuid.uuid4(),
                    closure_event_id=events[0].id,
                    reference_type="source_case",
                    source_case_id=uuid.uuid4(),
                )
            )
            db.flush()
        db.rollback()

        with pytest.raises(IntegrityError) as self_correction:
            db.execute(
                update(AdminReviewCaseNote)
                .where(AdminReviewCaseNote.id == note_result.note.id)
                .values(corrects_note_id=note_result.note.id)
            )
            db.commit()
        assert constraint_name(self_correction.value) == (
            "ck_admin_review_case_notes_no_self_correction"
        )


@pytest.mark.requirement("WS03-05B-R2", "WS03-05B-R3", "WS03-05B-R7")
def test_resolution_reference_shape_is_enforced_during_closure_transaction() -> None:
    with session() as db:
        game = seed_game(db)
        admin = seed_admin(db)
        review_case = create_content_case(db, game)

        with patch.object(db, "commit", side_effect=db.flush):
            close_review_case(
                db,
                review_case_id=review_case.id,
                admin_user=admin,
                payload=AdminReviewCaseClose(
                    outcome="no_action_needed",
                    reason="Hold the closure transaction open for shape validation.",
                    expected_case_version=review_case.case_version,
                    idempotency_key="ws03-05b-reference-shape-transaction",
                ),
            )

        reference = db.scalar(select(AdminReviewCaseResolutionReference))
        assert reference is not None
        closure_event = db.get(AdminReviewCaseEvent, reference.closure_event_id)
        assert closure_event is not None
        db.add(
            AdminReviewCaseResolutionReference(
                id=uuid.uuid4(),
                closure_event_id=closure_event.id,
                reference_type="finding",
                content_moderation_finding_id=(reference.content_moderation_finding_id),
                admin_action_id=closure_event.admin_action_id,
                was_current=True,
            )
        )
        with pytest.raises(IntegrityError) as invalid_shape:
            db.flush()
        assert constraint_name(invalid_shape.value) == (
            "ck_admin_review_case_resolution_refs_shape"
        )


@pytest.mark.requirement("WS03-05B-R2", "WS03-05B-R3", "WS03-05B-R7")
@pytest.mark.parametrize(
    "scenario",
    (
        "finding_after_reopen",
        "signal_after_source_change",
        "action_after_later_link",
        "source_case_after_merge",
    ),
)
def test_closure_resolution_reference_sets_are_sealed_after_creation(
    scenario: str,
) -> None:
    with session() as db:
        game = seed_game(db)
        admin = seed_admin(db)

        if scenario == "signal_after_source_change":
            review_case = create_chat_case(db, game)
            signal = db.scalar(
                select(AdminReviewSignal).where(
                    AdminReviewSignal.review_case_id == review_case.id
                )
            )
            closed = close_review_case(
                db,
                review_case_id=review_case.id,
                admin_user=admin,
                payload=AdminReviewCaseClose(
                    outcome="no_action_needed",
                    reason="Seal the original signal reference set.",
                    expected_case_version=review_case.case_version,
                    idempotency_key=f"ws03-05b-seal-close-{scenario}",
                ),
            )
            closure_event = latest_case_event(db, review_case.id, "closed")
            reopen_review_case(
                db,
                review_case_id=review_case.id,
                admin_user=admin,
                payload=AdminReviewCaseReopen(
                    reason="Change the signal after its historical closure.",
                    expected_case_version=closed.resulting_case_version,
                    idempotency_key=f"ws03-05b-seal-reopen-{scenario}",
                ),
            )
            signal = db.get(AdminReviewSignal, signal.id)
            assert apply_review_signal_current_state(
                db,
                signal_id=signal.id,
                metadata={**(signal.metadata_ or {}), "current_match": False},
                changed_at=datetime.now(timezone.utc),
            )
            db.commit()
            delayed_reference = AdminReviewCaseResolutionReference(
                id=uuid.uuid4(),
                closure_event_id=closure_event.id,
                reference_type="signal",
                signal_id=signal.id,
                was_current=False,
            )
        else:
            review_case = create_content_case(db, game)
            closed = close_review_case(
                db,
                review_case_id=review_case.id,
                admin_user=admin,
                payload=AdminReviewCaseClose(
                    outcome="no_action_needed",
                    reason="Seal the original content reference set.",
                    expected_case_version=review_case.case_version,
                    idempotency_key=f"ws03-05b-seal-close-{scenario}",
                ),
            )

            if scenario == "source_case_after_merge":
                game.description = "Call 214-555-0100 for changed details."
                db.commit()
                destination = create_content_case(db, game)
                merge_review_case(
                    db,
                    source_case_id=review_case.id,
                    admin_user=admin,
                    payload=AdminReviewCaseMerge(
                        destination_case_id=destination.id,
                        reason="Create immutable merged-source attribution.",
                        expected_source_version=closed.resulting_case_version,
                        expected_destination_version=destination.case_version,
                        idempotency_key="ws03-05b-seal-merge-source",
                    ),
                )
                close_review_case(
                    db,
                    review_case_id=destination.id,
                    admin_user=admin,
                    payload=AdminReviewCaseClose(
                        outcome="no_action_needed",
                        reason="Seal the merged destination reference set.",
                        expected_case_version=destination.case_version,
                        idempotency_key="ws03-05b-seal-close-destination",
                    ),
                )
                closure_event = latest_case_event(db, destination.id, "closed")
                delayed_reference = AdminReviewCaseResolutionReference(
                    id=uuid.uuid4(),
                    closure_event_id=closure_event.id,
                    reference_type="source_case",
                    source_case_id=review_case.id,
                )
            else:
                closure_event = latest_case_event(db, review_case.id, "closed")
                reopened = reopen_review_case(
                    db,
                    review_case_id=review_case.id,
                    admin_user=admin,
                    payload=AdminReviewCaseReopen(
                        reason="Exercise the sealed historical reference set.",
                        expected_case_version=closed.resulting_case_version,
                        idempotency_key=f"ws03-05b-seal-reopen-{scenario}",
                    ),
                )
                if scenario == "finding_after_reopen":
                    finding = db.scalar(
                        select(AdminContentModerationFinding).where(
                            AdminContentModerationFinding.review_case_id
                            == review_case.id,
                            AdminContentModerationFinding.current_match.is_(True),
                        )
                    )
                    delayed_reference = AdminReviewCaseResolutionReference(
                        id=uuid.uuid4(),
                        closure_event_id=closure_event.id,
                        reference_type="finding",
                        content_moderation_finding_id=finding.id,
                        was_current=True,
                    )
                else:
                    action = record_admin_action(
                        db,
                        admin_user_id=admin.id,
                        action_type="hide_community_game",
                        target_game_id=game.id,
                        target_user_id=game.host_user_id,
                        reason="Link enforcement after the historical closure.",
                        metadata={"source": "ws03-05b-reference-seal"},
                        idempotency_key="ws03-05b-seal-later-enforcement",
                    )
                    assert (
                        link_admin_action_to_open_review_case(
                            db,
                            action,
                            case_category="content_moderation",
                        ).id
                        == reopened.review_case.id
                    )
                    db.commit()
                    delayed_reference = AdminReviewCaseResolutionReference(
                        id=uuid.uuid4(),
                        closure_event_id=closure_event.id,
                        reference_type="enforcement_action",
                        admin_action_id=action.id,
                    )

        reference_count = db.scalar(
            select(func.count(AdminReviewCaseResolutionReference.id)).where(
                AdminReviewCaseResolutionReference.closure_event_id == closure_event.id
            )
        )
        db.add(delayed_reference)
        with pytest.raises(DBAPIError, match="reference set is sealed"):
            db.flush()
        db.rollback()
        assert (
            db.scalar(
                select(func.count(AdminReviewCaseResolutionReference.id)).where(
                    AdminReviewCaseResolutionReference.closure_event_id
                    == closure_event.id
                )
            )
            == reference_count
        )


@pytest.mark.requirement("WS03-05B-R2", "WS03-05B-R3", "WS03-05B-R7")
def test_postgresql_resolution_references_enforce_aggregate_ownership_and_state() -> (
    None
):
    with session() as db:
        owner_game = seed_game(db)
        other_game = seed_game(db)
        admin = seed_admin(db)
        owner_case = create_content_case(db, owner_game)
        other_case = create_content_case(db, other_game)
        owner_finding = db.scalar(
            select(AdminContentModerationFinding).where(
                AdminContentModerationFinding.review_case_id == owner_case.id
            )
        )
        other_finding = db.scalar(
            select(AdminContentModerationFinding).where(
                AdminContentModerationFinding.review_case_id == other_case.id
            )
        )
        _chat_case, other_signal, _created, _replayed = create_internal_review_signal(
            db,
            signal_category="chat_moderation",
            source="chat_moderation",
            priority="urgent",
            title="Unrelated signal",
            summary="Unrelated aggregate signal.",
            target_data={"target_game_id": other_game.id},
            metadata={"current_match": True},
            idempotency_key="ws03-05b-unrelated-resolution-signal",
        )
        owner_chat_case, owner_signal, _created, _replayed = (
            create_internal_review_signal(
                db,
                signal_category="chat_moderation",
                source="chat_moderation",
                priority="urgent",
                title="Owning signal",
                summary="Owning aggregate signal.",
                target_data={"target_game_id": owner_game.id},
                metadata={"current_match": True},
                idempotency_key="ws03-05b-owning-resolution-signal",
            )
        )
        unrelated_action = record_admin_action(
            db,
            admin_user_id=admin.id,
            action_type="hide_community_game",
            target_game_id=other_game.id,
            target_user_id=other_game.host_user_id,
            reason="Unrelated enforcement action.",
            metadata={"source": "resolution-reference-contract"},
            idempotency_key="ws03-05b-unrelated-resolution-action",
        )
        assert (
            link_admin_action_to_open_review_case(
                db,
                unrelated_action,
                case_category="content_moderation",
            ).id
            == other_case.id
        )
        closed = close_review_case(
            db,
            review_case_id=owner_case.id,
            admin_user=admin,
            payload=AdminReviewCaseClose(
                outcome="no_action_needed",
                reason="Create owning closure event.",
                expected_case_version=2,
                idempotency_key="ws03-05b-resolution-owner-close",
            ),
        )
        closure_event = db.scalar(
            select(AdminReviewCaseEvent).where(
                AdminReviewCaseEvent.review_case_id == owner_case.id,
                AdminReviewCaseEvent.event_type == "closed",
            )
        )
        close_review_case(
            db,
            review_case_id=owner_chat_case.id,
            admin_user=admin,
            payload=AdminReviewCaseClose(
                outcome="no_action_needed",
                reason="Create signal closure event.",
                expected_case_version=2,
                idempotency_key="ws03-05b-resolution-signal-close",
            ),
        )
        signal_closure_event = db.scalar(
            select(AdminReviewCaseEvent).where(
                AdminReviewCaseEvent.review_case_id == owner_chat_case.id,
                AdminReviewCaseEvent.event_type == "closed",
            )
        )
        db.commit()

        invalid_references = (
            (
                AdminReviewCaseResolutionReference(
                    id=uuid.uuid4(),
                    closure_event_id=closure_event.id,
                    reference_type="finding",
                    content_moderation_finding_id=other_finding.id,
                    was_current=other_finding.current_match,
                ),
                "finding ownership",
            ),
            (
                AdminReviewCaseResolutionReference(
                    id=uuid.uuid4(),
                    closure_event_id=signal_closure_event.id,
                    reference_type="signal",
                    signal_id=owner_signal.id,
                    was_current=False,
                ),
                "signal ownership",
            ),
            (
                AdminReviewCaseResolutionReference(
                    id=uuid.uuid4(),
                    closure_event_id=closure_event.id,
                    reference_type="signal",
                    signal_id=other_signal.id,
                    was_current=True,
                ),
                "signal ownership",
            ),
            (
                AdminReviewCaseResolutionReference(
                    id=uuid.uuid4(),
                    closure_event_id=closure_event.id,
                    reference_type="enforcement_action",
                    admin_action_id=unrelated_action.id,
                ),
                "enforcement action ownership",
            ),
            (
                AdminReviewCaseResolutionReference(
                    id=uuid.uuid4(),
                    closure_event_id=closure_event.id,
                    reference_type="source_case",
                    source_case_id=other_case.id,
                ),
                "source case ownership",
            ),
            (
                AdminReviewCaseResolutionReference(
                    id=uuid.uuid4(),
                    closure_event_id=closure_event.id,
                    reference_type="finding",
                    content_moderation_finding_id=owner_finding.id,
                    was_current=False,
                ),
                "finding ownership",
            ),
            (
                AdminReviewCaseResolutionReference(
                    id=uuid.uuid4(),
                    closure_event_id=closure_event.id,
                    reference_type="enforcement_action",
                    admin_action_id=closed.audit_action_id,
                ),
                "enforcement action ownership",
            ),
        )
        for invalid_reference, message in invalid_references:
            db.add(invalid_reference)
            with pytest.raises(DBAPIError, match=message):
                db.flush()
            db.rollback()


@pytest.mark.requirement("WS03-05B-R3", "WS03-05B-R7")
def test_model_canonical_migrations_and_live_schema_remain_in_parity() -> None:
    from backend.database import engine
    from backend.services.admin_action_display_service import ACTION_DISPLAY_RULES
    from backend.services.admin_action_policy import ADMIN_ACTION_POLICIES

    inspector = inspect(engine)
    recorded = record_pass_owned_migrations()
    model_tables = {
        AdminAction.__table__.name: AdminAction.__table__,
        AdminReviewCase.__table__.name: AdminReviewCase.__table__,
        AdminReviewCaseEvent.__table__.name: AdminReviewCaseEvent.__table__,
        AdminReviewCaseNote.__table__.name: AdminReviewCaseNote.__table__,
        AdminReviewCaseResolutionReference.__table__.name: (
            AdminReviewCaseResolutionReference.__table__
        ),
    }
    for table_name, model_table in model_tables.items():
        migration_items = recorded.tables[table_name]

        model_columns = {
            column.name: column_signature(column) for column in model_table.columns
        }
        migration_columns = {
            column.name: column_signature(column)
            for column in migration_items
            if hasattr(column, "server_default")
        }
        assert migration_columns == model_columns

        live_columns = {
            item["name"]: item for item in inspector.get_columns(table_name)
        }
        assert set(live_columns) == set(model_columns)
        for column_name, model_column in model_columns.items():
            live_column = live_columns[column_name]
            assert (
                str(live_column["type"].compile(dialect=postgresql.dialect())).lower()
                == model_column[1]
            )
            assert bool(live_column["nullable"]) == model_column[2]
            model_default = model_column[4]
            live_default = normalize_schema_sql(live_column.get("default"))
            if model_default is None:
                assert live_default is None
            else:
                assert model_default in live_default

        model_checks = check_signatures(model_table.constraints)
        assert check_signatures(migration_items) == model_checks
        with engine.connect() as connection:
            expected_checks, expected_partial_predicates = (
                model_postgresql_semantic_definitions(
                    connection,
                    table_name,
                    model_table,
                )
            )
            live_checks = live_postgresql_check_definitions(connection, table_name)
            live_partial_predicates = live_postgresql_partial_index_predicates(
                connection, table_name
            )
        assert live_checks == expected_checks

        model_fks = foreign_key_signatures(model_table.constraints)
        assert foreign_key_signatures(migration_items) == model_fks
        live_fks = {
            (
                tuple(item["constrained_columns"]),
                tuple(
                    f"{item['referred_table']}.{column}"
                    for column in item["referred_columns"]
                ),
                item.get("options", {}).get("ondelete"),
            )
            for item in inspector.get_foreign_keys(table_name)
        }
        assert live_fks == model_fks

        model_uniques = unique_signatures(model_table.constraints)
        migration_uniques = unique_signatures(migration_items) | set(
            recorded.uniques.get(table_name, [])
        )
        assert migration_uniques == model_uniques
        live_uniques = {
            (item["name"], tuple(item["column_names"]))
            for item in inspector.get_unique_constraints(table_name)
            if item["name"] is not None
        }
        assert live_uniques == model_uniques

        model_indexes = {
            index_signature(
                item.name,
                item.expressions,
                item.unique,
                item.dialect_options["postgresql"].get("where"),
            )
            for item in model_table.indexes
        }
        migration_indexes = set(recorded.indexes.get(table_name, []))
        assert migration_indexes == model_indexes
        live_indexes = {
            item["name"]: item
            for item in inspector.get_indexes(table_name)
            if item.get("duplicates_constraint") is None
        }
        assert set(live_indexes) == {item[0] for item in model_indexes}
        for name, expressions, unique, where in model_indexes:
            live_index = live_indexes[name]
            assert bool(live_index["unique"]) is unique
            live_sorting = live_index.get("column_sorting", {})
            live_expressions = tuple(
                normalize_schema_sql(
                    f"{item} {' '.join(live_sorting.get(item, ()))}".strip()
                )
                for item in (
                    live_index.get("expressions")
                    or live_index.get("column_names")
                    or ()
                )
            )
            assert live_expressions == expressions
            if where is None:
                assert name not in live_partial_predicates
            else:
                assert (
                    live_partial_predicates[name] == expected_partial_predicates[name]
                )
        assert set(live_partial_predicates) == set(expected_partial_predicates)

    lifecycle_action_types = {
        "assign_review_case",
        "reopen_review_case",
        "merge_review_case",
    }
    assert set(ADMIN_ACTION_POLICIES) == set(ACTION_DISPLAY_RULES)
    assert lifecycle_action_types <= set(ADMIN_ACTION_POLICIES)
    action_type_constraint = next(
        constraint
        for constraint in AdminAction.__table__.constraints
        if constraint.name == "ck_admin_actions_action_type"
    )
    action_type_sql = str(action_type_constraint.sqltext)
    migration_text = "\n".join(recorded.sql)
    migration_text += "\n".join(
        normalize_schema_sql(value) or ""
        for value in check_signatures(recorded.tables["admin_actions"]).values()
    )
    for action_type in lifecycle_action_types:
        assert f"'{action_type}'" in action_type_sql
        assert f"'{action_type}'" in migration_text
        policy = ADMIN_ACTION_POLICIES[action_type]
        assert policy.requires_reason is True
        assert policy.metadata_builder_key == "review_workflow"

    expected_triggers = {
        (
            "trg_admin_review_cases_identity_immutable",
            "admin_review_cases",
            "reject_admin_review_case_identity_mutation",
            "BEFORE UPDATE",
        ),
        (
            "trg_admin_review_case_events_validate_insert",
            "admin_review_case_events",
            "validate_admin_review_case_event_insert",
            "BEFORE INSERT",
        ),
        (
            "trg_admin_review_case_events_immutable",
            "admin_review_case_events",
            "reject_admin_review_case_event_mutation",
            "BEFORE UPDATE OR DELETE",
        ),
        (
            "trg_admin_review_case_resolution_refs_validate_insert",
            "admin_review_case_resolution_references",
            "validate_admin_review_case_resolution_ref_insert",
            "BEFORE INSERT",
        ),
        (
            "trg_admin_review_case_resolution_refs_immutable",
            "admin_review_case_resolution_references",
            "reject_admin_review_case_resolution_ref_mutation",
            "BEFORE UPDATE OR DELETE",
        ),
    }
    for trigger_name, table_name, function_name, timing in expected_triggers:
        assert trigger_name in migration_text
        assert table_name in migration_text
        assert function_name in migration_text
        assert timing.lower() in migration_text.lower()

    expected_function_bodies = {
        match.group(1): normalize_schema_sql(match.group(2))
        for statement in recorded.sql
        for match in re.finditer(
            r"CREATE FUNCTION\s+([a-z0-9_]+)\(\).*?AS\s+\$\$(.*?)\$\$",
            statement,
            flags=re.IGNORECASE | re.DOTALL,
        )
    }
    with engine.connect() as connection:
        live_trigger_rows = connection.execute(
            text(
                "SELECT trigger.tgname, table_class.relname, function.proname, "
                "pg_get_triggerdef(trigger.oid) "
                "FROM pg_trigger AS trigger "
                "JOIN pg_class AS table_class ON table_class.oid = trigger.tgrelid "
                "JOIN pg_proc AS function ON function.oid = trigger.tgfoid "
                "WHERE NOT trigger.tgisinternal AND table_class.relname IN ("
                "'admin_review_cases', "
                "'admin_review_case_events', "
                "'admin_review_case_resolution_references')"
            )
        ).all()
        live_function_bodies = dict(
            connection.execute(
                text(
                    "SELECT proname, prosrc FROM pg_proc "
                    "WHERE proname = ANY(:function_names)"
                ),
                {"function_names": list(expected_function_bodies)},
            ).all()
        )

    assert {row[0] for row in live_trigger_rows} == {
        item[0] for item in expected_triggers
    }
    for trigger_name, table_name, function_name, timing in expected_triggers:
        row = next(item for item in live_trigger_rows if item[0] == trigger_name)
        assert row[1] == table_name
        assert row[2] == function_name
        for timing_token in set(timing.split()) - {"OR"}:
            assert timing_token in row[3]
    assert {
        name: normalize_schema_sql(body) for name, body in live_function_bodies.items()
    } == expected_function_bodies


@pytest.mark.requirement("WS03-05B-R7")
def test_database_cleanup_uses_its_own_bounded_statement_timeout() -> None:
    import backend.tests.conftest as backend_conftest

    calls: list[tuple[str, dict[str, str] | None]] = []

    class RecordingConnection:
        def execute(self, statement, parameters=None) -> None:
            calls.append((str(statement), parameters))

    backend_conftest._truncate_test_tables(RecordingConnection(), "users")

    assert calls == [
        (
            "SELECT set_config('statement_timeout', :timeout, true)",
            {
                "timeout": str(
                    backend_conftest.TEST_DATABASE_CLEANUP_STATEMENT_TIMEOUT_MILLISECONDS
                )
            },
        ),
        ("TRUNCATE TABLE users RESTART IDENTITY CASCADE", None),
    ]
    assert (
        backend_conftest.TEST_DATABASE_CLEANUP_STATEMENT_TIMEOUT_MILLISECONDS == 60_000
    )
