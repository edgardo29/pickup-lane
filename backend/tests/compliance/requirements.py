from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .report import CheckResult


REQUIREMENT_ID_RE = re.compile(r"^[A-Z]+[0-9]+-R[0-9]+$")
VALID_REQUIREMENT_STATES = frozenset(
    {
        "required",
        "covered",
        "partial",
        "missing",
        "blocked",
        "deferred",
        "covered_elsewhere",
        "not_applicable",
    }
)
REASON_REQUIRED_STATES = frozenset(
    {
        "partial",
        "missing",
        "blocked",
        "deferred",
        "covered_elsewhere",
        "not_applicable",
    }
)
DEFAULT_REQUIREMENT_DECLARATION_PATH = (
    Path(__file__).resolve().parents[1] / "support" / "requirements" / "en01.json"
)


@dataclass(frozen=True)
class RequirementDeclaration:
    requirement_id: str
    owning_pass: str
    source_controls: tuple[str, ...]
    state: str
    scope: str | None = None
    reason: str | None = None


def load_requirement_declarations(
    path: Path = DEFAULT_REQUIREMENT_DECLARATION_PATH,
) -> tuple[dict[str, RequirementDeclaration], CheckResult]:
    result = CheckResult(target=str(path), scope=None)
    if not path.exists():
        result.add_issue("REQ001", "blocker", "canonical requirement declaration file is missing", str(path))
        return {}, result

    try:
        raw = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        result.add_issue("REQ002", "failure", f"canonical requirement declarations are not valid JSON: {exc}", str(path))
        return {}, result

    declarations = parse_requirement_declarations(raw, result, location=str(path))
    result.summary["Requirement declarations"] = f"{len(declarations)} loaded"
    return declarations, result


def parse_requirement_declarations(
    raw: object,
    result: CheckResult,
    *,
    location: str | None = None,
) -> dict[str, RequirementDeclaration]:
    if not isinstance(raw, dict):
        result.add_issue("REQ002", "failure", "requirement declaration payload must be an object", location)
        return {}
    if raw.get("schema_version") != 1:
        result.add_issue("REQ003", "failure", "requirement declaration schema_version must be 1", location)
    entries = raw.get("requirements")
    if not isinstance(entries, list):
        result.add_issue("REQ004", "failure", "requirements must be a list", location)
        return {}

    declarations: dict[str, RequirementDeclaration] = {}
    seen: set[str] = set()
    for index, entry in enumerate(entries):
        entry_location = f"{location or '<requirements>'}#{index}"
        declaration = _parse_declaration_entry(entry, result, entry_location)
        if declaration is None:
            continue
        if declaration.requirement_id in seen:
            result.add_issue(
                "REQ005",
                "failure",
                f"duplicate canonical requirement declaration: {declaration.requirement_id}",
                entry_location,
            )
            continue
        seen.add(declaration.requirement_id)
        declarations[declaration.requirement_id] = declaration
    return declarations


def valid_requirement_id(requirement_id: str) -> bool:
    return bool(REQUIREMENT_ID_RE.fullmatch(requirement_id))


def _parse_declaration_entry(
    entry: object,
    result: CheckResult,
    location: str,
) -> RequirementDeclaration | None:
    if not isinstance(entry, dict):
        result.add_issue("REQ004", "failure", "requirement declaration must be an object", location)
        return None

    requirement_id = _string_field(entry, "id")
    owning_pass = _string_field(entry, "owning_pass")
    state = _string_field(entry, "state")
    source_controls = _string_list_field(entry, "source_controls")
    scope = entry.get("scope")
    reason = entry.get("reason")

    if not requirement_id or not valid_requirement_id(requirement_id):
        result.add_issue("REQ006", "failure", f"malformed requirement ID: {requirement_id!r}", location)
        return None
    if not owning_pass:
        result.add_issue("REQ007", "failure", f"{requirement_id} requires owning_pass", location)
        return None
    if not source_controls:
        result.add_issue("REQ008", "failure", f"{requirement_id} requires source_controls", location)
        return None
    if state not in VALID_REQUIREMENT_STATES:
        result.add_issue("REQ009", "failure", f"{requirement_id} has unsupported state: {state!r}", location)
        return None
    if state in REASON_REQUIRED_STATES and not (isinstance(reason, str) and reason.strip()):
        result.add_issue("REQ010", "blocker", f"{requirement_id} state {state!r} requires a reason", location)
    if scope is not None and not isinstance(scope, str):
        result.add_issue("REQ011", "failure", f"{requirement_id} scope must be a string when provided", location)
        return None

    return RequirementDeclaration(
        requirement_id=requirement_id,
        owning_pass=owning_pass,
        source_controls=tuple(source_controls),
        state=state,
        scope=scope,
        reason=reason if isinstance(reason, str) else None,
    )


def _string_field(entry: dict[str, Any], key: str) -> str:
    value = entry.get(key)
    return value.strip() if isinstance(value, str) else ""


def _string_list_field(entry: dict[str, Any], key: str) -> tuple[str, ...]:
    value = entry.get(key)
    if not isinstance(value, list):
        return ()
    strings = [item.strip() for item in value if isinstance(item, str) and item.strip()]
    return tuple(strings)
