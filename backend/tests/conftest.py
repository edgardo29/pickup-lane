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
    assert_cleanup_table_inventory_complete,
    build_allowed_database_network,
    guard_socket_connect,
    guard_socket_connect_ex,
    guard_socket_create_connection,
    validate_dedicated_test_database_url,
)

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)

# Keep this list in dependency order for cleanup: child tables first, then the
# parent tables they reference.
TEST_TABLES = (
    "durable_job_events",
    "durable_worker_heartbeats",
    "durable_jobs",
    "admin_review_case_resolution_references",
    "admin_review_case_events",
    "admin_review_case_notes",
    "admin_content_moderation_findings",
    "admin_review_signals",
    "admin_target_notices",
    "sub_post_chat_reads",
    "sub_post_chat_message_detections",
    "sub_post_chat_messages",
    "sub_post_chats",
    "sub_post_status_history",
    "sub_post_request_status_history",
    "sub_post_requests",
    "sub_post_positions",
    "sub_posts",
    "platform_notice_selected_reads",
    "platform_notice_global_seen_states",
    "platform_notice_recipients",
    "admin_rejected_attempts",
    "support_flags",
    "admin_financial_outcomes",
    "admin_actions",
    "admin_review_cases",
    "platform_notices",
    "money_issue_events",
    "money_issues",
    "game_credit_usage",
    "game_credits",
    "game_chat_reads",
    "game_chat_message_detections",
    "notifications",
    "chat_messages",
    "game_chats",
    "community_game_details",
    "game_status_history",
    "booking_status_history",
    "participant_status_history",
    "refund_events",
    "refunds",
    "host_publish_entitlements",
    "host_publish_fees",
    "community_publish_attempts",
    "payment_compensations",
    "payment_confirmation_attempts",
    "payment_method_operations",
    "payment_events",
    "payments",
    "waitlist_entries",
    "game_participants",
    "booking_policy_acceptances",
    "bookings",
    "user_stats",
    "user_payment_methods",
    "user_settings",
    "venue_images",
    "game_images",
    "games",
    "venue_approval_requests",
    "venues",
    "policy_acceptances",
    "policy_documents",
    "users",
)
CLEANUP_TABLE_EXCLUSIONS: dict[str, str] = {}
TEST_DATABASE_ADVISORY_LOCK_ID = 917_263_514
TEST_DATABASE_CLEANUP_STATEMENT_TIMEOUT_MILLISECONDS = 60_000
NON_DATABASE_TEST_FILES = {
    "test_check_backend_tests.py",
    "test_environment_safety.py",
}
_NETWORK_GUARD_RESTORE = None


def _install_synthetic_backend_test_settings() -> None:
    os.environ.setdefault("APP_ENV", "test")
    os.environ.setdefault("INBOX_TOKEN_SECRET", "synthetic-inbox-test-token")
    os.environ.setdefault("STRIPE_SECRET_KEY", "synthetic-stripe-secret-key")
    os.environ.setdefault("STRIPE_PUBLISHABLE_KEY", "synthetic-stripe-publishable-key")
    os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "synthetic-stripe-webhook-secret")
    os.environ.setdefault("STRIPE_CURRENCY", "USD")
    os.environ.setdefault("FIREBASE_PROJECT_ID", "pickup-lane-synthetic")


def _is_safe_test_database(database_url: str) -> bool:
    try:
        validate_dedicated_test_database_url(database_url)
    except EnvironmentSafetyError:
        return False
    return True


def _validate_backend_test_environment(database_url: str) -> None:
    validate_dedicated_test_database_url(database_url)
    assert_cleanup_table_inventory_complete(
        TEST_TABLES,
        excluded_tables=CLEANUP_TABLE_EXCLUSIONS,
    )


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
    if request.node.get_closest_marker("migration_lifecycle"):
        return False
    path = Path(str(request.node.fspath))
    return path.name not in NON_DATABASE_TEST_FILES


def _truncate_test_tables(connection, table_names: str) -> None:
    # Bulk test cleanup is infrastructure work, not an application request.
    # Keep the ordinary lock timeout so leaked transactions still fail fast.
    connection.execute(
        text("SELECT set_config('statement_timeout', :timeout, true)"),
        {"timeout": str(TEST_DATABASE_CLEANUP_STATEMENT_TIMEOUT_MILLISECONDS)},
    )
    connection.execute(text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE"))


def _clear_main_app_dependency_overrides() -> None:
    import backend.main as main_module

    main_module.app.dependency_overrides.clear()


def _rebuild_shared_test_app():
    # No-DB platform tests may import backend.main while settings are
    # monkeypatched. Rebuild the shared app after those patches are restored so
    # DB-backed tests do not inherit a stale module-level app.
    reset_settings_cache()

    import backend.main as main_module

    main_module.app.dependency_overrides.clear()
    main_module.app = main_module.create_app()
    return main_module.app


@pytest.fixture
def client() -> TestClient:
    database_url = os.getenv("DATABASE_URL", "")

    if not database_url:
        pytest.skip("DATABASE_URL is required for backend integration tests.")

    try:
        validate_dedicated_test_database_url(database_url)
    except EnvironmentSafetyError as exc:
        raise pytest.UsageError(str(exc)) from exc

    app = _rebuild_shared_test_app()

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        _clear_main_app_dependency_overrides()


@pytest.fixture(autouse=True)
def clean_database(
    request: pytest.FixtureRequest,
):
    if not _test_uses_database(request):
        yield
        return

    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        pytest.skip("DATABASE_URL is required for backend integration tests.")

    try:
        validate_dedicated_test_database_url(database_url)
    except EnvironmentSafetyError as exc:
        raise pytest.UsageError(str(exc)) from exc

    from backend.database import engine

    table_names = ", ".join(TEST_TABLES)

    with engine.connect() as connection:
        connection.execute(
            text("SELECT pg_advisory_lock(:lock_id)"),
            {"lock_id": TEST_DATABASE_ADVISORY_LOCK_ID},
        )
        connection.commit()

        try:
            _clear_main_app_dependency_overrides()

            # Each test gets a clean database so tests can create the same
            # logical records without leaking state into the next test. The
            # advisory lock keeps shared-DB local runs from truncating while
            # another test request is still reading or writing.
            with connection.begin():
                _truncate_test_tables(connection, table_names)

            yield

            _clear_main_app_dependency_overrides()

            # Clean again after the test so a failed test does not leave rows
            # behind for the next local run.
            with connection.begin():
                _truncate_test_tables(connection, table_names)
        finally:
            _clear_main_app_dependency_overrides()
            if connection.in_transaction():
                connection.rollback()

            connection.execute(
                text("SELECT pg_advisory_unlock(:lock_id)"),
                {"lock_id": TEST_DATABASE_ADVISORY_LOCK_ID},
            )
            connection.commit()
