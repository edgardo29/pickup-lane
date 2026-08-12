import uuid

import pytest

from backend.observability.telemetry import (
    TelemetryLabelError,
    validate_telemetry_label,
    validate_telemetry_labels,
)


pytestmark = pytest.mark.no_db_cleanup


def test_approved_bounded_labels_are_accepted_and_sorted():
    labels = validate_telemetry_labels(
        {
            "result": "success",
            "operation": "api.request",
            "environment": "test",
            "provider_kind": "stripe",
            "resource_kind": "payment",
            "route_template": "/games/{game_id}/checkout",
            "error_code": "PAYMENT.UNAVAILABLE",
        }
    )

    assert labels == {
        "environment": "test",
        "error_code": "PAYMENT.UNAVAILABLE",
        "operation": "api.request",
        "provider_kind": "stripe",
        "resource_kind": "payment",
        "route_template": "/games/{game_id}/checkout",
        "result": "success",
    }


@pytest.mark.parametrize(
    "name",
    [
        "request_id",
        "correlation_id",
        "user_id",
        "payment_id",
        "booking_id",
        "provider_event_id",
        "idempotency_key",
        "url",
        "object_key",
        "exception_message",
        "free_text",
        "unknown_label",
    ],
)
def test_identifier_and_unknown_label_names_are_rejected(name):
    with pytest.raises(TelemetryLabelError):
        validate_telemetry_label(name, "safe")


@pytest.mark.parametrize(
    "value",
    [
        str(uuid.uuid4()),
        "evt_123",
        "payment:00000000-0000-4000-8000-000000000001",
        "player@example.com",
        "312-555-1212",
        "https://example.com/path",
        "venues/example/object.jpg",
        "IntegrityError: duplicate key value",
        "free form text",
    ],
)
def test_unbounded_or_sensitive_label_values_are_rejected(value):
    with pytest.raises(TelemetryLabelError):
        validate_telemetry_label("result", value)


def test_unapproved_environment_is_rejected():
    with pytest.raises(TelemetryLabelError):
        validate_telemetry_label("environment", "qa_personal")


def test_preview_environment_is_approved():
    assert validate_telemetry_label("environment", "preview") == "preview"


@pytest.mark.parametrize(
    "route_template",
    [
        "/games/00000000-0000-4000-8000-000000000001",
        "/games/{game_id}?user_id=123",
        "https://example.com/games/{game_id}",
        "/games/{game_id}/player@example.com",
    ],
)
def test_route_template_label_rejects_raw_params_urls_and_personal_data(route_template):
    with pytest.raises(TelemetryLabelError):
        validate_telemetry_label("route_template", route_template)
