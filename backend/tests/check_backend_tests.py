#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
from typing import cast

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from compliance.discovery import collect_requirement_metadata
from compliance.policies import analyze_policy, load_suite_policy
from compliance.report import CheckResult, Scope, merge_results, render_report
from compliance.requirements import load_requirement_declarations
from compliance.targeting import resolve_target
from compliance.traceability import build_traceability


VALID_SCOPES = {"file", "domain", "suite"}


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        result = run_checker(argv)
    except Exception as exc:  # noqa: BLE001 - top-level guard for checker bugs.
        result = CheckResult(
            target=" ".join(argv) or "<missing>",
            scope=None,
            forced_state="INTERNAL_ERROR",
        )
        result.add_issue("INTERNAL001", "failure", f"checker internal error: {exc}")
        result.commands_run.append(_checker_invocation(argv))
    print(render_report(result))
    return result.exit_code


def run_checker(argv: list[str]) -> CheckResult:
    invocation = _checker_invocation(argv)
    parsed = _parse_args(argv)
    if isinstance(parsed, CheckResult):
        parsed.commands_run.append(invocation)
        return parsed
    scope, target_text = parsed

    target, target_error = resolve_target(scope=scope, target_text=target_text, cwd=Path.cwd())
    if target_error is not None:
        target_error.commands_run.append(invocation)
        return target_error
    assert target is not None

    base = CheckResult(target=target.display, scope=target.scope)
    base.commands_run.append(invocation)

    declarations, declaration_result = load_requirement_declarations(
        target.tests_root / "support" / "requirements"
    )
    suite_policy, suite_policy_result = load_suite_policy(
        target.tests_root / "support" / "suite_policy.json"
    )
    policy_result = analyze_policy(target, suite_policy)
    collection, collection_result = collect_requirement_metadata(target, declarations)
    traceability_result = build_traceability(
        declarations=declarations,
        usages=collection.usages,
        scope=target.scope,
        target=target.display,
    )

    return merge_results(
        base,
        [
            declaration_result,
            suite_policy_result,
            policy_result,
            collection_result,
            traceability_result,
        ],
    )


def _checker_invocation(argv: list[str]) -> str:
    return " ".join(["python", "backend/tests/check_backend_tests.py", *argv]).strip()


def _parse_args(argv: list[str]) -> tuple[Scope, str | None] | CheckResult:
    scope: str | None = None
    targets: list[str] = []
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg == "--scope":
            index += 1
            if index >= len(argv):
                return _usage(" ".join(argv), "--scope requires one of: file, domain, suite", "CLI001")
            scope = argv[index]
        elif arg.startswith("--scope="):
            scope = arg.split("=", 1)[1]
        elif arg.startswith("--"):
            return _usage(" ".join(argv), f"unsupported option: {arg}", "CLI002")
        else:
            targets.append(arg)
        index += 1

    if scope not in VALID_SCOPES:
        return _usage(" ".join(argv), "--scope must be one of: file, domain, suite", "CLI001")
    if len(targets) > 1:
        return _usage(" ".join(targets), "at most one target path is allowed", "CLI003")
    if scope != "suite" and not targets:
        return _usage(" ".join(argv), "file and domain scopes require a target path", "CLI004")
    return cast(Scope, scope), targets[0] if targets else None


def _usage(target: str, message: str, rule_id: str) -> CheckResult:
    result = CheckResult(target=target or "<missing>", scope=None, forced_state="USAGE_ERROR")
    result.add_issue(rule_id, "failure", message)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
