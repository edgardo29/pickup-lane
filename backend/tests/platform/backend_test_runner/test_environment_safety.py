from __future__ import annotations

import socket
import sys
from pathlib import Path

import pytest

import backend.tests.conftest as backend_conftest
from backend.settings import reset_settings_cache
from backend.tests.support.environment_safety import (
    DEDICATED_MIGRATION_TEST_DATABASE_NAME,
    DEDICATED_TEST_DATABASE_NAME,
    MODEL_MODULE_FILE_EXCLUSIONS,
    NETWORK_BLOCKED_MESSAGE,
    EnvironmentSafetyError,
    assert_cleanup_table_inventory_complete,
    build_allowed_database_network,
    database_socket_allowed,
    discover_model_module_names,
    guard_socket_connect,
    guard_socket_connect_ex,
    guard_socket_create_connection,
    install_test_network_guard,
    isolated_test_subprocess_environment,
    registered_sqlalchemy_table_names,
    socket_address_allowed,
    validate_dedicated_test_database_url,
    validate_migration_test_database_urls,
)

SAFE_DATABASE_URL = (
    "postgresql+psycopg://postgres:postgres@localhost:5432/"
    f"{DEDICATED_TEST_DATABASE_NAME}"
)
SAFE_DATABASE_HOST_URL = (
    "postgresql+psycopg://postgres:postgres@test-db.local:5544/"
    f"{DEDICATED_TEST_DATABASE_NAME}"
)
SAFE_MIGRATION_DATABASE_URL = (
    "postgresql+psycopg://postgres:postgres@localhost:5432/"
    f"{DEDICATED_MIGRATION_TEST_DATABASE_NAME}"
)
SAFE_MIGRATION_DATABASE_HOST_URL = (
    "postgresql+psycopg://postgres:postgres@test-db.local:5544/"
    f"{DEDICATED_MIGRATION_TEST_DATABASE_NAME}"
)


pytestmark = [
    pytest.mark.no_db_cleanup,
    pytest.mark.pass_provenance('EN-01'),
]


@pytest.fixture(autouse=True)
def safe_database_url_for_model_imports(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", SAFE_DATABASE_URL)
    reset_settings_cache()
    yield
    reset_settings_cache()


@pytest.fixture(scope="session")
def session_level_network_guard_error():
    probe_socket = socket.socket()
    try:
        with pytest.raises(EnvironmentSafetyError) as exc_info:
            probe_socket.connect(("api.stripe.com", 443))
        return str(exc_info.value)
    finally:
        probe_socket.close()


def _fake_database_resolver(host, port, *args, **kwargs):
    del host, args, kwargs
    return [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.0.2.10", port)),
        (socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("2001:db8::10", port, 0, 0)),
    ]


def _fake_allowed_network():
    return build_allowed_database_network(
        SAFE_DATABASE_HOST_URL,
        resolver=_fake_database_resolver,
    )


def _remove_registered_table(table_name: str) -> None:
    from backend.database_metadata import Base

    table = Base.metadata.tables.get(table_name)
    if table is not None:
        Base.metadata.remove(table)


def _drop_modules_with_prefix(prefix: str) -> None:
    for module_name in list(sys.modules):
        if module_name == prefix or module_name.startswith(f"{prefix}."):
            del sys.modules[module_name]


def _write_temp_model_package(
    tmp_path: Path,
    *,
    package_name: str,
    module_name: str,
    table_name: str,
) -> None:
    package_dir = tmp_path / package_name
    package_dir.mkdir()
    (package_dir / "__init__.py").write_text("# temporary model package\n")
    (package_dir / f"{module_name}.py").write_text(
        "from sqlalchemy import Column, Integer\n"
        "from backend.database_metadata import Base\n\n"
        "class TemporaryUnimportedModel(Base):\n"
        f"    __tablename__ = {table_name!r}\n"
        "    id = Column(Integer, primary_key=True)\n"
    )


@pytest.mark.parametrize(
    "database_url",
    [
        f"postgresql://postgres:postgres@localhost:5432/{DEDICATED_TEST_DATABASE_NAME}",
        f"postgresql+psycopg://postgres:postgres@localhost:5432/{DEDICATED_TEST_DATABASE_NAME}",
        (
            "postgresql+psycopg://postgres:postgres@localhost:5432/"
            f"{DEDICATED_TEST_DATABASE_NAME}?sslmode=disable"
        ),
        f"postgresql+psycopg://postgres:postgres@127.0.0.1:5432/{DEDICATED_TEST_DATABASE_NAME}",
        f"postgresql+psycopg://postgres:postgres@[::1]:5432/{DEDICATED_TEST_DATABASE_NAME}",
        (
            "postgresql+psycopg://user%40example:p%2Fss@localhost:5432/"
            f"{DEDICATED_TEST_DATABASE_NAME}"
        ),
    ],
)
def test_accepts_repository_dedicated_postgresql_database_url_forms(database_url: str):
    parsed = validate_dedicated_test_database_url(database_url)

    assert parsed.drivername == "postgresql" or parsed.drivername.startswith("postgresql+")
    assert parsed.database_name == DEDICATED_TEST_DATABASE_NAME
    assert parsed.host
    assert parsed.port > 0


@pytest.mark.parametrize(
    "database_url",
    [
        "postgresql+psycopg://postgres:postgres@localhost:5432/pickup_lane_db_dev",
        "postgresql+psycopg://postgres:postgres@localhost:5432/pickup_lane_staging_db",
        "postgresql+psycopg://postgres:postgres@localhost:5432/pickup_lane_production_db",
        "postgresql+psycopg://postgres:postgres@localhost:5432/pickup_lane_test_db_backup",
        "postgresql+psycopg://postgres:postgres@localhost:5432/test",
        "postgresql+psycopg://postgres:postgres@localhost:5432/pickup_lane_prod_test_db",
        "postgresql+psycopg://postgres:postgres@localhost:5432/",
        "postgresql+psycopg:///pickup_lane_test_db",
        "postgresql+psycopg://postgres:postgres@localhost:5432/pickup_lane_test_db%20",
        "postgresql+psycopg://postgres:postgres@localhost:5432/pickup%5Flane%5Ftest%5Fdb",
        "sqlite:///pickup_lane_test_db",
        "mysql://postgres:postgres@localhost:5432/pickup_lane_test_db",
        "postgres://postgres:postgres@localhost:5432/pickup_lane_test_db",
        "not-a-database-url",
    ],
)
def test_rejects_unsafe_ambiguous_or_non_postgresql_database_urls(database_url: str):
    with pytest.raises(EnvironmentSafetyError):
        validate_dedicated_test_database_url(database_url)


def test_accepts_separate_migration_lifecycle_database_on_same_test_endpoint():
    targets = validate_migration_test_database_urls(
        SAFE_DATABASE_URL,
        SAFE_MIGRATION_DATABASE_URL,
    )

    assert targets.application_database.database_name == DEDICATED_TEST_DATABASE_NAME
    assert (
        targets.migration_database.database_name
        == DEDICATED_MIGRATION_TEST_DATABASE_NAME
    )
    assert targets.application_database.host == targets.migration_database.host
    assert targets.application_database.port == targets.migration_database.port


@pytest.mark.parametrize(
    "migration_database_url",
    [
        SAFE_DATABASE_URL,
        (
            "postgresql+psycopg://postgres:postgres@localhost:5432/"
            "pickup_lane_migration_test_db_backup"
        ),
        SAFE_MIGRATION_DATABASE_HOST_URL,
        (
            "postgresql+psycopg://postgres:postgres@localhost:5544/"
            f"{DEDICATED_MIGRATION_TEST_DATABASE_NAME}"
        ),
    ],
)
def test_rejects_unsafe_or_cross_endpoint_migration_lifecycle_database(
    migration_database_url: str,
):
    with pytest.raises(EnvironmentSafetyError):
        validate_migration_test_database_urls(
            SAFE_DATABASE_URL,
            migration_database_url,
        )


def test_session_validation_rejects_unsafe_database_before_cleanup(monkeypatch):
    cleanup_calls: list[str] = []

    def fail_if_called(*_args, **_kwargs):
        cleanup_calls.append("called")

    monkeypatch.setattr(
        backend_conftest,
        "assert_cleanup_table_inventory_complete",
        fail_if_called,
    )

    with pytest.raises(EnvironmentSafetyError):
        backend_conftest._validate_backend_test_environment(
            "postgresql+psycopg://postgres:postgres@localhost:5432/pickup_lane_db_dev"
        )

    assert cleanup_calls == []


def test_discovers_all_existing_backend_model_modules():
    import backend.models as backend_models

    model_path = Path(next(iter(backend_models.__path__)))
    expected_modules = tuple(
        f"backend.models.{path.stem}"
        for path in sorted(model_path.glob("*_model.py"), key=lambda candidate: candidate.name)
    )

    assert discover_model_module_names() == expected_modules


def test_unexpected_non_model_python_file_requires_explicit_exclusion(
    monkeypatch,
    tmp_path,
):
    package_name = "temporary_non_model_package"
    package_dir = tmp_path / package_name
    package_dir.mkdir()
    (package_dir / "__init__.py").write_text("# temporary package\n")
    (package_dir / "helpers.py").write_text("VALUE = 1\n")

    monkeypatch.syspath_prepend(str(tmp_path))
    _drop_modules_with_prefix(package_name)

    with pytest.raises(EnvironmentSafetyError):
        discover_model_module_names(package_name)

    exclusions = {
        **MODEL_MODULE_FILE_EXCLUSIONS,
        "helpers.py": "Temporary support module used to prove explicit exclusions.",
    }
    assert discover_model_module_names(package_name, excluded_files=exclusions) == ()


def test_model_module_exclusions_require_documented_reason():
    with pytest.raises(EnvironmentSafetyError):
        discover_model_module_names(
            "backend.models",
            excluded_files={"__init__.py": ""},
        )


def test_unimported_model_module_cannot_evade_cleanup_inventory(
    monkeypatch,
    tmp_path,
):
    package_name = "temporary_unimported_models"
    table_name = "temporary_unimported_inventory_table"

    _write_temp_model_package(
        tmp_path,
        package_name=package_name,
        module_name="hidden_table_model",
        table_name=table_name,
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    _drop_modules_with_prefix(package_name)

    try:
        registered_tables = registered_sqlalchemy_table_names(model_package=package_name)

        assert table_name in registered_tables
        with pytest.raises(EnvironmentSafetyError) as exc_info:
            assert_cleanup_table_inventory_complete(
                backend_conftest.TEST_TABLES,
                excluded_tables=backend_conftest.CLEANUP_TABLE_EXCLUSIONS,
                registered_tables=registered_tables,
            )
        assert table_name in str(exc_info.value)
    finally:
        _remove_registered_table(table_name)
        _drop_modules_with_prefix(package_name)


def test_cleanup_inventory_detects_missing_registered_table():
    with pytest.raises(EnvironmentSafetyError) as exc_info:
        assert_cleanup_table_inventory_complete(
            ("users",),
            registered_tables={"users", "new_domain_table"},
        )

    assert "new_domain_table" in str(exc_info.value)


def test_cleanup_inventory_requires_documented_exclusion_reason():
    with pytest.raises(EnvironmentSafetyError) as exc_info:
        assert_cleanup_table_inventory_complete(
            ("users",),
            excluded_tables={"append_only_audit_log": ""},
            registered_tables={"users", "append_only_audit_log"},
        )

    assert "requires a documented reason" in str(exc_info.value)


def test_cleanup_inventory_currently_covers_registered_sqlalchemy_tables(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", SAFE_DATABASE_URL)

    assert_cleanup_table_inventory_complete(
        backend_conftest.TEST_TABLES,
        excluded_tables=backend_conftest.CLEANUP_TABLE_EXCLUSIONS,
        registered_tables=registered_sqlalchemy_table_names(),
    )


def test_configured_test_database_socket_access_is_permitted():
    allowed_network = _fake_allowed_network()

    assert socket_address_allowed(("test-db.local", 5544), allowed_network)
    assert socket_address_allowed(("192.0.2.10", 5544), allowed_network)
    assert socket_address_allowed(("2001:db8::10", 5544, 0, 0), allowed_network)
    assert database_socket_allowed(("127.0.0.1", 5432), SAFE_DATABASE_URL)


@pytest.mark.parametrize(
    "address",
    [
        ("example.com", 80),
        ("203.0.113.25", 443),
        ("api.stripe.com", 443),
        ("firebase.googleapis.com", 443),
        ("example.r2.cloudflarestorage.com", 443),
        ("smtp.example.com", 587),
        ("test-db.local", 5545),
        ("other-db.local", 5544),
    ],
)
def test_external_network_and_provider_addresses_are_blocked(address):
    allowed_network = _fake_allowed_network()
    calls: list[object] = []

    def original_connect(_socket, original_address):
        calls.append(original_address)

    with pytest.raises(EnvironmentSafetyError) as exc_info:
        guard_socket_connect(original_connect, allowed_network, object(), address)

    assert NETWORK_BLOCKED_MESSAGE in str(exc_info.value)
    assert calls == []


def test_configured_test_database_connect_uses_original_socket_call():
    allowed_network = _fake_allowed_network()
    calls: list[object] = []

    def original_connect(_socket, original_address):
        calls.append(original_address)
        return "connected"

    result = guard_socket_connect(
        original_connect,
        allowed_network,
        object(),
        ("test-db.local", 5544),
    )

    assert result == "connected"
    assert calls == [("test-db.local", 5544)]


def test_configured_resolved_database_ip_uses_original_socket_call():
    allowed_network = _fake_allowed_network()
    calls: list[object] = []

    def original_connect(_socket, original_address):
        calls.append(original_address)
        return "connected"

    result = guard_socket_connect(
        original_connect,
        allowed_network,
        object(),
        ("192.0.2.10", 5544),
    )

    assert result == "connected"
    assert calls == [("192.0.2.10", 5544)]


def test_connect_ex_guard_blocks_external_network_before_provider_contact():
    allowed_network = _fake_allowed_network()
    calls: list[object] = []

    def original_connect_ex(_socket, original_address):
        calls.append(original_address)
        return 0

    with pytest.raises(EnvironmentSafetyError):
        guard_socket_connect_ex(
            original_connect_ex,
            allowed_network,
            object(),
            ("api.stripe.com", 443),
        )

    assert calls == []


def test_create_connection_guard_blocks_external_network_before_provider_contact():
    allowed_network = _fake_allowed_network()
    calls: list[object] = []

    def original_create_connection(original_address, *args, **kwargs):
        calls.append((original_address, args, kwargs))
        return object()

    with pytest.raises(EnvironmentSafetyError):
        guard_socket_create_connection(
            original_create_connection,
            allowed_network,
            ("api.stripe.com", 443),
            timeout=1,
        )

    assert calls == []


def test_create_connection_guard_allows_configured_database_endpoint():
    allowed_network = _fake_allowed_network()
    calls: list[object] = []
    connected = object()

    def original_create_connection(original_address, *args, **kwargs):
        calls.append((original_address, args, kwargs))
        return connected

    result = guard_socket_create_connection(
        original_create_connection,
        allowed_network,
        ("test-db.local", 5544),
        timeout=1,
    )

    assert result is connected
    assert calls == [(("test-db.local", 5544), (), {"timeout": 1})]


def test_network_guard_is_active_for_session_scoped_fixture(
    session_level_network_guard_error,
):
    assert NETWORK_BLOCKED_MESSAGE in session_level_network_guard_error


def test_isolated_subprocess_environment_drops_ambient_credentials_and_options():
    child = isolated_test_subprocess_environment(
        {
            "PATH": "/synthetic/bin",
            "DATABASE_URL": SAFE_DATABASE_URL,
            "PYTEST_ADDOPTS": "-k unsafe",
            "R2_SECRET_ACCESS_KEY": "application-r2-secret",
            "R2_TEST_SECRET_ACCESS_KEY": "provider-r2-secret",
            "UNRELATED_SECRET": "unrelated-secret",
        },
        overrides={"DATABASE_URL": SAFE_DATABASE_URL},
    )

    assert child["APP_ENV"] == "test"
    assert child["PATH"] == "/synthetic/bin"
    assert child["DATABASE_URL"] == SAFE_DATABASE_URL
    assert child["CORS_ALLOWED_ORIGINS"] == (
        "http://localhost:5173,http://127.0.0.1:5173"
    )
    assert child["ENABLE_DB_HEALTH"] == "true"
    assert child["STRIPE_SECRET_KEY"] == "synthetic-stripe-secret-key"
    assert "PYTEST_ADDOPTS" not in child
    assert "R2_SECRET_ACCESS_KEY" not in child
    assert "R2_TEST_SECRET_ACCESS_KEY" not in child
    assert "UNRELATED_SECRET" not in child


def test_install_test_network_guard_blocks_external_access_and_restores(
    monkeypatch: pytest.MonkeyPatch,
):
    def original_connect(_socket, _address):
        return "connected"

    def original_connect_ex(_socket, _address):
        return 0

    def original_create_connection(_address, *_args, **_kwargs):
        return object()

    monkeypatch.setattr(socket.socket, "connect", original_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", original_connect_ex)
    monkeypatch.setattr(socket, "create_connection", original_create_connection)

    restore = install_test_network_guard()
    try:
        with pytest.raises(EnvironmentSafetyError, match="blocked external network"):
            socket.create_connection(("api.stripe.com", 443))
    finally:
        restore()

    assert socket.socket.connect is original_connect
    assert socket.socket.connect_ex is original_connect_ex
    assert socket.create_connection is original_create_connection


@pytest.mark.parametrize(
    ("address", "expected"),
    [
        (("abc123.r2.cloudflarestorage.com", 443), True),
        (("ABC123.R2.CLOUDFLARESTORAGE.COM.", 443), True),
        (("192.0.2.25", 443), True),
        (("other.r2.cloudflarestorage.com", 443), False),
        (("abc123.r2.cloudflarestorage.com", 80), False),
        (("192.0.2.26", 443), False),
    ],
)
@pytest.mark.pass_provenance("WS06-02")
def test_r2_provider_contract_network_allows_only_exact_host_or_resolved_address(
    address,
    expected: bool,
):
    assert backend_conftest._r2_socket_address_allowed(
        address,
        expected_hostname="abc123.r2.cloudflarestorage.com",
        allowed_addresses={"192.0.2.25", "2001:db8::25"},
    ) is expected
