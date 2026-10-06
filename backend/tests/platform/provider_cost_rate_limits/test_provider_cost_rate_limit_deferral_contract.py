from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.no_db_cleanup

_REPO_ROOT = Path(__file__).resolve().parents[4]

_LIMITS_REGISTER = "docs/production-readiness/governance/limits-and-thresholds-register.md"


def _read(relative_path: str) -> str:
    return (_REPO_ROOT / relative_path).read_text()


@pytest.mark.pass_provenance('WS02-04C3B')
def test_non_chat_costly_action_rate_limits_remain_unapproved_in_current_governance() -> None:
    register = _read(_LIMITS_REGISTER)

    assert "No numeric non-chat costly-action rate policy is approved" in register
    assert "Stripe payment creation and saved-card actions" in register
    assert "Cloudflare R2 upload authorization" in register
    assert "remain TBD pending owner decision and evidence" in register


@pytest.mark.pass_provenance('WS02-04C3B')
def test_deferred_rate_control_scope_excludes_config_migrations_and_limiter_state() -> None:
    settings = _read("backend/settings.py")
    env_example = _read("backend/.env.example")
    migrations = sorted((_REPO_ROOT / "backend/alembic/versions").glob("*.py"))

    assert "Gate B must not add" not in settings
    assert "PROVIDER_COST_RATE" not in settings
    assert "PROVIDER_COST_RATE" not in env_example
    assert "C3B" not in env_example
    assert not [
        path
        for path in migrations
        if "rate" in path.name.lower() or "limiter" in path.name.lower()
    ]


@pytest.mark.pass_provenance('WS02-04C3B')
def test_no_numeric_provider_rate_policy_or_generic_limiter_artifact_is_approved() -> None:
    register = _read(_LIMITS_REGISTER)
    backend_paths = {
        path.relative_to(_REPO_ROOT).as_posix()
        for path in (_REPO_ROOT / "backend").rglob("*.py")
        if ".venv" not in path.parts
        and "tests" not in path.relative_to(_REPO_ROOT).parts
        and "__pycache__" not in path.parts
    }

    assert "No numeric non-chat costly-action rate policy is approved" in register
    assert "TBD - owner decision and evidence required" in register
    assert not any(path.endswith("rate_limit_middleware.py") for path in backend_paths)
    assert not any(path.endswith("provider_cost_rate_limit_service.py") for path in backend_paths)
    assert not any(path.endswith("limiter_service.py") for path in backend_paths)


@pytest.mark.pass_provenance('WS02-04C3B')
def test_chat_is_the_only_approved_source_owned_rate_limit_exception() -> None:
    register = _read(_LIMITS_REGISTER)

    assert "5 visible text messages per sender per chat per rolling 60-second window" in register
    assert "applies only to game chat and Need-a-Sub chat" in register
    assert "must not be reused as a default for unrelated actions" in register
