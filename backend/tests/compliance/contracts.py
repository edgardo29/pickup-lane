from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .report import CheckResult
from .targeting import Target


MANDATORY_SCENARIOS: tuple[tuple[str, str], ...] = (
    ("normal", "Valid request succeeds."),
    ("normal", "Response matches the final API contract."),
    ("normal", "Expected database state is produced."),
    ("validation", "Missing required fields."),
    ("validation", "Invalid types."),
    ("validation", "Invalid enum values."),
    ("validation", "Invalid date or timestamp formats."),
    ("validation", "Values below or above allowed limits."),
    ("validation", "Conflicting fields."),
    ("validation", "Malformed cursor or token."),
    ("authentication", "Anonymous request where authentication is required."),
    ("authentication", "Valid authenticated request."),
    ("authentication", "Invalid or malformed credentials."),
    ("authentication", "Expired credentials when relevant."),
    ("authorization_visibility", "Owner or host access."),
    ("authorization_visibility", "Participant or relationship-based access."),
    ("authorization_visibility", "Stale, expired, cancelled, removed, or no-longer-active relationship denial."),
    ("authorization_visibility", "Unrelated-user denial."),
    ("authorization_visibility", "Admin or privileged-role access."),
    ("authorization_visibility", "Invalid privileged actor denial, including inactive, suspended, deleted, or revoked actors when those states exist."),
    ("authorization_visibility", "Horizontal authorization using another user's resource ID."),
    ("authorization_visibility", "Vertical authorization using a lower-privilege user."),
    ("authorization_visibility", "Hidden or private resource behavior."),
    ("authorization_visibility", "Hidden or private resource enumeration through detail, list, lookup, and helper routes that accept resource identifiers."),
    ("authorization_visibility", "Correct 401, 403, or 404 response according to policy."),
    ("authorization_visibility", "Required privacy and cache headers."),
    ("state_lifecycle", "Allowed state transitions."),
    ("state_lifecycle", "Prohibited state transitions."),
    ("state_lifecycle", "Repeated transition attempts."),
    ("state_lifecycle", "Terminal-state behavior."),
    ("state_lifecycle", "Historical rows not granting active privileges."),
    ("dates_times_expiration", "Before the boundary."),
    ("dates_times_expiration", "At the exact boundary."),
    ("dates_times_expiration", "After the boundary."),
    ("dates_times_expiration", "UTC handling."),
    ("dates_times_expiration", "Configured timezone behavior."),
    ("dates_times_expiration", "Daylight-saving transitions when relevant."),
    ("dates_times_expiration", "Expired records that cleanup has not processed yet."),
    ("capacity_concurrency", "Empty capacity."),
    ("capacity_concurrency", "One remaining spot."),
    ("capacity_concurrency", "Exactly full."),
    ("capacity_concurrency", "Over-capacity defensive behavior."),
    ("capacity_concurrency", "Expired temporary holds."),
    ("capacity_concurrency", "Multiple participant rows under one booking."),
    ("capacity_concurrency", "Competing requests for the final spot."),
    ("capacity_concurrency", "Required transaction and row-lock behavior."),
    ("pagination_sorting_counts", "First page."),
    ("pagination_sorting_counts", "Middle page."),
    ("pagination_sorting_counts", "Final page."),
    ("pagination_sorting_counts", "Exact-limit page."),
    ("pagination_sorting_counts", "Empty page."),
    ("pagination_sorting_counts", "Stable ordering when primary sort values match."),
    ("pagination_sorting_counts", "Cursor mismatch."),
    ("pagination_sorting_counts", "Invalid cursor."),
    ("pagination_sorting_counts", "No duplicates across pages."),
    ("pagination_sorting_counts", "Aggregate totals, grouped counts, summaries, and available-count fields use the same authorization, visibility, lifecycle, cutoff, and status filters as the item query."),
    ("external_webhooks", "Successful provider response."),
    ("external_webhooks", "Provider failure."),
    ("external_webhooks", "Timeout or exception."),
    ("external_webhooks", "Duplicate webhook."),
    ("external_webhooks", "Out-of-order webhook."),
    ("external_webhooks", "Late webhook."),
    ("external_webhooks", "Invalid webhook signature."),
    ("external_webhooks", "Idempotent retry behavior."),
    ("regression", "Every confirmed production or pre-production bug has a regression test or written exception."),
)

VALID_REQUIREMENT_STATUSES = {
    "covered",
    "partial",
    "missing",
    "covered_elsewhere",
    "not_applicable",
}
VALID_CLASSIFICATIONS = {
    "covered",
    "excluded_by_policy",
    "not_relevant",
    "missing_test",
}
VALID_APPLICABILITY = {"required", "not_relevant", "covered_elsewhere"}
VALID_REVIEW_STATUSES = {"confirmed", "unresolved"}
VALID_EFFECT_PHASES = {"successful_mutation", "rejected_mutation", "idempotency", "rollback"}
VALID_EFFECT_KINDS = {
    "row_exists",
    "row_absent",
    "row_count",
    "field_equals",
    "field_changed",
    "field_unchanged",
    "no_new_rows",
    "count_delta",
    "timestamp_set",
    "relationship_exists",
    "external_call_count",
}


@dataclass(frozen=True)
class Contract:
    path: Path
    data: dict[str, Any]
    scoped_data: dict[str, Any]


def load_contract(target: Target, collected_refs: set[str]) -> tuple[Contract | None, CheckResult]:
    result = CheckResult(target=str(target.relative_path), scope=target.scope)  # type: ignore[arg-type]
    contract_path = target.contract_dir / "_backend_test_contract.py"
    if not contract_path.exists():
        result.add_issue("CON001", "failure", "missing _backend_test_contract.py", str(contract_path))
        return None, result

    data = _parse_literal_contract(contract_path, result)
    if data is None:
        return None, result

    scoped = _scope_contract(data, target)
    contract = Contract(path=contract_path, data=data, scoped_data=scoped)
    _validate_schema(contract, target, collected_refs, result)
    _summarize_contract(contract, result)
    return contract, result


def _parse_literal_contract(path: Path, result: CheckResult) -> dict[str, Any] | None:
    try:
        module = ast.parse(path.read_text())
    except SyntaxError as exc:
        result.add_issue("CON002", "failure", f"contract is not valid Python: {exc}", str(path))
        return None

    body = [node for node in module.body if not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str))]
    if len(body) != 1 or not isinstance(body[0], ast.Assign):
        result.add_issue("CON002", "failure", "contract must contain exactly one literal CONTRACT assignment", str(path))
        return None
    assignment = body[0]
    if len(assignment.targets) != 1 or not isinstance(assignment.targets[0], ast.Name) or assignment.targets[0].id != "CONTRACT":
        result.add_issue("CON002", "failure", "contract assignment must target CONTRACT", str(path))
        return None
    try:
        value = ast.literal_eval(assignment.value)
    except Exception as exc:  # noqa: BLE001 - literal_eval error types vary.
        result.add_issue("CON002", "failure", f"contract must be literal-only: {exc}", str(path))
        return None
    if not isinstance(value, dict):
        result.add_issue("CON002", "failure", "CONTRACT must be a dictionary", str(path))
        return None
    return value


def _scope_contract(data: dict[str, Any], target: Target) -> dict[str, Any]:
    if target.scope == "directory":
        return data
    filename = target.path.name

    def refs_entry_applies(entry: dict[str, Any]) -> bool:
        refs = _entry_refs(entry)
        return any(ref.split("::", 1)[0] == filename for ref in refs)

    scoped = dict(data)
    for key in (
        "requirements",
        "state_matrices",
        "scenarios",
        "ownership",
        "effects",
        "constraints",
        "time_boundaries",
        "clock_controls",
        "mutation_targets",
    ):
        value = data.get(key, [])
        if isinstance(value, list):
            scoped[key] = [entry for entry in value if isinstance(entry, dict) and refs_entry_applies(entry)]
    return scoped


def _entry_refs(entry: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    if isinstance(entry.get("test_ref"), str):
        refs.append(entry["test_ref"])
    if isinstance(entry.get("test_refs"), list):
        refs.extend(ref for ref in entry["test_refs"] if isinstance(ref, str))
    for child_key in ("classifications",):
        children = entry.get(child_key)
        if isinstance(children, list):
            for child in children:
                if isinstance(child, dict):
                    refs.extend(_entry_refs(child))
    return refs


def _validate_schema(contract: Contract, target: Target, collected_refs: set[str], result: CheckResult) -> None:
    data = contract.scoped_data
    full_data = contract.data
    if data.get("schema_version") != 1:
        result.add_issue("CON003", "failure", "unsupported or missing schema_version")

    review = full_data.get("review")
    if not isinstance(review, dict):
        result.add_issue("CON004", "failure", "review section is required")
    else:
        sources = review.get("sources")
        if not isinstance(sources, list) or not sources:
            result.add_issue("CON004", "failure", "review.sources must list finalized sources")
        else:
            for source in sources:
                if not isinstance(source, dict) or not source.get("id") or not source.get("kind") or not source.get("summary"):
                    result.add_issue("CON004", "failure", "each source needs id, kind, and summary")
                    continue
                source_path = source.get("path")
                if isinstance(source_path, str):
                    path = target.repo_root / source_path
                    if not path.exists():
                        result.add_issue("CON004", "blocker", f"source path does not exist: {source_path}")
        for conflict in review.get("conflicts", []) if isinstance(review.get("conflicts"), list) else []:
            if conflict.get("status") == "unresolved":
                result.add_issue("CON005", "blocker", f"unresolved conflict: {conflict.get('summary', conflict.get('id'))}")
            elif conflict.get("status") == "resolved":
                if not conflict.get("resolution"):
                    result.add_issue("CON005", "failure", "resolved conflict requires resolution")
            else:
                result.add_issue("CON005", "failure", "conflict status must be resolved or unresolved")
        for stop in review.get("stop_conditions", []) if isinstance(review.get("stop_conditions"), list) else []:
            if stop.get("status") == "unresolved":
                result.add_issue("CON005", "blocker", f"unresolved stop condition: {stop.get('summary', stop.get('id'))}")
            elif stop.get("status") == "resolved":
                pass
            else:
                result.add_issue("CON005", "failure", "stop condition status must be resolved or unresolved")

    _validate_requirements(data.get("requirements"), collected_refs, result)
    _validate_state_matrices(data.get("state_matrices"), collected_refs, contract.path, result)
    _validate_scenarios(data.get("scenarios"), collected_refs, result)
    _validate_ownership(data.get("ownership"), collected_refs, result)
    _validate_effects(data.get("effects"), collected_refs, result)
    _validate_constraints(data.get("constraints"), collected_refs, contract.path, result)
    _validate_time_boundaries(data.get("time_boundaries"), collected_refs, result)
    _validate_clock_controls(data.get("clock_controls", []), collected_refs, result)
    _validate_review_flags(data.get("review_flags"), result)
    _validate_gaps(data.get("gaps"), target, result)


def _summarize_contract(contract: Contract, result: CheckResult) -> None:
    data = contract.scoped_data
    full_data = contract.data
    review = full_data.get("review") if isinstance(full_data.get("review"), dict) else {}
    sources = _as_list(review.get("sources", []) if isinstance(review, dict) else [])
    source_ids = [str(source.get("id")) for source in sources if isinstance(source, dict) and source.get("id")]
    result.completion["Sources Reviewed"] = _count_and_ids(source_ids)

    requirements = _as_list(data.get("requirements", []))
    requirement_ids = [str(entry.get("id")) for entry in requirements if isinstance(entry, dict) and entry.get("id")]
    requirement_statuses: dict[str, int] = {}
    for entry in requirements:
        if isinstance(entry, dict):
            status = str(entry.get("status"))
            requirement_statuses[status] = requirement_statuses.get(status, 0) + 1
    result.completion["Requirement Coverage"] = (
        f"{_count_and_ids(requirement_ids)}; statuses: {_format_counts(requirement_statuses)}"
    )

    matrices = _as_list(data.get("state_matrices", []))
    matrix_ids = [str(entry.get("id")) for entry in matrices if isinstance(entry, dict) and entry.get("id")]
    value_count = sum(
        len(entry.get("classifications", []))
        for entry in matrices
        if isinstance(entry, dict) and isinstance(entry.get("classifications"), list)
    )
    result.completion["Enum And State Matrix"] = (
        f"{len(matrix_ids)} matrix/matrices, {value_count} classified value(s); ids: {_ids(matrix_ids)}"
    )

    scenarios = _as_list(data.get("scenarios", []))
    scenario_ids = [str(entry.get("id")) for entry in scenarios if isinstance(entry, dict) and entry.get("id")]
    scenario_counts: dict[str, int] = {}
    for entry in scenarios:
        if isinstance(entry, dict):
            applicability = str(entry.get("applicability"))
            scenario_counts[applicability] = scenario_counts.get(applicability, 0) + 1
    result.completion["Scenario Coverage"] = (
        f"{_count_and_ids(scenario_ids)}; applicability: {_format_counts(scenario_counts)}"
    )

    ownership = _as_list(data.get("ownership", []))
    ownership_ids = [str(_entry_refs(entry)[0]) for entry in ownership if isinstance(entry, dict) and _entry_refs(entry)]
    result.completion["Ownership Decisions"] = _count_and_ids(ownership_ids)

    effects = _as_list(data.get("effects", []))
    constraints = _as_list(data.get("constraints", []))
    effect_ids = [str(entry.get("id")) for entry in effects if isinstance(entry, dict) and entry.get("id")]
    constraint_ids = [str(entry.get("id")) for entry in constraints if isinstance(entry, dict) and entry.get("id")]
    result.completion["Assertion Review"] = (
        f"{len(effect_ids)} effect(s): {_ids(effect_ids)}; {len(constraint_ids)} constraint(s): {_ids(constraint_ids)}"
    )

    boundaries = _as_list(data.get("time_boundaries", []))
    boundary_ids = [str(entry.get("id")) for entry in boundaries if isinstance(entry, dict) and entry.get("id")]
    result.completion["Time Control"] = _count_and_ids(boundary_ids)

    clock_controls = _as_list(data.get("clock_controls", []))
    clock_control_ids = [str(entry.get("id")) for entry in clock_controls if isinstance(entry, dict) and entry.get("id")]
    result.completion["Captured Clock Controls"] = _count_and_ids(clock_control_ids)

    gaps = _as_list(data.get("gaps", []))
    gap_ids = [str(entry.get("id")) for entry in gaps if isinstance(entry, dict) and entry.get("id")]
    gap_counts: dict[str, int] = {}
    for entry in gaps:
        if isinstance(entry, dict):
            status = str(entry.get("status"))
            gap_counts[status] = gap_counts.get(status, 0) + 1
    result.completion["Remaining Gaps"] = (
        f"{_count_and_ids(gap_ids)}; statuses: {_format_counts(gap_counts)}"
    )

    conflicts = _as_list(review.get("conflicts", []) if isinstance(review, dict) else [])
    conflict_ids = [str(entry.get("id")) for entry in conflicts if isinstance(entry, dict) and entry.get("id")]
    conflict_counts: dict[str, int] = {}
    for entry in conflicts:
        if isinstance(entry, dict):
            status = str(entry.get("status"))
            conflict_counts[status] = conflict_counts.get(status, 0) + 1
    result.completion["Conflicts"] = (
        f"{_count_and_ids(conflict_ids)}; statuses: {_format_counts(conflict_counts)}"
    )


def _count_and_ids(ids: list[str]) -> str:
    return f"{len(ids)} item(s); ids: {_ids(ids)}"


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _ids(ids: list[str]) -> str:
    return ", ".join(ids) if ids else "none"


def _format_counts(counts: dict[str, int]) -> str:
    return ", ".join(f"{key}={counts[key]}" for key in sorted(counts)) if counts else "none"


def _validate_requirements(requirements: Any, collected_refs: set[str], result: CheckResult) -> None:
    if not isinstance(requirements, list) or not requirements:
        result.add_issue("CON006", "blocker", "requirements map is required")
        return
    for req in requirements:
        if not isinstance(req, dict) or not req.get("id") or not req.get("source_id") or not req.get("behavior"):
            result.add_issue("CON006", "failure", "each requirement needs id, source_id, and behavior")
            continue
        status = req.get("status")
        if status not in VALID_REQUIREMENT_STATUSES:
            result.add_issue("CON006", "failure", f"invalid requirement status for {req.get('id')}")
        refs = _entry_refs(req)
        if status == "covered" and not refs:
            result.add_issue("CON006", "blocker", f"covered requirement lacks test_refs: {req.get('id')}")
        if status != "covered" and not req.get("reason"):
            result.add_issue("CON007", "failure", f"{status} requirement needs reason: {req.get('id')}")
        _validate_refs(refs, collected_refs, "CON008", result)


def _validate_state_matrices(matrices: Any, collected_refs: set[str], contract_path: Path, result: CheckResult) -> None:
    if matrices is None:
        result.add_issue("CON009", "blocker", "state_matrices section is required, even when empty")
        return
    if not isinstance(matrices, list):
        result.add_issue("CON009", "failure", "state_matrices must be a list")
        return
    for matrix in matrices:
        if not isinstance(matrix, dict):
            result.add_issue("CON009", "failure", "state matrix entries must be dictionaries")
            continue
        source = matrix.get("authoritative_source")
        extracted_values: set[str] | None = None
        if not isinstance(source, dict):
            result.add_issue("CON009", "failure", f"state matrix lacks authoritative_source: {matrix.get('id')}")
        else:
            extracted_values = _extract_authoritative_values(source, contract_path, result)
        classifications = matrix.get("classifications")
        if not isinstance(classifications, list):
            result.add_issue("CON009", "failure", f"state matrix lacks classifications: {matrix.get('id')}")
            continue
        classified: list[str] = []
        for classification in classifications:
            if not isinstance(classification, dict) or "value" not in classification:
                result.add_issue("CON009", "failure", f"invalid classification in matrix {matrix.get('id')}")
                continue
            value = str(classification["value"])
            classified.append(value)
            if classification.get("classification") not in VALID_CLASSIFICATIONS:
                result.add_issue("CON009", "failure", f"invalid classification for {value}")
            if classification.get("classification") == "covered":
                _validate_refs(_entry_refs(classification), collected_refs, "CON008", result)
            elif not classification.get("reason"):
                result.add_issue("CON009", "failure", f"non-covered matrix value needs reason: {value}")
        if len(classified) != len(set(classified)):
            result.add_issue("CON009", "failure", f"duplicate state classifications in {matrix.get('id')}")
        if extracted_values is not None and set(classified) != extracted_values:
            missing = sorted(extracted_values - set(classified))
            extra = sorted(set(classified) - extracted_values)
            detail = []
            if missing:
                detail.append(f"missing {missing}")
            if extra:
                detail.append(f"extra {extra}")
            result.add_issue("CON009", "failure", f"state matrix does not match authoritative source: {', '.join(detail)}")


def _extract_authoritative_values(source: dict[str, Any], contract_path: Path, result: CheckResult) -> set[str] | None:
    kind = source.get("kind")
    if kind == "manual_fallback":
        values = source.get("manual_values")
        if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
            result.add_issue("CON009", "failure", "manual_fallback requires manual_values")
            return None
        if not source.get("manual_fallback_reason"):
            result.add_issue("CON009", "failure", "manual_fallback requires manual_fallback_reason")
        if not _manual_fallback_confirmed(source, contract_path):
            result.add_issue("CON009", "blocker", "manual authoritative values require confirmed semantic review")
        else:
            result.human_confirmed.append(f"manual authoritative values confirmed by {source.get('review_flag_id')}")
        return set(values)

    module = source.get("module")
    if not isinstance(module, str):
        result.add_issue("CON009", "blocker", "non-manual authoritative source requires module for AST extraction")
        return None
    module_path = _module_to_path(module, contract_path)
    if module_path is None or not module_path.exists():
        result.add_issue("CON009", "blocker", f"could not locate module source without import: {module}")
        return None
    try:
        tree = ast.parse(module_path.read_text())
    except SyntaxError as exc:
        result.add_issue("CON009", "blocker", f"could not parse authoritative source {module}: {exc}")
        return None

    if kind == "python_enum":
        symbol = source.get("symbol")
        if not isinstance(symbol, str):
            result.add_issue("CON009", "failure", "python_enum source requires symbol")
            return None
        values = _extract_python_enum_values(tree, symbol)
        if values is None:
            result.add_issue("CON009", "blocker", f"could not extract enum values for {module}.{symbol}")
        return values

    if kind == "literal_constant":
        symbol = source.get("symbol")
        if not isinstance(symbol, str):
            result.add_issue("CON009", "failure", "literal_constant source requires symbol")
            return None
        values = _extract_literal_constant_values(tree, symbol)
        if values is None:
            result.add_issue("CON009", "blocker", f"could not extract literal constant values for {module}.{symbol}")
        return values

    if kind == "sqlalchemy_enum_field":
        model = source.get("model")
        field = source.get("field")
        if not isinstance(model, str) or not isinstance(field, str):
            result.add_issue("CON009", "failure", "sqlalchemy_enum_field requires model and field")
            return None
        values = _extract_sqlalchemy_enum_values(tree, model, field)
        if values is None:
            result.add_issue("CON009", "blocker", f"could not extract SQLAlchemy enum values for {module}.{model}.{field}")
        return values

    if kind == "sqlalchemy_check_constraint":
        constraint_name = source.get("constraint_name")
        if not isinstance(constraint_name, str):
            result.add_issue("CON009", "failure", "sqlalchemy_check_constraint requires constraint_name")
            return None
        values = _extract_check_constraint_values(tree, constraint_name)
        if values is None:
            result.add_issue("CON009", "blocker", f"could not extract check constraint values for {constraint_name}")
        return values

    result.add_issue("CON009", "failure", f"unsupported authoritative source kind: {kind}")
    return None


def _manual_fallback_confirmed(source: dict[str, Any], contract_path: Path) -> bool:
    review_flag_id = source.get("review_flag_id")
    if not isinstance(review_flag_id, str):
        return False
    try:
        data = _parse_contract_without_result(contract_path)
    except Exception:
        return False
    flags = data.get("review_flags")
    if not isinstance(flags, list):
        return False
    return any(
        isinstance(flag, dict)
        and flag.get("id") == review_flag_id
        and flag.get("status") == "confirmed"
        for flag in flags
    )


def _parse_contract_without_result(path: Path) -> dict[str, Any]:
    module = ast.parse(path.read_text())
    body = [node for node in module.body if not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str))]
    assignment = body[0]
    if not isinstance(assignment, ast.Assign):
        return {}
    value = ast.literal_eval(assignment.value)
    return value if isinstance(value, dict) else {}


def _module_to_path(module: str, contract_path: Path) -> Path | None:
    repo_root = contract_path
    for parent in contract_path.parents:
        if (parent / "backend").exists():
            repo_root = parent
            break
    parts = module.split(".")
    candidates = [
        repo_root / "backend" / Path(*parts[1:]).with_suffix(".py") if parts and parts[0] == "app" else repo_root / Path(*parts).with_suffix(".py"),
        repo_root / Path(*parts).with_suffix(".py"),
        repo_root / "backend" / Path(*parts).with_suffix(".py"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0] if candidates else None


def _extract_python_enum_values(tree: ast.AST, symbol: str) -> set[str] | None:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == symbol:
            values: set[str] = set()
            for stmt in node.body:
                if isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
                    values.add(stmt.value.value)
                elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
                    values.add(stmt.value.value)
            return values or None
    return None


def _extract_literal_constant_values(tree: ast.AST, symbol: str) -> set[str] | None:
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == symbol for target in node.targets):
                try:
                    value = ast.literal_eval(node.value)
                except Exception:
                    return None
                if isinstance(value, (set, tuple, list)) and all(isinstance(item, str) for item in value):
                    return set(value)
    return None


def _extract_sqlalchemy_enum_values(tree: ast.AST, model: str, field: str) -> set[str] | None:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == model:
            for stmt in node.body:
                target_name = None
                value = None
                if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                    target_name = stmt.targets[0].id
                    value = stmt.value
                elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                    target_name = stmt.target.id
                    value = stmt.value
                if target_name == field and value is not None:
                    return _extract_enum_call_values(value)
    return None


def _extract_enum_call_values(node: ast.AST) -> set[str] | None:
    for child in ast.walk(node):
        if isinstance(child, ast.Call) and _name_of(child.func).endswith("Enum"):
            values: set[str] = set()
            for arg in child.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    values.add(arg.value)
                elif isinstance(arg, (ast.List, ast.Tuple, ast.Set)):
                    for elt in arg.elts:
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                            values.add(elt.value)
            return values or None
    return None


def _extract_check_constraint_values(tree: ast.AST, constraint_name: str) -> set[str] | None:
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _name_of(node.func).endswith("CheckConstraint"):
            name_matches = any(
                keyword.arg == "name"
                and isinstance(keyword.value, ast.Constant)
                and keyword.value.value == constraint_name
                for keyword in node.keywords
            )
            if not name_matches or not node.args:
                continue
            expression = node.args[0]
            if isinstance(expression, ast.Constant) and isinstance(expression.value, str):
                return _parse_in_values(expression.value)
    return None


def _parse_in_values(expression: str) -> set[str] | None:
    marker = " IN "
    upper = expression.upper()
    if marker not in upper:
        return None
    start = expression.find("(")
    end = expression.rfind(")")
    if start == -1 or end == -1 or end <= start:
        return None
    raw = expression[start + 1 : end]
    values = []
    for part in raw.split(","):
        value = part.strip().strip("'\"")
        if value:
            values.append(value)
    return set(values) or None


def _name_of(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_name_of(node.value)}.{node.attr}"
    return ""


def _validate_scenarios(scenarios: Any, collected_refs: set[str], result: CheckResult) -> None:
    if not isinstance(scenarios, list):
        if result.scope == "directory":
            result.add_issue("CON010", "blocker", "scenario matrix is required")
        return
    if result.scope == "directory":
        seen = {(entry.get("category"), entry.get("item")) for entry in scenarios if isinstance(entry, dict)}
        for category, item in MANDATORY_SCENARIOS:
            if (category, item) not in seen:
                result.add_issue("CON010", "blocker", f"scenario item missing: {category} / {item}")
    for scenario in scenarios:
        if not isinstance(scenario, dict):
            result.add_issue("CON010", "failure", "scenario entries must be dictionaries")
            continue
        applicability = scenario.get("applicability")
        if applicability not in VALID_APPLICABILITY:
            result.add_issue("CON010", "failure", f"invalid scenario applicability: {scenario.get('id')}")
        refs = _entry_refs(scenario)
        if applicability == "required" and not refs:
            result.add_issue("CON010", "blocker", f"required scenario lacks test_refs: {scenario.get('id')}")
        if applicability != "required" and not scenario.get("reason"):
            result.add_issue("CON010", "failure", f"scenario requires reason: {scenario.get('id')}")
        _validate_refs(refs, collected_refs, "CON008", result)


def _validate_ownership(ownership: Any, collected_refs: set[str], result: CheckResult) -> None:
    if not isinstance(ownership, list):
        result.add_issue("CON011", "blocker", "ownership section is required")
        return
    owned = {_entry_refs(entry)[0] for entry in ownership if isinstance(entry, dict) and _entry_refs(entry)}
    for ref in sorted(collected_refs):
        if ref not in owned:
            result.add_issue("CON011", "blocker", f"missing ownership decision for {ref}")
    for entry in ownership:
        if not isinstance(entry, dict):
            result.add_issue("CON011", "failure", "ownership entries must be dictionaries")
            continue
        if not entry.get("rationale") or not entry.get("behavior_under_test") or entry.get("owner_kind") not in {"page", "shared_domain", "legacy"}:
            result.add_issue("CON011", "failure", f"invalid ownership entry for {entry.get('test_ref')}")
        _validate_refs(_entry_refs(entry), collected_refs, "CON008", result)


def _validate_effects(effects: Any, collected_refs: set[str], result: CheckResult) -> None:
    if effects is None:
        result.add_issue("CON012", "blocker", "effects section is required, even when empty")
        return
    if not isinstance(effects, list):
        result.add_issue("CON012", "failure", "effects must be a list")
        return
    for effect in effects:
        if not isinstance(effect, dict):
            result.add_issue("CON012", "failure", "effect entries must be dictionaries")
            continue
        phase = effect.get("phase")
        kind = effect.get("kind")
        rule = {"successful_mutation": "CON012", "rejected_mutation": "CON013", "idempotency": "CON014", "rollback": "CON013"}.get(str(phase), "CON012")
        if phase not in VALID_EFFECT_PHASES:
            result.add_issue(rule, "failure", f"invalid effect phase: {effect.get('id')}")
        if kind not in VALID_EFFECT_KINDS:
            result.add_issue(rule, "failure", f"invalid effect kind: {effect.get('id')}")
        if kind != "external_call_count" and not (effect.get("model") or effect.get("table")):
            result.add_issue(rule, "failure", f"database effect requires model or table: {effect.get('id')}")
        if not isinstance(effect.get("lookup"), dict):
            result.add_issue(rule, "failure", f"effect requires structured lookup: {effect.get('id')}")
        if not isinstance(effect.get("after"), dict):
            result.add_issue(rule, "failure", f"effect requires after expectation: {effect.get('id')}")
        _validate_refs(_entry_refs(effect), collected_refs, "CON008", result)


def _validate_constraints(constraints: Any, collected_refs: set[str], contract_path: Path, result: CheckResult) -> None:
    if constraints is None:
        result.add_issue("CON015", "blocker", "constraints section is required, even when empty")
        return
    if not isinstance(constraints, list):
        result.add_issue("CON015", "failure", "constraints must be a list")
        return
    for constraint in constraints:
        if not isinstance(constraint, dict):
            result.add_issue("CON015", "failure", "constraint entries must be dictionaries")
            continue
        source = constraint.get("constraint_source")
        if not isinstance(source, dict) or not constraint.get("expected_database_identifier"):
            result.add_issue("CON015", "failure", f"constraint source and expected identifier are required: {constraint.get('id')}")
        elif source.get("kind") == "manual_fallback":
            if not source.get("manual_fallback_reason"):
                result.add_issue("CON015", "failure", "manual constraint fallback requires reason")
            review_flag_id = source.get("review_flag_id")
            if not isinstance(review_flag_id, str) or not _contract_review_flag_confirmed(review_flag_id, contract_path):
                result.add_issue("CON015", "blocker", "manual constraint fallback requires confirmed semantic review")
            else:
                result.human_confirmed.append(f"manual constraint source confirmed by {review_flag_id}")
        elif not _constraint_source_contains_identifier(source, contract_path, str(constraint.get("expected_database_identifier"))):
            result.add_issue("CON015", "blocker", f"could not extract expected constraint identifier: {constraint.get('expected_database_identifier')}")
        _validate_refs(_entry_refs(constraint), collected_refs, "CON008", result)


def _constraint_source_contains_identifier(source: dict[str, Any], contract_path: Path, expected_identifier: str) -> bool:
    kind = source.get("kind")
    if kind == "sqlalchemy_constraint":
        module = source.get("module")
        if not isinstance(module, str):
            return False
        module_path = _module_to_path(module, contract_path)
        if module_path is None or not module_path.exists():
            return False
        try:
            tree = ast.parse(module_path.read_text())
        except SyntaxError:
            return False
        return _ast_contains_constraint_name(tree, expected_identifier)
    if kind == "migration_constraint":
        migration_path = source.get("migration_path")
        if not isinstance(migration_path, str):
            return False
        repo_root = _repo_root_for_contract(contract_path)
        path = repo_root / migration_path
        if not path.exists():
            return False
        return expected_identifier in path.read_text()
    return False


def _repo_root_for_contract(contract_path: Path) -> Path:
    for parent in contract_path.parents:
        if (parent / "backend").exists():
            return parent
    return contract_path.parent


def _ast_contains_constraint_name(tree: ast.AST, expected_identifier: str) -> bool:
    constraint_suffixes = (
        "CheckConstraint",
        "UniqueConstraint",
        "ForeignKeyConstraint",
        "PrimaryKeyConstraint",
        "Index",
    )
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not _name_of(node.func).endswith(constraint_suffixes):
            continue
        for keyword in node.keywords:
            if (
                keyword.arg == "name"
                and isinstance(keyword.value, ast.Constant)
                and keyword.value.value == expected_identifier
            ):
                return True
    return False


def _validate_time_boundaries(boundaries: Any, collected_refs: set[str], result: CheckResult) -> None:
    if boundaries is None:
        result.add_issue("CON016", "blocker", "time_boundaries section is required, even when empty")
        return
    if not isinstance(boundaries, list):
        result.add_issue("CON016", "failure", "time_boundaries must be a list")
        return
    for boundary in boundaries:
        if not isinstance(boundary, dict):
            result.add_issue("CON016", "failure", "time boundary entries must be dictionaries")
            continue
        if boundary.get("clock_strategy") not in {"captured", "frozen", "injected", "service_layer_exact_api_margin"}:
            result.add_issue("CON016", "failure", f"invalid clock strategy: {boundary.get('id')}")
        if not isinstance(boundary.get("boundary_cases"), list):
            result.add_issue("CON016", "failure", f"time boundary requires boundary_cases: {boundary.get('id')}")
        _validate_refs(_entry_refs(boundary), collected_refs, "CON008", result)


def _validate_clock_controls(controls: Any, collected_refs: set[str], result: CheckResult) -> None:
    if controls is None:
        return
    if not isinstance(controls, list):
        result.add_issue("CON016", "failure", "clock_controls must be a list")
        return
    for control in controls:
        if not isinstance(control, dict):
            result.add_issue("CON016", "failure", "clock control entries must be dictionaries")
            continue
        if not control.get("id"):
            result.add_issue("CON016", "failure", "clock control requires id")
        if control.get("strategy") not in {"captured_test_baseline", "frozen_application_clock"}:
            result.add_issue("CON016", "failure", f"invalid clock control strategy: {control.get('id')}")
        _validate_refs(_entry_refs(control), collected_refs, "CON008", result)


def _validate_review_flags(flags: Any, result: CheckResult) -> None:
    if flags is None:
        result.add_issue("CON018", "blocker", "review_flags section is required, even when empty")
        return
    if not isinstance(flags, list):
        result.add_issue("CON018", "failure", "review_flags must be a list")
        return
    for flag in flags:
        if not isinstance(flag, dict):
            result.add_issue("CON018", "failure", "review flag entries must be dictionaries")
            continue
        status = flag.get("status")
        if status not in VALID_REVIEW_STATUSES:
            result.add_issue("CON018", "failure", f"invalid review flag status: {flag.get('id')}")
        elif status == "unresolved":
            result.add_issue("CON018", "blocker", f"unresolved review flag: {flag.get('summary', flag.get('id'))}")
        else:
            result.human_confirmed.append(f"review flag confirmed: {flag.get('id')}")


def _contract_review_flag_confirmed(review_flag_id: str, contract_path: Path) -> bool:
    try:
        data = _parse_contract_without_result(contract_path)
    except Exception:
        return False
    flags = data.get("review_flags")
    if not isinstance(flags, list):
        return False
    return any(
        isinstance(flag, dict)
        and flag.get("id") == review_flag_id
        and flag.get("status") == "confirmed"
        for flag in flags
    )


def _validate_gaps(gaps: Any, target: Target, result: CheckResult) -> None:
    if gaps is None:
        result.add_issue("CON017", "blocker", "gaps section is required, even when empty")
        return
    if not isinstance(gaps, list):
        result.add_issue("CON017", "failure", "gaps must be a list")
        return
    for gap in gaps:
        if not isinstance(gap, dict):
            result.add_issue("CON017", "failure", "gap entries must be dictionaries")
            continue
        if gap.get("status") == "open" and target.scope == "directory":
            result.add_issue("CON017", "blocker", f"open gap prevents feature-level pass: {gap.get('summary', gap.get('id'))}")
        elif gap.get("status") == "accepted_exception":
            if not gap.get("approved_by_user"):
                result.add_issue("CON017", "blocker", f"accepted gap lacks user approval: {gap.get('id')}")
            else:
                result.human_confirmed.append(f"accepted gap approved by user: {gap.get('id')}")
        elif gap.get("status") != "open":
            result.add_issue("CON017", "failure", f"invalid gap status: {gap.get('id')}")


def _validate_refs(refs: list[str], collected_refs: set[str], rule_id: str, result: CheckResult) -> None:
    for ref in refs:
        if ref not in collected_refs:
            result.add_issue(rule_id, "failure", f"contract references unknown test: {ref}")
