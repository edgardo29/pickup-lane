from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from backend.tests.support import environment_safety, migration_test_database
from backend.tests.support.environment_safety import (
    DEDICATED_MIGRATION_TEST_DATABASE_NAME,
    DEDICATED_TEST_DATABASE_NAME,
    EnvironmentSafetyError,
    validate_dedicated_migration_test_database_url,
    validate_dedicated_test_database_url,
    validate_migration_test_database_urls,
)
from backend.tests.support.migration_test_database import (
    migration_database_targets_from_environment,
    reset_migration_database,
    run_alembic_upgrade,
)

pytestmark = pytest.mark.no_db_cleanup

_APP_DATABASE_URL = (
    "postgresql+psycopg://postgres:postgres@localhost:5432/"
    f"{DEDICATED_TEST_DATABASE_NAME}"
)
_MIGRATION_DATABASE_URL = (
    "postgresql+psycopg://postgres:postgres@localhost:5432/"
    f"{DEDICATED_MIGRATION_TEST_DATABASE_NAME}"
)


@pytest.mark.requirement("WS04-03A-R4", "WS04-03A-R7", "WS04-03A-R8")
def test_migration_database_validation_accepts_exact_purpose_databases() -> None:
    targets = validate_migration_test_database_urls(
        _APP_DATABASE_URL,
        _MIGRATION_DATABASE_URL,
    )

    assert targets.application_database.database_name == DEDICATED_TEST_DATABASE_NAME
    assert (
        targets.migration_database.database_name
        == DEDICATED_MIGRATION_TEST_DATABASE_NAME
    )
    assert targets.application_database.host == targets.migration_database.host
    assert targets.application_database.port == targets.migration_database.port
    assert validate_dedicated_test_database_url(_APP_DATABASE_URL).database_name == (
        DEDICATED_TEST_DATABASE_NAME
    )
    assert validate_dedicated_migration_test_database_url(
        _MIGRATION_DATABASE_URL
    ).database_name == DEDICATED_MIGRATION_TEST_DATABASE_NAME


@pytest.mark.requirement("WS04-03A-R4", "WS04-03A-R8")
@pytest.mark.parametrize(
    "migration_database_url",
    [
        "",
        _APP_DATABASE_URL,
        "postgresql+psycopg://postgres:postgres@localhost:5432/pickup_lane_db_dev",
        "postgresql+psycopg://postgres:postgres@localhost:5432/pickup_lane_test_db_backup",
        "postgresql+psycopg://postgres:postgres@other-db.local:5432/"
        f"{DEDICATED_MIGRATION_TEST_DATABASE_NAME}",
        "postgresql+psycopg://postgres:postgres@localhost:6543/"
        f"{DEDICATED_MIGRATION_TEST_DATABASE_NAME}",
        f"sqlite:///{DEDICATED_MIGRATION_TEST_DATABASE_NAME}",
        f"postgresql+psycopg:///{DEDICATED_MIGRATION_TEST_DATABASE_NAME}",
        "not-a-database-url",
    ],
)
def test_migration_database_validation_rejects_unsafe_targets(
    migration_database_url: str,
) -> None:
    with pytest.raises(EnvironmentSafetyError):
        validate_migration_test_database_urls(
            _APP_DATABASE_URL,
            migration_database_url,
        )


@pytest.mark.requirement("WS04-03A-R4", "WS04-03A-R8")
def test_migration_lifecycle_environment_requires_migration_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", _APP_DATABASE_URL)
    monkeypatch.delenv("MIGRATION_DATABASE_URL", raising=False)

    with pytest.raises(EnvironmentSafetyError, match="MIGRATION_DATABASE_URL is required"):
        migration_database_targets_from_environment()


@pytest.mark.requirement("WS04-03A-R4", "WS04-03A-R8")
def test_migration_lifecycle_environment_rejects_application_database_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", _APP_DATABASE_URL)
    monkeypatch.setenv("MIGRATION_DATABASE_URL", _APP_DATABASE_URL)

    with pytest.raises(EnvironmentSafetyError):
        migration_database_targets_from_environment()


@pytest.mark.parametrize(
    ("ordinary_url", "migration_url"),
    [
        (
            _APP_DATABASE_URL.replace("localhost", "db.example.invalid"),
            (
                "postgresql+psycopg://postgres:postgres@db.example.invalid:5432/"
                "pickup_lane_migration_test_db"
            ),
        ),
        (_APP_DATABASE_URL, _MIGRATION_DATABASE_URL + "?host=db.example.invalid"),
    ],
)
def test_direct_migration_helpers_reject_nonlocal_or_overridden_targets(
    monkeypatch: pytest.MonkeyPatch,
    ordinary_url: str,
    migration_url: str,
) -> None:
    monkeypatch.setenv("DATABASE_URL", ordinary_url)
    monkeypatch.setenv("MIGRATION_DATABASE_URL", migration_url)
    with pytest.raises(EnvironmentSafetyError):
        migration_database_targets_from_environment()


def test_direct_upgrade_rejects_a_remote_migration_url_before_alembic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "DATABASE_URL", _APP_DATABASE_URL.replace("localhost", "db.example.invalid")
    )
    monkeypatch.setenv(
        "MIGRATION_DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@db.example.invalid:5432/"
        "pickup_lane_migration_test_db",
    )
    monkeypatch.setattr(
        migration_test_database.command,
        "upgrade",
        lambda *_args: pytest.fail("Alembic must not run for a remote URL"),
    )

    with pytest.raises(EnvironmentSafetyError):
        run_alembic_upgrade("head")


def test_direct_reset_rejects_a_misbound_engine_before_drop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executed: list[str] = []
    monkeypatch.setenv("DATABASE_URL", _APP_DATABASE_URL)
    monkeypatch.setenv("MIGRATION_DATABASE_URL", _MIGRATION_DATABASE_URL)
    monkeypatch.setattr(
        environment_safety,
        "_connection_socket_peer",
        lambda _connection: ("127.0.0.1", 5432),
    )

    class FakeConnection:
        def exec_driver_sql(self, statement: str):
            executed.append(statement)
            return SimpleNamespace(scalar_one=lambda: "pickup_lane_test_db")

        def execute(self, statement):
            pytest.fail(f"destructive SQL must not run: {statement}")

    class FakeEngine:
        @contextmanager
        def begin(self):
            yield FakeConnection()

    with pytest.raises(EnvironmentSafetyError, match="does not match"):
        reset_migration_database(FakeEngine())
    assert executed == ["SELECT current_database()"]


def test_migration_upgrade_uses_the_validated_migration_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", _APP_DATABASE_URL)
    monkeypatch.setenv("MIGRATION_DATABASE_URL", _MIGRATION_DATABASE_URL)
    config = SimpleNamespace(attributes={}, config_ini_section="alembic")
    config.get_section = lambda *_args: {}
    monkeypatch.setattr(migration_test_database, "alembic_config", lambda: config)
    observed: list[tuple[str, str]] = []
    monkeypatch.setattr(
        migration_test_database.command,
        "upgrade",
        lambda supplied_config, revision: observed.append(
            (
                supplied_config.attributes[
                    "pickup_lane_migration_test_database_url_override"
                ],
                revision,
            )
        ),
    )

    run_alembic_upgrade("head")

    assert observed == [(_MIGRATION_DATABASE_URL, "head")]
