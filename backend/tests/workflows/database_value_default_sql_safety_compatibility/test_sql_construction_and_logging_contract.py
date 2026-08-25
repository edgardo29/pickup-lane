from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

import backend.services.database_value_sql_safety_policy as value_policy

pytestmark = pytest.mark.no_db_cleanup

_REPO_ROOT = Path(__file__).resolve().parents[4]
_BACKEND_ROOT = _REPO_ROOT / "backend"
_SQLISH_PATTERN = re.compile(
    r"(?i)(\b(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP)\b\s+|\bSET\s+(statement_timeout|lock_timeout|search_path))"
)
_BLOCKED_LOG_TOKENS = (
    "raw_payload",
    "provider_payload",
    "payment_metadata",
    "database_url",
    "connection_string",
    "client_secret",
    "secret_key",
    "password",
    "card_fingerprint",
    "card_last4",
    "credential",
)


def _python_files(*relative_roots: str) -> list[Path]:
    files: list[Path] = []
    for relative_root in relative_roots:
        root = _REPO_ROOT / relative_root
        if root.is_file():
            files.append(root)
            continue
        files.extend(
            path
            for path in root.rglob("*.py")
            if "legacy" not in path.parts and "__pycache__" not in path.parts
        )
    return sorted(files)


def _relative(path: Path) -> str:
    return path.relative_to(_REPO_ROOT).as_posix()


def _call_name(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def _constructor_name(node: ast.Call) -> str | None:
    name = _call_name(node)
    if name == "text":
        return "sqlalchemy.text"
    if name == "literal_column":
        return "sqlalchemy.literal_column"
    if name == "execute":
        return "execute"
    return None


def _literal_or_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return node.id
    return None


def _source_segment(path: Path, node: ast.AST) -> str:
    return ast.get_source_segment(path.read_text(), node) or ""


def _raw_sql_calls(paths: list[Path]) -> set[tuple[str, str, str]]:
    calls: set[tuple[str, str, str]] = set()
    for path in paths:
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            constructor = _constructor_name(node)
            if constructor is None:
                continue
            expression = _literal_or_name(node.args[0])
            if expression is None:
                continue
            if constructor == "execute":
                if _relative(path) == "backend/database.py":
                    constructor = "dbapi.execute"
                elif _relative(path).startswith("backend/alembic/versions/"):
                    constructor = "op.execute"
                else:
                    continue
            if constructor == "dbapi.execute" and _relative(path) != "backend/database.py":
                continue
            calls.add((_relative(path), constructor, expression))
    return calls


def _joined_string_text(node: ast.JoinedStr) -> str:
    return "".join(
        value.value
        for value in node.values
        if isinstance(value, ast.Constant) and isinstance(value.value, str)
    )


def _is_sqlish(value: str) -> bool:
    return bool(_SQLISH_PATTERN.search(value))


@pytest.mark.requirement("WS04-02C-R6", "WS04-02C-R8")
def test_current_production_raw_sql_inventory_matches_policy_allowlist() -> None:
    actual = _raw_sql_calls(
        _python_files(
            "backend/database.py",
            "backend/services",
            "backend/routes",
            "backend/schemas",
        )
    )

    assert actual == value_policy.raw_sql_allowlist_keys()


@pytest.mark.requirement("WS04-02C-R6", "WS04-02C-R8")
def test_production_source_rejects_unsafe_sql_construction_patterns() -> None:
    violations: list[str] = []
    blocked_substrings = (
        "exec_driver_sql(",
        ".from_statement(",
        "search_path",
        "echo=True",
    )

    for path in _python_files(
        "backend/database.py",
        "backend/models",
        "backend/services",
        "backend/routes",
        "backend/schemas",
    ):
        if _relative(path) == "backend/services/database_value_sql_safety_policy.py":
            continue
        source = path.read_text()
        for substring in blocked_substrings:
            if substring in source:
                violations.append(f"{_relative(path)} contains {substring}")

        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.JoinedStr) and _is_sqlish(_joined_string_text(node)):
                violations.append(
                    f"{_relative(path)}:{node.lineno} contains SQL-like f-string"
                )
            if (
                isinstance(node, ast.BinOp)
                and isinstance(node.op, ast.Add)
                and _is_sqlish(_source_segment(path, node))
            ):
                violations.append(
                    f"{_relative(path)}:{node.lineno} contains SQL-like string concatenation"
                )

    assert violations == []


@pytest.mark.requirement("WS04-02C-R6", "WS04-02C-R8")
def test_migration_raw_sql_is_fixed_and_allowlisted_for_value_safety_scope() -> None:
    migrations = _python_files("backend/alembic/versions")
    actual = {
        (source_path, constructor, expression)
        for source_path, constructor, expression in _raw_sql_calls(migrations)
        if constructor == "op.execute"
    }

    assert actual == value_policy.migration_raw_sql_allowlist_keys()

    dynamic_violations: list[str] = []
    for path in migrations:
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or _call_name(node) != "execute":
                continue
            if not node.args or not isinstance(node.args[0], ast.Constant):
                dynamic_violations.append(f"{_relative(path)}:{node.lineno}")
            elif not isinstance(node.args[0].value, str):
                dynamic_violations.append(f"{_relative(path)}:{node.lineno}")

    assert dynamic_violations == []


@pytest.mark.requirement("WS04-02C-R7", "WS04-02C-R8")
def test_repository_logging_does_not_intentionally_emit_sensitive_database_values() -> None:
    violations: list[str] = []
    for path in _python_files(
        "backend/database.py",
        "backend/services",
        "backend/routes",
        "backend/observability",
    ):
        source = path.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (
                isinstance(func, ast.Attribute)
                and func.attr in {"debug", "info", "warning", "error", "exception", "critical"}
            ):
                continue

            segment = _source_segment(path, node).lower()
            for blocked in _BLOCKED_LOG_TOKENS:
                if blocked in segment:
                    violations.append(f"{_relative(path)}:{node.lineno} logs {blocked}")

    assert violations == []
