from __future__ import annotations

import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_backend_tests import run_checker, render_report
from support.traceability import validate_traceability_manifest_text


pytestmark = pytest.mark.no_db_cleanup


VALID_SETUP_CFG = """\
[tool:pytest]
addopts =
    --strict-markers
norecursedirs =
    legacy
markers =
    db: uses the dedicated PostgreSQL backend test database
    concurrency: exercises deterministic concurrent or race-sensitive behavior
    migration: validates Alembic or schema migration behavior
    provider_integration: uses an approved provider sandbox, emulator, or test-resource boundary
    slow: intentionally slower than ordinary focused backend tests
    no_db_cleanup: marks backend harness tests that must not open or clean the application database
"""

VALID_MANIFEST = """\
schema_version: 1
domain: games
authoritative_sources:
  - docs/agent-notes/game-details.md
behaviors:
  - id: GAMES-001
    summary: Authenticated eligible users can join an open game.
    source: docs/agent-notes/game-details.md
test_refs:
  - backend/tests/games/test_api_join.py::test_eligible_user_can_join_open_game
known_gaps:
  - Provider sandbox checkout remains deferred to WS05.
external_boundaries:
  - Stripe is mocked at the application-owned boundary in the standard suite.
"""


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def _make_repo(tmp_path: Path, *, setup_cfg: str = VALID_SETUP_CFG) -> Path:
    repo = tmp_path / "repo"
    _write(repo / "backend" / "setup.cfg", setup_cfg)
    _write(repo / "backend" / "tests" / "__init__.py", "")
    return repo


def _write_test(repo: Path, relative: str, text: str) -> None:
    _write(repo / "backend" / "tests" / relative, text)


def test_mechanical_checker_passes_domain_first_traceability_without_contract(tmp_path):
    repo = _make_repo(tmp_path)
    _write_test(
        repo,
        "games/test_api_join.py",
        "import pytest\n\npytestmark = pytest.mark.db\n\n"
        "def test_eligible_user_can_join_open_game():\n"
        "    assert True\n",
    )
    _write(repo / "backend" / "tests" / "games" / "TESTING.md", "# Games Backend Testing\n")
    _write(repo / "backend" / "tests" / "games" / "testing_manifest.yaml", VALID_MANIFEST)

    result = run_checker([], cwd=repo)

    assert result.state == "PASS"
    assert not any(issue.rule_id.startswith("CON") for issue in result.issues)


def test_checker_rejects_removed_runtime_and_mutation_modes(tmp_path):
    repo = _make_repo(tmp_path)

    runtime = run_checker(["--runtime"], cwd=repo)
    mutations = run_checker(["--mutations"], cwd=repo)

    assert runtime.state == "USAGE_ERROR"
    assert mutations.state == "USAGE_ERROR"
    assert any(issue.rule_id == "CLI001" for issue in runtime.issues)
    assert any(issue.rule_id == "CLI001" for issue in mutations.issues)


def test_checker_requires_strict_registered_execution_markers(tmp_path):
    setup_cfg = """\
[tool:pytest]
markers =
    db: uses the database
    auth: ownership marker that must not be registered
"""
    repo = _make_repo(tmp_path, setup_cfg=setup_cfg)

    result = run_checker([], cwd=repo)

    rule_ids = {issue.rule_id for issue in result.issues}
    assert result.state == "FAIL"
    assert {"CFG003", "CFG004", "CFG005", "CFG006"} <= rule_ids


def test_checker_rejects_unknown_or_ownership_markers_in_tests(tmp_path):
    repo = _make_repo(tmp_path)
    _write_test(
        repo,
        "games/test_policy_auth_marker.py",
        "import pytest\n\n"
        "@pytest.mark.auth\n"
        "def test_marker_policy():\n"
        "    assert True\n",
    )

    result = run_checker(["games"], cwd=repo)

    rule_ids = {issue.rule_id for issue in result.issues}
    assert result.state == "FAIL"
    assert {"MRK001", "MRK002"} <= rule_ids


def test_checker_enforces_skip_and_xfail_policy(tmp_path):
    repo = _make_repo(tmp_path)
    _write_test(
        repo,
        "infrastructure/test_marker_policy.py",
        "import pytest\n\n"
        "@pytest.mark.skip\n"
        "def test_skip_requires_reason():\n"
        "    assert True\n\n"
        "@pytest.mark.xfail(reason='known temporary issue')\n"
        "def test_xfail_requires_strict():\n"
        "    assert False\n",
    )

    result = run_checker(["infrastructure"], cwd=repo)

    rule_ids = {issue.rule_id for issue in result.issues}
    assert result.state == "FAIL"
    assert {"MRK003", "MRK004"} <= rule_ids


def test_checker_keeps_no_db_cleanup_from_bypassing_database_cleanup(tmp_path):
    repo = _make_repo(tmp_path)
    _write_test(
        repo,
        "infrastructure/test_bad_cleanup_marker.py",
        "import pytest\n\n"
        "pytestmark = [pytest.mark.no_db_cleanup, pytest.mark.db]\n\n"
        "def test_db_case(client):\n"
        "    assert True\n",
    )

    result = run_checker(["infrastructure"], cwd=repo)

    rule_ids = {issue.rule_id for issue in result.issues}
    assert result.state == "FAIL"
    assert {"MRK005", "MRK006"} <= rule_ids


def test_checker_blocks_direct_database_import_with_no_db_cleanup(tmp_path):
    repo = _make_repo(tmp_path)
    _write_test(
        repo,
        "infrastructure/test_bad_direct_database_import.py",
        "import pytest\n\n"
        "from backend.database import SessionLocal\n\n"
        "pytestmark = pytest.mark.no_db_cleanup\n\n"
        "def test_direct_database_import():\n"
        "    assert SessionLocal is not None\n",
    )

    result = run_checker(["infrastructure"], cwd=repo)

    rule_ids = {issue.rule_id for issue in result.issues}
    assert result.state == "FAIL"
    assert "MRK007" in rule_ids


def test_checker_validates_traceability_manifest_schema(tmp_path):
    repo = _make_repo(tmp_path)
    _write_test(
        repo,
        "games/test_api_join.py",
        "def test_eligible_user_can_join_open_game():\n"
        "    assert True\n",
    )
    _write(repo / "backend" / "tests" / "games" / "TESTING.md", "# Games Backend Testing\n")
    _write(
        repo / "backend" / "tests" / "games" / "testing_manifest.yaml",
        "schema_version: 2\n"
        "domain: Games\n"
        "authoritative_sources:\n"
        "  - docs/agent-notes/game-details.md\n"
        "behaviors:\n"
        "  - id: GAMES-001\n"
        "    summary: missing source field\n"
        "test_refs:\n"
        "  - backend/tests/games/test_api_join.py::test_eligible_user_can_join_open_game\n"
        "duplicated_spec_matrix: should not be here\n",
    )

    result = run_checker(["games"], cwd=repo)

    assert result.state == "FAIL"
    assert any(issue.rule_id == "TRC001" for issue in result.issues)


def test_checker_requires_testing_doc_and_manifest_as_a_pair(tmp_path):
    repo = _make_repo(tmp_path)
    _write(repo / "backend" / "tests" / "games" / "TESTING.md", "# Games Backend Testing\n")

    result = run_checker(["games"], cwd=repo)

    assert result.state == "FAIL"
    assert any(issue.rule_id == "TRC003" for issue in result.issues)


def test_checker_enforces_support_dependency_direction(tmp_path):
    repo = _make_repo(tmp_path)
    _write(
        repo / "backend" / "tests" / "support" / "factories.py",
        "import backend.tests.pages.my_games.conftest\n",
    )

    result = run_checker(["support"], cwd=repo)

    assert result.state == "FAIL"
    assert any(issue.rule_id == "SUP001" for issue in result.issues)


def test_traceability_template_stays_valid():
    template = (
        Path(__file__).resolve().parent
        / "support"
        / "testing_manifest.template.yaml"
    ).read_text()

    result = validate_traceability_manifest_text(template)

    assert result.ok


def test_report_states_checker_does_not_certify_business_coverage(tmp_path):
    repo = _make_repo(tmp_path)
    result = run_checker([], cwd=repo)

    report = render_report(result)

    assert "mechanical backend test architecture and safety rules only" in report
    assert "no business coverage is validated" in report
