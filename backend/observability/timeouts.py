"""Operation-specific timeout and cancellation classification."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from fastapi import status
from sqlalchemy.exc import OperationalError, TimeoutError as SQLAlchemyTimeoutError

from backend.observability.telemetry import validate_telemetry_labels

DEPENDENCY_READ_TIMEOUT_CODE = "API.DEPENDENCY_READ_TIMEOUT"
DEPENDENCY_MUTATION_TIMEOUT_UNKNOWN_CODE = "API.DEPENDENCY_MUTATION_TIMEOUT_UNKNOWN"
DATABASE_TIMEOUT_CODE = "API.DATABASE_TIMEOUT"

DEPENDENCY_READ_TIMEOUT_DETAIL = (
    "Required dependency did not complete in time. Please try again later."
)
DEPENDENCY_MUTATION_TIMEOUT_UNKNOWN_DETAIL = (
    "External operation status was not confirmed. Check current status before retrying."
)
DATABASE_TIMEOUT_DETAIL = (
    "Database operation could not complete within the configured application bound."
)

_TIMEOUT_CLASS_NAMES = frozenset(
    {
        "Timeout",
        "TimeoutError",
        "ReadTimeout",
        "ConnectTimeout",
        "ReadTimeoutError",
        "ConnectTimeoutError",
        "DeadlineExceededError",
    }
)
_DATABASE_TIMEOUT_CLASS_NAMES = frozenset(
    {
        "QueryCanceled",
        "LockNotAvailable",
        "LockNotAvailableError",
    }
)


@dataclass(frozen=True)
class TimeoutContract:
    status_code: int
    code: str
    message: str
    detail: str
    details: Mapping[str, str]
    telemetry_labels: Mapping[str, str]


class PublicTimeoutError(RuntimeError):
    """Base for timeout exceptions with safe public semantics."""

    contract: TimeoutContract


class DependencyReadTimeoutError(PublicTimeoutError):
    """A dependency read/query operation exceeded its app-owned timeout."""

    def __init__(self, *, provider_kind: str, operation: str) -> None:
        self.provider_kind = provider_kind
        self.operation = operation
        self.contract = TimeoutContract(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code=DEPENDENCY_READ_TIMEOUT_CODE,
            message="Dependency read timed out.",
            detail=DEPENDENCY_READ_TIMEOUT_DETAIL,
            details={
                "outcome": "retry_later",
                "timeout_class": "dependency_read_timeout",
            },
            telemetry_labels=validate_telemetry_labels(
                {
                    "error_code": DEPENDENCY_READ_TIMEOUT_CODE,
                    "operation": operation,
                    "outcome": "retry_later",
                    "provider_kind": provider_kind,
                }
            ),
        )
        super().__init__(self.contract.message)


class DependencyMutationTimeoutUnknownError(PublicTimeoutError):
    """A dependency mutation timed out and its provider outcome is unknown."""

    def __init__(self, *, provider_kind: str, operation: str) -> None:
        self.provider_kind = provider_kind
        self.operation = operation
        self.contract = TimeoutContract(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code=DEPENDENCY_MUTATION_TIMEOUT_UNKNOWN_CODE,
            message="Dependency mutation outcome is unknown.",
            detail=DEPENDENCY_MUTATION_TIMEOUT_UNKNOWN_DETAIL,
            details={
                "outcome": "unknown",
                "timeout_class": "dependency_mutation_timeout",
            },
            telemetry_labels=validate_telemetry_labels(
                {
                    "error_code": DEPENDENCY_MUTATION_TIMEOUT_UNKNOWN_CODE,
                    "operation": operation,
                    "outcome": "unknown",
                    "provider_kind": provider_kind,
                }
            ),
        )
        super().__init__(self.contract.message)


class DatabaseTimeoutError(PublicTimeoutError):
    """An app-owned database timeout reached its configured bound."""

    def __init__(self, *, timeout_kind: str = "database") -> None:
        self.timeout_kind = timeout_kind
        self.contract = TimeoutContract(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code=DATABASE_TIMEOUT_CODE,
            message="Database operation timed out.",
            detail=DATABASE_TIMEOUT_DETAIL,
            details={
                "outcome": "retry_later",
                "timeout_class": "database_timeout",
                "timeout_kind": timeout_kind,
            },
            telemetry_labels=validate_telemetry_labels(
                {
                    "error_code": DATABASE_TIMEOUT_CODE,
                    "operation": "database.timeout",
                    "outcome": "retry_later",
                    "resource_kind": "database",
                }
            ),
        )
        super().__init__(self.contract.message)


def is_cancellation(exc: BaseException) -> bool:
    return isinstance(exc, asyncio.CancelledError)


def re_raise_if_cancellation(exc: BaseException) -> None:
    if is_cancellation(exc):
        raise exc


def is_timeout_like_exception(exc: BaseException) -> bool:
    return _exception_chain_contains_class_name(exc, _TIMEOUT_CLASS_NAMES)


def is_database_timeout_exception(exc: BaseException) -> bool:
    if isinstance(exc, SQLAlchemyTimeoutError):
        return True
    if isinstance(exc, OperationalError):
        return _exception_chain_contains_class_name(
            exc,
            _DATABASE_TIMEOUT_CLASS_NAMES,
        )
    return False


def database_timeout_from_exception(exc: BaseException) -> DatabaseTimeoutError | None:
    if isinstance(exc, SQLAlchemyTimeoutError):
        return DatabaseTimeoutError(timeout_kind="pool_wait")
    if isinstance(exc, OperationalError):
        if _exception_chain_contains_class_name(exc, {"LockNotAvailable"}):
            return DatabaseTimeoutError(timeout_kind="lock")
        if _exception_chain_contains_class_name(exc, {"QueryCanceled"}):
            return DatabaseTimeoutError(timeout_kind="statement")
    return None


def cancellation_telemetry_labels(*, operation: str) -> dict[str, str]:
    return validate_telemetry_labels(
        {
            "operation": operation,
            "outcome": "cancelled",
            "result": "cancelled",
        }
    )


def public_timeout_contract(exc: BaseException) -> TimeoutContract | None:
    if isinstance(exc, PublicTimeoutError):
        return exc.contract

    database_timeout = database_timeout_from_exception(exc)
    if database_timeout is not None:
        return database_timeout.contract

    return None


def _exception_chain_contains_class_name(
    exc: BaseException,
    class_names: set[str] | frozenset[str],
) -> bool:
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        class_name = current.__class__.__name__
        if class_name in class_names:
            return True
        current = _next_exception(current)
    return False


def _next_exception(exc: BaseException) -> BaseException | None:
    cause = exc.__cause__
    if cause is not None:
        return cause
    context = exc.__context__
    return context
