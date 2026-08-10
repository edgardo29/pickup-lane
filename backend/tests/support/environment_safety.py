from __future__ import annotations

import importlib
import socket
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.schema import Table


TEST_APP_ENV = "test"
DEDICATED_TEST_DATABASE_NAME = "pickup_lane_test_db"
NON_APPLICATION_CLEANUP_TABLE_EXCLUSIONS = {
    "alembic_version": "Alembic migration bookkeeping table; not application data.",
}
NETWORK_BLOCKED_MESSAGE = (
    "EN-01 network safety guard blocked external network access during standard "
    "backend tests. Only the configured dedicated PostgreSQL test database host "
    "and exact port are allowed."
)


class EnvironmentSafetyError(RuntimeError):
    """Raised when backend tests would use an unsafe resource."""


@dataclass(frozen=True)
class ParsedDatabaseUrl:
    drivername: str
    database_name: str
    host: str
    port: int


@dataclass(frozen=True)
class AllowedDatabaseNetwork:
    host: str
    port: int
    allowed_hosts: frozenset[str]


@dataclass(frozen=True)
class CleanupPlan:
    table_keys: tuple[str, ...]
    truncate_sql: str


def validate_backend_test_app_env(app_env: str | None) -> None:
    if app_env != TEST_APP_ENV:
        raise EnvironmentSafetyError(
            "Automated backend tests require APP_ENV='test'; got "
            f"{app_env!r}."
        )


def parse_database_url(database_url: str) -> ParsedDatabaseUrl:
    try:
        parsed = make_url(database_url)
    except Exception as exc:  # noqa: BLE001 - SQLAlchemy wraps URL parsing details.
        raise EnvironmentSafetyError("DATABASE_URL is not a valid SQLAlchemy URL.") from exc

    drivername = parsed.drivername.lower()
    if drivername != "postgresql" and not drivername.startswith("postgresql+"):
        raise EnvironmentSafetyError(
            "DATABASE_URL must use a PostgreSQL SQLAlchemy driver."
        )

    database_name = parsed.database or ""
    if not database_name:
        raise EnvironmentSafetyError("DATABASE_URL must include a database name.")

    host = parsed.host or ""
    if not host:
        raise EnvironmentSafetyError(
            "DATABASE_URL must include a PostgreSQL host so the EN-01 network "
            "guard can enforce the configured host-and-port boundary."
        )

    return ParsedDatabaseUrl(
        drivername=drivername,
        database_name=database_name,
        host=host,
        port=parsed.port or 5432,
    )


def validate_dedicated_test_database_url(database_url: str) -> ParsedDatabaseUrl:
    parsed = parse_database_url(database_url)
    if parsed.database_name != DEDICATED_TEST_DATABASE_NAME:
        raise EnvironmentSafetyError(
            "Backend tests may only run against the dedicated PostgreSQL test "
            f"database named {DEDICATED_TEST_DATABASE_NAME!r}; got "
            f"{parsed.database_name!r}."
        )
    return parsed


def import_model_package(model_package: str = "backend.models") -> object:
    try:
        return importlib.import_module(model_package)
    except Exception as exc:  # noqa: BLE001 - expose import failure as safety setup.
        raise EnvironmentSafetyError(
            f"Could not import SQLAlchemy model package {model_package!r} for "
            "backend test cleanup target discovery."
        ) from exc


def registered_sqlalchemy_tables(
    *,
    model_package: str = "backend.models",
) -> tuple[Table, ...]:
    # Use the same package-level model import surface as Alembic and
    # application code so cleanup target discovery follows the app metadata
    # contract instead of test-only filename scanning.
    import_model_package(model_package)
    from backend.database import Base

    tables = tuple(
        sorted(
            Base.metadata.tables.values(),
            key=lambda table: (table.schema or "", table.name),
        )
    )
    if not tables:
        raise EnvironmentSafetyError(
            "No SQLAlchemy application tables are registered for backend test cleanup."
        )
    return tables


def registered_sqlalchemy_table_names(
    *,
    model_package: str = "backend.models",
) -> set[str]:
    return {
        cleanup_table_key(table)
        for table in registered_sqlalchemy_tables(
            model_package=model_package,
        )
    }


def cleanup_table_key(table: Table) -> str:
    return _format_table_key(table.schema, table.name)


def _format_table_key(schema: str | None, table_name: str) -> str:
    return f"{schema}.{table_name}" if schema else table_name


def _validated_cleanup_exclusions(
    excluded_database_tables: Mapping[str, str] | None,
) -> Mapping[str, str]:
    exclusions = (
        NON_APPLICATION_CLEANUP_TABLE_EXCLUSIONS
        if excluded_database_tables is None
        else excluded_database_tables
    )
    for table, reason in exclusions.items():
        if not reason.strip():
            raise EnvironmentSafetyError(
                f"Cleanup exclusion for table {table!r} requires a documented reason."
            )
    return exclusions


def assert_cleanup_schema_state(
    *,
    metadata_table_keys: Iterable[str],
    database_table_keys: Iterable[str],
    excluded_database_tables: Mapping[str, str] | None = None,
) -> None:
    metadata_keys = set(metadata_table_keys)
    database_keys = set(database_table_keys)
    exclusions = _validated_cleanup_exclusions(excluded_database_tables)
    excluded_keys = set(exclusions)

    app_exclusions = sorted(metadata_keys & excluded_keys)
    if app_exclusions:
        formatted = ", ".join(app_exclusions)
        raise EnvironmentSafetyError(
            "Backend test cleanup exclusions may not omit SQLAlchemy "
            f"application table(s): {formatted}."
        )

    missing_database_tables = sorted(metadata_keys - database_keys)
    unhandled_database_tables = sorted(database_keys - metadata_keys - excluded_keys)
    if missing_database_tables or unhandled_database_tables:
        parts: list[str] = []
        if missing_database_tables:
            parts.append(
                "missing metadata table(s) in PostgreSQL: "
                + ", ".join(missing_database_tables)
            )
        if unhandled_database_tables:
            parts.append(
                "unhandled PostgreSQL table(s): "
                + ", ".join(unhandled_database_tables)
            )
        raise EnvironmentSafetyError(
            "PostgreSQL test database schema does not match SQLAlchemy cleanup "
            f"metadata ({'; '.join(parts)}). Rebuild the dedicated test database "
            "or document a narrow non-application exclusion."
        )


def database_table_keys_for_cleanup(
    connection,
    metadata_tables: Sequence[Table],
) -> set[str]:
    inspector = inspect(connection)
    schemas = sorted(
        {table.schema for table in metadata_tables},
        key=lambda schema: schema or "",
    )
    table_keys: set[str] = set()
    for schema in schemas:
        for table_name in inspector.get_table_names(schema=schema):
            table_keys.add(_format_table_key(schema, table_name))
    return table_keys


def assert_database_schema_matches_cleanup_metadata(
    connection,
    metadata_tables: Sequence[Table],
    *,
    excluded_database_tables: Mapping[str, str] | None = None,
) -> None:
    assert_cleanup_schema_state(
        metadata_table_keys=[cleanup_table_key(table) for table in metadata_tables],
        database_table_keys=database_table_keys_for_cleanup(connection, metadata_tables),
        excluded_database_tables=excluded_database_tables,
    )


def quoted_table_identifier(table: Table, dialect) -> str:
    preparer = dialect.identifier_preparer
    table_name = preparer.quote_identifier(table.name)
    if table.schema:
        return f"{preparer.quote_identifier(table.schema)}.{table_name}"
    return table_name


def build_cleanup_truncate_statement(
    metadata_tables: Sequence[Table],
    dialect,
) -> str:
    if not metadata_tables:
        raise EnvironmentSafetyError(
            "Backend test cleanup requires at least one SQLAlchemy application table."
        )

    table_targets = [
        quoted_table_identifier(table, dialect)
        for table in sorted(
            metadata_tables,
            key=lambda table: (table.schema or "", table.name),
        )
    ]
    return f"TRUNCATE TABLE {', '.join(table_targets)} RESTART IDENTITY CASCADE"


def cleanup_application_tables(
    connection,
    *,
    metadata_tables: Sequence[Table] | None = None,
    excluded_database_tables: Mapping[str, str] | None = None,
) -> CleanupPlan:
    tables = (
        registered_sqlalchemy_tables()
        if metadata_tables is None
        else tuple(metadata_tables)
    )
    assert_database_schema_matches_cleanup_metadata(
        connection,
        tables,
        excluded_database_tables=excluded_database_tables,
    )
    truncate_sql = build_cleanup_truncate_statement(tables, connection.dialect)
    connection.execute(text(truncate_sql))
    return CleanupPlan(
        table_keys=tuple(cleanup_table_key(table) for table in tables),
        truncate_sql=truncate_sql,
    )


def build_allowed_database_network(
    database_url: str,
    *,
    resolver=socket.getaddrinfo,
) -> AllowedDatabaseNetwork | None:
    if not database_url:
        return None

    parsed = validate_dedicated_test_database_url(database_url)
    allowed_hosts = {parsed.host}
    try:
        address_infos = resolver(parsed.host, parsed.port, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise EnvironmentSafetyError(
            "Configured PostgreSQL test host could not be resolved for EN-01 "
            f"network safety: {parsed.host!r}."
        ) from exc

    for address_info in address_infos:
        socket_address = address_info[4]
        if isinstance(socket_address, tuple) and socket_address:
            allowed_hosts.add(str(socket_address[0]))

    return AllowedDatabaseNetwork(
        host=parsed.host,
        port=parsed.port,
        allowed_hosts=frozenset(allowed_hosts),
    )


def socket_address_allowed(
    address: Any,
    allowed_network: AllowedDatabaseNetwork | None,
) -> bool:
    if allowed_network is None:
        return False

    if not isinstance(address, tuple) or len(address) < 2:
        return False

    host = str(address[0])
    try:
        port = int(address[1])
    except (TypeError, ValueError):
        return False

    if port != allowed_network.port:
        return False

    return host in allowed_network.allowed_hosts


def database_socket_allowed(address: Any, database_url: str) -> bool:
    return socket_address_allowed(address, build_allowed_database_network(database_url))


def _coerce_allowed_network(
    database_url_or_network: str | AllowedDatabaseNetwork | None,
) -> AllowedDatabaseNetwork | None:
    if isinstance(database_url_or_network, AllowedDatabaseNetwork):
        return database_url_or_network
    return build_allowed_database_network(database_url_or_network or "")


def guard_socket_connect(
    original_connect,
    database_url_or_network: str | AllowedDatabaseNetwork | None,
    socket_instance: socket.socket,
    address: Any,
):
    allowed_network = _coerce_allowed_network(database_url_or_network)
    if socket_address_allowed(address, allowed_network):
        return original_connect(socket_instance, address)
    raise EnvironmentSafetyError(NETWORK_BLOCKED_MESSAGE)


def guard_socket_connect_ex(
    original_connect_ex,
    database_url_or_network: str | AllowedDatabaseNetwork | None,
    socket_instance: socket.socket,
    address: Any,
):
    allowed_network = _coerce_allowed_network(database_url_or_network)
    if socket_address_allowed(address, allowed_network):
        return original_connect_ex(socket_instance, address)
    raise EnvironmentSafetyError(NETWORK_BLOCKED_MESSAGE)


def guard_socket_create_connection(
    original_create_connection,
    database_url_or_network: str | AllowedDatabaseNetwork | None,
    address: Any,
    *args,
    **kwargs,
):
    allowed_network = _coerce_allowed_network(database_url_or_network)
    if socket_address_allowed(address, allowed_network):
        return original_create_connection(address, *args, **kwargs)
    raise EnvironmentSafetyError(NETWORK_BLOCKED_MESSAGE)
