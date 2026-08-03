from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Iterable, Literal


ResultState = Literal["PASS", "FAIL", "BLOCKED", "USAGE_ERROR", "INTERNAL_ERROR"]
Severity = Literal["failure", "blocker", "review", "info"]
Scope = Literal["file", "directory"]


class ExitCode(IntEnum):
    PASS = 0
    FAIL = 1
    BLOCKED = 2
    USAGE_ERROR = 3
    INTERNAL_ERROR = 4


_STATE_PRECEDENCE: dict[ResultState, int] = {
    "PASS": 0,
    "BLOCKED": 1,
    "FAIL": 2,
    "INTERNAL_ERROR": 3,
    "USAGE_ERROR": 4,
}


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
    commands_not_run: list[str] = field(default_factory=list)
    human_confirmed: list[str] = field(default_factory=list)
    completion: dict[str, str] = field(default_factory=dict)
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
        base.commands_not_run.extend(other.commands_not_run)
        base.human_confirmed.extend(other.human_confirmed)
        base.completion.update(other.completion)
    return base


def usage_error(target: str, message: str, rule_id: str = "TGT001") -> CheckResult:
    result = CheckResult(target=target, scope=None, forced_state="USAGE_ERROR")
    result.add_issue(rule_id, "failure", message)
    return result


def render_report(result: CheckResult) -> str:
    state = result.state
    lines: list[str] = [
        f"Target: {result.target}",
        f"Scope: {result.scope or 'unknown'}",
        f"Result: {state}",
        f"Exit code: {result.exit_code}",
    ]

    if result.scope == "file":
        lines.append(
            "File-level compliance only; containing feature is not certified complete."
        )

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

    if result.human_confirmed:
        lines.append("")
        lines.append("Human-confirmed evidence:")
        for item in sorted(set(result.human_confirmed)):
            lines.append(f"- {item}")

    lines.append("")
    lines.append("Commands run:")
    commands_run = _unique(result.commands_run)
    if commands_run:
        for command in commands_run:
            lines.append(f"- {command}")
    else:
        lines.append("- None")

    lines.append("")
    lines.append("Commands not run:")
    commands_not_run = _unique(result.commands_not_run)
    if commands_not_run:
        for command in commands_not_run:
            lines.append(f"- {command}")
    else:
        lines.append("- None")

    lines.append("")
    lines.append("Completion sections:")
    review_ids = sorted({issue.rule_id for issue in grouped["review"]})
    if review_ids:
        result.completion.setdefault(
            "Review Findings",
            f"{len(grouped['review'])} finding(s); rule ids: {', '.join(review_ids)}",
        )
    else:
        result.completion.setdefault("Review Findings", "0 finding(s)")
    for section in _completion_sections():
        lines.append(f"- {section}: {result.completion.get(section, 'not reported')}")
    if result.scope == "directory" and state == "PASS":
        lines.append("- Feature/domain completion is certified for this target.")
    elif result.scope == "directory":
        lines.append("- Feature/domain completion is not certified because failures or blockers remain.")
    elif result.scope == "file":
        lines.append("- Feature/domain completion is not certified by a single-file check.")
    else:
        lines.append("- Completion could not be evaluated.")

    return "\n".join(lines)


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _completion_sections() -> tuple[str, ...]:
    return (
        "Sources Reviewed",
        "Requirement Coverage",
        "Enum And State Matrix",
        "Scenario Coverage",
        "Ownership Decisions",
        "Assertion Review",
        "Time Control",
        "Remaining Gaps",
        "Conflicts",
        "Review Findings",
        "Runtime Evidence",
        "Mutation Status",
        "Mutation Evidence",
        "Verification",
    )
