"""WS03-05C schema, migration, and live PostgreSQL contract tests."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from backend.models import AdminAction, AdminTargetNotice
from backend.tests.workflows.admin_route_list_high_risk_function_authorization.test_admin_game_roster_moderation_contract import (
    _persist_community_game_fixture,
    _persist_sub_post_fixture,
)
from backend.tests.workflows.admin_route_list_high_risk_function_authorization.test_admin_matrix_scope_and_dependencies_contract import (
    _add_users,
    _session,
    _user,
)

pytestmark = pytest.mark.suite_type("ordinary")

REPO_ROOT = Path(__file__).resolve().parents[4]
NOTICE_MIGRATION = (
    REPO_ROOT
    / "backend/alembic/versions/0028_create_admin_target_notices_table.py"
)
NOTICE_CONSTRAINTS = {
    "ck_admin_target_notices_notice_type",
    "ck_admin_target_notices_game_enforcement_target",
    "ck_admin_target_notices_sub_enforcement_target",
    "ck_admin_target_notices_sub_removal_target",
}
IDEMPOTENCY_INDEX_COLUMNS = {
    "uq_admin_actions_suspend_user_idempotency": (
        "admin_user_id",
        "target_user_id",
        "idempotency_key",
    ),
    "uq_admin_actions_unsuspend_user_idempotency": (
        "admin_user_id",
        "target_user_id",
        "idempotency_key",
    ),
    "uq_admin_actions_restrict_hosting_idempotency": (
        "admin_user_id",
        "target_user_id",
        "idempotency_key",
    ),
    "uq_admin_actions_restore_hosting_idempotency": (
        "admin_user_id",
        "target_user_id",
        "idempotency_key",
    ),
    "uq_admin_actions_community_game_enforcement_idempotency": (
        "admin_user_id",
        "target_game_id",
        "action_type",
        "idempotency_key",
    ),
    "uq_admin_actions_hide_unsafe_community_payment_text_idempotency": (
        "admin_user_id",
        "target_game_id",
        "idempotency_key",
    ),
    "uq_admin_actions_need_sub_enforcement_idempotency": (
        "admin_user_id",
        "target_sub_post_id",
        "action_type",
        "idempotency_key",
    ),
    "uq_admin_actions_remove_sub_post_idempotency": (
        "admin_user_id",
        "target_sub_post_id",
        "idempotency_key",
    ),
    "uq_admin_actions_remove_chat_message_idempotency": (
        "admin_user_id",
        "target_message_id",
        "idempotency_key",
    ),
    "uq_admin_actions_restore_chat_message_idempotency": (
        "admin_user_id",
        "target_message_id",
        "idempotency_key",
    ),
    "uq_admin_actions_remove_sub_chat_message_idempotency": (
        "admin_user_id",
        "target_sub_chat_message_id",
        "idempotency_key",
    ),
    "uq_admin_actions_restore_sub_chat_message_idempotency": (
        "admin_user_id",
        "target_sub_chat_message_id",
        "idempotency_key",
    ),
}


def test_notice_constraints_and_action_indexes_match_model_migration_and_live_schema(
) -> None:
    migration_source = NOTICE_MIGRATION.read_text()
    model_constraint_names = {
        constraint.name
        for constraint in AdminTargetNotice.__table__.constraints
        if constraint.name is not None
    }
    model_constraint_sql = " ".join(
        str(constraint.sqltext)
        for constraint in AdminTargetNotice.__table__.constraints
        if hasattr(constraint, "sqltext")
    )
    model_index_columns = {
        index.name: tuple(column.name for column in index.columns)
        for index in AdminAction.__table__.indexes
    }
    assert NOTICE_CONSTRAINTS <= model_constraint_names
    assert all(name in migration_source for name in NOTICE_CONSTRAINTS)
    for notice_type in (
        "game_chat_message_removed",
        "game_chat_message_restored",
        "need_sub_chat_message_removed",
        "need_sub_chat_message_restored",
    ):
        assert notice_type in migration_source
        assert notice_type in model_constraint_sql

    with _session() as db:
        inspector = inspect(db.bind)
        live_constraint_names = {
            item["name"]
            for item in inspector.get_check_constraints("admin_target_notices")
        }
        live_indexes = {
            item["name"]: item for item in inspector.get_indexes("admin_actions")
        }

    assert NOTICE_CONSTRAINTS <= live_constraint_names
    for index_name, expected_columns in IDEMPOTENCY_INDEX_COLUMNS.items():
        assert model_index_columns[index_name] == expected_columns
        assert tuple(live_indexes[index_name]["column_names"]) == expected_columns
        assert live_indexes[index_name]["unique"] is True
        assert (
            live_indexes[index_name]["dialect_options"]["postgresql_where"]
            is not None
        )


@pytest.mark.parametrize(
    ("notice_type", "target_kind", "expected_constraint"),
    (
        (
            "unsupported_notice_type",
            "user",
            "ck_admin_target_notices_notice_type",
        ),
        (
            "game_chat_message_removed",
            "sub_post",
            "ck_admin_target_notices_game_enforcement_target",
        ),
        (
            "need_sub_chat_message_removed",
            "game",
            "ck_admin_target_notices_sub_enforcement_target",
        ),
        (
            "need_sub_post_removed",
            "game",
            "ck_admin_target_notices_sub_removal_target",
        ),
    ),
)
def test_live_notice_constraints_reject_unsupported_type_and_target_shapes(
    notice_type: str,
    target_kind: str,
    expected_constraint: str,
) -> None:
    admin = _user(f"05c-schema-admin-{uuid.uuid4()}", role="admin")
    target = _user(f"05c-schema-target-{uuid.uuid4()}")
    _add_users(admin, target)
    game_id, _ = _persist_community_game_fixture(
        f"05c-schema-game-{uuid.uuid4()}",
        admin=admin,
        host=target,
    )
    post_id = _persist_sub_post_fixture(
        f"05c-schema-post-{uuid.uuid4()}",
        owner=target,
    )
    target_fields = {
        "target_user_id": target.id if target_kind == "user" else None,
        "target_game_id": game_id if target_kind == "game" else None,
        "target_sub_post_id": post_id if target_kind == "sub_post" else None,
    }
    with _session() as db:
        db.add(
            AdminTargetNotice(
                id=uuid.uuid4(),
                recipient_user_id=target.id,
                notice_type=notice_type,
                notice_status="active",
                title="Schema rejection",
                body="This row must be rejected.",
                user_safe_reason=None,
                created_by_user_id=admin.id,
                **target_fields,
            )
        )
        with pytest.raises(IntegrityError) as rejected:
            db.flush()
        assert rejected.value.orig.diag.constraint_name == expected_constraint
        db.rollback()
