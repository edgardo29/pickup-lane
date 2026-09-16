"""Bounded process-local metrics with explicit, provider-neutral collection."""

from __future__ import annotations

import math
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from threading import Lock
from types import MappingProxyType
from typing import Protocol

from backend.observability.structured_logging import RuntimeEventEmitter
from backend.observability.telemetry import (
    validate_low_cardinality_token,
    validate_telemetry_labels,
)

PRODUCTION_JOB_TYPES = (
    "stripe_webhook_event",
    "stripe_payment_intent_reconcile",
    "stripe_payment_method_operation_reconcile",
)
JOB_TYPES = (*PRODUCTION_JOB_TYPES, "unsupported")
BACKLOG_STATES = ("pending", "retry_waiting", "leased", "exhausted")
MONEY_ISSUE_TYPES = (
    "refund_missing_provider_reference",
    "refund_processing_overdue",
    "refund_failed",
    "refund_cancelled",
    "refund_outcome_unknown",
    "credit_restore_failed",
    "credit_release_failed",
)
MODERATION_CONTEXTS = ("community_game", "need_a_sub", "game_chat", "need_a_sub_chat")
HTTP_OPERATIONS = tuple(
    f"http.{method}"
    for method in (
        "get",
        "post",
        "put",
        "patch",
        "delete",
        "head",
        "options",
        "other",
    )
)
READ_RESULTS = frozenset(
    {
        "succeeded",
        "timed_out",
        "rate_limited",
        "failed",
        "configuration_error",
    }
)
MUTATION_RESULTS = (READ_RESULTS - {"timed_out"}) | {"unknown_outcome"}
PROVIDER_RESULTS = MappingProxyType(
    {
        **{
            f"stripe.{operation}": MUTATION_RESULTS
            for operation in (
                "customer.create",
                "setup_intent.create",
                "payment_method.detach",
                "customer.default_payment_method.set",
                "customer.default_payment_method.clear",
                "refund.create",
            )
        },
        **{
            f"stripe.{operation}": READ_RESULTS
            for operation in (
                "setup_intent.retrieve",
                "payment_method.retrieve",
                "payment_intent.retrieve",
                "refund.retrieve",
            )
        },
        "stripe.payment_intent.create": MUTATION_RESULTS | {"rejected"},
        "stripe.payment_intent.confirm": MUTATION_RESULTS | {"rejected"},
        "firebase.token.verify": READ_RESULTS | {"rejected"},
        "firebase.user.lookup": READ_RESULTS | {"rejected", "not_found"},
        "firebase.app_check.verify": READ_RESULTS | {"rejected"},
        "firebase.user.delete": MUTATION_RESULTS,
        "r2.upload_url.create": READ_RESULTS,
        "r2.read_url.create": READ_RESULTS,
        "r2.metadata.head": READ_RESULTS | {"not_found"},
        "r2.upload.validate": frozenset({"configuration_error"}),
        "r2.readiness.check": frozenset({"configuration_error"}),
    }
)


@dataclass(frozen=True)
class MetricDescriptor:
    name: str
    kind: str
    unit: str
    dimensions: tuple[tuple[str, frozenset[str] | None], ...] = ()
    integer: bool = False


def _dimensions(**values: tuple[str, ...]) -> tuple[tuple[str, frozenset[str]], ...]:
    return tuple(
        sorted((name, frozenset(vocabulary)) for name, vocabulary in values.items())
    )


_HTTP_DIMENSIONS = (
    *_dimensions(
        operation=HTTP_OPERATIONS,
        result=(
            "success",
            "client_error",
            "server_error",
        ),
    ),
    ("route_template", None),
)
DESCRIPTORS = (
    MetricDescriptor(
        "api.request.total", "counter", "requests", _HTTP_DIMENSIONS, True
    ),
    MetricDescriptor(
        "api.request.duration_seconds", "distribution", "seconds", _HTTP_DIMENSIONS
    ),
    MetricDescriptor("api.request.in_flight", "gauge", "requests", integer=True),
    MetricDescriptor("database.pool.checked_out", "gauge", "connections", integer=True),
    MetricDescriptor("database.pool.capacity", "gauge", "connections", integer=True),
    MetricDescriptor(
        "database.timeout.total",
        "counter",
        "timeouts",
        _dimensions(
            operation=("database.pool_wait", "database.statement", "database.lock"),
            result=("timed_out",),
        ),
        True,
    ),
    MetricDescriptor(
        "worker.job.outcome.total",
        "counter",
        "jobs",
        _dimensions(
            job_type=JOB_TYPES,
            result=(
                "succeeded",
                "retry_waiting",
                "exhausted",
                "lease_lost",
                "missing",
                "unsupported",
            ),
        ),
        True,
    ),
    MetricDescriptor(
        "worker.backlog.count",
        "gauge",
        "jobs",
        _dimensions(
            job_type=JOB_TYPES,
            result=BACKLOG_STATES,
        ),
        True,
    ),
    MetricDescriptor(
        "worker.backlog.oldest_age_seconds",
        "gauge",
        "seconds",
        _dimensions(job_type=JOB_TYPES),
    ),
    MetricDescriptor(
        "payment.reconciliation.outcome.total",
        "counter",
        "operations",
        _dimensions(
            job_type=PRODUCTION_JOB_TYPES[1:],
            result=("succeeded", "failed", "pending", "already_terminal"),
        ),
        True,
    ),
    MetricDescriptor(
        "financial.discrepancy.open",
        "gauge",
        "issues",
        _dimensions(
            operation=tuple(f"money_issue.{kind}" for kind in MONEY_ISSUE_TYPES),
            result=("open",),
        ),
        True,
    ),
    MetricDescriptor(
        "provider.operation.outcome.total",
        "counter",
        "operations",
        _dimensions(
            provider_kind=("stripe", "firebase", "r2"),
            operation=tuple(PROVIDER_RESULTS),
            result=tuple(sorted(set().union(*PROVIDER_RESULTS.values()))),
        ),
        True,
    ),
    MetricDescriptor(
        "moderation.scan.duration_seconds",
        "distribution",
        "seconds",
        _dimensions(
            operation=tuple(
                f"moderation.scan.{context}" for context in MODERATION_CONTEXTS
            ),
        ),
    ),
)
FAMILY_METRICS = MappingProxyType(
    {
        "database_pool": frozenset(
            {"database.pool.checked_out", "database.pool.capacity"}
        ),
        "durable_backlog": frozenset(
            {"worker.backlog.count", "worker.backlog.oldest_age_seconds"}
        ),
        "financial_discrepancy": frozenset({"financial.discrepancy.open"}),
    }
)
_OBSERVABLE_NAMES = frozenset().union(*FAMILY_METRICS.values())


@dataclass(frozen=True)
class RecorderIdentity:
    source_identity: str
    environment: str
    release: str


@dataclass(frozen=True)
class MetricObservation:
    descriptor: MetricDescriptor
    value: int | float
    dimensions: tuple[tuple[str, str], ...]
    identity: RecorderIdentity
    event_sequence: int = 0


@dataclass(frozen=True)
class ObservableBatch:
    identity: RecorderIdentity
    family: str
    collection_sequence: int
    observations: tuple[MetricObservation, ...]
    unavailable: bool = False


@dataclass(frozen=True)
class Distribution:
    count: int
    sum: int | float
    min: int | float
    max: int | float


@dataclass(frozen=True)
class MetricSeries:
    name: str
    dimensions: tuple[tuple[str, str], ...]
    value: int | float | Distribution


@dataclass(frozen=True)
class MetricSnapshot:
    identity: RecorderIdentity
    series: tuple[MetricSeries, ...]
    unavailable_families: tuple[str, ...]


class MetricSink(Protocol):
    """One binding per recorder lifetime; delivery is best-effort, without retries."""

    def record(self, observation: MetricObservation) -> None: ...

    def replace_family(self, batch: ObservableBatch) -> None: ...


def _aggregate(previous: float | Distribution | None, observation: MetricObservation):
    value = observation.value
    if observation.descriptor.kind == "counter":
        return (previous or 0) + value
    if observation.descriptor.kind == "gauge":
        return value
    if isinstance(previous, Distribution):
        return Distribution(
            previous.count + 1,
            previous.sum + value,
            min(previous.min, value),
            max(previous.max, value),
        )
    return Distribution(1, value, value, value)


class InMemoryMetricSink:
    """Thread-safe local adapter demonstrating event ordering and family replacement."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._events = {}
        self._gauge_sequences = {}
        self._families: dict[str, ObservableBatch] = {}

    def record(self, observation: MetricObservation) -> None:
        key = (observation.descriptor.name, observation.dimensions)
        with self._lock:
            if observation.descriptor.kind == "gauge":
                if observation.event_sequence <= self._gauge_sequences.get(key, -1):
                    return
                self._gauge_sequences[key] = observation.event_sequence
            self._events[key] = _aggregate(self._events.get(key), observation)

    def replace_family(self, batch: ObservableBatch) -> None:
        with self._lock:
            previous = self._families.get(batch.family)
            if (
                previous is None
                or batch.collection_sequence > previous.collection_sequence
            ):
                self._families[batch.family] = batch

    def snapshot(self, identity: RecorderIdentity) -> MetricSnapshot:
        with self._lock:
            return _snapshot(identity, self._events, self._families)


def _snapshot(identity, events, families) -> MetricSnapshot:
    series = [
        MetricSeries(name, dimensions, value)
        for (name, dimensions), value in events.items()
    ]
    for batch in families.values():
        series.extend(
            MetricSeries(item.descriptor.name, item.dimensions, item.value)
            for item in batch.observations
        )
    return MetricSnapshot(
        identity,
        tuple(sorted(series, key=lambda item: (item.name, item.dimensions))),
        tuple(sorted(name for name, batch in families.items() if batch.unavailable)),
    )


ObservableCallback = Callable[[], list[tuple[str, int | float, Mapping[str, str]]]]


class MetricsRecorder:
    """Canonical bounded aggregates; runtime rejection never enters product control flow."""

    def __init__(
        self,
        source_identity: str,
        environment: str,
        release: str,
        *,
        sink: MetricSink | None = None,
        descriptors=DESCRIPTORS,
    ) -> None:
        RuntimeEventEmitter(source_identity, environment, release)
        self._identity = RecorderIdentity(source_identity, environment, release)
        self._descriptors: dict[str, MetricDescriptor] = {}
        for descriptor in descriptors:
            if (
                not isinstance(descriptor, MetricDescriptor)
                or not isinstance(descriptor.dimensions, tuple)
                or not isinstance(descriptor.integer, bool)
                or any(
                    not isinstance(item, tuple)
                    or len(item) != 2
                    or (item[1] is not None and not isinstance(item[1], frozenset))
                    for item in descriptor.dimensions
                )
            ):
                raise ValueError("Metric definitions must be immutable.")
            validate_low_cardinality_token(descriptor.name)
            if descriptor.name in self._descriptors or descriptor.kind not in {
                "counter",
                "gauge",
                "distribution",
            }:
                raise ValueError("Invalid static metric definition.")
            validate_low_cardinality_token(descriptor.unit)
            dimension_names = [name for name, _ in descriptor.dimensions]
            if len(set(dimension_names)) != len(dimension_names):
                raise ValueError("Duplicate static metric dimension.")
            for name, vocabulary in descriptor.dimensions:
                if vocabulary is None:
                    if name != "route_template":
                        raise ValueError("Unbounded static metric dimension.")
                    validate_telemetry_labels({name: "/{unmatched}"})
                elif not vocabulary:
                    raise ValueError("Empty static metric vocabulary.")
                else:
                    for value in vocabulary:
                        validate_telemetry_labels({name: value})
            if descriptor.kind == "counter" and not descriptor.integer:
                raise ValueError("Counters require integer increments.")
            self._descriptors[descriptor.name] = descriptor
        self._sink = sink
        self._lock = Lock()
        self._collection_lock = Lock()
        self._event_sequence = 0
        self._collection_sequence = 0
        self._events = {}
        self._families: dict[str, ObservableBatch] = {}
        self._callbacks: dict[str, ObservableCallback] = {}
        self._in_flight = 0

    @property
    def identity(self) -> RecorderIdentity:
        return self._identity

    def _validate(self, name, value, dimensions) -> MetricObservation:
        descriptor = self._descriptors[name]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            raise ValueError("Invalid metric number.")
        if not math.isfinite(value) or (
            descriptor.integer and not isinstance(value, int)
        ):
            raise ValueError("Invalid metric numeric domain.")
        labels = validate_telemetry_labels(dimensions)
        if set(labels) != {key for key, _ in descriptor.dimensions}:
            raise ValueError("Invalid metric dimensions.")
        for key, vocabulary in descriptor.dimensions:
            if vocabulary is not None and labels[key] not in vocabulary:
                raise ValueError("Invalid metric vocabulary.")
        if name == "provider.operation.outcome.total":
            operation = labels["operation"]
            if (
                not operation.startswith(labels["provider_kind"] + ".")
                or labels["result"] not in PROVIDER_RESULTS[operation]
            ):
                raise ValueError("Invalid provider operation/result pair.")
        return MetricObservation(
            descriptor, value, tuple(sorted(labels.items())), self.identity
        )

    def _mutate(self, observation: MetricObservation) -> MetricObservation:
        key = (observation.descriptor.name, observation.dimensions)
        updated = _aggregate(self._events.get(key), observation)
        if (
            isinstance(updated, float)
            and not math.isfinite(updated)
            or isinstance(updated, Distribution)
            and isinstance(updated.sum, float)
            and not math.isfinite(updated.sum)
        ):
            raise ValueError("Metric aggregate must remain finite.")
        self._event_sequence += 1
        observation = MetricObservation(
            observation.descriptor,
            observation.value,
            observation.dimensions,
            self.identity,
            self._event_sequence,
        )
        self._events[key] = updated
        return observation

    def _deliver(self, observation: MetricObservation) -> None:
        try:
            if self._sink is not None:
                self._sink.record(observation)
        except Exception:  # noqa: BLE001, S110 - best-effort sink cannot undo canonical acceptance.
            pass

    def record(self, name, value, dimensions: Mapping[str, str] | None = None) -> bool:
        try:
            if name in _OBSERVABLE_NAMES or name == "api.request.in_flight":
                return False
            with self._lock:
                observation = self._mutate(self._validate(name, value, dimensions))
            self._deliver(observation)
            return True
        except Exception:  # noqa: BLE001 - reject unsafe runtime data without disclosure.
            return False

    def _change_in_flight(self, delta: int) -> bool:
        try:
            with self._lock:
                value = self._in_flight + delta
                observation = self._validate("api.request.in_flight", value, {})
                observation = self._mutate(observation)
                self._in_flight = value
            self._deliver(observation)
            return True
        except Exception:  # noqa: BLE001 - lifecycle rejection cannot raise.
            return False

    def enter_request(self) -> bool:
        return self._change_in_flight(1)

    def exit_request(self) -> bool:
        return self._change_in_flight(-1)

    def register_observable(self, family: str, callback: ObservableCallback) -> None:
        if (
            family not in FAMILY_METRICS
            or family in self._callbacks
            or not callable(callback)
        ):
            raise ValueError("Invalid observable family registration.")
        self._callbacks[family] = callback

    def collect(self) -> MetricSnapshot:
        with self._collection_lock, metrics_context(self):
            self._collection_sequence += 1
            for family, callback in self._callbacks.items():
                try:
                    observations = tuple(self._validate(*item) for item in callback())
                    keys = {
                        (item.descriptor.name, item.dimensions) for item in observations
                    }
                    if len(keys) != len(observations) or any(
                        item.descriptor.name not in FAMILY_METRICS[family]
                        for item in observations
                    ):
                        raise ValueError("Invalid observable family batch.")
                    batch = ObservableBatch(
                        self.identity, family, self._collection_sequence, observations
                    )
                except Exception:  # noqa: BLE001 - unavailable replaces stale, never hides failure as zero.
                    batch = ObservableBatch(
                        self.identity, family, self._collection_sequence, (), True
                    )
                with self._lock:
                    self._families[family] = batch
                try:
                    if self._sink is not None:
                        self._sink.replace_family(batch)
                except Exception:  # noqa: BLE001, S110 - delivery does not undo local replacement.
                    pass
            return self.snapshot()

    def snapshot(self) -> MetricSnapshot:
        with self._lock:
            return _snapshot(self.identity, self._events, self._families)


_active_recorder: ContextVar[MetricsRecorder | None] = ContextVar(
    "pickup_lane_metrics", default=None
)


@contextmanager
def metrics_context(recorder: MetricsRecorder | None) -> Iterator[None]:
    token = _active_recorder.set(recorder)
    try:
        yield
    finally:
        _active_recorder.reset(token)


def current_metrics() -> MetricsRecorder | None:
    return _active_recorder.get()


def record_metric(name: str, value: float, dimensions: Mapping[str, str]) -> bool:
    try:
        recorder = current_metrics()
        return (
            recorder.record(name, value, dimensions) if recorder is not None else False
        )
    except Exception:  # noqa: BLE001 - instrumentation cannot mask product behavior.
        return False


def record_provider_outcome(operation: str, result: str) -> bool:
    return record_metric(
        "provider.operation.outcome.total",
        1,
        {
            "provider_kind": operation.split(".", 1)[0],
            "operation": operation,
            "result": result,
        },
    )


@dataclass
class ReconciliationAttempt:
    staged: tuple[str, str] | None = None


_reconciliation_attempt: ContextVar[ReconciliationAttempt | None] = ContextVar(
    "pickup_lane_reconciliation_metric", default=None
)


@contextmanager
def reconciliation_attempt() -> Iterator[ReconciliationAttempt]:
    attempt = ReconciliationAttempt()
    token = _reconciliation_attempt.set(attempt)
    try:
        yield attempt
    finally:
        _reconciliation_attempt.reset(token)


def stage_reconciliation_outcome(job_type: str, result: str) -> None:
    attempt = _reconciliation_attempt.get()
    if (
        attempt is not None
        and attempt.staged is None
        and job_type in PRODUCTION_JOB_TYPES[1:]
        and result in {"succeeded", "failed", "pending", "already_terminal"}
    ):
        attempt.staged = (job_type, result)


def emit_staged_reconciliation() -> None:
    attempt = _reconciliation_attempt.get()
    if attempt is not None and attempt.staged is not None:
        job_type, result = attempt.staged
        attempt.staged = None
        record_metric(
            "payment.reconciliation.outcome.total",
            1,
            {"job_type": job_type, "result": result},
        )
