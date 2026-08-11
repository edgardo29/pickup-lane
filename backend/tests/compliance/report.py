from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Iterable, Literal


ResultState = Literal["PASS", "FAIL", "BLOCKED", "USAGE_ERROR", "INTERNAL_ERROR"]
Severity = Literal["failure", "blocker", "review", "info"]
Scope = Literal["file", "domain", "suite"]


class ExitCode(IntEnum):
    PASS = 0
    FAIL = 1
    BLOCKED = 2
    USAGE_ERROR = 3
    INTERNAL_ERROR = 4


@dataclass(frozen=True)
class Issue:
    rule_id: str
    severity: Severity
    message: str
    location: str | None = None


@dataclass
class CheckResult:
    target: str
    scope: Scope | None
    issues: list[Issue] = field(default_factory=list)
    commands_run: list[str] = field(default_factory=list)
    traceability: dict[str, dict[str, list[str]]] = field(default_factory=dict)
    summary: dict[str, str] = field(default_factory=dict)
    forced_state: ResultState | None = None

    def add_issue(
        self,
        rule_id: str,
        severity: Severity,
        message: str,
        location: str | None = None,
    ) -> None:
        self.issues.append(Issue(rule_id, severity, message, location))

    @property
    def state(self) -> ResultState:
        if self.forced_state is not None:
            return self.forced_state
        if any(issue.severity == "failure" for issue in self.issues):
            return "FAIL"
        if any(issue.severity == "blocker" for issue in self.issues):
            return "BLOCKED"
        return "PASS"

    @property
    def exit_code(self) -> int:
        return int(ExitCode[self.state])


def merge_results(base: CheckResult, others: Iterable[CheckResult]) -> CheckResult:
    for other in others:
        base.issues.extend(other.issues)
        base.commands_run.extend(other.commands_run)
        base.summary.update(other.summary)
        for pass_id, requirement_map in other.traceability.items():
            target_map = base.traceability.setdefault(pass_id, {})
            for requirement_id, nodeids in requirement_map.items():
                target_map.setdefault(requirement_id, [])
                target_map[requirement_id].extend(nodeids)
    for pass_id, requirement_map in base.traceability.items():
        for requirement_id, nodeids in requirement_map.items():
            requirement_map[requirement_id] = sorted(set(nodeids))
    return base


def usage_error(target: str, message: str, rule_id: str = "USAGE") -> CheckResult:
    result = CheckResult(target=target or "<missing>", scope=None, forced_state="USAGE_ERROR")
    result.add_issue(rule_id, "failure", message)
    return result


def render_report(result: CheckResult) -> str:
    lines = [
        f"Target: {result.target}",
        f"Scope: {result.scope or 'unknown'}",
        f"Result: {result.state}",
        f"Exit code: {result.exit_code}",
    ]

    if result.scope == "file":
        lines.append("File scope validates machine-compliance only and makes no completeness claim.")
    elif result.scope == "domain":
        lines.append("Domain/subtree scope validates scoped machine-compliance only.")
    elif result.scope == "suite":
        lines.append("Suite scope validates trusted repository-wide machine-compliance only.")

    grouped: dict[Severity, list[Issue]] = {
        "failure": [],
        "blocker": [],
        "review": [],
        "info": [],
    }
    for issue in result.issues:
        grouped[issue.severity].append(issue)

    for title, severity in (
        ("Failures", "failure"),
        ("Blockers", "blocker"),
        ("Review Findings", "review"),
        ("Info", "info"),
    ):
        if not grouped[severity]:
            continue
        lines.append("")
        lines.append(f"{title}:")
        for issue in grouped[severity]:
            location = f" [{issue.location}]" if issue.location else ""
            lines.append(f"- {issue.rule_id}{location}: {issue.message}")

    if result.traceability:
        lines.append("")
        lines.append("Generated traceability:")
        for pass_id in sorted(result.traceability):
            lines.append(f"- {pass_id}:")
            for requirement_id, nodeids in sorted(result.traceability[pass_id].items()):
                if nodeids:
                    lines.append(f"  - {requirement_id}: {len(nodeids)} test node(s)")
                else:
                    lines.append(f"  - {requirement_id}: no mapped test nodes")

    if result.summary:
        lines.append("")
        lines.append("Summary:")
        for key in sorted(result.summary):
            lines.append(f"- {key}: {result.summary[key]}")

    lines.append("")
    lines.append("Commands run:")
    if result.commands_run:
        for command in dict.fromkeys(result.commands_run):
            lines.append(f"- {command}")
    else:
        lines.append("- None")

    return "\n".join(lines)
