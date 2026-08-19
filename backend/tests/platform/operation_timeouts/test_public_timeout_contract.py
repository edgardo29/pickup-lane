from __future__ import annotations

import ast
import asyncio
import json
from pathlib import Path

import pytest

import backend.observability.timeouts as timeout_module
from backend.observability.correlation import (
    CORRELATION_ID_HEADER,
    reset_correlation_id,
    set_correlation_id,
)
from backend.observability.http_errors import handle_unexpected_exception
from backend.observability.timeouts import (
    DATABASE_TIMEOUT_CODE,
    DATABASE_TIMEOUT_DETAIL,
    DEPENDENCY_MUTATION_TIMEOUT_UNKNOWN_CODE,
    DEPENDENCY_MUTATION_TIMEOUT_UNKNOWN_DETAIL,
    DEPENDENCY_READ_TIMEOUT_CODE,
    DEPENDENCY_READ_TIMEOUT_DETAIL,
    DatabaseTimeoutError,
    DependencyMutationTimeoutUnknownError,
    DependencyReadTimeoutError,
    is_cancellation,
    is_timeout_like_exception,
    re_raise_if_cancellation,
)
from backend.services.stripe_service import _call_stripe_mutation, _call_stripe_read

pytestmark = pytest.mark.no_db_cleanup

_REPO_ROOT = Path(__file__).resolve().parents[4]
_CORRELATION_ID = "123e4567-e89b-42d3-a456-426614174000"
_SENSITIVE_MARKERS = (
    "postgresql://private_user:private_pass@example.invalid/db",
    "Bearer synthetic-token",
    "sk_test_secret",
    "pi_private",
    "user_private",
    "venues/private-object-key.jpg",
    "Authorization: Bearer private-request-header-sentinel",
    "submitted_request_content=private-form-value",
    "raw provider exception carried pi_raw_private_identifier",
    "Traceback",
    "DATABASE_URL",
    "internal diagnostic stack frame",
)


def _timeout_response(exc: Exception) -> tuple[int, dict[str, object], str]:
    token = set_correlation_id(_CORRELATION_ID)
    try:
        request = {
            "headers": {
                "authorization": "Bearer private-request-header-sentinel",
            },
            "submitted": "submitted_request_content=private-form-value",
        }
        response = asyncio.run(handle_unexpected_exception(request, exc))
    finally:
        reset_correlation_id(token)
    return response.status_code, json.loads(response.body), response.headers[CORRELATION_ID_HEADER]


@pytest.mark.requirement("WS02-04C1-R6")
@pytest.mark.parametrize(
    ("exc", "code", "message", "detail", "details"),
    [
        (
            DependencyReadTimeoutError(
                provider_kind="stripe",
                operation="stripe.payment_intent.retrieve",
            ),
            DEPENDENCY_READ_TIMEOUT_CODE,
            "Dependency read timed out.",
            DEPENDENCY_READ_TIMEOUT_DETAIL,
            {
                "outcome": "retry_later",
                "timeout_class": "dependency_read_timeout",
            },
        ),
        (
            DependencyMutationTimeoutUnknownError(
                provider_kind="stripe",
                operation="stripe.payment_intent.confirm",
            ),
            DEPENDENCY_MUTATION_TIMEOUT_UNKNOWN_CODE,
            "Dependency mutation outcome is unknown.",
            DEPENDENCY_MUTATION_TIMEOUT_UNKNOWN_DETAIL,
            {
                "outcome": "unknown",
                "timeout_class": "dependency_mutation_timeout",
            },
        ),
        (
            DatabaseTimeoutError(timeout_kind="statement"),
            DATABASE_TIMEOUT_CODE,
            "Database operation timed out.",
            DATABASE_TIMEOUT_DETAIL,
            {
                "outcome": "retry_later",
                "timeout_class": "database_timeout",
                "timeout_kind": "statement",
            },
        ),
    ],
)
def test_public_timeout_errors_return_safe_503_contracts(
    exc: Exception,
    code: str,
    message: str,
    detail: str,
    details: dict[str, str],
) -> None:
    try:
        raise exc from RuntimeError(" ".join(_SENSITIVE_MARKERS))
    except Exception as raised:
        status_code, body, correlation_id = _timeout_response(raised)

    rendered = json.dumps(body, sort_keys=True)

    assert status_code == 503
    assert correlation_id == _CORRELATION_ID
    assert body["code"] == code
    assert body["message"] == message
    assert body["detail"] == detail
    assert body["correlation_id"] == _CORRELATION_ID
    assert body["details"] == details
    for marker in _SENSITIVE_MARKERS:
        assert marker not in rendered


@pytest.mark.requirement("WS02-04C1-R6")
def test_timeout_telemetry_labels_are_bounded_and_safe() -> None:
    read_error = DependencyReadTimeoutError(
        provider_kind="r2",
        operation="r2.metadata.head",
    )
    mutation_error = DependencyMutationTimeoutUnknownError(
        provider_kind="firebase",
        operation="firebase.user.delete",
    )
    database_error = DatabaseTimeoutError(timeout_kind="lock")

    assert read_error.contract.telemetry_labels == {
        "error_code": DEPENDENCY_READ_TIMEOUT_CODE,
        "operation": "r2.metadata.head",
        "outcome": "retry_later",
        "provider_kind": "r2",
    }
    assert mutation_error.contract.telemetry_labels == {
        "error_code": DEPENDENCY_MUTATION_TIMEOUT_UNKNOWN_CODE,
        "operation": "firebase.user.delete",
        "outcome": "unknown",
        "provider_kind": "firebase",
    }
    assert database_error.contract.telemetry_labels == {
        "error_code": DATABASE_TIMEOUT_CODE,
        "operation": "database.timeout",
        "outcome": "retry_later",
        "resource_kind": "database",
    }


@pytest.mark.requirement("WS02-04C1-R7")
def test_cancellation_is_distinct_from_timeout_and_is_re_raised() -> None:
    cancellation = asyncio.CancelledError()

    assert is_cancellation(cancellation)
    assert not is_timeout_like_exception(cancellation)
    with pytest.raises(asyncio.CancelledError):
        re_raise_if_cancellation(cancellation)


@pytest.mark.requirement("WS02-04C1-R7")
def test_timeout_helpers_do_not_catch_base_exception() -> None:
    tree = ast.parse((_REPO_ROOT / "backend" / "observability" / "timeouts.py").read_text())
    caught_names = {
        handler.type.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Try)
        for handler in node.handlers
        if isinstance(handler.type, ast.Name)
    }

    assert "BaseException" not in caught_names


@pytest.mark.requirement("WS02-04C1-R7")
@pytest.mark.parametrize("wrapper", [_call_stripe_read, _call_stripe_mutation])
def test_representative_provider_wrappers_do_not_convert_cancellation(wrapper) -> None:
    def cancelled_call() -> None:
        raise asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        wrapper("payment_intent.confirm", cancelled_call)
