import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import text

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)

# Keep this list in dependency order for cleanup: child tables first, then the
# parent tables they reference.
TEST_TABLES = (
    "waitlist_entries",
    "game_participants",
    "bookings",
    "user_payment_methods",
    "user_settings",
    "games",
    "venues",
    "users",
)


def _is_safe_test_database(database_url: str) -> bool:
    # Local test runs should never truncate a real development database by
    # accident, so require the database name itself to include "test".
    return "test" in database_url.rsplit("/", maxsplit=1)[-1]


@pytest.fixture(scope="session")
def client() -> TestClient:
    database_url = os.getenv("DATABASE_URL", "")

    if not database_url:
        pytest.skip("DATABASE_URL is required for backend integration tests.")

    if not _is_safe_test_database(database_url):
        if os.getenv("CI") == "true":
            pytest.fail("CI DATABASE_URL must point to a test database.")

        # Local runs skip instead of failing so developers can run collection
        # checks without needing a PostgreSQL test database every time.
        pytest.skip("Backend integration tests require a test database.")

    from backend.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clean_database(client: TestClient):
    from backend.database import engine

    table_names = ", ".join(TEST_TABLES)

    # Each test gets a clean database so tests can create the same logical
    # records without leaking state into the next test.
    with engine.begin() as connection:
        connection.execute(
            text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE")
        )

    yield

    # Clean again after the test so a failed test does not leave rows behind
    # for the next local run.
    with engine.begin() as connection:
        connection.execute(
            text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE")
        )
