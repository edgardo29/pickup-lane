from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import CHAR, DateTime, Integer

from backend.database_metadata import Base
from backend.models import (
    Booking,
    CommunityGameDetail,
    Game,
    GameCredit,
    GameCreditUsage,
    HostPublishFee,
    MoneyIssue,
    Payment,
    Refund,
)
import backend.services.database_value_sql_safety_policy as value_policy

pytestmark = pytest.mark.no_db_cleanup

_REPO_ROOT = Path(__file__).resolve().parents[4]
_REQUIREMENT_IDS = {f"WS04-02C-R{index}" for index in range(1, 9)}


def _source(relative_path: str) -> str:
    return (_REPO_ROOT / relative_path).read_text()


def _combined_source(*relative_roots: str) -> str:
    chunks: list[str] = []
    for relative_root in relative_roots:
        root = _REPO_ROOT / relative_root
        chunks.extend(
            path.read_text()
            for path in sorted(root.rglob("*.py"))
            if "legacy" not in path.parts
            and "__pycache__" not in path.parts
            and path.name != "database_value_sql_safety_policy.py"
        )
    return "\n".join(chunks)


def _constraint_names(model: type[object]) -> set[str]:
    return {
        constraint.name
        for constraint in model.__table__.constraints
        if constraint.name is not None
    }


def _server_default(column) -> str:
    default = column.server_default
    if default is None:
        return ""
    return str(default.arg)


@pytest.mark.requirement("WS04-02C-R1", "WS04-02C-R8")
def test_value_sql_safety_policy_declares_complete_current_scope() -> None:
    families = value_policy.DATABASE_VALUE_SQL_SAFETY_FAMILIES
    family_ids = [family.family_id for family in families]

    assert family_ids == [
        "timestamp_and_update_timestamps",
        "money_currency_and_amounts",
        "status_defaults_and_state_machines",
        "json_defaults_and_payload_shapes",
        "production_raw_sql",
        "migration_sql_expressions",
        "sql_and_value_logging_safety",
        "accepted_database_contract_boundaries",
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


@pytest.mark.requirement("WS04-02C-R2", "WS04-02C-R8")
def test_persisted_datetime_columns_are_timezone_aware_without_implicit_onupdate() -> None:
    naive_columns = []
    implicit_onupdate_columns = []

    for table in Base.metadata.sorted_tables:
        for column in table.columns:
            if isinstance(column.type, DateTime) and not column.type.timezone:
                naive_columns.append(f"{table.name}.{column.name}")
            if column.onupdate is not None:
                implicit_onupdate_columns.append(f"{table.name}.{column.name}")

    assert naive_columns == []
    assert implicit_onupdate_columns == []
    source = _combined_source("backend/models", "backend/services", "backend/routes", "backend/schemas")
    assert "datetime.utcnow(" not in source
    assert "datetime.now()" not in source


@pytest.mark.requirement("WS04-02C-R3", "WS04-02C-R4", "WS04-02C-R8")
def test_money_and_status_defaults_match_current_model_constraints() -> None:
    money_models = (
        Booking,
        Game,
        GameCredit,
        GameCreditUsage,
        HostPublishFee,
        MoneyIssue,
        Payment,
        Refund,
    )

    for model in money_models:
        table = model.__table__
        constraints = _constraint_names(model)
        assert isinstance(table.c.currency.type, CHAR)
        assert table.c.currency.type.length == 3
        assert _server_default(table.c.currency) == "'USD'"
        assert f"ck_{table.name}_currency" in constraints

        cent_columns = [
            column for column in table.columns if column.name.endswith("_cents")
        ]
        assert cent_columns
        assert all(isinstance(column.type, Integer) for column in cent_columns)

    assert _server_default(Booking.__table__.c.booking_status) == "'pending_payment'"
    assert _server_default(Booking.__table__.c.payment_status) == "'unpaid'"
    assert _server_default(CommunityGameDetail.__table__.c.payment_text_moderation_status) == "'visible'"
    assert _server_default(GameCredit.__table__.c.credit_status) == "'active'"
    assert _server_default(Payment.__table__.c.provider) == "'stripe'"


@pytest.mark.requirement("WS04-02C-R1", "WS04-02C-R8")
def test_requirement_declaration_matches_frozen_ws04_02c_scope() -> None:
    declaration = json.loads(
        _source("backend/tests/support/requirements/ws04_02c.json")
    )

    requirements = declaration["requirements"]
    assert declaration["schema_version"] == 1
    assert {requirement["id"] for requirement in requirements} == _REQUIREMENT_IDS
    assert {requirement["owning_pass"] for requirement in requirements} == {"WS04-02C"}
    assert {requirement["state"] for requirement in requirements} == {"required"}
    assert {
        requirement["scope"]
        for requirement in requirements
    } == {"workflows/database_value_default_sql_safety_compatibility"}

    rendered_policy = repr(value_policy.DATABASE_VALUE_SQL_SAFETY_FAMILIES)
    assert "final production PostgreSQL topology" in value_policy.LATER_OWNED_EVIDENCE["WS04-01D"]
    assert "DATABASE" + "_URL" not in rendered_policy
    assert "postgresql" + "://" not in rendered_policy
