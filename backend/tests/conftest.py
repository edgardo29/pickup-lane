import os
import socket
from pathlib import Path

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import text

from backend.settings import reset_settings_cache
from backend.tests.support.environment_safety import (
    EnvironmentSafetyError,
    build_allowed_database_network,
    cleanup_application_tables,
    guard_socket_connect,
    guard_socket_connect_ex,
    guard_socket_create_connection,
    registered_sqlalchemy_tables,
    validate_backend_test_app_env,
    validate_dedicated_test_database_url,
)

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)

TEST_DATABASE_ADVISORY_LOCK_ID = 917_263_514
_NETWORK_GUARD_RESTORE = None


def _install_synthetic_backend_test_settings() -> None:
    os.environ.setdefault("APP_ENV", "test")
    os.environ.setdefault("INBOX_TOKEN_SECRET", "synthetic-inbox-test-token")
    os.environ.setdefault("STRIPE_SECRET_KEY", "synthetic-stripe-secret-key")
    os.environ.setdefault("STRIPE_PUBLISHABLE_KEY", "synthetic-stripe-publishable-key")
    os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "synthetic-stripe-webhook-secret")
    os.environ.setdefault("STRIPE_CURRENCY", "USD")
    os.environ.setdefault("FIREBASE_PROJECT_ID", "pickup-lane-synthetic")


def _validate_backend_test_environment(database_url: str) -> None:
    validate_backend_test_app_env(os.getenv("APP_ENV"))
    validate_dedicated_test_database_url(database_url)
    registered_sqlalchemy_tables()


def _install_backend_network_guard(database_url: str) -> None:
    global _NETWORK_GUARD_RESTORE

    if _NETWORK_GUARD_RESTORE is not None:
        return

    allowed_network = build_allowed_database_network(database_url)
    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex
    original_create_connection = socket.create_connection

    def guarded_connect(socket_instance, address):
        return guard_socket_connect(
            original_connect,
            allowed_network,
            socket_instance,
            address,
        )

    def guarded_connect_ex(socket_instance, address):
        return guard_socket_connect_ex(
            original_connect_ex,
            allowed_network,
            socket_instance,
            address,
        )

    def guarded_create_connection(address, *args, **kwargs):
        return guard_socket_create_connection(
            original_create_connection,
            allowed_network,
            address,
            *args,
            **kwargs,
        )

    socket.socket.connect = guarded_connect
    socket.socket.connect_ex = guarded_connect_ex
    socket.create_connection = guarded_create_connection

    def restore_network_guard() -> None:
        socket.socket.connect = original_connect
        socket.socket.connect_ex = original_connect_ex
        socket.create_connection = original_create_connection

    _NETWORK_GUARD_RESTORE = restore_network_guard


def _restore_backend_network_guard() -> None:
    global _NETWORK_GUARD_RESTORE

    if _NETWORK_GUARD_RESTORE is None:
        return

    restore_network_guard = _NETWORK_GUARD_RESTORE
    _NETWORK_GUARD_RESTORE = None
    restore_network_guard()


def pytest_sessionstart(session) -> None:
    del session
    _install_synthetic_backend_test_settings()
    reset_settings_cache()
    database_url = os.getenv("DATABASE_URL", "")
    try:
        validate_backend_test_app_env(os.getenv("APP_ENV"))
        _install_backend_network_guard(database_url)
        if database_url:
            _validate_backend_test_environment(database_url)
    except EnvironmentSafetyError as exc:
        raise pytest.UsageError(str(exc)) from exc


def pytest_sessionfinish(session, exitstatus) -> None:
    del session, exitstatus
    reset_settings_cache()
    _restore_backend_network_guard()


def _test_uses_database(request: pytest.FixtureRequest) -> bool:
    if request.node.get_closest_marker("no_db_cleanup"):
        return False
    return True


@pytest.fixture(scope="session")
def client() -> TestClient:
    database_url = os.getenv("DATABASE_URL", "")

    if not database_url:
        pytest.skip("DATABASE_URL is required for backend integration tests.")

    try:
        validate_backend_test_app_env(os.getenv("APP_ENV"))
        validate_dedicated_test_database_url(database_url)
    except EnvironmentSafetyError as exc:
        raise pytest.UsageError(str(exc)) from exc

    from backend.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def enable_stripe_payments_for_existing_tests(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ENABLE_STRIPE_PAYMENTS", "true")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "synthetic-stripe-secret-key")
    monkeypatch.setenv("STRIPE_PUBLISHABLE_KEY", "synthetic-stripe-publishable-key")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "synthetic-stripe-webhook-secret")
    monkeypatch.setenv("INBOX_TOKEN_SECRET", "synthetic-inbox-test-token")
    reset_settings_cache()
    yield
    reset_settings_cache()


@pytest.fixture(autouse=True)
def clean_database(
    request: pytest.FixtureRequest,
    enable_stripe_payments_for_existing_tests,
):
    if not _test_uses_database(request):
        yield
        return

    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        pytest.skip("DATABASE_URL is required for backend integration tests.")

    try:
        validate_backend_test_app_env(os.getenv("APP_ENV"))
        validate_dedicated_test_database_url(database_url)
    except EnvironmentSafetyError as exc:
        raise pytest.UsageError(str(exc)) from exc

    from backend.database import engine
    from backend.main import app

    with engine.connect() as connection:
        connection.execute(
            text("SELECT pg_advisory_lock(:lock_id)"),
            {"lock_id": TEST_DATABASE_ADVISORY_LOCK_ID},
        )
        connection.commit()

        try:
            app.dependency_overrides.clear()

            # Each test gets a clean database so tests can create the same
            # logical records without leaking state into the next test. The
            # advisory lock keeps shared-DB local runs from truncating while
            # another test request is still reading or writing.
            with connection.begin():
                cleanup_application_tables(connection)

            yield

            app.dependency_overrides.clear()

            # Clean again after the test so a failed test does not leave rows
            # behind for the next local run.
            with connection.begin():
                cleanup_application_tables(connection)
        finally:
            app.dependency_overrides.clear()
            if connection.in_transaction():
                connection.rollback()

            connection.execute(
                text("SELECT pg_advisory_unlock(:lock_id)"),
                {"lock_id": TEST_DATABASE_ADVISORY_LOCK_ID},
            )
            connection.commit()
