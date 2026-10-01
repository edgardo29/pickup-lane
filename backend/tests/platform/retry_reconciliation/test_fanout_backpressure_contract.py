from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.no_db_cleanup

_REPO_ROOT = Path(__file__).resolve().parents[4]
_FANOUT_OWNER_FILES = (
    "backend/services/platform_notice_service.py",
    "backend/services/game_chat_service.py",
    "backend/services/sub_post_chat_service.py",
    "backend/services/game_notification_service.py",
    "backend/services/game_waitlist_service.py",
    "backend/services/account_deletion_service.py",
    "backend/services/game_cancellation_service.py",
    "backend/services/official_game_player_removal_service.py",
    "backend/services/admin_financial_outcome_service.py",
    "backend/services/stripe_webhook_service.py",
)


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        if parent:
            return f"{parent}.{node.attr}"
    return None


@pytest.mark.pass_provenance('WS02-04C2')
def test_current_fanout_sources_do_not_introduce_unapproved_parallel_execution() -> None:
    prohibited_calls: list[str] = []
    prohibited_imports: list[str] = []

    for relative_path in _FANOUT_OWNER_FILES:
        path = _REPO_ROOT / relative_path
        tree = ast.parse(path.read_text(), filename=relative_path)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [alias.name for alias in getattr(node, "names", [])]
                module = getattr(node, "module", None)
                if module in {"threading", "multiprocessing", "concurrent.futures"}:
                    prohibited_imports.append(relative_path)
                if any(name in {"threading", "multiprocessing"} for name in names):
                    prohibited_imports.append(relative_path)
            if isinstance(node, ast.Call):
                call_name = _call_name(node.func)
                if call_name in {
                    "asyncio.gather",
                    "asyncio.create_task",
                    "BackgroundTasks",
                    "run_in_executor",
                    "ThreadPoolExecutor",
                    "ProcessPoolExecutor",
                }:
                    prohibited_calls.append(f"{relative_path}: {call_name}")

    assert prohibited_imports == []
    assert prohibited_calls == []
