from __future__ import annotations

import pytest

from backend.observability.telemetry import (
    TelemetryLabelError,
    validate_telemetry_label,
    validate_telemetry_labels,
)


pytestmark = pytest.mark.no_db_cleanup


@pytest.mark.requirement("EN02-TEL-001")
def test_telemetry_labels_accept_only_approved_bounded_names_and_values():
    labels = validate_telemetry_labels(
        {
            "result": "success",
            "environment": "test",
            "operation": "booking.create",
            "route_template": "/games/{game_id}/join",
            "error_code": "API.TIMEOUT",
        }
    )

    assert list(labels.items()) == [
        ("environment", "test"),
        ("error_code", "API.TIMEOUT"),
        ("operation", "booking.create"),
        ("result", "success"),
        ("route_template", "/games/{game_id}/join"),
    ]


@pytest.mark.requirement("EN02-TEL-001")
@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("user_id", "user_123"),
        ("correlation_id", "123e4567-e89b-42d3-a456-426614174030"),
        ("operation", "123e4567-e89b-42d3-a456-426614174030"),
        ("operation", "pi_synthetic_provider_id"),
        ("operation", "user@example.invalid"),
        ("operation", "312-555-0199"),
        ("operation", "https://example.invalid/path"),
        ("operation", "venues/private/object.jpg"),
        ("operation", "free text value"),
        ("Operation", "booking.create"),
        ("arbitrary_label", "booking.create"),
    ],
)
def test_telemetry_labels_reject_high_cardinality_or_privacy_unsafe_material(
    name: str,
    value: str,
):
    with pytest.raises(TelemetryLabelError):
        validate_telemetry_label(name, value)


@pytest.mark.requirement("EN02-TEL-001")
def test_telemetry_label_mapping_is_immutable_after_validation():
    labels = validate_telemetry_labels({"operation": "booking.create"})

    with pytest.raises(TypeError):
        labels["operation"] = "user@example.invalid"
    with pytest.raises(TypeError):
        labels["email"] = "user@example.invalid"
    assert dict(labels) == {"operation": "booking.create"}


@pytest.mark.requirement("EN02-TEL-001")
def test_telemetry_labels_defensively_copy_source_mapping():
    source_labels = {"operation": "booking.create"}
    labels = validate_telemetry_labels(source_labels)

    source_labels["operation"] = "user@example.invalid"
    source_labels["email"] = "user@example.invalid"

    assert dict(labels) == {"operation": "booking.create"}


@pytest.mark.requirement("EN02-TEL-001")
@pytest.mark.parametrize(
    "route_template",
    [
        "/games/123e4567-e89b-42d3-a456-426614174030",
        "/games/{game_id}?token=synthetic",
        "https://example.invalid/games/{game_id}",
    ],
)
def test_telemetry_route_template_rejects_raw_identifiers_queries_and_urls(
    route_template: str,
):
    with pytest.raises(TelemetryLabelError):
        validate_telemetry_label("route_template", route_template)


@pytest.mark.requirement("EN02-TEL-001")
def test_telemetry_label_validation_rejects_sensitive_redaction_inputs():
    with pytest.raises(TelemetryLabelError):
        validate_telemetry_label("operation", "sk_test_synthetic")
