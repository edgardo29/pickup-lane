from __future__ import annotations

import ast
import re
from pathlib import Path

from .report import CheckResult, Severity
from .static_analysis import StaticIndex
from .targeting import Target


BUILTIN_MARKERS = {
    "parametrize",
    "skip",
    "skipif",
    "xfail",
    "usefixtures",
    "filterwarnings",
}


def analyze_repository(target: Target, index: StaticIndex) -> CheckResult:
    result = CheckResult(target=str(target.relative_path), scope=target.scope)  # type: ignore[arg-type]
    directory_level = target.scope == "directory"

    workflows = _read_workflows(target.repo_root)
    pytest_config = _read_pytest_config(target.repo_root)
    custom_markers = _collect_custom_markers(index)

    if custom_markers:
        if not _markers_registered(pytest_config, custom_markers) or "--strict-markers" not in pytest_config:
            _add_repo_issue(
                result,
                directory_level,
                "REP001",
                "failure",
                f"custom markers need registration and strict marker validation: {sorted(custom_markers)}",
            )

    if not workflows:
        _add_repo_issue(result, directory_level, "REP002", "blocker", "no GitHub Actions workflow files found for backend validation")
        return result

    workflow_text = "\n".join(workflows)

    if not ("pytest" in workflow_text and "backend/tests" in workflow_text):
        _add_repo_issue(result, directory_level, "REP002", "blocker", "CI workflow does not show backend test suite execution")
    if not _has_isolated_db_indicator(workflow_text):
        _add_repo_issue(result, directory_level, "REP003", "blocker", "CI workflow lacks clear isolated test database evidence")
    if "alembic" not in workflow_text:
        _add_repo_issue(result, directory_level, "REP004", "blocker", "CI workflow lacks migration apply/validation evidence")
    if re.search(r"\b(prod|production)\b", workflow_text, flags=re.IGNORECASE):
        _add_repo_issue(result, directory_level, "REP005", "failure", "CI workflow contains production credential/infrastructure indicators")
    if re.search(r"(--maxfail\s*=?\s*1|\s-x(\s|$)|--exitfirst)", workflow_text):
        _add_repo_issue(result, directory_level, "REP006", "failure", "normal CI appears to stop after first backend test failure")
    if "permissions:" not in workflow_text:
        _add_repo_issue(result, directory_level, "REP007", "blocker", "CI workflow lacks explicit least-privilege permissions evidence")
    if re.search(r">\s*/dev/null|2>\s*/dev/null", workflow_text):
        _add_repo_issue(result, directory_level, "REP008", "review", "CI output may suppress readable failure detail")
    if re.search(r"(-m\s+['\"]not|--ignore(?:=|\s+)backend/tests)", workflow_text):
        _add_repo_issue(result, directory_level, "REP009", "blocker", "CI marker/defaults may silently exclude required tests")
    if "--reruns" in workflow_text or "pytest-rerunfailures" in workflow_text:
        if "diagnostic" not in workflow_text.lower():
            _add_repo_issue(result, directory_level, "REP010", "failure", "permanent rerun configuration requires diagnostic-only documentation")

    return result


def _add_repo_issue(
    result: CheckResult,
    directory_level: bool,
    rule_id: str,
    severity: Severity,
    message: str,
) -> None:
    if directory_level:
        result.add_issue(rule_id, severity, message)
    else:
        result.add_issue(rule_id, "review", f"repository finding for file-level report: {message}")


def _read_workflows(repo_root: Path) -> list[str]:
    workflow_dir = repo_root / ".github" / "workflows"
    if not workflow_dir.exists():
        return []
    texts = []
    for path in sorted([*workflow_dir.glob("*.yml"), *workflow_dir.glob("*.yaml")]):
        try:
            texts.append(path.read_text())
        except OSError:
            continue
    return texts


def _read_pytest_config(repo_root: Path) -> str:
    texts: list[str] = []
    for name in ("pyproject.toml", "pytest.ini", "setup.cfg", "tox.ini"):
        path = repo_root / name
        if path.exists():
            try:
                texts.append(path.read_text())
            except OSError:
                pass
    return "\n".join(texts)


def _collect_custom_markers(index: StaticIndex) -> set[str]:
    markers: set[str] = set()
    for tree in index.module_trees.values():
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            for decorator in node.decorator_list:
                marker = _marker_name(decorator)
                if marker and marker not in BUILTIN_MARKERS:
                    markers.add(marker)
    return markers


def _marker_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Call):
        return _marker_name(node.func)
    if isinstance(node, ast.Attribute):
        parts = []
        current: ast.AST = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        dotted = ".".join(reversed(parts))
        if dotted.startswith("pytest.mark."):
            return dotted.split(".")[-1]
    return None


def _markers_registered(config_text: str, custom_markers: set[str]) -> bool:
    return all(re.search(rf"^\s*{re.escape(marker)}\s*:", config_text, flags=re.MULTILINE) for marker in custom_markers)


def _has_isolated_db_indicator(workflow_text: str) -> bool:
    return any(
        indicator in workflow_text
        for indicator in (
            "pickup_lane_test_db",
            "pickup-lane-test",
            "DATABASE_URL",
            "_test",
            "postgres",
        )
    )

