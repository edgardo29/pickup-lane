from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Callable

import pytest

import backend.services.stripe_service as stripe_service
from backend.observability.timeouts import (
    DependencyMutationTimeoutUnknownError,
    DependencyReadTimeoutError,
)

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
        invoice_settings = payload.get("invoice_settings", {}) if isinstance(payload, dict) else {}
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
    monkeypatch.setattr(stripe_service, "get_stripe_module", lambda: SimpleNamespace(api_key=None))
    monkeypatch.setattr(stripe_service, "_stripe_settings", lambda: _FakeStripeSettings())
    return calls


@pytest.mark.requirement("WS02-04C1-R2")
def test_stripe_read_and_mutation_clients_receive_distinct_timeout_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(stripe_service, "_stripe_settings", lambda: _FakeStripeSettings())
    monkeypatch.setattr(stripe_service, "_import_stripe_module", lambda: _StripeModule)

    pair = stripe_service.get_stripe_client_pair()

    assert pair.read.secret_key == "sk_test_synthetic"
    assert pair.mutation.secret_key == "sk_test_synthetic"
    assert pair.read.http_client.timeout == 6
    assert pair.mutation.http_client.timeout == 15
    assert pair.read is not pair.mutation


_READ_CALLS: tuple[tuple[str, Callable[[], object]], ...] = (
    ("stripe.setup_intent.retrieve", lambda: stripe_service.retrieve_setup_intent("seti_test")),
    ("stripe.payment_method.retrieve", lambda: stripe_service.retrieve_payment_method("pm_test")),
    ("stripe.payment_intent.retrieve", lambda: stripe_service.retrieve_payment_intent("pi_test")),
    ("stripe.refund.retrieve", lambda: stripe_service.retrieve_refund("re_test")),
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
    ("stripe.payment_method.detach", lambda: stripe_service.detach_payment_method("pm_test")),
    (
        "stripe.customer.default_payment_method.set",
        lambda: stripe_service.set_customer_default_payment_method(
            customer_id="cus_test",
            payment_method_id="pm_test",
        ),
    ),
    (
        "stripe.customer.default_payment_method.clear",
        lambda: stripe_service.clear_customer_default_payment_method(customer_id="cus_test"),
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
