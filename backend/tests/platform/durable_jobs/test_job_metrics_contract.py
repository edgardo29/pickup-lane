"""Committed execution outcomes and transient reconciliation handoff isolation."""

import uuid
from datetime import timedelta

import pytest
from sqlalchemy import func, select

from backend.database import SessionLocal
from backend.models import DurableJob, DurableJobEvent
from backend.observability.metrics import MetricsRecorder, stage_reconciliation_outcome
from backend.services import durable_job_service as jobs


def _runner(registry, recorder, factory=SessionLocal):
    return jobs.DurableJobRunner(
        session_factory=factory,
        registry=registry,
        worker_identity="metric-test-worker",
        worker_version="test",
        metrics_recorder=recorder,
        policy=jobs.DurableJobQueuePolicy(
            lease_duration=timedelta(seconds=30),
            heartbeat_interval=timedelta(seconds=10),
            fairness_age=timedelta(seconds=5),
        ),
    )


def _enqueue(registry, job_type, version=1, payload=None):
    with SessionLocal() as db:
        job = jobs.enqueue_job(
            db,
            registry=registry,
            job_type=job_type,
            payload_version=version,
            payload=payload or {},
            protected_identity={},
            idempotency_key=str(uuid.uuid4()),
            correlation_id=str(uuid.uuid4()),
        )
        job_id = job.id
        db.commit()
    return job_id


@pytest.mark.parametrize(
    "job_type",
    [
        "stripe_webhook_event",
        "stripe_payment_intent_reconcile",
        "stripe_payment_method_operation_reconcile",
        "synthetic",
    ],
)
@pytest.mark.parametrize(
    ("mode", "returned", "committed"),
    [
        ("success", "succeeded", "succeeded"),
        ("retry", "retry_waiting", "retry_waiting"),
        ("permanent", "exhausted", "exhausted"),
        ("final_transient", "retry_waiting", "exhausted"),
        ("exception", "retry_waiting", "retry_waiting"),
    ],
)
def test_runner_metrics_use_authoritative_committed_outcome(
    job_type, mode, returned, committed
):
    def handler(db, job):
        if mode == "exception":
            raise RuntimeError("private-provider-error")
        if mode in {"retry", "final_transient"}:
            return jobs.HandlerResult.transient_failure("transient_failure")
        if mode == "permanent":
            return jobs.HandlerResult.permanent_failure("permanent_failure")
        return jobs.HandlerResult.success()

    registry = jobs.DurableJobRegistry(
        (
            jobs.JobDefinition(
                job_type,
                1,
                maximum_attempts=1 if mode == "final_transient" else 3,
                handler=handler,
            ),
        )
    )
    job_id = _enqueue(registry, job_type)
    recorder = MetricsRecorder("worker", "test", "worker-metric-test")
    runner = _runner(registry, recorder)
    assert runner.process_once() == returned
    series = recorder.snapshot().series
    assert len(series) == 1 and series[0].value == 1
    assert dict(series[0].dimensions) == {
        "job_type": "unsupported" if job_type == "synthetic" else job_type,
        "result": committed,
    }
    with SessionLocal() as db:
        assert db.get(DurableJob, job_id).status == committed
    runner.request_shutdown()
    assert runner.process_once() == "shutdown"
    runner.mark_stopped()
    assert recorder.snapshot().series == series


@pytest.mark.parametrize("failure", ["commit", "lease", "exception"])
def test_staged_reconciliation_is_not_emitted_when_owning_transition_fails(
    monkeypatch, failure
):
    job_type = "stripe_payment_method_operation_reconcile"
    handler_calls = []

    def handler(db, job):
        handler_calls.append(job.id)
        stage_reconciliation_outcome(job_type, "failed")
        if failure == "exception":
            raise RuntimeError("private-error")
        return jobs.HandlerResult.success()

    registry = jobs.DurableJobRegistry(
        (jobs.JobDefinition(job_type, 1, maximum_attempts=3, handler=handler),)
    )
    job_id = _enqueue(registry, job_type)
    recorder = MetricsRecorder("worker", "test", "worker-metric-test")
    if failure == "lease":
        monkeypatch.setattr(jobs, "complete_job", lambda *a, **k: False)
    if failure == "commit":
        from sqlalchemy.orm import Session

        original = Session.commit
        calls = []

        def commit(session):
            calls.append(1)
            # Claim and current-job heartbeat commit first. Fail only after the
            # handler has staged telemetry and the owning completion is committing.
            if len(calls) == 3:
                raise RuntimeError("synthetic-final-commit-failure")
            original(session)

        monkeypatch.setattr(Session, "commit", commit)
    runner = _runner(registry, recorder)
    if failure == "commit":
        with pytest.raises(RuntimeError, match="final-commit"):
            runner.process_once()
    else:
        assert runner.process_once() == (
            "lease_lost" if failure == "lease" else "retry_waiting"
        )
    assert handler_calls == [job_id]
    assert not any(
        item.name == "payment.reconciliation.outcome.total"
        for item in recorder.snapshot().series
    )
    if failure == "commit":
        assert recorder.snapshot().series == ()
        with SessionLocal() as db:
            job = db.get(DurableJob, job_id)
            assert job.status == "leased"
            assert job.result_metadata == {}
            assert not db.scalar(
                select(func.count())
                .select_from(DurableJobEvent)
                .where(
                    DurableJobEvent.job_id == job_id,
                    DurableJobEvent.event_type == "succeeded",
                )
            )
    else:
        (worker_outcome,) = [
            item
            for item in recorder.snapshot().series
            if item.name == "worker.job.outcome.total"
        ]
        assert dict(worker_outcome.dimensions) == {
            "job_type": job_type,
            "result": "lease_lost" if failure == "lease" else "retry_waiting",
        }


def test_idle_and_shutdown_do_not_create_job_outcomes():
    recorder = MetricsRecorder("worker", "test", "worker-metric-test")
    runner = _runner(jobs.DurableJobRegistry(), recorder)

    assert runner.process_once() == "idle"
    runner.request_shutdown()
    assert runner.process_once() == "shutdown"

    assert not any(
        item.name == "worker.job.outcome.total" for item in recorder.snapshot().series
    )


def test_expired_final_lease_records_committed_exhaustion():
    job_type = "stripe_webhook_event"
    registry = jobs.DurableJobRegistry(
        (
            jobs.JobDefinition(
                job_type,
                1,
                maximum_attempts=1,
                handler=lambda db, job: jobs.HandlerResult.success(),
            ),
        )
    )
    job_id = _enqueue(registry, job_type)
    with SessionLocal() as db:
        now = db.scalar(select(func.clock_timestamp()))
        job = db.get(DurableJob, job_id)
        job.status = "leased"
        job.attempt_count = job.maximum_attempts
        job.lease_token = uuid.uuid4()
        job.lease_owner = "expired-worker"
        job.lease_expires_at = now - timedelta(seconds=1)
        job.heartbeat_at = now - timedelta(seconds=2)
        db.commit()

    recorder = MetricsRecorder("worker", "test", "worker-metric-test")
    assert _runner(registry, recorder).process_once() == "idle"

    (outcome,) = [
        item
        for item in recorder.snapshot().series
        if item.name == "worker.job.outcome.total"
    ]
    assert outcome.value == 1
    assert dict(outcome.dimensions) == {
        "job_type": job_type,
        "result": "exhausted",
    }
    with SessionLocal() as db:
        assert db.get(DurableJob, job_id).status == "exhausted"


@pytest.mark.parametrize("outcome", ["missing", "unsupported"])
def test_nontransition_diagnostics_remain_distinct(outcome):
    job_id = uuid.uuid4()
    summary = jobs._JobLogSummary(
        job_id=job_id,
        job_type="synthetic",
        payload_version=2,
        attempt_count=1,
        maximum_attempts=3,
        correlation_id=None,
    )
    if outcome == "unsupported":
        with SessionLocal() as db:
            db.add(
                DurableJob(
                    id=job_id,
                    job_type="synthetic",
                    payload_version=2,
                    maximum_attempts=3,
                    correlation_id="private",
                    idempotency_key=str(uuid.uuid4()),
                )
            )
            db.commit()
    recorder = MetricsRecorder("worker", "test", "worker-metric-test")
    runner = _runner(jobs.DurableJobRegistry(), recorder)
    assert runner._run_handler(job_id, uuid.uuid4(), summary) == outcome
    (item,) = recorder.snapshot().series
    assert dict(item.dimensions) == {"job_type": "unsupported", "result": outcome}


@pytest.mark.parametrize(
    ("producer", "scalar", "result", "worker_result"),
    [
        ("pi", "processed", "succeeded", "succeeded"),
        ("pi", "already_terminal", "already_terminal", "succeeded"),
        ("pi", "permanent_failure", "failed", "exhausted"),
        ("pi", "retry", "pending", "retry_waiting"),
        ("pm", "succeeded", "succeeded", "succeeded"),
        ("pm", "failed", "failed", "succeeded"),
        ("pm", "provider_unknown", "pending", "retry_waiting"),
        ("pm_missing", None, "failed", "succeeded"),
    ],
)
def test_actual_consumer_and_runner_keep_domain_result_distinct(
    monkeypatch, producer, scalar, result, worker_result
):
    from backend.services import (
        payment_job_service,
        payment_method_service,
        payment_transition_service,
    )

    if producer == "pi":
        monkeypatch.setattr(
            payment_transition_service, "reconcile_payment_intent", lambda *a: scalar
        )
        job_type = payment_job_service.STRIPE_PAYMENT_INTENT_RECONCILE_JOB
        payload = {"payment_id": str(uuid.uuid4())}
    else:
        if producer != "pm_missing":
            monkeypatch.setattr(
                payment_method_service,
                "reconcile_payment_method_operation",
                lambda *a: scalar,
            )
        # Missing operation uses the real domain consumer, not a mocked scalar.
        job_type = payment_job_service.STRIPE_PAYMENT_METHOD_OPERATION_RECONCILE_JOB
        payload = {"payment_method_operation_id": str(uuid.uuid4())}
    registry = payment_job_service.build_production_job_registry()
    job_id = _enqueue(registry, job_type, payload=payload)
    recorder = MetricsRecorder("worker", "test", "consumer-metric-test")
    assert _runner(registry, recorder).process_once() == worker_result
    observations = {item.name: item for item in recorder.snapshot().series}
    assert dict(observations["payment.reconciliation.outcome.total"].dimensions) == {
        "job_type": job_type,
        "result": result,
    }
    assert dict(observations["worker.job.outcome.total"].dimensions) == {
        "job_type": job_type,
        "result": worker_result,
    }
    assert all(item.value == 1 for item in observations.values())
    with SessionLocal() as db:
        job = db.get(DurableJob, job_id)
        events = db.scalars(
            select(DurableJobEvent).where(DurableJobEvent.job_id == job_id)
        ).all()
        assert "staged" not in str(job.result_metadata)
        assert "reconciliation_metric" not in str(job.result_metadata)
        assert all("staged" not in str(event.event_metadata) for event in events)


def test_repeated_reconciliation_attempts_are_separate_observations(monkeypatch):
    from backend.services import payment_job_service, payment_transition_service

    outcomes = iter(("retry", "processed"))
    monkeypatch.setattr(
        payment_transition_service,
        "reconcile_payment_intent",
        lambda *args: next(outcomes),
    )
    job_type = payment_job_service.STRIPE_PAYMENT_INTENT_RECONCILE_JOB
    registry = payment_job_service.build_production_job_registry()
    job_id = _enqueue(
        registry,
        job_type,
        payload={"payment_id": str(uuid.uuid4())},
    )
    recorder = MetricsRecorder("worker", "test", "consumer-metric-test")
    runner = _runner(registry, recorder)

    assert runner.process_once() == "retry_waiting"
    with SessionLocal() as db:
        job = db.get(DurableJob, job_id)
        job.available_at = db.scalar(select(func.clock_timestamp()))
        db.commit()
    assert runner.process_once() == "succeeded"

    reconciliation = {
        dict(item.dimensions)["result"]: item.value
        for item in recorder.snapshot().series
        if item.name == "payment.reconciliation.outcome.total"
    }
    assert reconciliation == {"pending": 1, "succeeded": 1}
