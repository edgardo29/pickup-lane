from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import check_backend_tests as checker_module
from check_backend_tests import run_checker
from compliance.policies import parse_suite_policy
from compliance.report import CheckResult
from compliance.requirements import (
    load_requirement_declarations,
    parse_requirement_declarations,
    valid_requirement_id,
)
from compliance.targeting import resolve_target, trusted_test_files


pytestmark = [
    pytest.mark.no_db_cleanup,
    pytest.mark.requirement(
        "EN01-R1",
        "EN01-R2",
        "EN01-R8",
        "EN01-R9",
        "EN01-R10",
        "EN01-R11",
    ),
]


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def _requirements_payload(*requirement_ids: str, state: str = "required") -> dict:
    return {
        "schema_version": 1,
        "requirements": [
            {
                "id": requirement_id,
                "owning_pass": "EN-01",
                "source_controls": ["TST-001"],
                "state": state,
                "scope": "checker",
            }
            for requirement_id in requirement_ids
        ],
    }


def _suite_policy_payload() -> dict:
    return {
        "schema_version": 1,
        "suite_types": {
            "ordinary": {
                "allows_uncontrolled_network": False,
                "allows_production_resources": False,
            },
            "full_stack": {
                "allows_uncontrolled_network": False,
                "allows_production_resources": False,
            },
            "provider_contract": {
                "allows_uncontrolled_network": False,
                "allows_production_resources": False,
                "requires_explicit_network_opt_in": True,
            },
        },
        "trusted_roots": {
            "checker": "ordinary",
            "domains": "ordinary",
            "workflows": "ordinary",
            "platform": "ordinary",
            "migrations": "ordinary",
            "provider_contract": "provider_contract",
        },
        "untrusted_application_roots": ["pages", "shared"],
        "historical_roots": ["legacy"],
    }


def _marker_config(*, strict: bool = True) -> str:
    addopts = "addopts = --strict-markers\n" if strict else ""
    return (
        "[tool:pytest]\n"
        f"{addopts}"
        "markers =\n"
        "    no_db_cleanup: no database cleanup\n"
        "    requirement(*ids): stable requirement metadata\n"
        "    suite_type(name): execution suite type\n"
    )


def _make_repo(
    tmp_path: Path,
    *,
    test_text: str,
    requirements: dict | None = None,
    suite_policy: dict | None = None,
    marker_config: str | None = None,
) -> Path:
    repo = tmp_path / "repo"
    _write(repo / "backend" / "setup.cfg", marker_config or _marker_config())
    _write(
        repo / "backend" / "tests" / "support" / "requirements" / "en01.json",
        json.dumps(requirements or _requirements_payload("EN01-R1"), indent=2),
    )
    _write(
        repo / "backend" / "tests" / "support" / "suite_policy.json",
        json.dumps(suite_policy or _suite_policy_payload(), indent=2),
    )
    _write(repo / "backend" / "tests" / "checker" / "test_foundation.py", test_text)
    return repo


def _trusted_test(requirement_ids: str = '"EN01-R1"') -> str:
    return (
        "import pytest\n\n"
        "pytestmark = [pytest.mark.no_db_cleanup, pytest.mark.requirement("
        f"{requirement_ids})]\n\n"
        "def test_foundation_rule():\n"
        "    assert True\n"
    )


def test_file_domain_and_suite_scopes_generate_traceability(tmp_path, monkeypatch):
    repo = _make_repo(
        tmp_path,
        requirements=_requirements_payload("EN01-R1"),
        test_text=_trusted_test('"EN01-R1"'),
    )
    monkeypatch.chdir(repo)

    file_result = run_checker(["--scope", "file", "backend/tests/checker/test_foundation.py"])
    domain_result = run_checker(["--scope", "domain", "backend/tests/checker"])
    suite_result = run_checker(["--scope", "suite"])

    assert file_result.state == "PASS"
    assert domain_result.state == "PASS"
    assert suite_result.state == "PASS"
    assert suite_result.traceability["EN-01"]["EN01-R1"] == [
        "backend/tests/checker/test_foundation.py::test_foundation_rule"
    ]


def test_requirement_declarations_load_multiple_pass_files_and_en02_ids(tmp_path):
    requirements_dir = tmp_path / "requirements"
    _write(
        requirements_dir / "en01.json",
        json.dumps(_requirements_payload("EN01-R1"), indent=2),
    )
    _write(
        requirements_dir / "en02.json",
        json.dumps(
            {
                "schema_version": 1,
                "requirements": [
                    {
                        "id": "EN02-CORR-001",
                        "owning_pass": "EN-02",
                        "source_controls": ["API-M15"],
                        "state": "required",
                        "scope": "platform/observability",
                    }
                ],
            },
            indent=2,
        ),
    )

    declarations, result = load_requirement_declarations(requirements_dir)

    assert result.state == "PASS"
    assert valid_requirement_id("EN02-CORR-001")
    assert set(declarations) == {"EN01-R1", "EN02-CORR-001"}
    assert declarations["EN02-CORR-001"].owning_pass == "EN-02"


def test_domain_traceability_completeness_uses_requirement_scope(tmp_path, monkeypatch):
    repo = _make_repo(
        tmp_path,
        requirements=_requirements_payload("EN01-R1"),
        test_text=_trusted_test('"EN01-R1"'),
    )
    _write(
        repo / "backend" / "tests" / "support" / "requirements" / "en02.json",
        json.dumps(
            {
                "schema_version": 1,
                "requirements": [
                    {
                        "id": "EN02-CORR-001",
                        "owning_pass": "EN-02",
                        "source_controls": ["API-M15"],
                        "state": "required",
                        "scope": "platform/observability",
                    }
                ],
            },
            indent=2,
        ),
    )
    _write(
        repo / "backend" / "tests" / "platform" / "observability" / "test_correlation.py",
        "import pytest\n\n"
        "pytestmark = [pytest.mark.no_db_cleanup, pytest.mark.requirement('EN02-CORR-001')]\n\n"
        "def test_en02_correlation():\n"
        "    assert True\n",
    )
    monkeypatch.chdir(repo)

    platform_result = run_checker(["--scope", "domain", "backend/tests/platform/observability"])
    checker_result = run_checker(["--scope", "domain", "backend/tests/checker"])
    suite_result = run_checker(["--scope", "suite"])

    assert platform_result.state == "PASS"
    assert checker_result.state == "PASS"
    assert suite_result.state == "PASS"
    assert platform_result.traceability["EN-02"]["EN02-CORR-001"] == [
        "backend/tests/platform/observability/test_correlation.py::test_en02_correlation"
    ]
    assert checker_result.traceability["EN-01"]["EN01-R1"] == [
        "backend/tests/checker/test_foundation.py::test_foundation_rule"
    ]


def test_file_scope_has_no_completeness_claim_but_domain_scope_blocks_missing_required_evidence(tmp_path, monkeypatch):
    repo = _make_repo(
        tmp_path,
        requirements=_requirements_payload("EN01-R1", "EN01-R2"),
        test_text=_trusted_test('"EN01-R1"'),
    )
    monkeypatch.chdir(repo)

    file_result = run_checker(["--scope", "file", "backend/tests/checker/test_foundation.py"])
    domain_result = run_checker(["--scope", "domain", "backend/tests/checker"])

    assert file_result.state == "PASS"
    assert domain_result.state == "BLOCKED"
    assert any(issue.rule_id == "TRACE001" and issue.location == "EN01-R2" for issue in domain_result.issues)


def test_requirement_declarations_detect_duplicates_malformed_ids_and_explicit_state_reasons():
    result = CheckResult(target="synthetic", scope="suite")
    declarations = parse_requirement_declarations(
        {
            "schema_version": 1,
            "requirements": [
                {
                    "id": "EN01-R1",
                    "owning_pass": "EN-01",
                    "source_controls": ["TST-001"],
                    "state": "required",
                },
                {
                    "id": "EN01-R1",
                    "owning_pass": "EN-01",
                    "source_controls": ["TST-001"],
                    "state": "required",
                },
                {
                    "id": "bad",
                    "owning_pass": "EN-01",
                    "source_controls": ["TST-001"],
                    "state": "required",
                },
                {
                    "id": "EN01-R2",
                    "owning_pass": "EN-01",
                    "source_controls": ["TST-001"],
                    "state": "blocked",
                },
            ],
        },
        result,
    )

    assert "EN01-R1" in declarations
    assert result.state == "FAIL"
    assert any(issue.rule_id == "REQ005" for issue in result.issues)
    assert any(issue.rule_id == "REQ006" for issue in result.issues)
    assert any(issue.rule_id == "REQ010" for issue in result.issues)


def test_explicit_blocked_requirement_blocks_domain_and_suite_with_exit_code(tmp_path, monkeypatch):
    requirements = {
        "schema_version": 1,
        "requirements": [
            {
                "id": "EN01-R1",
                "owning_pass": "EN-01",
                "source_controls": ["TST-001"],
                "state": "required",
            },
            {
                "id": "EN01-R2",
                "owning_pass": "EN-01",
                "source_controls": ["TST-001"],
                "state": "blocked",
                "reason": "waiting on authoritative owner decision",
            },
        ],
    }
    repo = _make_repo(
        tmp_path,
        requirements=requirements,
        test_text=_trusted_test('"EN01-R1"'),
    )
    monkeypatch.chdir(repo)

    domain_result = run_checker(["--scope", "domain", "backend/tests/checker"])
    suite_result = run_checker(["--scope", "suite"])

    for result in (domain_result, suite_result):
        assert result.state == "BLOCKED"
        assert result.exit_code == 2
        assert any(
            issue.rule_id == "TRACE002"
            and issue.location == "EN01-R2"
            and "waiting on authoritative owner decision" in issue.message
            for issue in result.issues
        )


def test_clean_required_and_covered_requirements_do_not_become_blocked(tmp_path, monkeypatch):
    requirements = {
        "schema_version": 1,
        "requirements": [
            {
                "id": "EN01-R1",
                "owning_pass": "EN-01",
                "source_controls": ["TST-001"],
                "state": "required",
            },
            {
                "id": "EN01-R2",
                "owning_pass": "EN-01",
                "source_controls": ["TST-001"],
                "state": "covered",
            },
        ],
    }
    repo = _make_repo(
        tmp_path,
        requirements=requirements,
        test_text=_trusted_test('"EN01-R1"'),
    )
    monkeypatch.chdir(repo)

    result = run_checker(["--scope", "suite"])

    assert result.state == "PASS"
    assert not any(issue.rule_id == "TRACE002" for issue in result.issues)


def test_failure_precedence_remains_higher_than_explicit_blocked_requirement(tmp_path, monkeypatch):
    requirements = {
        "schema_version": 1,
        "requirements": [
            {
                "id": "EN01-R1",
                "owning_pass": "EN-01",
                "source_controls": ["TST-001"],
                "state": "blocked",
                "reason": "safe blocked reason",
            },
        ],
    }
    repo = _make_repo(
        tmp_path,
        requirements=requirements,
        test_text=(
            "import pytest\n\n"
            "pytestmark = [pytest.mark.no_db_cleanup, pytest.mark.requirement('EN99-R1')]\n\n"
            "def test_unknown_requirement():\n"
            "    assert True\n"
        ),
    )
    monkeypatch.chdir(repo)

    result = run_checker(["--scope", "suite"])

    assert result.state == "FAIL"
    assert result.exit_code == 1
    assert any(issue.rule_id == "META003" for issue in result.issues)
    assert any(issue.rule_id == "TRACE002" for issue in result.issues)


def test_supported_explicit_requirement_states_parse_with_reasons():
    result = CheckResult(target="synthetic", scope="suite")
    payload = {
        "schema_version": 1,
        "requirements": [
            {
                "id": f"EN01-R{index}",
                "owning_pass": "EN-01",
                "source_controls": ["TST-001"],
                "state": state,
                **({"reason": "synthetic state reason"} if state != "required" else {}),
            }
            for index, state in enumerate(
                [
                    "required",
                    "covered",
                    "partial",
                    "missing",
                    "blocked",
                    "deferred",
                    "covered_elsewhere",
                    "not_applicable",
                ],
                start=1,
            )
        ],
    }

    declarations = parse_requirement_declarations(payload, result)

    assert result.state == "PASS"
    assert set(declarations) == {f"EN01-R{index}" for index in range(1, 9)}


def test_unknown_malformed_and_missing_requirement_metadata_are_machine_failures(tmp_path, monkeypatch):
    repo = _make_repo(
        tmp_path,
        requirements=_requirements_payload("EN01-R1"),
        test_text=(
            "import pytest\n\n"
            "pytestmark = pytest.mark.no_db_cleanup\n\n"
            "@pytest.mark.requirement('EN99-R1')\n"
            "def test_unknown():\n"
            "    assert True\n\n"
            "@pytest.mark.requirement('bad')\n"
            "def test_malformed():\n"
            "    assert True\n\n"
            "def test_missing_metadata():\n"
            "    assert True\n"
        ),
    )
    monkeypatch.chdir(repo)

    result = run_checker(["--scope", "domain", "backend/tests/checker"])

    assert result.state == "FAIL"
    assert any(issue.rule_id == "META001" for issue in result.issues)
    assert any(issue.rule_id == "META002" for issue in result.issues)
    assert any(issue.rule_id == "META003" for issue in result.issues)


def test_one_requirement_can_map_to_many_tests_and_one_test_can_map_to_many_requirements(tmp_path, monkeypatch):
    repo = _make_repo(
        tmp_path,
        requirements=_requirements_payload("EN01-R1", "EN01-R2"),
        test_text=(
            "import pytest\n\n"
            "pytestmark = pytest.mark.no_db_cleanup\n\n"
            "@pytest.mark.requirement('EN01-R1')\n"
            "def test_first_mapping():\n"
            "    assert True\n\n"
            "@pytest.mark.requirement('EN01-R1', 'EN01-R2')\n"
            "def test_second_mapping():\n"
            "    assert True\n"
        ),
    )
    monkeypatch.chdir(repo)

    result = run_checker(["--scope", "suite"])

    assert result.state == "PASS"
    assert result.traceability["EN-01"]["EN01-R1"] == [
        "backend/tests/checker/test_foundation.py::test_first_mapping",
        "backend/tests/checker/test_foundation.py::test_second_mapping",
    ]
    assert result.traceability["EN-01"]["EN01-R2"] == [
        "backend/tests/checker/test_foundation.py::test_second_mapping"
    ]


def test_generated_traceability_updates_when_a_test_is_renamed_without_registry_changes(tmp_path, monkeypatch):
    repo = _make_repo(
        tmp_path,
        requirements=_requirements_payload("EN01-R1"),
        test_text=(
            "import pytest\n\n"
            "pytestmark = [pytest.mark.no_db_cleanup, pytest.mark.requirement('EN01-R1')]\n\n"
            "def test_before_rename():\n"
            "    assert True\n"
        ),
    )
    monkeypatch.chdir(repo)

    before = run_checker(["--scope", "suite"])
    (repo / "backend" / "tests" / "checker" / "test_foundation.py").write_text(
        "import pytest\n\n"
        "pytestmark = [pytest.mark.no_db_cleanup, pytest.mark.requirement('EN01-R1')]\n\n"
        "def test_after_rename():\n"
        "    assert True\n"
    )
    after = run_checker(["--scope", "suite"])

    assert before.traceability["EN-01"]["EN01-R1"] == [
        "backend/tests/checker/test_foundation.py::test_before_rename"
    ]
    assert after.traceability["EN-01"]["EN01-R1"] == [
        "backend/tests/checker/test_foundation.py::test_after_rename"
    ]


def test_historical_and_untrusted_application_areas_are_not_trusted_targets(tmp_path):
    repo = tmp_path / "repo"
    (repo / "backend" / "tests" / "legacy").mkdir(parents=True)
    (repo / "backend" / "tests" / "pages" / "example").mkdir(parents=True)
    (repo / "backend" / "tests" / "shared" / "example").mkdir(parents=True)

    legacy_target, legacy_error = resolve_target(
        scope="file",
        target_text="backend/tests/legacy/test_old.py",
        cwd=repo,
    )
    pages_target, pages_error = resolve_target(
        scope="domain",
        target_text="backend/tests/pages/example",
        cwd=repo,
    )
    shared_target, shared_error = resolve_target(
        scope="domain",
        target_text="backend/tests/shared/example",
        cwd=repo,
    )

    assert legacy_target is None
    assert legacy_error is not None
    assert legacy_error.state == "USAGE_ERROR"
    assert pages_target is None
    assert pages_error is not None
    assert pages_error.state == "USAGE_ERROR"
    assert shared_target is None
    assert shared_error is not None
    assert shared_error.state == "USAGE_ERROR"


def test_untrusted_application_tests_do_not_satisfy_suite_traceability(tmp_path, monkeypatch):
    repo = _make_repo(
        tmp_path,
        requirements=_requirements_payload("EN01-R1", "EN01-R2"),
        test_text=_trusted_test('"EN01-R2"'),
    )
    _write(
        repo / "backend" / "tests" / "pages" / "example" / "test_page.py",
        "import pytest\n\n"
        "pytestmark = [pytest.mark.no_db_cleanup, pytest.mark.requirement('EN01-R1')]\n\n"
        "def test_untrusted_page_evidence():\n"
        "    assert True\n",
    )
    monkeypatch.chdir(repo)

    result = run_checker(["--scope", "suite"])

    assert result.state == "BLOCKED"
    assert result.traceability["EN-01"]["EN01-R1"] == []
    assert result.traceability["EN-01"]["EN01-R2"] == [
        "backend/tests/checker/test_foundation.py::test_foundation_rule"
    ]


def test_normalized_real_trusted_file_target_is_accepted(tmp_path, monkeypatch):
    repo = _make_repo(
        tmp_path,
        requirements=_requirements_payload("EN01-R1"),
        test_text=_trusted_test('"EN01-R1"'),
    )
    monkeypatch.chdir(repo)

    result = run_checker(["--scope", "file", "backend/tests/checker/../checker/test_foundation.py"])

    assert result.state == "PASS"
    assert result.traceability["EN-01"]["EN01-R1"] == [
        "backend/tests/checker/test_foundation.py::test_foundation_rule"
    ]


def test_direct_symlink_file_target_under_trusted_root_is_rejected(tmp_path, monkeypatch):
    repo = _make_repo(
        tmp_path,
        requirements=_requirements_payload("EN01-R1"),
        test_text=_trusted_test('"EN01-R1"'),
    )
    untrusted_file = repo / "backend" / "tests" / "pages" / "example" / "test_page.py"
    _write(untrusted_file, _trusted_test('"EN01-R1"'))
    link_path = repo / "backend" / "tests" / "checker" / "test_link.py"
    link_path.symlink_to(untrusted_file)
    monkeypatch.chdir(repo)

    result = run_checker(["--scope", "file", "backend/tests/checker/test_link.py"])

    assert result.state == "USAGE_ERROR"
    assert any(issue.rule_id == "TGT013" for issue in result.issues)


def test_direct_symlink_file_target_to_another_trusted_root_is_rejected(tmp_path, monkeypatch):
    repo = _make_repo(
        tmp_path,
        requirements=_requirements_payload("EN01-R1"),
        test_text=_trusted_test('"EN01-R1"'),
    )
    domain_file = repo / "backend" / "tests" / "domains" / "example" / "test_domain.py"
    _write(domain_file, _trusted_test('"EN01-R1"'))
    link_path = repo / "backend" / "tests" / "checker" / "test_domain_link.py"
    link_path.symlink_to(domain_file)
    monkeypatch.chdir(repo)

    result = run_checker(["--scope", "file", "backend/tests/checker/test_domain_link.py"])

    assert result.state == "USAGE_ERROR"
    assert any(issue.rule_id == "TGT013" for issue in result.issues)


def test_domain_and_suite_discovery_do_not_count_symlinked_untrusted_evidence(tmp_path, monkeypatch):
    repo = _make_repo(
        tmp_path,
        requirements=_requirements_payload("EN01-R1", "EN01-R2"),
        test_text=_trusted_test('"EN01-R2"'),
    )
    untrusted_dir = repo / "backend" / "tests" / "pages" / "example"
    untrusted_file = untrusted_dir / "test_page.py"
    _write(untrusted_file, _trusted_test('"EN01-R1"'))
    symlink_file = repo / "backend" / "tests" / "checker" / "test_page_link.py"
    symlink_dir = repo / "backend" / "tests" / "checker" / "page_link"
    symlink_file.symlink_to(untrusted_file)
    symlink_dir.symlink_to(untrusted_dir, target_is_directory=True)
    monkeypatch.chdir(repo)

    direct_dir_result = run_checker(["--scope", "domain", "backend/tests/checker/page_link"])
    domain_result = run_checker(["--scope", "domain", "backend/tests/checker"])
    suite_result = run_checker(["--scope", "suite"])
    trusted_files = trusted_test_files(repo / "backend" / "tests")

    assert direct_dir_result.state == "USAGE_ERROR"
    assert domain_result.state == "BLOCKED"
    assert suite_result.state == "BLOCKED"
    assert domain_result.traceability["EN-01"]["EN01-R1"] == []
    assert suite_result.traceability["EN-01"]["EN01-R1"] == []
    assert all(not path.is_symlink() for path in trusted_files)
    assert symlink_file not in trusted_files


def test_checker_result_states_are_deterministic(tmp_path, monkeypatch, capsys):
    passing_repo = _make_repo(
        tmp_path / "pass",
        requirements=_requirements_payload("EN01-R1"),
        test_text=_trusted_test('"EN01-R1"'),
    )
    monkeypatch.chdir(passing_repo)
    assert run_checker(["--scope", "suite"]).state == "PASS"
    assert run_checker(["--scope", "suite", "--runtime"]).state == "USAGE_ERROR"

    blocked_repo = _make_repo(
        tmp_path / "blocked",
        requirements=_requirements_payload("EN01-R1", "EN01-R2"),
        test_text=_trusted_test('"EN01-R1"'),
    )
    monkeypatch.chdir(blocked_repo)
    assert run_checker(["--scope", "suite"]).state == "BLOCKED"

    failing_repo = _make_repo(
        tmp_path / "fail",
        requirements=_requirements_payload("EN01-R1"),
        test_text=(
            "import pytest\n\n"
            "pytestmark = [pytest.mark.no_db_cleanup, pytest.mark.requirement('UNKNOWN-R1')]\n\n"
            "def test_unknown():\n"
            "    assert True\n"
        ),
    )
    monkeypatch.chdir(failing_repo)
    assert run_checker(["--scope", "suite"]).state == "FAIL"

    def raise_internal_error(_argv):
        raise RuntimeError("synthetic checker failure")

    monkeypatch.setattr(checker_module, "run_checker", raise_internal_error)
    assert checker_module.main(["--scope", "suite"]) == 4
    assert "INTERNAL_ERROR" in capsys.readouterr().out


def test_suite_policy_defines_required_execution_suite_types():
    result = CheckResult(target="suite_policy", scope="suite")

    policy = parse_suite_policy(_suite_policy_payload(), result)

    assert result.state == "PASS"
    assert policy is not None
    assert {"ordinary", "full_stack", "provider_contract"}.issubset(policy.suite_types)
    assert policy.suite_types["ordinary"]["allows_production_resources"] is False
    assert policy.suite_types["provider_contract"]["requires_explicit_network_opt_in"] is True


def test_suite_separation_blocks_ordinary_provider_calls_and_suite_type_mismatch(tmp_path, monkeypatch):
    repo = _make_repo(
        tmp_path,
        requirements=_requirements_payload("EN01-R1"),
        test_text=(
            "import pytest\n"
            "import socket\n\n"
            "pytestmark = [pytest.mark.no_db_cleanup, pytest.mark.requirement('EN01-R1'), pytest.mark.suite_type('provider_contract')]\n\n"
            "def test_bad_ordinary_provider_call():\n"
            "    socket.create_connection(('example.invalid', 443))\n"
        ),
    )
    monkeypatch.chdir(repo)

    result = run_checker(["--scope", "domain", "backend/tests/checker"])

    assert result.state == "FAIL"
    assert any(issue.rule_id == "SUITE008" for issue in result.issues)
    assert any(issue.rule_id == "NET001" for issue in result.issues)


def test_provider_contract_suite_type_is_separate_from_ordinary_tests(tmp_path, monkeypatch):
    repo = _make_repo(
        tmp_path,
        requirements=_requirements_payload("EN01-R1"),
        test_text=_trusted_test('"EN01-R1"'),
    )
    provider_test = (
        "import pytest\n"
        "import socket\n\n"
        "pytestmark = [pytest.mark.no_db_cleanup, pytest.mark.requirement('EN01-R1')]\n\n"
        "def test_provider_contract_network_boundary():\n"
        "    socket.create_connection(('example.invalid', 443))\n"
    )
    _write(repo / "backend" / "tests" / "provider_contract" / "test_provider_boundary.py", provider_test)
    monkeypatch.chdir(repo)

    result = run_checker(["--scope", "domain", "backend/tests/provider_contract"])

    assert result.state == "PASS"


def test_marker_registration_and_strict_markers_are_required(tmp_path, monkeypatch):
    repo = _make_repo(
        tmp_path,
        marker_config=_marker_config(strict=False),
        requirements=_requirements_payload("EN01-R1"),
        test_text=_trusted_test('"EN01-R1"'),
    )
    monkeypatch.chdir(repo)

    result = run_checker(["--scope", "suite"])

    assert result.state == "FAIL"
    assert any(issue.rule_id == "CFG002" for issue in result.issues)
