#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

from compliance.contracts import load_contract
from compliance.mutations import evaluate_mutation_requirement, run_mutation_preflight, run_mutations
from compliance.repository import analyze_repository
from compliance.report import CheckResult, merge_results, render_report
from compliance.runtime import evaluate_runtime_requirement, run_runtime_validation
from compliance.static_analysis import analyze_static, collect_tests
from compliance.targeting import resolve_target


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        result = run_checker(argv)
    except Exception as exc:  # noqa: BLE001 - top-level guard for checker bugs.
        result = CheckResult(target=" ".join(argv) or "<missing>", scope=None, forced_state="INTERNAL_ERROR")
        result.add_issue("INTERNAL", "failure", f"checker internal error: {exc}")
        result.commands_run.append(_checker_invocation(argv))
    print(render_report(result))
    return result.exit_code


def run_checker(argv: list[str]) -> CheckResult:
    invocation = _checker_invocation(argv)
    parse_result = _parse_args(argv)
    if isinstance(parse_result, CheckResult):
        parse_result.commands_run.append(invocation)
        return parse_result
    target_args, runtime_requested, mutations_requested = parse_result

    target, target_error = resolve_target(target_args, cwd=Path.cwd())
    if target_error is not None:
        target_error.commands_run.append(invocation)
        return target_error
    assert target is not None

    base = CheckResult(target=str(target.relative_path), scope=target.scope)  # type: ignore[arg-type]
    base.commands_run.append(invocation)
    if runtime_requested and mutations_requested:
        base.completion["Verification"] = "static, contract, repository, runtime, and optional mutation hardening checker run"
    elif runtime_requested:
        base.completion["Verification"] = "static, contract, repository, and runtime evidence checker run"
    else:
        base.completion["Verification"] = "static, contract, and repository checker run only"
    base.commands_not_run.extend(
        [
            "migrations",
            "application servers",
            "database reset/create/drop/truncate commands",
            "external services",
        ]
    )

    static_index, collect_result = collect_tests(target)
    contract, contract_result = load_contract(target, set(static_index.tests))
    results = [collect_result, contract_result]
    if contract is None:
        return merge_results(base, results)

    results.append(analyze_static(target, contract, static_index))
    results.append(analyze_repository(target, static_index))
    results.append(evaluate_runtime_requirement(contract, runtime_requested))
    results.append(evaluate_mutation_requirement(contract, runtime_requested, mutations_requested))

    mutation_preflight_result: CheckResult | None = None
    if mutations_requested:
        mutation_preflight_result = run_mutation_preflight(target, contract)
        results.append(mutation_preflight_result)

    if runtime_requested:
        results.append(run_runtime_validation(target, contract))
    else:
        base.commands_not_run.append("pytest target with compliance evidence plugin")

    mutation_preflight_status = (
        mutation_preflight_result.completion.get("Mutation Preflight")
        if mutation_preflight_result is not None
        else None
    )
    if mutations_requested and mutation_preflight_status == "passed":
        results.append(run_mutations(target, contract))
    elif mutations_requested:
        base.commands_not_run.append("mutmut run for declared mutation targets (mutation preflight deferred or unsupported)")
    else:
        base.commands_not_run.append("mutmut run for declared mutation targets")

    return merge_results(base, results)


def _checker_invocation(argv: list[str]) -> str:
    return " ".join(["python", "check_backend_tests.py", *argv]).strip()


def _parse_args(argv: list[str]) -> tuple[list[str], bool, bool] | CheckResult:
    runtime_requested = False
    mutations_requested = False
    targets: list[str] = []

    for arg in argv:
        if arg == "--runtime":
            runtime_requested = True
        elif arg == "--mutations":
            mutations_requested = True
        elif arg.startswith("--"):
            result = CheckResult(target=" ".join(argv) or "<missing>", scope=None, forced_state="USAGE_ERROR")
            result.add_issue("CLI001", "failure", f"unsupported option: {arg}")
            return result
        else:
            targets.append(arg)

    if mutations_requested and not runtime_requested:
        result = CheckResult(target=" ".join(targets) or "<missing>", scope=None, forced_state="USAGE_ERROR")
        result.add_issue("MUT001", "failure", "--mutations requires --runtime")
        return result

    return targets, runtime_requested, mutations_requested


if __name__ == "__main__":
    raise SystemExit(main())
