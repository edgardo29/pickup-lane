from __future__ import annotations

import ast
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from queue import Empty, Queue
from threading import Thread
from typing import Any

from .contracts import Contract
from .report import CheckResult
from .runtime import EVIDENCE_ENV, NETWORK_BLOCK_ENV
from .targeting import Target


MIN_MUTMUT_VERSION = (2, 4, 0)
MUTMUT_HEARTBEAT_SECONDS = 30
DEFAULT_MUTMUT_BASELINE_TIMEOUT_SECONDS = 5 * 60
DEFAULT_MUTMUT_BATCH_TIMEOUT_SECONDS = 15 * 60


@dataclass(frozen=True)
class ProcessResult:
    returncode: int
    stdout: str
    stderr: str = ""
    timed_out: bool = False
    timeout_kind: str | None = None


def evaluate_mutation_requirement(contract: Contract, runtime_requested: bool, mutation_requested: bool) -> CheckResult:
    result = CheckResult(target=str(contract.path.parent), scope=None)
    targets = _mutation_targets(contract)
    target_ids = [str(entry.get("id")) for entry in targets if entry.get("id")]
    for message in _mutation_target_schema_errors(targets):
        result.add_issue("MUT003", "failure", message)
    if mutation_requested and not runtime_requested:
        result.add_issue("MUT001", "failure", "--mutations requires --runtime")
    if not mutation_requested:
        result.commands_not_run.append("mutmut run for declared mutation targets")
        result.completion["Mutation Status"] = "NOT_REQUESTED"
    if targets and not mutation_requested:
        result.completion["Mutation Evidence"] = (
            f"not requested; target ids: {', '.join(target_ids)}"
        )
    elif targets:
        result.completion["Mutation Status"] = "DEFERRED"
        result.completion["Mutation Evidence"] = (
            f"requested; pending optional hardening run for target ids: {', '.join(target_ids)}"
        )
    else:
        result.completion.setdefault("Mutation Status", "NOT_REQUESTED")
        result.completion["Mutation Evidence"] = "no mutation targets declared"
    return result


def run_mutations(target: Target, contract: Contract) -> CheckResult:
    result = CheckResult(target=str(target.relative_path), scope=target.scope)  # type: ignore[arg-type]
    targets = _mutation_targets(contract)
    if not targets:
        result.add_issue("MUT002", "info", "no mutation_targets declared for mutation mode")
        result.completion["Mutation Status"] = "UNSUPPORTED"
        result.completion["Mutation Evidence"] = "mutation mode requested but no targets declared"
        return result

    batch_statuses: list[str] = []
    batch_summaries: list[str] = []
    for entry in targets:
        batch_result = _run_mutation_batch(target, entry)
        result.issues.extend(batch_result.issues)
        result.commands_run.extend(batch_result.commands_run)
        result.commands_not_run.extend(batch_result.commands_not_run)
        status_text = batch_result.completion.get("Mutation Status", "UNSUPPORTED")
        batch_statuses.append(status_text)
        batch_summaries.append(
            f"{entry.get('id', '<unknown>')}={status_text}: "
            f"{batch_result.completion.get('Mutation Evidence', 'not reported')}"
        )

    result.completion["Mutation Status"] = _aggregate_mutation_status(batch_statuses)
    result.completion["Mutation Evidence"] = "; ".join(batch_summaries)
    return result


def _run_mutation_batch(target: Target, entry: dict[str, Any]) -> CheckResult:
    result = CheckResult(target=str(target.relative_path), scope=target.scope)  # type: ignore[arg-type]
    source_path = _module_to_path(target.repo_root, str(entry.get("module")))
    if source_path is None:
        result.add_issue("MUT003", "info", f"mutation target module cannot be resolved: {entry.get('module')}")
        result.completion["Mutation Status"] = "UNSUPPORTED"
        result.completion["Mutation Evidence"] = "mutation target module resolution failed"
        return result
    line_scope = _mutation_line_scope([entry], [source_path])
    if isinstance(line_scope, str):
        result.add_issue("MUT003", "info", line_scope)
        result.completion["Mutation Status"] = "UNSUPPORTED"
        result.completion["Mutation Evidence"] = "mutation target symbol scope resolution failed"
        return result

    test_refs = sorted(ref for ref in entry.get("test_refs", []) if isinstance(ref, str))
    pytest_selection = [str(target.contract_dir / ref.split("::", 1)[0]) + ("::" + ref.split("::", 1)[1] if "::" in ref else "") for ref in test_refs]
    if not pytest_selection:
        result.add_issue("MUT003", "info", f"mutation target requires test_refs: {entry.get('id')}")
        result.completion["Mutation Status"] = "UNSUPPORTED"
        result.completion["Mutation Evidence"] = "mutation target test selection was empty"
        return result

    evidence_path = Path(tempfile.mkdtemp(prefix="backend-test-compliance-mutmut-")) / "evidence.jsonl"
    runner = " ".join(
        [
            sys.executable,
            "-m",
            "pytest",
            "-p",
            "compliance.runtime",
            *pytest_selection,
        ]
    )
    command = [
        sys.executable,
        "-m",
        "mutmut",
        "run",
        "--paths-to-mutate",
        str(source_path),
        "--runner",
        runner,
        "--simple-output",
    ]
    if line_scope:
        patch_path = evidence_path.with_name("mutation-scope.patch")
        _write_mutation_scope_patch(patch_path, line_scope)
        command.extend(["--use-patch-file", str(patch_path)])
    env = os.environ.copy()
    env[EVIDENCE_ENV] = str(evidence_path)
    env[NETWORK_BLOCK_ENV] = "1"
    env["PYTHONPATH"] = os.pathsep.join(
        [
            str(target.repo_root),
            str(target.tests_root),
            env.get("PYTHONPATH", ""),
        ]
    )
    mutmut_cwd = _mutmut_cwd(target)
    source_backups = {
        source_path: source_path.read_bytes()
    }
    cache_path = mutmut_cwd / ".mutmut-cache"
    if cache_path.exists():
        _remove_mutmut_cache(cache_path)
    try:
        completed = _run_command_with_heartbeat(
            command,
            cwd=mutmut_cwd,
            env=env,
            label="mutmut",
        )
    finally:
        for path, content in source_backups.items():
            if path.exists() and path.read_bytes() != content:
                path.write_bytes(content)
    result.commands_run.append(" ".join(command))
    if completed.returncode != 0:
        results_command = [sys.executable, "-m", "mutmut", "results"]
        results_completed = subprocess.run(results_command, cwd=mutmut_cwd, env=env, text=True, capture_output=True, check=False)
        result.commands_run.append(" ".join(results_command))
        output_path = evidence_path.with_name("mutmut-output.txt")
        output_path.write_text(
            "\n".join(
                [
                    "$ " + " ".join(command),
                    "",
                    "STDOUT:",
                    completed.stdout,
                    "",
                    "STDERR:",
                    completed.stderr,
                    "",
                    "RESULTS:",
                    results_completed.stdout,
                    "",
                    "RESULTS STDERR:",
                    results_completed.stderr,
                ]
            )
        )
        if _output_mentions_survivors(completed.stdout + completed.stderr):
            result.add_issue(
                "MUT004",
                "info",
                f"declared protected mutation survived; captured output: {output_path}",
            )
            result.completion["Mutation Status"] = "FAILED"
        elif completed.timed_out:
            timeout_detail = f" ({completed.timeout_kind} cap)" if completed.timeout_kind else ""
            result.add_issue(
                "MUT005",
                "info",
                f"mutmut exceeded checker hard cap{timeout_detail}; captured output: {output_path}",
            )
            result.completion["Mutation Status"] = "DEFERRED"
        else:
            result.add_issue(
                "MUT005",
                "info",
                f"mutmut did not complete cleanly; mutation coverage unsupported or timed out; captured output: {output_path}",
            )
            result.completion["Mutation Status"] = "UNSUPPORTED"
        status_text = result.completion["Mutation Status"]
        result.completion["Mutation Evidence"] = f"{status_text}; captured output: {output_path}"
        return result

    results_command = [sys.executable, "-m", "mutmut", "results"]
    results_completed = subprocess.run(results_command, cwd=mutmut_cwd, env=env, text=True, capture_output=True, check=False)
    result.commands_run.append(" ".join(results_command))
    output = results_completed.stdout + results_completed.stderr
    if _output_mentions_survivors(output):
        result.add_issue("MUT004", "info", "declared protected mutation survived")
        result.completion["Mutation Status"] = "FAILED"
    if "timeout" in output.lower():
        result.add_issue("MUT005", "info", "mutation run reported timeout; review mutmut timeout configuration")
        result.completion["Mutation Status"] = "DEFERRED"
    result.completion.setdefault("Mutation Status", "PASSED")
    result.completion["Mutation Evidence"] = f"mutmut completed for target id: {entry.get('id')}"
    return result


def run_mutation_preflight(target: Target, contract: Contract) -> CheckResult:
    result = CheckResult(target=str(target.relative_path), scope=target.scope)  # type: ignore[arg-type]
    targets = _mutation_targets(contract)
    if not targets:
        result.add_issue("MUT002", "info", "no mutation_targets declared for mutation mode")
        result.completion["Mutation Status"] = "UNSUPPORTED"
        result.completion["Mutation Preflight"] = "unsupported; no mutation targets declared"
        return result
    preflight = _preflight(target, contract, targets)
    result.issues.extend(preflight.issues)
    result.commands_run.extend(preflight.commands_run)
    result.commands_not_run.extend(preflight.commands_not_run)
    preflight_status = _mutation_status_from_preflight_issues(preflight.issues)
    if preflight_status == "PASSED":
        result.completion["Mutation Preflight"] = "passed"
    else:
        result.completion["Mutation Status"] = preflight_status
        result.completion["Mutation Preflight"] = f"{preflight_status.lower()}; mutmut body not run"
    return result


def _preflight(target: Target, contract: Contract, targets: list[dict[str, Any]]) -> CheckResult:
    result = CheckResult(target=str(target.relative_path), scope=target.scope)  # type: ignore[arg-type]
    version_command = [sys.executable, "-m", "mutmut", "version"]
    completed = subprocess.run(version_command, cwd=target.repo_root, text=True, capture_output=True, check=False)
    result.commands_run.append(" ".join(version_command))
    if completed.returncode != 0:
        result.add_issue("MUT002", "info", "mutmut is not installed or not executable")
        return result
    version = _parse_version(completed.stdout + completed.stderr)
    if version is None or version < MIN_MUTMUT_VERSION:
        result.add_issue("MUT002", "info", f"mutmut version is unsupported: {completed.stdout.strip() or completed.stderr.strip()}")

    if not hasattr(os, "fork"):
        result.add_issue("MUT002", "info", "current platform lacks fork support required by mutmut")

    if _uses_symbol_scope(targets):
        patch_dependency_command = [sys.executable, "-c", "import whatthepatch"]
        patch_dependency = subprocess.run(
            patch_dependency_command,
            cwd=target.repo_root,
            text=True,
            capture_output=True,
            check=False,
        )
        result.commands_run.append(" ".join(patch_dependency_command))
        if patch_dependency.returncode != 0:
            result.add_issue(
                "MUT002",
                "info",
                "whatthepatch is required for symbol-scoped mutmut --use-patch-file support",
            )

    if not _mutmut_timeout_configured(target.repo_root):
        result.add_issue("MUT005", "info", "mutmut-supported timeout configuration was not found")

    database_url = os.environ.get("DATABASE_URL", "")
    if "test" not in database_url.lower():
        result.add_issue("MUT006", "info", "DATABASE_URL must clearly point to a test database before mutation mode")

    for entry in targets:
        module = entry.get("module")
        refs = entry.get("test_refs")
        if not isinstance(module, str) or not isinstance(refs, list) or not refs:
            result.add_issue("MUT003", "info", "mutation target requires module and test_refs")
            continue
        source_path = _module_to_path(target.repo_root, module)
        if source_path is None or not source_path.exists():
            result.add_issue("MUT003", "info", f"mutation target module cannot be resolved: {module}")
            continue
        if not _source_path_allowed(target.repo_root, source_path):
            result.add_issue("MUT003", "info", f"mutation target is outside supported backend source: {module}")
        symbol_errors = _symbol_scope_errors(entry, source_path)
        for message in symbol_errors:
            result.add_issue("MUT003", "info", message)
        status_command = ["git", "status", "--porcelain", "--", str(source_path)]
        status = subprocess.run(status_command, cwd=target.repo_root, text=True, capture_output=True, check=False)
        result.commands_run.append(" ".join(status_command))
        if status.stdout.strip():
            result.add_issue(
                "MUT003",
                "info",
                f"mutation target has uncommitted changes; backup/restore safety will be used: {source_path}",
            )

    if not _network_blocking_configured(contract):
        result.add_issue("MUT006", "info", "network blocking was not confirmed for mutation mode")

    return result


def _mutation_targets(contract: Contract) -> list[dict[str, Any]]:
    targets = contract.scoped_data.get("mutation_targets")
    if not isinstance(targets, list):
        return []
    return [entry for entry in targets if isinstance(entry, dict)]


def _aggregate_mutation_status(statuses: list[str]) -> str:
    if not statuses:
        return "UNSUPPORTED"
    for status in ("FAILED", "DEFERRED", "UNSUPPORTED"):
        if status in statuses:
            return status
    if all(status == "PASSED" for status in statuses):
        return "PASSED"
    return "DEFERRED"


def _mutation_status_from_preflight_issues(issues: list[Any]) -> str:
    actionable_issues = [
        issue for issue in issues
        if "backup/restore safety will be used" not in issue.message
    ]
    if not actionable_issues:
        return "PASSED"
    unsupported_rules = {"MUT002", "MUT003"}
    if any(issue.rule_id in unsupported_rules for issue in actionable_issues):
        return "UNSUPPORTED"
    return "DEFERRED"


def _mutation_target_schema_errors(targets: list[dict[str, Any]]) -> list[str]:
    allowed_keys = {"id", "source_id", "module", "test_refs", "symbols", "protected_requirement"}
    messages: list[str] = []
    for entry in targets:
        ignored_keys = sorted(set(entry) - allowed_keys)
        if ignored_keys:
            messages.append(
                "mutation targeting supports module plus optional AST symbol scope; unsupported mutation target metadata must be removed: "
                + ", ".join(ignored_keys)
            )
    return messages


def _module_to_path(repo_root: Path, module: str) -> Path | None:
    parts = module.split(".")
    candidates = [
        repo_root / Path(*parts).with_suffix(".py"),
        repo_root / "backend" / Path(*parts).with_suffix(".py"),
        repo_root / "backend" / Path(*parts[1:]).with_suffix(".py") if parts and parts[0] in {"app", "backend"} else repo_root / Path(*parts).with_suffix(".py"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _source_path_allowed(repo_root: Path, source_path: Path) -> bool:
    try:
        relative = source_path.resolve().relative_to(repo_root.resolve() / "backend")
    except ValueError:
        return False
    return (
        "tests" not in relative.parts
        and "alembic" not in relative.parts
        and source_path.name not in {"settings.py", "config.py"}
    )


def _parse_version(output: str) -> tuple[int, int, int] | None:
    match = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", output)
    if not match:
        return None
    return (
        int(match.group(1)),
        int(match.group(2)),
        int(match.group(3) or 0),
    )


def _mutmut_timeout_configured(repo_root: Path) -> bool:
    for config_root in (repo_root, repo_root / "backend"):
        for name in ("pyproject.toml", "setup.cfg", "mutmut_config.py"):
            path = config_root / name
            if path.exists():
                text = path.read_text()
                if (
                    "timeout_factor" in text
                    or "test_time_multiplier" in text
                    or "test-time-multiplier" in text
                ):
                    return True
    return False


def _mutmut_cwd(target: Target) -> Path:
    backend_root = target.repo_root / "backend"
    if (backend_root / "tests").exists():
        return backend_root
    return target.repo_root


def _remove_mutmut_cache(cache_path: Path) -> None:
    if cache_path.is_dir():
        shutil.rmtree(cache_path)
    else:
        cache_path.unlink()


def _mutation_line_scope(
    targets: list[dict[str, Any]],
    source_paths: list[Path | None],
) -> dict[Path, set[int]] | str | None:
    if not _uses_symbol_scope(targets):
        return None
    if any(not entry.get("symbols") for entry in targets):
        return "all mutation targets must declare symbols when symbol-scoped mutation is used"

    scoped_lines: dict[Path, set[int]] = {}
    for entry, source_path in zip(targets, source_paths, strict=True):
        if source_path is None:
            return "could not resolve every mutation target module"
        symbols = _target_symbols(entry)
        if not symbols:
            return f"mutation target has invalid or empty symbols: {entry.get('module')}"
        ranges, missing = _symbol_line_ranges(source_path, symbols)
        if missing:
            return (
                f"mutation target symbols were not found in {source_path}: "
                + ", ".join(missing)
            )
        lines = scoped_lines.setdefault(source_path, set())
        for start, end in ranges.values():
            lines.update(range(start, end + 1))

    if not any(scoped_lines.values()):
        return "mutation symbol scope resolved to no source lines"
    return scoped_lines


def _symbol_scope_errors(entry: dict[str, Any], source_path: Path) -> list[str]:
    if "symbols" not in entry:
        return []
    symbols = _target_symbols(entry)
    if not symbols:
        return [f"mutation target symbols must be a non-empty list of strings: {entry.get('module')}"]
    _ranges, missing = _symbol_line_ranges(source_path, symbols)
    if missing:
        return [
            f"mutation target symbols were not found in {source_path}: "
            + ", ".join(missing)
        ]
    return []


def _target_symbols(entry: dict[str, Any]) -> list[str]:
    raw_symbols = entry.get("symbols")
    if not isinstance(raw_symbols, list):
        return []
    return [symbol for symbol in raw_symbols if isinstance(symbol, str) and symbol]


def _symbol_line_ranges(source_path: Path, symbols: list[str]) -> tuple[dict[str, tuple[int, int]], list[str]]:
    tree = ast.parse(source_path.read_text(), filename=str(source_path))
    wanted = set(symbols)
    ranges: dict[str, tuple[int, int]] = {}
    for node in tree.body:
        for name in _node_symbol_names(node):
            if name in wanted and hasattr(node, "lineno"):
                ranges[name] = (
                    int(node.lineno),
                    int(getattr(node, "end_lineno", node.lineno)),
                )
    missing = [symbol for symbol in symbols if symbol not in ranges]
    return ranges, missing


def _node_symbol_names(node: ast.AST) -> list[str]:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return [node.name]
    if isinstance(node, ast.Assign):
        names: list[str] = []
        for target in node.targets:
            names.extend(_assignment_target_names(target))
        return names
    if isinstance(node, ast.AnnAssign):
        return _assignment_target_names(node.target)
    return []


def _assignment_target_names(target: ast.AST) -> list[str]:
    if isinstance(target, ast.Name):
        return [target.id]
    if isinstance(target, (ast.Tuple, ast.List)):
        names: list[str] = []
        for element in target.elts:
            names.extend(_assignment_target_names(element))
        return names
    return []


def _write_mutation_scope_patch(path: Path, scoped_lines: dict[Path, set[int]]) -> None:
    chunks: list[str] = []
    for source_path, lines in sorted(scoped_lines.items(), key=lambda item: str(item[0])):
        chunks.append(f"--- /dev/null\n+++ {source_path}\n")
        for start, end in _collapse_line_ranges(lines):
            count = end - start + 1
            chunks.append(f"@@ -0,0 +{start},{count} @@\n")
            chunks.extend("+mutation scope\n" for _line in range(start, end + 1))
    path.write_text("".join(chunks))


def _collapse_line_ranges(lines: set[int]) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    start: int | None = None
    previous: int | None = None
    for line in sorted(lines):
        if start is None:
            start = line
            previous = line
            continue
        assert previous is not None
        if line == previous + 1:
            previous = line
            continue
        ranges.append((start, previous))
        start = line
        previous = line
    if start is not None and previous is not None:
        ranges.append((start, previous))
    return ranges


def _run_command_with_heartbeat(command: list[str], *, cwd: Path, env: dict[str, str], label: str) -> ProcessResult:
    baseline_timeout_seconds = _baseline_timeout_seconds()
    batch_timeout_seconds = _batch_timeout_seconds()
    started_at = time.monotonic()
    last_heartbeat = started_at
    output_queue: Queue[str] = Queue()
    output: list[str] = []

    process = subprocess.Popen(
        command,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
        start_new_session=True,
    )

    def read_output() -> None:
        assert process.stdout is not None
        for line in process.stdout:
            output_queue.put(line)

    reader = Thread(target=read_output, daemon=True)
    reader.start()

    timed_out = False
    timeout_kind: str | None = None
    baseline_finished = False
    try:
        while process.poll() is None:
            _drain_output(output_queue, output)
            now = time.monotonic()
            elapsed = int(now - started_at)
            if not baseline_finished and _mutmut_baseline_finished(output):
                baseline_finished = True
            if now - last_heartbeat >= MUTMUT_HEARTBEAT_SECONDS:
                print(
                    f"[backend-test-checker] {label} still running after {elapsed}s",
                    file=sys.stderr,
                    flush=True,
                )
                last_heartbeat = now
            if (
                not baseline_finished
                and baseline_timeout_seconds is not None
                and now - started_at > baseline_timeout_seconds
            ):
                timed_out = True
                timeout_kind = "baseline"
                print(
                    f"[backend-test-checker] {label} baseline exceeded "
                    f"{baseline_timeout_seconds}s hard cap; terminating",
                    file=sys.stderr,
                    flush=True,
                )
                _terminate_process(process)
                break
            if batch_timeout_seconds is not None and now - started_at > batch_timeout_seconds:
                timed_out = True
                timeout_kind = "batch"
                print(
                    f"[backend-test-checker] {label} batch exceeded "
                    f"{batch_timeout_seconds}s hard cap; terminating",
                    file=sys.stderr,
                    flush=True,
                )
                _terminate_process(process)
                break
            time.sleep(0.5)
    except KeyboardInterrupt:
        _terminate_process(process)
        raise

    reader.join(timeout=1)
    _drain_output(output_queue, output)
    return ProcessResult(
        returncode=process.returncode if process.returncode is not None else 124,
        stdout="".join(output),
        timed_out=timed_out,
        timeout_kind=timeout_kind,
    )


def _drain_output(output_queue: Queue[str], output: list[str]) -> None:
    while True:
        try:
            line = output_queue.get_nowait()
        except Empty:
            return
        output.append(line)
        print(line, end="", file=sys.stderr, flush=True)


def _baseline_timeout_seconds() -> int | None:
    return _timeout_seconds(
        "BACKEND_TEST_MUTMUT_BASELINE_TIMEOUT_SECONDS",
        DEFAULT_MUTMUT_BASELINE_TIMEOUT_SECONDS,
    )


def _batch_timeout_seconds() -> int | None:
    raw_legacy = os.environ.get("BACKEND_TEST_MUTMUT_WALL_TIMEOUT_SECONDS")
    if raw_legacy:
        return _parse_timeout_seconds(raw_legacy, DEFAULT_MUTMUT_BATCH_TIMEOUT_SECONDS)
    return _timeout_seconds(
        "BACKEND_TEST_MUTMUT_BATCH_TIMEOUT_SECONDS",
        DEFAULT_MUTMUT_BATCH_TIMEOUT_SECONDS,
    )


def _timeout_seconds(name: str, default: int) -> int | None:
    return _parse_timeout_seconds(os.environ.get(name), default)


def _parse_timeout_seconds(raw: str | None, default: int) -> int | None:
    if raw is None or raw == "":
        return default
    if raw.lower() in {"0", "none", "off", "false"}:
        return None
    try:
        return max(1, int(raw))
    except ValueError:
        return default


def _mutmut_baseline_finished(output: list[str]) -> bool:
    return any("2. Checking mutants" in line for line in output)


def _terminate_process(process: subprocess.Popen[str]) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except (AttributeError, ProcessLookupError, PermissionError):
        process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except (AttributeError, ProcessLookupError, PermissionError):
            process.kill()
        process.wait(timeout=5)


def _network_blocking_configured(contract: Contract) -> bool:
    flags = contract.data.get("review_flags")
    if not isinstance(flags, list):
        return False
    return any(
        isinstance(flag, dict)
        and flag.get("kind") == "network_blocking"
        and flag.get("status") == "confirmed"
        for flag in flags
    )


def _output_mentions_survivors(output: str) -> bool:
    lowered = output.lower()
    return "survived" in lowered or "surviving" in lowered


def _uses_symbol_scope(targets: list[dict[str, Any]]) -> bool:
    return any(bool(entry.get("symbols")) for entry in targets)
