from __future__ import annotations

from collections import defaultdict
import re

from .discovery import RequirementUsage
from .report import CheckResult, Scope
from .requirements import RequirementDeclaration


def build_traceability(
    *,
    declarations: dict[str, RequirementDeclaration],
    usages: tuple[RequirementUsage, ...],
    scope: Scope,
    target: str,
) -> CheckResult:
    result = CheckResult(target=target, scope=scope)
    by_pass: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for declaration in declarations.values():
        by_pass[declaration.owning_pass][declaration.requirement_id] = []

    for usage in usages:
        declaration = declarations[usage.requirement_id]
        by_pass[declaration.owning_pass][usage.requirement_id].append(usage.nodeid)

    result.traceability = {
        pass_id: {
            requirement_id: sorted(set(nodeids))
            for requirement_id, nodeids in sorted(requirement_map.items())
        }
        for pass_id, requirement_map in sorted(by_pass.items())
    }

    if scope in {"domain", "suite"}:
        for declaration in declarations.values():
            if not _declaration_applies_to_target(declaration, scope, target):
                continue
            mapped = result.traceability.get(declaration.owning_pass, {}).get(declaration.requirement_id, [])
            if declaration.state == "blocked":
                reason = _safe_reason_summary(declaration.reason)
                result.add_issue(
                    "TRACE002",
                    "blocker",
                    f"requirement is explicitly blocked: {declaration.requirement_id}; reason: {reason}",
                    declaration.requirement_id,
                )
            if declaration.state == "required" and not mapped:
                result.add_issue(
                    "TRACE001",
                    "blocker",
                    f"required requirement has no trusted executable evidence: {declaration.requirement_id}",
                    declaration.requirement_id,
                )

    result.summary["Traceability passes"] = str(len(result.traceability))
    result.summary["Traceability requirements"] = str(sum(len(items) for items in result.traceability.values()))
    return result


def _declaration_applies_to_target(
    declaration: RequirementDeclaration,
    scope: Scope,
    target: str,
) -> bool:
    if scope == "suite":
        return True
    if not declaration.scope:
        return True

    declaration_scope = declaration.scope.strip("/")
    target_scope = target.strip("/")
    return (
        declaration_scope == target_scope
        or declaration_scope.startswith(f"{target_scope}/")
        or target_scope.startswith(f"{declaration_scope}/")
    )


def _safe_reason_summary(reason: str | None) -> str:
    if not reason:
        return "no reason declared"
    summary = " ".join(reason.split())
    summary = re.sub(r"\bBearer\s+[A-Za-z0-9._~+/=-]+", "Bearer [REDACTED]", summary, flags=re.IGNORECASE)
    summary = re.sub(r"\b(?:sk|rk|pk|whsec)_(?:test|live)?_[A-Za-z0-9_]+\b", "[REDACTED]", summary)
    summary = re.sub(r"\bpostgres(?:ql)?(?:\+\w+)?://[^\s'\"<>]+", "[REDACTED]", summary, flags=re.IGNORECASE)
    if len(summary) > 180:
        summary = f"{summary[:177]}..."
    return summary
