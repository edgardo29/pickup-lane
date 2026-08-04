from datetime import datetime, timezone
import uuid

import pytest

from backend.observability.correlation import correlation_context
from backend.observability.events import EventEnvelope, EventEnvelopeError


pytestmark = pytest.mark.no_db_cleanup

FIXED_OCCURRED_AT = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


def test_valid_minimal_envelope_serializes_deterministically():
    envelope = EventEnvelope(
        event_name="api.request_completed",
        occurred_at=FIXED_OCCURRED_AT,
    )

    assert envelope.to_dict() == {
        "event_name": "api.request_completed",
        "occurred_at": "2026-01-02T03:04:05Z",
        "schema_version": "1",
    }
    assert envelope.to_json() == (
        '{"event_name":"api.request_completed",'
        '"occurred_at":"2026-01-02T03:04:05Z","schema_version":"1"}'
    )


def test_valid_optional_safe_fields_and_context_correlation_serialize():
    correlation_id = str(uuid.uuid4())
    request_id = str(uuid.uuid4())

    with correlation_context(correlation_id):
        envelope = EventEnvelope(
            event_name="payment.provider_outcome_recorded",
            occurred_at=FIXED_OCCURRED_AT,
            environment="test",
            request_id=request_id,
            actor_kind="system",
            operation="payment.refund",
            resource_kind="payment",
            result="success",
            stable_error_code="PAYMENT.OUTCOME_RECORDED",
            provider_kind="stripe",
            release="c1d68518c606f5b704b02bd9639fb76189c07a82",
            source_identity="backend-test-artifact",
            labels={
                "environment": "test",
                "operation": "payment.refund",
                "provider_kind": "stripe",
                "result": "success",
            },
        )

    body = envelope.to_dict()

    assert body["correlation_id"] == correlation_id
    assert body["request_id"] == request_id
    assert body["labels"] == {
        "environment": "test",
        "operation": "payment.refund",
        "provider_kind": "stripe",
        "result": "success",
    }


@pytest.mark.parametrize(
    "event_name",
    [
        "",
        "Payment Succeeded",
        "../payment.succeeded",
        "payment/succeeded",
        "payment." + ("a" * 90),
    ],
)
def test_invalid_event_names_are_rejected(event_name):
    with pytest.raises(EventEnvelopeError):
        EventEnvelope(event_name=event_name, occurred_at=FIXED_OCCURRED_AT)


@pytest.mark.parametrize("version", ["", "2", "v1"])
def test_invalid_schema_versions_are_rejected(version):
    with pytest.raises(EventEnvelopeError):
        EventEnvelope(
            event_name="api.request_completed",
            occurred_at=FIXED_OCCURRED_AT,
            schema_version=version,
        )


def test_naive_timestamp_is_rejected():
    with pytest.raises(EventEnvelopeError):
        EventEnvelope(
            event_name="api.request_completed",
            occurred_at=datetime(2026, 1, 2, 3, 4, 5),
        )


@pytest.mark.parametrize(
    "labels",
    [
        {"correlation_id": str(uuid.uuid4())},
        {"provider_event_id": "evt_123"},
        {"raw_payload": "{}"},
        {"result": "IntegrityError: duplicate key value"},
    ],
)
def test_prohibited_event_labels_are_rejected(labels):
    with pytest.raises(EventEnvelopeError):
        EventEnvelope(
            event_name="api.request_completed",
            occurred_at=FIXED_OCCURRED_AT,
            labels=labels,
        )


def test_free_form_exception_is_rejected_as_error_code():
    with pytest.raises(EventEnvelopeError):
        EventEnvelope(
            event_name="api.request_completed",
            occurred_at=FIXED_OCCURRED_AT,
            stable_error_code="IntegrityError: duplicate key value",
        )
