from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.no_db_cleanup

_REPO_ROOT = Path(__file__).resolve().parents[4]

_C3B_PLAN = "docs/production-readiness/planning/ws02-04c3b-provider-cost-rate-limit-deferral.md"
_LIMITS_REGISTER = "docs/production-readiness/governance/limits-and-thresholds-register.md"
_SOURCE_OWNED_CLOSEOUT = "docs/production-readiness/planning/ws02-04-source-owned-closeout.md"


def _read(relative_path: str) -> str:
    return (_REPO_ROOT / relative_path).read_text()


@pytest.mark.requirement("WS02-04C3B-R2", "WS02-04C3B-R3", "WS02-04C3B-R7")
def test_c3b_deferral_agrees_across_plan_register_and_closeout() -> None:
    plan = _read(_C3B_PLAN)
    register = _read(_LIMITS_REGISTER)
    closeout = _read(_SOURCE_OWNED_CLOSEOUT)

    assert (
        "The current authoritative conclusion is that C3B does not approve any new\n"
        "source-owned provider-cost/action limiter"
    ) in plan
    assert "No numeric rate policy is approved" in plan
    assert "claim API-M11 is closed" in plan
    assert "C3B provider-cost/action values are not approved" in register
    assert "Provider-cost action rates" in closeout
    assert "remain open or evidence-deferred" in closeout


@pytest.mark.requirement("WS02-04C3B-R2", "WS02-04C3B-R5", "WS02-04C3B-R7")
def test_gate_b_scope_excludes_production_config_migration_and_limiter_state() -> None:
    plan = _read(_C3B_PLAN)
    settings = _read("backend/settings.py")
    env_example = _read("backend/.env.example")
    migrations = sorted((_REPO_ROOT / "backend/alembic/versions").glob("*.py"))

    assert "frozen and is not a Gate B editable file" in plan
    assert "Production correction set\n\nNONE" in plan
    assert "Configuration correction set\n\nNONE" in plan
    assert "Gate B must not add rate-limit settings" in plan
    assert "Gate B must not add" not in settings
    assert "PROVIDER_COST_RATE" not in settings
    assert "PROVIDER_COST_RATE" not in env_example
    assert "C3B" not in env_example
    assert not [
        path
        for path in migrations
        if "rate" in path.name.lower() or "limiter" in path.name.lower()
    ]


@pytest.mark.requirement("WS02-04C3B-R2", "WS02-04C3B-R5")
def test_no_numeric_c3b_rate_policy_or_generic_limiter_artifact_is_approved() -> None:
    plan = _read(_C3B_PLAN)
    register = _read(_LIMITS_REGISTER)
    backend_paths = {
        path.relative_to(_REPO_ROOT).as_posix()
        for path in (_REPO_ROOT / "backend").rglob("*.py")
        if ".venv" not in path.parts
        and "tests" not in path.relative_to(_REPO_ROOT).parts
        and "__pycache__" not in path.parts
    }

    assert "must not approve or implement any of the following" in plan
    for phrase in (
        "a maximum request or action count",
        "a time window",
        "a limiter key, scope, actor, token, user, resource, provider-object, IP",
        "rate-limit `Retry-After` semantics",
        "PostgreSQL, Redis, in-memory, provider-dashboard, edge, or auth-provider",
        "limiter-state retention",
        "telemetry or alert thresholds",
        "rollout, rollback, or safe-adjustment procedure",
    ):
        assert phrase in plan

    assert "TBD - owner decision and evidence required" in register
    assert not any(path.endswith("rate_limit_middleware.py") for path in backend_paths)
    assert not any(path.endswith("provider_cost_rate_limit_service.py") for path in backend_paths)
    assert not any(path.endswith("limiter_service.py") for path in backend_paths)


@pytest.mark.requirement("WS02-04C3B-R2", "WS02-04C3B-R4", "WS02-04C3B-R7")
def test_c3a_chat_is_the_only_approved_source_owned_rate_limit_exception() -> None:
    plan = _read(_C3B_PLAN)
    register = _read(_LIMITS_REGISTER)
    c3a_plan = _read("docs/production-readiness/planning/ws02-04c3a-chat-rate-limit-contract.md")

    assert "C3A owns the approved source-owned authenticated chat limiter only" in plan
    assert "C3B must not reuse that value elsewhere" in plan
    assert "C3A chat values approved and source-enforced" in register
    assert "C3B provider-cost/action values are not approved" in register
    assert "does not approve\nprovider-cost action limits" in c3a_plan
    assert "Provider-cost/action rate values" in c3a_plan
