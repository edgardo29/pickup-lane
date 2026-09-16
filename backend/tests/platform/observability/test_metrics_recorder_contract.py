"""Canonical metrics, privacy, ordering, and explicit collection lifecycle."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Event

import pytest

from backend.observability.metrics import (
    DESCRIPTORS,
    PROVIDER_RESULTS,
    Distribution,
    InMemoryMetricSink,
    MetricDescriptor,
    MetricsRecorder,
    current_metrics,
    metrics_context,
    record_metric,
)

pytestmark = pytest.mark.no_db_cleanup


def _value(snapshot, name):
    return next(item.value for item in snapshot.series if item.name == name)


def test_complete_fixed_inventory_and_numeric_kinds():
    recorder = MetricsRecorder("api", "test", "test-release")
    expected = {
        "api.request.total": (
            "counter",
            "requests",
            True,
            {
                "operation": {
                    "http.get",
                    "http.post",
                    "http.put",
                    "http.patch",
                    "http.delete",
                    "http.head",
                    "http.options",
                    "http.other",
                },
                "route_template": None,
                "result": {"success", "client_error", "server_error"},
            },
        ),
        "api.request.duration_seconds": (
            "distribution",
            "seconds",
            False,
            {
                "operation": {
                    "http.get",
                    "http.post",
                    "http.put",
                    "http.patch",
                    "http.delete",
                    "http.head",
                    "http.options",
                    "http.other",
                },
                "route_template": None,
                "result": {"success", "client_error", "server_error"},
            },
        ),
        "api.request.in_flight": ("gauge", "requests", True, {}),
        "database.pool.checked_out": ("gauge", "connections", True, {}),
        "database.pool.capacity": ("gauge", "connections", True, {}),
        "database.timeout.total": (
            "counter",
            "timeouts",
            True,
            {
                "operation": {
                    "database.pool_wait",
                    "database.statement",
                    "database.lock",
                },
                "result": {"timed_out"},
            },
        ),
        "worker.job.outcome.total": (
            "counter",
            "jobs",
            True,
            {
                "job_type": {
                    "stripe_webhook_event",
                    "stripe_payment_intent_reconcile",
                    "stripe_payment_method_operation_reconcile",
                    "unsupported",
                },
                "result": {
                    "succeeded",
                    "retry_waiting",
                    "exhausted",
                    "lease_lost",
                    "missing",
                    "unsupported",
                },
            },
        ),
        "worker.backlog.count": (
            "gauge",
            "jobs",
            True,
            {
                "job_type": {
                    "stripe_webhook_event",
                    "stripe_payment_intent_reconcile",
                    "stripe_payment_method_operation_reconcile",
                    "unsupported",
                },
                "result": {"pending", "retry_waiting", "leased", "exhausted"},
            },
        ),
        "worker.backlog.oldest_age_seconds": (
            "gauge",
            "seconds",
            False,
            {
                "job_type": {
                    "stripe_webhook_event",
                    "stripe_payment_intent_reconcile",
                    "stripe_payment_method_operation_reconcile",
                    "unsupported",
                }
            },
        ),
        "payment.reconciliation.outcome.total": (
            "counter",
            "operations",
            True,
            {
                "job_type": {
                    "stripe_payment_intent_reconcile",
                    "stripe_payment_method_operation_reconcile",
                },
                "result": {"succeeded", "failed", "pending", "already_terminal"},
            },
        ),
        "financial.discrepancy.open": (
            "gauge",
            "issues",
            True,
            {
                "operation": {
                    "money_issue.refund_missing_provider_reference",
                    "money_issue.refund_processing_overdue",
                    "money_issue.refund_failed",
                    "money_issue.refund_cancelled",
                    "money_issue.refund_outcome_unknown",
                    "money_issue.credit_restore_failed",
                    "money_issue.credit_release_failed",
                },
                "result": {"open"},
            },
        ),
        "provider.operation.outcome.total": (
            "counter",
            "operations",
            True,
            {
                "provider_kind": {"stripe", "firebase", "r2"},
                "operation": {
                    "stripe.customer.create",
                    "stripe.setup_intent.create",
                    "stripe.setup_intent.retrieve",
                    "stripe.payment_method.retrieve",
                    "stripe.payment_method.detach",
                    "stripe.customer.default_payment_method.set",
                    "stripe.customer.default_payment_method.clear",
                    "stripe.payment_intent.create",
                    "stripe.payment_intent.confirm",
                    "stripe.payment_intent.retrieve",
                    "stripe.refund.create",
                    "stripe.refund.retrieve",
                    "firebase.token.verify",
                    "firebase.user.lookup",
                    "firebase.app_check.verify",
                    "firebase.user.delete",
                    "r2.upload_url.create",
                    "r2.read_url.create",
                    "r2.metadata.head",
                    "r2.upload.validate",
                    "r2.readiness.check",
                },
                "result": {
                    "succeeded",
                    "timed_out",
                    "unknown_outcome",
                    "rate_limited",
                    "not_found",
                    "configuration_error",
                    "rejected",
                    "failed",
                },
            },
        ),
        "moderation.scan.duration_seconds": (
            "distribution",
            "seconds",
            False,
            {
                "operation": {
                    "moderation.scan.community_game",
                    "moderation.scan.need_a_sub",
                    "moderation.scan.game_chat",
                    "moderation.scan.need_a_sub_chat",
                }
            },
        ),
    }
    actual = {
        descriptor.name: (
            descriptor.kind,
            descriptor.unit,
            descriptor.integer,
            {
                name: None if vocabulary is None else set(vocabulary)
                for name, vocabulary in descriptor.dimensions
            },
        )
        for descriptor in DESCRIPTORS
    }
    assert actual == expected
    assert recorder.identity.source_identity == "api"
    assert recorder.identity.environment == "test"
    assert recorder.identity.release == "test-release"
    read_results = {
        "succeeded",
        "timed_out",
        "rate_limited",
        "failed",
        "configuration_error",
    }
    mutation_results = {
        "succeeded",
        "unknown_outcome",
        "rate_limited",
        "failed",
        "configuration_error",
    }
    expected_provider_results = {
        "stripe.customer.create": mutation_results,
        "stripe.setup_intent.create": mutation_results,
        "stripe.setup_intent.retrieve": read_results,
        "stripe.payment_method.retrieve": read_results,
        "stripe.payment_method.detach": mutation_results,
        "stripe.customer.default_payment_method.set": mutation_results,
        "stripe.customer.default_payment_method.clear": mutation_results,
        "stripe.payment_intent.create": mutation_results | {"rejected"},
        "stripe.payment_intent.confirm": mutation_results | {"rejected"},
        "stripe.payment_intent.retrieve": read_results,
        "stripe.refund.create": mutation_results,
        "stripe.refund.retrieve": read_results,
        "firebase.token.verify": read_results | {"rejected"},
        "firebase.user.lookup": read_results | {"rejected", "not_found"},
        "firebase.app_check.verify": read_results | {"rejected"},
        "firebase.user.delete": mutation_results,
        "r2.upload_url.create": read_results,
        "r2.read_url.create": read_results,
        "r2.metadata.head": read_results | {"not_found"},
        "r2.upload.validate": {"configuration_error"},
        "r2.readiness.check": {"configuration_error"},
    }
    assert {
        operation: set(results) for operation, results in PROVIDER_RESULTS.items()
    } == expected_provider_results
    assert recorder.record(
        "database.timeout.total",
        1,
        {"operation": "database.lock", "result": "timed_out"},
    )
    assert recorder.record(
        "moderation.scan.duration_seconds",
        0.5,
        {"operation": "moderation.scan.game_chat"},
    )
    assert recorder.record(
        "moderation.scan.duration_seconds",
        1.5,
        {"operation": "moderation.scan.game_chat"},
    )
    assert _value(
        recorder.snapshot(), "moderation.scan.duration_seconds"
    ) == Distribution(2, 2, 0.5, 1.5)


def test_finite_inputs_cannot_overflow_distribution_aggregate():
    recorder = MetricsRecorder("api", "test", "test-release")
    labels = {"operation": "moderation.scan.game_chat"}
    assert recorder.record("moderation.scan.duration_seconds", 1e308, labels)
    assert not recorder.record("moderation.scan.duration_seconds", 1e308, labels)
    assert _value(
        recorder.snapshot(), "moderation.scan.duration_seconds"
    ) == Distribution(1, 1e308, 1e308, 1e308)


def test_identity_and_static_vocabularies_are_immutable():
    recorder = MetricsRecorder("api", "test", "test-release")
    with pytest.raises(AttributeError):
        recorder.identity = recorder.identity
    with pytest.raises(ValueError, match="immutable"):
        MetricsRecorder(
            "api",
            "test",
            "test-release",
            descriptors=(
                replace(DESCRIPTORS[0], dimensions=(("operation", {"http.get"}),)),
            ),
        )


def test_reordered_additive_delivery_and_fresh_sink_binding():
    class ReorderedSink(InMemoryMetricSink):
        def __init__(self):
            super().__init__()
            self.held = []

        def record(self, observation):
            self.held.append(observation)

    sink = ReorderedSink()
    recorder = MetricsRecorder("api", "test", "test-release", sink=sink)
    for value in (0.25, 0.5, 0.75):
        assert recorder.record(
            "moderation.scan.duration_seconds",
            value,
            {"operation": "moderation.scan.game_chat"},
        )
        assert recorder.record(
            "database.timeout.total",
            1,
            {"operation": "database.lock", "result": "timed_out"},
        )
    for observation in reversed(sink.held):
        InMemoryMetricSink.record(sink, observation)
    assert sink.snapshot(recorder.identity) == recorder.snapshot()
    assert recorder.enter_request()
    fresh_sink = InMemoryMetricSink()
    fresh = MetricsRecorder("api", "test", "test-release", sink=fresh_sink)
    assert fresh.enter_request() and fresh.exit_request()
    assert _value(fresh_sink.snapshot(fresh.identity), "api.request.in_flight") == 0


def test_collection_cycles_are_serialized_without_blocking_events():
    entered = Event()
    release = Event()
    calls = []
    recorder = MetricsRecorder("api", "test", "test-release")

    def callback():
        calls.append(len(calls) + 1)
        if len(calls) == 1:
            entered.set()
            assert release.wait(5)
        # Snapshot and event mutation from a callback must not deadlock.
        recorder.snapshot()
        assert recorder.enter_request() and recorder.exit_request()
        return [("database.pool.checked_out", len(calls), {})]

    recorder.register_observable("database_pool", callback)
    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(recorder.collect)
        assert entered.wait(5)
        second = executor.submit(recorder.collect)
        assert recorder.record(
            "database.timeout.total",
            1,
            {"operation": "database.lock", "result": "timed_out"},
        )
        assert calls == [1]
        release.set()
        first.result(timeout=5)
        second.result(timeout=5)
    assert calls == [1, 2]
    assert _value(recorder.snapshot(), "database.pool.checked_out") == 2


@pytest.mark.parametrize(
    "value", [float("nan"), float("inf"), -1, True, False, "1", None, {}, 1.5]
)
def test_invalid_counter_values_do_not_mutate(value):
    recorder = MetricsRecorder("api", "test", "test-release")
    assert not recorder.record(
        "database.timeout.total",
        value,
        {"operation": "database.lock", "result": "timed_out"},
    )
    assert recorder.snapshot().series == ()


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1, True, False])
def test_invalid_distribution_values_do_not_mutate(value):
    recorder = MetricsRecorder("api", "test", "test-release")
    assert not recorder.record(
        "moderation.scan.duration_seconds",
        value,
        {"operation": "moderation.scan.game_chat"},
    )
    assert recorder.snapshot().series == ()


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1, True, 1.5])
def test_invalid_observable_gauge_values_make_the_family_unavailable(value):
    recorder = MetricsRecorder("api", "test", "test-release")
    recorder.register_observable(
        "database_pool",
        lambda: [("database.pool.checked_out", value, {})],
    )

    snapshot = recorder.collect()

    assert snapshot.series == ()
    assert snapshot.unavailable_families == ("database_pool",)


@pytest.mark.parametrize(
    "dimensions",
    [
        {
            "operation": "database.lock",
            "result": "timed_out",
            "correlation_id": "private",
        },
        {"operation": "database.private", "result": "timed_out"},
        {"operation": "https://private.invalid", "result": "timed_out"},
        {"operation": "user@example.invalid", "result": "timed_out"},
        {"operation": "pi_private", "result": "timed_out"},
        {"operation": "database.lock", "result": "private free text"},
        {"operation": "database.lock"},
    ],
)
def test_unsafe_or_undeclared_dimensions_are_rejected(dimensions):
    recorder = MetricsRecorder("api", "test", "test-release")
    assert not recorder.record("database.timeout.total", 1, dimensions)
    assert not recorder.record("private.metric", 1, {})
    assert recorder.snapshot().series == ()


def test_cross_provider_result_vocabulary_is_enforced():
    recorder = MetricsRecorder("api", "test", "test-release")
    for provider, operation, result in [
        ("firebase", "stripe.customer.create", "succeeded"),
        ("stripe", "stripe.customer.create", "timed_out"),
        ("r2", "r2.upload.validate", "succeeded"),
        ("stripe", "stripe.refund.retrieve", "rejected"),
    ]:
        assert not recorder.record(
            "provider.operation.outcome.total",
            1,
            {
                "provider_kind": provider,
                "operation": operation,
                "result": result,
            },
        )
    assert recorder.snapshot().series == ()


def test_static_definition_and_process_identity_fail_strictly():
    with pytest.raises(ValueError):
        MetricsRecorder("invalid", "test", "test-release")
    with pytest.raises(ValueError):
        MetricsRecorder(
            "api", "test", "test-release", descriptors=(DESCRIPTORS[0], DESCRIPTORS[0])
        )
    for descriptor in [
        MetricDescriptor("test.metric", "invalid", "requests"),
        MetricDescriptor("test.metric", "counter", "requests"),
        replace(DESCRIPTORS[0], dimensions=(("user_id", frozenset({"private"})),)),
        replace(DESCRIPTORS[0], dimensions=(("operation", None),)),
    ]:
        with pytest.raises(ValueError):
            MetricsRecorder("api", "test", "test-release", descriptors=(descriptor,))


def test_concurrent_additive_observations_and_sink_match_without_raw_history():
    sink = InMemoryMetricSink()
    recorder = MetricsRecorder("worker", "test", "test-release", sink=sink)

    def observe(_):
        assert recorder.record(
            "database.timeout.total",
            1,
            {"operation": "database.lock", "result": "timed_out"},
        )
        assert recorder.record(
            "moderation.scan.duration_seconds",
            0.5,
            {"operation": "moderation.scan.game_chat"},
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(observe, range(200)))
    assert _value(recorder.snapshot(), "database.timeout.total") == 200
    assert _value(
        recorder.snapshot(), "moderation.scan.duration_seconds"
    ) == Distribution(200, 100, 0.5, 0.5)
    assert recorder.snapshot() == sink.snapshot(recorder.identity)


def test_out_of_order_exit_delivery_cannot_restore_stale_gauge():
    blocked = Event()
    release = Event()

    class ReorderedSink(InMemoryMetricSink):
        def record(self, observation):
            if observation.event_sequence == 3:
                blocked.set()
                assert release.wait(5)
            super().record(observation)

    sink = ReorderedSink()
    recorder = MetricsRecorder("api", "test", "test-release", sink=sink)
    assert recorder.enter_request()
    assert recorder.enter_request()
    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(recorder.exit_request)
        assert blocked.wait(5)
        second = executor.submit(recorder.exit_request)
        assert second.result(timeout=5)
        release.set()
        assert first.result(timeout=5)
    assert _value(recorder.snapshot(), "api.request.in_flight") == 0
    assert _value(sink.snapshot(recorder.identity), "api.request.in_flight") == 0


def test_sink_failure_does_not_change_acceptance_or_balance():
    class FailingSink:
        def record(self, observation):
            raise RuntimeError("private-sink-canary")

        def replace_family(self, batch):
            raise RuntimeError("private-sink-canary")

    recorder = MetricsRecorder("api", "test", "test-release", sink=FailingSink())
    assert recorder.enter_request()
    assert recorder.exit_request()
    assert _value(recorder.snapshot(), "api.request.in_flight") == 0
    assert not recorder.exit_request()
    assert not recorder.record("api.request.in_flight", 5, {})


@pytest.mark.parametrize("failure", ["exception", "duplicate", "invalid"])
def test_collection_replaces_zero_absent_and_unavailable_without_stale_values(failure):
    sink = InMemoryMetricSink()
    recorder = MetricsRecorder("api", "test", "test-release", sink=sink)
    rows = [
        ("worker.backlog.count", 1, {"job_type": "unsupported", "result": "pending"}),
        ("worker.backlog.oldest_age_seconds", 2, {"job_type": "unsupported"}),
    ]

    def collect():
        if rows is None:
            raise RuntimeError("private-query-canary")
        return rows

    recorder.register_observable("durable_backlog", collect)
    recorder.register_observable(
        "financial_discrepancy",
        lambda: [
            (
                "financial.discrepancy.open",
                0,
                {"operation": "money_issue.refund_failed", "result": "open"},
            ),
        ],
    )
    assert _value(recorder.collect(), "worker.backlog.oldest_age_seconds") == 2
    rows = [
        ("worker.backlog.count", 0, {"job_type": "unsupported", "result": "pending"})
    ]
    snapshot = recorder.collect()
    assert _value(snapshot, "worker.backlog.count") == 0
    assert not any(
        item.name == "worker.backlog.oldest_age_seconds" for item in snapshot.series
    )
    if failure == "exception":
        rows = None
    elif failure == "duplicate":
        rows = rows * 2
    else:
        rows = [
            (
                "worker.backlog.count",
                -1,
                {"job_type": "unsupported", "result": "pending"},
            )
        ]
    snapshot = recorder.collect()
    assert snapshot.unavailable_families == ("durable_backlog",)
    assert [item.name for item in snapshot.series] == ["financial.discrepancy.open"]
    assert sink.snapshot(recorder.identity) == snapshot


def test_runtime_context_is_explicit_nested_and_fresh_recorders_are_empty():
    first = MetricsRecorder("api", "test", "test-release")
    second = MetricsRecorder("worker", "test", "test-release")
    assert current_metrics() is None
    assert not record_metric(
        "database.timeout.total",
        1,
        {"operation": "database.lock", "result": "timed_out"},
    )
    with metrics_context(first):
        with metrics_context(second):
            assert current_metrics() is second
        assert current_metrics() is first
    assert current_metrics() is None
    assert second.snapshot().series == ()
