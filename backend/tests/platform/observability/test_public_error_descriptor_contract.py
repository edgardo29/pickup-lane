from __future__ import annotations

from types import MappingProxyType

import pytest

from backend.observability.errors import PublicErrorDescriptor, PublicErrorError


pytestmark = pytest.mark.no_db_cleanup


@pytest.mark.requirement("EN02-PUBLIC-001")
def test_public_error_descriptor_accepts_safe_fields_and_serializes_plain_details():
    correlation_id = "123e4567-e89b-42d3-a456-426614174020"
    descriptor = PublicErrorDescriptor(
        code="API.NOT_FOUND",
        message="Resource was not found.",
        correlation_id=correlation_id,
        details={
            "outcome": "not_found",
            "retryable": False,
            "hints": ["check_status"],
            "metadata": {"resource_kind": "booking"},
        },
    )

    serialized = descriptor.to_dict()

    assert serialized == {
        "code": "API.NOT_FOUND",
        "message": "Resource was not found.",
        "correlation_id": correlation_id,
        "details": {
            "hints": ["check_status"],
            "metadata": {"resource_kind": "booking"},
            "outcome": "not_found",
            "retryable": False,
        },
    }
    assert not isinstance(serialized["details"], MappingProxyType)
    assert isinstance(serialized["details"]["hints"], list)


@pytest.mark.requirement("EN02-PUBLIC-001")
@pytest.mark.parametrize(
    "details",
    [
        {"authorization": "Bearer synthetic-token"},
        {"message": "Traceback (most recent call last)"},
        {"error": RuntimeError("synthetic internal exception")},
        {"provider_response": {"body": "synthetic raw provider body"}},
        {"badKey": "unsafe"},
    ],
)
def test_public_error_descriptor_rejects_unsafe_internal_details(details: dict[str, object]):
    with pytest.raises(PublicErrorError):
        PublicErrorDescriptor(
            code="API.INTERNAL_ERROR",
            message="Request could not be completed.",
            details=details,
        )


@pytest.mark.requirement("EN02-PUBLIC-001")
def test_public_error_descriptor_defensively_copies_caller_owned_details():
    source_details = {
        "hints": ["retry_later"],
        "metadata": {"outcome": "retry_later"},
    }
    descriptor = PublicErrorDescriptor(
        code="API.UNAVAILABLE",
        message="Service is temporarily unavailable.",
        details=source_details,
    )

    source_details["authorization"] = "Bearer synthetic-token"
    source_details["hints"].append("Bearer synthetic-token")
    source_details["metadata"]["message"] = "Traceback (most recent call last)"

    assert descriptor.to_dict()["details"] == {
        "hints": ["retry_later"],
        "metadata": {"outcome": "retry_later"},
    }


@pytest.mark.requirement("EN02-PUBLIC-001")
def test_public_error_descriptor_nested_validated_details_are_immutable():
    descriptor = PublicErrorDescriptor(
        code="API.UNAVAILABLE",
        message="Service is temporarily unavailable.",
        details={
            "hints": ["retry_later"],
            "metadata": {"outcome": "retry_later"},
        },
    )

    assert descriptor.details is not None
    with pytest.raises(TypeError):
        descriptor.details["authorization"] = "Bearer synthetic-token"
    with pytest.raises(TypeError):
        descriptor.details["metadata"]["message"] = "Traceback (most recent call last)"
    with pytest.raises(AttributeError):
        descriptor.details["hints"].append("Bearer synthetic-token")

    assert descriptor.to_dict()["details"] == {
        "hints": ["retry_later"],
        "metadata": {"outcome": "retry_later"},
    }


@pytest.mark.requirement("EN02-PUBLIC-001")
@pytest.mark.parametrize(
    ("code", "message", "correlation_id"),
    [
        ("not stable", "Safe public message.", None),
        ("API.INTERNAL_ERROR", "postgresql://user:pass@example.invalid/db", None),
        ("API.INTERNAL_ERROR", "Safe public message.", "booking_12345"),
    ],
)
def test_public_error_descriptor_rejects_unsafe_top_level_fields(
    code: str,
    message: str,
    correlation_id: str | None,
):
    with pytest.raises(PublicErrorError):
        PublicErrorDescriptor(
            code=code,
            message=message,
            correlation_id=correlation_id,
        )
