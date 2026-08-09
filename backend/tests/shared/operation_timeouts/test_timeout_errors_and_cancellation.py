from __future__ import annotations

import asyncio
import logging
from threading import Event, Thread
import time

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from backend.observability.correlation import CORRELATION_ID_HEADER
from backend.observability.http_errors import (
    CorrelationIdMiddleware,
    register_exception_handlers,
)
from backend.observability.timeouts import (
    DATABASE_TIMEOUT_CODE,
    DEPENDENCY_MUTATION_TIMEOUT_UNKNOWN_CODE,
    DEPENDENCY_READ_TIMEOUT_CODE,
    DatabaseTimeoutError,
    DependencyMutationTimeoutUnknownError,
    DependencyReadTimeoutError,
    cancellation_telemetry_labels,
    is_cancellation,
    re_raise_if_cancellation,
)


pytestmark = pytest.mark.no_db_cleanup


def build_timeout_test_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)
    app.add_middleware(CorrelationIdMiddleware)

    @app.get("/dependency-read-timeout")
    def dependency_read_timeout():
        raise DependencyReadTimeoutError(
            provider_kind="stripe",
            operation="stripe.payment_intent.retrieve",
        )

    @app.get("/dependency-mutation-timeout")
    def dependency_mutation_timeout():
        raise DependencyMutationTimeoutUnknownError(
            provider_kind="stripe",
            operation="stripe.payment_intent.confirm",
        )

    @app.get("/database-timeout")
    def database_timeout():
        raise DatabaseTimeoutError(timeout_kind="statement")

    return app


@pytest.mark.parametrize(
    ("path", "expected_code", "expected_outcome"),
    [
        (
            "/dependency-read-timeout",
            DEPENDENCY_READ_TIMEOUT_CODE,
            "retry_later",
        ),
        (
            "/dependency-mutation-timeout",
            DEPENDENCY_MUTATION_TIMEOUT_UNKNOWN_CODE,
            "unknown",
        ),
        ("/database-timeout", DATABASE_TIMEOUT_CODE, "retry_later"),
    ],
)
def test_timeout_public_errors_are_stable_and_sanitized(
    caplog,
    path: str,
    expected_code: str,
    expected_outcome: str,
):
    app = build_timeout_test_app()

    with caplog.at_level(logging.WARNING, logger="backend.observability.http_errors"):
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get(path)

    body = response.json()
    assert response.status_code == 503
    assert body["code"] == expected_code
    assert body["details"]["outcome"] == expected_outcome
    assert body["correlation_id"] == response.headers[CORRELATION_ID_HEADER]
    assert "Traceback" not in response.text
    assert "private" not in response.text
    assert "Application operation timed out." in caplog.text


def test_cancellation_is_not_an_ordinary_exception_and_propagates():
    cancellation = asyncio.CancelledError()

    assert is_cancellation(cancellation)
    assert not isinstance(cancellation, Exception)
    with pytest.raises(asyncio.CancelledError):
        re_raise_if_cancellation(cancellation)


def test_cancellation_telemetry_labels_are_bounded():
    labels = cancellation_telemetry_labels(operation="stripe.worker.cancelled")

    assert labels == {
        "operation": "stripe.worker.cancelled",
        "outcome": "cancelled",
        "result": "cancelled",
    }


def test_local_timeout_signal_does_not_prove_sync_work_stopped():
    started = Event()
    finished = Event()

    def blocked_sync_work():
        started.set()
        time.sleep(0.05)
        finished.set()

    worker = Thread(target=blocked_sync_work)
    worker.start()
    started.wait(timeout=1)

    timeout_error = DependencyMutationTimeoutUnknownError(
        provider_kind="stripe",
        operation="stripe.payment_intent.confirm",
    )

    assert timeout_error.contract.code == DEPENDENCY_MUTATION_TIMEOUT_UNKNOWN_CODE
    assert timeout_error.contract.details["outcome"] == "unknown"
    assert not finished.is_set()
    worker.join(timeout=1)
    assert finished.is_set()
