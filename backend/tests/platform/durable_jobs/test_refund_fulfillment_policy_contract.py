from dataclasses import replace
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

pytestmark = [
    pytest.mark.suite_type("ordinary"),
    pytest.mark.requirement("WS05-03A-R1"),
]

Payment: Any = None
Refund: Any = None
DependencyMutationTimeoutUnknownError: Any = None
DependencyReadTimeoutError: Any = None
refunds: Any = None
stripe_service: Any = None
ConflictingIdempotencyKeyError: Any = None
InvalidJobPayloadError: Any = None
build_production_job_registry: Any = None
provider_observation_can_update_refund: Any = None
StripeRefundResult: Any = None


def _contract_imports():
    from backend.models import Payment, Refund
    from backend.observability.timeouts import (
        DependencyMutationTimeoutUnknownError,
        DependencyReadTimeoutError,
    )
    from backend.services import refund_fulfillment_service as refunds
    from backend.services import stripe_service
    from backend.services.durable_job_service import (
        ConflictingIdempotencyKeyError,
        InvalidJobPayloadError,
    )
    from backend.services.payment_job_service import build_production_job_registry
    from backend.services.refund_event_service import (
        provider_observation_can_update_refund,
    )
    from backend.services.stripe_service import StripeRefundResult

    return SimpleNamespace(
        Payment=Payment,
        Refund=Refund,
        DependencyMutationTimeoutUnknownError=DependencyMutationTimeoutUnknownError,
        DependencyReadTimeoutError=DependencyReadTimeoutError,
        refunds=refunds,
        stripe_service=stripe_service,
        ConflictingIdempotencyKeyError=ConflictingIdempotencyKeyError,
        InvalidJobPayloadError=InvalidJobPayloadError,
        build_production_job_registry=build_production_job_registry,
        provider_observation_can_update_refund=provider_observation_can_update_refund,
        StripeRefundResult=StripeRefundResult,
    )


@pytest.fixture(autouse=True)
def _load_contract_globals() -> None:
    globals().update(vars(_contract_imports()))


@pytest.mark.no_db_cleanup
def test_refund_job_policy_is_exact_and_registered() -> None:
    registry = build_production_job_registry()
    definition = registry.definition_for(refunds.STRIPE_REFUND_FULFILLMENT_JOB, 1)
    assert definition.maximum_attempts == 6
    assert definition.on_exhausted is refunds.handle_refund_job_exhausted
    assert refunds.REFUND_RETRY_DELAYS_SECONDS == (60, 300, 1800, 7200, 86400)


@pytest.mark.no_db_cleanup
@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"refund_id": str(uuid4())},
        {"refund_id": str(uuid4()), "attempt_number": 0},
        {"refund_id": str(uuid4()), "attempt_number": True},
        {"refund_id": "not-a-uuid", "attempt_number": 1},
        {"refund_id": str(uuid4()), "attempt_number": 1, "extra": "unsafe"},
    ],
)
def test_refund_job_payload_rejects_every_noncanonical_shape(payload) -> None:
    with pytest.raises(InvalidJobPayloadError):
        refunds.validate_refund_job_payload(payload)


@pytest.mark.no_db_cleanup
def test_refund_enqueue_uses_one_identity_for_payload_key_and_origin(monkeypatch) -> None:
    refund_id = uuid4()
    refund = Refund(
        id=refund_id,
        current_attempt_number=2,
        stripe_request_key=f"refund:{refund_id}:attempt:2",
    )
    captured = {}

    def fake_enqueue(db, **kwargs):
        del db
        captured.update(kwargs)
        return SimpleNamespace(**kwargs)

    monkeypatch.setattr(refunds, "enqueue_job", fake_enqueue)
    job = refunds.enqueue_refund_fulfillment_job(
        object(), refund=refund, registry=build_production_job_registry()
    )

    identity = {"refund_id": str(refund_id), "attempt_number": 2}
    assert captured["payload"] == identity
    assert captured["protected_identity"] == identity
    assert captured["idempotency_key"] == refund.stripe_request_key
    assert captured["origin_reference_type"] == "refund"
    assert captured["origin_reference_id"] == str(refund_id)
    assert captured["maximum_attempts"] == 6
    assert job.payload == identity


@pytest.mark.no_db_cleanup
def test_refund_enqueue_rejects_non_derived_request_key(monkeypatch) -> None:
    refund_id = uuid4()
    refund = Refund(
        id=refund_id,
        current_attempt_number=1,
        stripe_request_key="caller-selected-key",
    )
    called = False

    def fake_enqueue(*args, **kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(refunds, "enqueue_job", fake_enqueue)
    with pytest.raises(ConflictingIdempotencyKeyError):
        refunds.enqueue_refund_fulfillment_job(
            object(), refund=refund, registry=build_production_job_registry()
        )
    assert called is False


@pytest.mark.no_db_cleanup
@pytest.mark.parametrize(
    "changed_field",
    [
        "payload",
        "protected_identity",
        "idempotency_key",
        "origin_reference_type",
        "origin_reference_id",
        "maximum_attempts",
    ],
)
def test_refund_enqueue_rejects_existing_job_policy_mismatch(
    monkeypatch, changed_field
) -> None:
    refund_id = uuid4()
    identity = {"refund_id": str(refund_id), "attempt_number": 1}
    expected = {
        "payload": identity,
        "protected_identity": identity,
        "idempotency_key": f"refund:{refund_id}:attempt:1",
        "job_type": refunds.STRIPE_REFUND_FULFILLMENT_JOB,
        "payload_version": 1,
        "origin_reference_type": "refund",
        "origin_reference_id": str(refund_id),
        "maximum_attempts": 6,
    }
    mismatches = {
        "payload": {"refund_id": str(refund_id), "attempt_number": 2},
        "protected_identity": {"refund_id": str(uuid4()), "attempt_number": 1},
        "idempotency_key": "refund:conflict:attempt:1",
        "origin_reference_type": "payment",
        "origin_reference_id": str(uuid4()),
        "maximum_attempts": 5,
    }
    expected[changed_field] = mismatches[changed_field]
    monkeypatch.setattr(
        refunds,
        "enqueue_job",
        lambda *args, **kwargs: SimpleNamespace(**expected),
    )
    refund = Refund(
        id=refund_id,
        current_attempt_number=1,
        stripe_request_key=f"refund:{refund_id}:attempt:1",
    )

    with pytest.raises(ConflictingIdempotencyKeyError):
        refunds.enqueue_refund_fulfillment_job(
            object(), refund=refund, registry=build_production_job_registry()
        )


@pytest.mark.no_db_cleanup
def test_exhaustion_identity_can_use_protected_identity_when_payload_is_malformed() -> None:
    refund_id = uuid4()
    identity = {"refund_id": str(refund_id), "attempt_number": 3}
    job = SimpleNamespace(
        payload={"malformed": True},
        protected_identity=identity,
        idempotency_key=f"refund:{refund_id}:attempt:3",
        origin_reference_type="refund",
        origin_reference_id=str(refund_id),
    )
    assert refunds._proven_exhausted_identity(job) == (refund_id, 3)


@pytest.mark.no_db_cleanup
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("protected_identity", {"refund_id": "bad", "attempt_number": 1}),
        ("idempotency_key", "refund:bad:attempt:1"),
        ("origin_reference_type", "payment"),
        ("origin_reference_id", str(uuid4())),
    ],
)
def test_exhaustion_identity_rejects_unproved_components(field, value) -> None:
    refund_id = uuid4()
    identity = {"refund_id": str(refund_id), "attempt_number": 1}
    fields = {
        "payload": identity,
        "protected_identity": identity,
        "idempotency_key": f"refund:{refund_id}:attempt:1",
        "origin_reference_type": "refund",
        "origin_reference_id": str(refund_id),
    }
    fields[field] = value
    assert refunds._proven_exhausted_identity(SimpleNamespace(**fields)) is None


@pytest.mark.no_db_cleanup
@pytest.mark.parametrize(
    ("raw", "local", "provider", "reason"),
    [
        ("pending", "processing", "processing", "stripe_refund_pending"),
        (
            "requires_action",
            "processing",
            "processing",
            "stripe_refund_requires_action",
        ),
        ("succeeded", "succeeded", "succeeded", "stripe_refund_succeeded"),
        ("failed", "failed", "failed", "stripe_refund_failed"),
        ("canceled", "cancelled", "cancelled", "stripe_refund_cancelled"),
        ("unexpected", "processing", "unknown", "stripe_refund_unknown"),
    ],
)
def test_refund_status_normalization_is_finite(raw, local, provider, reason) -> None:
    assert refunds._normalize_provider_status(raw) == (local, provider, reason)


@pytest.mark.no_db_cleanup
@pytest.mark.parametrize(
    ("current", "observed", "allowed"),
    [
        ("processing", "succeeded", True),
        ("processing", "failed", True),
        ("succeeded", "processing", False),
        ("succeeded", "failed", False),
        ("succeeded", "cancelled", False),
        ("failed", "processing", False),
        ("cancelled", "failed", False),
        ("failed", "succeeded", True),
    ],
)
def test_provider_observation_transition_matrix_is_monotonic(
    current: str, observed: str, allowed: bool
) -> None:
    assert (
        provider_observation_can_update_refund(
            current_status=current, observed_status=observed
        )
        is allowed
    )


@pytest.mark.no_db_cleanup
def test_attempt_history_ignores_audit_events_and_keeps_success_absorbing() -> None:
    from backend.services.refund_attempt_policy import reduce_refund_attempt_events

    def provider_event(attempt_number: int, status: str):
        return SimpleNamespace(
            attempt_number=attempt_number,
            event_type="provider_result_recorded",
            provider="stripe",
            provider_refund_id=f"re_attempt_{attempt_number}",
            provider_status=status,
            new_refund_status=status,
            event_metadata=None,
        )

    events = [
        SimpleNamespace(
            attempt_number=1,
            event_type="local_status_changed",
            provider="stripe",
            provider_refund_id=None,
            provider_status=None,
            new_refund_status="failed",
            event_metadata=None,
        ),
        provider_event(1, "failed"),
        provider_event(1, "succeeded"),
        provider_event(1, "failed"),
        provider_event(2, "cancelled"),
        SimpleNamespace(
            attempt_number=2,
            event_type="local_status_changed",
            provider="stripe",
            provider_refund_id=None,
            provider_status=None,
            new_refund_status="failed",
            event_metadata={"provider_call_started": False},
        ),
    ]

    assert reduce_refund_attempt_events(events) == {
        1: "succeeded",
        2: "cancelled",
    }


@pytest.mark.no_db_cleanup
def test_status_bearing_non_authoritative_event_cannot_prove_terminal_attempt() -> None:
    from backend.services.refund_attempt_policy import reduce_refund_attempt_events

    event = SimpleNamespace(
        attempt_number=1,
        event_type="local_status_changed",
        provider="stripe",
        provider_refund_id=None,
        provider_status=None,
        new_refund_status="failed",
        event_metadata={"audit_only": True},
    )

    assert reduce_refund_attempt_events([event]) == {}


@pytest.mark.no_db_cleanup
def test_attempt_evidence_rejects_conflicting_provider_identity() -> None:
    from backend.services.refund_attempt_policy import (
        canonical_provider_attempt_event,
        reduce_refund_attempt_evidence,
    )

    def provider_event(provider_refund_id: str):
        return SimpleNamespace(
            id=uuid4(),
            refund_id=uuid4(),
            attempt_number=1,
            attempt_amount_cents=500,
            attempt_currency="USD",
            attempt_request_key="refund:00000000-0000-0000-0000-000000000001:attempt:1",
            event_type="provider_result_recorded",
            provider="stripe",
            provider_refund_id=provider_refund_id,
            provider_charge_id="ch_exact",
            provider_status="failed",
            new_refund_status="failed",
            event_metadata=None,
        )

    events = [provider_event("re_first"), provider_event("re_conflicting")]
    evidence = reduce_refund_attempt_evidence(events)[1]

    assert evidence.identity_consistent is False
    assert canonical_provider_attempt_event(events, attempt_number=1) is None


@pytest.mark.no_db_cleanup
@pytest.mark.parametrize(
    "mutation",
    [
        {"id": "re_wrong"},
        {"amount_cents": 499},
        {"currency": "EUR"},
        {"charge_id": "ch_wrong"},
        {"payment_intent_id": "pi_wrong"},
        {"metadata": {"refund_id": "wrong", "payment_id": "wrong", "attempt_number": "1"}},
        {"metadata": None},
    ],
)
def test_provider_result_requires_complete_immutable_attempt_identity(mutation) -> None:
    refund_id = uuid4()
    payment_id = uuid4()
    payment = Payment(
        id=payment_id,
        provider_payment_intent_id="pi_exact",
        provider_charge_id="ch_exact",
    )
    refund = Refund(
        id=refund_id,
        payment_id=payment_id,
        current_attempt_number=1,
        stripe_request_key=f"refund:{refund_id}:attempt:1",
        provider_refund_id="re_exact",
        provider_charge_id="ch_exact",
        amount_cents=500,
        currency="USD",
    )
    valid = StripeRefundResult(
        id="re_exact",
        status="succeeded",
        amount_cents=500,
        currency="USD",
        charge_id="ch_exact",
        payment_intent_id="pi_exact",
        metadata={
            "refund_id": str(refund_id),
            "payment_id": str(payment_id),
            "attempt_number": "1",
        },
    )
    assert refunds._validate_provider_result(refund, payment, valid)
    assert not refunds._validate_provider_result(
        refund, payment, replace(valid, **mutation)
    )


class _HttpError(RuntimeError):
    def __init__(self, status: int):
        super().__init__(str(status))
        self.http_status = status


@pytest.mark.no_db_cleanup
@pytest.mark.parametrize(
    ("error_kind", "classification"),
    [
        ("http_429", "rate_limited"),
        ("http_400", "unsafe_client_error"),
        ("http_503", "provider_server_error"),
        ("network", "network_or_unknown"),
        ("mutation_timeout", "mutation_timeout_unknown"),
        ("read_timeout", "read_timeout"),
    ],
)
def test_stripe_refund_error_classification_is_finite(
    error_kind: str, classification: str
) -> None:
    errors = {
        "http_429": _HttpError(429),
        "http_400": _HttpError(400),
        "http_503": _HttpError(503),
        "network": RuntimeError("network"),
        "mutation_timeout": DependencyMutationTimeoutUnknownError(
            provider_kind="stripe", operation="stripe.refund.create"
        ),
        "read_timeout": DependencyReadTimeoutError(
            provider_kind="stripe", operation="stripe.refund.retrieve"
        ),
    }
    error = errors[error_kind]
    assert stripe_service._classify_refund_exception(error) == classification


@pytest.mark.no_db_cleanup
def test_refund_listing_enforces_three_page_bound(monkeypatch) -> None:
    pages = []

    def fake_read(_operation, call, **_kwargs):
        page_number = len(pages) + 1
        rows = [
            SimpleNamespace(
                id=f"re_{page_number}_{index}",
                status="pending",
                amount=100,
                currency="usd",
                charge="ch_exact",
                payment_intent="pi_exact",
                metadata={},
            )
            for index in range(100)
        ]
        page = SimpleNamespace(data=rows, has_more=True)
        pages.append(page)
        return call(SimpleNamespace(v1=SimpleNamespace(refunds=SimpleNamespace(list=lambda _params: page))))

    monkeypatch.setattr(stripe_service, "_call_stripe_read", fake_read)
    results, truncated = stripe_service.list_refunds_for_charge("ch_exact")
    assert len(pages) == 3
    assert len(results) == 300
    assert truncated is True


@pytest.mark.no_db_cleanup
@pytest.mark.parametrize(
    "credit_component", ["none", "released", "restored", "mixed"]
)
def test_refund_notice_credit_component_is_finite(credit_component: str) -> None:
    from backend.services.game_notification_service import booking_refunded_copy

    copy = booking_refunded_copy(
        stripe_refund_processed=True,
        credit_component=credit_component,
        notice_context="generic_refund",
    )
    assert set(copy) == {"title", "summary", "body"}


@pytest.mark.no_db_cleanup
def test_refund_notice_rejects_nonfinite_credit_component() -> None:
    from backend.services.game_notification_service import booking_refunded_copy

    with pytest.raises(ValueError):
        booking_refunded_copy(
            stripe_refund_processed=False,
            credit_component="attempted",  # type: ignore[arg-type]
            notice_context="generic_refund",
        )


@pytest.mark.no_db_cleanup
@pytest.mark.parametrize(
    ("cash_complete", "credit_component"),
    [
        (False, "restored"),
        (True, "restored"),
        (True, "mixed"),
    ],
)
def test_player_removal_refund_notice_uses_removal_wording_for_completion_orders(
    cash_complete: bool,
    credit_component: str,
) -> None:
    from backend.services.game_notification_service import booking_refunded_copy

    copy = booking_refunded_copy(
        stripe_refund_processed=cash_complete,
        credit_component=credit_component,  # type: ignore[arg-type]
        notice_context="player_removal",
    )
    assert "removed from this official game" in copy["body"]
    assert "canceled official game" not in copy["body"]


@pytest.mark.no_db_cleanup
@pytest.mark.parametrize(
    ("notice_context", "expected"),
    [
        ("game_cancellation", "canceled official game"),
        ("player_removal", "removed from this official game"),
        ("reservation_expired", "reservation expired"),
        ("capacity_conflict", "capacity changed"),
        ("generic_refund", "official-game booking"),
    ],
)
@pytest.mark.parametrize(
    ("stripe_refund_processed", "credit_component"),
    [(False, "restored"), (True, "none"), (True, "restored")],
)
def test_refund_notice_context_covers_both_completion_orders(
    notice_context: str,
    expected: str,
    stripe_refund_processed: bool,
    credit_component: str,
) -> None:
    from backend.services.game_notification_service import booking_refunded_copy

    copy = booking_refunded_copy(
        stripe_refund_processed=stripe_refund_processed,
        credit_component=credit_component,  # type: ignore[arg-type]
        notice_context=notice_context,  # type: ignore[arg-type]
    )
    assert expected in copy["body"]


@pytest.mark.no_db_cleanup
@pytest.mark.parametrize(
    ("notice_context", "game_status", "expected_force_null"),
    [
        ("player_removal", "scheduled", False),
        ("reservation_expired", "scheduled", False),
        ("capacity_conflict", "full", False),
        ("generic_refund", "scheduled", False),
        ("generic_refund", "cancelled", True),
        ("game_cancellation", "scheduled", True),
    ],
)
def test_refund_notice_action_follows_context_and_current_game_state(
    monkeypatch,
    notice_context: str,
    game_status: str,
    expected_force_null: bool,
) -> None:
    from datetime import datetime, timezone

    from backend.services import game_notification_service as notifications

    captured = {}
    monkeypatch.setattr(
        notifications,
        "build_game_notification_fields",
        lambda _game, _type, **kwargs: captured.update(kwargs) or {},
    )
    monkeypatch.setattr(notifications, "reopen_aggregated_notification", lambda *_a, **_k: None)
    game = SimpleNamespace(
        id=uuid4(),
        deleted_at=None,
        publish_status="published",
        game_status=game_status,
    )
    booking = SimpleNamespace(id=uuid4(), buyer_user_id=uuid4())
    db = SimpleNamespace(
        scalars=lambda _statement: SimpleNamespace(first=lambda: None),
        get=lambda *_args: None,
    )
    notifications.create_or_reopen_booking_refunded_notification(
        db,
        db_game=game,
        booking=booking,
        now=datetime.now(timezone.utc),
        stripe_refund_processed=True,
        notice_context=notice_context,  # type: ignore[arg-type]
    )
    assert captured["force_action_null"] is expected_force_null


@pytest.mark.no_db_cleanup
@pytest.mark.parametrize("completion_order", ["credit_then_cash", "cash_then_credit"])
def test_refund_notice_preserves_combined_completion_in_either_order(
    monkeypatch, completion_order: str
) -> None:
    from datetime import datetime, timezone

    from backend.services import game_notification_service as notifications

    state = {"existing": None, "values": None}
    payment = SimpleNamespace(id=uuid4())
    refund = SimpleNamespace(id=uuid4())

    class _Db:
        def scalars(self, _statement):
            return SimpleNamespace(first=lambda: state["existing"])

        def get(self, _model, object_id):
            return {payment.id: payment, refund.id: refund}.get(object_id)

    def reopen(_db, **kwargs):
        values = kwargs["values"]
        state["values"] = values
        state["existing"] = SimpleNamespace(
            related_payment_id=values["related_payment_id"],
            related_refund_id=values["related_refund_id"],
        )

    monkeypatch.setattr(
        notifications,
        "build_game_notification_fields",
        lambda _game, _type, **kwargs: kwargs,
    )
    monkeypatch.setattr(notifications, "reopen_aggregated_notification", reopen)
    game = SimpleNamespace(
        id=uuid4(),
        deleted_at=None,
        publish_status="published",
        game_status="scheduled",
    )
    booking = SimpleNamespace(id=uuid4(), buyer_user_id=uuid4())
    calls = {
        "credit": {
            "payment": None,
            "refund": None,
            "stripe_refund_processed": False,
            "credit_component": "restored",
        },
        "cash": {
            "payment": payment,
            "refund": refund,
            "stripe_refund_processed": True,
            "credit_component": "restored",
        },
    }
    order = ("credit", "cash") if completion_order == "credit_then_cash" else ("cash", "credit")
    for step in order:
        notifications.create_or_reopen_booking_refunded_notification(
            _Db(),
            db_game=game,
            booking=booking,
            now=datetime.now(timezone.utc),
            notice_context="generic_refund",
            **calls[step],
        )

    assert state["values"]["title"] == "Refund and credit processed"
    assert state["values"]["related_refund_id"] == refund.id
