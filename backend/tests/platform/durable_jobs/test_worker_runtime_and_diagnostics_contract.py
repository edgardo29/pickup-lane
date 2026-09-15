from __future__ import annotations

import importlib
import json
import time
import uuid
from contextlib import nullcontext
from dataclasses import asdict
from datetime import timedelta
from pathlib import Path
from threading import Event
from unittest.mock import Mock
from uuid import UUID

import pytest
from sqlalchemy import select

from backend.models import DurableJob, DurableJobEvent, DurableWorkerHeartbeat
from backend.observability.correlation import correlation_context, get_correlation_id
from backend.observability.structured_logging import (
    RuntimeEventEmitter,
    configure_process_logging,
)
from backend.services import durable_job_service
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
    event_emitter: RuntimeEventEmitter | None = None,
) -> DurableJobRunner:
    return DurableJobRunner(
        session_factory=_session_factory(),
        registry=registry,
        worker_identity=worker_identity or f"runner-{uuid.uuid4()}",
        worker_version="test-version",
        event_emitter=event_emitter,
        policy=policy
        or DurableJobQueuePolicy(
            lease_duration=timedelta(seconds=30),
            heartbeat_interval=timedelta(seconds=10),
            fairness_age=timedelta(seconds=5),
        ),
    )


@pytest.mark.requirement("WS05-01A-R4", "WS05-01A-R6")
def test_runner_executes_success_retry_and_permanent_failure_with_synthetic_handlers() -> (
    None
):
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
        transient_events = (
            db.execute(
                select(DurableJobEvent).where(
                    DurableJobEvent.job_id == transient_job_id
                )
            )
            .scalars()
            .all()
        )
        retry_events = [
            event for event in transient_events if event.event_type == "retry_scheduled"
        ]
        assert retry_events[0].safe_error_code == "synthetic_transient_exception"
        assert "raw transient detail" not in str(retry_events[0].event_metadata)

        permanent_job = db.get(DurableJob, permanent_job_id)
        assert permanent_job.status == EXHAUSTED
        assert permanent_job.last_error_code == "synthetic_permanent_exception"
        permanent_events = (
            db.execute(
                select(DurableJobEvent).where(
                    DurableJobEvent.job_id == permanent_job_id
                )
            )
            .scalars()
            .all()
        )
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
                heartbeat_events = (
                    observer.execute(
                        select(DurableJobEvent).where(
                            DurableJobEvent.job_id == job.id,
                            DurableJobEvent.event_type == "heartbeat",
                        )
                    )
                    .scalars()
                    .all()
                )
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
    capsys,
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

    emitter = RuntimeEventEmitter("worker", "test", "test-release")
    assert (
        _runner(registry, policy=policy, event_emitter=emitter).process_once()
        == "lease_lost"
    )

    record = json.loads(capsys.readouterr().out.splitlines()[-1])
    assert record["severity"] == "warning"
    assert record["result"] == "lease_lost"
    assert record["stable_error_code"] == "JOB.LEASE_LOST"
    assert record["resource_id"] == str(job_id)

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
def test_shutdown_requested_before_iteration_does_not_claim_new_work(capsys) -> None:
    registry = _registry_with_handler(lambda db, job: HandlerResult.success())
    job_id = _enqueue_with_registry(registry)
    emitter = RuntimeEventEmitter("worker", "test", "test-release")
    runner = _runner(
        registry,
        worker_identity="shutdown-idle-worker",
        event_emitter=emitter,
    )

    runner.request_shutdown()
    assert runner.process_once() == "shutdown"
    assert capsys.readouterr().out == ""

    with _db_session() as db:
        stored = db.get(DurableJob, job_id)
        assert stored.status == PENDING
        assert stored.attempt_count == 0
        heartbeat = db.get(DurableWorkerHeartbeat, "shutdown-idle-worker")
        assert heartbeat.status == "stopped"
        assert heartbeat.current_job_id is None


@pytest.mark.requirement("WS05-01A-R6")
def test_shutdown_requested_while_leased_finishes_current_job_without_new_claims() -> (
    None
):
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


@pytest.mark.requirement("WS05-01A-R4", "WS05-01A-R6", "WS09-01A")
def test_runner_fails_closed_for_malformed_persisted_payload_without_side_effect(
    capsys,
) -> None:
    calls: list[str] = []

    def validate(payload):
        raise InvalidJobPayloadError("malformed synthetic payload")

    def handler(db, job):
        calls.append("handler-called")
        return HandlerResult.success()

    enqueue_registry = _registry_with_handler(lambda db, job: HandlerResult.success())
    job_id = _enqueue_with_registry(enqueue_registry)
    worker_registry = _registry_with_handler(handler, validator=validate)

    emitter = RuntimeEventEmitter("worker", "test", "test-release")
    assert _runner(worker_registry, event_emitter=emitter).process_once() == "exhausted"
    assert calls == []

    record = json.loads(capsys.readouterr().out.splitlines()[-1])
    assert record["severity"] == "error"
    assert record["result"] == "exhausted"
    assert record["stable_error_code"] == "JOB.MALFORMED_PAYLOAD"
    assert record["resource_id"] == str(job_id)

    with _db_session() as db:
        stored = db.get(DurableJob, job_id)
        assert stored.status == EXHAUSTED
        assert stored.last_error_code == "malformed_payload"


@pytest.mark.requirement("WS09-01A")
def test_malformed_payload_reports_lease_lost_when_exhaust_transition_loses_lease(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def validate(payload):
        del payload
        raise InvalidJobPayloadError("malformed synthetic payload")

    enqueue_registry = _registry_with_handler(lambda db, job: HandlerResult.success())
    job_id = _enqueue_with_registry(enqueue_registry)
    worker_registry = _registry_with_handler(
        lambda db, job: HandlerResult.success(),
        validator=validate,
    )
    monkeypatch.setattr(
        durable_job_service, "exhaust_job", lambda *args, **kwargs: False
    )
    emitter = RuntimeEventEmitter("worker", "test", "test-release")

    assert (
        _runner(worker_registry, event_emitter=emitter).process_once() == "lease_lost"
    )

    record = json.loads(capsys.readouterr().out.splitlines()[-1])
    assert record["event_name"] == "durable_job.processed"
    assert record["severity"] == "warning"
    assert record["result"] == "lease_lost"
    assert record["stable_error_code"] == "JOB.LEASE_LOST"
    assert record["resource_id"] == str(job_id)
    with _db_session() as db:
        assert db.get(DurableJob, job_id).status == LEASED


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

    records = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert len(records) == 2
    status_record, job_record = records
    assert status_record["record_type"] == "durable_job_status"
    assert status_record["schema_version"] == 1
    assert status_record["attempt_counts_by_status"] == [
        {
            "status": "pending",
            "attempt_counts": [{"attempt_count": 0, "count": 1}],
        }
    ]
    assert job_record["record_type"] == "durable_job_details"
    assert job_record["missing"] is False
    assert job_record["recent_events"]
    output = json.dumps(records)
    assert "payload=" not in output
    assert "protected_identity" not in output
    assert "correlation_id" not in output
    assert "lease_token" not in output


@pytest.mark.requirement("WS09-01A")
def test_enqueue_defaults_to_request_correlation_then_generated_uuid() -> None:
    registry = _registry_with_handler(lambda db, job: HandlerResult.success())
    request_correlation = str(uuid.uuid4())

    with _db_session() as db, correlation_context(request_correlation):
        request_job = enqueue_job(
            db,
            registry=registry,
            job_type="synthetic_job",
            payload_version=1,
            payload={"kind": "synthetic"},
            idempotency_key=f"request-correlation-{uuid.uuid4()}",
        )
        request_job_id = request_job.id
        db.commit()

    with _db_session() as db:
        background_job = enqueue_job(
            db,
            registry=registry,
            job_type="synthetic_job",
            payload_version=1,
            payload={"kind": "synthetic"},
            idempotency_key=f"background-correlation-{uuid.uuid4()}",
        )
        background_job_id = background_job.id
        db.commit()

    with _db_session() as db:
        assert db.get(DurableJob, request_job_id).correlation_id == request_correlation
        generated = db.get(DurableJob, background_job_id).correlation_id
        assert str(uuid.UUID(generated, version=4)) == generated


@pytest.mark.requirement("WS09-01A")
@pytest.mark.parametrize(
    (
        "job_kind",
        "downstream_outcome",
        "expected_process_outcome",
        "expected_status",
        "expected_result",
        "expected_code",
    ),
    [
        ("webhook", "processed", "succeeded", SUCCEEDED, "succeeded", None),
        (
            "webhook",
            "retry",
            "retry_waiting",
            RETRY_WAITING,
            "retry_waiting",
            "JOB.PROVIDER_EVENT_RETRY",
        ),
        (
            "webhook",
            "failed",
            "exhausted",
            EXHAUSTED,
            "exhausted",
            "JOB.INVALID_PROVIDER_EVENT",
        ),
        (
            "payment",
            "retry",
            "retry_waiting",
            RETRY_WAITING,
            "retry_waiting",
            "JOB.PAYMENT_RECONCILE_RETRY",
        ),
        (
            "payment",
            "permanent_failure",
            "exhausted",
            EXHAUSTED,
            "exhausted",
            "JOB.PAYMENT_RECONCILE_INVALID",
        ),
        (
            "payment_method",
            "retry",
            "retry_waiting",
            RETRY_WAITING,
            "retry_waiting",
            "JOB.PAYMENT_METHOD_RECONCILE_RETRY",
        ),
    ],
)
def test_production_payment_jobs_preserve_request_correlation_state_and_safe_events(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    job_kind: str,
    downstream_outcome: str,
    expected_process_outcome: str,
    expected_status: str,
    expected_result: str,
    expected_code: str | None,
) -> None:
    from backend.services import (
        payment_job_service,
        payment_method_service,
        payment_transition_service,
        stripe_webhook_service,
    )

    protected_reference = uuid.uuid4()
    if job_kind == "webhook":
        monkeypatch.setattr(
            stripe_webhook_service,
            "process_stored_stripe_event",
            lambda db, event_id: downstream_outcome,
        )
        enqueue = lambda db: payment_job_service.enqueue_webhook_event_job(
            db, protected_reference
        )
    elif job_kind == "payment":
        monkeypatch.setattr(
            payment_transition_service,
            "reconcile_payment_intent",
            lambda db, payment_id: downstream_outcome,
        )
        enqueue = lambda db: payment_job_service.enqueue_payment_reconcile_job(
            db,
            protected_reference,
            reason="ws09_observability_proof",
        )
    else:
        monkeypatch.setattr(
            payment_method_service,
            "reconcile_payment_method_operation",
            lambda db, operation_id: downstream_outcome,
        )
        enqueue = lambda db: payment_job_service.enqueue_payment_method_reconcile_job(
            db, protected_reference
        )

    correlation_id = str(uuid.uuid4())
    registry = payment_job_service.build_production_job_registry()
    with _db_session() as db, correlation_context(correlation_id):
        job = enqueue(db)
        job_id = job.id
        db.commit()

    emitter = RuntimeEventEmitter("worker", "test", "test-release")
    assert (
        _runner(registry, event_emitter=emitter).process_once()
        == expected_process_outcome
    )

    with _db_session() as db:
        stored = db.get(DurableJob, job_id)
        assert stored.status == expected_status
        assert stored.correlation_id == correlation_id

    records = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert len(records) == 1
    record = records[0]
    assert record["event_name"] == "durable_job.processed"
    assert record["provider_kind"] == "stripe"
    assert record["resource_kind"] == "durable_job"
    assert record["resource_id"] == str(job_id)
    assert record["correlation_id"] == correlation_id
    assert record["result"] == expected_result
    if expected_code is None:
        assert "stable_error_code" not in record
    else:
        assert record["stable_error_code"] == expected_code
    serialized = json.dumps(record)
    assert str(protected_reference) not in serialized
    assert "payment_id" not in serialized
    assert "payment_event_id" not in serialized
    assert "payment_method_operation_id" not in serialized


@pytest.mark.requirement("WS09-01A")
@pytest.mark.parametrize(
    ("handler_result", "attempts", "expected_outcome", "severity", "result", "code"),
    [
        (HandlerResult.success(), 3, "succeeded", "info", "succeeded", None),
        (
            HandlerResult.transient_failure("provider_event_retry"),
            3,
            "retry_waiting",
            "warning",
            "retry_waiting",
            "JOB.PROVIDER_EVENT_RETRY",
        ),
        (
            HandlerResult.transient_failure("handler_transient_failure"),
            3,
            "retry_waiting",
            "warning",
            "retry_waiting",
            "JOB.HANDLER_TRANSIENT_FAILURE",
        ),
        (
            HandlerResult.transient_failure("transient_failure"),
            3,
            "retry_waiting",
            "warning",
            "retry_waiting",
            "JOB.TRANSIENT_FAILURE",
        ),
        (
            HandlerResult.transient_failure("payment_reconcile_retry"),
            3,
            "retry_waiting",
            "warning",
            "retry_waiting",
            "JOB.PAYMENT_RECONCILE_RETRY",
        ),
        (
            HandlerResult.transient_failure("payment_method_reconcile_retry"),
            3,
            "retry_waiting",
            "warning",
            "retry_waiting",
            "JOB.PAYMENT_METHOD_RECONCILE_RETRY",
        ),
        (
            HandlerResult.transient_failure("future_private_code"),
            1,
            "retry_waiting",
            "error",
            "exhausted",
            "JOB.UNMAPPED_ERROR",
        ),
        (
            HandlerResult.permanent_failure("permanent_failure"),
            3,
            "exhausted",
            "error",
            "exhausted",
            "JOB.PERMANENT_FAILURE",
        ),
        (
            HandlerResult.permanent_failure("handler_permanent_failure"),
            3,
            "exhausted",
            "error",
            "exhausted",
            "JOB.HANDLER_PERMANENT_FAILURE",
        ),
        (
            HandlerResult.permanent_failure("invalid_provider_event"),
            3,
            "exhausted",
            "error",
            "exhausted",
            "JOB.INVALID_PROVIDER_EVENT",
        ),
        (
            HandlerResult.permanent_failure("payment_reconcile_invalid"),
            3,
            "exhausted",
            "error",
            "exhausted",
            "JOB.PAYMENT_RECONCILE_INVALID",
        ),
    ],
)
def test_runner_events_follow_committed_state_and_fixed_code_translation(
    capsys,
    handler_result: HandlerResult,
    attempts: int,
    expected_outcome: str,
    severity: str,
    result: str,
    code: str | None,
) -> None:
    registry = _registry_with_handler(lambda db, job: handler_result, attempts=attempts)
    correlation_id = str(uuid.uuid4())
    with _db_session() as db:
        job = enqueue_job(
            db,
            registry=registry,
            job_type="synthetic_job",
            payload_version=1,
            payload={"kind": "synthetic"},
            idempotency_key=f"event-mapping-{uuid.uuid4()}",
            correlation_id=correlation_id,
        )
        job_id = job.id
        db.commit()
    emitter = RuntimeEventEmitter("worker", "test", "test-release")

    assert _runner(registry, event_emitter=emitter).process_once() == expected_outcome

    record = json.loads(capsys.readouterr().out.splitlines()[-1])
    assert record["event_name"] == "durable_job.processed"
    assert record["severity"] == severity
    assert record["result"] == result
    assert record["resource_id"] == str(job_id)
    assert record["resource_kind"] == "durable_job"
    assert record["correlation_id"] == correlation_id
    assert record["attempt_count"] == 1
    assert record["maximum_attempts"] == attempts
    assert record["labels"] == {"job_type": "synthetic_job"}
    if code is None:
        assert "stable_error_code" not in record
    else:
        assert record["stable_error_code"] == code
    assert "future_private_code" not in json.dumps(record)


@pytest.mark.requirement("WS09-01A")
def test_canonical_job_correlation_scopes_handler_event_and_restores_outer_context(
    capsys: pytest.CaptureFixture[str],
) -> None:
    stored_correlation = str(uuid.uuid4())
    outer_correlation = str(uuid.uuid4())
    handler_correlations: list[str | None] = []

    def handler(db, job):
        del db, job
        handler_correlations.append(get_correlation_id())
        return HandlerResult.success()

    registry = _registry_with_handler(handler)
    with _db_session() as db:
        job = enqueue_job(
            db,
            registry=registry,
            job_type="synthetic_job",
            payload_version=1,
            payload={"kind": "synthetic"},
            idempotency_key=f"canonical-correlation-{uuid.uuid4()}",
            correlation_id=stored_correlation,
        )
        job_id = job.id
        db.commit()

    emitter = RuntimeEventEmitter("worker", "test", "test-release")
    configure_process_logging(emitter, configure_uvicorn=False)

    with correlation_context(outer_correlation):
        assert _runner(registry, event_emitter=emitter).process_once() == "succeeded"
        assert get_correlation_id() == outer_correlation

    assert get_correlation_id() is None
    assert handler_correlations == [stored_correlation]
    record = json.loads(capsys.readouterr().out.splitlines()[-1])
    assert record["event_name"] == "durable_job.processed"
    assert record["resource_id"] == str(job_id)
    assert record["correlation_id"] == stored_correlation


@pytest.mark.requirement("WS09-01A")
@pytest.mark.no_db_cleanup
@pytest.mark.parametrize(
    ("durable_code", "structured_code"),
    sorted(
        {
            "malformed_payload": "JOB.MALFORMED_PAYLOAD",
            "handler_transient_failure": "JOB.HANDLER_TRANSIENT_FAILURE",
            "handler_permanent_failure": "JOB.HANDLER_PERMANENT_FAILURE",
            "transient_failure": "JOB.TRANSIENT_FAILURE",
            "permanent_failure": "JOB.PERMANENT_FAILURE",
            "invalid_provider_event": "JOB.INVALID_PROVIDER_EVENT",
            "provider_event_retry": "JOB.PROVIDER_EVENT_RETRY",
            "payment_reconcile_invalid": "JOB.PAYMENT_RECONCILE_INVALID",
            "payment_reconcile_retry": "JOB.PAYMENT_RECONCILE_RETRY",
            "payment_method_reconcile_retry": ("JOB.PAYMENT_METHOD_RECONCILE_RETRY"),
            "lease_expired_max_attempts": "JOB.LEASE_EXPIRED_MAX_ATTEMPTS",
        }.items()
    ),
)
def test_every_current_durable_error_code_has_exact_fixed_translation(
    durable_code: str,
    structured_code: str,
) -> None:
    assert (
        durable_job_service._structured_job_error_code(
            durable_code,
            fallback="JOB.FALLBACK",
        )
        == structured_code
    )


@pytest.mark.requirement("WS09-01A")
def test_job_event_is_attempted_after_commit_and_logging_failure_preserves_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = _registry_with_handler(lambda db, job: HandlerResult.success())
    job_id = _enqueue_with_registry(registry)
    observed_states: list[str] = []

    def failing_emit(emitter, emitted_job_id, severity, fields):
        del emitter, severity, fields
        with _db_session() as observer_db:
            observed_states.append(observer_db.get(DurableJob, emitted_job_id).status)
        return False

    monkeypatch.setattr(
        durable_job_service,
        "emit_durable_job_event",
        failing_emit,
    )

    assert _runner(registry).process_once() == "succeeded"
    assert observed_states == [SUCCEEDED]
    with _db_session() as db:
        assert db.get(DurableJob, job_id).status == SUCCEEDED


@pytest.mark.no_db_cleanup
@pytest.mark.requirement("WS09-01A")
def test_missing_claimed_job_has_exact_compatibility_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[object, ...]] = []
    job_id = uuid.uuid4()
    summary = durable_job_service._JobLogSummary(
        job_id=job_id,
        job_type="synthetic_job",
        attempt_count=1,
        maximum_attempts=3,
        correlation_id=None,
    )
    db = Mock()
    db.get.return_value = None
    monkeypatch.setattr(
        durable_job_service,
        "emit_durable_job_event",
        lambda *args: calls.append(args) or True,
    )
    runner = DurableJobRunner(
        session_factory=lambda: nullcontext(db),  # type: ignore[arg-type]
        registry=DurableJobRegistry(),
        worker_identity="test-worker",
    )

    assert runner._run_handler(job_id, uuid.uuid4(), summary) == "missing"
    assert calls == [
        (
            None,
            job_id,
            "error",
            {
                "attempt_count": 1,
                "maximum_attempts": 3,
                "result": "missing",
                "labels": {"job_type": "synthetic_job"},
                "stable_error_code": "JOB.MISSING",
            },
        )
    ]


@pytest.mark.no_db_cleanup
@pytest.mark.requirement("WS09-01A")
def test_unsupported_claimed_definition_has_exact_compatibility_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[object, ...]] = []
    job_id = uuid.uuid4()
    correlation_id = str(uuid.uuid4())
    summary = durable_job_service._JobLogSummary(
        job_id=job_id,
        job_type="synthetic_job",
        attempt_count=1,
        maximum_attempts=3,
        correlation_id=correlation_id,
    )
    db = Mock()
    db.get.return_value = Mock(
        id=job_id,
        job_type="synthetic_job",
        payload_version=99,
        attempt_count=1,
        maximum_attempts=3,
        correlation_id=correlation_id,
    )
    monkeypatch.setattr(
        durable_job_service,
        "emit_durable_job_event",
        lambda *args: calls.append(args) or True,
    )
    runner = DurableJobRunner(
        session_factory=lambda: nullcontext(db),  # type: ignore[arg-type]
        registry=DurableJobRegistry(),
        worker_identity="test-worker",
    )

    assert runner._run_handler(job_id, uuid.uuid4(), summary) == "unsupported"
    db.rollback.assert_called_once_with()
    assert calls[0][1:] == (
        job_id,
        "error",
        {
            "attempt_count": 1,
            "maximum_attempts": 3,
            "result": "unsupported",
            "labels": {"job_type": "synthetic_job"},
            "stable_error_code": "JOB.UNSUPPORTED_DEFINITION",
        },
    )


@pytest.mark.requirement("WS09-01A")
def test_legacy_job_correlation_is_cleared_for_handler_and_event(capsys) -> None:
    seen_correlation: list[str | None] = []

    def handler(db, job):
        del db, job
        from backend.observability.correlation import get_correlation_id

        seen_correlation.append(get_correlation_id())
        return HandlerResult.success()

    registry = _registry_with_handler(handler)
    job_id = _enqueue_with_registry(registry)
    emitter = RuntimeEventEmitter("worker", "test", "test-release")
    inherited = str(uuid.uuid4())

    with correlation_context(inherited):
        assert _runner(registry, event_emitter=emitter).process_once() == "succeeded"

    record = json.loads(capsys.readouterr().out.splitlines()[-1])
    assert seen_correlation == [None]
    assert "correlation_id" not in record
    assert record["resource_id"] == str(job_id)


@pytest.mark.requirement("WS09-01A")
def test_expired_final_attempt_emits_after_recovery_commit(capsys) -> None:
    registry = _registry_with_handler(
        lambda db, job: HandlerResult.success(), attempts=1
    )
    job_id = _enqueue_with_registry(registry)
    policy = DurableJobQueuePolicy(
        lease_duration=timedelta(seconds=30),
        heartbeat_interval=timedelta(seconds=10),
        fairness_age=timedelta(seconds=5),
    )
    from backend.services.durable_job_service import claim_job

    with _db_session() as db:
        claim = claim_job(
            db,
            registry=registry,
            worker_identity="expired-original",
            policy=policy,
        )
        assert claim is not None
        stored = db.get(DurableJob, job_id)
        stored.lease_expires_at = stored.heartbeat_at - timedelta(seconds=1)
        db.commit()

    emitter = RuntimeEventEmitter("worker", "test", "test-release")
    assert (
        _runner(registry, policy=policy, event_emitter=emitter).process_once() == "idle"
    )

    record = json.loads(capsys.readouterr().out.splitlines()[-1])
    assert record["result"] == "exhausted"
    assert record["stable_error_code"] == "JOB.LEASE_EXPIRED_MAX_ATTEMPTS"
    assert record["resource_id"] == str(job_id)
    with _db_session() as db:
        assert db.get(DurableJob, job_id).status == EXHAUSTED


@pytest.mark.requirement("WS09-01A")
def test_expired_final_attempt_and_new_claim_each_emit_in_same_iteration(
    capsys,
) -> None:
    registry = _registry_with_handler(
        lambda db, job: HandlerResult.success(), attempts=1
    )
    expired_job_id = _enqueue_with_registry(registry)
    pending_job_id = _enqueue_with_registry(registry)
    policy = DurableJobQueuePolicy(
        lease_duration=timedelta(seconds=30),
        heartbeat_interval=timedelta(seconds=10),
        fairness_age=timedelta(seconds=5),
    )

    with _db_session() as db:
        claim = durable_job_service.claim_job(
            db,
            registry=registry,
            worker_identity="expired-original",
            policy=policy,
        )
        assert claim is not None
        assert claim.job.id == expired_job_id
        stored = db.get(DurableJob, expired_job_id)
        stored.lease_expires_at = stored.heartbeat_at - timedelta(seconds=1)
        db.commit()

    emitter = RuntimeEventEmitter("worker", "test", "test-release")
    assert (
        _runner(registry, policy=policy, event_emitter=emitter).process_once()
        == "succeeded"
    )

    records = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert [(record["resource_id"], record["result"]) for record in records] == [
        (str(expired_job_id), "exhausted"),
        (str(pending_job_id), "succeeded"),
    ]
    assert records[0]["stable_error_code"] == "JOB.LEASE_EXPIRED_MAX_ATTEMPTS"
    with _db_session() as db:
        assert db.get(DurableJob, expired_job_id).status == EXHAUSTED
        assert db.get(DurableJob, pending_job_id).status == SUCCEEDED


@pytest.mark.requirement("WS05-01A-R6")
def test_worker_heartbeat_records_running_and_stopped_state(capsys) -> None:
    registry = _registry_with_handler(lambda db, job: HandlerResult.success())
    emitter = RuntimeEventEmitter("worker", "test", "test-release")
    runner = _runner(registry, event_emitter=emitter)

    assert runner.process_once() == "idle"
    assert capsys.readouterr().out == ""
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
