"""Finite queue-state/claimability aggregates from real PostgreSQL rows."""

import uuid
from datetime import timedelta

import pytest
from sqlalchemy import func, select

from backend.database import SessionLocal
from backend.models import DurableJob, DurableJobEvent
from backend.observability.metrics import (
    BACKLOG_STATES,
    JOB_TYPES,
    PRODUCTION_JOB_TYPES,
    MetricsRecorder,
)
from backend.services.durable_job_service import (
    CLAIMABLE_STATUSES,
    backlog_metric_observations,
    operator_cancel_job,
    requeue_exhausted_job,
)
from backend.services.payment_job_service import build_production_job_registry


@pytest.mark.parametrize(
    "status",
    ["pending", "retry_waiting", "leased", "exhausted", "succeeded", "cancelled"],
)
@pytest.mark.parametrize(
    "kind", [*PRODUCTION_JOB_TYPES, "unknown", "unsupported_version"]
)
@pytest.mark.parametrize("availability", ["ready", "future", "attempt_limit"])
def test_complete_status_type_version_claimability_matrix(status, kind, availability):
    registry = build_production_job_registry()
    assert set(registry.supported_pairs) == {(kind, 1) for kind in PRODUCTION_JOB_TYPES}
    statuses = {
        "pending",
        "retry_waiting",
        "leased",
        "exhausted",
        "succeeded",
        "cancelled",
    }
    assert set(BACKLOG_STATES).isdisjoint({"succeeded", "cancelled"})
    assert set(BACKLOG_STATES) | {"succeeded", "cancelled"} == statuses
    assert set(CLAIMABLE_STATUSES) == {"pending", "retry_waiting"}
    with SessionLocal() as db:
        now = db.scalar(select(func.clock_timestamp()))
        job = DurableJob(
            job_type=kind
            if kind in PRODUCTION_JOB_TYPES
            else PRODUCTION_JOB_TYPES[0]
            if kind == "unsupported_version"
            else "private-arbitrary-type",
            payload_version=2 if kind == "unsupported_version" else 1,
            status=status,
            maximum_attempts=3,
            attempt_count=3 if availability == "attempt_limit" else 1,
            available_at=now + timedelta(hours=1 if availability == "future" else -1),
            correlation_id="private-correlation",
            idempotency_key=str(uuid.uuid4()),
            payload={"private": "payload"},
            protected_identity={"private": "identity"},
            result_metadata={"private": "result"},
        )
        if status == "leased":
            job.lease_token = uuid.uuid4()
            job.lease_owner = "private-worker"
            job.lease_expires_at = now - timedelta(minutes=1)
            job.heartbeat_at = now - timedelta(minutes=2)
        if status in {"succeeded", "exhausted", "cancelled"}:
            setattr(
                job,
                {
                    "succeeded": "completed_at",
                    "exhausted": "exhausted_at",
                    "cancelled": "cancelled_at",
                }[status],
                now,
            )
        db.add(job)
        db.commit()
        job_id = job.id
    # The recorder starts after persistence, proving restart-visible exhausted work.
    recorder = MetricsRecorder("api", "test", "backlog-test")

    def collect():
        with SessionLocal() as db:
            return backlog_metric_observations(db, registry=registry)

    recorder.register_observable("durable_backlog", collect)
    snapshot = recorder.collect()
    counts = [item for item in snapshot.series if item.name == "worker.backlog.count"]
    assert len(counts) == 16
    mapped = kind if kind in PRODUCTION_JOB_TYPES else "unsupported"
    for item in counts:
        labels = dict(item.dimensions)
        assert item.value == int(
            status in BACKLOG_STATES
            and labels == {"job_type": mapped, "result": status}
        )
    ages = [
        item
        for item in snapshot.series
        if item.name == "worker.backlog.oldest_age_seconds"
    ]
    ready = status in CLAIMABLE_STATUSES and availability == "ready"
    assert len(ages) == int(ready)
    if ready:
        assert dict(ages[0].dimensions) == {"job_type": mapped}
        assert 3600 <= ages[0].value < 3610
    assert "private" not in repr(snapshot)
    with SessionLocal() as db:
        db.delete(db.get(DurableJob, job_id))
        db.commit()
    emptied = recorder.collect()
    assert len(emptied.series) == 16
    assert all(item.value == 0 for item in emptied.series)


def test_aggregate_query_projects_only_bounded_domain_aggregates():
    class InspectSession:
        def execute(self, statement):
            sql = str(statement)
            for prohibited in (
                "durable_jobs.payload,",
                "durable_jobs.protected_identity",
                "durable_jobs.result_metadata",
                "durable_jobs.correlation_id",
                "durable_jobs.lease_token",
            ):
                assert prohibited not in sql
            assert (
                "CASE" in sql
                and "count(" in sql
                and "min(" in sql
                and "metric_clock" in sql
            )
            return self

        def all(self):
            return []

    rows = backlog_metric_observations(
        InspectSession(), registry=build_production_job_registry()
    )
    assert len(rows) == len(JOB_TYPES) * len(BACKLOG_STATES) == 16
    assert all(value == 0 for _, value, _ in rows)


def test_exhausted_backlog_resolves_through_requeue_and_cancellation_without_collection_writes():
    registry = build_production_job_registry()
    job_type = PRODUCTION_JOB_TYPES[0]
    with SessionLocal() as db:
        now = db.scalar(select(func.clock_timestamp()))
        jobs = [
            DurableJob(
                id=uuid.uuid4(),
                job_type=job_type,
                payload_version=1,
                status="exhausted",
                attempt_count=1,
                maximum_attempts=1,
                available_at=now - timedelta(minutes=5),
                exhausted_at=now,
                correlation_id="private-correlation",
                idempotency_key=str(uuid.uuid4()),
                payload={"private": "payload"},
                protected_identity={"private": "identity"},
                result_metadata={"private": "result"},
            )
            for _ in range(2)
        ]
        db.add_all(jobs)
        db.commit()
        requeued_id, cancelled_id = (job.id for job in jobs)

    recorder = MetricsRecorder("api", "test", "backlog-test")

    def collect():
        with SessionLocal() as db:
            before = (
                db.scalar(select(func.count()).select_from(DurableJobEvent)),
                tuple(
                    db.execute(
                        select(DurableJob.id, DurableJob.status).order_by(DurableJob.id)
                    ).all()
                ),
            )
            observations = backlog_metric_observations(db, registry=registry)
            after = (
                db.scalar(select(func.count()).select_from(DurableJobEvent)),
                tuple(
                    db.execute(
                        select(DurableJob.id, DurableJob.status).order_by(DurableJob.id)
                    ).all()
                ),
            )
            assert after == before
            return observations

    recorder.register_observable("durable_backlog", collect)

    def counts():
        return {
            (dict(item.dimensions)["job_type"], dict(item.dimensions)["result"]): (
                item.value
            )
            for item in recorder.collect().series
            if item.name == "worker.backlog.count"
        }

    assert counts()[(job_type, "exhausted")] == 2
    with SessionLocal() as db:
        assert requeue_exhausted_job(
            db,
            job_id=requeued_id,
            maximum_attempts=2,
        )
        db.commit()
    after_requeue = counts()
    assert after_requeue[(job_type, "exhausted")] == 1
    assert after_requeue[(job_type, "pending")] == 1

    with SessionLocal() as db:
        assert requeue_exhausted_job(
            db,
            job_id=cancelled_id,
            maximum_attempts=2,
        )
        assert operator_cancel_job(
            db,
            job_id=cancelled_id,
            reason_code="operator_cancel",
        )
        db.commit()
    after_exhausted_cancel = counts()
    assert after_exhausted_cancel[(job_type, "exhausted")] == 0
    assert after_exhausted_cancel[(job_type, "pending")] == 1

    with SessionLocal() as db:
        assert operator_cancel_job(
            db,
            job_id=requeued_id,
            reason_code="operator_cancel",
        )
        db.commit()
    emptied = recorder.collect()
    assert all(
        item.value == 0
        for item in emptied.series
        if item.name == "worker.backlog.count"
    )
    assert not any(
        item.name == "worker.backlog.oldest_age_seconds" for item in emptied.series
    )
