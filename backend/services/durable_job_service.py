"""PostgreSQL-backed durable job lifecycle for WS05-01A.

This module owns the generic durable-job framework only. It intentionally does
not register payment, refund, credit, notification, moderation, storage, or
provider handlers.
"""

from __future__ import annotations

import re
from threading import Event, Thread
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Iterable, Mapping, Sequence

from sqlalchemy import case, func, select, tuple_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from backend.models import DurableJob, DurableJobEvent, DurableWorkerHeartbeat
from backend.observability.redaction import contains_sensitive_text, is_sensitive_key


PENDING = "pending"
RETRY_WAITING = "retry_waiting"
LEASED = "leased"
SUCCEEDED = "succeeded"
EXHAUSTED = "exhausted"
CANCELLED = "cancelled"
CLAIMABLE_STATUSES = (PENDING, RETRY_WAITING)
TERMINAL_STATUSES = (SUCCEEDED, EXHAUSTED, CANCELLED)
DEFAULT_LEASE_DURATION = timedelta(seconds=30)
DEFAULT_HEARTBEAT_INTERVAL = timedelta(seconds=10)
DEFAULT_FAIRNESS_AGE = timedelta(minutes=5)
DEFAULT_POLL_INTERVAL_SECONDS = 5.0
DEFAULT_WORKER_VERSION = "source"
_SAFE_KEY_RE = re.compile(r"^[a-z][a-z0-9_]{0,49}$")
_SAFE_CODE_RE = re.compile(r"^[a-z][a-z0-9_]{0,79}$")


class DurableJobError(RuntimeError):
    """Base durable-job error."""


class UnsupportedJobDefinitionError(DurableJobError):
    """Raised when a requested type/version is not registered."""


class ConflictingIdempotencyKeyError(DurableJobError):
    """Raised when an idempotency key is reused for different durable work."""


class UnsafeDiagnosticMetadataError(DurableJobError):
    """Raised when metadata is unsafe to store in job diagnostics."""


class InvalidJobPayloadError(DurableJobError):
    """Raised when a registered payload validator rejects a job payload."""


class HandlerOutcome(str, Enum):
    SUCCESS = "success"
    TRANSIENT_FAILURE = "transient_failure"
    PERMANENT_FAILURE = "permanent_failure"


@dataclass(frozen=True)
class HandlerResult:
    outcome: HandlerOutcome
    result_metadata: Mapping[str, Any] = field(default_factory=dict)
    error_code: str | None = None
    retry_delay: timedelta | None = None

    @classmethod
    def success(cls, result_metadata: Mapping[str, Any] | None = None) -> "HandlerResult":
        return cls(
            outcome=HandlerOutcome.SUCCESS,
            result_metadata=result_metadata or {},
        )

    @classmethod
    def transient_failure(
        cls,
        error_code: str,
        *,
        retry_delay: timedelta | None = None,
        result_metadata: Mapping[str, Any] | None = None,
    ) -> "HandlerResult":
        return cls(
            outcome=HandlerOutcome.TRANSIENT_FAILURE,
            error_code=error_code,
            retry_delay=retry_delay,
            result_metadata=result_metadata or {},
        )

    @classmethod
    def permanent_failure(
        cls,
        error_code: str,
        *,
        result_metadata: Mapping[str, Any] | None = None,
    ) -> "HandlerResult":
        return cls(
            outcome=HandlerOutcome.PERMANENT_FAILURE,
            error_code=error_code,
            result_metadata=result_metadata or {},
        )


PayloadValidator = Callable[[Mapping[str, Any]], None]
JobHandler = Callable[[Session, DurableJob], HandlerResult]


@dataclass(frozen=True)
class JobDefinition:
    job_type: str
    payload_version: int
    maximum_attempts: int
    handler: JobHandler | None = None
    payload_validator: PayloadValidator | None = None
    transient_retry_delay: timedelta = timedelta(seconds=1)
    permanent_exception_error_code: str = "handler_permanent_failure"
    transient_exception_error_code: str = "handler_transient_failure"
    exceptions_are_transient: bool = True

    def __post_init__(self) -> None:
        if not _SAFE_CODE_RE.fullmatch(self.job_type):
            raise ValueError("job_type must be a safe lower-case diagnostic label")
        if self.payload_version < 1:
            raise ValueError("payload_version must be positive")
        if self.maximum_attempts < 1:
            raise ValueError("maximum_attempts must be positive")

    @property
    def key(self) -> tuple[str, int]:
        return (self.job_type, self.payload_version)

    def validate_payload(self, payload: Mapping[str, Any]) -> None:
        _validate_json_object("payload", payload)
        if self.payload_validator is not None:
            self.payload_validator(payload)


class DurableJobRegistry:
    def __init__(self, definitions: Iterable[JobDefinition] = ()) -> None:
        self._definitions = {definition.key: definition for definition in definitions}

    def definition_for(self, job_type: str, payload_version: int) -> JobDefinition:
        try:
            return self._definitions[(job_type, payload_version)]
        except KeyError as exc:
            raise UnsupportedJobDefinitionError(
                f"unsupported durable job type/version: {job_type} v{payload_version}"
            ) from exc

    @property
    def supported_pairs(self) -> tuple[tuple[str, int], ...]:
        return tuple(
            sorted(
                key
                for key, definition in self._definitions.items()
                if definition.handler is not None
            )
        )

    def executable_definition_for(self, job_type: str, payload_version: int) -> JobDefinition:
        definition = self.definition_for(job_type, payload_version)
        if definition.handler is None:
            raise UnsupportedJobDefinitionError(
                f"durable job type/version is not executable: {job_type} v{payload_version}"
            )
        return definition

    def supports(self, job_type: str, payload_version: int) -> bool:
        return (job_type, payload_version) in self.supported_pairs


@dataclass(frozen=True)
class DurableJobQueuePolicy:
    lease_duration: timedelta = DEFAULT_LEASE_DURATION
    heartbeat_interval: timedelta = DEFAULT_HEARTBEAT_INTERVAL
    fairness_age: timedelta = DEFAULT_FAIRNESS_AGE
    poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS

    def __post_init__(self) -> None:
        if self.lease_duration <= timedelta(0):
            raise ValueError("lease_duration must be positive")
        if self.heartbeat_interval <= timedelta(0):
            raise ValueError("heartbeat_interval must be positive")
        if self.heartbeat_interval >= self.lease_duration:
            raise ValueError("heartbeat_interval must be shorter than lease_duration")
        if self.fairness_age <= timedelta(0):
            raise ValueError("fairness_age must be positive")
        if self.poll_interval_seconds < 0:
            raise ValueError("poll_interval_seconds cannot be negative")


@dataclass(frozen=True)
class ClaimResult:
    job: DurableJob
    lease_token: uuid.UUID
    database_time: datetime


@dataclass(frozen=True)
class WorkerHeartbeatSummary:
    worker_identity: str
    worker_version: str
    status: str
    heartbeat_age_seconds: int
    has_current_job: bool


@dataclass(frozen=True)
class JobEventSummary:
    event_type: str
    previous_status: str | None
    new_status: str | None
    attempt_count: int | None
    lease_owner: str | None
    safe_error_code: str | None
    event_metadata: Mapping[str, Any]
    occurred_at: datetime


@dataclass(frozen=True)
class JobInspectionSummary:
    job_type: str
    payload_version: int
    status: str
    attempt_count: int
    maximum_attempts: int
    last_safe_error_code: str | None
    recent_events: tuple[JobEventSummary, ...]


@dataclass(frozen=True)
class BacklogSummary:
    by_status: Mapping[str, int]
    by_type_version: Mapping[tuple[str, int], int]
    unsupported_type_versions: tuple[tuple[str, int], ...]
    expired_leases: int
    exhausted_jobs: int
    retry_waiting_jobs: int
    oldest_pending_age_seconds: int | None
    fairness_protected_jobs: int
    attempt_counts_by_status: Mapping[str, Mapping[int, int]]
    worker_heartbeats: tuple[WorkerHeartbeatSummary, ...]


def enqueue_job(
    db: Session,
    *,
    registry: DurableJobRegistry,
    job_type: str,
    payload_version: int,
    payload: Mapping[str, Any],
    idempotency_key: str,
    protected_identity: Mapping[str, Any] | None = None,
    available_at: datetime | None = None,
    priority: int = 0,
    maximum_attempts: int | None = None,
    correlation_id: str | None = None,
    origin_reference_type: str | None = None,
    origin_reference_id: str | None = None,
) -> DurableJob:
    definition = registry.executable_definition_for(job_type, payload_version)
    definition.validate_payload(payload)
    identity = protected_identity or {}
    _validate_json_object("protected_identity", identity)
    _validate_safe_correlation_id(correlation_id)
    if priority < 0:
        raise ValueError("priority cannot be negative")
    attempts = maximum_attempts or definition.maximum_attempts
    if attempts < 1:
        raise ValueError("maximum_attempts must be positive")
    if attempts > definition.maximum_attempts:
        raise ValueError("maximum_attempts cannot exceed the registered policy")

    existing = _job_by_idempotency_key(db, idempotency_key)
    if existing is not None:
        _assert_idempotent_match(
            existing,
            job_type=job_type,
            payload_version=payload_version,
            protected_identity=dict(identity),
        )
        return existing

    now = _database_now(db)
    job = DurableJob(
        job_type=job_type,
        payload_version=payload_version,
        payload=dict(payload),
        protected_identity=dict(identity),
        priority=priority,
        available_at=available_at or now,
        status=PENDING,
        attempt_count=0,
        maximum_attempts=attempts,
        correlation_id=correlation_id or _generated_safe_correlation_id(),
        origin_reference_type=origin_reference_type,
        origin_reference_id=origin_reference_id,
        idempotency_key=idempotency_key,
        result_metadata={},
        created_at=now,
        updated_at=now,
    )
    try:
        with db.begin_nested():
            db.add(job)
            db.flush()
            _append_event(
                db,
                job,
                event_type="enqueued",
                previous_status=None,
                new_status=PENDING,
                metadata={"job_type": job_type, "payload_version": payload_version},
                occurred_at=now,
            )
            db.flush()
    except IntegrityError:
        existing = _job_by_idempotency_key(db, idempotency_key)
        if existing is None:
            raise
        _assert_idempotent_match(
            existing,
            job_type=job_type,
            payload_version=payload_version,
            protected_identity=dict(identity),
        )
        return existing
    return job


def claim_job(
    db: Session,
    *,
    registry: DurableJobRegistry,
    worker_identity: str,
    policy: DurableJobQueuePolicy | None = None,
) -> ClaimResult | None:
    active_policy = policy or DurableJobQueuePolicy()
    supported_pairs = registry.supported_pairs
    if not supported_pairs:
        return None

    now = _database_now(db)
    recovered = _recover_one_expired_lease(
        db,
        supported_pairs=supported_pairs,
        worker_identity=worker_identity,
        policy=active_policy,
        now=now,
    )
    if recovered is not None:
        return recovered

    threshold = now - active_policy.fairness_age
    fairness_bucket = case((DurableJob.available_at <= threshold, 0), else_=1)
    fairness_available = case(
        (DurableJob.available_at <= threshold, DurableJob.available_at),
        else_=None,
    )
    normal_priority = case(
        (DurableJob.available_at > threshold, DurableJob.priority),
        else_=None,
    )
    statement = (
        select(DurableJob)
        .where(
            DurableJob.status.in_(CLAIMABLE_STATUSES),
            DurableJob.available_at <= now,
            DurableJob.attempt_count < DurableJob.maximum_attempts,
            tuple_(DurableJob.job_type, DurableJob.payload_version).in_(supported_pairs),
        )
        .order_by(
            fairness_bucket.asc(),
            fairness_available.asc().nulls_last(),
            normal_priority.desc().nulls_last(),
            DurableJob.available_at.asc(),
            DurableJob.created_at.asc(),
            DurableJob.id.asc(),
        )
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    job = db.execute(statement).scalars().first()
    if job is None:
        return None
    return _lease_job(
        db,
        job,
        worker_identity=worker_identity,
        event_type="claimed",
        policy=active_policy,
        now=now,
    )


def heartbeat_job(
    db: Session,
    *,
    job_id: uuid.UUID,
    lease_token: uuid.UUID,
    policy: DurableJobQueuePolicy | None = None,
) -> bool:
    active_policy = policy or DurableJobQueuePolicy()
    now = _database_now(db)
    job = _locked_job_by_id(db, job_id)
    if not _owns_current_unexpired_lease(job, lease_token, now):
        return False

    job.heartbeat_at = now
    job.lease_expires_at = now + active_policy.lease_duration
    job.updated_at = now
    _append_event(
        db,
        job,
        event_type="heartbeat",
        previous_status=LEASED,
        new_status=LEASED,
        metadata={},
        occurred_at=now,
    )
    db.flush()
    return True


def complete_job(
    db: Session,
    *,
    job_id: uuid.UUID,
    lease_token: uuid.UUID,
    result_metadata: Mapping[str, Any] | None = None,
) -> bool:
    metadata = sanitize_diagnostic_metadata(result_metadata or {})
    now = _database_now(db)
    job = _locked_job_by_id(db, job_id)
    if not _owns_current_unexpired_lease(job, lease_token, now):
        return False

    job.status = SUCCEEDED
    job.lease_token = None
    job.lease_owner = None
    job.lease_expires_at = None
    job.heartbeat_at = None
    job.completed_at = now
    job.result_metadata = metadata
    job.updated_at = now
    _append_event(
        db,
        job,
        event_type="succeeded",
        previous_status=LEASED,
        new_status=SUCCEEDED,
        metadata=metadata,
        occurred_at=now,
    )
    db.flush()
    return True


def retry_job(
    db: Session,
    *,
    job_id: uuid.UUID,
    lease_token: uuid.UUID,
    error_code: str,
    retry_delay: timedelta,
    result_metadata: Mapping[str, Any] | None = None,
) -> bool:
    _validate_safe_code(error_code)
    metadata = sanitize_diagnostic_metadata(result_metadata or {})
    now = _database_now(db)
    job = _locked_job_by_id(db, job_id)
    if not _owns_current_unexpired_lease(job, lease_token, now):
        return False
    if job.attempt_count >= job.maximum_attempts:
        return exhaust_job(
            db,
            job_id=job_id,
            lease_token=lease_token,
            error_code=error_code,
            result_metadata=metadata,
        )

    job.status = RETRY_WAITING
    job.available_at = now + retry_delay
    job.lease_token = None
    job.lease_owner = None
    job.lease_expires_at = None
    job.heartbeat_at = None
    job.last_error_code = error_code
    job.result_metadata = metadata
    job.updated_at = now
    _append_event(
        db,
        job,
        event_type="retry_scheduled",
        previous_status=LEASED,
        new_status=RETRY_WAITING,
        error_code=error_code,
        metadata=metadata,
        occurred_at=now,
    )
    db.flush()
    return True


def exhaust_job(
    db: Session,
    *,
    job_id: uuid.UUID,
    lease_token: uuid.UUID,
    error_code: str,
    result_metadata: Mapping[str, Any] | None = None,
) -> bool:
    _validate_safe_code(error_code)
    metadata = sanitize_diagnostic_metadata(result_metadata or {})
    now = _database_now(db)
    job = _locked_job_by_id(db, job_id)
    if not _owns_current_unexpired_lease(job, lease_token, now):
        return False

    _transition_to_exhausted(
        db,
        job,
        error_code=error_code,
        metadata=metadata,
        previous_status=LEASED,
        event_type="exhausted",
        now=now,
    )
    db.flush()
    return True


def release_job(
    db: Session,
    *,
    job_id: uuid.UUID,
    lease_token: uuid.UUID,
    reason_code: str = "worker_release",
    available_at: datetime | None = None,
    result_metadata: Mapping[str, Any] | None = None,
) -> bool:
    _validate_safe_code(reason_code)
    metadata = sanitize_diagnostic_metadata(result_metadata or {})
    now = _database_now(db)
    job = _locked_job_by_id(db, job_id)
    if not _owns_current_unexpired_lease(job, lease_token, now):
        return False
    if job.attempt_count >= job.maximum_attempts:
        _transition_to_exhausted(
            db,
            job,
            error_code=reason_code,
            metadata=metadata,
            previous_status=LEASED,
            event_type="released",
            now=now,
        )
        db.flush()
        return True

    job.status = PENDING
    job.available_at = available_at or now
    job.lease_token = None
    job.lease_owner = None
    job.lease_expires_at = None
    job.heartbeat_at = None
    job.last_error_code = reason_code
    job.result_metadata = metadata
    job.updated_at = now
    _append_event(
        db,
        job,
        event_type="released",
        previous_status=LEASED,
        new_status=PENDING,
        error_code=reason_code,
        metadata=metadata,
        occurred_at=now,
    )
    db.flush()
    return True


def operator_cancel_job(
    db: Session,
    *,
    job_id: uuid.UUID,
    reason_code: str,
) -> bool:
    _validate_safe_code(reason_code)
    now = _database_now(db)
    job = _locked_job_by_id(db, job_id)
    if job.status in TERMINAL_STATUSES:
        return False
    previous_status = job.status
    job.status = CANCELLED
    job.lease_token = None
    job.lease_owner = None
    job.lease_expires_at = None
    job.heartbeat_at = None
    job.cancelled_at = now
    job.last_error_code = reason_code
    job.updated_at = now
    _append_event(
        db,
        job,
        event_type="repair_cancelled",
        previous_status=previous_status,
        new_status=CANCELLED,
        error_code=reason_code,
        metadata={},
        occurred_at=now,
    )
    db.flush()
    return True


def requeue_exhausted_job(
    db: Session,
    *,
    job_id: uuid.UUID,
    maximum_attempts: int,
    available_at: datetime | None = None,
    reason_code: str = "operator_requeue",
) -> bool:
    _validate_safe_code(reason_code)
    if maximum_attempts < 1:
        raise ValueError("maximum_attempts must be positive")
    now = _database_now(db)
    job = _locked_job_by_id(db, job_id)
    if job.status != EXHAUSTED:
        return False
    previous_status = job.status
    previous_attempt_count = job.attempt_count
    job.status = PENDING
    job.attempt_count = 0
    job.maximum_attempts = maximum_attempts
    job.available_at = available_at or now
    job.last_error_code = None
    job.exhausted_at = None
    job.updated_at = now
    _append_event(
        db,
        job,
        event_type="repair_requeued",
        previous_status=previous_status,
        new_status=PENDING,
        error_code=reason_code,
        metadata={
            "previous_attempt_count": previous_attempt_count,
            "new_maximum_attempts": maximum_attempts,
        },
        occurred_at=now,
    )
    db.flush()
    return True


def register_worker_heartbeat(
    db: Session,
    *,
    worker_identity: str,
    worker_version: str = DEFAULT_WORKER_VERSION,
    status: str = "running",
    current_job_id: uuid.UUID | None = None,
) -> DurableWorkerHeartbeat:
    if status not in {"starting", "running", "stopping", "stopped"}:
        raise ValueError("invalid worker heartbeat status")
    now = _database_now(db)
    existing = db.get(DurableWorkerHeartbeat, worker_identity)
    stopped_at = now if status == "stopped" else None
    if existing is None:
        heartbeat = DurableWorkerHeartbeat(
            worker_identity=worker_identity,
            worker_version=worker_version,
            status=status,
            current_job_id=current_job_id,
            last_started_at=now,
            last_heartbeat_at=now,
            stopped_at=stopped_at,
            created_at=now,
            updated_at=now,
        )
        db.add(heartbeat)
    else:
        heartbeat = existing
        heartbeat.worker_version = worker_version
        heartbeat.status = status
        heartbeat.current_job_id = current_job_id
        heartbeat.last_heartbeat_at = now
        heartbeat.stopped_at = stopped_at
        heartbeat.updated_at = now
        if status in {"starting", "running"}:
            heartbeat.last_started_at = now
    db.flush()
    return heartbeat


def backlog_summary(
    db: Session,
    *,
    registry: DurableJobRegistry,
    policy: DurableJobQueuePolicy | None = None,
) -> BacklogSummary:
    active_policy = policy or DurableJobQueuePolicy()
    now = _database_now(db)
    supported = set(registry.supported_pairs)
    jobs = db.execute(select(DurableJob)).scalars().all()
    by_status: dict[str, int] = {}
    by_type_version: dict[tuple[str, int], int] = {}
    attempt_counts_by_status: dict[str, dict[int, int]] = {}
    unsupported: set[tuple[str, int]] = set()
    oldest_pending_age_seconds: int | None = None
    expired_leases = 0
    fairness_protected = 0

    for job in jobs:
        by_status[job.status] = by_status.get(job.status, 0) + 1
        status_attempts = attempt_counts_by_status.setdefault(job.status, {})
        status_attempts[job.attempt_count] = status_attempts.get(job.attempt_count, 0) + 1
        key = (job.job_type, job.payload_version)
        by_type_version[key] = by_type_version.get(key, 0) + 1
        if key not in supported and job.status in CLAIMABLE_STATUSES:
            unsupported.add(key)
        if job.status == LEASED and job.lease_expires_at and job.lease_expires_at <= now:
            expired_leases += 1
        if job.status in CLAIMABLE_STATUSES and job.available_at <= now:
            age = int((now - job.available_at).total_seconds())
            if oldest_pending_age_seconds is None or age > oldest_pending_age_seconds:
                oldest_pending_age_seconds = age
            if age >= active_policy.fairness_age.total_seconds():
                fairness_protected += 1

    worker_rows = db.execute(
        select(DurableWorkerHeartbeat).order_by(DurableWorkerHeartbeat.worker_identity.asc())
    ).scalars().all()
    worker_heartbeats = tuple(
        WorkerHeartbeatSummary(
            worker_identity=worker.worker_identity,
            worker_version=worker.worker_version,
            status=worker.status,
            heartbeat_age_seconds=max(
                0,
                int((now - worker.last_heartbeat_at).total_seconds()),
            ),
            has_current_job=worker.current_job_id is not None,
        )
        for worker in worker_rows
    )

    return BacklogSummary(
        by_status=by_status,
        by_type_version=by_type_version,
        unsupported_type_versions=tuple(sorted(unsupported)),
        expired_leases=expired_leases,
        exhausted_jobs=by_status.get(EXHAUSTED, 0),
        retry_waiting_jobs=by_status.get(RETRY_WAITING, 0),
        oldest_pending_age_seconds=oldest_pending_age_seconds,
        fairness_protected_jobs=fairness_protected,
        attempt_counts_by_status={
            status: dict(sorted(counts.items()))
            for status, counts in sorted(attempt_counts_by_status.items())
        },
        worker_heartbeats=worker_heartbeats,
    )


def inspect_job_history(
    db: Session,
    *,
    job_id: uuid.UUID,
    limit: int = 10,
) -> JobInspectionSummary | None:
    if limit < 1 or limit > 50:
        raise ValueError("limit must be between 1 and 50")
    job = db.get(DurableJob, job_id)
    if job is None:
        return None
    events = db.execute(
        select(DurableJobEvent)
        .where(DurableJobEvent.job_id == job_id)
        .order_by(DurableJobEvent.occurred_at.desc(), DurableJobEvent.id.desc())
        .limit(limit)
    ).scalars().all()
    return JobInspectionSummary(
        job_type=job.job_type,
        payload_version=job.payload_version,
        status=job.status,
        attempt_count=job.attempt_count,
        maximum_attempts=job.maximum_attempts,
        last_safe_error_code=job.last_error_code,
        recent_events=tuple(
            JobEventSummary(
                event_type=event.event_type,
                previous_status=event.previous_status,
                new_status=event.new_status,
                attempt_count=event.attempt_count,
                lease_owner=event.lease_owner,
                safe_error_code=event.safe_error_code,
                event_metadata=dict(event.event_metadata or {}),
                occurred_at=event.occurred_at,
            )
            for event in events
        ),
    )


class _ActiveLeaseRenewer:
    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        job_id: uuid.UUID,
        lease_token: uuid.UUID,
        policy: DurableJobQueuePolicy,
    ) -> None:
        self._session_factory = session_factory
        self._job_id = job_id
        self._lease_token = lease_token
        self._policy = policy
        self._stop = Event()
        self._thread = Thread(
            target=self._run,
            name=f"durable-job-lease-renewer-{job_id}",
            daemon=True,
        )
        self.lease_lost = False

    def start(self) -> "_ActiveLeaseRenewer":
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=max(1.0, self._policy.heartbeat_interval.total_seconds() * 2))

    def _run(self) -> None:
        while not self._stop.wait(self._policy.heartbeat_interval.total_seconds()):
            try:
                with self._session_factory() as db:
                    renewed = heartbeat_job(
                        db,
                        job_id=self._job_id,
                        lease_token=self._lease_token,
                        policy=self._policy,
                    )
                    if not renewed:
                        db.rollback()
                        self.lease_lost = True
                        self._stop.set()
                        return
                    db.commit()
            except Exception:
                self.lease_lost = True
                self._stop.set()
                return


class DurableJobRunner:
    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        registry: DurableJobRegistry,
        worker_identity: str,
        worker_version: str = DEFAULT_WORKER_VERSION,
        policy: DurableJobQueuePolicy | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.registry = registry
        self.worker_identity = worker_identity
        self.worker_version = worker_version
        self.policy = policy or DurableJobQueuePolicy()
        self._shutdown_requested = False

    def request_shutdown(self) -> None:
        self._shutdown_requested = True

    def process_once(self) -> str:
        if self._shutdown_requested:
            self.mark_stopped()
            return "shutdown"

        with self.session_factory() as db:
            register_worker_heartbeat(
                db,
                worker_identity=self.worker_identity,
                worker_version=self.worker_version,
                status="running",
            )
            claim = claim_job(
                db,
                registry=self.registry,
                worker_identity=self.worker_identity,
                policy=self.policy,
            )
            claimed_job_id = claim.job.id if claim is not None else None
            claimed_lease_token = claim.lease_token if claim is not None else None
            db.commit()

        if self._shutdown_requested and claim is None:
            self.mark_stopped()
            return "shutdown"

        if claim is None:
            with self.session_factory() as db:
                register_worker_heartbeat(
                    db,
                    worker_identity=self.worker_identity,
                    worker_version=self.worker_version,
                    status="running",
                )
                db.commit()
            return "idle"

        with self.session_factory() as db:
            register_worker_heartbeat(
                db,
                worker_identity=self.worker_identity,
                worker_version=self.worker_version,
                status="running",
                current_job_id=claimed_job_id,
            )
            db.commit()

        try:
            outcome = self._run_handler(claimed_job_id, claimed_lease_token)
        finally:
            with self.session_factory() as db:
                register_worker_heartbeat(
                    db,
                    worker_identity=self.worker_identity,
                    worker_version=self.worker_version,
                    status="stopped" if self._shutdown_requested else "running",
                    current_job_id=None,
                )
                db.commit()

        return outcome

    def mark_stopped(self) -> None:
        with self.session_factory() as db:
            register_worker_heartbeat(
                db,
                worker_identity=self.worker_identity,
                worker_version=self.worker_version,
                status="stopped",
            )
            db.commit()

    def _run_handler(self, job_id: uuid.UUID, lease_token: uuid.UUID) -> str:
        with self.session_factory() as db:
            job = db.get(DurableJob, job_id)
            if job is None:
                return "missing"
            try:
                definition = self.registry.executable_definition_for(
                    job.job_type,
                    job.payload_version,
                )
            except UnsupportedJobDefinitionError:
                db.rollback()
                return "unsupported"
            renewer: _ActiveLeaseRenewer | None = None
            try:
                definition.validate_payload(job.payload)
                renewer = _ActiveLeaseRenewer(
                    session_factory=self.session_factory,
                    job_id=job_id,
                    lease_token=lease_token,
                    policy=self.policy,
                ).start()
                result = definition.handler(db, job)
            except InvalidJobPayloadError:
                exhaust_job(
                    db,
                    job_id=job_id,
                    lease_token=lease_token,
                    error_code="malformed_payload",
                )
                db.commit()
                return "exhausted"
            except Exception:
                if definition.exceptions_are_transient:
                    result = HandlerResult.transient_failure(
                        definition.transient_exception_error_code,
                        retry_delay=definition.transient_retry_delay,
                    )
                else:
                    result = HandlerResult.permanent_failure(
                        definition.permanent_exception_error_code
                    )
            finally:
                if renewer is not None:
                    renewer.stop()

            if renewer is not None and renewer.lease_lost:
                db.rollback()
                return "lease_lost"

            if result.outcome == HandlerOutcome.SUCCESS:
                completed = complete_job(
                    db,
                    job_id=job_id,
                    lease_token=lease_token,
                    result_metadata=result.result_metadata,
                )
                db.commit()
                return "succeeded" if completed else "lease_lost"
            if result.outcome == HandlerOutcome.TRANSIENT_FAILURE:
                retry_delay = result.retry_delay or definition.transient_retry_delay
                retried = retry_job(
                    db,
                    job_id=job_id,
                    lease_token=lease_token,
                    error_code=result.error_code or "transient_failure",
                    retry_delay=retry_delay,
                    result_metadata=result.result_metadata,
                )
                db.commit()
                return "retry_waiting" if retried else "lease_lost"
            exhausted = exhaust_job(
                db,
                job_id=job_id,
                lease_token=lease_token,
                error_code=result.error_code or "permanent_failure",
                result_metadata=result.result_metadata,
            )
            db.commit()
            return "exhausted" if exhausted else "lease_lost"


def sanitize_diagnostic_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(metadata, Mapping):
        raise UnsafeDiagnosticMetadataError("diagnostic metadata must be an object")
    sanitized: dict[str, Any] = {}
    for key, value in metadata.items():
        if not isinstance(key, str) or not _SAFE_KEY_RE.fullmatch(key):
            raise UnsafeDiagnosticMetadataError("diagnostic metadata keys must be safe labels")
        if is_sensitive_key(key):
            raise UnsafeDiagnosticMetadataError("diagnostic metadata key is sensitive")
        if value is None or isinstance(value, bool | int):
            sanitized[key] = value
        elif isinstance(value, str):
            if len(value) > 120 or contains_sensitive_text(value):
                raise UnsafeDiagnosticMetadataError("diagnostic metadata value is unsafe")
            sanitized[key] = value
        else:
            raise UnsafeDiagnosticMetadataError("diagnostic metadata values must be bounded scalars")
    return sanitized


def _job_by_idempotency_key(db: Session, idempotency_key: str) -> DurableJob | None:
    return db.execute(
        select(DurableJob).where(DurableJob.idempotency_key == idempotency_key)
    ).scalars().first()


def _assert_idempotent_match(
    job: DurableJob,
    *,
    job_type: str,
    payload_version: int,
    protected_identity: Mapping[str, Any],
) -> None:
    if (
        job.job_type != job_type
        or job.payload_version != payload_version
        or job.protected_identity != dict(protected_identity)
    ):
        raise ConflictingIdempotencyKeyError("idempotency key conflicts with existing job")


def _database_now(db: Session) -> datetime:
    return db.execute(select(func.clock_timestamp())).scalar_one()


def _generated_safe_correlation_id() -> str:
    return f"job-{uuid.uuid4().hex[:8]}"


def _locked_job_by_id(db: Session, job_id: uuid.UUID) -> DurableJob:
    job = db.execute(
        select(DurableJob)
        .where(DurableJob.id == job_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).scalars().one()
    return job


def _recover_one_expired_lease(
    db: Session,
    *,
    supported_pairs: Sequence[tuple[str, int]],
    worker_identity: str,
    policy: DurableJobQueuePolicy,
    now: datetime,
) -> ClaimResult | None:
    statement = (
        select(DurableJob)
        .where(
            DurableJob.status == LEASED,
            DurableJob.lease_expires_at <= now,
            tuple_(DurableJob.job_type, DurableJob.payload_version).in_(supported_pairs),
        )
        .order_by(DurableJob.lease_expires_at.asc(), DurableJob.created_at.asc(), DurableJob.id.asc())
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    job = db.execute(statement).scalars().first()
    if job is None:
        return None
    if job.attempt_count >= job.maximum_attempts:
        _transition_to_exhausted(
            db,
            job,
            error_code="lease_expired_max_attempts",
            metadata={},
            previous_status=LEASED,
            event_type="lease_expired_exhausted",
            now=now,
        )
        db.flush()
        return None
    return _lease_job(
        db,
        job,
        worker_identity=worker_identity,
        event_type="lease_recovered",
        policy=policy,
        now=now,
    )


def _lease_job(
    db: Session,
    job: DurableJob,
    *,
    worker_identity: str,
    event_type: str,
    policy: DurableJobQueuePolicy,
    now: datetime,
) -> ClaimResult:
    previous_status = job.status
    lease_token = uuid.uuid4()
    job.status = LEASED
    job.lease_token = lease_token
    job.lease_owner = worker_identity
    job.lease_expires_at = now + policy.lease_duration
    job.heartbeat_at = now
    job.attempt_count += 1
    job.updated_at = now
    _append_event(
        db,
        job,
        event_type=event_type,
        previous_status=previous_status,
        new_status=LEASED,
        metadata={},
        occurred_at=now,
    )
    db.flush()
    return ClaimResult(job=job, lease_token=lease_token, database_time=now)


def _transition_to_exhausted(
    db: Session,
    job: DurableJob,
    *,
    error_code: str,
    metadata: Mapping[str, Any],
    previous_status: str,
    event_type: str,
    now: datetime,
) -> None:
    job.status = EXHAUSTED
    job.lease_token = None
    job.lease_owner = None
    job.lease_expires_at = None
    job.heartbeat_at = None
    job.exhausted_at = now
    job.last_error_code = error_code
    job.result_metadata = dict(metadata)
    job.updated_at = now
    _append_event(
        db,
        job,
        event_type=event_type,
        previous_status=previous_status,
        new_status=EXHAUSTED,
        error_code=error_code,
        metadata=metadata,
        occurred_at=now,
    )


def _owns_current_unexpired_lease(
    job: DurableJob,
    lease_token: uuid.UUID,
    now: datetime,
) -> bool:
    return (
        job.status == LEASED
        and job.lease_token == lease_token
        and job.lease_expires_at is not None
        and job.lease_expires_at > now
    )


def _append_event(
    db: Session,
    job: DurableJob,
    *,
    event_type: str,
    previous_status: str | None,
    new_status: str | None,
    metadata: Mapping[str, Any],
    occurred_at: datetime,
    error_code: str | None = None,
) -> DurableJobEvent:
    event = DurableJobEvent(
        job_id=job.id,
        event_type=event_type,
        previous_status=previous_status,
        new_status=new_status,
        attempt_count=job.attempt_count,
        lease_owner=job.lease_owner,
        lease_token=job.lease_token,
        safe_error_code=error_code,
        event_metadata=sanitize_diagnostic_metadata(metadata),
        occurred_at=occurred_at,
        created_at=occurred_at,
    )
    db.add(event)
    return event


def _validate_json_object(name: str, value: Mapping[str, Any]) -> None:
    if not isinstance(value, Mapping):
        raise InvalidJobPayloadError(f"{name} must be a JSON object")
    for key, item in value.items():
        if not isinstance(key, str):
            raise InvalidJobPayloadError(f"{name} keys must be strings")
        if is_sensitive_key(key):
            raise InvalidJobPayloadError(f"{name} key is sensitive")
        _validate_json_value(f"{name}.{key}", item)


def _validate_json_value(name: str, value: Any) -> None:
    if value is None or isinstance(value, bool | int | float):
        return
    if isinstance(value, str):
        if len(value) > 500 or contains_sensitive_text(value):
            raise InvalidJobPayloadError(f"{name} contains unsafe text")
        return
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        if len(value) > 50:
            raise InvalidJobPayloadError(f"{name} contains too many items")
        for index, item in enumerate(value):
            _validate_json_value(f"{name}[{index}]", item)
        return
    if isinstance(value, Mapping):
        _validate_json_object(name, value)
        return
    raise InvalidJobPayloadError(f"{name} must be JSON-serializable")


def _validate_safe_correlation_id(value: str | None) -> None:
    if value is None:
        return
    if len(value) > 120 or contains_sensitive_text(value):
        raise UnsafeDiagnosticMetadataError("correlation_id is unsafe")


def _validate_safe_code(value: str) -> None:
    if not _SAFE_CODE_RE.fullmatch(value):
        raise UnsafeDiagnosticMetadataError("error/reason code must be a safe label")
