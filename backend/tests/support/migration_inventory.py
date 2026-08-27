from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class MigrationRevision:
    path: Path
    revision: str
    down_revision: str | tuple[str, ...] | None
    branch_labels: str | tuple[str, ...] | None
    depends_on: str | tuple[str, ...] | None


@dataclass(frozen=True)
class MigrationOperationInventory:
    revision_count: int
    base_revisions: tuple[str, ...]
    head_revisions: tuple[str, ...]
    operation_categories: tuple[str, ...]
    risky_upgrade_findings: tuple[str, ...]


RISKY_UPGRADE_CALLS = frozenset(
    {
        "op.alter_column",
        "op.bulk_insert",
        "op.drop_column",
        "op.drop_constraint",
        "op.drop_index",
        "op.drop_table",
        "op.rename_table",
    }
)
RISKY_SQL_TOKENS = (
    "ALTER TABLE",
    "CREATE INDEX CONCURRENTLY",
    "DELETE ",
    "DROP ",
    "INSERT ",
    "NOT VALID",
    "RENAME ",
    "UPDATE ",
    "VALIDATE CONSTRAINT",
)
_REVIEWED_RAW_SQL_FORMS = {
    "CREATE EXTENSION IF NOT EXISTS PG_TRGM": "extension_setup",
    "CREATE SEQUENCE PLATFORM_NOTICE_GLOBAL_SEQUENCE_SEQ": "sequence_setup",
}


def load_migration_revisions(versions_dir: Path) -> tuple[MigrationRevision, ...]:
    revisions: list[MigrationRevision] = []
    for path in sorted(versions_dir.glob("*.py"), key=lambda candidate: candidate.name):
        tree = ast.parse(path.read_text())
        values = _module_assignments(tree)
        revision = values.get("revision")
        if not isinstance(revision, str) or not revision:
            raise AssertionError(f"{path.name} does not define a valid revision")
        revisions.append(
            MigrationRevision(
                path=path,
                revision=revision,
                down_revision=_revision_value(values.get("down_revision")),
                branch_labels=_revision_value(values.get("branch_labels")),
                depends_on=_revision_value(values.get("depends_on")),
            )
        )
    return tuple(revisions)


def build_migration_operation_inventory(versions_dir: Path) -> MigrationOperationInventory:
    revisions = load_migration_revisions(versions_dir)
    operation_categories: set[str] = set()
    risky_findings: list[str] = []

    for revision in revisions:
        tree = ast.parse(revision.path.read_text())
        upgrade = _function_def(tree, "upgrade")
        if upgrade is None:
            risky_findings.append(f"{revision.path.name}: missing upgrade()")
            continue
        categories, findings = _classify_upgrade_operations(revision.path, upgrade)
        operation_categories.update(categories)
        risky_findings.extend(findings)

    return MigrationOperationInventory(
        revision_count=len(revisions),
        base_revisions=_base_revisions(revisions),
        head_revisions=_head_revisions(revisions),
        operation_categories=tuple(sorted(operation_categories)),
        risky_upgrade_findings=tuple(risky_findings),
    )


def assert_linear_revision_chain(revisions: tuple[MigrationRevision, ...]) -> None:
    revision_ids = [revision.revision for revision in revisions]
    if len(revision_ids) != len(set(revision_ids)):
        raise AssertionError("Alembic revision IDs must be unique")

    revision_set = set(revision_ids)
    bases = _base_revisions(revisions)
    heads = _head_revisions(revisions)
    if len(bases) != 1:
        raise AssertionError(f"expected one base revision; got {bases!r}")
    if len(heads) != 1:
        raise AssertionError(f"expected one head revision; got {heads!r}")

    for revision in revisions:
        if revision.branch_labels is not None:
            raise AssertionError(f"{revision.path.name} has unexpected branch_labels")
        if revision.depends_on is not None:
            raise AssertionError(f"{revision.path.name} has unexpected depends_on")
        for parent in _parents(revision.down_revision):
            if parent not in revision_set:
                raise AssertionError(
                    f"{revision.path.name} references missing parent {parent!r}"
                )


def _module_assignments(tree: ast.Module) -> dict[str, object]:
    values: dict[str, object] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in {
                "revision",
                "down_revision",
                "branch_labels",
                "depends_on",
            }:
                values[target.id] = ast.literal_eval(node.value)
    return values


def _revision_value(value: object) -> str | tuple[str, ...] | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, tuple) and all(isinstance(item, str) for item in value):
        return value
    raise AssertionError(f"unsupported Alembic revision metadata value: {value!r}")


def _parents(value: str | tuple[str, ...] | None) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    return value


def _base_revisions(revisions: tuple[MigrationRevision, ...]) -> tuple[str, ...]:
    return tuple(
        revision.revision for revision in revisions if revision.down_revision is None
    )


def _head_revisions(revisions: tuple[MigrationRevision, ...]) -> tuple[str, ...]:
    parent_ids = {
        parent
        for revision in revisions
        for parent in _parents(revision.down_revision)
    }
    return tuple(
        revision.revision for revision in revisions if revision.revision not in parent_ids
    )


def _function_def(tree: ast.Module, name: str) -> ast.FunctionDef | None:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def _classify_upgrade_operations(
    path: Path,
    upgrade: ast.FunctionDef,
) -> tuple[set[str], list[str]]:
    categories: set[str] = set()
    findings: list[str] = []

    for node in ast.walk(upgrade):
        if isinstance(node, ast.Call):
            call_name = _call_name(node.func)
            if call_name == "op.create_table":
                categories.add("table_creation")
            elif call_name == "op.create_index":
                categories.add("ordinary_index_creation")
            elif call_name == "op.create_unique_constraint":
                categories.add("constraint_creation")
            elif call_name == "op.execute":
                categories.add(_classify_raw_sql_call(node))
                findings.extend(_unsafe_sql_findings(path, node))
            elif call_name in RISKY_UPGRADE_CALLS:
                findings.append(f"{path.name}: upgrade uses {call_name}")
            elif call_name.endswith(".create") and _call_contains_sequence(node):
                categories.add("sequence_setup")
            elif call_name.endswith("Constraint"):
                categories.add("constraint_creation")

        if isinstance(node, ast.JoinedStr):
            findings.append(f"{path.name}: upgrade contains f-string SQL or dynamic text")

    return categories, findings


def _classify_raw_sql_call(node: ast.Call) -> str:
    sql = _first_constant_string(node)
    if sql is None:
        return "raw_sql_expression"
    normalized = _normalized_sql(sql)
    reviewed_category = _REVIEWED_RAW_SQL_FORMS.get(normalized)
    if reviewed_category is not None:
        return reviewed_category
    return "raw_sql_expression"


def _unsafe_sql_findings(path: Path, node: ast.Call) -> tuple[str, ...]:
    sql = _first_constant_string(node)
    if sql is None:
        return (f"{path.name}: op.execute uses non-literal SQL",)
    normalized = _normalized_sql(sql)
    if normalized in _REVIEWED_RAW_SQL_FORMS:
        return ()

    findings = [
        f"{path.name}: op.execute contains {token.strip()}"
        for token in RISKY_SQL_TOKENS
        if token in normalized
    ]
    if "CREATE EXTENSION" in normalized:
        findings.append(f"{path.name}: op.execute uses unreviewed extension SQL")
    if "CREATE SEQUENCE" in normalized:
        findings.append(f"{path.name}: op.execute uses unreviewed sequence SQL")
    return tuple(findings)


def _normalized_sql(sql: str) -> str:
    return " ".join(sql.strip().rstrip(";").upper().split())


def _first_constant_string(node: ast.Call) -> str | None:
    if not node.args:
        return None
    first_arg = node.args[0]
    if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
        return first_arg.value
    return None


def _call_contains_sequence(node: ast.Call) -> bool:
    return any(
        isinstance(child, ast.Call) and _call_name(child.func).endswith("Sequence")
        for child in ast.walk(node)
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
    if isinstance(node, ast.Call):
        return _call_name(node.func)
    return ""
