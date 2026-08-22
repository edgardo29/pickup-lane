from __future__ import annotations

import importlib
import socket
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy.engine import make_url


DEDICATED_TEST_DATABASE_NAME = "pickup_lane_test_db"
MODEL_MODULE_FILE_EXCLUSIONS = {
    "__init__.py": "Package initializer and export surface; not a model module.",
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


def _validated_file_exclusions(
    excluded_files: Mapping[str, str] | None,
) -> Mapping[str, str]:
    exclusions = MODEL_MODULE_FILE_EXCLUSIONS if excluded_files is None else excluded_files
    for filename, reason in exclusions.items():
        if not reason.strip():
            raise EnvironmentSafetyError(
                f"Model module exclusion for {filename!r} requires a documented reason."
            )
    return exclusions


def discover_model_module_names(
    model_package: str = "backend.models",
    *,
    excluded_files: Mapping[str, str] | None = None,
) -> tuple[str, ...]:
    package = importlib.import_module(model_package)
    package_paths = getattr(package, "__path__", None)
    if not package_paths:
        raise EnvironmentSafetyError(
            f"Model package {model_package!r} does not expose a filesystem path."
        )

    exclusions = _validated_file_exclusions(excluded_files)
    package_path = Path(next(iter(package_paths))).resolve()
    module_names: list[str] = []

    for path in sorted(package_path.glob("*.py"), key=lambda candidate: candidate.name):
        if path.name in exclusions:
            continue
        if not path.name.endswith("_model.py"):
            raise EnvironmentSafetyError(
                "Unexpected Python file in model package "
                f"{model_package!r}: {path.name!r}. Add an explicit documented "
                "non-model exclusion or rename the model module to end with "
                "'_model.py'."
            )
        module_names.append(f"{model_package}.{path.stem}")

    return tuple(module_names)


def import_model_modules(
    model_package: str = "backend.models",
    *,
    excluded_files: Mapping[str, str] | None = None,
) -> tuple[str, ...]:
    module_names = discover_model_module_names(
        model_package,
        excluded_files=excluded_files,
    )
    for module_name in module_names:
        importlib.import_module(module_name)
    return module_names


def registered_sqlalchemy_table_names(
    *,
    model_package: str = "backend.models",
    excluded_model_files: Mapping[str, str] | None = None,
) -> set[str]:
    # Import every model module before reading metadata so unexported model
    # files cannot silently avoid cleanup-inventory validation.
    import_model_modules(model_package, excluded_files=excluded_model_files)
    from backend.database_metadata import Base

    return set(Base.metadata.tables)


def missing_cleanup_tables(
    cleanup_tables: Iterable[str],
    *,
    excluded_tables: Mapping[str, str] | None = None,
    registered_tables: Iterable[str] | None = None,
) -> list[str]:
    excluded_tables = excluded_tables or {}
    for table, reason in excluded_tables.items():
        if not reason.strip():
            raise EnvironmentSafetyError(
                f"Cleanup exclusion for table {table!r} requires a documented reason."
            )

    registered = (
        set(registered_tables)
        if registered_tables is not None
        else registered_sqlalchemy_table_names()
    )
    cleanup = set(cleanup_tables)
    excluded = set(excluded_tables)
    return sorted(registered - cleanup - excluded)


def assert_cleanup_table_inventory_complete(
    cleanup_tables: Iterable[str],
    *,
    excluded_tables: Mapping[str, str] | None = None,
    registered_tables: Iterable[str] | None = None,
) -> None:
    missing = missing_cleanup_tables(
        cleanup_tables,
        excluded_tables=excluded_tables,
        registered_tables=registered_tables,
    )
    if missing:
        formatted = ", ".join(missing)
        raise EnvironmentSafetyError(
            "Backend test cleanup inventory is missing registered SQLAlchemy "
            f"table(s): {formatted}. Add the table to TEST_TABLES or document "
            "an explicit cleanup exclusion."
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
