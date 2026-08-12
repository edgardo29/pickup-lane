from __future__ import annotations

import json
import os
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


EVIDENCE_ENV = "BACKEND_TEST_EVIDENCE_PATH"

try:
    import pytest
except Exception:  # pragma: no cover - pytest is available for tests.
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


def _backend_test_evidence(request: Any) -> EvidenceRecorder:
    path_text = os.environ.get(EVIDENCE_ENV)
    return EvidenceRecorder(Path(path_text) if path_text else None, request.node.nodeid)


if pytest is not None:
    backend_test_evidence = pytest.fixture(name="backend_test_evidence")(_backend_test_evidence)
else:  # pragma: no cover
    backend_test_evidence = _backend_test_evidence


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
    before_snapshot: Any = None

    def __enter__(self) -> "EffectAssertion":
        self.before_snapshot = _snapshot(
            session=self.session,
            model=self.model,
            lookup=self.lookup,
            field=self.field,
            kind=self.kind,
        )
        if self.before_expectation is not None:
            _assert_expected_snapshot(self.before_expectation, self.before_snapshot)
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        if exc_type is not None:
            return False
        if self.session is not None and hasattr(self.session, "expire_all"):
            self.session.expire_all()
        after = _snapshot(
            session=self.session,
            model=self.model,
            lookup=self.lookup,
            field=self.field,
            kind=self.kind,
        )
        _assert_effect(self.expect, self.before_snapshot, after, self.value, self.delta)
        self.recorder.record(
            {
                "type": "effect",
                "effect_id": self.effect_id,
                "kind": self.kind,
                "model": getattr(self.model, "__name__", None),
                "table": self.table,
                "lookup": self.lookup,
                "before": self.before_snapshot,
                "after": after,
                "expect": self.expect,
                "value": self.value,
                "delta": self.delta,
                "assertion": "passed",
            }
        )
        return False


def _snapshot(
    *,
    session: Any | None,
    model: Any | None,
    lookup: dict[str, Any],
    field: str | None,
    kind: str,
) -> Any:
    if session is None or model is None:
        return None
    query = session.query(model)
    for name, value in lookup.items():
        query = query.filter(getattr(model, name) == value)
    if kind in {"row_count", "count_delta"}:
        return int(query.count())
    row = query.first()
    if row is None:
        return None
    if field:
        return getattr(row, field)
    return {column.name: getattr(row, column.name) for column in model.__table__.columns}


def _assert_expected_snapshot(expectation: dict[str, Any], snapshot: Any) -> None:
    if "equals" in expectation:
        assert snapshot == expectation["equals"]
    if "in" in expectation:
        assert snapshot in expectation["in"]


def _assert_effect(expect: str, before: Any, after: Any, value: Any, delta: int | None) -> None:
    if expect == "equals":
        assert after == value
    elif expect == "in":
        assert after in value
    elif expect == "changed":
        assert after != before
    elif expect == "unchanged":
        assert after == before
    elif expect == "delta":
        assert before is not None and after is not None
        assert after - before == delta
    else:
        raise AssertionError(f"unsupported effect expectation: {expect}")
