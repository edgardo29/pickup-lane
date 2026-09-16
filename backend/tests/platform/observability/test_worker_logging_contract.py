from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
import uuid
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from backend.observability.structured_logging import (
    RuntimeEventEmitter,
    configure_process_logging,
)
from backend.scripts import durable_worker
from backend.services.durable_job_service import (
    BacklogSummary,
    DurableJobRegistry,
    DurableJobRunner,
    JobEventSummary,
    JobInspectionSummary,
    WorkerHeartbeatSummary,
)

pytestmark = [
    pytest.mark.no_db_cleanup,
    pytest.mark.requirement("WS09-01A"),
]
_REPO_ROOT = Path(__file__).resolve().parents[4]


def test_api_and_worker_bootstrap_precede_database_and_business_imports() -> None:
    api_source = (_REPO_ROOT / "backend/main.py").read_text()
    worker_source = (_REPO_ROOT / "backend/scripts/durable_worker.py").read_text()

    assert api_source.index("prepare_api_logging()") < api_source.index(
        "from backend.database import"
    )
    assert api_source.index(
        "configure_process_logging(\n        build_event_emitter"
    ) < api_source.index("from backend.routes import")
    assert worker_source.index("prepare_worker_logging()") < worker_source.index(
        "from backend.database import"
    )
    assert worker_source.index(
        "configure_process_logging(event_emitter"
    ) < worker_source.index("from backend.services.payment_job_service import")


def test_pre_bootstrap_import_failure_remains_a_host_runtime_boundary() -> None:
    private_text = "pre-bootstrap-host-canary"
    script = textwrap.dedent(
        f"""
        import builtins

        real_import = builtins.__import__

        def fail_before_bootstrap(name, *args, **kwargs):
            if name == "backend.observability.structured_logging":
                raise RuntimeError({private_text!r})
            return real_import(name, *args, **kwargs)

        builtins.__import__ = fail_before_bootstrap
        import backend.main
        """
    )

    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=_REPO_ROOT,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode != 0
    assert completed.stdout == ""
    assert private_text in completed.stderr
    assert '"event_name"' not in completed.stderr


def test_post_bootstrap_api_import_failure_is_fixed_by_uvicorn_handler() -> None:
    private_text = "Bearer post-bootstrap-import-canary user@example.invalid"
    script = textwrap.dedent(
        f"""
        import builtins
        import logging
        from backend.observability.structured_logging import (
            RuntimeEventEmitter,
            configure_process_logging,
            prepare_api_logging,
        )

        prepare_api_logging()
        configure_process_logging(RuntimeEventEmitter("api", "test", "test-release"))
        real_import = builtins.__import__

        def fail_business_import(name, *args, **kwargs):
            if name == "backend.database":
                raise RuntimeError({private_text!r})
            return real_import(name, *args, **kwargs)

        builtins.__import__ = fail_business_import
        try:
            __import__("backend.database")
        except RuntimeError:
            logging.getLogger("uvicorn.error").exception("unsafe import detail")
        """
    )

    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=_REPO_ROOT,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert completed.stderr == ""
    records = [json.loads(line) for line in completed.stdout.splitlines()]
    assert len(records) == 1
    assert records[0]["event_name"] == "runtime.framework"
    assert records[0]["operation"] == "uvicorn.runtime"
    assert private_text not in completed.stdout
    assert "unsafe import detail" not in completed.stdout


def test_post_bootstrap_worker_failure_is_one_fixed_event_and_exit_one(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    private_text = "Bearer private-worker-canary user@example.invalid"
    monkeypatch.setattr(
        "backend.database.check_database_connection",
        lambda: (_ for _ in ()).throw(RuntimeError(private_text)),
    )

    assert durable_worker.main(["--once"]) == 1

    output = capsys.readouterr()
    assert output.err == ""
    records = [json.loads(line) for line in output.out.splitlines()]
    assert len(records) == 1
    record = records[0]
    assert record["event_name"] == "durable_worker.failure"
    assert record["severity"] == "error"
    assert record["source_identity"] == "worker"
    assert record["operation"] == "durable_worker.run"
    assert record["result"] == "failed"
    assert record["stable_error_code"] == "WORKER.UNEXPECTED_FAILURE"
    assert private_text not in json.dumps(record)
    assert "Traceback" not in output.out


def test_post_bootstrap_worker_failure_is_safe_at_real_process_boundary() -> None:
    private_text = "Bearer private-subprocess-canary user@example.invalid"
    script = textwrap.dedent(
        f"""
        import backend.database
        from backend.scripts import durable_worker

        def fail_connection():
            raise RuntimeError({private_text!r})

        backend.database.check_database_connection = fail_connection
        raise SystemExit(durable_worker.main(["--once"]))
        """
    )

    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=_REPO_ROOT,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 1
    assert completed.stderr == ""
    records = [json.loads(line) for line in completed.stdout.splitlines()]
    assert len(records) == 1
    assert records[0]["event_name"] == "durable_worker.failure"
    assert records[0]["stable_error_code"] == "WORKER.UNEXPECTED_FAILURE"
    assert private_text not in completed.stdout
    assert "Traceback" not in completed.stdout


def test_worker_bootstrap_failure_raises_only_fixed_unchained_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        durable_worker,
        "prepare_worker_logging",
        lambda: (_ for _ in ()).throw(RuntimeError("private-bootstrap-canary")),
    )

    with pytest.raises(
        RuntimeError, match="^Worker logging bootstrap failed\\.$"
    ) as exc_info:
        durable_worker.main(["--once"])

    assert exc_info.value.__cause__ is None
    assert "private-bootstrap-canary" not in str(exc_info.value)


@pytest.mark.parametrize(
    "outcome",
    ["idle", "shutdown", "succeeded", "retry_waiting", "exhausted", "lease_lost"],
)
def test_once_outcomes_use_success_exit_without_plain_iteration_output(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    outcome: str,
) -> None:
    from backend.services import durable_job_service, payment_job_service

    calls: list[str] = []

    class FakeRunner:
        def __init__(self, **kwargs) -> None:
            del kwargs

        def process_once(self) -> str:
            calls.append("process_once")
            return outcome

        def mark_stopped(self) -> None:
            calls.append("mark_stopped")

    monkeypatch.setattr("backend.database.check_database_connection", lambda: None)
    monkeypatch.setattr(
        payment_job_service,
        "build_production_job_registry",
        DurableJobRegistry,
    )
    monkeypatch.setattr(durable_job_service, "DurableJobRunner", FakeRunner)

    assert durable_worker.main(["--once"]) == 0
    assert calls == ["process_once", "mark_stopped"]
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err == ""


def test_status_missing_job_uses_exact_operator_shape_at_command_boundary(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from backend.services import durable_job_service, payment_job_service

    missing_job_id = uuid.uuid4()
    summary = BacklogSummary(
        by_status={},
        by_type_version={},
        unsupported_type_versions=(),
        expired_leases=0,
        exhausted_jobs=0,
        retry_waiting_jobs=0,
        oldest_pending_age_seconds=None,
        fairness_protected_jobs=0,
        attempt_counts_by_status={},
        worker_heartbeats=(),
    )

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback) -> None:
            del exc_type, exc, traceback

    monkeypatch.setattr("backend.database.check_database_connection", lambda: None)
    monkeypatch.setattr("backend.database.SessionLocal", FakeSession)
    monkeypatch.setattr(
        payment_job_service,
        "build_production_job_registry",
        DurableJobRegistry,
    )
    monkeypatch.setattr(
        durable_job_service,
        "backlog_summary",
        lambda *args, **kwargs: summary,
    )
    monkeypatch.setattr(
        durable_job_service,
        "inspect_job_history",
        lambda *args, **kwargs: None,
    )

    assert durable_worker.main(["--status", "--job-id", str(missing_job_id)]) == 0

    records = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert records[1] == {
        "record_type": "durable_job_details",
        "schema_version": 1,
        "missing": True,
    }


def test_status_record_uses_exact_sorted_json_safe_shape() -> None:
    summary = BacklogSummary(
        by_status={"retry_waiting": 2, "pending": 1},
        by_type_version={("z_job", 2): 1, ("a_job", 1): 2},
        unsupported_type_versions=(("z_job", 3), ("a_job", 2)),
        expired_leases=4,
        exhausted_jobs=5,
        retry_waiting_jobs=2,
        oldest_pending_age_seconds=10,
        fairness_protected_jobs=1,
        attempt_counts_by_status={"retry_waiting": {2: 1, 1: 1}, "pending": {0: 1}},
        worker_heartbeats=(
            WorkerHeartbeatSummary("z-worker", "version", "running", 2, True),
            WorkerHeartbeatSummary("a-worker", "version", "stopped", 1, False),
        ),
    )

    record = durable_worker._status_record(summary)

    assert list(record) == [
        "record_type",
        "schema_version",
        "by_status",
        "by_type_version",
        "attempt_counts_by_status",
        "unsupported_type_versions",
        "expired_leases",
        "exhausted_jobs",
        "retry_waiting_jobs",
        "oldest_pending_age_seconds",
        "fairness_protected_jobs",
        "worker_heartbeats",
    ]
    assert record["by_status"] == [
        {"status": "pending", "count": 1},
        {"status": "retry_waiting", "count": 2},
    ]
    assert record["by_type_version"] == [
        {"job_type": "a_job", "payload_version": 1, "count": 2},
        {"job_type": "z_job", "payload_version": 2, "count": 1},
    ]
    assert record["unsupported_type_versions"] == [
        {"job_type": "a_job", "payload_version": 2},
        {"job_type": "z_job", "payload_version": 3},
    ]
    assert [item["worker_identity"] for item in record["worker_heartbeats"]] == [
        "a-worker",
        "z-worker",
    ]
    json.dumps(record)


@pytest.mark.parametrize(
    ("value", "maximum", "expected"),
    [
        ("x" * 120, 120, "x" * 120),
        ("x" * 121, 120, "redacted"),
        ("x" * 80, 80, "x" * 80),
        ("x" * 81, 80, "redacted"),
        ("worker\nprivate", 120, "redacted"),
        ("user@example.invalid", 120, "redacted"),
        (None, 120, None),
    ],
)
def test_operator_string_projection_uses_field_specific_bounds(
    value: str | None,
    maximum: int,
    expected: str | None,
) -> None:
    assert durable_worker._safe_operator_string(value, maximum=maximum) == expected


def test_job_record_has_exact_shape_and_fails_closed_for_unsafe_metadata() -> None:
    event = JobEventSummary(
        event_type="retry_scheduled",
        previous_status="leased",
        new_status="retry_waiting",
        attempt_count=1,
        lease_owner="x" * 121,
        safe_error_code="provider_event_retry",
        event_metadata={"safe_result": "user@example.invalid"},
        occurred_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    summary = JobInspectionSummary(
        job_type="synthetic_job",
        payload_version=1,
        status="retry_waiting",
        attempt_count=1,
        maximum_attempts=3,
        last_safe_error_code="provider_event_retry",
        recent_events=(event,),
    )

    record = durable_worker._job_record(summary)

    assert record == {
        "record_type": "durable_job_details",
        "schema_version": 1,
        "missing": False,
        "job_type": "synthetic_job",
        "payload_version": 1,
        "status": "retry_waiting",
        "attempt_count": 1,
        "maximum_attempts": 3,
        "last_safe_error_code": "provider_event_retry",
        "recent_events": [
            {
                "occurred_at": "2026-01-01T00:00:00Z",
                "event_type": "retry_scheduled",
                "previous_status": "leased",
                "new_status": "retry_waiting",
                "attempt_count": 1,
                "lease_owner": "redacted",
                "safe_error_code": "provider_event_retry",
                "event_metadata": {},
            }
        ],
    }
    assert "user@example.invalid" not in json.dumps(record)


@pytest.mark.parametrize(
    "job_type",
    [
        "stripe_webhook_event",
        "stripe_payment_intent_reconcile",
        "stripe_payment_method_operation_reconcile",
    ],
)
def test_current_stripe_job_events_have_provider_without_payment_identifiers(
    capsys: pytest.CaptureFixture[str],
    job_type: str,
) -> None:
    emitter = RuntimeEventEmitter("worker", "test", "test-release")
    configure_process_logging(emitter, configure_uvicorn=False)
    runner = DurableJobRunner(
        session_factory=None,  # type: ignore[arg-type]
        registry=DurableJobRegistry(),
        worker_identity="test-worker",
        event_emitter=emitter,
    )
    job_id = uuid.uuid4()

    runner._emit_job_event(
        SimpleNamespace(
            job_id=job_id,
            job_type=job_type,
            payload_version=1,
            attempt_count=1,
            maximum_attempts=3,
            correlation_id=None,
        ),
        severity="info",
        result="succeeded",
    )

    record = json.loads(capsys.readouterr().out)
    assert record["provider_kind"] == "stripe"
    assert record["resource_id"] == str(job_id)
    for forbidden in (
        "payment_id",
        "payment_event_id",
        "customer_id",
        "charge_id",
        "payment_intent_id",
        "payload",
        "protected_identity",
    ):
        assert forbidden not in record
