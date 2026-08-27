from __future__ import annotations

import ast
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.tests.support.environment_safety import (
    EnvironmentSafetyError,
    validate_dedicated_test_database_url,
)

from .report import CheckResult
from .targeting import Target


DEFAULT_SUITE_POLICY_PATH = Path(__file__).resolve().parents[1] / "support" / "suite_policy.json"
REQUIRED_MARKERS = frozenset(
    {"requirement", "suite_type", "no_db_cleanup", "migration_lifecycle"}
)
NETWORK_CALL_PREFIXES = (
    "requests.get",
    "requests.post",
    "requests.put",
    "requests.patch",
    "requests.delete",
    "httpx.get",
    "httpx.post",
    "httpx.put",
    "httpx.patch",
    "httpx.delete",
    "urllib.request.urlopen",
    "socket.create_connection",
    "stripe.",
)
RETRY_PATTERNS = (
    "--reruns",
    "pytest-rerunfailures",
)


@dataclass(frozen=True)
class SuitePolicy:
    suite_types: dict[str, dict[str, object]]
    trusted_roots: dict[str, str]
    untrusted_application_roots: tuple[str, ...]
    historical_roots: tuple[str, ...]


def load_suite_policy(path: Path = DEFAULT_SUITE_POLICY_PATH) -> tuple[SuitePolicy | None, CheckResult]:
    result = CheckResult(target=str(path), scope=None)
    if not path.exists():
        result.add_issue("SUITE001", "blocker", "suite policy file is missing", str(path))
        return None, result
    try:
        raw = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        result.add_issue("SUITE002", "failure", f"suite policy is not valid JSON: {exc}", str(path))
        return None, result
    policy = parse_suite_policy(raw, result, location=str(path))
    if policy is not None:
        result.summary["Suite policy"] = f"{len(policy.trusted_roots)} trusted root(s)"
    return policy, result


def parse_suite_policy(raw: object, result: CheckResult, *, location: str | None = None) -> SuitePolicy | None:
    if not isinstance(raw, dict):
        result.add_issue("SUITE002", "failure", "suite policy payload must be an object", location)
        return None
    if raw.get("schema_version") != 1:
        result.add_issue("SUITE003", "failure", "suite policy schema_version must be 1", location)

    suite_types = raw.get("suite_types")
    trusted_roots = raw.get("trusted_roots")
    untrusted = raw.get("untrusted_application_roots", [])
    historical = raw.get("historical_roots", [])
    if not isinstance(suite_types, dict) or not suite_types:
        result.add_issue("SUITE004", "failure", "suite_types must be a non-empty object", location)
        return None
    if not {"ordinary", "full_stack", "provider_contract"}.issubset(suite_types):
        result.add_issue("SUITE004", "failure", "suite_types must define ordinary, full_stack, and provider_contract", location)
    if not isinstance(trusted_roots, dict) or not trusted_roots:
        result.add_issue("SUITE005", "failure", "trusted_roots must be a non-empty object", location)
        return None
    for root, suite_type in trusted_roots.items():
        if not isinstance(root, str) or not isinstance(suite_type, str) or suite_type not in suite_types:
            result.add_issue("SUITE005", "failure", f"invalid trusted root mapping: {root!r} -> {suite_type!r}", location)
    for suite_type, config in suite_types.items():
        if not isinstance(config, dict):
            result.add_issue("SUITE004", "failure", f"suite type {suite_type!r} must map to an object", location)
            continue
        if config.get("allows_production_resources") is not False:
            result.add_issue("SUITE006", "failure", f"suite type {suite_type!r} must forbid production resources", location)
    return SuitePolicy(
        suite_types={str(key): dict(value) for key, value in suite_types.items() if isinstance(value, dict)},
        trusted_roots={str(key): str(value) for key, value in trusted_roots.items()},
        untrusted_application_roots=tuple(item for item in untrusted if isinstance(item, str)),
        historical_roots=tuple(item for item in historical if isinstance(item, str)),
    )


def analyze_policy(target: Target, policy: SuitePolicy | None = None) -> CheckResult:
    result = CheckResult(target=target.display, scope=target.scope)
    policy = policy or load_suite_policy()[0]
    if policy is None:
        result.add_issue("SUITE001", "blocker", "suite policy could not be loaded")
        return result

    _check_pytest_marker_config(target.repo_root, result)
    _check_retry_policy_config(target.repo_root, result)
    _check_database_environment(result)

    for file_path in target.files:
        relative = file_path.relative_to(target.tests_root)
        root_name = relative.parts[0]
        suite_type = policy.trusted_roots.get(root_name)
        if suite_type is None:
            result.add_issue("SUITE007", "failure", "trusted file has no suite policy root mapping", str(relative))
            continue
        _check_test_file_policy(file_path, target, suite_type, result)

    result.summary["Policy files checked"] = str(len(target.files))
    return result


def _check_pytest_marker_config(repo_root: Path, result: CheckResult) -> None:
    config_text = _read_pytest_config(repo_root)
    for marker in sorted(REQUIRED_MARKERS):
        if not re.search(rf"^\s*{re.escape(marker)}(?:\(|\s*:)", config_text, flags=re.MULTILINE):
            result.add_issue("CFG001", "failure", f"pytest marker is not registered: {marker}")
    if "--strict-markers" not in config_text:
        result.add_issue("CFG002", "failure", "pytest must run with --strict-markers")


def _check_retry_policy_config(repo_root: Path, result: CheckResult) -> None:
    config_text = _read_pytest_config(repo_root)
    for pattern in RETRY_PATTERNS:
        if pattern in config_text:
            result.add_issue("FLAKE001", "failure", f"ordinary pytest config must not enable silent retry behavior: {pattern}")


def _check_database_environment(result: CheckResult) -> None:
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        return
    try:
        validate_dedicated_test_database_url(database_url)
    except EnvironmentSafetyError as exc:
        result.add_issue("DB001", "failure", str(exc))


def _check_test_file_policy(
    file_path: Path,
    target: Target,
    suite_type: str,
    result: CheckResult,
) -> None:
    try:
        tree = ast.parse(file_path.read_text())
    except SyntaxError:
        return
    relative = str(file_path.relative_to(target.repo_root))
    declared_suite_types = _declared_suite_types(tree)
    for declared in declared_suite_types:
        if declared != suite_type:
            result.add_issue(
                "SUITE008",
                "failure",
                f"suite_type marker {declared!r} conflicts with owning suite {suite_type!r}",
                relative,
            )

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            call_name = _call_name(node.func)
            if call_name in {"time.sleep", "sleep"}:
                result.add_issue("BROWSER001", "failure", "sleep-based synchronization is not allowed", relative)
            if suite_type == "ordinary" and any(call_name.startswith(prefix) for prefix in NETWORK_CALL_PREFIXES):
                result.add_issue(
                    "NET001",
                    "failure",
                    "ordinary deterministic tests must not make direct provider/network calls",
                    relative,
                )
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if _looks_like_production_secret(node.value):
                result.add_issue(
                    "DATA001",
                    "failure",
                    "trusted tests must not contain production-looking provider credentials",
                    relative,
                )


def _declared_suite_types(tree: ast.Module) -> tuple[str, ...]:
    suite_types: list[str] = []
    for node in ast.walk(tree):
        marker_nodes: list[ast.AST] = []
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            marker_nodes.extend(node.decorator_list)
        elif isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "pytestmark" for target in node.targets):
            marker_nodes.extend(_iter_marker_nodes(node.value))
        for marker in marker_nodes:
            if isinstance(marker, ast.Call) and _call_name(marker.func) in {"pytest.mark.suite_type", "mark.suite_type"}:
                if marker.args and isinstance(marker.args[0], ast.Constant) and isinstance(marker.args[0].value, str):
                    suite_types.append(marker.args[0].value)
    return tuple(suite_types)


def _read_pytest_config(repo_root: Path) -> str:
    texts: list[str] = []
    for path in (
        repo_root / "setup.cfg",
        repo_root / "pytest.ini",
        repo_root / "pyproject.toml",
        repo_root / "tox.ini",
        repo_root / "backend" / "setup.cfg",
        repo_root / "backend" / "pytest.ini",
        repo_root / "backend" / "pyproject.toml",
    ):
        if path.exists():
            texts.append(path.read_text())
    return "\n".join(texts)


def _iter_marker_nodes(node: ast.AST):
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        yield from node.elts
    else:
        yield node


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Call):
        return _call_name(node.func)
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


def _looks_like_production_secret(value: str) -> bool:
    return bool(re.search(r"\b(sk|rk|pk|whsec)_live_", value))
