from __future__ import annotations

import os
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.pool import NullPool

import backend.models  # noqa: F401 - register model metadata for drift checks.
from backend.database_metadata import Base
from backend.settings import reset_settings_cache
from backend.tests.support.environment_safety import (
    EnvironmentSafetyError,
    MigrationTestDatabaseTargets,
    validate_migration_test_database_urls,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
ALEMBIC_INI_PATH = REPO_ROOT / "alembic.ini"
MIGRATION_DATABASE_ADVISORY_LOCK_ID = 740_403_001


@dataclass(frozen=True)
class MigrationDatabaseContext:
    engine: Engine
    targets: MigrationTestDatabaseTargets


def migration_database_targets_from_environment() -> MigrationTestDatabaseTargets:
    database_url = os.environ.get("DATABASE_URL", "")
    migration_database_url = os.environ.get("MIGRATION_DATABASE_URL", "")
    if not migration_database_url:
        raise EnvironmentSafetyError(
            "MIGRATION_DATABASE_URL is required for migration lifecycle tests."
        )
    return validate_migration_test_database_urls(database_url, migration_database_url)


@contextmanager
def locked_migration_database() -> Iterator[MigrationDatabaseContext]:
    targets = migration_database_targets_from_environment()
    migration_url = os.environ["MIGRATION_DATABASE_URL"]
    engine = create_engine(migration_url, poolclass=NullPool)
    try:
        with engine.connect() as lock_connection:
            lock_connection.execute(
                text("SELECT pg_advisory_lock(:lock_id)"),
                {"lock_id": MIGRATION_DATABASE_ADVISORY_LOCK_ID},
            )
            lock_connection.commit()
            try:
                yield MigrationDatabaseContext(engine=engine, targets=targets)
            finally:
                if lock_connection.in_transaction():
                    lock_connection.rollback()
                lock_connection.execute(
                    text("SELECT pg_advisory_unlock(:lock_id)"),
                    {"lock_id": MIGRATION_DATABASE_ADVISORY_LOCK_ID},
                )
                lock_connection.commit()
    finally:
        engine.dispose()


def reset_migration_database(engine: Engine) -> None:
    migration_database_targets_from_environment()
    with engine.begin() as connection:
        connection.execute(text("DROP EXTENSION IF EXISTS pg_trgm CASCADE"))
        _drop_public_views(connection)
        _drop_public_tables(connection)
        _drop_public_sequences(connection)
        _drop_public_types(connection)


def _drop_public_views(connection: Connection) -> None:
    view_names = _public_class_names(connection, "relkind IN ('m', 'v')")
    for view_name in view_names:
        connection.execute(text(f"DROP VIEW IF EXISTS {view_name} CASCADE"))


def _drop_public_tables(connection: Connection) -> None:
    table_names = _public_class_names(connection, "relkind IN ('p', 'r')")
    for table_name in table_names:
        connection.execute(text(f"DROP TABLE IF EXISTS {table_name} CASCADE"))


def _drop_public_sequences(connection: Connection) -> None:
    sequence_names = _public_class_names(connection, "relkind = 'S'")
    for sequence_name in sequence_names:
        connection.execute(text(f"DROP SEQUENCE IF EXISTS {sequence_name} CASCADE"))


def _drop_public_types(connection: Connection) -> None:
    type_names = connection.execute(
        text(
            """
            SELECT format('%I.%I', pg_namespace.nspname, pg_type.typname)
            FROM pg_type
            JOIN pg_namespace ON pg_namespace.oid = pg_type.typnamespace
            LEFT JOIN pg_class ON pg_class.oid = pg_type.typrelid
            WHERE pg_namespace.nspname = 'public'
              AND pg_type.typtype IN ('d', 'e')
              AND pg_class.oid IS NULL
            ORDER BY pg_type.typname
            """
        )
    ).scalars()
    for type_name in type_names:
        connection.execute(text(f"DROP TYPE IF EXISTS {type_name} CASCADE"))


def _public_class_names(connection: Connection, relkind_predicate: str) -> tuple[str, ...]:
    rows = connection.execute(
        text(
            f"""
            SELECT format('%I.%I', pg_namespace.nspname, pg_class.relname)
            FROM pg_class
            JOIN pg_namespace ON pg_namespace.oid = pg_class.relnamespace
            WHERE pg_namespace.nspname = 'public'
              AND {relkind_predicate}
            ORDER BY pg_class.relname
            """
        )
    ).scalars()
    return tuple(rows)


def alembic_config() -> Config:
    return Config(str(ALEMBIC_INI_PATH))


def alembic_script_directory() -> ScriptDirectory:
    return ScriptDirectory.from_config(alembic_config())


def alembic_head_revision() -> str:
    heads = alembic_script_directory().get_heads()
    if len(heads) != 1:
        raise AssertionError(f"expected one Alembic head; got {heads!r}")
    return heads[0]


def alembic_parent_revision(revision: str) -> str:
    script = alembic_script_directory()
    revision_script = script.get_revision(revision)
    if revision_script is None:
        raise AssertionError(f"unknown Alembic revision: {revision}")
    parent = revision_script.down_revision
    if not isinstance(parent, str):
        raise AssertionError(f"expected one parent revision for {revision}; got {parent!r}")
    return parent


def run_alembic_upgrade(revision: str = "head") -> None:
    migration_database_targets_from_environment()
    reset_settings_cache()
    try:
        command.upgrade(alembic_config(), revision)
    finally:
        reset_settings_cache()


def current_database_revision(engine: Engine) -> str | None:
    with engine.connect() as connection:
        table_exists = connection.execute(
            text("SELECT to_regclass('public.alembic_version')")
        ).scalar_one()
        if table_exists is None:
            return None
        return connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one_or_none()


def schema_object_names(engine: Engine) -> tuple[str, ...]:
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT relname
                FROM pg_class
                JOIN pg_namespace ON pg_namespace.oid = pg_class.relnamespace
                WHERE pg_namespace.nspname = 'public'
                  AND relkind IN ('r', 'p', 'v', 'm', 'S', 'i')
                ORDER BY relname
                """
            )
        ).scalars()
        return tuple(rows)


def model_schema_drift(engine: Engine) -> tuple[str, ...]:
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        raw_diffs = compare_metadata(context, Base.metadata)
    return tuple(
        repr(diff)
        for diff in raw_diffs
        if not _ignored_autogenerate_diff(diff)
    )


def _ignored_autogenerate_diff(diff: object) -> bool:
    if not isinstance(diff, tuple) or not diff:
        return False
    operation = diff[0]
    if operation == "remove_table" and len(diff) >= 2:
        table = diff[1]
        return getattr(table, "name", None) == "alembic_version"
    return False
