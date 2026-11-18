"""Migration checks run on their own empty database, pickup_lane_migration_test_db.

pytest-alembic walks every migration up and down, so it cannot share the
database the other tests use.
"""

import os
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, make_url, text
from sqlalchemy.pool import NullPool

REPO_ROOT = Path(__file__).resolve().parents[3]
MIGRATION_DATABASE_NAME = "pickup_lane_migration_test_db"


@pytest.fixture
def alembic_config() -> Config:
    config = Config()
    config.set_main_option("script_location", str(REPO_ROOT / "backend" / "alembic"))
    return config


@pytest.fixture
def alembic_engine():
    """An empty migration test database, on the same server as the test database."""
    url = make_url(os.environ["DATABASE_URL"]).set(database=MIGRATION_DATABASE_NAME)
    engine = create_engine(url, poolclass=NullPool)
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    try:
        yield engine
    finally:
        engine.dispose()
