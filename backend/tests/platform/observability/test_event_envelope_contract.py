from __future__ import annotations

from datetime import datetime, timezone

import pytest

from backend.observability.correlation import correlation_context
from backend.observability.events import EventEnvelope, EventEnvelopeError


pytestmark = pytest.mark.no_db_cleanup


def _occurred_at() -> datetime:
    return datetime(2026, 8, 11, 15, 30, tzinfo=timezone.utc)


@pytest.mark.requirement("EN02-EVENT-001")
def test_event_envelope_uses_current_correlation_and_serializes_safe_fields():
    correlation_id = "123e4567-e89b-42d3-a456-426614174010"

    with correlation_context(correlation_id):
        envelope = EventEnvelope(
            event_name="booking.created",
            occurred_at=_occurred_at(),
            environment="test",
            actor_kind="user",
            operation="booking.create",
            resource_kind="booking",
            result="success",
            labels={"provider_kind": "stripe", "outcome": "accepted"},
        )

    assert envelope.correlation_id == correlation_id
    assert envelope.to_dict() == {
        "actor_kind": "user",
        "correlation_id": correlation_id,
        "environment": "test",
        "event_name": "booking.created",
        "labels": {"outcome": "accepted", "provider_kind": "stripe"},
        "occurred_at": "2026-08-11T15:30:00Z",
        "operation": "booking.create",
        "resource_kind": "booking",
        "result": "success",
        "schema_version": "1",
    }
    assert "synthetic-secret" not in envelope.to_json()


@pytest.mark.requirement("EN02-EVENT-001")
@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [
        ("event_name", "raw route /games/123"),
        ("occurred_at", datetime(2026, 8, 11, 15, 30)),
        ("schema_version", "2"),
        ("operation", "booking create"),
        ("stable_error_code", "not a stable code"),
    ],
)
def test_event_envelope_rejects_unbounded_required_and_enum_fields(
    field_name: str,
    field_value: object,
):
    kwargs = {
        "event_name": "booking.created",
        "occurred_at": _occurred_at(),
        field_name: field_value,
    }

    with pytest.raises(EventEnvelopeError):
        EventEnvelope(**kwargs)


@pytest.mark.requirement("EN02-EVENT-001")
@pytest.mark.parametrize(
    "labels",
    [
        {"email": "user@example.invalid"},
        {"operation": "user@example.invalid"},
        {"operation": "https://example.invalid/path"},
        {"operation": "venues/private/object.jpg"},
        {"operation": "free text value"},
    ],
)
def test_event_envelope_rejects_unsafe_or_unapproved_labels(labels: dict[str, str]):
    with pytest.raises(EventEnvelopeError):
        EventEnvelope(
            event_name="booking.created",
            occurred_at=_occurred_at(),
            labels=labels,
        )


@pytest.mark.requirement("EN02-EVENT-001")
def test_event_envelope_defensively_copies_caller_owned_label_input():
    source_labels = {"operation": "booking.create"}
    envelope = EventEnvelope(
        event_name="booking.created",
        occurred_at=_occurred_at(),
        labels=source_labels,
    )

    source_labels["operation"] = "user@example.invalid"
    source_labels["email"] = "user@example.invalid"

    assert envelope.to_dict()["labels"] == {"operation": "booking.create"}


@pytest.mark.requirement("EN02-EVENT-001")
def test_event_envelope_validated_labels_cannot_be_mutated_after_validation():
    envelope = EventEnvelope(
        event_name="booking.created",
        occurred_at=_occurred_at(),
        labels={"operation": "booking.create"},
    )

    with pytest.raises(TypeError):
        envelope.labels["operation"] = "user@example.invalid"
    with pytest.raises(TypeError):
        envelope.labels["email"] = "user@example.invalid"
    assert envelope.to_dict()["labels"] == {"operation": "booking.create"}


@pytest.mark.requirement("EN02-EVENT-001")
@pytest.mark.parametrize(
    "release",
    [
        "release\n2026",
        "Bearer synthetic-token",
        "https://example.invalid/object?X-Amz-Signature=synthetic",
    ],
)
def test_event_envelope_rejects_unsafe_release_identity(release: str):
    with pytest.raises(EventEnvelopeError):
        EventEnvelope(
            event_name="booking.created",
            occurred_at=_occurred_at(),
            release=release,
        )
