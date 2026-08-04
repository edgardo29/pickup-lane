from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from pathlib import Path
from queue import Empty, Queue
from threading import Thread
from typing import Any
from urllib.parse import urlparse

from .contracts import Contract
from .report import CheckResult
from .targeting import Target


EVIDENCE_ENV = "BACKEND_TEST_EVIDENCE_PATH"
NETWORK_BLOCK_ENV = "BACKEND_TEST_BLOCK_NETWORK"
RUNTIME_HEARTBEAT_SECONDS = 30

try:
    import pytest
except Exception:  # pragma: no cover - pytest is expected in runtime mode.
    pytest = None


@dataclass
class EvidenceRecorder:
    path: Path | None
    test_nodeid: str
    labels: dict[str, dict[str, Any]] = field(default_factory=dict)
    fixture_values: dict[str, Any] = field(default_factory=dict)

    def record(self, payload: dict[str, Any]) -> None:
        if self.path is None:
            return
        record = {"test_nodeid": self.test_nodeid, **payload}
        with self.path.open("a") as handle:
            handle.write(json.dumps(record, default=str, sort_keys=True) + "\n")

    def register_label(self, label: str, fields: dict[str, Any]) -> None:
        self.labels[label] = dict(fields)

    def register_fixture_value(self, name: str, value: Any) -> None:
        self.fixture_values[name] = value


@dataclass(frozen=True)
class RuntimeProcessResult:
    returncode: int
    stdout: str
    stderr: str = ""


def pytest_configure(config: Any) -> None:
    del config


def pytest_runtest_setup(item: Any) -> None:
    if os.environ.get(NETWORK_BLOCK_ENV) != "1":
        return
    original_connect = socket.socket.connect

    def blocked_connect(self: socket.socket, address: Any) -> Any:
        if _network_address_allowed(address):
            return original_connect(self, address)
        raise RuntimeError(f"network access is blocked during backend test compliance runtime validation: {address}")

    socket.socket.connect = blocked_connect  # type: ignore[method-assign]
    item._backend_compliance_original_connect = original_connect


def _restore_network_block(item: Any) -> None:
    original_connect = getattr(item, "_backend_compliance_original_connect", None)
    if original_connect is not None:
        socket.socket.connect = original_connect  # type: ignore[method-assign]


if pytest is not None:

    @pytest.hookimpl(hookwrapper=True, trylast=True)
    def pytest_runtest_teardown(item: Any, nextitem: Any) -> Any:
        del nextitem
        yield
        _restore_network_block(item)
        _record_isolation_evidence(item)

else:

    def pytest_runtest_teardown(item: Any) -> None:  # pragma: no cover
        _restore_network_block(item)


def pytest_report_header(config: Any) -> str:
    del config
    if os.environ.get(EVIDENCE_ENV):
        return "backend compliance evidence recording enabled"
    return ""


def _backend_test_evidence(request: Any) -> EvidenceRecorder:
    path_text = os.environ.get(EVIDENCE_ENV)
    return EvidenceRecorder(Path(path_text) if path_text else None, request.node.nodeid)


def _network_address_allowed(address: Any) -> bool:
    allowed = _allowed_database_address()
    if allowed is None:
        return False
    if not isinstance(address, tuple) or len(address) < 2:
        return False
    host = str(address[0])
    try:
        port = int(address[1])
    except (TypeError, ValueError):
        return False
    allowed_host, allowed_port = allowed
    if port != allowed_port:
        return False
    local_hosts = {"localhost", "127.0.0.1", "::1"}
    if allowed_host in local_hosts and host in local_hosts:
        return True
    return host == allowed_host


def _allowed_database_address() -> tuple[str, int] | None:
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        return None
    parsed = urlparse(database_url)
    host = parsed.hostname
    if host is None:
        return None
    return host, parsed.port or 5432


def _record_isolation_evidence(item: Any) -> None:
    path_text = os.environ.get(EVIDENCE_ENV)
    if not path_text:
        return
    database_url = os.environ.get("DATABASE_URL", "")
    parsed_database_name = _database_name_from_url(database_url)
    assert _is_dedicated_test_database_name(parsed_database_name), (
        "runtime evidence requires DATABASE_URL to point to a dedicated test database"
    )

    from sqlalchemy import text

    from backend.database import engine
    from backend.tests.conftest import TEST_TABLES

    recorder = EvidenceRecorder(Path(path_text), item.nodeid)
    with engine.connect() as connection:
        identity = connection.execute(
            text(
                "SELECT current_database() AS database_name, "
                "pg_backend_pid() AS backend_pid, "
                "txid_current() AS transaction_id"
            )
        ).mappings().one()
        current_database = str(identity["database_name"])
        assert current_database == parsed_database_name
        assert _is_dedicated_test_database_name(current_database)
        table_counts = _cleanup_table_counts(connection, TEST_TABLES)

    nonempty_tables = {
        table: count for table, count in table_counts.items() if count != 0
    }
    assert not nonempty_tables, (
        "runtime database cleanup did not complete for tables: "
        f"{sorted(nonempty_tables)}"
    )
    recorder.record(
        {
            "type": "isolation",
            "isolation_id": "RUN007-DB-ISOLATION",
            "database_name": current_database,
            "database_host": urlparse(database_url).hostname,
            "backend_pid": identity["backend_pid"],
            "transaction_id": identity["transaction_id"],
            "cleanup_mechanism": "backend.tests.conftest.clean_database truncate before/after",
            "cleanup_table_count": len(table_counts),
            "cleanup_nonempty_tables": nonempty_tables,
            "cleanup_complete": True,
            "assertion": "passed",
        }
    )


def _database_name_from_url(database_url: str) -> str:
    parsed = urlparse(database_url)
    return parsed.path.rsplit("/", maxsplit=1)[-1]


def _is_dedicated_test_database_name(database_name: str) -> bool:
    normalized = database_name.lower()
    banned = {"dev", "development", "stage", "staging", "prod", "production"}
    return bool(normalized) and "test" in normalized and not any(
        banned_name in normalized for banned_name in banned
    )


def _cleanup_table_counts(connection: Any, tables: tuple[str, ...]) -> dict[str, int]:
    from sqlalchemy import text

    selects = []
    for table in tables:
        _validate_identifier(table)
        selects.append(f"SELECT '{table}' AS table_name, count(*) AS row_count FROM {table}")
    rows = connection.execute(text(" UNION ALL ".join(selects))).mappings().all()
    return {str(row["table_name"]): int(row["row_count"]) for row in rows}


if pytest is not None:
    backend_test_evidence = pytest.fixture(name="backend_test_evidence")(_backend_test_evidence)
else:  # pragma: no cover
    backend_test_evidence = _backend_test_evidence


def assert_effect(
    recorder: EvidenceRecorder,
    *,
    effect_id: str,
    kind: str,
    session: Any | None = None,
    model: Any | None = None,
    table: str | None = None,
    lookup: dict[str, Any] | None = None,
    field: str | None = None,
    before: dict[str, Any] | None = None,
    expect: str,
    value: Any = None,
    delta: int | None = None,
) -> "EffectAssertion":
    return EffectAssertion(
        recorder=recorder,
        effect_id=effect_id,
        kind=kind,
        session=session,
        model=model,
        table=table,
        lookup=lookup or {},
        field=field,
        before_expectation=before,
        expect=expect,
        value=value,
        delta=delta,
    )


def assert_external_call_count(
    recorder: EvidenceRecorder,
    *,
    effect_id: str,
    mock: Any,
    expect: str,
    value: int | None = None,
    delta: int | None = None,
) -> "ExternalCallCountAssertion":
    return ExternalCallCountAssertion(
        recorder=recorder,
        effect_id=effect_id,
        mock=mock,
        expect=expect,
        value=value,
        delta=delta,
    )


def assert_constraint_failure(
    recorder: EvidenceRecorder,
    *,
    constraint_id: str,
    expected_identifier: str,
    session: Any | None = None,
    model: Any | None = None,
    lookup: dict[str, Any] | None = None,
) -> "ConstraintFailureAssertion":
    return ConstraintFailureAssertion(
        recorder=recorder,
        constraint_id=constraint_id,
        expected_identifier=expected_identifier,
        session=session,
        model=model,
        lookup=lookup or {},
    )


def assert_rollback(
    recorder: EvidenceRecorder,
    *,
    effect_id: str,
    session: Any,
    model: Any,
    lookup: dict[str, Any],
    field: str | None = None,
) -> "RollbackAssertion":
    return RollbackAssertion(
        recorder=recorder,
        effect_id=effect_id,
        session=session,
        model=model,
        lookup=lookup,
        field=field,
    )


def assert_time_boundary(
    recorder: EvidenceRecorder,
    *,
    time_id: str,
    baseline: Any,
    boundary: str,
    actual: Any,
    expected: Any,
) -> None:
    assert actual == expected
    recorder.record(
        {
            "type": "time_boundary",
            "time_id": time_id,
            "baseline": baseline,
            "boundary": boundary,
            "actual": actual,
            "expected": expected,
            "assertion": "passed",
        }
    )


@dataclass
class EffectAssertion(AbstractContextManager["EffectAssertion"]):
    recorder: EvidenceRecorder
    effect_id: str
    kind: str
    session: Any | None
    model: Any | None
    table: str | None
    lookup: dict[str, Any]
    field: str | None
    before_expectation: dict[str, Any] | None
    expect: str
    value: Any = None
    delta: int | None = None
    before_snapshot: dict[str, Any] | None = None

    def __enter__(self) -> "EffectAssertion":
        resolved_lookup = _resolve_lookup(self.recorder, self.lookup)
        self.before_snapshot = _snapshot(
            session=self.session,
            model=self.model,
            table=self.table,
            lookup=resolved_lookup,
            field=self.field,
            kind=self.kind,
        )
        if self.before_expectation is not None:
            _assert_snapshot_expectation(
                self.before_expectation,
                self.before_snapshot,
                label="before",
            )
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        if exc_type is not None:
            return False
        resolved_lookup = _resolve_lookup(self.recorder, self.lookup)
        if self.session is not None and hasattr(self.session, "expire_all"):
            self.session.expire_all()
        after = _snapshot(
            session=self.session,
            model=self.model,
            table=self.table,
            lookup=resolved_lookup,
            field=self.field,
            kind=self.kind,
        )
        assert self.before_snapshot is not None
        _assert_effect_expectation(
            self.expect,
            self.before_snapshot,
            after,
            self.value,
            self.delta,
        )
        self.recorder.record(
            {
                "type": "effect",
                "effect_id": self.effect_id,
                "kind": self.kind,
                "model": _model_name(self.model),
                "table": self.table,
                "lookup": self.lookup,
                "resolved_lookup": resolved_lookup,
                "before": self.before_snapshot,
                "before_expectation": self.before_expectation,
                "after": after,
                "expect": self.expect,
                "value": self.value,
                "delta": self.delta,
                "assertion": "passed",
            }
        )
        return False


@dataclass
class ExternalCallCountAssertion(AbstractContextManager["ExternalCallCountAssertion"]):
    recorder: EvidenceRecorder
    effect_id: str
    mock: Any
    expect: str
    value: int | None
    delta: int | None
    before: int = 0

    def __enter__(self) -> "ExternalCallCountAssertion":
        self.before = int(getattr(self.mock, "call_count"))
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        if exc_type is not None:
            return False
        after = int(getattr(self.mock, "call_count"))
        observed_delta = after - self.before
        if self.expect == "equals":
            assert after == self.value
        elif self.expect == "delta":
            assert observed_delta == self.delta
        else:
            raise AssertionError(f"unsupported external call count expectation: {self.expect}")
        self.recorder.record(
            {
                "type": "effect",
                "effect_id": self.effect_id,
                "kind": "external_call_count",
                "before": self.before,
                "after": after,
                "expect": self.expect,
                "value": self.value,
                "delta": self.delta,
                "assertion": "passed",
            }
        )
        return False


@dataclass
class ConstraintFailureAssertion(AbstractContextManager["ConstraintFailureAssertion"]):
    recorder: EvidenceRecorder
    constraint_id: str
    expected_identifier: str
    session: Any | None
    model: Any | None
    lookup: dict[str, Any]

    def __enter__(self) -> "ConstraintFailureAssertion":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        if exc_type is None:
            raise AssertionError("expected database constraint failure, but no exception was raised")
        identifier = _constraint_identifier(exc)
        message = str(exc)
        matched = identifier == self.expected_identifier or self.expected_identifier in message
        if self.session is not None:
            self.session.rollback()
        post_rollback = None
        if self.session is not None and self.model is not None and self.lookup:
            resolved_lookup = _resolve_lookup(self.recorder, self.lookup)
            post_rollback = _snapshot(
                session=self.session,
                model=self.model,
                table=None,
                lookup=resolved_lookup,
                field=None,
                kind="row_absent",
            )
        assert matched, f"expected constraint {self.expected_identifier}, got {identifier or message}"
        self.recorder.record(
            {
                "type": "constraint",
                "constraint_id": self.constraint_id,
                "expected_identifier": self.expected_identifier,
                "observed_identifier": identifier,
                "message": message,
                "lookup": self.lookup,
                "post_rollback": post_rollback,
                "assertion": "passed",
            }
        )
        return True


@dataclass
class RollbackAssertion(AbstractContextManager["RollbackAssertion"]):
    recorder: EvidenceRecorder
    effect_id: str
    session: Any
    model: Any
    lookup: dict[str, Any]
    field: str | None
    before: dict[str, Any] | None = None

    def __enter__(self) -> "RollbackAssertion":
        resolved_lookup = _resolve_lookup(self.recorder, self.lookup)
        self.before = _snapshot(
            session=self.session,
            model=self.model,
            table=None,
            lookup=resolved_lookup,
            field=self.field,
            kind="field_unchanged" if self.field else "row_count",
        )
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        if exc_type is None:
            raise AssertionError("expected rollback assertion to wrap a failing transaction")
        self.session.rollback()
        resolved_lookup = _resolve_lookup(self.recorder, self.lookup)
        after = _snapshot(
            session=self.session,
            model=self.model,
            table=None,
            lookup=resolved_lookup,
            field=self.field,
            kind="field_unchanged" if self.field else "row_count",
        )
        assert self.before == after
        self.recorder.record(
            {
                "type": "rollback",
                "effect_id": self.effect_id,
                "model": _model_name(self.model),
                "lookup": self.lookup,
                "resolved_lookup": resolved_lookup,
                "before": self.before,
                "after": after,
                "exception": str(exc),
                "assertion": "passed",
            }
        )
        return True


def evaluate_runtime_requirement(contract: Contract, requested: bool) -> CheckResult:
    result = CheckResult(target=str(contract.path.parent), scope=None)
    required = _runtime_required_ids(contract)
    required_ids = [item_id for _kind, item_id in sorted(required)]
    if required and not requested:
        result.add_issue(
            "RUN002",
            "blocker",
            "runtime evidence is required but --runtime was not requested",
        )
        result.commands_not_run.append("pytest target with compliance evidence plugin")
        result.completion["Runtime Evidence"] = (
            f"required but not run; declared ids: {', '.join(required_ids)}"
        )
    elif required:
        result.completion["Runtime Evidence"] = (
            f"requested; declared ids: {', '.join(required_ids)}"
        )
    else:
        result.completion["Runtime Evidence"] = "not required; no effects, constraints, or time boundaries declared"
    return result


def run_runtime_validation(target: Target, contract: Contract) -> CheckResult:
    result = CheckResult(target=str(target.relative_path), scope=target.scope)  # type: ignore[arg-type]
    required = _runtime_required_ids(contract)
    if not required:
        result.commands_not_run.append("pytest target with compliance evidence plugin (no runtime evidence declared)")
        result.completion["Runtime Evidence"] = "not run; no runtime evidence declared"
        return result

    evidence_path = Path(tempfile.mkdtemp(prefix="backend-test-compliance-")) / "evidence.jsonl"
    pytest_target = str(target.path)
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-p",
        "compliance.runtime",
        pytest_target,
    ]
    env = os.environ.copy()
    env[EVIDENCE_ENV] = str(evidence_path)
    env[NETWORK_BLOCK_ENV] = "1"
    env["PYTHONPATH"] = f"{target.tests_root}{os.pathsep}{env.get('PYTHONPATH', '')}"
    completed = _run_pytest_with_heartbeat(command, cwd=target.repo_root, env=env)
    result.commands_run.append(" ".join(command))
    if completed.returncode != 0:
        output_path = evidence_path.with_name("pytest-output.txt")
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
                ]
            )
        )
        result.add_issue(
            "RUN003",
            "failure",
            f"targeted pytest runtime validation failed; captured output: {output_path}",
        )
        result.completion["Runtime Evidence"] = (
            f"runtime pytest failed before evidence could be validated; "
            f"captured output: {output_path}"
        )
        return result
    records = _read_evidence(evidence_path)
    _validate_runtime_records(contract, records, result)
    result.completion["Runtime Evidence"] = f"{len(records)} evidence record(s) captured"
    return result


def _run_pytest_with_heartbeat(command: list[str], *, cwd: Path, env: dict[str, str]) -> RuntimeProcessResult:
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
    try:
        while process.poll() is None:
            _drain_process_output(output_queue, output)
            now = time.monotonic()
            if now - last_heartbeat >= RUNTIME_HEARTBEAT_SECONDS:
                elapsed = int(now - started_at)
                print(
                    f"[backend-test-checker] runtime pytest still running after {elapsed}s",
                    file=sys.stderr,
                    flush=True,
                )
                last_heartbeat = now
            time.sleep(0.5)
    except KeyboardInterrupt:
        _terminate_process(process)
        raise

    reader.join(timeout=1)
    _drain_process_output(output_queue, output)
    return RuntimeProcessResult(
        returncode=process.returncode if process.returncode is not None else 124,
        stdout="".join(output),
    )


def _drain_process_output(output_queue: Queue[str], output: list[str]) -> None:
    while True:
        try:
            line = output_queue.get_nowait()
        except Empty:
            return
        output.append(line)
        print(line, end="", file=sys.stderr, flush=True)


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


def _runtime_required_ids(contract: Contract) -> set[tuple[str, str]]:
    required: set[tuple[str, str]] = set()
    for effect in contract.scoped_data.get("effects", []) or []:
        if isinstance(effect, dict) and effect.get("id"):
            required.add(("effect", str(effect["id"])))
    for constraint in contract.scoped_data.get("constraints", []) or []:
        if isinstance(constraint, dict) and constraint.get("id"):
            required.add(("constraint", str(constraint["id"])))
    for boundary in contract.scoped_data.get("time_boundaries", []) or []:
        if isinstance(boundary, dict) and boundary.get("id"):
            required.add(("time_boundary", str(boundary["id"])))
    return required


def _read_evidence(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        records.append(json.loads(line))
    return records


def _validate_runtime_records(contract: Contract, records: list[dict[str, Any]], result: CheckResult) -> None:
    effect_records: dict[str, dict[str, Any]] = {
        str(record.get("effect_id")): record
        for record in records
        if record.get("type") in {"effect", "rollback"} and record.get("effect_id")
    }
    constraint_records: dict[str, dict[str, Any]] = {
        str(record.get("constraint_id")): record
        for record in records
        if record.get("type") == "constraint" and record.get("constraint_id")
    }
    time_records_by_id: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        if record.get("type") == "time_boundary" and record.get("time_id"):
            time_records_by_id.setdefault(str(record["time_id"]), []).append(record)

    for effect in contract.scoped_data.get("effects", []) or []:
        if not isinstance(effect, dict):
            continue
        rule_id = _runtime_rule_for_effect(effect)
        record = effect_records.get(str(effect.get("id")))
        if record is None:
            result.add_issue(rule_id, "blocker", f"missing runtime effect evidence: {effect.get('id')}")
            continue
        _validate_effect_record(effect, record, rule_id, result)
    for constraint in contract.scoped_data.get("constraints", []) or []:
        if not isinstance(constraint, dict):
            continue
        record = constraint_records.get(str(constraint.get("id")))
        if record is None:
            result.add_issue("RUN006", "blocker", f"missing runtime constraint evidence: {constraint.get('id')}")
            continue
        expected_identifier = constraint.get("expected_database_identifier")
        if record.get("expected_identifier") != expected_identifier:
            result.add_issue("RUN006", "failure", f"constraint evidence identifier mismatch: {constraint.get('id')}")
    for boundary in contract.scoped_data.get("time_boundaries", []) or []:
        if not isinstance(boundary, dict):
            continue
        records_for_boundary = time_records_by_id.get(str(boundary.get("id")), [])
        if not records_for_boundary:
            result.add_issue("RUN009", "blocker", f"missing runtime time-boundary evidence: {boundary.get('id')}")
            continue
        expected_cases = set(boundary.get("boundary_cases", []))
        observed_cases = {record.get("boundary") for record in records_for_boundary}
        if expected_cases and not expected_cases.issubset(observed_cases):
            missing = sorted(expected_cases - observed_cases)
            result.add_issue("RUN009", "blocker", f"missing time-boundary case evidence for {boundary.get('id')}: {missing}")
        if any("baseline" not in record for record in records_for_boundary):
            result.add_issue("RUN010", "blocker", f"time-boundary evidence lacks controlled baseline: {boundary.get('id')}")

    if _runtime_required_ids(contract) and not _has_isolation_evidence(records):
        result.add_issue(
            "RUN007",
            "blocker",
            "runtime database isolation evidence is required; include rollback or deterministic cleanup evidence",
        )


def _has_isolation_evidence(records: list[dict[str, Any]]) -> bool:
    for record in records:
        if record.get("type") == "rollback" and record.get("assertion") == "passed":
            return True
        if (
            record.get("type") == "isolation"
            and record.get("assertion") == "passed"
            and record.get("cleanup_complete") is True
            and _is_dedicated_test_database_name(str(record.get("database_name", "")))
        ):
            return True
    return False


def _runtime_rule_for_effect(effect: dict[str, Any]) -> str:
    if effect.get("kind") == "external_call_count":
        return "RUN008"
    if effect.get("phase") == "idempotency":
        return "RUN005"
    if effect.get("phase") == "rollback":
        return "RUN006"
    return "RUN004"


def _validate_effect_record(effect: dict[str, Any], record: dict[str, Any], rule_id: str, result: CheckResult) -> None:
    effect_id = effect.get("id")
    if record.get("kind") != effect.get("kind"):
        result.add_issue(rule_id, "failure", f"runtime evidence kind mismatch: {effect_id}")
    if effect.get("model") and record.get("model") and effect.get("model") != record.get("model"):
        result.add_issue(rule_id, "failure", f"runtime evidence model mismatch: {effect_id}")
    if effect.get("table") and record.get("table") and effect.get("table") != record.get("table"):
        result.add_issue(rule_id, "failure", f"runtime evidence table mismatch: {effect_id}")
    before = effect.get("before")
    if isinstance(before, dict):
        if not isinstance(record.get("before"), dict):
            result.add_issue(rule_id, "failure", f"runtime evidence lacks before snapshot: {effect_id}")
        else:
            _validate_snapshot_record(before, record["before"], rule_id, effect_id, "before", result)
    after = effect.get("after")
    if isinstance(after, dict):
        expected_expect = after.get("expect")
        expected_value = after.get("value")
        if "equals" in after:
            expected_expect = "equals"
            expected_value = after["equals"]
        elif "in" in after:
            expected_expect = "in"
            expected_value = after["in"]
        if expected_expect and record.get("expect") != expected_expect:
            result.add_issue(rule_id, "failure", f"runtime evidence expectation mismatch: {effect_id}")
        if expected_value is not None and record.get("value") != expected_value:
            result.add_issue(rule_id, "failure", f"runtime evidence value mismatch: {effect_id}")
        if "delta" in after and record.get("delta") != after.get("delta"):
            result.add_issue(rule_id, "failure", f"runtime evidence delta mismatch: {effect_id}")
        if isinstance(record.get("after"), dict):
            _validate_snapshot_record(after, record["after"], rule_id, effect_id, "after", result)


def _validate_snapshot_record(
    expectation: dict[str, Any],
    snapshot: dict[str, Any],
    rule_id: str,
    effect_id: Any,
    phase: str,
    result: CheckResult,
) -> None:
    try:
        _assert_snapshot_expectation(expectation, snapshot, label=phase)
    except AssertionError as exc:
        result.add_issue(
            rule_id,
            "failure",
            f"runtime evidence {phase} snapshot mismatch for {effect_id}: {exc}",
        )


def _snapshot(
    *,
    session: Any | None,
    model: Any | None,
    table: str | None,
    lookup: dict[str, Any],
    field: str | None,
    kind: str,
) -> dict[str, Any]:
    if session is None:
        raise AssertionError("database effect assertions require a session")
    rows = _query_rows(session=session, model=model, table=table, lookup=lookup)
    snapshot: dict[str, Any] = {"count": len(rows), "exists": bool(rows)}
    if field:
        snapshot["field"] = field
        snapshot["field_values"] = [_row_field(row, field) for row in rows]
        snapshot["field_value"] = snapshot["field_values"][0] if rows else None
    if kind == "timestamp_set" and field:
        snapshot["timestamp_set"] = bool(snapshot.get("field_value"))
    return snapshot


def _query_rows(session: Any, model: Any | None, table: str | None, lookup: dict[str, Any]) -> list[Any]:
    if model is not None:
        query = session.query(model)
        for key, value in lookup.items():
            query = query.filter(getattr(model, key) == value)
        return list(query.all())
    if table is not None:
        try:
            from sqlalchemy import text
        except Exception as exc:  # pragma: no cover - depends on optional SQLAlchemy.
            raise AssertionError("table-based evidence requires SQLAlchemy") from exc
        _validate_identifier(table)
        clauses = []
        params = {}
        for key, value in lookup.items():
            _validate_identifier(key)
            param = f"p_{key}"
            clauses.append(f"{key} = :{param}")
            params[param] = value
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = session.execute(text(f"SELECT * FROM {table}{where}"), params).mappings().all()
        return list(rows)
    raise AssertionError("effect assertion requires model or table")


def _resolve_lookup(recorder: EvidenceRecorder, lookup: dict[str, Any]) -> dict[str, Any]:
    by = lookup.get("by")
    if by is None:
        return dict(lookup)
    if by == "field_values":
        fields = lookup.get("fields")
        if not isinstance(fields, dict):
            raise AssertionError("field_values lookup requires fields")
        return dict(fields)
    if by == "contract_label":
        label = lookup.get("label")
        if not isinstance(label, str) or label not in recorder.labels:
            raise AssertionError(f"unknown evidence lookup label: {label}")
        return dict(recorder.labels[label])
    if by == "fixture_value":
        name = lookup.get("name")
        field_name = lookup.get("field") or name
        if not isinstance(name, str) or name not in recorder.fixture_values:
            raise AssertionError(f"unknown evidence fixture value: {name}")
        if not isinstance(field_name, str):
            raise AssertionError("fixture_value lookup field must be a string")
        return {field_name: recorder.fixture_values[name]}
    raise AssertionError(f"unsupported evidence lookup mechanism: {by}")


def _validate_identifier(value: str) -> None:
    if not value.replace("_", "").isalnum():
        raise AssertionError(f"unsafe SQL identifier for evidence helper: {value}")


def _row_field(row: Any, field: str) -> Any:
    if isinstance(row, dict):
        return row.get(field)
    return getattr(row, field)


def _assert_effect_expectation(expect: str, before: dict[str, Any], after: dict[str, Any], value: Any, delta: int | None) -> None:
    if expect == "equals":
        if "field_value" in after:
            assert after["field_value"] == value
        else:
            assert after["count"] == value
    elif expect == "in":
        assert "field_value" in after
        assert isinstance(value, (list, tuple, set))
        assert after["field_value"] in value
    elif expect == "exists":
        assert after["exists"] is True
    elif expect == "absent":
        assert after["exists"] is False
    elif expect == "unchanged":
        assert after == before
    elif expect == "changed":
        assert after != before
    elif expect == "delta":
        assert delta is not None
        assert after["count"] - before["count"] == delta
    else:
        raise AssertionError(f"unsupported effect expectation: {expect}")


def _assert_snapshot_expectation(
    expectation: dict[str, Any],
    snapshot: dict[str, Any],
    *,
    label: str,
) -> None:
    if "equals" in expectation:
        expected = expectation["equals"]
        actual = snapshot.get("field_value", snapshot.get("count"))
        assert actual == expected, f"{label} expected {expected!r}, got {actual!r}"
    elif "in" in expectation:
        expected_values = expectation["in"]
        assert isinstance(expected_values, (list, tuple, set))
        actual = snapshot.get("field_value")
        assert actual in expected_values, (
            f"{label} expected one of {expected_values!r}, got {actual!r}"
        )
    elif expectation.get("expect") == "equals":
        expected = expectation.get("value")
        actual = snapshot.get("field_value", snapshot.get("count"))
        assert actual == expected, f"{label} expected {expected!r}, got {actual!r}"
    elif expectation.get("expect") == "exists":
        assert snapshot.get("exists") is True, f"{label} row does not exist"
    elif expectation.get("expect") == "absent":
        assert snapshot.get("exists") is False, f"{label} row exists"


def _constraint_identifier(exc: BaseException) -> str | None:
    current: Any = exc
    for attr in ("orig", "__cause__", "__context__"):
        current = getattr(current, attr, None)
        if current is None:
            continue
        diag = getattr(current, "diag", None)
        if diag is not None:
            name = getattr(diag, "constraint_name", None)
            if name:
                return str(name)
        name = getattr(current, "constraint_name", None)
        if name:
            return str(name)
    return None


def _model_name(model: Any | None) -> str | None:
    if model is None:
        return None
    return f"{model.__module__}.{model.__name__}"
