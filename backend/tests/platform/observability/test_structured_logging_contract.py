from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone

import pytest

from backend.observability.correlation import correlation_context, get_correlation_id
from backend.observability.events import EventEnvelope, EventEnvelopeError
from backend.observability.structured_logging import (
    APPLICATION_LOGGER_NAME,
    RuntimeEventEmitter,
    SafeJsonHandler,
    configure_process_logging,
    emit_durable_job_event,
    emit_event,
)

pytestmark = [
    pytest.mark.no_db_cleanup,
    pytest.mark.requirement("WS09-01A"),
]


def _emitter(
    *, source: str = "api", release: str = "test-release"
) -> RuntimeEventEmitter:
    emitter = RuntimeEventEmitter(
        source_identity=source,
        environment="test",
        release=release,
    )
    configure_process_logging(emitter, configure_uvicorn=source == "api")
    return emitter


def _records(capsys: pytest.CaptureFixture[str]) -> list[dict[str, object]]:
    output = capsys.readouterr()
    assert output.err == ""
    return [json.loads(line) for line in output.out.splitlines()]


@pytest.mark.parametrize(
    "values",
    [
        {"source_identity": "web", "environment": "test", "release": "release"},
        {
            "source_identity": "api",
            "environment": "bad environment",
            "release": "release",
        },
        {"source_identity": "worker", "environment": "test", "release": "x" * 121},
        {"source_identity": "api", "environment": None, "release": "release"},
        {"source_identity": "worker", "environment": "test", "release": None},
    ],
)
def test_runtime_emitter_rejects_invalid_process_metadata_at_activation(
    values: dict[str, object],
) -> None:
    with pytest.raises((EventEnvelopeError, TypeError, ValueError)):
        RuntimeEventEmitter(**values)  # type: ignore[arg-type]


def test_runtime_envelope_additive_fields_have_exact_bounded_shape() -> None:
    job_id = str(uuid.uuid4())
    envelope = EventEnvelope(
        event_name="durable_job.processed",
        occurred_at=datetime(2026, 9, 14, tzinfo=timezone.utc),
        severity="warning",
        source_identity="worker",
        environment="test",
        release="release-1",
        resource_kind="durable_job",
        resource_id=job_id,
        http_method="post",
        http_status_code=503,
        attempt_count=2,
        maximum_attempts=3,
    )

    assert envelope.to_dict() == {
        "attempt_count": 2,
        "environment": "test",
        "event_name": "durable_job.processed",
        "http_method": "post",
        "http_status_code": 503,
        "maximum_attempts": 3,
        "occurred_at": "2026-09-14T00:00:00Z",
        "release": "release-1",
        "resource_id": job_id,
        "resource_kind": "durable_job",
        "schema_version": "1",
        "severity": "warning",
        "source_identity": "worker",
    }


@pytest.mark.parametrize(
    "overrides",
    [
        {"severity": "notice"},
        {"http_method": "trace"},
        {"http_status_code": 99},
        {"http_status_code": 600},
        {"http_status_code": True},
        {"attempt_count": -1},
        {"maximum_attempts": 0},
        {"attempt_count": 2, "maximum_attempts": 1},
        {"release": "x" * 121},
        {"source_identity": "x" * 121},
        {"resource_kind": "payment", "resource_id": str(uuid.uuid4())},
        {"resource_kind": "durable_job", "resource_id": str(uuid.uuid4()).upper()},
    ],
)
def test_runtime_envelope_rejects_each_new_invalid_boundary(
    overrides: dict[str, object],
) -> None:
    values: dict[str, object] = {
        "event_name": "runtime.test",
        "occurred_at": datetime.now(timezone.utc),
    }
    values.update(overrides)

    with pytest.raises(EventEnvelopeError):
        EventEnvelope(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "fields",
    [
        {"unknown": "private-canary"},
        {"correlation_id": "private-canary"},
        {"request_id": "private-canary"},
        {"resource_id": "private-canary"},
        {"operation": "user@example.invalid"},
    ],
)
def test_general_emitter_rejects_unknown_owner_fields_without_input_leakage(
    capsys: pytest.CaptureFixture[str],
    fields: dict[str, object],
) -> None:
    _emitter()

    assert emit_event("runtime.private_canary", "info", fields) is True

    records = _records(capsys)
    assert len(records) == 1
    assert records[0]["event_name"] == "logging.event_rejected"
    assert "private" not in json.dumps(records[0]).lower()


def test_general_emitter_uses_only_active_canonical_correlation(
    capsys: pytest.CaptureFixture[str],
) -> None:
    _emitter()
    correlation_id = str(uuid.uuid4())

    with correlation_context(correlation_id):
        assert emit_event("runtime.test", "info", {"result": "success"}) is True

    assert get_correlation_id() is None
    assert _records(capsys)[0]["correlation_id"] == correlation_id


def test_only_durable_wrapper_populates_resource_id(
    capsys: pytest.CaptureFixture[str],
) -> None:
    emitter = _emitter(source="worker")
    job_id = uuid.uuid4()

    assert emit_durable_job_event(
        emitter,
        job_id,
        "info",
        {
            "attempt_count": 1,
            "maximum_attempts": 3,
            "result": "succeeded",
            "labels": {"job_type": "synthetic_job"},
        },
    )

    record = _records(capsys)[0]
    assert record["resource_kind"] == "durable_job"
    assert record["resource_id"] == str(job_id)


def test_serialization_failure_drops_without_rejection_or_stderr(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _emitter()
    monkeypatch.setattr(
        EventEnvelope,
        "to_json",
        lambda self: (_ for _ in ()).throw(RuntimeError("private-canary")),
    )

    assert emit_event("runtime.test", "info", {"result": "success"}) is False
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err == ""


def test_stream_write_failure_is_nonthrowing_and_does_not_recurse(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _emitter()

    class FailingStream:
        def write(self, value: str) -> None:
            del value
            raise RuntimeError("private-canary")

        def flush(self) -> None:
            raise RuntimeError("private-canary")

    monkeypatch.setattr(
        "backend.observability.structured_logging.sys.stdout", FailingStream()
    )

    assert emit_event("runtime.test", "info", {"result": "success"}) is False
    assert capsys.readouterr().err == ""


def test_stream_flush_failure_is_nonthrowing_and_does_not_recurse(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _emitter()

    class FailingFlushStream:
        def __init__(self) -> None:
            self.values: list[str] = []

        def write(self, value: str) -> None:
            self.values.append(value)

        def flush(self) -> None:
            raise RuntimeError("private-canary")

    stream = FailingFlushStream()
    monkeypatch.setattr("backend.observability.structured_logging.sys.stdout", stream)

    assert emit_event("runtime.test", "info", {"result": "success"}) is False
    assert len(stream.values) == 1
    assert json.loads(stream.values[0])["event_name"] == "runtime.test"
    assert capsys.readouterr().err == ""


def test_direct_application_logger_calls_cannot_bypass_validated_transport(
    capsys: pytest.CaptureFixture[str],
) -> None:
    _emitter()
    private_text = "Bearer private-canary user@example.invalid"

    logging.getLogger(APPLICATION_LOGGER_NAME).warning(private_text)
    logging.getLogger(f"{APPLICATION_LOGGER_NAME}.child").error(private_text)

    output = capsys.readouterr()
    assert output.out == ""
    assert output.err == ""


def test_handler_internal_failure_is_nonthrowing_and_silent(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _emitter()

    def fail_emit(self, record):
        del self, record
        raise RuntimeError("private-canary")

    monkeypatch.setattr(SafeJsonHandler, "emit", fail_emit)

    assert emit_event("runtime.test", "info", {"result": "success"}) is False
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err == ""


def test_custom_handler_failure_is_nonthrowing_and_silent(
    capsys: pytest.CaptureFixture[str],
) -> None:
    _emitter()

    class FailingHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            del record
            raise RuntimeError("private-canary")

    logging.getLogger(APPLICATION_LOGGER_NAME).handlers = [FailingHandler()]

    assert emit_event("runtime.test", "info", {"result": "success"}) is False
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err == ""


def test_uvicorn_handlers_drop_access_and_normalize_arbitrary_runtime_records(
    capsys: pytest.CaptureFixture[str],
) -> None:
    _emitter()
    private_text = "Bearer private-canary user@example.invalid"

    logging.getLogger("uvicorn.access").warning(private_text, "argument")
    try:
        raise RuntimeError(private_text)
    except RuntimeError:
        logging.getLogger("uvicorn.error").exception(
            private_text,
            "argument",
        )

    records = _records(capsys)
    assert len(records) == 1
    assert records[0]["event_name"] == "runtime.framework"
    assert records[0]["severity"] == "error"
    assert records[0]["operation"] == "uvicorn.runtime"
    assert private_text not in json.dumps(records)


def test_repeated_configuration_has_one_tagged_nonpropagating_handler(
    capsys: pytest.CaptureFixture[str],
) -> None:
    _emitter(release="release-one")
    _emitter(release="release-two")

    assert emit_event("runtime.test", "info", {"result": "success"}) is True

    logger = logging.getLogger(APPLICATION_LOGGER_NAME)
    assert logger.propagate is False
    assert len(logger.handlers) == 1
    assert getattr(logger.handlers[0], "pickup_lane_handler_tag", None)
    records = _records(capsys)
    assert len(records) == 1
    assert records[0]["release"] == "release-two"
