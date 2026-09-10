from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = [pytest.mark.no_db_cleanup, pytest.mark.suite_type("ordinary")]

REPO_ROOT = Path(__file__).resolve().parents[4]
SERVICES_ROOT = REPO_ROOT / "backend/services"


def _production_service_trees() -> list[tuple[Path, ast.AST]]:
    return [
        (path, ast.parse(path.read_text(encoding="utf-8")))
        for path in sorted(SERVICES_ROOT.glob("*.py"))
    ]


@pytest.mark.requirement("WS09-02A-R8")
def test_every_production_admin_action_writer_uses_explicit_outcome_and_database_time() -> (
    None
):
    calls: list[tuple[Path, ast.Call]] = []
    for path, tree in _production_service_trees():
        calls.extend(
            (path, node)
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "record_admin_action"
        )

    assert len(calls) == 46
    for path, call in calls:
        keyword_names = {keyword.arg for keyword in call.keywords}
        assert "outcome" in keyword_names, path
        assert "created_at" not in keyword_names, path


@pytest.mark.requirement("WS09-02A-R8")
def test_commit_owning_compatibility_paths_do_not_rewrite_admin_action_rows() -> None:
    refund_source = (SERVICES_ROOT / "admin_money_refund_service.py").read_text(
        encoding="utf-8"
    )
    review_source = (SERVICES_ROOT / "admin_review_service.py").read_text(
        encoding="utf-8"
    )
    financial_source = (SERVICES_ROOT / "admin_financial_outcome_service.py").read_text(
        encoding="utf-8"
    )
    need_sub_source = (SERVICES_ROOT / "need_a_sub_post_service.py").read_text(
        encoding="utf-8"
    )
    issue_source = (SERVICES_ROOT / "admin_money_issue_service.py").read_text(
        encoding="utf-8"
    )

    assert 'event_type="provider_result_recorded"' in refund_source
    assert "admin_action.metadata_" not in refund_source
    assert 'action_metadata["event_id"]' not in review_source
    assert "add_notice_id_to_action_metadata" not in financial_source
    assert need_sub_source.index("closed_request_ids =") < need_sub_source.index(
        'action_type="remove_sub_post"'
    )
    assert '"failure": "game_credit_ledger_error"' in issue_source
