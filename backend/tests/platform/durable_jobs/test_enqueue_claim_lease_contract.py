from __future__ import annotations

from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, inspect, select
from sqlalchemy.exc import IntegrityError

from backend.models import DurableJob, DurableJobEvent, DurableWorkerHeartbeat
from backend.services.durable_job_service import (
    CANCELLED,
    EXHAUSTED,
    LEASED,
    PENDING,
    RETRY_WAITING,
    SUCCEEDED,
    ConflictingIdempotencyKeyError,
    DurableJobQueuePolicy,
    DurableJobRegistry,
    HandlerResult,
    InvalidJobPayloadError,
    JobDefinition,
    UnsupportedJobDefinitionError,
    backlog_summary,
    claim_job,
    complete_job,
    enqueue_job,
    exhaust_job,
    heartbeat_job,
    operator_cancel_job,
    release_job,
    requeue_exhausted_job,
    retry_job,
)


def _db_session():
    from backend.database import SessionLocal

    return SessionLocal()


def _registry(*definitions: JobDefinition) -> DurableJobRegistry:
    return DurableJobRegistry(definitions or (_definition(),))


def _definition(
    job_type: str = "synthetic_job",
    *,
    payload_version: int = 1,
    maximum_attempts: int = 3,
) -> JobDefinition:
    def validate(payload):
        if payload.get("invalid"):
            raise InvalidJobPayloadError("synthetic invalid payload")

    return JobDefinition(
        job_type=job_type,
        payload_version=payload_version,
        maximum_attempts=maximum_attempts,
        handler=lambda db, job: HandlerResult.success(),
        payload_validator=validate,
    )


def _handlerless_definition(
    job_type: str = "synthetic_job",
    *,
    payload_version: int = 1,
    maximum_attempts: int = 3,
) -> JobDefinition:
    return JobDefinition(
        job_type=job_type,
        payload_version=payload_version,
        maximum_attempts=maximum_attempts,
    )


def _enqueue(
    *,
    registry: DurableJobRegistry | None = None,
    key: str | None = None,
    payload_version: int = 1,
    priority: int = 0,
    maximum_attempts: int = 3,
    available_offset: timedelta = timedelta(seconds=0),
) -> UUID:
    active_registry = registry or _registry(
        _definition(payload_version=payload_version, maximum_attempts=maximum_attempts)
    )
    with _db_session() as db:
        now = db.execute(select(func.clock_timestamp())).scalar_one()
        job = enqueue_job(
            db,
            registry=active_registry,
            job_type="synthetic_job",
            payload_version=payload_version,
            payload={"kind": "synthetic", "version": payload_version},
            protected_identity={"subject": "synthetic-subject"},
            idempotency_key=key or f"synthetic-{uuid4()}",
            priority=priority,
            maximum_attempts=maximum_attempts,
            available_at=now + available_offset,
            correlation_id="correlation-synthetic",
        )
        job_id = job.id
        db.commit()
        return job_id


def _base_job_insert_values(**overrides):
    values = {
        "id": uuid4(),
        "job_type": "synthetic_job",
        "payload_version": 1,
        "maximum_attempts": 3,
        "correlation_id": "correlation-synthetic",
        "idempotency_key": f"synthetic-{uuid4()}",
    }
    values.update(overrides)
    return values


@pytest.mark.no_db_cleanup
@pytest.mark.requirement("WS05-01A-R1")
def test_durable_job_models_declare_required_lifecycle_constraints() -> None:
    job_constraints = {
        constraint.name
        for constraint in DurableJob.__table__.constraints
        if constraint.name
    }
    event_constraints = {
        constraint.name
        for constraint in DurableJobEvent.__table__.constraints
        if constraint.name
    }
    heartbeat_constraints = {
        constraint.name
        for constraint in DurableWorkerHeartbeat.__table__.constraints
        if constraint.name
    }

    assert {
        "ck_durable_jobs_status",
        "ck_durable_jobs_attempt_count_within_maximum",
        "ck_durable_jobs_lease_fields_match_status",
        "ck_durable_jobs_terminal_fields_match_status",
        "uq_durable_jobs_idempotency_key",
    } <= job_constraints
    assert "ck_durable_job_events_event_type" in event_constraints
    assert "ck_durable_worker_heartbeats_status" in heartbeat_constraints


@pytest.mark.requirement("WS05-01A-R1")
def test_durable_job_database_defaults_schema_and_constraints_are_real() -> None:
    job_id = uuid4()
    event_id = uuid4()
    with _db_session() as db:
        db.execute(
            DurableJob.__table__.insert().values(
                _base_job_insert_values(
                    id=job_id,
                    idempotency_key=f"default-{uuid4()}",
                )
            )
        )
        db.execute(
            DurableJobEvent.__table__.insert().values(
                {
                    "id": event_id,
                    "job_id": job_id,
                    "event_type": "enqueued",
                    "new_status": PENDING,
                }
            )
        )
        db.execute(
            DurableWorkerHeartbeat.__table__.insert().values(
                {
                    "worker_identity": "default-worker",
                    "worker_version": "test-version",
                    "current_job_id": job_id,
                }
            )
        )
        db.commit()

    with _db_session() as db:
        stored = db.get(DurableJob, job_id)
        assert stored is not None
        assert stored.status == PENDING
        assert stored.payload == {}
        assert stored.protected_identity == {}
        assert stored.result_metadata == {}
        assert stored.priority == 0
        assert stored.attempt_count == 0
        assert stored.available_at.tzinfo is not None
        assert stored.created_at.tzinfo is not None
        assert stored.updated_at.tzinfo is not None

        event = db.get(DurableJobEvent, event_id)
        assert event is not None
        assert event.event_metadata == {}
        assert event.occurred_at.tzinfo is not None
        assert event.created_at.tzinfo is not None

        heartbeat = db.get(DurableWorkerHeartbeat, "default-worker")
        assert heartbeat is not None
        assert heartbeat.status == "starting"
        assert heartbeat.last_started_at.tzinfo is not None
        assert heartbeat.last_heartbeat_at.tzinfo is not None
        assert heartbeat.created_at.tzinfo is not None
        assert heartbeat.updated_at.tzinfo is not None

        schema = inspect(db.bind)
        job_columns = {column["name"] for column in schema.get_columns("durable_jobs")}
        assert {
            "id",
            "payload",
            "protected_identity",
            "status",
            "lease_token",
            "lease_expires_at",
            "result_metadata",
            "completed_at",
            "exhausted_at",
            "cancelled_at",
        } <= job_columns

        job_indexes = {index["name"] for index in schema.get_indexes("durable_jobs")}
        assert {
            "ix_durable_jobs_claimable",
            "ix_durable_jobs_type_version_status",
            "ix_durable_jobs_lease_expiry",
        } <= job_indexes
        event_fks = schema.get_foreign_keys("durable_job_events")
        heartbeat_fks = schema.get_foreign_keys("durable_worker_heartbeats")
        assert any(fk["referred_table"] == "durable_jobs" for fk in event_fks)
        assert any(fk["referred_table"] == "durable_jobs" for fk in heartbeat_fks)


@pytest.mark.requirement("WS05-01A-R1")
@pytest.mark.parametrize(
    "_case_name, overrides_factory",
    (
        (
            "leased_without_lease_fields",
            lambda now: {"status": LEASED},
        ),
        (
            "pending_with_lease_fields",
            lambda now: {
                "status": PENDING,
                "lease_token": uuid4(),
                "lease_owner": "unsafe-worker",
                "lease_expires_at": now + timedelta(seconds=30),
                "heartbeat_at": now,
            },
        ),
        (
            "succeeded_without_completed_at",
            lambda now: {"status": SUCCEEDED},
        ),
        (
            "succeeded_with_exhausted_timestamp",
            lambda now: {
                "status": SUCCEEDED,
                "completed_at": now,
                "exhausted_at": now,
            },
        ),
        (
            "exhausted_without_exhausted_at",
            lambda now: {"status": EXHAUSTED},
        ),
        (
            "cancelled_with_completed_timestamp",
            lambda now: {
                "status": CANCELLED,
                "completed_at": now,
                "cancelled_at": now,
            },
        ),
        (
            "attempt_count_exceeds_maximum",
            lambda now: {"attempt_count": 2, "maximum_attempts": 1},
        ),
        (
            "payload_must_be_json_object",
            lambda now: {"payload": ["not", "an", "object"]},
        ),
    ),
)
def test_durable_job_database_rejects_impossible_lifecycle_states(
    _case_name,
    overrides_factory,
) -> None:
    with _db_session() as db:
        now = db.execute(select(func.clock_timestamp())).scalar_one()
        values = _base_job_insert_values(**overrides_factory(now))

        with pytest.raises(IntegrityError):
            db.execute(DurableJob.__table__.insert().values(values))
            db.flush()
        db.rollback()


@pytest.mark.requirement("WS05-01A-R1", "WS05-01A-R2")
def test_enqueue_is_transactional_idempotent_and_conflict_checked() -> None:
    registry = _registry()

    with _db_session() as db:
        job = enqueue_job(
            db,
            registry=registry,
            job_type="synthetic_job",
            payload_version=1,
            payload={"kind": "synthetic"},
            protected_identity={"operation": "one"},
            idempotency_key="ws05-01a-idempotent",
            correlation_id="ws05-01a-correlation",
        )
        duplicate = enqueue_job(
            db,
            registry=registry,
            job_type="synthetic_job",
            payload_version=1,
            payload={"kind": "synthetic"},
            protected_identity={"operation": "one"},
            idempotency_key="ws05-01a-idempotent",
            correlation_id="ws05-01a-correlation",
        )

        assert duplicate.id == job.id
        assert db.execute(select(DurableJob)).scalars().all() == [job]
        db.rollback()

    with _db_session() as db:
        assert db.execute(select(DurableJob)).scalars().all() == []

        enqueue_job(
            db,
            registry=registry,
            job_type="synthetic_job",
            payload_version=1,
            payload={"kind": "synthetic"},
            protected_identity={"operation": "one"},
            idempotency_key="ws05-01a-conflict",
            correlation_id="ws05-01a-correlation",
        )
        db.commit()

    with _db_session() as db:
        with pytest.raises(ConflictingIdempotencyKeyError):
            enqueue_job(
                db,
                registry=registry,
                job_type="synthetic_job",
                payload_version=1,
                payload={"kind": "synthetic"},
                protected_identity={"operation": "different"},
                idempotency_key="ws05-01a-conflict",
                correlation_id="ws05-01a-correlation",
            )


@pytest.mark.requirement("WS05-01A-R2", "WS05-01A-R4")
def test_enqueue_rejects_unsupported_definitions_and_invalid_payloads() -> None:
    registry = _registry()

    with _db_session() as db:
        with pytest.raises(UnsupportedJobDefinitionError):
            enqueue_job(
                db,
                registry=registry,
                job_type="missing_job",
                payload_version=1,
                payload={},
                idempotency_key="ws05-01a-unsupported",
                correlation_id="ws05-01a-correlation",
            )

        with pytest.raises(InvalidJobPayloadError):
            enqueue_job(
                db,
                registry=registry,
                job_type="synthetic_job",
                payload_version=1,
                payload={"invalid": True},
                idempotency_key="ws05-01a-invalid",
                correlation_id="ws05-01a-correlation",
            )

        assert db.execute(select(DurableJob)).scalars().all() == []


@pytest.mark.requirement("WS05-01A-R2", "WS05-01A-R3", "WS05-01A-R4")
def test_handlerless_definitions_cannot_create_claimable_runnable_work() -> None:
    handlerless_registry = _registry(_handlerless_definition())
    assert handlerless_registry.supported_pairs == ()
    assert not handlerless_registry.supports("synthetic_job", 1)

    with _db_session() as db:
        with pytest.raises(UnsupportedJobDefinitionError):
            enqueue_job(
                db,
                registry=handlerless_registry,
                job_type="synthetic_job",
                payload_version=1,
                payload={"kind": "synthetic"},
                idempotency_key="ws05-01a-handlerless-enqueue",
                correlation_id="ws05-01a-correlation",
            )
        assert db.execute(select(DurableJob)).scalars().all() == []

    executable_registry = _registry()
    assert executable_registry.supports("synthetic_job", 1)
    job_id = _enqueue(registry=executable_registry)

    with _db_session() as db:
        assert (
            claim_job(
                db,
                registry=handlerless_registry,
                worker_identity="handlerless-worker",
            )
            is None
        )
        summary = backlog_summary(db, registry=handlerless_registry)
        assert summary.unsupported_type_versions == (("synthetic_job", 1),)
        db.commit()

    with _db_session() as db:
        stored = db.get(DurableJob, job_id)
        assert stored.status == PENDING
        assert stored.attempt_count == 0
        assert stored.lease_token is None
        event_types = [
            event.event_type
            for event in db.execute(
                select(DurableJobEvent).where(DurableJobEvent.job_id == job_id)
            ).scalars()
        ]
        assert event_types == ["enqueued"]


@pytest.mark.requirement("WS05-01A-R1", "WS05-01A-R3", "WS05-01A-R4")
def test_independent_sessions_skip_locked_rows_and_preserve_version_overlap() -> None:
    registry = _registry()
    job_id = _enqueue(registry=registry)

    session_one = _db_session()
    session_two = _db_session()
    try:
        first_claim = claim_job(
            session_one,
            registry=registry,
            worker_identity="worker-a",
        )
        second_claim = claim_job(
            session_two,
            registry=registry,
            worker_identity="worker-b",
        )

        assert first_claim is not None
        assert first_claim.job.id == job_id
        assert second_claim is None
    finally:
        session_two.rollback()
        session_two.close()
        session_one.rollback()
        session_one.close()

    with _db_session() as db:
        cleanup_claim = claim_job(
            db,
            registry=registry,
            worker_identity="cleanup-worker",
        )
        assert cleanup_claim is not None
        assert cleanup_claim.job.id == job_id
        assert complete_job(
            db,
            job_id=job_id,
            lease_token=cleanup_claim.lease_token,
        )
        db.commit()

    newer_registry = _registry(_definition(payload_version=2))
    version_two_id = _enqueue(registry=newer_registry, payload_version=2)

    with _db_session() as db:
        assert (
            claim_job(db, registry=registry, worker_identity="old-worker") is None
        )
        db.rollback()

    with _db_session() as db:
        untouched = db.get(DurableJob, version_two_id)
        assert untouched.status == PENDING
        assert untouched.attempt_count == 0
        assert untouched.lease_token is None

        compatible_claim = claim_job(
            db,
            registry=newer_registry,
            worker_identity="new-worker",
        )
        assert compatible_claim is not None
        assert compatible_claim.job.id == version_two_id
        db.rollback()


@pytest.mark.requirement("WS05-01A-R3", "WS05-01A-R5")
def test_claim_order_uses_fairness_before_newer_priority() -> None:
    registry = _registry()
    old_low_id = _enqueue(
        registry=registry,
        priority=1,
        available_offset=timedelta(seconds=-30),
    )
    _enqueue(
        registry=registry,
        priority=99,
        available_offset=timedelta(seconds=-1),
    )
    policy = DurableJobQueuePolicy(
        lease_duration=timedelta(seconds=30),
        heartbeat_interval=timedelta(seconds=10),
        fairness_age=timedelta(seconds=5),
    )

    with _db_session() as db:
        claim = claim_job(
            db,
            registry=registry,
            worker_identity="fair-worker",
            policy=policy,
        )
        assert claim is not None
        assert claim.job.id == old_low_id
        db.rollback()


@pytest.mark.requirement("WS05-01A-R3", "WS05-01A-R5")
def test_heartbeat_renews_lease_and_stale_tokens_cannot_mutate() -> None:
    registry = _registry(_definition(maximum_attempts=2))
    job_id = _enqueue(registry=registry, maximum_attempts=2)
    policy = DurableJobQueuePolicy(
        lease_duration=timedelta(seconds=30),
        heartbeat_interval=timedelta(seconds=10),
        fairness_age=timedelta(seconds=5),
    )

    with _db_session() as db:
        claim = claim_job(
            db,
            registry=registry,
            worker_identity="lease-worker",
            policy=policy,
        )
        assert claim is not None
        original_expiry = claim.job.lease_expires_at
        assert heartbeat_job(
            db,
            job_id=job_id,
            lease_token=claim.lease_token,
            policy=policy,
        )
        db.flush()
        assert db.get(DurableJob, job_id).lease_expires_at > original_expiry
        db.commit()
        stale_token = claim.lease_token

    with _db_session() as db:
        stored = db.get(DurableJob, job_id)
        stored.lease_expires_at = stored.heartbeat_at - timedelta(seconds=1)
        db.commit()

    with _db_session() as db:
        assert not heartbeat_job(
            db,
            job_id=job_id,
            lease_token=stale_token,
            policy=policy,
        )
        recovered = claim_job(
            db,
            registry=registry,
            worker_identity="recovery-worker",
            policy=policy,
        )
        assert recovered is not None
        assert recovered.job.id == job_id
        assert recovered.lease_token != stale_token
        assert not complete_job(
            db,
            job_id=job_id,
            lease_token=stale_token,
            result_metadata={"outcome": "stale"},
        )
        assert not retry_job(
            db,
            job_id=job_id,
            lease_token=stale_token,
            error_code="stale_retry",
            retry_delay=timedelta(seconds=1),
        )
        assert not exhaust_job(
            db,
            job_id=job_id,
            lease_token=stale_token,
            error_code="stale_exhaust",
        )
        assert complete_job(
            db,
            job_id=job_id,
            lease_token=recovered.lease_token,
            result_metadata={"outcome": "done"},
        )
        db.commit()

    with _db_session() as db:
        completed = db.get(DurableJob, job_id)
        assert completed.status == SUCCEEDED
        assert completed.attempt_count == 2


@pytest.mark.requirement("WS05-01A-R3", "WS05-01A-R5")
def test_worker_release_requires_current_lease_token_after_recovery() -> None:
    registry = _registry(_definition(maximum_attempts=3))
    job_id = _enqueue(registry=registry, maximum_attempts=3)
    policy = DurableJobQueuePolicy(
        lease_duration=timedelta(seconds=30),
        heartbeat_interval=timedelta(seconds=10),
        fairness_age=timedelta(seconds=5),
    )

    with _db_session() as db:
        original_claim = claim_job(
            db,
            registry=registry,
            worker_identity="release-original-worker",
            policy=policy,
        )
        assert original_claim is not None
        stale_token = original_claim.lease_token
        stored = db.get(DurableJob, job_id)
        stored.lease_expires_at = stored.heartbeat_at - timedelta(seconds=1)
        db.commit()

    with _db_session() as db:
        recovered_claim = claim_job(
            db,
            registry=registry,
            worker_identity="release-recovery-worker",
            policy=policy,
        )
        assert recovered_claim is not None
        assert recovered_claim.lease_token != stale_token
        recovered_state = db.get(DurableJob, job_id)
        unchanged_fields = {
            "status": recovered_state.status,
            "attempt_count": recovered_state.attempt_count,
            "lease_token": recovered_state.lease_token,
            "lease_owner": recovered_state.lease_owner,
            "lease_expires_at": recovered_state.lease_expires_at,
            "heartbeat_at": recovered_state.heartbeat_at,
        }

        assert not release_job(
            db,
            job_id=job_id,
            lease_token=stale_token,
            reason_code="stale_release",
        )
        after_stale_release = db.get(DurableJob, job_id)
        assert {
            "status": after_stale_release.status,
            "attempt_count": after_stale_release.attempt_count,
            "lease_token": after_stale_release.lease_token,
            "lease_owner": after_stale_release.lease_owner,
            "lease_expires_at": after_stale_release.lease_expires_at,
            "heartbeat_at": after_stale_release.heartbeat_at,
        } == unchanged_fields
        assert [
            event.event_type
            for event in db.execute(
                select(DurableJobEvent)
                .where(DurableJobEvent.job_id == job_id)
                .order_by(DurableJobEvent.occurred_at.asc())
            ).scalars()
        ] == ["enqueued", "claimed", "lease_recovered"]

        assert release_job(
            db,
            job_id=job_id,
            lease_token=recovered_claim.lease_token,
            reason_code="worker_release",
            result_metadata={"outcome": "shutdown"},
        )
        db.commit()

    with _db_session() as db:
        released = db.get(DurableJob, job_id)
        assert released.status == PENDING
        assert released.attempt_count == 2
        assert released.lease_token is None
        assert released.lease_owner is None
        assert released.lease_expires_at is None
        assert released.heartbeat_at is None
        assert released.last_error_code == "worker_release"
        assert released.result_metadata == {"outcome": "shutdown"}
        event_types = [
            event.event_type
            for event in db.execute(
                select(DurableJobEvent)
                .where(DurableJobEvent.job_id == job_id)
                .order_by(DurableJobEvent.occurred_at.asc())
            ).scalars()
        ]
        assert event_types == ["enqueued", "claimed", "lease_recovered", "released"]


@pytest.mark.requirement("WS05-01A-R3", "WS05-01A-R5")
def test_worker_release_at_final_attempt_exhausts_instead_of_reclaiming() -> None:
    registry = _registry(_definition(maximum_attempts=1))
    job_id = _enqueue(registry=registry, maximum_attempts=1)

    with _db_session() as db:
        claim = claim_job(db, registry=registry, worker_identity="final-release-worker")
        assert claim is not None
        assert release_job(
            db,
            job_id=job_id,
            lease_token=claim.lease_token,
            reason_code="worker_release_max_attempts",
        )
        db.commit()

    with _db_session() as db:
        exhausted = db.get(DurableJob, job_id)
        assert exhausted.status == EXHAUSTED
        assert exhausted.attempt_count == 1
        assert exhausted.lease_token is None
        assert exhausted.last_error_code == "worker_release_max_attempts"
        assert (
            claim_job(db, registry=registry, worker_identity="post-release-worker")
            is None
        )


@pytest.mark.requirement("WS05-01A-R1", "WS05-01A-R5")
def test_expired_final_attempt_exhausts_without_extra_attempt() -> None:
    registry = _registry(_definition(maximum_attempts=1))
    job_id = _enqueue(registry=registry, maximum_attempts=1)
    policy = DurableJobQueuePolicy(
        lease_duration=timedelta(seconds=30),
        heartbeat_interval=timedelta(seconds=10),
        fairness_age=timedelta(seconds=5),
    )

    with _db_session() as db:
        claim = claim_job(
            db,
            registry=registry,
            worker_identity="final-worker",
            policy=policy,
        )
        assert claim is not None
        stored = db.get(DurableJob, job_id)
        stored.lease_expires_at = stored.heartbeat_at - timedelta(seconds=1)
        db.commit()

    with _db_session() as db:
        assert (
            claim_job(
                db,
                registry=registry,
                worker_identity="recovery-worker",
                policy=policy,
            )
            is None
        )
        db.commit()

    with _db_session() as db:
        exhausted = db.get(DurableJob, job_id)
        assert exhausted.status == EXHAUSTED
        assert exhausted.attempt_count == 1
        assert exhausted.last_error_code == "lease_expired_max_attempts"
        assert exhausted.lease_token is None
        event_types = [
            event.event_type
            for event in db.execute(
                select(DurableJobEvent).where(DurableJobEvent.job_id == job_id)
            ).scalars()
        ]
        assert event_types == ["enqueued", "claimed", "lease_expired_exhausted"]


@pytest.mark.requirement("WS05-01A-R5", "WS05-01A-R7")
def test_operator_cancel_and_requeue_preserve_durable_history() -> None:
    registry = _registry(_definition(maximum_attempts=1))
    cancelled_id = _enqueue(registry=registry, key="ws05-01a-cancel", maximum_attempts=1)

    with _db_session() as db:
        assert operator_cancel_job(
            db,
            job_id=cancelled_id,
            reason_code="operator_cancel",
        )
        db.commit()

    with _db_session() as db:
        cancelled = db.get(DurableJob, cancelled_id)
        assert cancelled.status == CANCELLED
        assert cancelled.cancelled_at is not None
        assert cancelled.last_error_code == "operator_cancel"
        assert (
            claim_job(db, registry=registry, worker_identity="cancel-check-worker")
            is None
        )
        event_types = [
            event.event_type
            for event in db.execute(
                select(DurableJobEvent)
                .where(DurableJobEvent.job_id == cancelled_id)
                .order_by(DurableJobEvent.occurred_at.asc())
            ).scalars()
        ]
        assert event_types == ["enqueued", "repair_cancelled"]

    leased_cancelled_id = _enqueue(
        registry=registry,
        key="ws05-01a-operator-cancel-leased",
        maximum_attempts=1,
    )
    with _db_session() as db:
        claim = claim_job(db, registry=registry, worker_identity="operator-cancel-worker")
        assert claim is not None
        assert claim.job.id == leased_cancelled_id
        assert operator_cancel_job(
            db,
            job_id=leased_cancelled_id,
            reason_code="operator_cancel",
        )
        db.commit()

    with _db_session() as db:
        leased_cancelled = db.get(DurableJob, leased_cancelled_id)
        assert leased_cancelled.status == CANCELLED
        assert leased_cancelled.lease_token is None
        assert leased_cancelled.lease_owner is None
        assert leased_cancelled.cancelled_at is not None
        event_types = [
            event.event_type
            for event in db.execute(
                select(DurableJobEvent)
                .where(DurableJobEvent.job_id == leased_cancelled_id)
                .order_by(DurableJobEvent.occurred_at.asc())
            ).scalars()
        ]
        assert event_types == ["enqueued", "claimed", "repair_cancelled"]

    requeued_id = _enqueue(registry=registry, key="ws05-01a-requeue", maximum_attempts=1)
    with _db_session() as db:
        claim = claim_job(db, registry=registry, worker_identity="exhaust-worker")
        assert claim is not None
        assert claim.job.id == requeued_id
        assert exhaust_job(
            db,
            job_id=requeued_id,
            lease_token=claim.lease_token,
            error_code="permanent_failure",
        )
        db.commit()

    with _db_session() as db:
        assert requeue_exhausted_job(
            db,
            job_id=requeued_id,
            maximum_attempts=2,
            reason_code="operator_requeue",
        )
        db.commit()

    with _db_session() as db:
        repaired = db.get(DurableJob, requeued_id)
        assert repaired.status == PENDING
        assert repaired.attempt_count == 0
        assert repaired.maximum_attempts == 2
        assert repaired.exhausted_at is None
        assert repaired.last_error_code is None

        events = db.execute(
            select(DurableJobEvent)
            .where(DurableJobEvent.job_id == requeued_id)
            .order_by(DurableJobEvent.occurred_at.asc())
        ).scalars().all()
        assert [event.event_type for event in events] == [
            "enqueued",
            "claimed",
            "exhausted",
            "repair_requeued",
        ]
        repair_event = events[-1]
        assert repair_event.previous_status == EXHAUSTED
        assert repair_event.new_status == PENDING
        assert repair_event.event_metadata == {
            "previous_attempt_count": 1,
            "new_maximum_attempts": 2,
        }

        claim = claim_job(db, registry=registry, worker_identity="repaired-worker")
        assert claim is not None
        assert claim.job.id == requeued_id
        assert claim.job.attempt_count == 1
