from __future__ import annotations

from dataclasses import asdict
import importlib
import time
import uuid
from datetime import timedelta
from pathlib import Path
from threading import Event
from uuid import UUID

import pytest
from sqlalchemy import select

from backend.models import DurableJob, DurableJobEvent, DurableWorkerHeartbeat
from backend.services.durable_job_service import (
    EXHAUSTED,
    LEASED,
    PENDING,
    RETRY_WAITING,
    SUCCEEDED,
    DurableJobQueuePolicy,
    DurableJobRegistry,
    DurableJobRunner,
    HandlerResult,
    InvalidJobPayloadError,
    JobDefinition,
    UnsafeDiagnosticMetadataError,
    backlog_summary,
    enqueue_job,
    inspect_job_history,
    sanitize_diagnostic_metadata,
)

_REPO_ROOT = Path(__file__).resolve().parents[4]


def _db_session():
    return _session_factory()()


def _session_factory():
    from backend.database import SessionLocal

    return SessionLocal


def _registry_with_handler(
    handler,
    *,
    validator=None,
    attempts: int = 3,
    exceptions_are_transient: bool = True,
    transient_exception_error_code: str = "handler_transient_failure",
    permanent_exception_error_code: str = "handler_permanent_failure",
):
    return DurableJobRegistry(
        (
            JobDefinition(
                job_type="synthetic_job",
                payload_version=1,
                maximum_attempts=attempts,
                handler=handler,
                payload_validator=validator,
                transient_retry_delay=timedelta(seconds=1),
                exceptions_are_transient=exceptions_are_transient,
                transient_exception_error_code=transient_exception_error_code,
                permanent_exception_error_code=permanent_exception_error_code,
            ),
        )
    )


def _enqueue_with_registry(registry: DurableJobRegistry) -> UUID:
    with _db_session() as db:
        job = enqueue_job(
            db,
            registry=registry,
            job_type="synthetic_job",
            payload_version=1,
            payload={"kind": "synthetic"},
            protected_identity={"operation": "synthetic-operation"},
            idempotency_key=f"worker-{uuid.uuid4()}",
            correlation_id="correlation-worker",
        )
        job_id = job.id
        db.commit()
        return job_id


def _runner(
    registry: DurableJobRegistry,
    *,
    policy: DurableJobQueuePolicy | None = None,
    worker_identity: str | None = None,
) -> DurableJobRunner:
    return DurableJobRunner(
        session_factory=_session_factory(),
        registry=registry,
        worker_identity=worker_identity or f"runner-{uuid.uuid4()}",
        worker_version="test-version",
        policy=policy
        or DurableJobQueuePolicy(
            lease_duration=timedelta(seconds=30),
            heartbeat_interval=timedelta(seconds=10),
            fairness_age=timedelta(seconds=5),
        ),
    )


@pytest.mark.requirement("WS05-01A-R4", "WS05-01A-R6")
def test_runner_executes_success_retry_and_permanent_failure_with_synthetic_handlers() -> None:
    success_registry = _registry_with_handler(
        lambda db, job: HandlerResult.success({"safe_result": "ok"})
    )
    success_job_id = _enqueue_with_registry(success_registry)
    assert _runner(success_registry).process_once() == "succeeded"

    retry_registry = _registry_with_handler(
        lambda db, job: HandlerResult.transient_failure("temporary_failure")
    )
    retry_job_id = _enqueue_with_registry(retry_registry)
    assert _runner(retry_registry).process_once() == "retry_waiting"

    permanent_registry = _registry_with_handler(
        lambda db, job: HandlerResult.permanent_failure("permanent_failure")
    )
    permanent_job_id = _enqueue_with_registry(permanent_registry)
    assert _runner(permanent_registry).process_once() == "exhausted"

    with _db_session() as db:
        assert db.get(DurableJob, success_job_id).status == SUCCEEDED
        assert db.get(DurableJob, retry_job_id).status == RETRY_WAITING
        assert db.get(DurableJob, permanent_job_id).status == EXHAUSTED


@pytest.mark.requirement("WS05-01A-R4", "WS05-01A-R6")
def test_runner_classifies_handler_exceptions_with_safe_error_codes() -> None:
    def transient_handler(db, job):
        del db, job
        raise RuntimeError("raw transient detail must not leak")

    transient_registry = _registry_with_handler(
        transient_handler,
        transient_exception_error_code="synthetic_transient_exception",
    )
    transient_job_id = _enqueue_with_registry(transient_registry)

    assert _runner(transient_registry).process_once() == "retry_waiting"

    def permanent_handler(db, job):
        del db, job
        raise RuntimeError("raw permanent detail must not leak")

    permanent_registry = _registry_with_handler(
        permanent_handler,
        exceptions_are_transient=False,
        permanent_exception_error_code="synthetic_permanent_exception",
    )
    permanent_job_id = _enqueue_with_registry(permanent_registry)

    assert _runner(permanent_registry).process_once() == "exhausted"

    with _db_session() as db:
        transient_job = db.get(DurableJob, transient_job_id)
        assert transient_job.status == RETRY_WAITING
        assert transient_job.last_error_code == "synthetic_transient_exception"
        transient_events = db.execute(
            select(DurableJobEvent).where(DurableJobEvent.job_id == transient_job_id)
        ).scalars().all()
        retry_events = [
            event
            for event in transient_events
            if event.event_type == "retry_scheduled"
        ]
        assert retry_events[0].safe_error_code == "synthetic_transient_exception"
        assert "raw transient detail" not in str(retry_events[0].event_metadata)

        permanent_job = db.get(DurableJob, permanent_job_id)
        assert permanent_job.status == EXHAUSTED
        assert permanent_job.last_error_code == "synthetic_permanent_exception"
        permanent_events = db.execute(
            select(DurableJobEvent).where(DurableJobEvent.job_id == permanent_job_id)
        ).scalars().all()
        exhausted_events = [
            event for event in permanent_events if event.event_type == "exhausted"
        ]
        assert exhausted_events[0].safe_error_code == "synthetic_permanent_exception"
        assert "raw permanent detail" not in str(exhausted_events[0].event_metadata)


@pytest.mark.requirement("WS05-01A-R3", "WS05-01A-R6")
def test_runner_renews_active_handler_lease_with_separate_session() -> None:
    renewal_poll = Event()

    def handler(db, job):
        del db
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            with _db_session() as observer:
                heartbeat_events = observer.execute(
                    select(DurableJobEvent).where(
                        DurableJobEvent.job_id == job.id,
                        DurableJobEvent.event_type == "heartbeat",
                    )
                ).scalars().all()
                if heartbeat_events:
                    return HandlerResult.success({"safe_result": "renewed"})
            renewal_poll.wait(0.02)
        pytest.fail("lease renewal heartbeat did not commit while handler was active")

    registry = _registry_with_handler(handler)
    job_id = _enqueue_with_registry(registry)
    policy = DurableJobQueuePolicy(
        lease_duration=timedelta(seconds=1),
        heartbeat_interval=timedelta(seconds=0.05),
        fairness_age=timedelta(seconds=5),
    )

    assert _runner(registry, policy=policy).process_once() == "succeeded"

    with _db_session() as db:
        stored = db.get(DurableJob, job_id)
        assert stored.status == SUCCEEDED
        assert stored.attempt_count == 1
        event_types = [
            event.event_type
            for event in db.execute(
                select(DurableJobEvent).where(DurableJobEvent.job_id == job_id)
            ).scalars()
        ]
        assert "heartbeat" in event_types


@pytest.mark.requirement("WS05-01A-R3", "WS05-01A-R6")
@pytest.mark.parametrize(
    "handler_result",
    (
        HandlerResult.success({"safe_result": "lost"}),
        HandlerResult.transient_failure("lost_transient"),
        HandlerResult.permanent_failure("lost_permanent"),
    ),
)
def test_runner_does_not_record_transition_after_active_lease_loss(
    handler_result,
) -> None:
    lease_loss_observed = Event()

    def handler(db, job):
        del db
        with _db_session() as owner_change:
            stored = owner_change.get(DurableJob, job.id)
            stored.lease_token = uuid.uuid4()
            stored.lease_owner = "replacement-worker"
            owner_change.commit()
        lease_loss_observed.wait(0.25)
        return handler_result

    registry = _registry_with_handler(handler)
    job_id = _enqueue_with_registry(registry)
    policy = DurableJobQueuePolicy(
        lease_duration=timedelta(seconds=1),
        heartbeat_interval=timedelta(seconds=0.05),
        fairness_age=timedelta(seconds=5),
    )

    assert _runner(registry, policy=policy).process_once() == "lease_lost"

    with _db_session() as db:
        stored = db.get(DurableJob, job_id)
        assert stored.status == LEASED
        assert stored.lease_owner == "replacement-worker"
        assert stored.result_metadata == {}
        assert stored.completed_at is None
        assert stored.exhausted_at is None
        event_types = {
            event.event_type
            for event in db.execute(
                select(DurableJobEvent).where(DurableJobEvent.job_id == job_id)
            ).scalars()
        }
        assert "succeeded" not in event_types
        assert "retry_scheduled" not in event_types
        assert "exhausted" not in event_types
        assert "released" not in event_types


@pytest.mark.requirement("WS05-01A-R6")
def test_shutdown_requested_before_iteration_does_not_claim_new_work() -> None:
    registry = _registry_with_handler(lambda db, job: HandlerResult.success())
    job_id = _enqueue_with_registry(registry)
    runner = _runner(registry, worker_identity="shutdown-idle-worker")

    runner.request_shutdown()
    assert runner.process_once() == "shutdown"

    with _db_session() as db:
        stored = db.get(DurableJob, job_id)
        assert stored.status == PENDING
        assert stored.attempt_count == 0
        heartbeat = db.get(DurableWorkerHeartbeat, "shutdown-idle-worker")
        assert heartbeat.status == "stopped"
        assert heartbeat.current_job_id is None


@pytest.mark.requirement("WS05-01A-R6")
def test_shutdown_requested_while_leased_finishes_current_job_without_new_claims() -> None:
    runner_ref: dict[str, DurableJobRunner] = {}

    def handler(db, job):
        del db, job
        runner_ref["runner"].request_shutdown()
        return HandlerResult.success({"safe_result": "finished"})

    registry = _registry_with_handler(handler)
    first_job_id = _enqueue_with_registry(registry)
    second_job_id = _enqueue_with_registry(registry)
    runner = _runner(registry, worker_identity="shutdown-leased-worker")
    runner_ref["runner"] = runner

    assert runner.process_once() == "succeeded"
    assert runner.process_once() == "shutdown"

    with _db_session() as db:
        first = db.get(DurableJob, first_job_id)
        second = db.get(DurableJob, second_job_id)
        assert first.status == SUCCEEDED
        assert second.status == PENDING
        assert second.attempt_count == 0
        heartbeat = db.get(DurableWorkerHeartbeat, "shutdown-leased-worker")
        assert heartbeat.status == "stopped"
        assert heartbeat.current_job_id is None


@pytest.mark.requirement("WS05-01A-R4", "WS05-01A-R6")
def test_runner_fails_closed_for_malformed_persisted_payload_without_side_effect() -> None:
    calls: list[str] = []

    def validate(payload):
        raise InvalidJobPayloadError("malformed synthetic payload")

    def handler(db, job):
        calls.append("handler-called")
        return HandlerResult.success()

    enqueue_registry = _registry_with_handler(lambda db, job: HandlerResult.success())
    job_id = _enqueue_with_registry(enqueue_registry)
    worker_registry = _registry_with_handler(handler, validator=validate)

    assert _runner(worker_registry).process_once() == "exhausted"
    assert calls == []

    with _db_session() as db:
        stored = db.get(DurableJob, job_id)
        assert stored.status == EXHAUSTED
        assert stored.last_error_code == "malformed_payload"


@pytest.mark.requirement("WS05-01A-R6", "WS05-01A-R8")
def test_portable_worker_command_is_import_safe_and_not_deployment_topology() -> None:
    module = importlib.import_module("backend.scripts.durable_worker")
    source = (_REPO_ROOT / "backend/scripts/durable_worker.py").read_text()

    assert callable(module.main)
    assert "Celery" not in source
    assert "rq worker" not in source
    assert "Redis" not in source
    assert "--workers" not in source
    assert "autoscaling" not in source.lower()


@pytest.mark.requirement("WS05-01A-R6", "WS05-01A-R7")
def test_portable_worker_status_command_exposes_safe_operator_fields(capsys) -> None:
    registry = _registry_with_handler(lambda db, job: HandlerResult.success())
    job_id = _enqueue_with_registry(registry)
    module = importlib.import_module("backend.scripts.durable_worker")

    assert module.main(["--status", "--job-id", str(job_id)]) == 0

    output = capsys.readouterr().out
    assert "attempts_by_status=" in output
    assert "workers=" in output
    assert "recent_events=" in output
    assert "payload=" not in output
    assert "protected_identity" not in output
    assert "correlation_id" not in output
    assert "lease_token" not in output


@pytest.mark.requirement("WS05-01A-R6")
def test_worker_heartbeat_records_running_and_stopped_state() -> None:
    registry = _registry_with_handler(lambda db, job: HandlerResult.success())
    runner = _runner(registry)

    assert runner.process_once() == "idle"
    runner.mark_stopped()

    with _db_session() as db:
        heartbeat = db.execute(select(DurableWorkerHeartbeat)).scalars().one()
        assert heartbeat.worker_version == "test-version"
        assert heartbeat.status == "stopped"
        assert heartbeat.stopped_at is not None
        assert heartbeat.current_job_id is None


@pytest.mark.requirement("WS05-01A-R7", "WS05-01A-R8")
def test_backlog_summary_exposes_safe_counts_and_unsupported_versions() -> None:
    v1_registry = DurableJobRegistry(
        (
            JobDefinition(
                "synthetic_job",
                1,
                maximum_attempts=3,
                handler=lambda db, job: HandlerResult.success(),
            ),
        )
    )
    v2_registry = DurableJobRegistry(
        (
            JobDefinition(
                "synthetic_job",
                2,
                maximum_attempts=3,
                handler=lambda db, job: HandlerResult.success(),
            ),
        )
    )
    with _db_session() as db:
        enqueue_job(
            db,
            registry=v2_registry,
            job_type="synthetic_job",
            payload_version=2,
            payload={"kind": "synthetic"},
            protected_identity={"operation": "unsupported-operation"},
            idempotency_key=f"unsupported-{uuid.uuid4()}",
            correlation_id="correlation-unsupported",
        )
        db.commit()

    with _db_session() as db:
        summary = backlog_summary(
            db,
            registry=v1_registry,
            policy=DurableJobQueuePolicy(
                lease_duration=timedelta(seconds=30),
                heartbeat_interval=timedelta(seconds=10),
                fairness_age=timedelta(seconds=5),
            ),
        )

    assert summary.by_status == {"pending": 1}
    assert summary.unsupported_type_versions == (("synthetic_job", 2),)
    assert summary.expired_leases == 0
    assert summary.exhausted_jobs == 0
    assert summary.attempt_counts_by_status == {"pending": {0: 1}}


@pytest.mark.requirement("WS05-01A-R7", "WS05-01A-R8")
def test_operator_inspection_exposes_safe_worker_attempt_and_event_history() -> None:
    registry = _registry_with_handler(
        lambda db, job: HandlerResult.permanent_failure("permanent_failure")
    )
    job_id = _enqueue_with_registry(registry)
    runner = _runner(registry, worker_identity="operator-visible-worker")

    assert runner.process_once() == "exhausted"

    with _db_session() as db:
        summary = backlog_summary(db, registry=registry)
        assert summary.by_status == {EXHAUSTED: 1}
        assert summary.attempt_counts_by_status == {EXHAUSTED: {1: 1}}
        worker_summary = summary.worker_heartbeats[0]
        assert worker_summary.worker_identity == "operator-visible-worker"
        assert worker_summary.worker_version == "test-version"
        assert worker_summary.status == "running"
        assert worker_summary.heartbeat_age_seconds >= 0
        assert not worker_summary.has_current_job

    runner.mark_stopped()

    with _db_session() as db:
        refreshed = backlog_summary(db, registry=registry)
        worker_summary = refreshed.worker_heartbeats[0]
        assert worker_summary.worker_identity == "operator-visible-worker"
        assert worker_summary.worker_version == "test-version"
        assert worker_summary.status == "stopped"
        assert worker_summary.heartbeat_age_seconds >= 0
        assert not worker_summary.has_current_job

        job_summary = inspect_job_history(db, job_id=job_id)
        assert job_summary is not None
        assert job_summary.status == EXHAUSTED
        assert job_summary.attempt_count == 1
        assert job_summary.maximum_attempts == 3
        assert job_summary.last_safe_error_code == "permanent_failure"
        event_types = {event.event_type for event in job_summary.recent_events}
        assert {"enqueued", "claimed", "exhausted"} <= event_types
        exhausted_events = [
            event
            for event in job_summary.recent_events
            if event.event_type == "exhausted"
        ]
        assert exhausted_events[0].safe_error_code == "permanent_failure"

        public_shape = asdict(job_summary)
        assert "payload" not in public_shape
        assert "protected_identity" not in public_shape
        assert "correlation_id" not in public_shape
        assert "lease_token" not in str(public_shape)


@pytest.mark.requirement("WS05-01A-R7")
def test_diagnostic_metadata_rejects_sensitive_or_unbounded_values() -> None:
    assert sanitize_diagnostic_metadata({"safe_code": "ok", "attempt": 1}) == {
        "safe_code": "ok",
        "attempt": 1,
    }

    for unsafe in (
        {"email": "player@example.invalid"},
        {"safe_code": "postgresql://user:password@localhost/db"},
        {"safe_code": "x" * 121},
        {"raw_payload": "anything"},
    ):
        with pytest.raises(UnsafeDiagnosticMetadataError):
            sanitize_diagnostic_metadata(unsafe)
