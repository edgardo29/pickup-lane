from __future__ import annotations

import re
from pathlib import Path

import pytest
from sqlalchemy import CheckConstraint, Index, UniqueConstraint, inspect

from backend.models import (
    AdminContentModerationFinding,
    GameChatMessageDetection,
    SubPostChatMessageDetection,
)
from backend.services.moderation_taxonomy import (
    CHAT_DETECTION_OUTCOMES,
    CHAT_SEVERITIES,
    RISK_AREAS,
    SAVED_FINDING_TYPES,
    SAVED_PRIORITIES,
)

pytestmark = pytest.mark.suite_type("ordinary")

_REPO_ROOT = Path(__file__).resolve().parents[4]
_TABLE_CONTRACTS = (
    (
        AdminContentModerationFinding,
        _REPO_ROOT
        / "backend/alembic/versions/0056_create_admin_content_moderation_findings_table.py",
    ),
    (
        GameChatMessageDetection,
        _REPO_ROOT
        / "backend/alembic/versions/0039_create_game_chat_message_detections_table.py",
    ),
    (
        SubPostChatMessageDetection,
        _REPO_ROOT
        / "backend/alembic/versions/0034_create_sub_post_chat_message_detections_table.py",
    ),
)


def _session():
    from backend.database import SessionLocal

    return SessionLocal()


def _named_model_constraints(model, constraint_type) -> set[str]:
    return {
        constraint.name
        for constraint in model.__table__.constraints
        if isinstance(constraint, constraint_type) and constraint.name
    }


def _check_values(model, constraint_name: str) -> set[str]:
    constraint = next(
        item
        for item in model.__table__.constraints
        if isinstance(item, CheckConstraint) and item.name == constraint_name
    )
    return set(re.findall(r"'([^']+)'", str(constraint.sqltext)))


@pytest.mark.requirement("WS03-05A-R6")
def test_models_canonical_migrations_and_live_schema_share_the_same_contract() -> None:
    with _session() as db:
        inspector = inspect(db.bind)
        for model, migration_path in _TABLE_CONTRACTS:
            table = model.__table__
            migration_source = migration_path.read_text()
            model_columns = {column.name for column in table.columns}
            live_columns = {
                column["name"] for column in inspector.get_columns(table.name)
            }
            assert live_columns == model_columns

            model_checks = _named_model_constraints(model, CheckConstraint)
            live_checks = {
                constraint["name"]
                for constraint in inspector.get_check_constraints(table.name)
            }
            assert live_checks == model_checks

            model_unique = _named_model_constraints(model, UniqueConstraint)
            live_unique = {
                constraint["name"]
                for constraint in inspector.get_unique_constraints(table.name)
            }
            assert model_unique <= live_unique

            model_indexes = {
                index.name
                for index in table.indexes
                if isinstance(index, Index) and index.name
            }
            live_indexes = {
                index["name"] for index in inspector.get_indexes(table.name)
            }
            assert model_indexes <= live_indexes

            for name in model_columns | model_checks | model_unique | model_indexes:
                assert name in migration_source


@pytest.mark.requirement("WS03-05A-R1", "WS03-05A-R6")
def test_registry_model_migration_and_live_database_finite_sets_are_equal() -> None:
    finite_contracts = (
        (
            AdminContentModerationFinding,
            "ck_admin_content_moderation_findings_finding_type",
            SAVED_FINDING_TYPES,
            _TABLE_CONTRACTS[0][1],
        ),
        (
            AdminContentModerationFinding,
            "ck_admin_content_moderation_findings_priority",
            SAVED_PRIORITIES,
            _TABLE_CONTRACTS[0][1],
        ),
        (
            AdminContentModerationFinding,
            "ck_admin_content_moderation_findings_risk_area",
            RISK_AREAS,
            _TABLE_CONTRACTS[0][1],
        ),
        (
            GameChatMessageDetection,
            "ck_game_chat_message_detections_category",
            CHAT_DETECTION_OUTCOMES,
            _TABLE_CONTRACTS[1][1],
        ),
        (
            GameChatMessageDetection,
            "ck_game_chat_message_detections_severity",
            CHAT_SEVERITIES,
            _TABLE_CONTRACTS[1][1],
        ),
        (
            SubPostChatMessageDetection,
            "ck_sub_post_chat_message_detections_category",
            CHAT_DETECTION_OUTCOMES,
            _TABLE_CONTRACTS[2][1],
        ),
        (
            SubPostChatMessageDetection,
            "ck_sub_post_chat_message_detections_severity",
            CHAT_SEVERITIES,
            _TABLE_CONTRACTS[2][1],
        ),
    )
    with _session() as db:
        inspector = inspect(db.bind)
        for model, constraint_name, expected_values, migration_path in finite_contracts:
            assert _check_values(model, constraint_name) == set(expected_values)
            live_constraint = next(
                item
                for item in inspector.get_check_constraints(model.__tablename__)
                if item["name"] == constraint_name
            )
            assert set(re.findall(r"'([^']+)'", live_constraint["sqltext"])) == set(
                expected_values
            )
            migration_source = migration_path.read_text()
            assert constraint_name in migration_source
            assert all(f"'{value}'" in migration_source for value in expected_values)
