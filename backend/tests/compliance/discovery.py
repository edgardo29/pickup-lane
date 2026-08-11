from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .report import CheckResult
from .requirements import RequirementDeclaration, valid_requirement_id
from .targeting import Target


@dataclass(frozen=True)
class RequirementUsage:
    requirement_id: str
    nodeid: str
    path: Path


@dataclass(frozen=True)
class RequirementCollection:
    nodeids: tuple[str, ...]
    usages: tuple[RequirementUsage, ...]


def collect_requirement_metadata(
    target: Target,
    declarations: dict[str, RequirementDeclaration],
) -> tuple[RequirementCollection, CheckResult]:
    result = CheckResult(target=target.display, scope=target.scope)
    marker_index = _collect_marker_index(target, result)
    nodeids = _collect_pytest_nodeids(target, result)

    usages: list[RequirementUsage] = []
    for nodeid in nodeids:
        marker_key = _nodeid_marker_key(nodeid)
        requirement_ids = marker_index.get(marker_key, ())
        if not requirement_ids:
            result.add_issue(
                "META001",
                "failure",
                "trusted test is missing pytest requirement metadata",
                nodeid,
            )
            continue
        for requirement_id in requirement_ids:
            if not valid_requirement_id(requirement_id):
                result.add_issue(
                    "META002",
                    "failure",
                    f"malformed pytest requirement ID: {requirement_id!r}",
                    nodeid,
                )
                continue
            if requirement_id not in declarations:
                result.add_issue(
                    "META003",
                    "failure",
                    f"unknown pytest requirement ID: {requirement_id}",
                    nodeid,
                )
                continue
            usages.append(
                RequirementUsage(
                    requirement_id=requirement_id,
                    nodeid=nodeid,
                    path=target.repo_root / nodeid.split("::", 1)[0],
                )
            )

    result.summary["Collected pytest nodes"] = str(len(nodeids))
    result.summary["Requirement metadata links"] = str(len(usages))
    return RequirementCollection(tuple(nodeids), tuple(usages)), result


def _collect_marker_index(
    target: Target,
    result: CheckResult,
) -> dict[str, tuple[str, ...]]:
    marker_index: dict[str, tuple[str, ...]] = {}
    for file_path in target.files:
        try:
            tree = ast.parse(file_path.read_text())
        except SyntaxError as exc:
            result.add_issue("DISC001", "failure", f"could not parse trusted test file: {exc}", str(file_path))
            continue
        relative_file = file_path.relative_to(target.repo_root).as_posix()
        module_requirements = _requirement_ids_from_pytestmark(tree.body, result, relative_file)
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
                marker_index[f"{relative_file}::{node.name}"] = _merge_requirement_ids(
                    module_requirements,
                    _requirement_ids_from_decorators(node.decorator_list, result, f"{relative_file}::{node.name}"),
                )
            elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
                class_requirements = _merge_requirement_ids(
                    module_requirements,
                    _requirement_ids_from_decorators(node.decorator_list, result, f"{relative_file}::{node.name}"),
                )
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name.startswith("test_"):
                        marker_index[f"{relative_file}::{node.name}::{child.name}"] = _merge_requirement_ids(
                            class_requirements,
                            _requirement_ids_from_decorators(
                                child.decorator_list,
                                result,
                                f"{relative_file}::{node.name}::{child.name}",
                            ),
                        )
    return marker_index


def _collect_pytest_nodeids(target: Target, result: CheckResult) -> tuple[str, ...]:
    command = [
        sys.executable,
        "-m",
        "pytest",
        "--collect-only",
        "-q",
        *[str(path.relative_to(target.repo_root)) for path in target.files],
    ]
    env = os.environ.copy()
    env.setdefault("APP_ENV", "test")
    env["DATABASE_URL"] = ""
    env.setdefault("INBOX_TOKEN_SECRET", "synthetic-inbox-test-token")
    env.setdefault("STRIPE_SECRET_KEY", "synthetic-stripe-secret-key")
    env.setdefault("STRIPE_PUBLISHABLE_KEY", "synthetic-stripe-publishable-key")
    env.setdefault("STRIPE_WEBHOOK_SECRET", "synthetic-stripe-webhook-secret")
    env["PYTHONPATH"] = os.pathsep.join(
        value
        for value in (
            str(target.repo_root),
            str(target.tests_root),
            env.get("PYTHONPATH", ""),
        )
        if value
    )
    completed = subprocess.run(
        command,
        cwd=target.repo_root,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    result.commands_run.append(" ".join(command))
    if completed.returncode != 0:
        result.add_issue(
            "DISC002",
            "blocker",
            "pytest collection failed; checker cannot generate exact test references",
            _safe_collection_output(completed.stdout, completed.stderr),
        )
        return ()
    return tuple(
        _normalize_nodeid(line.strip())
        for line in completed.stdout.splitlines()
        if _looks_like_nodeid(line.strip())
    )


def _requirement_ids_from_pytestmark(
    body: Iterable[ast.stmt],
    result: CheckResult,
    location: str,
) -> tuple[str, ...]:
    requirement_ids: list[str] = []
    for node in body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "pytestmark" for target in node.targets):
            continue
        for marker in _iter_marker_nodes(node.value):
            requirement_ids.extend(_requirement_ids_from_marker(marker, result, location))
    return tuple(dict.fromkeys(requirement_ids))


def _requirement_ids_from_decorators(
    decorators: Iterable[ast.expr],
    result: CheckResult,
    location: str,
) -> tuple[str, ...]:
    requirement_ids: list[str] = []
    for decorator in decorators:
        requirement_ids.extend(_requirement_ids_from_marker(decorator, result, location))
    return tuple(dict.fromkeys(requirement_ids))


def _requirement_ids_from_marker(
    marker: ast.AST,
    result: CheckResult,
    location: str,
) -> tuple[str, ...]:
    if not isinstance(marker, ast.Call) or _call_name(marker.func) not in {
        "pytest.mark.requirement",
        "mark.requirement",
    }:
        return ()
    if not marker.args:
        result.add_issue("META004", "failure", "requirement marker requires at least one string ID", location)
        return ()
    ids: list[str] = []
    for arg in marker.args:
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            ids.append(arg.value)
        else:
            result.add_issue("META004", "failure", "requirement marker arguments must be string literals", location)
    return tuple(ids)


def _iter_marker_nodes(node: ast.AST) -> Iterable[ast.AST]:
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


def _merge_requirement_ids(*groups: tuple[str, ...]) -> tuple[str, ...]:
    merged: list[str] = []
    for group in groups:
        merged.extend(group)
    return tuple(dict.fromkeys(merged))


def _nodeid_marker_key(nodeid: str) -> str:
    if ".py::" in nodeid:
        path_part, test_part = nodeid.split(".py::", 1)
        return f"{path_part}.py::{test_part.split('[', 1)[0]}"
    if "::" not in nodeid:
        return re.sub(r"\[[^\]]*\]$", "", nodeid)
    prefix, final_segment = nodeid.rsplit("::", 1)
    return f"{prefix}::{final_segment.split('[', 1)[0]}"


def _looks_like_nodeid(line: str) -> bool:
    return line.endswith(".py") or "::" in line and ".py::" in line


def _normalize_nodeid(nodeid: str) -> str:
    if nodeid.startswith("tests/"):
        return f"backend/{nodeid}"
    return nodeid


def _safe_collection_output(stdout: str, stderr: str) -> str:
    output = "\n".join(part for part in (stdout.strip(), stderr.strip()) if part)
    if not output:
        return "<no pytest collection output>"
    return output[-1000:]
