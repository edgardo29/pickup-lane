import ipaddress
import os
import socket
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from backend.settings import reset_settings_cache
from backend.tests.support.environment_safety import (
    EnvironmentSafetyError,
    assert_cleanup_table_inventory_complete,
    install_test_network_guard,
    validate_dedicated_test_database_url,
    validate_local_test_connection_identity,
)

# Keep this list in dependency order for cleanup: child tables first, then the
# parent tables they reference.
TEST_TABLES = (
    "durable_job_events",
    "durable_worker_heartbeats",
    "durable_jobs",
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
_NETWORK_GUARD_RESTORE = None
ORDINARY_TEST_PROVIDER_ENVIRONMENT_NAMES = frozenset(
    {
        "BACKEND_PROVIDER_CONTRACT_MODE",
        "FIREBASE_ADMIN_CREDENTIALS",
        "FIREBASE_ADMIN_CREDENTIALS_JSON",
        "R2_ACCESS_KEY_ID",
        "R2_ACCOUNT_ID",
        "R2_BUCKET_NAME",
        "R2_ENDPOINT_URL",
        "R2_SECRET_ACCESS_KEY",
        "R2_TEST_ACCESS_KEY_ID",
        "R2_TEST_ACCOUNT_ID",
        "R2_TEST_BUCKET_NAME",
        "R2_TEST_ENDPOINT_URL",
        "R2_TEST_SECRET_ACCESS_KEY",
    }
)
ALWAYS_REMOVED_TEST_ENVIRONMENT_NAMES = frozenset(
    {
        "AWS_ACCESS_KEY_ID",
        "AWS_DEFAULT_PROFILE",
        "AWS_PROFILE",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
    }
)


def pytest_ignore_collect(collection_path, config) -> bool:
    del config
    try:
        relative = Path(str(collection_path)).resolve().relative_to(
            (Path(__file__).resolve().parent / "provider_contract" / "r2").resolve()
        )
    except ValueError:
        return False
    del relative
    return os.getenv("BACKEND_PROVIDER_CONTRACT_MODE") != "1"


def _install_synthetic_backend_test_settings(*, provider_contract_mode: bool) -> None:
    if os.environ.get("APP_ENV") not in {"ci", "test"}:
        os.environ["APP_ENV"] = "test"
    os.environ.update(
        {
            "ENABLE_STRIPE_PAYMENTS": "false",
            "FIREBASE_APP_CHECK_MODE": "disabled",
            "FIREBASE_PROJECT_ID": "pickup-lane-synthetic",
            "INBOX_TOKEN_SECRET": "synthetic-inbox-test-token",
            "STRIPE_CURRENCY": "USD",
            "STRIPE_PUBLISHABLE_KEY": "synthetic-stripe-publishable-key",
            "STRIPE_SECRET_KEY": "synthetic-stripe-secret-key",
            "STRIPE_WEBHOOK_SECRET": "synthetic-stripe-webhook-secret",
        }
    )
    for name in ALWAYS_REMOVED_TEST_ENVIRONMENT_NAMES:
        os.environ.pop(name, None)
    if not provider_contract_mode:
        for name in ORDINARY_TEST_PROVIDER_ENVIRONMENT_NAMES:
            os.environ.pop(name, None)


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

    _NETWORK_GUARD_RESTORE = install_test_network_guard(database_url)


def _r2_socket_address_allowed(
    address,
    *,
    expected_hostname: str,
    allowed_addresses: set[str],
) -> bool:
    if not isinstance(address, tuple) or len(address) < 2:
        return False
    host, port = address[0], address[1]
    if port != 443 or not isinstance(host, str) or not allowed_addresses:
        return False
    if host.rstrip(".").lower() == expected_hostname:
        return True
    try:
        normalized_ip = str(ipaddress.ip_address(host.split("%", 1)[0]))
    except ValueError:
        return False
    return normalized_ip in allowed_addresses


def _install_r2_provider_contract_network_guard(endpoint_url: str) -> None:
    global _NETWORK_GUARD_RESTORE

    parsed = urlsplit(endpoint_url)
    if parsed.scheme != "https" or parsed.hostname is None or parsed.port is not None:
        raise pytest.UsageError("Invalid isolated R2 provider-contract endpoint.")
    allowed_addresses = {
        address[4][0]
        for address in socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
    }
    expected_hostname = parsed.hostname.rstrip(".").lower()
    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex
    original_create_connection = socket.create_connection

    def is_allowed(address) -> bool:
        return _r2_socket_address_allowed(
            address,
            expected_hostname=expected_hostname,
            allowed_addresses=allowed_addresses,
        )

    def guarded_connect(socket_instance, address):
        if not is_allowed(address):
            raise OSError("R2 contract network access is restricted.")
        return original_connect(socket_instance, address)

    def guarded_connect_ex(socket_instance, address):
        if not is_allowed(address):
            return 1
        return original_connect_ex(socket_instance, address)

    def guarded_create_connection(address, *args, **kwargs):
        if not is_allowed(address):
            raise OSError("R2 contract network access is restricted.")
        return original_create_connection(address, *args, **kwargs)

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
    provider_contract_mode = os.getenv("BACKEND_PROVIDER_CONTRACT_MODE") == "1"
    _install_synthetic_backend_test_settings(
        provider_contract_mode=provider_contract_mode
    )
    reset_settings_cache()
    database_url = os.getenv("DATABASE_URL", "")
    try:
        if provider_contract_mode:
            _install_r2_provider_contract_network_guard(os.environ["R2_ENDPOINT_URL"])
        else:
            _install_backend_network_guard(database_url)
        if database_url and not provider_contract_mode:
            _validate_backend_test_environment(database_url)
    except EnvironmentSafetyError as exc:
        raise pytest.UsageError(str(exc)) from exc


def pytest_sessionfinish(session, exitstatus) -> None:
    del session, exitstatus
    reset_settings_cache()
    _restore_backend_network_guard()


def _test_uses_database(request: pytest.FixtureRequest) -> bool:
    if os.getenv("BACKEND_PROVIDER_CONTRACT_MODE") == "1":
        return False
    if request.node.get_closest_marker("no_db_cleanup"):
        return False
    return not request.node.get_closest_marker("migration_lifecycle")


def _truncate_test_tables(connection, table_names: str) -> None:
    # Cleanup is test-database maintenance, not an application query. Keep the
    # session lock timeout as the bounded guard against leaked transactions,
    # but do not let the application statement timeout cancel a large cascade
    # and contaminate every test that follows.
    connection.execute(text("SET LOCAL statement_timeout = 0"))
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
        target = validate_dedicated_test_database_url(database_url)
    except EnvironmentSafetyError as exc:
        raise pytest.UsageError(str(exc)) from exc

    from backend.database import engine

    table_names = ", ".join(TEST_TABLES)

    with engine.connect() as connection:
        validate_local_test_connection_identity(
            connection, target.database_name, target.port
        )
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
