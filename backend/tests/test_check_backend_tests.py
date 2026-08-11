from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from compliance.contracts import MANDATORY_SCENARIOS
from compliance.contracts import Contract
from compliance.mutations import evaluate_mutation_requirement, run_mutation_preflight, run_mutations
from compliance.runtime import EvidenceRecorder, assert_effect, assert_external_call_count, assert_time_boundary
from compliance.runtime import _validate_runtime_records, evaluate_runtime_requirement, run_runtime_validation
from compliance.report import CheckResult, render_report
from compliance.targeting import resolve_target
import compliance.mutations as mutations_module
import compliance.runtime as runtime_module
import check_backend_tests as checker_module
from check_backend_tests import run_checker


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def _base_contract(test_ref: str, *, extras: dict | None = None) -> dict:
    contract = {
        "schema_version": 1,
        "review": {
            "sources": [
                {
                    "id": "spec",
                    "path": "docs/spec.md",
                    "kind": "feature_spec",
                    "summary": "finalized synthetic spec",
                }
            ],
            "conflicts": [],
            "stop_conditions": [],
        },
        "requirements": [
            {
                "id": "REQ-01",
                "source_id": "spec",
                "behavior": "synthetic behavior is covered",
                "status": "covered",
                "test_refs": [test_ref],
            }
        ],
        "state_matrices": [],
        "scenarios": [
            {
                "id": f"SCENARIO-{index}",
                "category": category,
                "item": item,
                "applicability": "not_relevant",
                "reason": "not relevant to this synthetic checker test",
            }
            for index, (category, item) in enumerate(MANDATORY_SCENARIOS)
        ],
        "ownership": [
            {
                "test_ref": test_ref,
                "owner_kind": "page",
                "owner_path": "pages/example",
                "behavior_under_test": "synthetic page behavior",
                "rationale": "owned by the synthetic page target",
            }
        ],
        "effects": [],
        "constraints": [],
        "time_boundaries": [],
        "review_flags": [],
        "gaps": [],
    }
    if extras:
        contract.update(extras)
    return contract


def _write_contract(directory: Path, contract: dict) -> None:
    _write(directory / "_backend_test_contract.py", f"CONTRACT = {contract!r}\n")


def _make_repo(
    tmp_path: Path,
    test_text: str = "def test_valid_request_succeeds():\n    assert 1 == 1\n",
    *,
    with_ci: bool = False,
    pytest_config: str | None = None,
) -> Path:
    repo = tmp_path / "repo"
    target_dir = repo / "backend" / "tests" / "pages" / "example"
    _write(repo / "docs" / "spec.md", "Synthetic spec\n")
    _write(target_dir / "test_api_contract.py", test_text)
    _write_contract(target_dir, _base_contract("test_api_contract.py::test_valid_request_succeeds"))
    if with_ci:
        _write(
            repo / ".github" / "workflows" / "backend.yml",
            "name: backend\n"
            "permissions:\n"
            "  contents: read\n"
            "jobs:\n"
            "  tests:\n"
            "    runs-on: ubuntu-latest\n"
            "    services:\n"
            "      postgres:\n"
            "        image: postgres:16\n"
            "    steps:\n"
            "      - run: DATABASE_URL=postgresql://user:pass@localhost/pickup_lane_test_db alembic upgrade head\n"
            "      - run: DATABASE_URL=postgresql://user:pass@localhost/pickup_lane_test_db pytest backend/tests\n",
        )
    if pytest_config is not None:
        _write(repo / "pytest.ini", pytest_config)
    return repo


def _contract_for_tmp(tmp_path: Path, scoped_data: dict) -> Contract:
    return Contract(path=tmp_path / "_backend_test_contract.py", data=scoped_data, scoped_data=scoped_data)


def test_rejects_broad_target(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    monkeypatch.chdir(repo)

    result = run_checker(["pages"])

    assert result.state == "USAGE_ERROR"
    assert any(issue.rule_id == "TGT003" for issue in result.issues)
    assert result.commands_run == ["python check_backend_tests.py pages"]


def test_rejects_dot_as_broad_target(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    monkeypatch.chdir(repo)

    result = run_checker(["."])

    assert result.state == "USAGE_ERROR"
    assert any(issue.rule_id == "TGT003" for issue in result.issues)


def test_file_level_repo_findings_do_not_fail_local_file(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    monkeypatch.chdir(repo)

    result = run_checker(["pages/example/test_api_contract.py"])

    assert result.state == "PASS"
    assert any(issue.rule_id == "REP002" and issue.severity == "review" for issue in result.issues)


def test_contract_must_be_literal_only(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    contract_path = repo / "backend" / "tests" / "pages" / "example" / "_backend_test_contract.py"
    contract_path.write_text("import os\nCONTRACT = {}\n")
    monkeypatch.chdir(repo)

    result = run_checker(["pages/example/test_api_contract.py"])

    assert result.state == "FAIL"
    assert any(issue.rule_id == "CON002" for issue in result.issues)


def test_state_matrix_uses_extracted_enum_values(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    _write(
        repo / "backend" / "models" / "statuses.py",
        "from enum import Enum\n\nclass GameStatus(str, Enum):\n    published = 'published'\n    cancelled = 'cancelled'\n",
    )
    contract = _base_contract("test_api_contract.py::test_valid_request_succeeds")
    contract["state_matrices"] = [
        {
            "id": "MATRIX-01",
            "name": "status coverage",
            "authoritative_source": {
                "kind": "python_enum",
                "module": "backend.models.statuses",
                "symbol": "GameStatus",
            },
            "classifications": [
                {
                    "value": "published",
                    "expected_behavior": "visible",
                    "classification": "covered",
                    "test_refs": ["test_api_contract.py::test_valid_request_succeeds"],
                }
            ],
        }
    ]
    _write_contract(repo / "backend" / "tests" / "pages" / "example", contract)
    monkeypatch.chdir(repo)

    result = run_checker(["pages/example/test_api_contract.py"])

    assert result.state == "FAIL"
    assert any(issue.rule_id == "CON009" and "missing" in issue.message for issue in result.issues)


def test_manual_state_fallback_blocks_until_review_flag_confirmed(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    contract = _base_contract("test_api_contract.py::test_valid_request_succeeds")
    contract["state_matrices"] = [
        {
            "id": "MATRIX-01",
            "name": "manual values",
            "authoritative_source": {
                "kind": "manual_fallback",
                "manual_values": ["one"],
                "manual_fallback_reason": "dynamic source cannot be extracted",
                "review_flag_id": "REVIEW-MANUAL",
            },
            "classifications": [
                {
                    "value": "one",
                    "expected_behavior": "allowed",
                    "classification": "covered",
                    "test_refs": ["test_api_contract.py::test_valid_request_succeeds"],
                }
            ],
        }
    ]
    contract["review_flags"] = [
        {
            "id": "REVIEW-MANUAL",
            "kind": "manual_fallback",
            "summary": "manual source reviewed",
            "status": "unresolved",
        }
    ]
    _write_contract(repo / "backend" / "tests" / "pages" / "example", contract)
    monkeypatch.chdir(repo)

    result = run_checker(["pages/example/test_api_contract.py"])

    assert result.state == "BLOCKED"
    assert any(issue.rule_id == "CON009" for issue in result.issues)
    assert any(issue.rule_id == "CON018" for issue in result.issues)


def test_structured_effect_requires_runtime_evidence_by_default(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    contract = _base_contract("test_api_contract.py::test_valid_request_succeeds")
    contract["effects"] = [
        {
            "id": "EFF-01",
            "test_ref": "test_api_contract.py::test_valid_request_succeeds",
            "phase": "successful_mutation",
            "kind": "field_equals",
            "model": "backend.models.User",
            "lookup": {"by": "field_values", "fields": {"id": "$user.id"}},
            "after": {"expect": "equals", "value": "removed"},
        }
    ]
    _write_contract(repo / "backend" / "tests" / "pages" / "example", contract)
    monkeypatch.chdir(repo)

    result = run_checker(["pages/example/test_api_contract.py"])

    assert result.state == "BLOCKED"
    assert any(issue.rule_id == "RUN002" for issue in result.issues)


def test_conftest_fixture_import_fails_and_utility_import_is_review(tmp_path, monkeypatch):
    repo = _make_repo(
        tmp_path,
        "from .conftest import api_client, utility\n\n"
        "def test_valid_request_succeeds():\n"
        "    assert 1 == 1\n",
    )
    _write(
        repo / "backend" / "tests" / "pages" / "example" / "conftest.py",
        "import pytest\n\n@pytest.fixture\ndef api_client():\n    return object()\n\ndef utility():\n    return object()\n",
    )
    monkeypatch.chdir(repo)

    result = run_checker(["pages/example/test_api_contract.py"])

    assert result.state == "FAIL"
    assert any(issue.rule_id == "STA003" and issue.severity == "failure" for issue in result.issues)
    assert any(issue.rule_id == "STA003" and issue.severity == "review" for issue in result.issues)


def test_custom_marker_is_reported_as_static_review_finding(tmp_path, monkeypatch):
    repo = _make_repo(
        tmp_path,
        "import pytest\n\n"
        "@pytest.mark.slow\n"
        "def test_valid_request_succeeds():\n"
        "    assert 1 == 1\n",
    )
    monkeypatch.chdir(repo)

    result = run_checker(["pages/example/test_api_contract.py"])

    assert result.state == "PASS"
    assert any(issue.rule_id == "STA014" and issue.severity == "review" for issue in result.issues)


def test_dependency_override_without_reset_fails(tmp_path, monkeypatch):
    repo = _make_repo(
        tmp_path,
        "def test_valid_request_succeeds():\n"
        "    app.dependency_overrides[dep] = override\n"
        "    assert 1 == 1\n",
    )
    monkeypatch.chdir(repo)

    result = run_checker(["pages/example/test_api_contract.py"])

    assert result.state == "FAIL"
    assert any(issue.rule_id == "STA012" for issue in result.issues)


def test_support_factory_assertion_fails_static_scan(tmp_path, monkeypatch):
    repo = _make_repo(
        tmp_path,
        "from backend.tests.support.factories import make_user\n\n"
        "def test_valid_request_succeeds():\n"
        "    assert make_user is not None\n",
    )
    _write(
        repo / "backend" / "tests" / "support" / "factories.py",
        "def make_user():\n"
        "    assert True\n"
        "    return object()\n",
    )
    monkeypatch.chdir(repo)

    result = run_checker(["pages/example/test_api_contract.py"])

    assert result.state == "FAIL"
    assert any(issue.rule_id == "STA017" for issue in result.issues)


def test_broad_exception_can_be_review_mapped(tmp_path, monkeypatch):
    repo = _make_repo(
        tmp_path,
        "def test_valid_request_succeeds():\n"
        "    try:\n"
        "        raise Exception('expected')\n"
        "    except Exception:\n"
        "        assert 1 == 1\n",
    )
    contract = _base_contract("test_api_contract.py::test_valid_request_succeeds")
    contract["review_flags"] = [
        {
            "id": "REVIEW-BROAD",
            "test_ref": "test_api_contract.py::test_valid_request_succeeds",
            "kind": "broad_exception_behavior",
            "summary": "this synthetic test intentionally checks broad exception behavior",
            "status": "confirmed",
        }
    ]
    _write_contract(repo / "backend" / "tests" / "pages" / "example", contract)
    monkeypatch.chdir(repo)

    result = run_checker(["pages/example/test_api_contract.py"])

    assert result.state == "PASS"
    assert any(issue.rule_id == "STA008" and issue.severity == "review" for issue in result.issues)


def test_mutations_without_runtime_is_usage_error(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    monkeypatch.chdir(repo)

    result = run_checker(["pages/example/test_api_contract.py", "--mutations"])

    assert result.state == "USAGE_ERROR"
    assert any(issue.rule_id == "MUT001" for issue in result.issues)


def test_runtime_helpers_assert_and_record_observed_evidence(tmp_path):
    evidence_path = tmp_path / "evidence.jsonl"
    recorder = EvidenceRecorder(evidence_path, "test_file.py::test_records")
    mock = Mock()

    with assert_external_call_count(
        recorder,
        effect_id="EFF-EXTERNAL",
        mock=mock,
        expect="delta",
        delta=1,
    ):
        mock()
    assert_time_boundary(
        recorder,
        time_id="TIME-01",
        baseline="2026-01-01T00:00:00+00:00",
        boundary="equal",
        actual="expired",
        expected="expired",
    )

    evidence = evidence_path.read_text()
    assert '"effect_id": "EFF-EXTERNAL"' in evidence
    assert '"time_id": "TIME-01"' in evidence


def test_clock_controls_cover_non_boundary_wall_clock_tests(tmp_path, monkeypatch):
    repo = _make_repo(
        tmp_path,
        test_text=(
            "from datetime import UTC, datetime, timedelta\n\n"
            "def test_valid_request_succeeds():\n"
            "    now = datetime.now(UTC)\n"
            "    assert now + timedelta(days=7) > now\n"
        ),
    )
    contract_path = repo / "backend" / "tests" / "pages" / "example" / "_backend_test_contract.py"
    contract = _base_contract(
        "test_api_contract.py::test_valid_request_succeeds",
        extras={
            "clock_controls": [
                {
                    "id": "CLOCK-01",
                    "strategy": "captured_test_baseline",
                    "reason": "ordinary generous offset setup",
                    "test_refs": ["test_api_contract.py::test_valid_request_succeeds"],
                }
            ]
        },
    )
    _write_contract(contract_path.parent, contract)
    monkeypatch.chdir(repo)

    result = run_checker(["pages/example/test_api_contract.py"])

    assert result.state == "PASS"


def test_runtime_evidence_must_match_contract_details(tmp_path):
    contract = Contract(
        path=tmp_path / "_backend_test_contract.py",
        data={},
        scoped_data={
            "effects": [
                {
                    "id": "EFF-01",
                    "phase": "successful_mutation",
                    "kind": "field_equals",
                    "after": {"expect": "equals", "value": "removed"},
                }
            ],
            "constraints": [],
            "time_boundaries": [],
        },
    )
    result = CheckResult(target="pages/example", scope="directory")

    _validate_runtime_records(
        contract,
        [
            {
                "type": "effect",
                "effect_id": "EFF-01",
                "kind": "field_equals",
                "expect": "equals",
                "value": "active",
            }
        ],
        result,
    )

    assert result.state == "FAIL"
    assert any(issue.rule_id == "RUN004" and "value mismatch" in issue.message for issue in result.issues)


def test_tgt001_rejects_missing_and_multiple_targets(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    monkeypatch.chdir(repo)

    missing = run_checker([])
    multiple = run_checker(["pages/example/test_api_contract.py", "pages/example"])

    assert missing.state == "USAGE_ERROR"
    assert multiple.state == "USAGE_ERROR"
    assert any(issue.rule_id == "TGT001" for issue in missing.issues)
    assert any(issue.rule_id == "TGT001" for issue in multiple.issues)


def test_tgt002_rejects_target_outside_backend_tests(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    outside = tmp_path / "outside_test.py"
    outside.write_text("def test_outside():\n    pass\n")
    monkeypatch.chdir(repo)

    result = run_checker([str(outside)])

    assert result.state == "USAGE_ERROR"
    assert any(issue.rule_id == "TGT002" for issue in result.issues)


def test_tgt004_rejects_non_leaf_directory(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    _write(repo / "backend" / "tests" / "pages" / "example" / "nested" / "test_nested.py", "def test_nested():\n    pass\n")
    monkeypatch.chdir(repo)

    result = run_checker(["pages/example"])

    assert result.state == "USAGE_ERROR"
    assert any(issue.rule_id == "TGT004" for issue in result.issues)


def test_tgt004_allows_leaf_directory_with_python_cache(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    _write(
        repo / "backend" / "tests" / "pages" / "example" / "test_contract.py",
        "def test_example():\n    assert True\n",
    )
    (repo / "backend" / "tests" / "pages" / "example" / "__pycache__").mkdir()
    monkeypatch.chdir(repo)

    target, result = resolve_target(["pages/example"])

    assert result is None
    assert target is not None
    assert target.scope == "directory"


def test_tgt005_rejects_support_targets(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    _write(repo / "backend" / "tests" / "support" / "factories.py", "def helper():\n    pass\n")
    monkeypatch.chdir(repo)

    result = run_checker(["support/factories.py"])

    assert result.state == "USAGE_ERROR"
    assert any(issue.rule_id == "TGT005" for issue in result.issues)


def test_tgt006_rejects_conftest_target(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    _write(repo / "backend" / "tests" / "pages" / "example" / "conftest.py", "")
    monkeypatch.chdir(repo)

    result = run_checker(["pages/example/conftest.py"])

    assert result.state == "USAGE_ERROR"
    assert any(issue.rule_id == "TGT006" for issue in result.issues)


def test_tgt007_rejects_empty_leaf_without_contract(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    (repo / "backend" / "tests" / "pages" / "empty").mkdir(parents=True)
    monkeypatch.chdir(repo)

    result = run_checker(["pages/empty"])

    assert result.state == "USAGE_ERROR"
    assert any(issue.rule_id == "TGT007" for issue in result.issues)


def test_tgt008_rejects_broad_legacy_and_accepts_legacy_leaf_file(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    legacy_dir = repo / "backend" / "tests" / "legacy" / "old_area"
    _write(repo / "docs" / "spec.md", "Synthetic spec\n")
    _write(legacy_dir / "test_old.py", "def test_valid_request_succeeds():\n    assert 1 == 1\n")
    _write_contract(legacy_dir, _base_contract("test_old.py::test_valid_request_succeeds", extras={
        "ownership": [
            {
                "test_ref": "test_old.py::test_valid_request_succeeds",
                "owner_kind": "legacy",
                "owner_path": "legacy/old_area",
                "behavior_under_test": "legacy behavior",
                "rationale": "legacy leaf target is explicitly allowed",
                "legacy_exception": "legacy area not reorganized yet",
            }
        ]
    }))
    monkeypatch.chdir(repo)

    broad = run_checker(["legacy"])
    exact = run_checker(["legacy/old_area/test_old.py"])

    assert broad.state == "USAGE_ERROR"
    assert any(issue.rule_id == "TGT008" for issue in broad.issues)
    assert exact.scope == "file"
    assert exact.state == "PASS"


@pytest.mark.parametrize(
    "contract_text",
    [
        "import os\nCONTRACT = {}\n",
        "CONTRACT = dict()\n",
        "CONTRACT = {'schema_version': 1, **{}}\n",
        "CONTRACT = {'schema_version': len([])}\n",
        "CONTRACT = {'schema_version': object.attr}\n",
        "CONTRACT = {'requirements': [x for x in []]}\n",
    ],
)
def test_con002_rejects_nonliteral_contract_expressions(tmp_path, monkeypatch, contract_text):
    repo = _make_repo(tmp_path)
    (repo / "backend" / "tests" / "pages" / "example" / "_backend_test_contract.py").write_text(contract_text)
    monkeypatch.chdir(repo)

    result = run_checker(["pages/example/test_api_contract.py"])

    assert result.state == "FAIL"
    assert any(issue.rule_id == "CON002" for issue in result.issues)


@pytest.mark.parametrize(
    ("mutator", "rule_id", "expected_state"),
    [
        (lambda c: c.update({"schema_version": 999}), "CON003", "FAIL"),
        (lambda c: c.update({"review": {"sources": [], "conflicts": [], "stop_conditions": []}}), "CON004", "FAIL"),
        (lambda c: c["review"]["conflicts"].append({"id": "C1", "status": "unresolved", "summary": "conflict"}), "CON005", "BLOCKED"),
        (lambda c: c.update({"requirements": []}), "CON006", "BLOCKED"),
        (lambda c: c["requirements"][0].update({"status": "missing"}), "CON007", "FAIL"),
        (lambda c: c["requirements"][0].update({"test_refs": ["test_api_contract.py::test_missing"]}), "CON008", "FAIL"),
        (lambda c: c["scenarios"][0].update({"applicability": "unknown", "test_refs": ["test_api_contract.py::test_valid_request_succeeds"]}), "CON010", "FAIL"),
        (lambda c: c.update({"ownership": []}), "CON011", "BLOCKED"),
        (lambda c: c.update({"effects": None}), "CON012", "BLOCKED"),
        (lambda c: c.update({"constraints": None}), "CON015", "BLOCKED"),
        (lambda c: c.update({"time_boundaries": None}), "CON016", "BLOCKED"),
        (lambda c: c["gaps"].append({"id": "G1", "status": "accepted_exception", "summary": "gap", "reason": "reason", "approved_by_user": False}), "CON017", "BLOCKED"),
        (lambda c: c["review_flags"].append({"id": "R1", "kind": "mock_boundary", "summary": "needs review", "status": "unresolved"}), "CON018", "BLOCKED"),
    ],
)
def test_contract_rule_failures_are_reported_by_id(tmp_path, monkeypatch, mutator, rule_id, expected_state):
    repo = _make_repo(tmp_path)
    contract = _base_contract("test_api_contract.py::test_valid_request_succeeds")
    mutator(contract)
    _write_contract(repo / "backend" / "tests" / "pages" / "example", contract)
    monkeypatch.chdir(repo)

    result = run_checker(["pages/example/test_api_contract.py"])

    assert result.state == expected_state
    assert any(issue.rule_id == rule_id for issue in result.issues)


def test_con001_missing_contract_reports_contract_path(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    contract_path = repo / "backend" / "tests" / "pages" / "example" / "_backend_test_contract.py"
    contract_path.unlink()
    monkeypatch.chdir(repo)

    result = run_checker(["pages/example/test_api_contract.py"])

    assert result.state == "FAIL"
    issue = next(issue for issue in result.issues if issue.rule_id == "CON001")
    assert issue.location == str(contract_path)


def test_con009_state_matrix_positive_and_manual_confirmed(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    _write(
        repo / "backend" / "models" / "statuses.py",
        "from enum import Enum\n\nclass GameStatus(str, Enum):\n    active = 'active'\n",
    )
    contract = _base_contract("test_api_contract.py::test_valid_request_succeeds")
    contract["review_flags"] = [
        {
            "id": "REVIEW-MANUAL",
            "kind": "manual_fallback",
            "summary": "manual state source reviewed",
            "status": "confirmed",
        }
    ]
    contract["state_matrices"] = [
        {
            "id": "MATRIX-AUTO",
            "name": "auto",
            "authoritative_source": {
                "kind": "python_enum",
                "module": "backend.models.statuses",
                "symbol": "GameStatus",
            },
            "classifications": [
                {
                    "value": "active",
                    "expected_behavior": "allowed",
                    "classification": "covered",
                    "test_refs": ["test_api_contract.py::test_valid_request_succeeds"],
                }
            ],
        },
        {
            "id": "MATRIX-MANUAL",
            "name": "manual",
            "authoritative_source": {
                "kind": "manual_fallback",
                "manual_values": ["manual"],
                "manual_fallback_reason": "dynamic source",
                "review_flag_id": "REVIEW-MANUAL",
            },
            "classifications": [
                {
                    "value": "manual",
                    "expected_behavior": "allowed",
                    "classification": "covered",
                    "test_refs": ["test_api_contract.py::test_valid_request_succeeds"],
                }
            ],
        },
    ]
    _write_contract(repo / "backend" / "tests" / "pages" / "example", contract)
    monkeypatch.chdir(repo)

    result = run_checker(["pages/example/test_api_contract.py"])

    assert result.state == "PASS"
    assert any("manual authoritative values confirmed" in item for item in result.human_confirmed)


def test_con013_and_con014_structured_effect_validation(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    contract = _base_contract("test_api_contract.py::test_valid_request_succeeds")
    contract["effects"] = [
        {
            "id": "REJECT",
            "test_ref": "test_api_contract.py::test_valid_request_succeeds",
            "phase": "rejected_mutation",
            "kind": "field_equals",
            "model": "backend.models.User",
            "lookup": {"by": "field_values", "fields": {"id": 1}},
        },
        {
            "id": "IDEMP",
            "test_ref": "test_api_contract.py::test_valid_request_succeeds",
            "phase": "idempotency",
            "kind": "field_equals",
            "model": "backend.models.User",
            "lookup": {"by": "field_values", "fields": {"id": 1}},
        },
    ]
    _write_contract(repo / "backend" / "tests" / "pages" / "example", contract)
    monkeypatch.chdir(repo)

    result = run_checker(["pages/example/test_api_contract.py"])

    assert result.state == "FAIL"
    assert any(issue.rule_id == "CON013" for issue in result.issues)
    assert any(issue.rule_id == "CON014" for issue in result.issues)


def test_con015_constraint_source_can_be_extracted(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    _write(
        repo / "backend" / "models" / "booking.py",
        "from sqlalchemy import UniqueConstraint\n\nclass Booking:\n    __table_args__ = (UniqueConstraint('user_id', name='uq_booking_user'),)\n",
    )
    contract = _base_contract("test_api_contract.py::test_valid_request_succeeds")
    contract["constraints"] = [
        {
            "id": "CONSTRAINT-OK",
            "test_ref": "test_api_contract.py::test_valid_request_succeeds",
            "constraint_source": {
                "kind": "sqlalchemy_constraint",
                "module": "backend.models.booking",
            },
            "expected_database_identifier": "uq_booking_user",
        }
    ]
    _write_contract(repo / "backend" / "tests" / "pages" / "example", contract)
    monkeypatch.chdir(repo)

    result = run_checker(["pages/example/test_api_contract.py"])

    assert any(issue.rule_id == "RUN002" for issue in result.issues)
    assert not any(issue.rule_id == "CON015" for issue in result.issues)


def test_directory_level_blockers_for_gaps_conflicts_review_runtime_and_mutation(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path, with_ci=True, pytest_config="[pytest]\n")
    contract = _base_contract("test_api_contract.py::test_valid_request_succeeds")
    contract["review"]["conflicts"].append({"id": "C1", "status": "unresolved", "summary": "conflict"})
    contract["review_flags"].append({"id": "R1", "kind": "mock_boundary", "summary": "unresolved review", "status": "unresolved"})
    contract["gaps"].append({"id": "G1", "status": "open", "summary": "gap", "reason": "gap"})
    contract["effects"].append(
        {
            "id": "EFF-01",
            "test_ref": "test_api_contract.py::test_valid_request_succeeds",
            "phase": "successful_mutation",
            "kind": "field_equals",
            "model": "backend.models.User",
            "lookup": {"by": "field_values", "fields": {"id": 1}},
            "after": {"expect": "equals", "value": "removed"},
        }
    )
    contract["mutation_targets"] = [
        {
            "id": "MUT-TARGET",
            "source_id": "spec",
            "module": "backend.services.example",
            "test_refs": ["test_api_contract.py::test_valid_request_succeeds"],
        }
    ]
    _write_contract(repo / "backend" / "tests" / "pages" / "example", contract)
    monkeypatch.chdir(repo)

    result = run_checker(["pages/example"])

    assert result.state == "BLOCKED"
    assert any(issue.rule_id == "CON005" for issue in result.issues)
    assert any(issue.rule_id == "CON017" for issue in result.issues)
    assert any(issue.rule_id == "CON018" for issue in result.issues)
    assert any(issue.rule_id == "RUN002" for issue in result.issues)
    assert not any(issue.rule_id == "MUT002" for issue in result.issues)
    assert result.completion["Mutation Status"] == "NOT_REQUESTED"


@pytest.mark.parametrize(
    ("test_text", "rule_id", "expected_state"),
    [
        ("def test_valid_request_succeeds(:\n    pass\n", "STA001", "FAIL"),
        ("def test_game():\n    assert 1 == 1\n", "STA002", "FAIL"),
        ("from backend.tests.helpers import old\n\ndef test_valid_request_succeeds():\n    assert 1 == 1\n", "STA004", "FAIL"),
        ("def test_valid_request_succeeds():\n    assert response.status_code < 500\n", "STA006", "FAIL"),
        ("def test_valid_request_succeeds():\n    try:\n        pass\n    except:\n        pass\n", "STA008", "FAIL"),
        ("import time\n\ndef test_valid_request_succeeds():\n    time.sleep(1)\n    assert 1 == 1\n", "STA009", "FAIL"),
        ("import requests\n\ndef test_valid_request_succeeds():\n    requests.get('https://example.com')\n    assert 1 == 1\n", "STA011", "FAIL"),
        ("def test_valid_request_succeeds():\n    app.dependency_overrides[dep] = override\n    assert 1 == 1\n", "STA012", "FAIL"),
        ("def test_valid_request_succeeds(monkeypatch):\n    monkeypatch.setattr(obj, 'name', 1)\n    assert 1 == 1\n", "STA013", "BLOCKED"),
        ("import pytest\n\n@pytest.fixture(scope='module')\ndef fixture_value():\n    return 1\n\ndef test_valid_request_succeeds():\n    assert 1 == 1\n", "STA016", "BLOCKED"),
        ("STATE = []\n\ndef test_valid_request_succeeds():\n    assert 1 == 1\n", "STA019", "PASS"),
        ("import pytest\n\n@pytest.mark.xfail(reason='known')\ndef test_valid_request_succeeds():\n    assert 1 == 1\n", "STA020", "FAIL"),
    ],
)
def test_static_rule_diagnostics_by_id(tmp_path, monkeypatch, test_text, rule_id, expected_state):
    repo = _make_repo(tmp_path, test_text)
    if rule_id == "STA002":
        _write_contract(repo / "backend" / "tests" / "pages" / "example", _base_contract("test_api_contract.py::test_game"))
    monkeypatch.chdir(repo)

    result = run_checker(["pages/example/test_api_contract.py"])

    assert result.state == expected_state
    assert any(issue.rule_id == rule_id for issue in result.issues)


def test_sta005_mutation_status_only_is_review_not_failure(tmp_path, monkeypatch):
    repo = _make_repo(
        tmp_path,
        "def test_create_user_returns_status():\n"
        "    assert response.status_code == 201\n",
    )
    _write_contract(repo / "backend" / "tests" / "pages" / "example", _base_contract("test_api_contract.py::test_create_user_returns_status"))
    monkeypatch.chdir(repo)

    result = run_checker(["pages/example/test_api_contract.py"])

    assert result.state == "PASS"
    assert any(issue.rule_id == "STA005" and issue.severity == "review" for issue in result.issues)


def test_sta007_generic_integrity_error_constraint_failure(tmp_path, monkeypatch):
    repo = _make_repo(
        tmp_path,
        "import pytest\n"
        "from sqlalchemy.exc import IntegrityError\n\n"
        "def test_valid_request_succeeds():\n"
        "    with pytest.raises(IntegrityError):\n"
        "        do_insert()\n",
    )
    contract = _base_contract("test_api_contract.py::test_valid_request_succeeds")
    contract["review_flags"] = [
        {
            "id": "REVIEW-CONSTRAINT",
            "kind": "manual_fallback",
            "summary": "constraint source reviewed",
            "status": "confirmed",
        }
    ]
    contract["constraints"] = [
        {
            "id": "CONSTRAINT",
            "test_ref": "test_api_contract.py::test_valid_request_succeeds",
            "constraint_source": {
                "kind": "manual_fallback",
                "manual_fallback_reason": "synthetic",
                "review_flag_id": "REVIEW-CONSTRAINT",
            },
            "expected_database_identifier": "uq_synthetic",
        }
    ]
    _write_contract(repo / "backend" / "tests" / "pages" / "example", contract)
    monkeypatch.chdir(repo)

    result = run_checker(["pages/example/test_api_contract.py"])

    assert result.state == "FAIL"
    assert any(issue.rule_id == "STA007" for issue in result.issues)


def test_sta010_fixed_future_timestamp_is_review(tmp_path, monkeypatch):
    repo = _make_repo(
        tmp_path,
        "def test_valid_request_succeeds():\n"
        "    starts_at = '2099-01-01T00:00:00+00:00'\n"
        "    assert starts_at\n",
    )
    monkeypatch.chdir(repo)

    result = run_checker(["pages/example/test_api_contract.py"])

    assert result.state == "PASS"
    assert any(issue.rule_id == "STA010" and issue.severity == "review" for issue in result.issues)


def test_sta015_parametrize_review_and_confirmed_positive(tmp_path, monkeypatch):
    repo = _make_repo(
        tmp_path,
        "import pytest\n\n"
        "@pytest.mark.parametrize('value', [1, 2])\n"
        "def test_valid_request_succeeds(value):\n"
        "    assert value\n",
    )
    monkeypatch.chdir(repo)

    result = run_checker(["pages/example/test_api_contract.py"])

    assert result.state == "PASS"
    assert any(issue.rule_id == "STA015" and issue.severity == "review" for issue in result.issues)


def test_sta018_api_helper_factory_name_and_assertion_review(tmp_path, monkeypatch):
    repo = _make_repo(
        tmp_path,
        "from backend.tests.support.api_helpers import user_factory\n\n"
        "def test_valid_request_succeeds():\n"
        "    assert user_factory is not None\n",
    )
    _write(
        repo / "backend" / "tests" / "support" / "api_helpers.py",
        "def user_factory(client):\n"
        "    response = client.post('/users')\n"
        "    assert response.status_code == 201\n"
        "    return response\n",
    )
    monkeypatch.chdir(repo)

    result = run_checker(["pages/example/test_api_contract.py"])

    assert result.state == "FAIL"
    assert any(issue.rule_id == "STA018" and issue.severity == "failure" for issue in result.issues)
    assert any(issue.rule_id == "STA018" and issue.severity == "review" for issue in result.issues)


def test_unimported_api_helpers_are_not_scanned_for_selected_target(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    _write(
        repo / "backend" / "tests" / "support" / "api_helpers.py",
        "def user_factory(client):\n"
        "    response = client.post('/users')\n"
        "    assert response.status_code == 201\n"
        "    return response\n",
    )
    monkeypatch.chdir(repo)

    result = run_checker(["pages/example/test_api_contract.py"])

    assert result.state == "PASS"
    assert not any(issue.rule_id == "STA018" for issue in result.issues)


def test_transitive_support_imports_are_scanned_for_selected_target(tmp_path, monkeypatch):
    repo = _make_repo(
        tmp_path,
        "from backend.tests.support.auth import authenticate_as\n\n"
        "def test_valid_request_succeeds():\n"
        "    assert authenticate_as is not None\n",
    )
    _write(
        repo / "backend" / "tests" / "support" / "auth.py",
        "from backend.tests.support.api_helpers import create_user_factory\n\n"
        "def authenticate_as():\n"
        "    return create_user_factory\n",
    )
    _write(
        repo / "backend" / "tests" / "support" / "api_helpers.py",
        "def create_user_factory(client):\n"
        "    response = client.post('/users')\n"
        "    assert response.status_code == 201\n"
        "    return response\n",
    )
    monkeypatch.chdir(repo)

    result = run_checker(["pages/example/test_api_contract.py"])

    assert result.state == "FAIL"
    assert any(issue.rule_id == "STA018" and issue.severity == "failure" for issue in result.issues)
    assert any(issue.rule_id == "STA018" and issue.severity == "review" for issue in result.issues)


def test_static_positive_patterns_do_not_emit_static_failures(tmp_path, monkeypatch):
    repo = _make_repo(
        tmp_path,
        "def test_valid_request_succeeds():\n"
        "    app.dependency_overrides[dep] = override\n"
        "    app.dependency_overrides.clear()\n"
        "    assert response.status_code == 200\n",
    )
    _write(repo / "backend" / "tests" / "support" / "factories.py", "def make_user():\n    return object()\n")
    _write(repo / "backend" / "tests" / "support" / "api_helpers.py", "def create_user(client):\n    return client.post('/users')\n")
    monkeypatch.chdir(repo)

    result = run_checker(["pages/example/test_api_contract.py"])

    assert not any(issue.rule_id.startswith("STA") and issue.severity in {"failure", "blocker"} for issue in result.issues)


def _write_workflow(repo: Path, body: str) -> None:
    _write(repo / ".github" / "workflows" / "backend.yml", body)


def _valid_workflow() -> str:
    return (
        "name: backend\n"
        "permissions:\n"
        "  contents: read\n"
        "jobs:\n"
        "  tests:\n"
        "    runs-on: ubuntu-latest\n"
        "    services:\n"
        "      postgres:\n"
        "        image: postgres:16\n"
        "    steps:\n"
        "      - run: DATABASE_URL=postgresql://user:pass@localhost/pickup_lane_test_db alembic upgrade head\n"
        "      - run: DATABASE_URL=postgresql://user:pass@localhost/pickup_lane_test_db pytest backend/tests\n"
    )


@pytest.mark.parametrize(
    ("workflow", "rule_id", "expected_state"),
    [
        ("name: backend\npermissions:\n  contents: read\njobs:\n  tests:\n    steps:\n      - run: echo no tests\n", "REP002", "BLOCKED"),
        ("name: backend\npermissions:\n  contents: read\njobs:\n  tests:\n    steps:\n      - run: pytest backend/tests\n      - run: alembic upgrade head\n", "REP003", "BLOCKED"),
        ("name: backend\npermissions:\n  contents: read\njobs:\n  tests:\n    steps:\n      - run: DATABASE_URL=postgresql://x/test_db pytest backend/tests\n", "REP004", "BLOCKED"),
        (_valid_workflow() + "      - run: echo production\n", "REP005", "FAIL"),
        (_valid_workflow() + "      - run: pytest backend/tests -x\n", "REP006", "FAIL"),
        (_valid_workflow().replace("permissions:\n  contents: read\n", ""), "REP007", "BLOCKED"),
        (_valid_workflow() + "      - run: pytest backend/tests > /dev/null\n", "REP008", "PASS"),
        (_valid_workflow() + "      - run: pytest backend/tests -m 'not slow'\n", "REP009", "BLOCKED"),
        (_valid_workflow() + "      - run: pytest backend/tests --reruns 2\n", "REP010", "FAIL"),
    ],
)
def test_repository_rule_diagnostics_for_directory_targets(tmp_path, monkeypatch, workflow, rule_id, expected_state):
    repo = _make_repo(tmp_path, pytest_config="[pytest]\n")
    _write_workflow(repo, workflow)
    monkeypatch.chdir(repo)

    result = run_checker(["pages/example"])

    assert result.state == expected_state
    assert any(issue.rule_id == rule_id for issue in result.issues)


def test_rep001_marker_registration_and_strict_marker_config(tmp_path, monkeypatch):
    repo = _make_repo(
        tmp_path,
        "import pytest\n\n@pytest.mark.slow\ndef test_valid_request_succeeds():\n    assert 1 == 1\n",
        with_ci=True,
        pytest_config="[pytest]\nmarkers =\n    slow: slow tests\n",
    )
    monkeypatch.chdir(repo)

    missing_strict = run_checker(["pages/example"])
    (repo / "pytest.ini").write_text("[pytest]\naddopts = --strict-markers\nmarkers =\n    slow: slow tests\n")
    strict = run_checker(["pages/example"])

    assert missing_strict.state == "FAIL"
    assert any(issue.rule_id == "REP001" for issue in missing_strict.issues)
    assert not any(issue.rule_id == "REP001" and issue.severity in {"failure", "blocker"} for issue in strict.issues)


def test_repository_positive_directory_passes_global_ci_checks(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path, with_ci=True, pytest_config="[pytest]\n")
    monkeypatch.chdir(repo)

    result = run_checker(["pages/example"])

    assert result.state == "PASS"
    assert not any(issue.rule_id.startswith("REP") and issue.severity in {"failure", "blocker"} for issue in result.issues)


def test_checker_report_completion_sections_are_concrete(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path, with_ci=True, pytest_config="[pytest]\n")
    monkeypatch.chdir(repo)

    result = run_checker(["pages/example"])
    report = render_report(result)

    assert "validated through rule results above" not in report
    assert "Sources Reviewed: 1 item(s); ids: spec" in report
    assert "Requirement Coverage: 1 item(s); ids: REQ-01" in report
    assert "Scenario Coverage: " in report
    assert "Ownership Decisions: 1 item(s); ids: test_api_contract.py::test_valid_request_succeeds" in report
    assert "Runtime Evidence: not required; no effects, constraints, or time boundaries declared" in report
    assert "Mutation Status: NOT_REQUESTED" in report
    assert "Mutation Evidence: no mutation targets declared" in report


def test_run001_default_mode_never_starts_runtime_or_mutation_processes(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    monkeypatch.chdir(repo)

    def fail_runtime(*args, **kwargs):
        raise AssertionError("runtime should not run")

    monkeypatch.setattr(checker_module, "run_runtime_validation", fail_runtime)
    monkeypatch.setattr(checker_module, "run_mutations", fail_runtime)

    result = checker_module.run_checker(["pages/example/test_api_contract.py"])

    assert result.state == "PASS"
    assert result.commands_run == ["python check_backend_tests.py pages/example/test_api_contract.py"]
    assert "pytest target with compliance evidence plugin" in result.commands_not_run
    assert "mutmut run for declared mutation targets" in result.commands_not_run


def test_runtime_requirement_positive_when_no_runtime_evidence_declared(tmp_path):
    contract = _contract_for_tmp(tmp_path, {"effects": [], "constraints": [], "time_boundaries": []})

    result = evaluate_runtime_requirement(contract, requested=False)

    assert result.state == "PASS"
    assert not result.issues


def test_run003_runtime_command_is_limited_to_accepted_target(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    target, error = resolve_target(["pages/example/test_api_contract.py"], cwd=repo)
    assert error is None
    contract = _contract_for_tmp(
        tmp_path,
        {
            "effects": [
                {
                    "id": "EFF-01",
                    "phase": "successful_mutation",
                    "kind": "field_equals",
                    "model": "backend.models.User",
                    "lookup": {"by": "field_values", "fields": {"id": 1}},
                    "after": {"expect": "equals", "value": "removed"},
                }
            ],
            "constraints": [],
            "time_boundaries": [],
        },
    )
    calls = []

    def fake_run(command, *, cwd, env):
        calls.append((command, cwd, env))
        evidence_path = Path(env[runtime_module.EVIDENCE_ENV])
        evidence_path.write_text(
            '{"type": "effect", "effect_id": "EFF-01", "kind": "field_equals", "model": "backend.models.User", "expect": "equals", "value": "removed"}\n'
            '{"type": "rollback", "effect_id": "ROLLBACK", "assertion": "passed"}\n'
        )
        return runtime_module.RuntimeProcessResult(returncode=0, stdout="")

    monkeypatch.setattr(runtime_module, "_run_pytest_with_heartbeat", fake_run)

    result = run_runtime_validation(target, contract)

    assert calls
    command = calls[0][0]
    assert str(target.path) in command
    assert str(target.tests_root) not in command
    assert result.state == "PASS"


def test_run003_runtime_pytest_failure_reports_rule_id(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    target, error = resolve_target(["pages/example/test_api_contract.py"], cwd=repo)
    assert error is None
    contract = _contract_for_tmp(
        tmp_path,
        {
            "effects": [
                {
                    "id": "EFF-01",
                    "phase": "successful_mutation",
                    "kind": "field_equals",
                    "after": {"expect": "equals", "value": "removed"},
                }
            ],
            "constraints": [],
            "time_boundaries": [],
        },
    )

    def fake_run(command, *, cwd, env):
        return runtime_module.RuntimeProcessResult(returncode=1, stdout="", stderr="failed")

    monkeypatch.setattr(runtime_module, "_run_pytest_with_heartbeat", fake_run)

    result = run_runtime_validation(target, contract)

    assert result.state == "FAIL"
    assert any(issue.rule_id == "RUN003" for issue in result.issues)


def test_runtime_subprocess_emits_heartbeat_for_quiet_process(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(runtime_module, "RUNTIME_HEARTBEAT_SECONDS", 0)

    result = runtime_module._run_pytest_with_heartbeat(
        [sys.executable, "-c", "import time; time.sleep(0.2); print('done')"],
        cwd=tmp_path,
        env=os.environ.copy(),
    )

    captured = capsys.readouterr()
    assert result.returncode == 0
    assert "done" in result.stdout
    assert "runtime pytest still running" in captured.err


def test_runtime_evidence_positive_with_automatic_isolation_record(tmp_path):
    contract = _contract_for_tmp(
        tmp_path,
        {
            "effects": [
                {
                    "id": "EFF-01",
                    "phase": "successful_mutation",
                    "kind": "field_equals",
                    "model": "backend.models.User",
                    "field": "status",
                    "before": {"equals": "active"},
                    "after": {"in": ["removed", "deleted"]},
                },
                {
                    "id": "EXTERNAL",
                    "phase": "rejected_mutation",
                    "kind": "external_call_count",
                    "after": {"expect": "delta", "delta": 0},
                },
                {
                    "id": "IDEMP",
                    "phase": "idempotency",
                    "kind": "count_delta",
                    "after": {"expect": "delta", "delta": 0},
                },
            ],
            "constraints": [
                {
                    "id": "C1",
                    "expected_database_identifier": "uq_user",
                }
            ],
            "time_boundaries": [
                {
                    "id": "TIME",
                    "boundary_cases": ["before", "equal", "after"],
                }
            ],
        },
    )
    result = CheckResult(target="pages/example", scope="directory")

    _validate_runtime_records(
        contract,
        [
            {
                "type": "effect",
                "effect_id": "EFF-01",
                "kind": "field_equals",
                "model": "backend.models.User",
                "before": {"field": "status", "field_value": "active"},
                "after": {"field": "status", "field_value": "removed"},
                "expect": "in",
                "value": ["removed", "deleted"],
            },
            {"type": "effect", "effect_id": "EXTERNAL", "kind": "external_call_count", "expect": "delta", "delta": 0},
            {"type": "effect", "effect_id": "IDEMP", "kind": "count_delta", "expect": "delta", "delta": 0},
            {"type": "constraint", "constraint_id": "C1", "expected_identifier": "uq_user"},
            {"type": "time_boundary", "time_id": "TIME", "boundary": "before", "baseline": "now"},
            {"type": "time_boundary", "time_id": "TIME", "boundary": "equal", "baseline": "now"},
            {"type": "time_boundary", "time_id": "TIME", "boundary": "after", "baseline": "now"},
            {
                "type": "isolation",
                "isolation_id": "RUN007-DB-ISOLATION",
                "database_name": "pickup_lane_test_db",
                "cleanup_complete": True,
                "assertion": "passed",
            },
        ],
        result,
    )

    assert result.state == "PASS"


@pytest.mark.parametrize(
    ("scoped_data", "records", "rule_id", "expected_state"),
    [
        ({"effects": [{"id": "EFF", "phase": "successful_mutation", "kind": "field_equals", "after": {"expect": "equals", "value": "x"}}], "constraints": [], "time_boundaries": []}, [], "RUN004", "BLOCKED"),
        ({"effects": [{"id": "IDEMP", "phase": "idempotency", "kind": "count_delta", "after": {"expect": "delta", "delta": 0}}], "constraints": [], "time_boundaries": []}, [], "RUN005", "BLOCKED"),
        ({"effects": [], "constraints": [{"id": "C1", "expected_database_identifier": "uq"}], "time_boundaries": []}, [], "RUN006", "BLOCKED"),
        ({"effects": [{"id": "EFF", "phase": "successful_mutation", "kind": "field_equals", "after": {"expect": "equals", "value": "x"}}], "constraints": [], "time_boundaries": []}, [{"type": "effect", "effect_id": "EFF", "kind": "field_equals", "expect": "equals", "value": "x"}], "RUN007", "BLOCKED"),
        ({"effects": [{"id": "EXT", "phase": "rejected_mutation", "kind": "external_call_count", "after": {"expect": "delta", "delta": 0}}], "constraints": [], "time_boundaries": []}, [], "RUN008", "BLOCKED"),
        ({"effects": [], "constraints": [], "time_boundaries": [{"id": "TIME", "boundary_cases": ["before", "equal"]}]}, [{"type": "time_boundary", "time_id": "TIME", "boundary": "before", "baseline": "now"}, {"type": "rollback", "effect_id": "ROLLBACK", "assertion": "passed"}], "RUN009", "BLOCKED"),
        ({"effects": [], "constraints": [], "time_boundaries": [{"id": "TIME", "boundary_cases": ["before"]}]}, [{"type": "time_boundary", "time_id": "TIME", "boundary": "before"}, {"type": "rollback", "effect_id": "ROLLBACK", "assertion": "passed"}], "RUN010", "BLOCKED"),
    ],
)
def test_runtime_rule_blockers_by_id(tmp_path, scoped_data, records, rule_id, expected_state):
    contract = _contract_for_tmp(tmp_path, scoped_data)
    result = CheckResult(target="pages/example", scope="directory")

    _validate_runtime_records(contract, records, result)

    assert result.state == expected_state
    assert any(issue.rule_id == rule_id for issue in result.issues)


def _mutation_contract(tmp_path: Path, *, extra_target: dict | None = None) -> Contract:
    target = {
        "id": "MUT-TARGET",
        "source_id": "spec",
        "module": "backend.services.example",
        "test_refs": ["test_api_contract.py::test_valid_request_succeeds"],
    }
    if extra_target:
        target.update(extra_target)
    return _contract_for_tmp(tmp_path, {"mutation_targets": [target]})


def test_mutation_requirement_positive_without_declared_targets(tmp_path):
    contract = _contract_for_tmp(tmp_path, {"mutation_targets": []})

    result = evaluate_mutation_requirement(contract, runtime_requested=False, mutation_requested=False)

    assert result.state == "PASS"
    assert result.completion["Mutation Status"] == "NOT_REQUESTED"


def test_mut003_rejects_unsupported_mutation_metadata(tmp_path):
    contract = _mutation_contract(tmp_path, extra_target={"line_ranges": [[1, 3]]})

    result = evaluate_mutation_requirement(contract, runtime_requested=True, mutation_requested=True)

    assert result.state == "FAIL"
    assert any(issue.rule_id == "MUT003" for issue in result.issues)


def test_mut003_blocks_missing_symbol_scope_before_mutmut_body(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    _write(repo / "backend" / "services" / "example.py", "def value():\n    return 1\n")
    _write(repo / "pyproject.toml", "[tool.mutmut]\ntimeout_factor = 2\n")
    _write(repo / "backend" / ".mutmut-cache", "stale cache")
    target, error = resolve_target(["pages/example/test_api_contract.py"], cwd=repo)
    assert error is None
    contract = _mutation_contract(tmp_path, extra_target={"symbols": ["missing"]})
    contract.data["review_flags"] = [{"id": "NETWORK", "kind": "network_blocking", "status": "confirmed"}]

    def fake_run(command, **kwargs):
        if command[:3] == [sys.executable, "-m", "mutmut"]:
            return SimpleNamespace(returncode=0, stdout="mutmut 2.4.0", stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(mutations_module.subprocess, "run", fake_run)
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/pickup_lane_test_db")

    result = run_mutation_preflight(target, contract)

    assert result.state == "PASS"
    assert any(issue.rule_id == "MUT003" for issue in result.issues)
    assert result.completion["Mutation Status"] == "UNSUPPORTED"


def test_mutation_preflight_safety_blockers_do_not_run_mutmut_body(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    _write(repo / "backend" / "services" / "example.py", "def value():\n    return 1\n")
    target, error = resolve_target(["pages/example/test_api_contract.py"], cwd=repo)
    assert error is None
    contract = _mutation_contract(tmp_path)

    def fake_run(command, **kwargs):
        if command[:3] == [sys.executable, "-m", "mutmut"]:
            return SimpleNamespace(returncode=0, stdout="mutmut 2.4.0", stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(mutations_module.subprocess, "run", fake_run)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    result = run_mutation_preflight(target, contract)

    assert result.state == "PASS"
    assert any(issue.rule_id == "MUT005" for issue in result.issues)
    assert any(issue.rule_id == "MUT006" for issue in result.issues)
    assert result.completion["Mutation Status"] == "DEFERRED"


def test_mut004_surviving_mutation_is_failure(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    _write(repo / "backend" / "services" / "example.py", "def value():\n    return 1\n")
    _write(repo / "pyproject.toml", "[tool.mutmut]\ntimeout_factor = 2\n")
    target, error = resolve_target(["pages/example/test_api_contract.py"], cwd=repo)
    assert error is None
    contract = _mutation_contract(tmp_path)
    contract.data["review_flags"] = [{"id": "NETWORK", "kind": "network_blocking", "status": "confirmed"}]
    calls = []

    def fake_run(command, **kwargs):
        if command[:3] == [sys.executable, "-m", "mutmut"] and "--version" in command:
            return SimpleNamespace(returncode=0, stdout="mutmut 2.4.0", stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    def fake_mutmut(command, *, cwd, env, label):
        calls.append((command, {"cwd": cwd, "env": env, "label": label}))
        return mutations_module.ProcessResult(returncode=1, stdout="survived")

    monkeypatch.setattr(mutations_module.subprocess, "run", fake_run)
    monkeypatch.setattr(mutations_module, "_run_command_with_heartbeat", fake_mutmut)
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/pickup_lane_test_db")

    result = run_mutations(target, contract)

    assert result.state == "PASS"
    assert any(issue.rule_id == "MUT004" for issue in result.issues)
    assert result.completion["Mutation Status"] == "FAILED"


def test_mut005_timeout_defers_optional_mutation_hardening(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    _write(repo / "backend" / "services" / "example.py", "def value():\n    return 1\n")
    _write(repo / "pyproject.toml", "[tool.mutmut]\ntimeout_factor = 2\n")
    _write(repo / "backend" / ".mutmut-cache", "stale cache")
    target, error = resolve_target(["pages/example/test_api_contract.py"], cwd=repo)
    assert error is None
    contract = _mutation_contract(tmp_path)
    contract.data["review_flags"] = [{"id": "NETWORK", "kind": "network_blocking", "status": "confirmed"}]

    def fake_run(command, **kwargs):
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    def fake_mutmut(command, *, cwd, env, label):
        return mutations_module.ProcessResult(
            returncode=124,
            stdout="",
            timed_out=True,
            timeout_kind="baseline",
        )

    monkeypatch.setattr(mutations_module.subprocess, "run", fake_run)
    monkeypatch.setattr(mutations_module, "_run_command_with_heartbeat", fake_mutmut)
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/pickup_lane_test_db")

    result = run_mutations(target, contract)

    assert result.state == "PASS"
    assert any(issue.rule_id == "MUT005" for issue in result.issues)
    assert result.completion["Mutation Status"] == "DEFERRED"


def test_mutation_positive_path_is_module_level_and_uses_targeted_runner(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    _write(repo / "backend" / "services" / "example.py", "def value():\n    return 1\n")
    _write(repo / "pyproject.toml", "[tool.mutmut]\ntimeout_factor = 2\n")
    _write(repo / "backend" / ".mutmut-cache", "stale cache")
    target, error = resolve_target(["pages/example/test_api_contract.py"], cwd=repo)
    assert error is None
    contract = _mutation_contract(tmp_path)
    contract.data["review_flags"] = [{"id": "NETWORK", "kind": "network_blocking", "status": "confirmed"}]
    calls = []

    def fake_run(command, **kwargs):
        if command[:3] == [sys.executable, "-m", "mutmut"] and "--version" in command:
            return SimpleNamespace(returncode=0, stdout="mutmut 2.4.0", stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    def fake_mutmut(command, *, cwd, env, label):
        calls.append((command, {"cwd": cwd, "env": env, "label": label}))
        return mutations_module.ProcessResult(returncode=0, stdout="")

    monkeypatch.setattr(mutations_module.subprocess, "run", fake_run)
    monkeypatch.setattr(mutations_module, "_run_command_with_heartbeat", fake_mutmut)
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/pickup_lane_test_db")

    result = run_mutations(target, contract)

    assert result.state == "PASS"
    assert result.completion["Mutation Status"] == "PASSED"
    run_command, run_kwargs = next(
        (command, kwargs)
        for command, kwargs in calls
        if command[:4] == [sys.executable, "-m", "mutmut", "run"]
    )
    assert "--paths-to-mutate" in run_command
    assert "symbols" not in " ".join(run_command)
    assert str(target.contract_dir / "test_api_contract.py") in " ".join(run_command)
    assert run_kwargs["cwd"] == repo / "backend"
    assert not (repo / "backend" / ".mutmut-cache").exists()


def test_mutation_symbol_scope_uses_mutmut_patch_file(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    _write(
        repo / "backend" / "services" / "example.py",
        "MY_VALUE = 40\n\n"
        "def value():\n"
        "    return MY_VALUE\n\n"
        "def unrelated():\n"
        "    return 2\n",
    )
    _write(repo / "pyproject.toml", "[tool.mutmut]\ntimeout_factor = 2\n")
    target, error = resolve_target(["pages/example/test_api_contract.py"], cwd=repo)
    assert error is None
    contract = _mutation_contract(tmp_path, extra_target={"symbols": ["MY_VALUE", "value"]})
    contract.data["review_flags"] = [{"id": "NETWORK", "kind": "network_blocking", "status": "confirmed"}]
    calls = []

    def fake_run(command, **kwargs):
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    def fake_mutmut(command, *, cwd, env, label):
        calls.append((command, {"cwd": cwd, "env": env, "label": label}))
        return mutations_module.ProcessResult(returncode=0, stdout="")

    monkeypatch.setattr(mutations_module.subprocess, "run", fake_run)
    monkeypatch.setattr(mutations_module, "_run_command_with_heartbeat", fake_mutmut)
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/pickup_lane_test_db")

    result = run_mutations(target, contract)

    assert result.state == "PASS"
    run_command, _run_kwargs = next(
        (command, kwargs)
        for command, kwargs in calls
        if command[:4] == [sys.executable, "-m", "mutmut", "run"]
    )
    assert "--use-patch-file" in run_command
    patch_path = Path(run_command[run_command.index("--use-patch-file") + 1])
    patch_text = patch_path.read_text()
    assert f"+++ {repo / 'backend' / 'services' / 'example.py'}" in patch_text
    assert "@@ -0,0 +1,1 @@" in patch_text
    assert "@@ -0,0 +3,2 @@" in patch_text
    assert "@@ -0,0 +6,2 @@" not in patch_text


def test_report_rules_are_observable_for_file_and_directory_results():
    file_result = CheckResult(target="pages/example/test_file.py", scope="file")
    file_result.add_issue("STA005", "review", "review finding", "test_file.py::test_name")
    file_result.commands_run.extend(["static analysis", "static analysis"])
    file_result.commands_not_run.extend(["pytest", "pytest"])
    file_result.completion.update(
        {
            "Sources Reviewed": "2 item(s); ids: spec, route",
            "Requirement Coverage": "3 item(s); ids: REQ-1, REQ-2, REQ-3; statuses: covered=2, missing=1",
            "Enum And State Matrix": "1 matrix/matrices, 2 classified value(s); ids: STATE",
            "Scenario Coverage": "4 item(s); ids: SCN-1, SCN-2, SCN-3, SCN-4; applicability: required=2, not_relevant=2",
            "Ownership Decisions": "1 item(s); ids: test_file.py::test_name",
            "Assertion Review": "1 effect(s): EFF-1; 0 constraint(s): none",
            "Time Control": "1 item(s); ids: TIME-1",
            "Remaining Gaps": "1 item(s); ids: GAP-1; statuses: open=1",
            "Conflicts": "1 item(s); ids: CONFLICT-1; statuses: resolved=1",
            "Runtime Evidence": "required but not run; declared ids: TIME-1",
            "Mutation Status": "NOT_REQUESTED",
            "Mutation Evidence": "no mutation targets declared",
            "Verification": "static and contract checker run only",
        }
    )
    file_report = render_report(file_result)

    directory_result = CheckResult(target="pages/example", scope="directory")
    directory_result.add_issue("CON017", "blocker", "open gap")
    directory_report = render_report(directory_result)

    passing_directory = CheckResult(target="pages/example", scope="directory")
    passing_report = render_report(passing_directory)

    assert "Target: pages/example/test_file.py" in file_report
    assert "Scope: file" in file_report
    assert "Result: PASS" in file_report
    assert "Exit code: 0" in file_report
    assert "STA005 [test_file.py::test_name]" in file_report
    assert "File-level compliance only" in file_report
    assert "Sources Reviewed" in file_report
    assert "Commands run:\n- static analysis" in file_report
    assert "Commands not run:\n- pytest" in file_report
    assert "Requirement Coverage: 3 item(s); ids: REQ-1, REQ-2, REQ-3" in file_report
    assert "Review Findings: 1 finding(s); rule ids: STA005" in file_report
    assert file_report.count("- static analysis") == 1
    assert file_report.count("- pytest") == 1
    assert "not certified by a single-file check" in file_report
    assert "Result: BLOCKED" in directory_report
    assert "Feature/domain completion is not certified" in directory_report
    assert "Feature/domain completion is certified" in passing_report


def test_result_precedence_order_is_observable():
    usage = CheckResult(target="bad", scope=None, forced_state="USAGE_ERROR")
    usage.add_issue("TGT001", "failure", "usage")
    internal = CheckResult(target="bad", scope=None, forced_state="INTERNAL_ERROR")
    internal.add_issue("INTERNAL", "failure", "bug")
    failure = CheckResult(target="bad", scope=None)
    failure.add_issue("CON001", "failure", "fail")
    blocked = CheckResult(target="bad", scope=None)
    blocked.add_issue("RUN002", "blocker", "blocked")
    passing = CheckResult(target="ok", scope="file")

    assert usage.state == "USAGE_ERROR"
    assert usage.exit_code == 3
    assert internal.state == "INTERNAL_ERROR"
    assert internal.exit_code == 4
    assert failure.state == "FAIL"
    assert failure.exit_code == 1
    assert blocked.state == "BLOCKED"
    assert blocked.exit_code == 2
    assert passing.state == "PASS"
    assert passing.exit_code == 0


APPROVED_RULE_TEST_MATRIX = {
    # Targeting
    "TGT001": ("resolve_target", "enforced", "test_file_level_repo_findings_do_not_fail_local_file", "test_tgt001_rejects_missing_and_multiple_targets", "TGT001", "USAGE_ERROR", 3, "exact target count only"),
    "TGT002": ("targeting.resolve_target", "enforced", "test_file_level_repo_findings_do_not_fail_local_file", "test_tgt002_rejects_target_outside_backend_tests", "TGT002", "USAGE_ERROR", 3, "symlink edge cases are normalized by Path.resolve"),
    "TGT003": ("targeting.resolve_target", "enforced", "test_file_level_repo_findings_do_not_fail_local_file", "test_rejects_dot_as_broad_target", "TGT003", "USAGE_ERROR", 3, "denylist is explicit"),
    "TGT004": ("targeting.resolve_target", "enforced", "test_file_level_repo_findings_do_not_fail_local_file", "test_tgt004_rejects_non_leaf_directory", "TGT004", "USAGE_ERROR", 3, "leaf means no child directories"),
    "TGT005": ("targeting.resolve_target", "enforced", "test_file_level_repo_findings_do_not_fail_local_file", "test_tgt005_rejects_support_targets", "TGT005", "USAGE_ERROR", 3, "path-part based"),
    "TGT006": ("targeting.resolve_target", "enforced", "test_file_level_repo_findings_do_not_fail_local_file", "test_tgt006_rejects_conftest_target", "TGT006", "USAGE_ERROR", 3, "filename based"),
    "TGT007": ("targeting.resolve_target", "enforced", "test_file_level_repo_findings_do_not_fail_local_file", "test_tgt007_rejects_empty_leaf_without_contract", "TGT007", "USAGE_ERROR", 3, "contract-only leaf accepted"),
    "TGT008": ("targeting.resolve_target", "enforced", "test_tgt008_rejects_broad_legacy_and_accepts_legacy_leaf_file", "test_tgt008_rejects_broad_legacy_and_accepts_legacy_leaf_file", "TGT008", "USAGE_ERROR", 3, "exact legacy leaf/file allowed"),
    # Contract
    "CON001": ("contracts.load_contract", "enforced", "test_file_level_repo_findings_do_not_fail_local_file", "test_con001_missing_contract_reports_contract_path", "CON001", "FAIL", 1, "requires per-leaf contract"),
    "CON002": ("contracts._parse_literal_contract", "enforced", "test_file_level_repo_findings_do_not_fail_local_file", "test_con002_rejects_nonliteral_contract_expressions", "CON002", "FAIL", 1, "literal_eval based"),
    "CON003": ("contracts._validate_schema", "enforced", "test_file_level_repo_findings_do_not_fail_local_file", "test_contract_rule_failures_are_reported_by_id", "CON003", "FAIL", 1, "schema v1 only"),
    "CON004": ("contracts._validate_schema", "enforced", "test_file_level_repo_findings_do_not_fail_local_file", "test_contract_rule_failures_are_reported_by_id", "CON004", "FAIL", 1, "source summary depth remains semantic"),
    "CON005": ("contracts._validate_schema", "enforced", "test_directory_level_blockers_for_gaps_conflicts_review_runtime_and_mutation", "test_contract_rule_failures_are_reported_by_id", "CON005", "BLOCKED", 2, "unlisted conflicts cannot be discovered"),
    "CON006": ("contracts._validate_requirements", "enforced", "test_file_level_repo_findings_do_not_fail_local_file", "test_contract_rule_failures_are_reported_by_id", "CON006", "BLOCKED", 2, "requirement completeness is contract declared"),
    "CON007": ("contracts._validate_requirements", "enforced", "test_file_level_repo_findings_do_not_fail_local_file", "test_contract_rule_failures_are_reported_by_id", "CON007", "FAIL", 1, "reason quality is semantic"),
    "CON008": ("contracts._validate_refs", "enforced", "test_file_level_repo_findings_do_not_fail_local_file", "test_contract_rule_failures_are_reported_by_id", "CON008", "FAIL", 1, "dynamic tests unsupported"),
    "CON009": ("contracts._validate_state_matrices", "enforced", "test_con009_state_matrix_positive_and_manual_confirmed", "test_state_matrix_uses_extracted_enum_values", "CON009", "FAIL", 1, "dynamic sources need manual review"),
    "CON010": ("contracts._validate_scenarios", "enforced", "test_repository_positive_directory_passes_global_ci_checks", "test_contract_rule_failures_are_reported_by_id", "CON010", "FAIL", 1, "single-file scenario completeness is scoped"),
    "CON011": ("contracts._validate_ownership", "enforced", "test_file_level_repo_findings_do_not_fail_local_file", "test_contract_rule_failures_are_reported_by_id", "CON011", "BLOCKED", 2, "ownership rationale quality is semantic"),
    "CON012": ("contracts._validate_effects", "enforced", "test_structured_effect_requires_runtime_evidence_by_default", "test_contract_rule_failures_are_reported_by_id", "CON012", "BLOCKED", 2, "mutation detection itself is partly semantic"),
    "CON013": ("contracts._validate_effects", "enforced", "test_structured_effect_requires_runtime_evidence_by_default", "test_con013_and_con014_structured_effect_validation", "CON013", "FAIL", 1, "side-effect inventory completeness is semantic"),
    "CON014": ("contracts._validate_effects", "enforced", "test_structured_effect_requires_runtime_evidence_by_default", "test_con013_and_con014_structured_effect_validation", "CON014", "FAIL", 1, "idempotency relevance is semantic"),
    "CON015": ("contracts._validate_constraints", "enforced", "test_con015_constraint_source_can_be_extracted", "test_contract_rule_failures_are_reported_by_id", "CON015", "BLOCKED", 2, "complex migrations may need review"),
    "CON016": ("contracts._validate_time_boundaries", "enforced", "test_runtime_evidence_positive_with_automatic_isolation_record", "test_contract_rule_failures_are_reported_by_id", "CON016", "BLOCKED", 2, "time relevance is semantic"),
    "CON017": ("contracts._validate_gaps", "enforced", "test_repository_positive_directory_passes_global_ci_checks", "test_directory_level_blockers_for_gaps_conflicts_review_runtime_and_mutation", "CON017", "BLOCKED", 2, "file checks do not certify feature gaps"),
    "CON018": ("contracts._validate_review_flags", "enforced", "test_con009_state_matrix_positive_and_manual_confirmed", "test_directory_level_blockers_for_gaps_conflicts_review_runtime_and_mutation", "CON018", "BLOCKED", 2, "confirmed flags are human evidence"),
}

APPROVED_RULE_TEST_MATRIX.update(
    {
        "STA001": ("static_analysis.collect_tests", "enforced", "test_static_positive_patterns_do_not_emit_static_failures", "test_static_rule_diagnostics_by_id", "STA001", "FAIL", 1, "AST parse only"),
        "STA002": ("static_analysis._check_test_name", "enforced", "test_static_positive_patterns_do_not_emit_static_failures", "test_static_rule_diagnostics_by_id", "STA002", "FAIL", 1, "exact banned list"),
        "STA003": ("static_analysis._check_imports", "enforced/review-only", "test_static_positive_patterns_do_not_emit_static_failures", "test_conftest_fixture_import_fails_and_utility_import_is_review", "STA003", "FAIL", 1, "fixture detection is static best effort"),
        "STA004": ("static_analysis._check_imports", "enforced/review-only", "test_static_positive_patterns_do_not_emit_static_failures", "test_static_rule_diagnostics_by_id", "STA004", "FAIL", 1, "legacy imports are review findings"),
        "STA005": ("static_analysis._check_assertions", "review-only", "test_static_positive_patterns_do_not_emit_static_failures", "test_sta005_mutation_status_only_is_review_not_failure", "STA005", "PASS", 0, "name heuristic"),
        "STA006": ("static_analysis._check_assertions", "enforced", "test_static_positive_patterns_do_not_emit_static_failures", "test_static_rule_diagnostics_by_id", "STA006", "FAIL", 1, "only exact weak patterns"),
        "STA007": ("static_analysis._check_exceptions", "enforced", "test_con015_constraint_source_can_be_extracted", "test_sta007_generic_integrity_error_constraint_failure", "STA007", "FAIL", 1, "requires declared constraint test"),
        "STA008": ("static_analysis._check_exceptions", "enforced/review-only", "test_broad_exception_can_be_review_mapped", "test_static_rule_diagnostics_by_id", "STA008", "FAIL", 1, "mapped broad-exception behavior is review"),
        "STA009": ("static_analysis._check_time_calls", "enforced", "test_runtime_evidence_positive_with_automatic_isolation_record", "test_static_rule_diagnostics_by_id", "STA009", "FAIL", 1, "helper-hidden time calls can be missed"),
        "STA010": ("static_analysis._check_time_calls", "review-only", "test_static_positive_patterns_do_not_emit_static_failures", "test_sta010_fixed_future_timestamp_is_review", "STA010", "PASS", 0, "future-date heuristic"),
        "STA011": ("static_analysis._check_mocks_and_network", "enforced/review-only", "test_static_positive_patterns_do_not_emit_static_failures", "test_static_rule_diagnostics_by_id", "STA011", "FAIL", 1, "known direct calls only"),
        "STA012": ("static_analysis._check_dependency_overrides", "enforced", "test_static_positive_patterns_do_not_emit_static_failures", "test_static_rule_diagnostics_by_id", "STA012", "FAIL", 1, "reset in another fixture can be missed"),
        "STA013": ("static_analysis._check_mocks_and_network", "contract-justified", "test_broad_exception_can_be_review_mapped", "test_static_rule_diagnostics_by_id", "STA013", "BLOCKED", 2, "mock boundary correctness is semantic"),
        "STA014": ("static_analysis._check_markers", "review-only", "test_static_positive_patterns_do_not_emit_static_failures", "test_custom_marker_is_reported_as_static_review_finding", "STA014", "PASS", 0, "registration enforced by REP001"),
        "STA015": ("static_analysis._check_parametrize", "review-only", "test_static_positive_patterns_do_not_emit_static_failures", "test_sta015_parametrize_review_and_confirmed_positive", "STA015", "PASS", 0, "same-shape semantics need review"),
        "STA016": ("static_analysis._check_fixtures", "contract-justified", "test_static_positive_patterns_do_not_emit_static_failures", "test_static_rule_diagnostics_by_id", "STA016", "BLOCKED", 2, "fixture necessity is semantic"),
        "STA017": ("static_analysis._check_support_helper_modules", "enforced", "test_static_positive_patterns_do_not_emit_static_failures", "test_support_factory_assertion_fails_static_scan", "STA017", "FAIL", 1, "helper indirection can hide behavior"),
        "STA018": ("static_analysis._check_support_helper_modules", "enforced/review-only", "test_static_positive_patterns_do_not_emit_static_failures", "test_sta018_api_helper_factory_name_and_assertion_review", "STA018", "FAIL", 1, "assertion intent remains review"),
        "STA019": ("static_analysis._check_module_state", "review-only", "test_static_positive_patterns_do_not_emit_static_failures", "test_static_rule_diagnostics_by_id", "STA019", "PASS", 0, "mutable-state heuristic"),
        "STA020": ("static_analysis._check_markers", "enforced", "test_static_positive_patterns_do_not_emit_static_failures", "test_static_rule_diagnostics_by_id", "STA020", "FAIL", 1, "dynamic marks can be missed"),
        "REP001": ("repository.analyze_repository", "enforced", "test_rep001_marker_registration_and_strict_marker_config", "test_rep001_marker_registration_and_strict_marker_config", "REP001", "FAIL", 1, "only when markers are statically seen"),
        "REP002": ("repository.analyze_repository", "enforced/file-review", "test_repository_positive_directory_passes_global_ci_checks", "test_repository_rule_diagnostics_for_directory_targets", "REP002", "BLOCKED", 2, "GitHub workflow text only"),
        "REP003": ("repository.analyze_repository", "enforced/file-review", "test_repository_positive_directory_passes_global_ci_checks", "test_repository_rule_diagnostics_for_directory_targets", "REP003", "BLOCKED", 2, "DB isolation inferred from text"),
        "REP004": ("repository.analyze_repository", "enforced/file-review", "test_repository_positive_directory_passes_global_ci_checks", "test_repository_rule_diagnostics_for_directory_targets", "REP004", "BLOCKED", 2, "script-hidden migrations can be missed"),
        "REP005": ("repository.analyze_repository", "enforced/file-review", "test_repository_positive_directory_passes_global_ci_checks", "test_repository_rule_diagnostics_for_directory_targets", "REP005", "FAIL", 1, "production-name heuristic"),
        "REP006": ("repository.analyze_repository", "enforced/file-review", "test_repository_positive_directory_passes_global_ci_checks", "test_repository_rule_diagnostics_for_directory_targets", "REP006", "FAIL", 1, "simple CLI pattern detection"),
        "REP007": ("repository.analyze_repository", "enforced/file-review", "test_repository_positive_directory_passes_global_ci_checks", "test_repository_rule_diagnostics_for_directory_targets", "REP007", "BLOCKED", 2, "least privilege is text based"),
        "REP008": ("repository.analyze_repository", "review-only", "test_repository_positive_directory_passes_global_ci_checks", "test_repository_rule_diagnostics_for_directory_targets", "REP008", "PASS", 0, "suppressed-output heuristic"),
        "REP009": ("repository.analyze_repository", "enforced/file-review", "test_repository_positive_directory_passes_global_ci_checks", "test_repository_rule_diagnostics_for_directory_targets", "REP009", "BLOCKED", 2, "script expansion can hide exclusions"),
        "REP010": ("repository.analyze_repository", "enforced/file-review", "test_repository_positive_directory_passes_global_ci_checks", "test_repository_rule_diagnostics_for_directory_targets", "REP010", "FAIL", 1, "diagnostic text exception is heuristic"),
        "RUN001": ("check_backend_tests.run_checker", "structural", "test_run001_default_mode_never_starts_runtime_or_mutation_processes", "test_run001_default_mode_never_starts_runtime_or_mutation_processes", "none", "PASS", 0, "tested by monkeypatch boundary"),
        "RUN002": ("runtime.evaluate_runtime_requirement", "enforced", "test_runtime_requirement_positive_when_no_runtime_evidence_declared", "test_structured_effect_requires_runtime_evidence_by_default", "RUN002", "BLOCKED", 2, "runtime is opt-in"),
        "RUN003": ("runtime.run_runtime_validation", "enforced", "test_run003_runtime_command_is_limited_to_accepted_target", "test_run003_runtime_pytest_failure_reports_rule_id", "RUN003", "FAIL", 1, "subprocess boundary mocked in tests"),
        "RUN004": ("runtime._validate_runtime_records", "enforced", "test_runtime_evidence_positive_with_automatic_isolation_record", "test_runtime_evidence_must_match_contract_details", "RUN004", "FAIL", 1, "only declared effects checked"),
        "RUN005": ("runtime._validate_runtime_records", "enforced", "test_runtime_evidence_positive_with_automatic_isolation_record", "test_runtime_rule_blockers_by_id", "RUN005", "BLOCKED", 2, "idempotency inventory is semantic"),
        "RUN006": ("runtime._validate_runtime_records", "enforced", "test_runtime_evidence_positive_with_automatic_isolation_record", "test_runtime_rule_blockers_by_id", "RUN006", "BLOCKED", 2, "driver identifiers vary"),
        "RUN007": ("runtime._validate_runtime_records", "enforced", "test_runtime_evidence_positive_with_automatic_isolation_record", "test_runtime_rule_blockers_by_id", "RUN007", "BLOCKED", 2, "automatic cleanup evidence or rollback evidence is required"),
        "RUN008": ("runtime._validate_runtime_records", "enforced", "test_runtime_evidence_positive_with_automatic_isolation_record", "test_runtime_rule_blockers_by_id", "RUN008", "BLOCKED", 2, "mock call counts only"),
        "RUN009": ("runtime._validate_runtime_records", "enforced", "test_runtime_evidence_positive_with_automatic_isolation_record", "test_runtime_rule_blockers_by_id", "RUN009", "BLOCKED", 2, "boundary names are contract declared"),
        "RUN010": ("runtime._validate_runtime_records", "enforced", "test_runtime_evidence_positive_with_automatic_isolation_record", "test_runtime_rule_blockers_by_id", "RUN010", "BLOCKED", 2, "baseline presence, not clock correctness"),
        "MUT001": ("check_backend_tests._parse_args", "enforced", "test_mutation_requirement_positive_without_declared_targets", "test_mutations_without_runtime_is_usage_error", "MUT001", "USAGE_ERROR", 3, "CLI only"),
        "MUT002": ("mutations.evaluate_mutation_requirement", "optional-status", "test_mutation_requirement_positive_without_declared_targets", "test_mutation_preflight_safety_blockers_do_not_run_mutmut_body", "MUT002", "PASS", 0, "mutation absence no longer blocks feature completion"),
        "MUT003": ("mutations.evaluate_mutation_requirement/_preflight", "enforced", "test_mutation_symbol_scope_uses_mutmut_patch_file", "test_mut003_rejects_unsupported_mutation_metadata", "MUT003", "FAIL", 1, "module plus optional AST symbol scope"),
        "MUT004": ("mutations.run_mutations", "optional-status", "test_mutation_positive_path_is_module_level_and_uses_targeted_runner", "test_mut004_surviving_mutation_is_failure", "MUT004", "PASS", 0, "survivors report Mutation Status FAILED"),
        "MUT005": ("mutations._preflight/run_mutations", "optional-status", "test_mutation_positive_path_is_module_level_and_uses_targeted_runner", "test_mut005_timeout_defers_optional_mutation_hardening", "MUT005", "PASS", 0, "timeout reports Mutation Status DEFERRED"),
        "MUT006": ("mutations._preflight", "optional-status", "test_mutation_positive_path_is_module_level_and_uses_targeted_runner", "test_mutation_preflight_safety_blockers_do_not_run_mutmut_body", "MUT006", "PASS", 0, "unsafe DB or missing network blocking defers optional mutation hardening"),
        "RPT001": ("report.render_report", "structural", "test_report_rules_are_observable_for_file_and_directory_results", "test_report_rules_are_observable_for_file_and_directory_results", "none", "PASS", 0, "format test"),
        "RPT002": ("report.render_report", "structural", "test_report_rules_are_observable_for_file_and_directory_results", "test_report_rules_are_observable_for_file_and_directory_results", "none", "PASS", 0, "grouping by severity"),
        "RPT003": ("report.render_report", "structural", "test_report_rules_are_observable_for_file_and_directory_results", "test_report_rules_are_observable_for_file_and_directory_results", "none", "PASS", 0, "directory wording"),
        "RPT004": ("report.render_report", "structural", "test_report_rules_are_observable_for_file_and_directory_results", "test_report_rules_are_observable_for_file_and_directory_results", "none", "PASS", 0, "file wording"),
        "RPT005": ("report.render_report", "structural", "test_report_rules_are_observable_for_file_and_directory_results", "test_report_rules_are_observable_for_file_and_directory_results", "none", "PASS", 0, "section presence, not semantic completeness"),
        "RPT006": ("report.render_report", "structural", "test_report_rules_are_observable_for_file_and_directory_results", "test_report_rules_are_observable_for_file_and_directory_results", "none", "PASS", 0, "command lists"),
        "RPT007": ("report.render_report", "structural", "test_report_rules_are_observable_for_file_and_directory_results", "test_report_rules_are_observable_for_file_and_directory_results", "none", "PASS", 0, "no completion certification with blockers"),
    }
)


def test_rule_matrix_contains_all_approved_ids():
    expected = {
        *(f"TGT{index:03d}" for index in range(1, 9)),
        *(f"CON{index:03d}" for index in range(1, 19)),
        *(f"STA{index:03d}" for index in range(1, 21)),
        *(f"REP{index:03d}" for index in range(1, 11)),
        *(f"RUN{index:03d}" for index in range(1, 11)),
        *(f"MUT{index:03d}" for index in range(1, 7)),
        *(f"RPT{index:03d}" for index in range(1, 8)),
    }
    missing = expected - set(APPROVED_RULE_TEST_MATRIX)
    assert not missing


def test_rule_matrix_references_existing_synthetic_tests_and_valid_states():
    valid_statuses = {"enforced", "review-only", "structural", "unsupported", "contract-justified", "enforced/review-only", "enforced/file-review", "optional-status"}
    valid_states = {"PASS", "FAIL", "BLOCKED", "USAGE_ERROR", "INTERNAL_ERROR"}
    valid_exit_codes = {0, 1, 2, 3, 4}
    test_names = {name for name in globals() if name.startswith("test_")}

    for rule_id, row in APPROVED_RULE_TEST_MATRIX.items():
        implementation, status, positive, negative, diagnostic, state, exit_code, limitation = row
        assert implementation
        assert status in valid_statuses, rule_id
        assert positive in test_names, rule_id
        assert negative in test_names, rule_id
        assert diagnostic == "none" or diagnostic == rule_id
        assert state in valid_states
        assert exit_code in valid_exit_codes
        assert limitation
