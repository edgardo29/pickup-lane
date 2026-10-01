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


def _current_nonlegacy_test_files() -> tuple[Path, ...]:
    return tuple(
        path
        for path in sorted(BACKEND_TESTS_ROOT.rglob("test_*.py"))
        if "legacy" not in path.relative_to(BACKEND_TESTS_ROOT).parts
    )


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


def test_current_nonlegacy_tests_do_not_use_sleep_based_synchronization():
    assert _sleep_synchronization_lines("import time\ntime.sleep(1)\n") == [2]

    violations = {
        str(path.relative_to(REPO_ROOT)): lines
        for path in _current_nonlegacy_test_files()
        if (lines := _sleep_synchronization_lines(path.read_text(encoding="utf-8")))
    }

    assert violations == {}


def test_current_test_source_and_configuration_have_no_production_credentials():
    sample = "credential = '" + "sk_" + "live_example'\n"
    assert _production_credential_lines(sample) == [1]

    source_violations = {
        str(path.relative_to(REPO_ROOT)): lines
        for path in _current_nonlegacy_test_files()
        if (lines := _production_credential_lines(path.read_text(encoding="utf-8")))
    }
    config_violations = {
        str(path.relative_to(REPO_ROOT)): match.group(0)
        for path in _current_pytest_config_paths()
        if (match := PRODUCTION_CREDENTIAL_RE.search(path.read_text(encoding="utf-8")))
    }

    assert source_violations == {}
    assert config_violations == {}
