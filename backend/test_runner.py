"""Safe repository-owned runner for backend test databases and pytest."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import ipaddress
import os
import re
import socket
import subprocess
import sys
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Any
from urllib.parse import quote, urlsplit

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from dotenv import dotenv_values
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.pool import NullPool

from backend.settings import (
    LOCAL_TEST_DATABASE_HOSTS,
)
from backend.tests.support.artifacts import sanitize_artifact_text
from backend.tests.support.environment_safety import (
    DEDICATED_MIGRATION_TEST_DATABASE_NAME,
    DEDICATED_TEST_DATABASE_NAME,
    EnvironmentSafetyError,
    ParsedDatabaseUrl,
    parse_database_url,
    validate_local_test_connection_endpoint,
    validate_local_test_connection_identity,
    validate_migration_test_database_urls,
    validate_test_database_connection_environment,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ENV_PATH = REPO_ROOT / "backend" / ".env"
ALEMBIC_INI_PATH = REPO_ROOT / "alembic.ini"
ALEMBIC_ENV_PATH = REPO_ROOT / "backend" / "alembic" / "env.py"
ALEMBIC_VERSIONS_PATH = REPO_ROOT / "backend" / "alembic" / "versions"
ALEMBIC_URL_OVERRIDE_ATTRIBUTE = "pickup_lane_database_url_override"
SCHEMA_FINGERPRINT_PREFIX = "pickup-lane-test-schema:v1:"
DATABASE_COMMENT_QUERY = (
    "SELECT shobj_description(oid, 'pg_database') "
    "FROM pg_database WHERE datname = :database_name"
)
REBUILD_ORDINARY_COMMAND = (
    "backend/.venv/bin/python -m backend.test_runner rebuild ordinary"
)
LOCK_FILE_PREFIX = "pickup-lane-backend-test"
LOCK_ROOT = Path("/tmp")
BACKEND_TESTS_ROOT = REPO_ROOT / "backend" / "tests"
PYTEST_SAFETY_BYPASS_OPTIONS = frozenset(
    {
        "--noconftest",
        "--confcutdir",
        "--pyargs",
        "--rootdir",
        "--override-ini",
        "-c",
        "-o",
        "-p",
    }
)
PYTEST_OPTIONS_WITH_VALUES = frozenset(
    {
        "-k", "-m", "--maxfail", "--tb", "--capture", "--junitxml",
        "--basetemp", "--durations", "--durations-min", "--ignore",
        "--ignore-glob", "--deselect", "--log-level", "--log-cli-level",
        "--color", "--import-mode", "--show-capture",
    }
)


class BackendTestRunnerError(RuntimeError):
    """Raised when a runner command cannot proceed safely."""


@dataclass(frozen=True)
class RunnerConfiguration:
    ordinary_url: str
    migration_url: str
    ordinary_target: ParsedDatabaseUrl
    migration_target: ParsedDatabaseUrl

    def __post_init__(self) -> None:
        ordinary_target, migration_target = validate_runner_database_urls(
            self.ordinary_url,
            self.migration_url,
        )
        if (
            self.ordinary_target != ordinary_target
            or self.migration_target != migration_target
        ):
            raise BackendTestRunnerError(
                "Runner database targets must match their validated connection URLs."
            )

    def subprocess_environment(
        self,
        environ: Mapping[str, str] | None = None,
    ) -> dict[str, str]:
        source = os.environ if environ is None else environ
        _validate_connection_environment(source)
        child_environment = dict(source)
        # Pytest must run the selection supplied to this invocation, not an
        # ambient selection inherited from the caller's shell.
        child_environment.pop("PYTEST_ADDOPTS", None)
        child_environment.pop("PYTEST_PLUGINS", None)
        child_environment.update(
            {
                "APP_ENV": "ci" if _is_ci_environment(source) else "test",
                "DATABASE_URL": self.ordinary_url,
                "TEST_DATABASE_URL": self.ordinary_url,
                "MIGRATION_DATABASE_URL": self.migration_url,
                "PYTHONPATH": str(REPO_ROOT),
            }
        )
        return child_environment


@dataclass(frozen=True)
class OrdinarySchemaState:
    expected_head: str
    actual_revisions: tuple[str, ...]
    expected_fingerprint: str
    stored_fingerprint: str | None

    @property
    def is_current(self) -> bool:
        return self.actual_revisions == (self.expected_head,) and (
            self.stored_fingerprint == self.expected_fingerprint
        )


def _is_ci_environment(environ: Mapping[str, str]) -> bool:
    for name in ("CI", "GITHUB_ACTIONS"):
        value = environ.get(name)
        if value and value.strip().lower() not in {"0", "false", "no", "off"}:
            return True
    return False


def load_runner_configuration(
    environ: Mapping[str, str] | None = None,
    *,
    dotenv_path: Path = BACKEND_ENV_PATH,
) -> RunnerConfiguration:
    source = os.environ if environ is None else environ
    values: dict[str, str] = {}
    if dotenv_path.is_file():
        try:
            loaded = dotenv_values(dotenv_path, interpolate=False)
        except Exception as exc:
            raise BackendTestRunnerError(
                "Could not read backend/.env for backend test configuration."
            ) from exc
        values.update(
            {name: value for name, value in loaded.items() if value is not None}
        )
    values.update({name: value for name, value in source.items() if value is not None})
    _validate_connection_environment(values)

    ordinary_url = _required_configuration_value(values, "TEST_DATABASE_URL")
    migration_url = _required_configuration_value(values, "MIGRATION_DATABASE_URL")
    ordinary_target, migration_target = validate_runner_database_urls(
        ordinary_url,
        migration_url,
    )
    return RunnerConfiguration(
        ordinary_url=ordinary_url,
        migration_url=migration_url,
        ordinary_target=ordinary_target,
        migration_target=migration_target,
    )


def _required_configuration_value(values: Mapping[str, str], name: str) -> str:
    value = values.get(name, "").strip()
    if not value:
        raise BackendTestRunnerError(
            f"{name} is required in backend/.env or the command environment."
        )
    return value


def validate_runner_database_urls(
    ordinary_url: str,
    migration_url: str,
) -> tuple[ParsedDatabaseUrl, ParsedDatabaseUrl]:
    ordinary_unrestricted = parse_database_url(
        ordinary_url,
        name="TEST_DATABASE_URL",
    )
    migration_unrestricted = parse_database_url(
        migration_url,
        name="MIGRATION_DATABASE_URL",
    )
    if (
        ordinary_unrestricted.host == migration_unrestricted.host
        and ordinary_unrestricted.port == migration_unrestricted.port
        and ordinary_unrestricted.database_name == migration_unrestricted.database_name
    ):
        raise EnvironmentSafetyError(
            "TEST_DATABASE_URL and MIGRATION_DATABASE_URL must identify distinct "
            "databases."
        )

    targets = validate_migration_test_database_urls(ordinary_url, migration_url)
    _validate_runner_database_url(
        ordinary_url,
        targets.application_database,
        name="TEST_DATABASE_URL",
    )
    _validate_runner_database_url(
        migration_url,
        targets.migration_database,
        name="MIGRATION_DATABASE_URL",
    )
    return targets.application_database, targets.migration_database


def _validate_runner_database_url(
    database_url: str,
    target: ParsedDatabaseUrl,
    *,
    name: str,
) -> None:
    if target.host.lower() not in LOCAL_TEST_DATABASE_HOSTS:
        raise EnvironmentSafetyError(
            f"{name} must use the local PostgreSQL test server. The repository "
            "runner accepts only localhost or an explicit loopback address."
        )
    _validate_loopback_resolution(target.host, target.port, name=name)
    if make_url(database_url).query:
        raise EnvironmentSafetyError(
            f"{name} must not use connection query parameters because they can "
            "override the validated local test endpoint."
        )


def _validate_connection_environment(environ: Mapping[str, str]) -> None:
    validate_test_database_connection_environment(environ)


def _validate_loopback_resolution(host: str, port: int, *, name: str) -> None:
    try:
        addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise EnvironmentSafetyError(
            f"{name} must resolve to the local loopback PostgreSQL server."
        ) from exc
    if not addresses or any(
        not ipaddress.ip_address(address[4][0]).is_loopback for address in addresses
    ):
        raise EnvironmentSafetyError(
            f"{name} must resolve only to local loopback addresses."
        )


def migration_source_fingerprint() -> str:
    source_paths = [
        ALEMBIC_INI_PATH,
        ALEMBIC_ENV_PATH,
        *sorted(ALEMBIC_VERSIONS_PATH.glob("*.py")),
    ]
    digest = hashlib.sha256()
    for path in source_paths:
        if not path.is_file():
            raise BackendTestRunnerError(
                f"Required migration source is missing: {path.relative_to(REPO_ROOT)}"
            )
        relative_path = path.relative_to(REPO_ROOT).as_posix().encode("utf-8")
        digest.update(relative_path)
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def expected_alembic_head() -> str:
    config = Config(str(ALEMBIC_INI_PATH))
    heads = tuple(ScriptDirectory.from_config(config).get_heads())
    if len(heads) != 1:
        raise BackendTestRunnerError(
            "Backend test workflow requires exactly one Alembic head; "
            f"found {len(heads)}."
        )
    return heads[0]


def schema_fingerprint_marker(fingerprint: str) -> str:
    return f"{SCHEMA_FINGERPRINT_PREFIX}{fingerprint}"


def _database_engine(database_url: str):
    return create_engine(database_url, poolclass=NullPool)


def inspect_ordinary_schema(configuration: RunnerConfiguration) -> OrdinarySchemaState:
    _validate_connection_environment(os.environ)
    expected_head = expected_alembic_head()
    expected_fingerprint = schema_fingerprint_marker(migration_source_fingerprint())
    engine = _database_engine(configuration.ordinary_url)
    try:
        with engine.connect() as connection:
            validate_local_test_connection_identity(
                connection,
                DEDICATED_TEST_DATABASE_NAME,
                configuration.ordinary_target.port,
            )
            actual_revisions = tuple(
                sorted(
                    connection.execute(
                        text("SELECT version_num FROM alembic_version")
                    ).scalars()
                )
            )
            stored_fingerprint = connection.execute(
                text(DATABASE_COMMENT_QUERY),
                {"database_name": DEDICATED_TEST_DATABASE_NAME},
            ).scalar_one_or_none()
    except EnvironmentSafetyError:
        raise
    except Exception as exc:
        raise BackendTestRunnerError(_ordinary_rebuild_required_message()) from exc
    finally:
        engine.dispose()

    return OrdinarySchemaState(
        expected_head=expected_head,
        actual_revisions=actual_revisions,
        expected_fingerprint=expected_fingerprint,
        stored_fingerprint=stored_fingerprint,
    )


def require_current_ordinary_schema(configuration: RunnerConfiguration) -> None:
    state = inspect_ordinary_schema(configuration)
    if not state.is_current:
        raise BackendTestRunnerError(_ordinary_rebuild_required_message())


def _ordinary_rebuild_required_message() -> str:
    return (
        "The ordinary test database is missing or stale. Rebuild it before "
        f"running tests with: {REBUILD_ORDINARY_COMMAND}"
    )


def _lock_path(target: ParsedDatabaseUrl, lock_root: Path) -> Path:
    host_identity = (
        "loopback"
        if target.host.lower() in LOCAL_TEST_DATABASE_HOSTS
        else target.host.lower()
    )
    identity = f"{host_identity}:{target.port}/{target.database_name}"
    suffix = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
    return lock_root / f"{LOCK_FILE_PREFIX}-{suffix}.lock"


@contextmanager
def database_operation_lock(
    target: ParsedDatabaseUrl,
    *,
    lock_root: Path | None = None,
) -> Iterator[None]:
    root = LOCK_ROOT if lock_root is None else lock_root
    root.mkdir(parents=True, exist_ok=True)
    path = _lock_path(target, root)
    handle = path.open("a+", encoding="utf-8")
    try:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise BackendTestRunnerError(
                f"Another backend test operation already owns the "
                f"{target.database_name} lock."
            ) from exc
        yield
    finally:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()


@contextmanager
def database_operation_locks(
    targets: Iterable[ParsedDatabaseUrl],
) -> Iterator[None]:
    ordered = sorted(
        targets,
        key=lambda target: (target.host, target.port, target.database_name),
    )
    with ExitStack() as stack:
        for target in ordered:
            stack.enter_context(database_operation_lock(target))
        yield


def _maintenance_url(database_url: str) -> URL:
    return make_url(database_url).set(database="postgres")


def _quoted_database_name(database_name: str) -> str:
    if database_name not in {
        DEDICATED_TEST_DATABASE_NAME,
        DEDICATED_MIGRATION_TEST_DATABASE_NAME,
    }:
        raise BackendTestRunnerError(
            "Refusing a destructive operation for a database outside the exact "
            "test-database allow list."
        )
    return f'"{database_name}"'


def recreate_database(database_url: str, expected_database_name: str) -> None:
    _validate_connection_environment(os.environ)
    parsed_target = parse_database_url(database_url, name="test database URL")
    _validate_runner_database_url(
        database_url,
        parsed_target,
        name="test database URL",
    )
    if parsed_target.database_name != expected_database_name:
        raise BackendTestRunnerError(
            "Refusing a destructive operation because the validated database "
            "target does not match the connection URL."
        )
    quoted_name = _quoted_database_name(parsed_target.database_name)
    engine = create_engine(
        _maintenance_url(database_url),
        isolation_level="AUTOCOMMIT",
        poolclass=NullPool,
    )
    try:
        with engine.connect() as connection:
            validate_local_test_connection_endpoint(connection, parsed_target.port)
            connection.exec_driver_sql(
                f"DROP DATABASE IF EXISTS {quoted_name} WITH (FORCE)"
            )
            connection.exec_driver_sql(f"CREATE DATABASE {quoted_name}")
    finally:
        engine.dispose()


def apply_migrations_to_ordinary_database(configuration: RunnerConfiguration) -> None:
    _validate_connection_environment(os.environ)
    config = Config(str(ALEMBIC_INI_PATH))
    config.attributes[ALEMBIC_URL_OVERRIDE_ATTRIBUTE] = configuration.ordinary_url
    command.upgrade(config, "head")


def require_unchanged_migration_source(expected_fingerprint: str) -> None:
    if migration_source_fingerprint() != expected_fingerprint:
        raise BackendTestRunnerError(
            "Migration source changed while the ordinary test database was being "
            "rebuilt. Re-run the ordinary rebuild before running tests."
        )


def record_ordinary_schema_fingerprint(
    configuration: RunnerConfiguration,
    source_fingerprint: str,
) -> None:
    _validate_connection_environment(os.environ)
    marker = schema_fingerprint_marker(source_fingerprint)
    quoted_name = _quoted_database_name(configuration.ordinary_target.database_name)
    escaped_marker = marker.replace("'", "''")
    engine = _database_engine(configuration.ordinary_url)
    try:
        with engine.begin() as connection:
            validate_local_test_connection_identity(
                connection,
                DEDICATED_TEST_DATABASE_NAME,
                configuration.ordinary_target.port,
            )
            connection.exec_driver_sql(
                f"COMMENT ON DATABASE {quoted_name} IS '{escaped_marker}'"
            )
    finally:
        engine.dispose()


def rebuild_ordinary_database(configuration: RunnerConfiguration) -> None:
    with database_operation_lock(configuration.ordinary_target):
        source_fingerprint = migration_source_fingerprint()
        recreate_database(
            configuration.ordinary_url,
            DEDICATED_TEST_DATABASE_NAME,
        )
        apply_migrations_to_ordinary_database(configuration)
        require_unchanged_migration_source(source_fingerprint)
        record_ordinary_schema_fingerprint(configuration, source_fingerprint)
        require_current_ordinary_schema(configuration)
    print(f"Rebuilt {DEDICATED_TEST_DATABASE_NAME} at the current Alembic head.")


def rebuild_migration_database(configuration: RunnerConfiguration) -> None:
    with database_operation_lock(configuration.migration_target):
        recreate_database(
            configuration.migration_url,
            DEDICATED_MIGRATION_TEST_DATABASE_NAME,
        )
    print(f"Rebuilt empty {DEDICATED_MIGRATION_TEST_DATABASE_NAME}.")


def rebuild_all_databases(configuration: RunnerConfiguration) -> None:
    with database_operation_locks(
        (configuration.ordinary_target, configuration.migration_target)
    ):
        source_fingerprint = migration_source_fingerprint()
        recreate_database(
            configuration.migration_url,
            DEDICATED_MIGRATION_TEST_DATABASE_NAME,
        )
        recreate_database(
            configuration.ordinary_url,
            DEDICATED_TEST_DATABASE_NAME,
        )
        apply_migrations_to_ordinary_database(configuration)
        require_unchanged_migration_source(source_fingerprint)
        record_ordinary_schema_fingerprint(configuration, source_fingerprint)
        require_current_ordinary_schema(configuration)
    print("Rebuilt both dedicated backend test databases.")


def pytest_command(pytest_arguments: Sequence[str]) -> list[str]:
    if not pytest_arguments or pytest_arguments[0].startswith("-"):
        raise BackendTestRunnerError(
            "An explicit backend/tests pytest selection must be the first "
            "argument after the test target."
        )
    _validate_pytest_selection(pytest_arguments[0])
    option_value_pending = False
    for argument in pytest_arguments[1:]:
        # Pytest expands @files after this validation pass. Do not let an
        # unchecked file add paths or options that bypass the root conftest.
        if argument.startswith("@"):
            raise BackendTestRunnerError(
                "Pytest argument files can bypass backend test safety fixtures "
                "and are not supported."
            )
        if option_value_pending:
            option_value_pending = False
            continue
        option = argument.split("=", 1)[0]
        if option in PYTEST_SAFETY_BYPASS_OPTIONS or any(
            argument.startswith(short_option)
            for short_option in ("-c", "-o", "-p")
        ) or (
            argument.startswith("-")
            and not argument.startswith("--")
            and len(argument) > 2
            and argument[1] not in {"k", "m", "r", "W"}
            and any(character in "cop" for character in argument[2:])
        ):
            raise BackendTestRunnerError(
                "Pytest options that can bypass backend test safety fixtures "
                "or change their configuration are not supported."
            )
        if argument.startswith("-"):
            option_value_pending = argument in PYTEST_OPTIONS_WITH_VALUES
            continue
        # An option value may not be a filesystem path. Every existing
        # positional path, however, must remain under the guarded test tree.
        if Path(argument.split("::", 1)[0]).exists():
            _validate_pytest_selection(argument)
    return [sys.executable, "-m", "pytest", *pytest_arguments]


def _validate_pytest_selection(selection: str) -> None:
    selection_path = Path(selection.split("::", 1)[0])
    try:
        selected = selection_path.resolve(strict=True)
        selected.relative_to(BACKEND_TESTS_ROOT.resolve())
    except (OSError, ValueError) as exc:
        raise BackendTestRunnerError(
            "Every existing pytest selection must be under backend/tests; "
            "the first selection must exist."
        ) from exc


def _database_output_secrets(database_urls: Sequence[str]) -> tuple[str, ...]:
    secrets: set[str] = set()
    for raw_url in database_urls:
        secrets.add(raw_url)
        try:
            password = make_url(raw_url).password
            userinfo = urlsplit(raw_url).netloc.rpartition("@")[0]
            encoded_password = userinfo.partition(":")[2]
        except Exception:  # noqa: BLE001 - malformed inputs still need safe output.
            password = None
            encoded_password = ""
        if password:
            secrets.update({password, quote(password, safe="")})
        if encoded_password:
            secrets.update({encoded_password, encoded_password.replace("%", "%%")})
    return tuple(sorted(secrets - {""}, key=len, reverse=True))


def redact_output(text_value: str, *, database_urls: Sequence[str] = ()) -> str:
    sanitized = text_value
    for secret in _database_output_secrets(database_urls):
        # Match a configured secret even if output inserts a line break inside it.
        wrapped = r"(?:\r?\n)?".join(map(re.escape, secret))
        sanitized = re.sub(wrapped, "[REDACTED]", sanitized)
    return sanitize_artifact_text(sanitized)


def _secret_prefix_match(value: str, secret: str) -> tuple[bool, int | None]:
    """Return whether value could grow into secret, or its completed span."""

    position = 0
    for index, character in enumerate(secret):
        if index and position < len(value):
            if value[position] == "\r":
                if position + 1 == len(value):
                    return True, None
                if value[position + 1] == "\n":
                    position += 2
            elif value[position] == "\n":
                position += 1
        if position == len(value):
            return True, None
        if value[position] != character:
            return False, None
        position += 1
    return False, position


def stream_redacted_output(
    source: Iterable[str],
    output: IO[str],
    *,
    database_urls: Sequence[str],
) -> None:
    """Emit live pytest progress while retaining only possible sensitive text."""

    secrets = _database_output_secrets(database_urls)
    pending = ""
    visible_line = ""

    def emit(value: str) -> None:
        nonlocal visible_line
        visible_line += value
        while "\n" in visible_line:
            line, visible_line = visible_line.split("\n", 1)
            output.write(sanitize_artifact_text(line + "\n"))
            output.flush()
        # Pytest's quiet progress markers are safe to show before its row ends.
        # Other text stays on one line until the generic sanitizer can see it.
        if visible_line and all(character in ".FE" for character in visible_line):
            output.write(visible_line)
            output.flush()
            visible_line = ""

    def drain(*, final: bool) -> None:
        nonlocal pending
        while pending:
            matches = [_secret_prefix_match(pending, secret) for secret in secrets]
            if not final and any(possible for possible, _span in matches):
                return
            completed = [span for _possible, span in matches if span is not None]
            if completed:
                emit("[REDACTED]")
                pending = pending[max(completed):]
            else:
                emit(pending[0])
                pending = pending[1:]

    # A pipe iterator waits for a newline, which can hide pytest progress for
    # minutes. Read characters from the real pipe as they become available.
    chunks = iter(lambda: source.read(1), "") if hasattr(source, "read") else source
    for chunk in chunks:
        pending += chunk
        drain(final=False)
    drain(final=True)
    if visible_line:
        output.write(sanitize_artifact_text(visible_line))
        output.flush()


def run_pytest(
    pytest_arguments: Sequence[str],
    *,
    environment: Mapping[str, str],
    database_urls: Sequence[str],
    process_factory: Callable[..., Any] = subprocess.Popen,
    output: IO[str] = sys.stdout,
) -> int:
    process = process_factory(
        pytest_command(pytest_arguments),
        cwd=REPO_ROOT,
        env=dict(environment),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    if process.stdout is None:
        raise BackendTestRunnerError("Pytest output stream was not available.")
    stream_redacted_output(process.stdout, output, database_urls=database_urls)
    return process.wait()


class RedactingArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        super().error(sanitize_artifact_text(message))


def test_ordinary_database(
    configuration: RunnerConfiguration,
    pytest_arguments: Sequence[str],
) -> int:
    pytest_command(pytest_arguments)
    # A broad ordinary selection can discover migration-lifecycle tests. Hold
    # both locks so such a selection cannot overlap a migration rebuild.
    with database_operation_locks(
        (configuration.ordinary_target, configuration.migration_target)
    ):
        require_current_ordinary_schema(configuration)
        return run_pytest(
            pytest_arguments,
            environment=configuration.subprocess_environment(),
            database_urls=(configuration.ordinary_url, configuration.migration_url),
        )


def test_migration_database(
    configuration: RunnerConfiguration,
    pytest_arguments: Sequence[str],
) -> int:
    pytest_command(pytest_arguments)
    # A broad selection passed to the migration target can discover ordinary
    # tests too, even though the first selection is restricted to backend/tests.
    with database_operation_locks(
        (configuration.ordinary_target, configuration.migration_target)
    ):
        require_current_ordinary_schema(configuration)
        return run_pytest(
            pytest_arguments,
            environment=configuration.subprocess_environment(),
            database_urls=(configuration.ordinary_url, configuration.migration_url),
        )


def build_argument_parser() -> argparse.ArgumentParser:
    parser = RedactingArgumentParser(
        description=(
            "Safely rebuild Pickup Lane's dedicated backend test databases or "
            "run an explicit pytest selection against one of them."
        )
    )
    subparsers = parser.add_subparsers(
        dest="command", required=True, parser_class=RedactingArgumentParser
    )

    rebuild_parser = subparsers.add_parser(
        "rebuild",
        help="Drop and recreate an exact allow-listed test database.",
    )
    rebuild_parser.add_argument(
        "target",
        choices=("ordinary", "migration", "all"),
        help="ordinary, migration, or both databases",
    )

    test_parser = subparsers.add_parser(
        "test",
        help="Run an explicit pytest selection through the guarded environment.",
    )
    test_parser.add_argument(
        "target",
        choices=("ordinary", "migration"),
        help="database purpose for the pytest selection",
    )
    test_parser.add_argument(
        "pytest_arguments",
        nargs=argparse.REMAINDER,
        help="pytest paths, node IDs, and options forwarded without rewriting",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_argument_parser()
    arguments = parser.parse_args(argv)
    database_urls: tuple[str, ...] = ()
    try:
        configuration = load_runner_configuration()
        database_urls = (configuration.ordinary_url, configuration.migration_url)
        if arguments.command == "rebuild":
            if arguments.target == "ordinary":
                rebuild_ordinary_database(configuration)
            elif arguments.target == "migration":
                rebuild_migration_database(configuration)
            else:
                rebuild_all_databases(configuration)
            return 0

        if arguments.target == "ordinary":
            return test_ordinary_database(
                configuration,
                arguments.pytest_arguments,
            )
        return test_migration_database(
            configuration,
            arguments.pytest_arguments,
        )
    except (BackendTestRunnerError, EnvironmentSafetyError) as exc:
        print(
            f"backend-test: {redact_output(str(exc), database_urls=database_urls)}",
            file=sys.stderr,
        )
        return 2
    except KeyboardInterrupt:
        print("backend-test: interrupted", file=sys.stderr)
        return 130
    except Exception as exc:  # noqa: BLE001 - CLI must not leak URL credentials.
        detail = redact_output(str(exc), database_urls=database_urls)
        print(f"backend-test: operation failed: {detail}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
