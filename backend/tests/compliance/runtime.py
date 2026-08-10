from __future__ import annotations

import json
import os
import socket
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


EVIDENCE_ENV = "BACKEND_TEST_EVIDENCE_PATH"
NETWORK_BLOCK_ENV = "BACKEND_TEST_BLOCK_NETWORK"

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
    from backend.tests.support.environment_safety import (
        registered_sqlalchemy_tables,
        validate_dedicated_test_database_url,
    )

    parsed_database = validate_dedicated_test_database_url(database_url)
    parsed_database_name = parsed_database.database_name
    assert _is_dedicated_test_database_name(parsed_database_name), (
        "runtime evidence requires DATABASE_URL to point to a dedicated test database"
    )

    from sqlalchemy import text

    from backend.database import engine

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
        table_counts = _cleanup_table_counts(connection, registered_sqlalchemy_tables())

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


def _is_dedicated_test_database_name(database_name: str) -> bool:
    from backend.tests.support.environment_safety import DEDICATED_TEST_DATABASE_NAME

    return database_name == DEDICATED_TEST_DATABASE_NAME


def _cleanup_table_counts(connection: Any, tables: tuple[Any, ...]) -> dict[str, int]:
    from sqlalchemy import text

    from backend.tests.support.environment_safety import (
        cleanup_table_key,
        quoted_table_identifier,
    )

    selects = []
    for table in tables:
        table_key = cleanup_table_key(table)
        table_label = table_key.replace("'", "''")
        selects.append(
            "SELECT "
            f"'{table_label}' AS table_name, "
            f"count(*) AS row_count FROM {quoted_table_identifier(table, connection.dialect)}"
        )
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
