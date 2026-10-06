from __future__ import annotations

import ast
import configparser
import re
import shlex
from pathlib import Path

import pytest

pytestmark = pytest.mark.no_db_cleanup

REPO_ROOT = Path(__file__).resolve().parents[4]
BACKEND_TESTS_ROOT = REPO_ROOT / "backend" / "tests"
CI_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "ci.yml"
PLAYWRIGHT_CONFIG_PATH = REPO_ROOT / "frontend" / "playwright.config.js"
ACTIVE_BACKEND_TEST_ROOTS = ("domains", "workflows", "platform", "migrations")
SEPARATE_BACKEND_TEST_ROOTS = ("provider_contract",)
ACTIVE_EXECUTABLE_ROOTS = (
    REPO_ROOT / ".github",
    REPO_ROOT / "backend",
    REPO_ROOT / "frontend",
    REPO_ROOT / "scripts",
)
ACTIVE_EXECUTABLE_SUFFIXES = frozenset(
    {
        ".cfg",
        ".cjs",
        ".ini",
        ".js",
        ".jsx",
        ".mjs",
        ".py",
        ".sh",
        ".toml",
        ".ts",
        ".tsx",
        ".yaml",
        ".yml",
    }
)
INACTIVE_EXECUTABLE_PATH_PARTS = frozenset(
    {
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "__pycache__",
        "dist",
        "legacy",
        "node_modules",
        "playwright-report",
        "test-results",
    }
)
PYTEST_CONFIG_PATHS = (
    REPO_ROOT / "setup.cfg",
    REPO_ROOT / "pytest.ini",
    REPO_ROOT / "pyproject.toml",
    REPO_ROOT / "tox.ini",
    REPO_ROOT / "backend" / "setup.cfg",
    REPO_ROOT / "backend" / "pytest.ini",
    REPO_ROOT / "backend" / "pyproject.toml",
)
FINAL_CUSTOM_MARKERS = {
    "migration_lifecycle",
    "no_db_cleanup",
    "pass_provenance",
}
SILENT_RETRY_PATTERNS = ("--reruns", "pytest-rerunfailures")
PRODUCTION_CREDENTIAL_RE = re.compile(r"\b(?:sk|rk|pk|whsec)_live_")


def _current_pytest_config_paths() -> tuple[Path, ...]:
    return tuple(path for path in PYTEST_CONFIG_PATHS if path.is_file())


def _current_backend_test_files() -> tuple[Path, ...]:
    return tuple(
        path
        for path in sorted(BACKEND_TESTS_ROOT.rglob("test_*.py"))
        if "__pycache__" not in path.relative_to(BACKEND_TESTS_ROOT).parts
    )


def _normalized_whitespace(source: str) -> str:
    return " ".join(source.split())


def _current_active_executable_files() -> tuple[Path, ...]:
    files: set[Path] = set()
    for root in ACTIVE_EXECUTABLE_ROOTS:
        if not root.is_dir():
            continue
        files.update(
            path
            for path in root.rglob("*")
            if path.is_file()
            and path.suffix in ACTIVE_EXECUTABLE_SUFFIXES
            and not INACTIVE_EXECUTABLE_PATH_PARTS & set(path.relative_to(root).parts)
        )
    return tuple(sorted(files))


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parts: list[str] = []
        current: ast.AST = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))
    return ""


def _path_literal_parts(node: ast.AST) -> tuple[str, ...]:
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        return _path_literal_parts(node.left) + _path_literal_parts(node.right)
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return (node.value,)
    return ()


def _retired_requirements_manifest_text_lines(source: str) -> set[int]:
    slash_marker = "/".join(  # noqa: FLY002 - avoid matching the guarded literal.
        ("backend", "tests", "support", "requirements")
    )
    short_slash_marker = "/".join(  # noqa: FLY002 - same self-scan constraint.
        ("support", "requirements")
    )
    dotted_marker = ".".join(  # noqa: FLY002 - same self-scan constraint.
        ("backend", "tests", "support", "requirements")
    )
    markers = (slash_marker, short_slash_marker, dotted_marker)
    return {
        line_number
        for line_number, line in enumerate(source.splitlines(), start=1)
        if any(marker in line.replace("\\", "/") for marker in markers)
    }


def _retired_requirements_manifest_lines(source: str) -> list[int]:
    tree = ast.parse(source)
    violations = _retired_requirements_manifest_text_lines(source)

    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            parts = _path_literal_parts(node)
            if any(
                parts[index : index + 2] == ("support", "requirements")
                for index in range(len(parts) - 1)
            ):
                violations.add(node.lineno)

    return sorted(violations)


def _sleep_synchronization_lines(source: str) -> list[int]:
    tree = ast.parse(source)
    return sorted(
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and _call_name(node.func) in {"sleep", "time.sleep"}
    )


def _production_credential_lines(source: str) -> list[int]:
    tree = ast.parse(source)
    return sorted(
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and PRODUCTION_CREDENTIAL_RE.search(node.value)
    )


def _inline_python_child_installs_network_guard(
    tree: ast.Module,
    call: ast.Call,
    command: ast.List | ast.Tuple,
) -> bool:
    command_parts = command.elts
    command_flag_index = next(
        (
            index
            for index, element in enumerate(command_parts)
            if isinstance(element, ast.Constant) and element.value == "-c"
        ),
        None,
    )
    if command_flag_index is None or command_flag_index + 1 >= len(command_parts):
        return False
    script_expression = command_parts[command_flag_index + 1]
    if isinstance(script_expression, ast.Name):
        enclosing_scopes = [
            scope
            for scope in ast.walk(tree)
            if isinstance(scope, (ast.AsyncFunctionDef, ast.FunctionDef))
            and scope.lineno <= call.lineno <= (scope.end_lineno or scope.lineno)
        ]
        scope: ast.AST = min(
            enclosing_scopes,
            key=lambda candidate: (candidate.end_lineno or candidate.lineno)
            - candidate.lineno,
            default=tree,
        )
        assignments = [
            node
            for node in ast.walk(scope)
            if isinstance(node, ast.Assign)
            and node.lineno < call.lineno
            and any(
                isinstance(target, ast.Name)
                and target.id == script_expression.id
                for target in node.targets
            )
        ]
        if not assignments:
            return False
        script_expression = max(assignments, key=lambda node: node.lineno).value

    return any(
        isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and "install_test_network_guard" in node.value
        for node in ast.walk(script_expression)
    )


def _unsafe_subprocess_lines(source: str) -> list[int]:
    tree = ast.parse(source)
    violations: set[int] = set()

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or _call_name(node.func) not in {
            "subprocess.call",
            "subprocess.check_call",
            "subprocess.check_output",
            "subprocess.Popen",
            "subprocess.run",
        }:
            continue

        environment = next(
            (keyword.value for keyword in node.keywords if keyword.arg == "env"),
            None,
        )
        if not (
            isinstance(environment, ast.Call)
            and _call_name(environment.func) == "isolated_test_subprocess_environment"
        ):
            violations.add(node.lineno)

        command = node.args[0] if node.args else None
        if isinstance(command, (ast.List, ast.Tuple)):
            is_python_inline = any(
                _call_name(element) == "sys.executable"
                for element in command.elts
            ) and any(
                isinstance(element, ast.Constant) and element.value == "-c"
                for element in command.elts
            )
            if is_python_inline and not _inline_python_child_installs_network_guard(
                tree,
                node,
                command,
            ):
                violations.add(node.lineno)

    return sorted(violations)


def _registered_markers(config: configparser.ConfigParser) -> set[str]:
    marker_lines = config.get("tool:pytest", "markers").splitlines()
    return {
        line.strip().split(":", 1)[0].split("(", 1)[0]
        for line in marker_lines
        if line.strip()
    }


@pytest.mark.pass_provenance("EN-01")
def test_marker_registration_and_strict_markers_are_required():
    config = configparser.ConfigParser()
    loaded = config.read(REPO_ROOT / "backend" / "setup.cfg")

    assert loaded == [str(REPO_ROOT / "backend" / "setup.cfg")]
    addopts = shlex.split(config.get("tool:pytest", "addopts"))
    assert "--strict-markers" in addopts

    registered = _registered_markers(config)
    assert registered == FINAL_CUSTOM_MARKERS


def test_pytest_configuration_does_not_enable_silent_reruns():
    config_paths = _current_pytest_config_paths()
    assert config_paths
    assert any(pattern in "addopts = --reruns 2" for pattern in SILENT_RETRY_PATTERNS)

    violations = {
        str(path.relative_to(REPO_ROOT)): pattern
        for path in config_paths
        for pattern in SILENT_RETRY_PATTERNS
        if pattern in path.read_text(encoding="utf-8")
    }

    assert violations == {}


def test_ci_collects_and_executes_the_complete_active_backend_suite():
    source = _normalized_whitespace(CI_WORKFLOW_PATH.read_text(encoding="utf-8"))
    guarded_runner = "python -m backend.test_runner"

    assert (
        f"{guarded_runner} test ordinary "
        "backend/tests/domains backend/tests/workflows backend/tests/platform "
        "backend/tests/migrations --collect-only -q"
    ) in source
    assert (
        f"{guarded_runner} test ordinary "
        "backend/tests/domains backend/tests/workflows backend/tests/platform -q"
    ) in source
    assert (
        f"{guarded_runner} test migration backend/tests/migrations -q"
    ) in source
    assert f"{guarded_runner} test ordinary backend/tests --collect-only" not in source

    active_roots = {
        path.relative_to(BACKEND_TESTS_ROOT).parts[0]
        for path in _current_backend_test_files()
    }
    assert active_roots == {
        *ACTIVE_BACKEND_TEST_ROOTS,
        *SEPARATE_BACKEND_TEST_ROOTS,
    }


def test_ci_runs_frontend_unit_and_reproducible_zero_retry_browser_smoke():
    workflow = _normalized_whitespace(CI_WORKFLOW_PATH.read_text(encoding="utf-8"))
    playwright = PLAYWRIGHT_CONFIG_PATH.read_text(encoding="utf-8")

    assert "npm run test:unit" in workflow
    assert "npx playwright install --with-deps chromium" in workflow
    assert "npm run test:e2e:smoke" in workflow
    assert "retries: 0" in playwright
    assert "channel:" not in playwright
    assert "trace: 'retain-on-failure'" in playwright


def test_current_backend_tests_do_not_use_sleep_based_synchronization():
    assert _sleep_synchronization_lines("import time\ntime.sleep(1)\n") == [2]

    violations = {
        str(path.relative_to(REPO_ROOT)): lines
        for path in _current_backend_test_files()
        if (lines := _sleep_synchronization_lines(path.read_text(encoding="utf-8")))
    }

    assert violations == {}


def test_current_executable_sources_do_not_depend_on_retired_requirements_manifests():
    direct_reference = "/".join(  # noqa: FLY002 - construct the forbidden sample.
        ("backend", "tests", "support", "requirements", "ws02_02.json")
    )
    composed_reference = "ROOT / " + " / ".join(
        repr(part)
        for part in ("backend", "tests", "support", "requirements", "ws02_02.json")
    )
    assert _retired_requirements_manifest_lines(
        f'declaration_path = "{direct_reference}"\n'
    ) == [1]
    assert _retired_requirements_manifest_lines(
        f"declaration_path = {composed_reference}\n"
    ) == [1]

    violations = {
        str(path.relative_to(REPO_ROOT)): lines
        for path in _current_active_executable_files()
        if (
            lines := (
                _retired_requirements_manifest_lines(path.read_text(encoding="utf-8"))
                if path.suffix == ".py"
                else sorted(
                    _retired_requirements_manifest_text_lines(
                        path.read_text(encoding="utf-8")
                    )
                )
            )
        )
    }

    assert violations == {}


def test_current_test_source_and_configuration_have_no_production_credentials():
    sample = "credential = '" + "sk_" + "live_example'\n"
    assert _production_credential_lines(sample) == [1]

    source_violations = {
        str(path.relative_to(REPO_ROOT)): lines
        for path in _current_backend_test_files()
        if (lines := _production_credential_lines(path.read_text(encoding="utf-8")))
    }
    config_violations = {
        str(path.relative_to(REPO_ROOT)): match.group(0)
        for path in _current_pytest_config_paths()
        if (match := PRODUCTION_CREDENTIAL_RE.search(path.read_text(encoding="utf-8")))
    }

    assert source_violations == {}
    assert config_violations == {}


def test_active_test_subprocesses_use_isolated_environment_and_network_guard():
    unsafe_source = (
        "import os, subprocess, sys\n"
        "subprocess.run([sys.executable, '-c', 'print(1)'], env=os.environ.copy())\n"
    )
    safe_source = (
        "import subprocess, sys\n"
        "from backend.tests.support.environment_safety import "
        "isolated_test_subprocess_environment\n"
        "child = '''from backend.tests.support.environment_safety import "
        "install_test_network_guard\ninstall_test_network_guard()\n'''\n"
        "subprocess.run([sys.executable, '-c', child], "
        "env=isolated_test_subprocess_environment())\n"
    )
    assert _unsafe_subprocess_lines(unsafe_source) == [2]
    assert _unsafe_subprocess_lines(safe_source) == []

    violations = {
        str(path.relative_to(REPO_ROOT)): lines
        for path in _current_backend_test_files()
        if (lines := _unsafe_subprocess_lines(path.read_text(encoding="utf-8")))
    }

    assert violations == {}
