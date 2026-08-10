from __future__ import annotations

import socket
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import Column, Integer, MetaData, Table
from sqlalchemy.dialects import postgresql

import backend.tests.conftest as backend_conftest
from backend.tests.support import environment_safety
from backend.tests.support.environment_safety import (
    DEDICATED_TEST_DATABASE_NAME,
    NETWORK_BLOCKED_MESSAGE,
    NON_APPLICATION_CLEANUP_TABLE_EXCLUSIONS,
    EnvironmentSafetyError,
    assert_cleanup_schema_state,
    build_allowed_database_network,
    build_cleanup_truncate_statement,
    cleanup_application_tables,
    cleanup_table_key,
    database_socket_allowed,
    database_table_keys_for_cleanup,
    guard_socket_connect,
    guard_socket_connect_ex,
    guard_socket_create_connection,
    import_model_package,
    registered_sqlalchemy_table_names,
    socket_address_allowed,
    validate_backend_test_app_env,
    validate_dedicated_test_database_url,
)


SAFE_DATABASE_URL = (
    "postgresql+psycopg://localhost:5432/"
    f"{DEDICATED_TEST_DATABASE_NAME}"
)
SAFE_DATABASE_HOST_URL = (
    "postgresql+psycopg://test-db.local:5544/"
    f"{DEDICATED_TEST_DATABASE_NAME}"
)


pytestmark = pytest.mark.no_db_cleanup


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
    for table in environment_safety.registered_sqlalchemy_tables():
        if table.name == table_name:
            table.metadata.remove(table)
            return


def _drop_modules_with_prefix(prefix: str) -> None:
    for module_name in list(sys.modules):
        if module_name == prefix or module_name.startswith(f"{prefix}."):
            del sys.modules[module_name]


def _write_temp_model_package(
    tmp_path: Path,
    *,
    package_name: str,
    table_name: str,
) -> None:
    package_dir = tmp_path / package_name
    package_dir.mkdir()
    (package_dir / "__init__.py").write_text(
        "from .records import TemporaryExportedModel\n\n"
        "__all__ = ('TemporaryExportedModel',)\n"
    )
    (package_dir / "records.py").write_text(
        "from sqlalchemy import Column, Integer\n"
        "from backend.database import Base\n\n"
        "class TemporaryExportedModel(Base):\n"
        f"    __tablename__ = {table_name!r}\n"
        "    id = Column(Integer, primary_key=True)\n"
    )
    (package_dir / "helpers.py").write_text("VALUE = 1\n")


def _metadata_tables(*names: str) -> tuple[Table, ...]:
    metadata = MetaData()
    return tuple(
        Table(name, metadata, Column("id", Integer, primary_key=True))
        for name in names
    )


@pytest.mark.parametrize(
    "app_env",
    [None, "", "local", "ci", "preview", "staging", "production"],
)
def test_backend_test_app_env_must_be_exactly_test(app_env: str | None):
    with pytest.raises(EnvironmentSafetyError):
        validate_backend_test_app_env(app_env)


def test_backend_test_app_env_accepts_test():
    validate_backend_test_app_env("test")


@pytest.mark.parametrize(
    "database_url",
    [
        f"postgresql://localhost:5432/{DEDICATED_TEST_DATABASE_NAME}",
        (
            "postgresql+psycopg://localhost:5432/"
            f"{DEDICATED_TEST_DATABASE_NAME}"
        ),
        (
            "postgresql+psycopg://localhost:5432/"
            f"{DEDICATED_TEST_DATABASE_NAME}?sslmode=disable"
        ),
        (
            "postgresql+psycopg://127.0.0.1:5432/"
            f"{DEDICATED_TEST_DATABASE_NAME}"
        ),
        (
            "postgresql+psycopg://[::1]:5432/"
            f"{DEDICATED_TEST_DATABASE_NAME}"
        ),
        f"postgresql+psycopg://localhost/{DEDICATED_TEST_DATABASE_NAME}",
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
        "postgresql+psycopg://localhost:5432/pickup_lane_db_dev",
        "postgresql+psycopg://localhost:5432/pickup_lane_staging_db",
        "postgresql+psycopg://localhost:5432/pickup_lane_production_db",
        "postgresql+psycopg://localhost:5432/pickup_lane_test_db_backup",
        "postgresql+psycopg://localhost:5432/test",
        "postgresql+psycopg://localhost:5432/pickup_lane_prod_test_db",
        "postgresql+psycopg://localhost:5432/",
        "postgresql+psycopg:///pickup_lane_test_db",
        "postgresql+psycopg://localhost:5432/pickup_lane_test_db%20",
        "postgresql+psycopg://localhost:5432/pickup%5Flane%5Ftest%5Fdb",
        "sqlite:///pickup_lane_test_db",
        "mysql://localhost:5432/pickup_lane_test_db",
        "postgres://localhost:5432/pickup_lane_test_db",
        "not-a-database-url",
    ],
)
def test_rejects_unsafe_ambiguous_or_non_postgresql_database_urls(database_url: str):
    with pytest.raises(EnvironmentSafetyError):
        validate_dedicated_test_database_url(database_url)


def test_root_validation_rejects_app_env_before_database_metadata(monkeypatch):
    metadata_calls: list[str] = []

    def fail_if_called(*_args, **_kwargs):
        metadata_calls.append("called")

    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setattr(backend_conftest, "registered_sqlalchemy_tables", fail_if_called)

    with pytest.raises(EnvironmentSafetyError):
        backend_conftest._validate_backend_test_environment(SAFE_DATABASE_URL)

    assert metadata_calls == []


def test_root_validation_rejects_unsafe_database_before_metadata(monkeypatch):
    metadata_calls: list[str] = []

    def fail_if_called(*_args, **_kwargs):
        metadata_calls.append("called")

    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setattr(backend_conftest, "registered_sqlalchemy_tables", fail_if_called)

    with pytest.raises(EnvironmentSafetyError):
        backend_conftest._validate_backend_test_environment(
            "postgresql+psycopg://localhost:5432/pickup_lane_db_dev"
        )

    assert metadata_calls == []


def test_backend_model_package_import_surface_populates_cleanup_metadata():
    import backend.models as backend_models

    exported_table_names = set()
    for export_name in backend_models.__all__:
        exported_model = getattr(backend_models, export_name)
        table = getattr(exported_model, "__table__", None)
        assert table is not None, export_name
        exported_table_names.add(table.name)

    cleanup_table_names = registered_sqlalchemy_table_names()

    assert exported_table_names
    assert exported_table_names <= cleanup_table_names


def test_model_package_import_controls_cleanup_targets_without_filename_scan(
    monkeypatch,
    tmp_path,
):
    package_name = "temporary_exported_models"
    table_name = "temporary_exported_cleanup_table"

    _write_temp_model_package(
        tmp_path,
        package_name=package_name,
        table_name=table_name,
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    _drop_modules_with_prefix(package_name)

    try:
        assert table_name in registered_sqlalchemy_table_names(model_package=package_name)
    finally:
        _remove_registered_table(table_name)
        _drop_modules_with_prefix(package_name)


def test_model_package_import_failure_is_reported_as_safety_error():
    with pytest.raises(EnvironmentSafetyError):
        import_model_package("missing_cleanup_model_package")


def test_cleanup_targets_are_derived_from_registered_sqlalchemy_metadata():
    table_names = registered_sqlalchemy_table_names()

    assert table_names
    assert "alembic_version" not in table_names
    assert all("." not in table_name for table_name in table_names)


def test_cleanup_schema_state_allows_only_documented_non_application_exclusions():
    assert_cleanup_schema_state(
        metadata_table_keys={"users"},
        database_table_keys={"users", "alembic_version"},
    )

    assert NON_APPLICATION_CLEANUP_TABLE_EXCLUSIONS == {
        "alembic_version": "Alembic migration bookkeeping table; not application data.",
    }


def test_cleanup_schema_state_rejects_application_table_exclusion():
    with pytest.raises(EnvironmentSafetyError) as exc_info:
        assert_cleanup_schema_state(
            metadata_table_keys={"users"},
            database_table_keys={"users"},
            excluded_database_tables={"users": "Do not clean app rows."},
        )

    assert "may not omit SQLAlchemy application table" in str(exc_info.value)


def test_cleanup_schema_state_requires_documented_exclusion_reason():
    with pytest.raises(EnvironmentSafetyError) as exc_info:
        assert_cleanup_schema_state(
            metadata_table_keys={"users"},
            database_table_keys={"users", "append_only_audit_log"},
            excluded_database_tables={"append_only_audit_log": ""},
        )

    assert "requires a documented reason" in str(exc_info.value)


def test_unknown_database_schema_state_fails_safely():
    with pytest.raises(EnvironmentSafetyError) as exc_info:
        assert_cleanup_schema_state(
            metadata_table_keys={"users"},
            database_table_keys={"users", "new_untracked_table"},
        )

    assert "unhandled PostgreSQL table" in str(exc_info.value)
    assert "new_untracked_table" in str(exc_info.value)


def test_missing_metadata_table_in_database_fails_safely():
    with pytest.raises(EnvironmentSafetyError) as exc_info:
        assert_cleanup_schema_state(
            metadata_table_keys={"users", "games"},
            database_table_keys={"users", "alembic_version"},
        )

    assert "missing metadata table" in str(exc_info.value)
    assert "games" in str(exc_info.value)


def test_database_table_key_discovery_uses_metadata_schemas(monkeypatch):
    metadata = MetaData()
    tables = (
        Table("users", metadata, Column("id", Integer, primary_key=True)),
        Table(
            "tenant_records",
            metadata,
            Column("id", Integer, primary_key=True),
            schema="tenant_one",
        ),
    )
    inspected_schemas: list[str | None] = []

    class FakeInspector:
        def get_table_names(self, *, schema=None):
            inspected_schemas.append(schema)
            if schema is None:
                return ["users", "alembic_version"]
            if schema == "tenant_one":
                return ["tenant_records"]
            return []

    monkeypatch.setattr(
        environment_safety,
        "inspect",
        lambda connection: FakeInspector(),
    )

    assert database_table_keys_for_cleanup(object(), tables) == {
        "users",
        "alembic_version",
        "tenant_one.tenant_records",
    }
    assert inspected_schemas == [None, "tenant_one"]


def test_cleanup_truncate_sql_quotes_and_schema_qualifies_targets():
    metadata = MetaData()
    tables = (
        Table("select", metadata, Column("id", Integer, primary_key=True)),
        Table(
            "child table",
            metadata,
            Column("id", Integer, primary_key=True),
            schema="app schema",
        ),
    )

    statement = build_cleanup_truncate_statement(tables, postgresql.dialect())

    assert statement.startswith("TRUNCATE TABLE ")
    assert '"select"' in statement
    assert '"app schema"."child table"' in statement
    assert statement.endswith(" RESTART IDENTITY CASCADE")


def test_cleanup_application_tables_executes_checked_truncate(monkeypatch):
    tables = _metadata_tables("users", "games")
    schema_checks: list[tuple[str, ...]] = []
    executed_sql: list[str] = []

    class FakeConnection:
        dialect = postgresql.dialect()

        def execute(self, statement):
            executed_sql.append(str(statement))

    def fake_schema_check(connection, metadata_tables, *, excluded_database_tables=None):
        del connection, excluded_database_tables
        schema_checks.append(tuple(cleanup_table_key(table) for table in metadata_tables))

    monkeypatch.setattr(
        environment_safety,
        "assert_database_schema_matches_cleanup_metadata",
        fake_schema_check,
    )

    plan = cleanup_application_tables(FakeConnection(), metadata_tables=tables)

    assert schema_checks == [("users", "games")]
    assert executed_sql == [
        'TRUNCATE TABLE "games", "users" RESTART IDENTITY CASCADE',
    ]
    assert plan.table_keys == ("users", "games")


def test_cleanup_application_tables_rejects_empty_metadata_targets(monkeypatch):
    monkeypatch.setattr(
        environment_safety,
        "assert_database_schema_matches_cleanup_metadata",
        lambda *_args, **_kwargs: None,
    )

    with pytest.raises(EnvironmentSafetyError):
        cleanup_application_tables(
            SimpleNamespace(dialect=postgresql.dialect(), execute=lambda statement: None),
            metadata_tables=(),
        )


class _FakeMarkerRequest:
    def __init__(self, marker_name: str | None):
        self.node = self
        self.marker_name = marker_name

    def get_closest_marker(self, marker_name: str):
        if marker_name == self.marker_name:
            return object()
        return None


def test_no_db_cleanup_is_the_only_root_cleanup_bypass():
    assert not backend_conftest._test_uses_database(
        _FakeMarkerRequest("no_db_cleanup")
    )
    assert backend_conftest._test_uses_database(_FakeMarkerRequest(None))


def test_clean_database_runs_before_and_after_cleanup(monkeypatch):
    cleanup_calls: list[str] = []
    cleanup_seen_overrides: list[dict[str, object]] = []
    events: list[tuple[str, object]] = []

    class FakeTransaction:
        def __enter__(self):
            events.append(("begin", len(cleanup_calls)))

        def __exit__(self, exc_type, exc, traceback):
            del exc_type, exc, traceback
            events.append(("end", len(cleanup_calls)))

    class FakeConnection:
        dialect = postgresql.dialect()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            del exc_type, exc, traceback

        def execute(self, statement, params=None):
            events.append(("execute", (str(statement), params)))

        def commit(self):
            events.append(("commit", len(cleanup_calls)))

        def begin(self):
            return FakeTransaction()

        def in_transaction(self):
            return False

    fake_connection = FakeConnection()
    fake_app = SimpleNamespace(dependency_overrides={"existing": object()})
    fake_engine = SimpleNamespace(connect=lambda: fake_connection)

    def fake_cleanup(connection):
        assert connection is fake_connection
        cleanup_seen_overrides.append(dict(fake_app.dependency_overrides))
        cleanup_calls.append("cleanup")

    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", SAFE_DATABASE_URL)
    monkeypatch.setitem(
        sys.modules,
        "backend.database",
        SimpleNamespace(engine=fake_engine),
    )
    monkeypatch.setitem(sys.modules, "backend.main", SimpleNamespace(app=fake_app))
    monkeypatch.setattr(backend_conftest, "cleanup_application_tables", fake_cleanup)

    generator = backend_conftest.clean_database.__wrapped__(
        _FakeMarkerRequest(None),
        object(),
    )
    next(generator)
    fake_app.dependency_overrides["during_test"] = object()

    with pytest.raises(StopIteration):
        next(generator)

    assert cleanup_calls == ["cleanup", "cleanup"]
    assert cleanup_seen_overrides == [{}, {}]
    assert fake_app.dependency_overrides == {}
    assert events[0] == (
        "execute",
        ("SELECT pg_advisory_lock(:lock_id)", {"lock_id": 917263514}),
    )
    assert events[-2] == (
        "execute",
        ("SELECT pg_advisory_unlock(:lock_id)", {"lock_id": 917263514}),
    )


def test_configured_test_database_socket_access_is_permitted():
    allowed_network = _fake_allowed_network()

    assert socket_address_allowed(("test-db.local", 5544), allowed_network)
    assert socket_address_allowed(("192.0.2.10", 5544), allowed_network)
    assert socket_address_allowed(("2001:db8::10", 5544, 0, 0), allowed_network)
    assert database_socket_allowed(("127.0.0.1", 5432), SAFE_DATABASE_URL)


def test_network_guard_without_database_blocks_all_destinations():
    assert not socket_address_allowed(("localhost", 5432), None)
    assert not socket_address_allowed(("api.stripe.com", 443), None)


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
        return None

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
