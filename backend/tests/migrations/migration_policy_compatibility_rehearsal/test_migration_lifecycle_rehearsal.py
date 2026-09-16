from __future__ import annotations

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.pool import NullPool

from backend.settings import escape_alembic_config_url
from backend.tests.support import environment_safety
from backend.tests.support.environment_safety import EnvironmentSafetyError
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
def test_clean_moderation_schema_has_no_durable_execution_duration(migration_database):
    run_alembic_upgrade("head")
    inspector = inspect(migration_database.engine)
    for table in (
        "admin_content_moderation_findings",
        "game_chat_message_detections",
        "sub_post_chat_message_detections",
    ):
        assert "execution_duration_us" not in {
            column["name"] for column in inspector.get_columns(table)
        }
        assert all(
            "execution_duration_us" not in constraint["sqltext"]
            for constraint in inspector.get_check_constraints(table)
        )
    assert model_schema_drift(migration_database.engine) == ()


@pytest.mark.requirement("WS04-03A-R3", "WS04-03A-R4", "WS04-03A-R7", "WS04-03A-R8")
def test_empty_database_upgrades_to_head_and_has_no_model_schema_drift(
    migration_database,
) -> None:
    assert current_database_revision(migration_database.engine) is None

    run_alembic_upgrade("head")

    assert (
        current_database_revision(migration_database.engine) == alembic_head_revision()
    )
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
def test_migration_database_reset_restores_genuine_empty_state(
    migration_database,
) -> None:
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
            assert (
                first.execute(
                    text("SELECT pg_try_advisory_lock(:lock_id)"),
                    {"lock_id": MIGRATION_DATABASE_ADVISORY_LOCK_ID},
                ).scalar_one()
                is True
            )

            assert (
                second.execute(
                    text("SELECT pg_try_advisory_lock(:lock_id)"),
                    {"lock_id": MIGRATION_DATABASE_ADVISORY_LOCK_ID},
                ).scalar_one()
                is False
            )

            assert (
                first.execute(
                    text("SELECT pg_advisory_unlock(:lock_id)"),
                    {"lock_id": MIGRATION_DATABASE_ADVISORY_LOCK_ID},
                ).scalar_one()
                is True
            )
            first.commit()

            assert (
                second.execute(
                    text("SELECT pg_try_advisory_lock(:lock_id)"),
                    {"lock_id": MIGRATION_DATABASE_ADVISORY_LOCK_ID},
                ).scalar_one()
                is True
            )
            assert (
                second.execute(
                    text("SELECT pg_advisory_unlock(:lock_id)"),
                    {"lock_id": MIGRATION_DATABASE_ADVISORY_LOCK_ID},
                ).scalar_one()
                is True
            )
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


def test_synthetic_alembic_checks_its_own_connection_before_migration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = (
        "postgresql+psycopg://test-user:encoded%40secret@localhost:5432/"
        "pickup_lane_migration_test_db"
    )
    config = _synthetic_interruption_alembic_config(
        tmp_path, database_url, fail_during_upgrade=False
    )
    assert config.get_main_option("sqlalchemy.url") == database_url

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

    class FakeEngine:
        def connect(self):
            return FakeConnection()

        def dispose(self):
            pass

    def reject_wrong_connection(_connection, expected_name: str, expected_port: int):
        assert expected_name == "pickup_lane_migration_test_db"
        assert expected_port == 5432
        raise EnvironmentSafetyError("misbound migration connection")

    monkeypatch.setattr("sqlalchemy.create_engine", lambda *_args, **_kwargs: FakeEngine())
    monkeypatch.setattr(
        environment_safety,
        "validate_local_test_connection_identity",
        reject_wrong_connection,
    )

    with pytest.raises(EnvironmentSafetyError, match="misbound migration connection"):
        command.upgrade(config, "head")


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
        "from sqlalchemy import create_engine, make_url, pool\n"
        "from backend.tests.support.environment_safety import (\n"
        "    DEDICATED_MIGRATION_TEST_DATABASE_NAME,\n"
        "    validate_local_test_connection_identity,\n"
        ")\n\n"
        "config = context.config\n\n"
        "def run_migrations_online():\n"
        "    database_url = config.get_main_option('sqlalchemy.url')\n"
        "    engine = create_engine(\n"
        "        database_url,\n"
        "        poolclass=pool.NullPool,\n"
        "    )\n"
        "    try:\n"
        "        with engine.connect() as connection:\n"
        "            validate_local_test_connection_identity(\n"
        "                connection,\n"
        "                DEDICATED_MIGRATION_TEST_DATABASE_NAME,\n"
        "                make_url(database_url).port or 5432,\n"
        "            )\n"
        "            connection.commit()\n"
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
    config.set_main_option(
        "sqlalchemy.url", escape_alembic_config_url(database_url)
    )
    return config
