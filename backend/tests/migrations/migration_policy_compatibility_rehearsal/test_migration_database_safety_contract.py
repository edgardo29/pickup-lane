from __future__ import annotations

import pytest

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
