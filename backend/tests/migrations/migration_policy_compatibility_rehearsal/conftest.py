from __future__ import annotations

from collections.abc import Iterator

import pytest

from backend.tests.support.migration_test_database import (
    MigrationDatabaseContext,
    locked_migration_database,
    reset_migration_database,
)


@pytest.fixture
def migration_database() -> Iterator[MigrationDatabaseContext]:
    with locked_migration_database() as database:
        reset_migration_database(database.engine)
        try:
            yield database
        finally:
            reset_migration_database(database.engine)
