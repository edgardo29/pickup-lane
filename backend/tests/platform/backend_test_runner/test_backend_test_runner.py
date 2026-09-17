from __future__ import annotations

import io
import runpy
import socket
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest
import sqlalchemy
from alembic import context as alembic_context

from backend import test_runner as backend_test
from backend.tests import conftest as backend_conftest
from backend.tests.support import environment_safety
from backend.tests.support.environment_safety import EnvironmentSafetyError

pytestmark = pytest.mark.no_db_cleanup

ORDINARY_URL = (
    "postgresql+psycopg://test-user:ordinary-secret@localhost:5432/pickup_lane_test_db"
)
MIGRATION_URL = (
    "postgresql+psycopg://test-user:migration-secret@localhost:5432/"
    "pickup_lane_migration_test_db"
)


def _write_dotenv(path: Path, *, ordinary: str, migration: str) -> None:
    path.write_text(
        f"TEST_DATABASE_URL={ordinary}\nMIGRATION_DATABASE_URL={migration}\n",
        encoding="utf-8",
    )


def test_configuration_selects_distinct_ordinary_and_migration_urls(
    tmp_path: Path,
) -> None:
    dotenv_path = tmp_path / ".env"
    _write_dotenv(dotenv_path, ordinary=ORDINARY_URL, migration=MIGRATION_URL)

    configuration = backend_test.load_runner_configuration({}, dotenv_path=dotenv_path)

    assert configuration.ordinary_url == ORDINARY_URL
    assert configuration.migration_url == MIGRATION_URL
    environment = configuration.subprocess_environment({"APP_ENV": "production"})
    assert environment["APP_ENV"] == "test"
    assert environment["DATABASE_URL"] == ORDINARY_URL
    assert environment["TEST_DATABASE_URL"] == ORDINARY_URL
    assert environment["MIGRATION_DATABASE_URL"] == MIGRATION_URL

    ci_environment = configuration.subprocess_environment({"CI": "true"})
    assert ci_environment["APP_ENV"] == "ci"

    ambient_pytest_options = configuration.subprocess_environment(
        {
            "PYTEST_ADDOPTS": "-k only_some_tests",
            "PYTEST_PLUGINS": "unsafe_plugin",
        }
    )
    assert "PYTEST_ADDOPTS" not in ambient_pytest_options
    assert "PYTEST_PLUGINS" not in ambient_pytest_options


def test_environment_values_override_dotenv_without_using_database_url_alias(
    tmp_path: Path,
) -> None:
    dotenv_path = tmp_path / ".env"
    _write_dotenv(dotenv_path, ordinary=ORDINARY_URL, migration=MIGRATION_URL)

    configuration = backend_test.load_runner_configuration(
        {
            "TEST_DATABASE_URL": ORDINARY_URL,
            "MIGRATION_DATABASE_URL": MIGRATION_URL,
            "DATABASE_URL": "postgresql+psycopg://user:secret@localhost/pickup_lane_db_dev",
        },
        dotenv_path=dotenv_path,
    )

    assert configuration.ordinary_target.database_name == "pickup_lane_test_db"
    assert configuration.migration_target.database_name == (
        "pickup_lane_migration_test_db"
    )


def test_same_database_is_rejected_explicitly() -> None:
    with pytest.raises(EnvironmentSafetyError, match="must identify distinct"):
        backend_test.validate_runner_database_urls(ORDINARY_URL, ORDINARY_URL)


@pytest.mark.parametrize(
    ("ordinary_url", "migration_url"),
    [
        (
            "postgresql+psycopg://user:secret@localhost/pickup_lane_db_dev",
            MIGRATION_URL,
        ),
        (
            "postgresql+psycopg://user:secret@localhost/pickup_lane_prod",
            MIGRATION_URL,
        ),
        (
            ORDINARY_URL,
            "postgresql+psycopg://user:secret@localhost/pickup_lane_db_dev",
        ),
        (
            ORDINARY_URL,
            "postgresql+psycopg://user:secret@localhost/pickup_lane_prod",
        ),
    ],
)
def test_development_and_production_database_names_are_rejected(
    ordinary_url: str,
    migration_url: str,
) -> None:
    with pytest.raises(EnvironmentSafetyError):
        backend_test.validate_runner_database_urls(ordinary_url, migration_url)


def test_non_loopback_database_hosts_are_rejected() -> None:
    remote_ordinary = ORDINARY_URL.replace("localhost", "test-db.example.invalid")
    remote_migration = MIGRATION_URL.replace("localhost", "test-db.example.invalid")

    with pytest.raises(EnvironmentSafetyError, match="local PostgreSQL test server"):
        backend_test.validate_runner_database_urls(
            remote_ordinary,
            remote_migration,
        )


def test_connection_query_parameters_cannot_override_the_validated_endpoint() -> None:
    ordinary_with_override = f"{ORDINARY_URL}?host=production-db.example.invalid"

    with pytest.raises(EnvironmentSafetyError, match="query parameters"):
        backend_test.validate_runner_database_urls(
            ordinary_with_override,
            MIGRATION_URL,
        )


@pytest.mark.parametrize(
    "name",
    ("PGHOSTADDR", "PGPORT", "PGSERVICE", "PGSERVICEFILE", "PGOPTIONS"),
)
def test_postgres_connection_overrides_are_rejected(name: str, tmp_path: Path) -> None:
    with pytest.raises(EnvironmentSafetyError, match=name):
        backend_test.load_runner_configuration(
            {
                "TEST_DATABASE_URL": ORDINARY_URL,
                "MIGRATION_DATABASE_URL": MIGRATION_URL,
                name: "unsafe-override",
            },
            dotenv_path=tmp_path / "missing.env",
        )


def test_test_database_environment_guard_checks_current_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PGHOSTADDR", "203.0.113.10")
    with pytest.raises(EnvironmentSafetyError, match="PGHOSTADDR"):
        environment_safety.validate_test_database_connection_environment()


def test_dotenv_postgres_connection_override_is_rejected(tmp_path: Path) -> None:
    dotenv_path = tmp_path / ".env"
    _write_dotenv(dotenv_path, ordinary=ORDINARY_URL, migration=MIGRATION_URL)
    with dotenv_path.open("a", encoding="utf-8") as env_file:
        env_file.write("PGHOSTADDR=203.0.113.10\n")

    with pytest.raises(EnvironmentSafetyError, match="PGHOSTADDR"):
        backend_test.load_runner_configuration({}, dotenv_path=dotenv_path)


def test_postgres_connection_override_is_rejected_before_destructive_sql(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PGHOSTADDR", "203.0.113.10")
    monkeypatch.setattr(
        backend_test,
        "create_engine",
        lambda *_args, **_kwargs: pytest.fail("must not create a database engine"),
    )

    with pytest.raises(EnvironmentSafetyError, match="PGHOSTADDR"):
        backend_test.recreate_database(
            ORDINARY_URL,
            backend_test.DEDICATED_TEST_DATABASE_NAME,
        )


def test_actual_remote_endpoint_is_rejected_before_destructive_sql(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executed_statements: list[str] = []

    for name in environment_safety.UNSAFE_POSTGRES_ENVIRONMENT_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(
        environment_safety,
        "_connection_socket_peer",
        lambda _connection: ("203.0.113.10", 5432),
    )

    class FakeConnection:
        def exec_driver_sql(self, statement: str):
            executed_statements.append(statement)
            return self

    class FakeEngine:
        @contextmanager
        def connect(self):
            yield FakeConnection()

        def dispose(self):
            pass

    monkeypatch.setattr(
        backend_test,
        "create_engine",
        lambda *_args, **_kwargs: FakeEngine(),
    )

    with pytest.raises(EnvironmentSafetyError, match="validated loopback port"):
        backend_test.recreate_database(
            ORDINARY_URL,
            backend_test.DEDICATED_TEST_DATABASE_NAME,
        )

    assert executed_statements == []


def test_connection_endpoint_check_uses_the_client_socket_peer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed_fds: list[int] = []

    class FakeSocket:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def getpeername(self):
            return "127.0.0.1", 5432

    def fake_socket(*, fileno: int):
        observed_fds.append(fileno)
        return FakeSocket()

    monkeypatch.setattr(environment_safety.os, "dup", lambda fd: fd + 100)
    monkeypatch.setattr(environment_safety.socket, "socket", fake_socket)

    fake_connection = SimpleNamespace(
        connection=SimpleNamespace(
            driver_connection=SimpleNamespace(pgconn=SimpleNamespace(socket=17))
        )
    )
    environment_safety.validate_local_test_connection_endpoint(fake_connection, 5432)
    assert observed_fds == [117]


def test_localhost_must_resolve_only_to_loopback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        backend_test.socket,
        "getaddrinfo",
        lambda *_args, **_kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("203.0.113.10", 5432))
        ],
    )

    with pytest.raises(EnvironmentSafetyError, match="only to local loopback"):
        backend_test.validate_runner_database_urls(ORDINARY_URL, MIGRATION_URL)


@pytest.mark.parametrize(
    "values",
    [
        {},
        {"TEST_DATABASE_URL": ORDINARY_URL},
        {"MIGRATION_DATABASE_URL": MIGRATION_URL},
        {
            "TEST_DATABASE_URL": "not-a-url",
            "MIGRATION_DATABASE_URL": MIGRATION_URL,
        },
        {
            "TEST_DATABASE_URL": ORDINARY_URL,
            "MIGRATION_DATABASE_URL": "not-a-url",
        },
    ],
)
def test_missing_or_malformed_urls_are_rejected(
    values: dict[str, str],
    tmp_path: Path,
) -> None:
    with pytest.raises((backend_test.BackendTestRunnerError, EnvironmentSafetyError)):
        backend_test.load_runner_configuration(
            values,
            dotenv_path=tmp_path / "missing.env",
        )


def test_output_redacts_database_urls_and_passwords() -> None:
    encoded_url = ORDINARY_URL.replace("ordinary-secret", "encoded%40secret")
    output = backend_test.redact_output(
        f"failed for {ORDINARY_URL}; password=ordinary-secret; "
        f"other={encoded_url}; decoded=encoded@secret; "
        "encoded-fragment=encoded%40secret",
        database_urls=(ORDINARY_URL, encoded_url),
    )

    assert ORDINARY_URL not in output
    assert "ordinary-secret" not in output
    assert encoded_url not in output
    assert "encoded@secret" not in output
    assert "encoded%40secret" not in output
    assert "[REDACTED]" in output


def test_output_redacts_a_url_split_before_its_encoded_password() -> None:
    encoded_url = ORDINARY_URL.replace("ordinary-secret", "encoded%40secret")
    stream = io.StringIO()

    class FakeProcess:
        stdout = io.StringIO(
            "postgresql+psycopg://test-user:\n"
            "encoded%40secret@localhost:5432/pickup_lane_test_db\n"
        )

        def wait(self) -> int:
            return 0

    assert backend_test.run_pytest(
        ["backend/tests/platform"],
        environment={},
        database_urls=(encoded_url,),
        process_factory=lambda *_args, **_kwargs: FakeProcess(),
        output=stream,
    ) == 0
    assert "encoded%40secret" not in stream.getvalue()


def test_pytest_dots_and_failure_marker_are_visible_before_exit() -> None:
    stream = io.StringIO()

    class FakeStdout:
        def __init__(self) -> None:
            self.source = io.StringIO("..F [ 50%]\nfailure details\n")

        def read(self, size: int) -> str:
            if self.source.tell() == 3:
                assert stream.getvalue() == "..F"
            return self.source.read(size)

    class FakeProcess:
        stdout = FakeStdout()

        def wait(self) -> int:
            assert "failure details\n" in stream.getvalue()
            return 1

    assert backend_test.run_pytest(
        ["backend/tests/platform"],
        environment={},
        database_urls=(),
        process_factory=lambda *_args, **_kwargs: FakeProcess(),
        output=stream,
    ) == 1


@pytest.mark.parametrize(
    ("password", "first_fragment", "second_fragment"),
    [
        ("encoded@secret", "encoded@", "secret"),
        ("encoded%40secret", "encoded%40", "secret"),
    ],
)
def test_output_redacts_a_password_split_across_lines(
    password: str,
    first_fragment: str,
    second_fragment: str,
) -> None:
    encoded_url = ORDINARY_URL.replace("ordinary-secret", "encoded%40secret")
    stream = io.StringIO()

    class FakeProcess:
        stdout = io.StringIO(f"password={first_fragment}\n{second_fragment}\n")

        def wait(self) -> int:
            return 0

    assert backend_test.run_pytest(
        ["backend/tests/platform"],
        environment={},
        database_urls=(encoded_url,),
        process_factory=lambda *_args, **_kwargs: FakeProcess(),
        output=stream,
    ) == 0
    assert password not in stream.getvalue()
    assert first_fragment not in stream.getvalue()
    assert second_fragment not in stream.getvalue()


def test_invalid_cli_argument_does_not_echo_database_credentials(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit):
        backend_test.build_argument_parser().parse_args(
            ["rebuild", "ordinary", ORDINARY_URL]
        )

    assert ORDINARY_URL not in capsys.readouterr().err


def test_fingerprint_changes_when_canonical_migration_content_changes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    ini_path = tmp_path / "alembic.ini"
    env_path = tmp_path / "env.py"
    versions_path = tmp_path / "versions"
    versions_path.mkdir()
    migration_path = versions_path / "0001_create_users_table.py"
    ini_path.write_text("[alembic]\n", encoding="utf-8")
    env_path.write_text("# env\n", encoding="utf-8")
    migration_path.write_text("revision = '0001'\n", encoding="utf-8")
    monkeypatch.setattr(backend_test, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(backend_test, "ALEMBIC_INI_PATH", ini_path)
    monkeypatch.setattr(backend_test, "ALEMBIC_ENV_PATH", env_path)
    monkeypatch.setattr(backend_test, "ALEMBIC_VERSIONS_PATH", versions_path)

    original = backend_test.migration_source_fingerprint()
    migration_path.write_text("revision = '0001'\n# edited\n", encoding="utf-8")

    assert backend_test.migration_source_fingerprint() != original


def test_stale_schema_state_requires_the_exact_rebuild_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = backend_test.OrdinarySchemaState(
        expected_head="0065",
        actual_revisions=("0065",),
        expected_fingerprint="expected",
        stored_fingerprint="old",
    )

    assert state.is_current is False
    monkeypatch.setattr(backend_test, "inspect_ordinary_schema", lambda _config: state)
    with pytest.raises(
        backend_test.BackendTestRunnerError,
        match="rebuild ordinary",
    ):
        backend_test.require_current_ordinary_schema(object())
    assert (
        backend_test.REBUILD_ORDINARY_COMMAND
        in backend_test._ordinary_rebuild_required_message()
    )


def test_schema_fingerprint_marker_contains_only_fixed_prefix_and_hex_digest() -> None:
    marker = backend_test.schema_fingerprint_marker("a" * 64)

    assert marker == f"{backend_test.SCHEMA_FINGERPRINT_PREFIX}{'a' * 64}"
    assert "'" not in marker
    assert "shobj_description" in backend_test.DATABASE_COMMENT_QUERY


def test_database_lock_rejects_a_conflicting_runner_operation(
    tmp_path: Path,
) -> None:
    target = backend_test.validate_runner_database_urls(
        ORDINARY_URL,
        MIGRATION_URL,
    )[0]

    with (
        backend_test.database_operation_lock(target, lock_root=tmp_path),
        pytest.raises(
            backend_test.BackendTestRunnerError,
            match="already owns",
        ),
        backend_test.database_operation_lock(target, lock_root=tmp_path),
    ):
        pass


def test_loopback_aliases_share_the_same_database_lock(tmp_path: Path) -> None:
    localhost_target = backend_test.validate_runner_database_urls(
        ORDINARY_URL,
        MIGRATION_URL,
    )[0]
    loopback_target = backend_test.validate_runner_database_urls(
        ORDINARY_URL.replace("localhost", "127.0.0.1"),
        MIGRATION_URL.replace("localhost", "127.0.0.1"),
    )[0]

    assert backend_test._lock_path(localhost_target, tmp_path) == backend_test._lock_path(
        loopback_target,
        tmp_path,
    )
    with (
        backend_test.database_operation_lock(localhost_target, lock_root=tmp_path),
        pytest.raises(backend_test.BackendTestRunnerError, match="already owns"),
        backend_test.database_operation_lock(loopback_target, lock_root=tmp_path),
    ):
        pass


def test_default_lock_root_does_not_follow_tmpdir(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = backend_test.validate_runner_database_urls(ORDINARY_URL, MIGRATION_URL)[0]
    observed_roots: list[Path] = []

    def capture_lock_path(_target, lock_root: Path) -> Path:
        observed_roots.append(lock_root)
        return tmp_path / "shared.lock"

    monkeypatch.setattr(backend_test, "_lock_path", capture_lock_path)
    for value in (str(tmp_path / "first"), str(tmp_path / "second")):
        monkeypatch.setenv("TMPDIR", value)
        with backend_test.database_operation_lock(target):
            pass

    assert observed_roots == [Path("/tmp"), Path("/tmp")]


def test_destructive_rebuild_rejects_a_url_target_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_engine_called = False

    def fail_if_called(*_args, **_kwargs):
        nonlocal create_engine_called
        create_engine_called = True
        raise AssertionError("database engine must not be created")

    monkeypatch.setattr(backend_test, "create_engine", fail_if_called)

    with pytest.raises(backend_test.BackendTestRunnerError, match="does not match"):
        backend_test.recreate_database(
            ORDINARY_URL,
            backend_test.DEDICATED_MIGRATION_TEST_DATABASE_NAME,
        )

    assert create_engine_called is False


def test_runner_configuration_rejects_targets_from_different_urls() -> None:
    ordinary_target, migration_target = backend_test.validate_runner_database_urls(
        ORDINARY_URL,
        MIGRATION_URL,
    )

    with pytest.raises(backend_test.BackendTestRunnerError, match="must match"):
        backend_test.RunnerConfiguration(
            ordinary_url=ORDINARY_URL,
            migration_url=MIGRATION_URL,
            ordinary_target=migration_target,
            migration_target=ordinary_target,
        )


def test_ordinary_test_runs_lock_both_database_targets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ordinary_target, migration_target = backend_test.validate_runner_database_urls(
        ORDINARY_URL,
        MIGRATION_URL,
    )
    configuration = backend_test.RunnerConfiguration(
        ordinary_url=ORDINARY_URL,
        migration_url=MIGRATION_URL,
        ordinary_target=ordinary_target,
        migration_target=migration_target,
    )
    locked_targets = []

    @contextmanager
    def capture_locks(targets):
        locked_targets.extend(targets)
        yield

    monkeypatch.setattr(backend_test, "database_operation_locks", capture_locks)
    monkeypatch.setattr(
        backend_test,
        "require_current_ordinary_schema",
        lambda _configuration: None,
    )
    monkeypatch.setattr(backend_test, "run_pytest", lambda *_args, **_kwargs: 0)

    assert backend_test.test_ordinary_database(configuration, ["backend/tests"]) == 0
    assert locked_targets == [ordinary_target, migration_target]


def test_migration_test_runs_lock_both_targets_and_validate_ordinary_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ordinary_target, migration_target = backend_test.validate_runner_database_urls(
        ORDINARY_URL,
        MIGRATION_URL,
    )
    configuration = backend_test.RunnerConfiguration(
        ordinary_url=ORDINARY_URL,
        migration_url=MIGRATION_URL,
        ordinary_target=ordinary_target,
        migration_target=migration_target,
    )
    operations: list[object] = []

    @contextmanager
    def capture_locks(targets):
        operations.append(("locks", tuple(targets)))
        yield

    monkeypatch.setattr(backend_test, "database_operation_locks", capture_locks)
    monkeypatch.setattr(
        backend_test,
        "require_current_ordinary_schema",
        lambda _configuration: operations.append("verify-ordinary"),
    )
    monkeypatch.setattr(
        backend_test,
        "run_pytest",
        lambda *_args, **_kwargs: operations.append("pytest") or 0,
    )

    assert backend_test.test_migration_database(configuration, ["backend/tests"]) == 0
    assert operations == [
        ("locks", (ordinary_target, migration_target)),
        "verify-ordinary",
        "pytest",
    ]


def test_changed_migration_source_is_rejected_before_fingerprint_recording(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        backend_test,
        "migration_source_fingerprint",
        lambda: "changed",
    )

    with pytest.raises(backend_test.BackendTestRunnerError, match="changed while"):
        backend_test.require_unchanged_migration_source("applied")


def test_rebuild_all_recreates_both_databases_and_prepares_only_ordinary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ordinary_target, migration_target = backend_test.validate_runner_database_urls(
        ORDINARY_URL,
        MIGRATION_URL,
    )
    configuration = backend_test.RunnerConfiguration(
        ordinary_url=ORDINARY_URL,
        migration_url=MIGRATION_URL,
        ordinary_target=ordinary_target,
        migration_target=migration_target,
    )
    operations: list[object] = []

    @contextmanager
    def capture_locks(targets):
        operations.append(("locks", tuple(targets)))
        yield

    monkeypatch.setattr(backend_test, "database_operation_locks", capture_locks)
    monkeypatch.setattr(
        backend_test,
        "recreate_database",
        lambda url, name: operations.append(("recreate", url, name)),
    )
    monkeypatch.setattr(
        backend_test,
        "migration_source_fingerprint",
        lambda: "source-fingerprint",
    )
    monkeypatch.setattr(
        backend_test,
        "apply_migrations_to_ordinary_database",
        lambda _configuration: operations.append("migrate-ordinary"),
    )
    monkeypatch.setattr(
        backend_test,
        "record_ordinary_schema_fingerprint",
        lambda _configuration, fingerprint: operations.append(
            ("fingerprint-ordinary", fingerprint)
        ),
    )
    monkeypatch.setattr(
        backend_test,
        "require_current_ordinary_schema",
        lambda _configuration: operations.append("verify-ordinary"),
    )

    backend_test.rebuild_all_databases(configuration)

    assert operations == [
        ("locks", (ordinary_target, migration_target)),
        (
            "recreate",
            MIGRATION_URL,
            backend_test.DEDICATED_MIGRATION_TEST_DATABASE_NAME,
        ),
        ("recreate", ORDINARY_URL, backend_test.DEDICATED_TEST_DATABASE_NAME),
        "migrate-ordinary",
        ("fingerprint-ordinary", "source-fingerprint"),
        "verify-ordinary",
    ]


def test_pytest_arguments_are_forwarded_without_rewriting() -> None:
    calls: list[dict[str, object]] = []

    class FakeProcess:
        stdout = iter(("one passed\n",))

        def wait(self) -> int:
            return 0

    def fake_process(command, **kwargs):
        calls.append({"command": command, **kwargs})
        return FakeProcess()

    pytest_arguments = [
        "backend/tests/platform/settings/test_backend_settings_contract.py::test_name",
        "-q",
        "-k",
        "safe and exact",
    ]
    output = io.StringIO()

    result = backend_test.run_pytest(
        pytest_arguments,
        environment={"APP_ENV": "test"},
        database_urls=(ORDINARY_URL, MIGRATION_URL),
        process_factory=fake_process,
        output=output,
    )

    assert result == 0
    assert calls[0]["command"] == [
        backend_test.sys.executable,
        "-m",
        "pytest",
        *pytest_arguments,
    ]
    assert calls[0]["env"] == {"APP_ENV": "test"}
    assert output.getvalue() == "one passed\n"


def test_pytest_requires_an_existing_backend_tests_selection_first() -> None:
    with pytest.raises(backend_test.BackendTestRunnerError, match="selection"):
        backend_test.pytest_command(["-q"])

    with pytest.raises(backend_test.BackendTestRunnerError, match="backend/tests"):
        backend_test.pytest_command(["backend/settings.py", "-q"])

    assert backend_test.pytest_command(["backend/tests", "-q"]) == [
        backend_test.sys.executable,
        "-m",
        "pytest",
        "backend/tests",
        "-q",
    ]


@pytest.mark.parametrize(
    "unsafe_arguments",
    [
        ["--noconftest"],
        ["--confcutdir", "backend/tests/platform"],
        ["--confcutdir=backend/tests/platform"],
        ["-c", "backend/tests/platform/setup.cfg"],
        ["-cbackend/tests/platform/setup.cfg"],
        ["-qc", "backend/tests/platform/setup.cfg"],
        ["-qo", "addopts=--noconftest"],
        ["-o", "addopts=--noconftest"],
        ["-p", "no:backend.tests.conftest"],
        ["--override-ini=addopts=--noconftest"],
        ["--pyargs"],
        ["--rootdir=backend/tests/platform"],
    ],
)
def test_pytest_rejects_options_that_can_bypass_root_safety_fixtures(
    unsafe_arguments: list[str],
) -> None:
    with pytest.raises(backend_test.BackendTestRunnerError, match="safety fixtures"):
        backend_test.pytest_command(["backend/tests/platform", *unsafe_arguments])


def test_pytest_rejects_a_later_selection_outside_the_guarded_tree() -> None:
    with pytest.raises(backend_test.BackendTestRunnerError, match="backend/tests"):
        backend_test.pytest_command(
            ["backend/tests/platform", "-q", "backend/settings.py"]
        )


def test_pytest_rejects_argument_files_before_pytest_expands_them(
    tmp_path: Path,
) -> None:
    argument_file = tmp_path / "unsafe-pytest-arguments"
    argument_file.write_text("--noconftest\nbackend/settings.py\n")
    with pytest.raises(backend_test.BackendTestRunnerError, match="argument files"):
        backend_test.pytest_command(
            ["backend/tests/platform", f"@{argument_file}"]
        )


def test_pytest_preserves_safe_multiple_selections_and_options() -> None:
    arguments = [
        "backend/tests/platform",
        "-q",
        "-k",
        "safe and exact",
        "backend/tests/migrations",
        "--junitxml=/tmp/backend-results.xml",
    ]
    assert backend_test.pytest_command(arguments) == [
        backend_test.sys.executable, "-m", "pytest", *arguments
    ]


def test_connected_database_identity_rejects_a_wrong_database_before_sql(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executed: list[str] = []
    monkeypatch.setattr(
        environment_safety,
        "_connection_socket_peer",
        lambda _connection: ("127.0.0.1", 5432),
    )

    class FakeConnection:
        def exec_driver_sql(self, statement: str):
            executed.append(statement)
            return SimpleNamespace(scalar_one=lambda: "pickup_lane_db_dev")

    with pytest.raises(EnvironmentSafetyError, match="does not match"):
        environment_safety.validate_local_test_connection_identity(
            FakeConnection(), "pickup_lane_test_db", 5432
        )
    assert executed == ["SELECT current_database()"]


def test_cleanup_refuses_a_misbound_engine_before_truncate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executed: list[str] = []
    monkeypatch.setenv("DATABASE_URL", ORDINARY_URL)
    monkeypatch.setattr(backend_conftest, "_test_uses_database", lambda _request: True)
    monkeypatch.setattr(
        environment_safety,
        "_connection_socket_peer",
        lambda _connection: ("127.0.0.1", 5432),
    )

    class FakeConnection:
        def exec_driver_sql(self, statement: str):
            executed.append(statement)
            return SimpleNamespace(scalar_one=lambda: "pickup_lane_db_dev")

    class FakeEngine:
        @contextmanager
        def connect(self):
            yield FakeConnection()

    monkeypatch.setattr("backend.database.engine", FakeEngine())
    fixture = backend_conftest.clean_database.__wrapped__(object())
    with pytest.raises(EnvironmentSafetyError, match="does not match"):
        next(fixture)
    assert executed == ["SELECT current_database()"]


def test_schema_fingerprint_write_refuses_a_misbound_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ordinary_target, migration_target = backend_test.validate_runner_database_urls(
        ORDINARY_URL, MIGRATION_URL
    )
    configuration = backend_test.RunnerConfiguration(
        ordinary_url=ORDINARY_URL,
        migration_url=MIGRATION_URL,
        ordinary_target=ordinary_target,
        migration_target=migration_target,
    )
    executed: list[str] = []
    monkeypatch.setattr(
        environment_safety,
        "_connection_socket_peer",
        lambda _connection: ("127.0.0.1", 5432),
    )

    class FakeConnection:
        def exec_driver_sql(self, statement: str):
            executed.append(statement)
            return SimpleNamespace(scalar_one=lambda: "pickup_lane_db_dev")

    class FakeEngine:
        @contextmanager
        def begin(self):
            yield FakeConnection()

        def dispose(self):
            pass

    monkeypatch.setattr(backend_test, "_database_engine", lambda _url: FakeEngine())
    with pytest.raises(EnvironmentSafetyError, match="does not match"):
        backend_test.record_ordinary_schema_fingerprint(configuration, "a" * 64)
    assert executed == ["SELECT current_database()"]


@pytest.mark.parametrize(
    ("connected_name", "expected_operations"),
    [
        ("pickup_lane_migration_test_db", ["identity", "commit", "configure", "migrate"]),
        ("pickup_lane_db_dev", ["identity"]),
    ],
)
def test_alembic_test_override_checks_identity_and_commits_before_migrations(
    monkeypatch: pytest.MonkeyPatch,
    connected_name: str,
    expected_operations: list[str],
) -> None:
    operations: list[str] = []

    class FakeConfig:
        config_file_name = None
        config_ini_section = "alembic"

        def __init__(self) -> None:
            self.attributes = {
                "pickup_lane_migration_test_database_url_override": MIGRATION_URL
            }

        def set_main_option(self, _name: str, _value: str) -> None:
            pass

        def get_section(self, _name: str, _default: object):
            return {}

    class FakeConnection:
        def exec_driver_sql(self, _statement: str):
            operations.append("identity")
            return SimpleNamespace(scalar_one=lambda: connected_name)

        def commit(self) -> None:
            operations.append("commit")

    class FakeEngine:
        @contextmanager
        def connect(self):
            yield FakeConnection()

    @contextmanager
    def fake_transaction():
        yield

    monkeypatch.setattr(
        environment_safety,
        "_connection_socket_peer",
        lambda _connection: ("127.0.0.1", 5432),
    )
    monkeypatch.setattr(alembic_context, "config", FakeConfig(), raising=False)
    monkeypatch.setattr(
        alembic_context, "is_offline_mode", lambda: False, raising=False
    )
    monkeypatch.setattr(
        alembic_context,
        "configure",
        lambda **_kwargs: operations.append("configure"),
        raising=False,
    )
    monkeypatch.setattr(
        alembic_context,
        "begin_transaction",
        fake_transaction,
        raising=False,
    )
    monkeypatch.setattr(
        alembic_context,
        "run_migrations",
        lambda: operations.append("migrate"),
        raising=False,
    )
    monkeypatch.setattr(
        sqlalchemy,
        "engine_from_config",
        lambda *_args, **_kwargs: FakeEngine(),
    )

    env_path = backend_test.REPO_ROOT / "backend" / "alembic" / "env.py"
    if connected_name == "pickup_lane_db_dev":
        with pytest.raises(EnvironmentSafetyError, match="does not match"):
            runpy.run_path(str(env_path))
    else:
        runpy.run_path(str(env_path))
    assert operations == expected_operations
