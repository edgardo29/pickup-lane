from __future__ import annotations

import os
from pathlib import Path

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from backend.tests.support.migration_test_database import (
    MIGRATION_DATABASE_ADVISORY_LOCK_ID,
    alembic_head_revision,
    alembic_parent_revision,
    current_database_revision,
    migration_database_targets_from_environment,
    model_schema_drift,
    reset_migration_database,
    run_alembic_upgrade,
    schema_object_names,
)

pytestmark = pytest.mark.migration_lifecycle

_SYNTHETIC_INTERRUPTION_REVISION = "ws04_03a_interruption"
_INTERRUPTION_MARKER_TABLE = "ws04_03a_interruption_marker"


@pytest.mark.requirement("WS04-03A-R3", "WS04-03A-R4", "WS04-03A-R7", "WS04-03A-R8")
def test_empty_database_upgrades_to_head_and_has_no_model_schema_drift(
    migration_database,
) -> None:
    assert current_database_revision(migration_database.engine) is None

    run_alembic_upgrade("head")

    assert current_database_revision(migration_database.engine) == alembic_head_revision()
    assert model_schema_drift(migration_database.engine) == ()


@pytest.mark.requirement("WS04-03A-R4", "WS04-03A-R7", "WS04-03A-R8")
def test_prior_revision_upgrades_to_head_and_reruns_cleanly(migration_database) -> None:
    head_revision = alembic_head_revision()
    prior_revision = alembic_parent_revision(head_revision)

    run_alembic_upgrade(prior_revision)
    assert current_database_revision(migration_database.engine) == prior_revision

    run_alembic_upgrade("head")
    assert current_database_revision(migration_database.engine) == head_revision

    run_alembic_upgrade("head")
    assert current_database_revision(migration_database.engine) == head_revision


@pytest.mark.requirement("WS04-03A-R4", "WS04-03A-R6", "WS04-03A-R7", "WS04-03A-R8")
def test_migration_database_reset_restores_genuine_empty_state(migration_database) -> None:
    run_alembic_upgrade("head")
    assert "alembic_version" in schema_object_names(migration_database.engine)

    reset_migration_database(migration_database.engine)

    assert current_database_revision(migration_database.engine) is None
    assert "alembic_version" not in schema_object_names(migration_database.engine)
    assert "users" not in schema_object_names(migration_database.engine)


@pytest.mark.requirement("WS04-03A-R4", "WS04-03A-R6", "WS04-03A-R7", "WS04-03A-R8")
def test_migration_advisory_lock_serializes_overlapping_lifecycle_attempts() -> None:
    migration_database_targets_from_environment()
    engine = create_engine(os.environ["MIGRATION_DATABASE_URL"], poolclass=NullPool)
    try:
        with engine.connect() as first, engine.connect() as second:
            assert first.execute(
                text("SELECT pg_try_advisory_lock(:lock_id)"),
                {"lock_id": MIGRATION_DATABASE_ADVISORY_LOCK_ID},
            ).scalar_one() is True

            assert second.execute(
                text("SELECT pg_try_advisory_lock(:lock_id)"),
                {"lock_id": MIGRATION_DATABASE_ADVISORY_LOCK_ID},
            ).scalar_one() is False

            assert first.execute(
                text("SELECT pg_advisory_unlock(:lock_id)"),
                {"lock_id": MIGRATION_DATABASE_ADVISORY_LOCK_ID},
            ).scalar_one() is True
            first.commit()

            assert second.execute(
                text("SELECT pg_try_advisory_lock(:lock_id)"),
                {"lock_id": MIGRATION_DATABASE_ADVISORY_LOCK_ID},
            ).scalar_one() is True
            assert second.execute(
                text("SELECT pg_advisory_unlock(:lock_id)"),
                {"lock_id": MIGRATION_DATABASE_ADVISORY_LOCK_ID},
            ).scalar_one() is True
            second.commit()
    finally:
        engine.dispose()


@pytest.mark.requirement("WS04-03A-R6", "WS04-03A-R7", "WS04-03A-R8")
def test_controlled_alembic_interruption_is_inspectable_and_recoverable(
    migration_database,
    tmp_path: Path,
) -> None:
    failing_config = _synthetic_interruption_alembic_config(
        tmp_path,
        os.environ["MIGRATION_DATABASE_URL"],
        fail_during_upgrade=True,
    )

    with pytest.raises(RuntimeError, match="controlled alembic interruption"):
        command.upgrade(failing_config, "head")

    assert current_database_revision(migration_database.engine) is None
    assert _INTERRUPTION_MARKER_TABLE not in schema_object_names(
        migration_database.engine
    )

    repaired_config = _synthetic_interruption_alembic_config(
        tmp_path,
        os.environ["MIGRATION_DATABASE_URL"],
        fail_during_upgrade=False,
    )

    command.upgrade(repaired_config, "head")
    assert current_database_revision(migration_database.engine) == (
        _SYNTHETIC_INTERRUPTION_REVISION
    )
    assert _INTERRUPTION_MARKER_TABLE in schema_object_names(migration_database.engine)

    command.upgrade(repaired_config, "head")
    assert current_database_revision(migration_database.engine) == (
        _SYNTHETIC_INTERRUPTION_REVISION
    )

    reset_migration_database(migration_database.engine)
    assert current_database_revision(migration_database.engine) is None
    assert _INTERRUPTION_MARKER_TABLE not in schema_object_names(
        migration_database.engine
    )


def _synthetic_interruption_alembic_config(
    tmp_path: Path,
    database_url: str,
    *,
    fail_during_upgrade: bool,
) -> Config:
    script_location = tmp_path / "synthetic_interruption_alembic"
    versions_dir = script_location / "versions"
    versions_dir.mkdir(parents=True, exist_ok=True)
    (script_location / "env.py").write_text(
        "from alembic import context\n"
        "from sqlalchemy import create_engine, pool\n\n"
        "config = context.config\n\n"
        "def run_migrations_online():\n"
        "    engine = create_engine(\n"
        "        config.get_main_option('sqlalchemy.url'),\n"
        "        poolclass=pool.NullPool,\n"
        "    )\n"
        "    try:\n"
        "        with engine.connect() as connection:\n"
        "            context.configure(connection=connection)\n"
        "            with context.begin_transaction():\n"
        "                context.run_migrations()\n"
        "    finally:\n"
        "        engine.dispose()\n\n"
        "if context.is_offline_mode():\n"
        "    raise RuntimeError('offline migration rehearsal is not supported')\n"
        "run_migrations_online()\n"
    )
    failure_line = (
        "    raise RuntimeError('controlled alembic interruption')\n"
        if fail_during_upgrade
        else ""
    )
    (versions_dir / "0001_ws04_03a_interruption.py").write_text(
        "from alembic import op\n"
        "import sqlalchemy as sa\n\n"
        f"revision = {_SYNTHETIC_INTERRUPTION_REVISION!r}\n"
        "down_revision = None\n"
        "branch_labels = None\n"
        "depends_on = None\n\n"
        "def upgrade():\n"
        f"    op.create_table({_INTERRUPTION_MARKER_TABLE!r}, "
        "sa.Column('id', sa.Integer, primary_key=True))\n"
        f"    op.execute('INSERT INTO {_INTERRUPTION_MARKER_TABLE} (id) VALUES (1)')\n"
        f"{failure_line}"
        "\n"
        "def downgrade():\n"
        f"    op.drop_table({_INTERRUPTION_MARKER_TABLE!r})\n"
    )
    config = Config()
    config.set_main_option("script_location", str(script_location))
    config.set_main_option("sqlalchemy.url", database_url)
    return config
