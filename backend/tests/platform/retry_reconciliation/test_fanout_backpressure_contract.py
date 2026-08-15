from __future__ import annotations

import ast
from pathlib import Path

import pytest

import backend.services.provider_retry_policy as retry_policy

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


@pytest.mark.requirement("WS02-04C2-R8")
def test_frozen_fanout_inventory_is_represented_as_synchronous_sequential_policy() -> None:
    policies = {
        policy.workflow: policy
        for policy in retry_policy.FANOUT_EXECUTION_POLICIES
    }

    assert policies["platform_notice.selected_user_publish"].current_bound == (
        "Selected-user product maximum is 500 recipients."
    )
    assert policies["game_chat.notification_rows"].provider_calls_per_item == "none"
    assert policies["need_a_sub_chat.notification_rows"].provider_calls_per_item == "none"
    assert policies["game_updated.notification_rows"].provider_calls_per_item == "none"
    assert "possible Stripe payment" in policies[
        "waitlist.promotion"
    ].provider_calls_per_item
    assert "Firebase delete or Stripe detach" in policies[
        "account_deletion.cleanup"
    ].provider_calls_per_item
    assert "Stripe refund" in policies[
        "official_game_cancellation.refunds"
    ].provider_calls_per_item
    assert "Stripe refund" in policies[
        "official_game_player_removal.refunds"
    ].provider_calls_per_item
    assert policies[
        "community_publish_fee.financial_outcome_refund"
    ].execution_model == "single_admin_state_gated_workflow"
    assert policies["late_checkout_payment.refund"].execution_model == (
        "single_webhook_repair_helper"
    )

    for policy in policies.values():
        assert policy.new_concurrency_allowed is False
        assert policy.approved_concurrency_cap is None
        assert policy.approved_batch_size is None


@pytest.mark.requirement("WS02-04C2-R8")
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


@pytest.mark.requirement("WS02-04C2-R8")
def test_product_audience_bounds_are_not_treated_as_worker_or_provider_limits() -> None:
    selected_user_policy = retry_policy.FANOUT_EXECUTION_POLICIES[0]

    assert selected_user_policy.workflow == "platform_notice.selected_user_publish"
    assert "500 recipients" in selected_user_policy.current_bound
    assert selected_user_policy.approved_batch_size is None
    assert selected_user_policy.approved_concurrency_cap is None
    assert "worker" not in selected_user_policy.current_bound.lower()
    assert "provider" not in selected_user_policy.current_bound.lower()
