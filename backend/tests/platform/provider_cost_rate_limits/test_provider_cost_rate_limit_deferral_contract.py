from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.no_db_cleanup

_REPO_ROOT = Path(__file__).resolve().parents[4]

_MASTER = "docs/production-readiness/planning/program/pickup-lane-master-production-readiness-blueprint.md"


def _read(relative_path: str) -> str:
    return (_REPO_ROOT / relative_path).read_text()


@pytest.mark.pass_provenance('WS02-04C3B')
def test_non_chat_costly_actions_require_operation_specific_controls_before_traffic() -> None:
    master = _read(_MASTER)

    assert "- a blanket rate limiter;" in master
    assert "Pass 07 requirements 4, 6, 9, 10, 18, and 24 control booking, payment, refund, credit, and Stripe requests" in master
    assert "Pass 09 requirements 3, 4, 8, 9, and 11 control administrative image-upload and Cloudflare R2 requests" in master
    assert "a second request limiter must not be added when an existing control already proves that result" in master


@pytest.mark.pass_provenance('WS02-04C3B')
def test_deferred_rate_control_scope_excludes_config_migrations_and_limiter_state() -> None:
    settings = _read("backend/settings.py")
    env_example = _read("backend/.env.example")
    migrations = sorted((_REPO_ROOT / "backend/alembic/versions").glob("*.py"))

    assert "PROVIDER_COST_RATE" not in settings
    assert "NON_CHAT_RATE" not in settings
    assert "GENERIC_RATE_LIMIT" not in settings
    assert "PROVIDER_COST_RATE" not in env_example
    assert "NON_CHAT_RATE" not in env_example
    assert "GENERIC_RATE_LIMIT" not in env_example
    assert not [
        path
        for path in migrations
        if "rate" in path.name.lower() or "limiter" in path.name.lower()
    ]


@pytest.mark.pass_provenance('WS02-04C3B')
def test_no_numeric_non_chat_rate_policy_or_generic_limiter_artifact_is_configured() -> None:
    settings = _read("backend/settings.py")
    env_example = _read("backend/.env.example")
    backend_paths = {
        path.relative_to(_REPO_ROOT).as_posix()
        for path in (_REPO_ROOT / "backend").rglob("*.py")
        if ".venv" not in path.parts
        and "tests" not in path.relative_to(_REPO_ROOT).parts
        and "__pycache__" not in path.parts
    }

    for name in ("PROVIDER_COST_RATE", "NON_CHAT_RATE", "GENERIC_RATE_LIMIT"):
        assert name not in settings
        assert name not in env_example
    assert not any(path.endswith("rate_limit_middleware.py") for path in backend_paths)
    assert not any(path.endswith("provider_cost_rate_limit_service.py") for path in backend_paths)
    assert not any(path.endswith("limiter_service.py") for path in backend_paths)


@pytest.mark.pass_provenance('WS02-04C3B')
def test_chat_is_the_only_current_source_owned_rate_limit_exception() -> None:
    limiter = _read("backend/services/chat_rate_limit_service.py")
    game_chat = _read("backend/services/game_chat_service.py")
    need_a_sub_chat = _read("backend/services/sub_post_chat_service.py")

    assert "CHAT_RATE_LIMIT_MAX_VISIBLE_TEXT_MESSAGES = 5" in limiter
    assert "CHAT_RATE_LIMIT_WINDOW_SECONDS = 60" in limiter
    assert 'limiter_category="game_chat"' in game_chat
    assert 'limiter_category="need_a_sub_chat"' in need_a_sub_chat
