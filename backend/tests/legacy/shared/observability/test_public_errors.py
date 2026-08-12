import uuid

import pytest

from backend.observability.errors import PublicErrorDescriptor, PublicErrorError


pytestmark = pytest.mark.no_db_cleanup


def test_public_error_serializes_stable_code_safe_message_and_correlation_id():
    correlation_id = str(uuid.uuid4())

    descriptor = PublicErrorDescriptor(
        code="PAYMENT.UNAVAILABLE",
        message="Payment is temporarily unavailable. Please try again.",
        correlation_id=correlation_id,
        details={"retryable": True, "reason_code": "provider_unavailable"},
    )

    assert descriptor.to_dict() == {
        "code": "PAYMENT.UNAVAILABLE",
        "message": "Payment is temporarily unavailable. Please try again.",
        "correlation_id": correlation_id,
        "details": {"reason_code": "provider_unavailable", "retryable": True},
    }


def test_exception_object_cannot_serialize_as_public_detail():
    with pytest.raises(PublicErrorError):
        PublicErrorDescriptor(
            code="API.UNEXPECTED",
            message="Something went wrong.",
            details={"error": RuntimeError("database exploded")},
        )


def test_exception_object_cannot_serialize_as_public_message():
    with pytest.raises(PublicErrorError):
        PublicErrorDescriptor(
            code="API.UNEXPECTED",
            message=RuntimeError("database exploded"),
        )


@pytest.mark.parametrize(
    "message",
    [
        "Traceback (most recent call last): File \"/tmp/app.py\", line 1",
        "IntegrityError: duplicate key value violates unique constraint",
        "R2_SECRET_ACCESS_KEY is not set.",
        "Contact user@example.com for details.",
        "Open https://example.com/upload?X-Amz-Signature=secret",
    ],
)
def test_stack_trace_database_provider_and_secret_messages_are_rejected(message):
    with pytest.raises(PublicErrorError):
        PublicErrorDescriptor(code="API.UNEXPECTED", message=message)


def test_sensitive_detail_key_is_rejected():
    with pytest.raises(PublicErrorError):
        PublicErrorDescriptor(
            code="API.UNEXPECTED",
            message="Something went wrong.",
            details={"database_url": "postgresql://user:pass@localhost/app"},
        )
