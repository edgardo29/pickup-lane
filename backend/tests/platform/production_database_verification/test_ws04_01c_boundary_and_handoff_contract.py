from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.no_db_cleanup

_REPO_ROOT = Path(__file__).resolve().parents[4]
_PLAN = (
    "docs/production-readiness/planning/passes/ws04/"
    "ws04-01c-production-postgresql-topology-connection-budget-role-verification.md"
)
_INTAKE = "docs/production-readiness/planning/passes/ws04/ws04-01-intake.md"
_REGISTER = "docs/production-readiness/planning/program/PASS-EXECUTION-REGISTER.md"
_BLUEPRINT = (
    "docs/production-readiness/planning/program/"
    "pickup-lane-master-production-readiness-blueprint.md"
)
_CONTRACT_PATH = (
    "docs/production-readiness/planning/passes/ws04/"
    "ws04-01c-production-database-evidence-contract.json"
)


def _read(relative_path: str) -> str:
    return (_REPO_ROOT / relative_path).read_text()


@pytest.mark.requirement("WS04-01C-R1", "WS04-01C-R5", "WS04-01C-R8")
def test_current_authority_preserves_provider_independent_c_and_mandatory_d() -> None:
    plan = _read(_PLAN)
    intake = _read(_INTAKE)
    register = _read(_REGISTER)
    blueprint = _read(_BLUEPRINT)

    for source in (plan, intake, register):
        assert "WS04-01C" in source
        assert "WS04-01D" in source
        assert "final production" in source

    assert "WS04-01" in blueprint
    assert "mandatory deferred follow-up" in blueprint
    assert "Final production hosting and database-hosting infrastructure" in blueprint
    assert "provider-independent production-verification framework" in register
    assert "### Mandatory deferred follow-up" in intake
    assert "D is mandatory before `CLOSE-01`" in plan
    assert "temporary development/demo infrastructure" in plan
    assert "Final provider-specific\nvalues remain late-bound" in register


@pytest.mark.requirement("WS04-01C-R1", "WS04-01C-R7", "WS04-01C-R8")
def test_gate_b_scope_does_not_introduce_production_source_config_or_migrations() -> None:
    plan = _read(_PLAN)
    settings = _read("backend/settings.py")
    env_example = _read("backend/.env.example")
    migration_paths = sorted((_REPO_ROOT / "backend/alembic/versions").glob("*.py"))

    assert "Production application source, migrations, database schema" in plan
    assert "provider settings" in plan
    assert "deployment settings" in plan
    assert "credentials" in plan
    assert "real production role/grant state should\nnot change merely to complete C" in plan
    assert "WS04-01C" not in settings
    assert "WS04_01C" not in env_example
    assert not [path for path in migration_paths if "ws04_01c" in path.name.lower()]


@pytest.mark.requirement("WS04-01C-R2", "WS04-01C-R8")
def test_contract_handoff_names_all_d_owned_final_facts_without_values() -> None:
    contract = json.loads((_REPO_ROOT / _CONTRACT_PATH).read_text())

    assert contract["handoff"]["mandatory_follow_up"] == "WS04-01D"
    assert contract["handoff"]["required_before"] == ["CLOSE-01", "CLOSE-02"]
    assert {
        "actual provider usable connection capacity",
        "pooler/proxy/direct mode",
        "actual API instance/process/autoscaling/rolling-overlap topology",
        "deployed application pool values and connection wait behavior",
        "final deployment-wide peak and headroom",
        "real grants, ownership, search path, default privileges, and operational database access",
    } <= set(contract["handoff"]["d_owned_facts"])

    for calculation in contract["budget_model"]["reported_calculations"].values():
        assert calculation is None
