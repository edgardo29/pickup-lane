from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import pytest

from backend.observability.metrics import MetricsRecorder, metrics_context
from backend.observability.timeouts import (
    DependencyMutationTimeoutUnknownError,
    DependencyReadTimeoutError,
)
from backend.services import stripe_service

pytestmark = pytest.mark.no_db_cleanup


@dataclass(frozen=True)
class _FakeStripeSettings:
    enable_stripe_payments: bool = True
    stripe_secret_key_value: str = "sk_test_synthetic"
    stripe_read_timeout_seconds: int = 6
    stripe_mutation_timeout_seconds: int = 15
    stripe_currency: str = "USD"


class _ConstructedStripeClient:
    def __init__(self, secret_key: str, *, http_client: Any) -> None:
        self.secret_key = secret_key
        self.http_client = http_client


class _ConstructedRequestsClient:
    def __init__(self, *, timeout: int) -> None:
        self.timeout = timeout


class _StripeModule:
    StripeClient = _ConstructedStripeClient
    RequestsClient = _ConstructedRequestsClient
    api_key: str | None = None


class _TimeoutingResource:
    def __init__(self, *, side: str, calls: list[tuple[str, str]]) -> None:
        self.side = side
        self.calls = calls

    def _raise(self, operation: str) -> None:
        self.calls.append((self.side, operation))
        raise TimeoutError(operation)


class _Customers(_TimeoutingResource):
    def create(self, *args: Any, **kwargs: Any) -> None:
        self._raise("customer.create")

    def update(self, customer_id: str, *args: Any, **kwargs: Any) -> None:
        del customer_id
        payload = args[0] if args else kwargs
        invoice_settings = (
            payload.get("invoice_settings", {}) if isinstance(payload, dict) else {}
        )
        if invoice_settings.get("default_payment_method") is None:
            self._raise("customer.default_payment_method.clear")
        self._raise("customer.default_payment_method.set")


class _SetupIntents(_TimeoutingResource):
    def create(self, *args: Any, **kwargs: Any) -> None:
        self._raise("setup_intent.create")

    def retrieve(self, *args: Any, **kwargs: Any) -> None:
        self._raise("setup_intent.retrieve")


class _PaymentMethods(_TimeoutingResource):
    def retrieve(self, *args: Any, **kwargs: Any) -> None:
        self._raise("payment_method.retrieve")

    def detach(self, *args: Any, **kwargs: Any) -> None:
        self._raise("payment_method.detach")


class _PaymentIntents(_TimeoutingResource):
    def create(self, *args: Any, **kwargs: Any) -> None:
        self._raise("payment_intent.create")

    def confirm(self, *args: Any, **kwargs: Any) -> None:
        self._raise("payment_intent.confirm")

    def retrieve(self, *args: Any, **kwargs: Any) -> None:
        self._raise("payment_intent.retrieve")


class _Refunds(_TimeoutingResource):
    def create(self, *args: Any, **kwargs: Any) -> None:
        self._raise("refund.create")

    def retrieve(self, *args: Any, **kwargs: Any) -> None:
        self._raise("refund.retrieve")

    def list(self, *args: Any, **kwargs: Any) -> None:
        self._raise("refund.list")


class _TimeoutingV1:
    def __init__(self, *, side: str, calls: list[tuple[str, str]]) -> None:
        self.customers = _Customers(side=side, calls=calls)
        self.setup_intents = _SetupIntents(side=side, calls=calls)
        self.payment_methods = _PaymentMethods(side=side, calls=calls)
        self.payment_intents = _PaymentIntents(side=side, calls=calls)
        self.refunds = _Refunds(side=side, calls=calls)


class _TimeoutingClient:
    def __init__(self, *, side: str, calls: list[tuple[str, str]]) -> None:
        self.v1 = _TimeoutingV1(side=side, calls=calls)


def _install_timeout_pair(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    calls: list[tuple[str, str]] = []
    pair = stripe_service.StripeClientPair(
        read=_TimeoutingClient(side="read", calls=calls),
        mutation=_TimeoutingClient(side="mutation", calls=calls),
    )
    monkeypatch.setattr(stripe_service, "get_stripe_client_pair", lambda: pair)
    monkeypatch.setattr(
        stripe_service, "get_stripe_module", lambda: SimpleNamespace(api_key=None)
    )
    monkeypatch.setattr(
        stripe_service, "_stripe_settings", lambda: _FakeStripeSettings()
    )
    return calls


@pytest.mark.requirement("WS02-04C1-R2")
def test_stripe_read_and_mutation_clients_receive_distinct_timeout_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        stripe_service, "_stripe_settings", lambda: _FakeStripeSettings()
    )
    monkeypatch.setattr(stripe_service, "_import_stripe_module", lambda: _StripeModule)

    pair = stripe_service.get_stripe_client_pair()

    assert pair.read.secret_key == "sk_test_synthetic"
    assert pair.mutation.secret_key == "sk_test_synthetic"
    assert pair.read.http_client.timeout == 6
    assert pair.mutation.http_client.timeout == 15
    assert pair.read is not pair.mutation


_READ_CALLS: tuple[tuple[str, Callable[[], object]], ...] = (
    (
        "stripe.setup_intent.retrieve",
        lambda: stripe_service.retrieve_setup_intent("seti_test"),
    ),
    (
        "stripe.payment_method.retrieve",
        lambda: stripe_service.retrieve_payment_method("pm_test"),
    ),
    (
        "stripe.payment_intent.retrieve",
        lambda: stripe_service.retrieve_payment_intent("pi_test"),
    ),
    ("stripe.refund.retrieve", lambda: stripe_service.retrieve_refund("re_test")),
    (
        "stripe.refund.list",
        lambda: stripe_service.list_refunds_for_charge("ch_test"),
    ),
)

_MUTATION_CALLS: tuple[tuple[str, Callable[[], object]], ...] = (
    (
        "stripe.customer.create",
        lambda: stripe_service.create_customer(
            email="user@example.invalid",
            name="Synthetic User",
            idempotency_key="customer-key",
            metadata={"source": "test"},
        ),
    ),
    (
        "stripe.setup_intent.create",
        lambda: stripe_service.create_setup_intent(
            customer_id="cus_test",
            idempotency_key="setup-key",
            metadata={"source": "test"},
        ),
    ),
    (
        "stripe.payment_method.detach",
        lambda: stripe_service.detach_payment_method("pm_test"),
    ),
    (
        "stripe.customer.default_payment_method.set",
        lambda: stripe_service.set_customer_default_payment_method(
            customer_id="cus_test",
            payment_method_id="pm_test",
        ),
    ),
    (
        "stripe.customer.default_payment_method.clear",
        lambda: stripe_service.clear_customer_default_payment_method(
            customer_id="cus_test"
        ),
    ),
    (
        "stripe.payment_intent.create",
        lambda: stripe_service.create_payment_intent(
            amount_cents=1500,
            currency="USD",
            idempotency_key="payment-key",
            metadata={"source": "test"},
        ),
    ),
    (
        "stripe.payment_intent.confirm",
        lambda: stripe_service.confirm_payment_intent(
            "pi_test",
            payment_method_id="pm_test",
        ),
    ),
    (
        "stripe.refund.create",
        lambda: stripe_service.create_refund(
            charge_id="ch_test",
            amount_cents=500,
            currency="USD",
            idempotency_key="refund-key",
            metadata={"source": "test"},
        ),
    ),
)


@pytest.mark.requirement("WS02-04C1-R2")
@pytest.mark.parametrize(("operation", "call"), _READ_CALLS)
def test_current_stripe_reads_map_timeout_to_dependency_read(
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
    call: Callable[[], object],
) -> None:
    calls = _install_timeout_pair(monkeypatch)

    if operation.startswith("stripe.refund."):
        with pytest.raises(stripe_service.StripeRefundOperationError) as exc_info:
            call()
        assert exc_info.value.operation == operation.removeprefix("stripe.")
        assert exc_info.value.classification == "read_timeout"
    else:
        with pytest.raises(DependencyReadTimeoutError) as exc_info:
            call()
        assert exc_info.value.provider_kind == "stripe"
        assert exc_info.value.operation == operation
        assert exc_info.value.contract.details["outcome"] == "retry_later"
    assert calls == [("read", operation.removeprefix("stripe."))]


@pytest.mark.requirement("WS02-04C1-R2")
@pytest.mark.parametrize(("operation", "call"), _MUTATION_CALLS)
def test_current_stripe_mutations_map_timeout_to_unknown_without_replay(
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
    call: Callable[[], object],
) -> None:
    calls = _install_timeout_pair(monkeypatch)

    if operation.startswith("stripe.refund."):
        with pytest.raises(stripe_service.StripeRefundOperationError) as exc_info:
            call()
        assert exc_info.value.operation == operation.removeprefix("stripe.")
        assert exc_info.value.classification == "mutation_timeout_unknown"
    else:
        with pytest.raises(DependencyMutationTimeoutUnknownError) as exc_info:
            call()
        assert exc_info.value.provider_kind == "stripe"
        assert exc_info.value.operation == operation
        assert exc_info.value.contract.details["outcome"] == "unknown"
    assert calls == [("mutation", operation.removeprefix("stripe."))]


@pytest.mark.requirement("WS02-04C1-R2", "WS02-04C1-R8")
def test_stripe_non_timeout_provider_errors_are_not_reclassified_or_replayed() -> None:
    calls = 0

    def fail_once() -> None:
        nonlocal calls
        calls += 1
        raise RuntimeError("synthetic provider failure")

    with pytest.raises(RuntimeError, match="synthetic provider failure"):
        stripe_service._call_stripe_mutation("payment_intent.create", fail_once)

    assert calls == 1


@pytest.mark.parametrize(("operation", "call"), (*_READ_CALLS, *_MUTATION_CALLS))
@pytest.mark.parametrize(
    "scenario",
    ["succeeded", "timeout", "rate_limited", "failed", "configuration_error"],
)
def test_every_stripe_operation_has_one_safe_metric_and_preserves_result_or_exception(
    monkeypatch,
    operation,
    call,
    scenario,
):
    import stripe

    sdk_calls = []
    result = SimpleNamespace(
        id="synthetic",
        status="succeeded",
        type="card",
        card=SimpleNamespace(
            fingerprint="synthetic",
            brand="visa",
            last4="4242",
            exp_month=12,
            exp_year=2035,
        ),
    )
    errors = {
        "timeout": TimeoutError("private-canary"),
        "rate_limited": stripe.RateLimitError("private-canary"),
        "failed": RuntimeError("private-canary"),
        "configuration_error": stripe_service.StripeConfigError("private-canary"),
    }

    class Resource:
        def __getattr__(self, name):
            def sdk_call(*args, **kwargs):
                sdk_calls.append(name)
                if scenario in errors:
                    raise errors[scenario]
                return result

            return sdk_call

    client = SimpleNamespace(
        v1=SimpleNamespace(
            **{
                name: Resource()
                for name in (
                    "customers",
                    "setup_intents",
                    "payment_methods",
                    "payment_intents",
                    "refunds",
                )
            }
        )
    )

    def acquire():
        if scenario == "configuration_error":
            raise errors[scenario]
        return stripe_service.StripeClientPair(read=client, mutation=client)

    monkeypatch.setattr(stripe_service, "get_stripe_client_pair", acquire)
    monkeypatch.setattr(
        stripe_service, "_stripe_settings", lambda: _FakeStripeSettings()
    )
    recorder = MetricsRecorder("api", "test", "test-release")
    read = operation in {item[0] for item in _READ_CALLS}
    with metrics_context(recorder):
        if scenario == "succeeded":
            call()
        else:
            if operation.startswith("stripe.refund.") and scenario != "configuration_error":
                expected = stripe_service.StripeRefundOperationError
            else:
                expected = (
                    (
                        DependencyReadTimeoutError
                        if read
                        else DependencyMutationTimeoutUnknownError
                    )
                    if scenario == "timeout"
                    else type(errors[scenario])
                )
            with pytest.raises(expected):
                call()
    metric = recorder.snapshot().series
    assert len(metric) == 1
    expected_result = (
        ("timed_out" if read else "unknown_outcome")
        if scenario == "timeout"
        else scenario
    )
    assert dict(metric[0].dimensions) == {
        "provider_kind": "stripe",
        "operation": operation,
        "result": expected_result,
    }
    assert metric[0].value == 1
    assert len(sdk_calls) == (0 if scenario == "configuration_error" else 1)
    assert "private-canary" not in repr(recorder.snapshot())


@pytest.mark.parametrize(
    ("operation", "call"),
    tuple(
        item
        for item in _MUTATION_CALLS
        if item[0] in {"stripe.payment_intent.create", "stripe.payment_intent.confirm"}
    ),
)
def test_payment_intent_card_rejection_is_not_operational_failure(
    monkeypatch, operation, call
):
    import stripe

    calls = _install_timeout_pair(monkeypatch)

    def reject(self, sdk_operation):
        calls.append((self.side, sdk_operation))
        raise stripe.CardError("private-canary", "payment_method", "card_declined")

    monkeypatch.setattr(_TimeoutingResource, "_raise", reject)
    recorder = MetricsRecorder("api", "test", "test-release")
    with metrics_context(recorder), pytest.raises(stripe.CardError):
        call()
    series = recorder.snapshot().series
    assert len(series) == 1
    assert dict(series[0].dimensions)["result"] == "rejected"
    assert len(calls) == 1


def test_extraction_failure_is_not_success_or_new_timeout_translation(monkeypatch):
    class Client:
        v1 = SimpleNamespace(
            payment_methods=SimpleNamespace(
                retrieve=lambda value: SimpleNamespace(type="other")
            )
        )

    monkeypatch.setattr(
        stripe_service,
        "get_stripe_client_pair",
        lambda: stripe_service.StripeClientPair(Client(), Client()),
    )
    recorder = MetricsRecorder("api", "test", "test-release")
    with metrics_context(recorder), pytest.raises(stripe_service.StripeConfigError):
        stripe_service.retrieve_payment_method("pm_synthetic")
    assert dict(recorder.snapshot().series[0].dimensions)["result"] == "failed"
    monkeypatch.setattr(
        stripe_service,
        "extract_card_payment_method_result",
        lambda value: (_ for _ in ()).throw(TimeoutError("private-canary")),
    )
    with metrics_context(recorder), pytest.raises(TimeoutError):
        stripe_service.retrieve_payment_method("pm_synthetic")
