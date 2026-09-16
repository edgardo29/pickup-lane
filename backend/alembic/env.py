from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, make_url, pool

# Import models so their tables are registered on Base.metadata before Alembic
# reads the metadata for migrations.
import backend.models  # noqa: F401
from backend.database_metadata import Base
from backend.settings import (
    escape_alembic_config_url,
    get_migration_database_url,
    validate_migration_test_database_url,
    validate_ordinary_test_database_url,
)

config = context.config
database_url_override = config.attributes.get("pickup_lane_database_url_override")
migration_test_database_url_override = config.attributes.get(
    "pickup_lane_migration_test_database_url_override"
)
if database_url_override is not None and migration_test_database_url_override is not None:
    raise ValueError("Alembic cannot use both test database URL overrides.")
if database_url_override is not None or migration_test_database_url_override is not None:
    from backend.tests.support.environment_safety import (
        validate_test_database_connection_environment,
    )

    validate_test_database_connection_environment()
if database_url_override is not None:
    MIGRATION_DATABASE_URL = validate_ordinary_test_database_url(
        database_url_override,
        name="pickup_lane_database_url_override",
    )
elif migration_test_database_url_override is not None:
    MIGRATION_DATABASE_URL = validate_migration_test_database_url(
        migration_test_database_url_override,
        name="pickup_lane_migration_test_database_url_override",
    )
else:
    MIGRATION_DATABASE_URL = get_migration_database_url()
# ConfigParser interprets percent signs. A URL-encoded password must survive
# that interpolation unchanged before SQLAlchemy receives the URL.
config.set_main_option(
    "sqlalchemy.url", escape_alembic_config_url(MIGRATION_DATABASE_URL)
)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Alembic compares and runs migrations against this metadata collection.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    # Offline mode generates SQL without opening a live DB connection.
    context.configure(
        url=MIGRATION_DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # Online mode connects directly to PostgreSQL and applies migrations.
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        if (
            database_url_override is not None
            or migration_test_database_url_override is not None
        ):
            from backend.tests.support.environment_safety import (
                DEDICATED_MIGRATION_TEST_DATABASE_NAME,
                DEDICATED_TEST_DATABASE_NAME,
                validate_local_test_connection_identity,
            )

            validate_local_test_connection_identity(
                connection,
                DEDICATED_TEST_DATABASE_NAME
                if database_url_override is not None
                else DEDICATED_MIGRATION_TEST_DATABASE_NAME,
                make_url(MIGRATION_DATABASE_URL).port or 5432,
            )
            # The identity SELECT autobegins a transaction. Let Alembic own
            # the migration transaction so successful revisions are committed.
            connection.commit()
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
