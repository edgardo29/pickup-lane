"""Backend test setup.

Every test run:

1. Uses synthetic settings only. Real keys and the development database are
   never loaded.
2. Refuses to run unless the database is ``pickup_lane_test_db``.
3. Rebuilds the test database schema from the Alembic migrations.
4. Runs each test inside a database transaction that is rolled back afterward.

Network access is blocked by pytest-socket (see ``pytest.ini``). Tests marked
``live`` call real outside services and run only with ``pytest --live``.
"""

import os
import time
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
import time_machine
from dotenv import dotenv_values
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
TEST_DATABASE_NAME = "pickup_lane_test_db"

# Settings every test run uses. All values are synthetic.
SYNTHETIC_SETTINGS = {
    "APP_ENV": "test",
    "CURSOR_SIGNING_SECRET": "synthetic-cursor-signing-secret",
    "ENABLE_STRIPE_PAYMENTS": "false",
    "FIREBASE_APP_CHECK_MODE": "disabled",
    "FIREBASE_PROJECT_ID": "pickup-lane-synthetic",
    "INBOX_TOKEN_SECRET": "synthetic-inbox-token-secret",
    "STRIPE_CURRENCY": "USD",
    "STRIPE_PUBLISHABLE_KEY": "synthetic-stripe-publishable-key",
    "STRIPE_SECRET_KEY": "synthetic-stripe-secret-key",
    "STRIPE_WEBHOOK_SECRET": "synthetic-stripe-webhook-secret",
}

# Real credentials that must never reach a test, even if exported in the shell.
REMOVED_SETTINGS = (
    "MIGRATION_DATABASE_URL",
    "FIREBASE_ADMIN_CREDENTIALS",
    "FIREBASE_ADMIN_CREDENTIALS_JSON",
    "R2_ACCOUNT_ID",
    "R2_ACCESS_KEY_ID",
    "R2_SECRET_ACCESS_KEY",
    "R2_BUCKET_NAME",
    "R2_ENDPOINT_URL",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "AWS_PROFILE",
    "AWS_DEFAULT_PROFILE",
)


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--live",
        action="store_true",
        help="also run tests marked live, which call real outside services",
    )


def pytest_configure(config: pytest.Config) -> None:
    # Runs before any backend module is imported, so the app only ever sees
    # these settings. TEST_DATABASE_URL comes from the environment (CI) or
    # backend/.env (local); nothing else is read from backend/.env.
    database_url = os.environ.get("TEST_DATABASE_URL") or dotenv_values(
        REPO_ROOT / "backend" / ".env"
    ).get("TEST_DATABASE_URL")
    if not database_url:
        raise pytest.UsageError(
            "TEST_DATABASE_URL is not set. Add it to backend/.env or the environment."
        )
    os.environ.update(SYNTHETIC_SETTINGS, DATABASE_URL=database_url)
    for name in REMOVED_SETTINGS:
        os.environ.pop(name, None)


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    if config.getoption("--live"):
        return
    skip_live = pytest.mark.skip(reason="calls a real outside service; run with --live")
    for item in items:
        if item.get_closest_marker("live"):
            item.add_marker(skip_live)


@pytest.fixture(scope="session")
def _test_database():
    """Check the database, then rebuild its schema from the migrations."""
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, text
    from sqlalchemy.pool import NullPool

    engine = create_engine(os.environ["DATABASE_URL"], poolclass=NullPool)
    try:
        with engine.begin() as connection:
            name = connection.scalar(text("SELECT current_database()"))
            if name != TEST_DATABASE_NAME:
                pytest.exit(
                    f"Refusing to run tests against {name!r}; "
                    f"expected {TEST_DATABASE_NAME!r}.",
                    returncode=pytest.ExitCode.USAGE_ERROR,
                )
            connection.execute(text("DROP SCHEMA public CASCADE"))
            connection.execute(text("CREATE SCHEMA public"))
        alembic_config = Config()
        alembic_config.set_main_option(
            "script_location", str(REPO_ROOT / "backend" / "alembic")
        )
        alembic_config.attributes["connection"] = engine
        command.upgrade(alembic_config, "head")
    finally:
        engine.dispose()


@pytest.fixture
def db(_test_database):
    """A database session. Everything the test and the API write is rolled back."""
    from backend.database import SessionLocal, engine

    connection = engine.connect()
    transaction = connection.begin()
    original_session_settings = dict(SessionLocal.kw)
    # Every session the app opens during the test (API requests, the audit
    # log, background jobs) joins this transaction. Their commits become
    # savepoints, and the whole transaction is rolled back at the end.
    SessionLocal.configure(bind=connection, join_transaction_mode="create_savepoint")
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        SessionLocal.kw.clear()
        SessionLocal.kw.update(original_session_settings)
        transaction.rollback()
        connection.close()


@pytest.fixture
def committed_db(request: pytest.FixtureRequest, _test_database):
    """A database session whose writes are really committed.

    Only for tests that need data shared across separate database connections,
    such as two requests racing for the last spot. Slower than ``db``: every
    table is emptied after the test.
    """
    if "db" in request.fixturenames:
        raise pytest.UsageError("A test uses either db or committed_db, not both.")

    from sqlalchemy import text

    import backend.models  # noqa: F401 - registers every table on the metadata.
    from backend.database import SessionLocal, engine
    from backend.database_metadata import Base

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        tables = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
        with engine.begin() as connection:
            connection.execute(text("SET LOCAL statement_timeout = 0"))
            connection.execute(
                text(f"TRUNCATE TABLE {tables} RESTART IDENTITY CASCADE")
            )


@pytest.fixture(scope="session")
def _running_app():
    """Start the app once per run, as in production, and stop it at the end."""
    from backend.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def client(request: pytest.FixtureRequest, _running_app: TestClient):
    """Calls the API the way the browser does, inside the test's database setup."""
    database = "committed_db" if "committed_db" in request.fixturenames else "db"
    request.getfixturevalue(database)

    _running_app.cookies.clear()
    try:
        yield _running_app
    finally:
        _running_app.app.dependency_overrides.clear()


# A fixed moment used by time-sensitive tests: noon in America/Chicago (CDT).
FIXED_NOW = datetime(2026, 6, 15, 17, 0, tzinfo=UTC)


class Clock:
    """Controls what the application sees as the current time during a test."""

    def __init__(self, traveller) -> None:
        self._traveller = traveller

    @property
    def now(self) -> datetime:
        return datetime.now(UTC)

    def move_to(self, moment: datetime) -> None:
        self._traveller.move_to(moment, tick=False)

    def advance(self, delta: timedelta) -> None:
        self._traveller.shift(delta)


@pytest.fixture
def clock():
    """Freeze time at FIXED_NOW for the whole test; move it only on purpose."""
    with time_machine.travel(FIXED_NOW, tick=False) as traveller:
        yield Clock(traveller)


class FakeFirebase:
    """Stands in for Firebase Authentication during a test.

    Only Firebase's answers are faked: whether a token is valid, revoked, or
    expired, and what the Firebase user record says. The app's own token
    handling runs unchanged. This proves the app's decisions, not Firebase's
    project settings, which need the real Firebase test project (P03.R13).
    """

    def __init__(self) -> None:
        self._tokens: dict[str, dict | Exception] = {}
        self._revoked: set[str] = set()
        self.accounts: dict[str, SimpleNamespace] = {}
        self.unavailable = False
        self.token_checks = 0

    def sign_in(self, user, *, email_verified: bool = True, **claims) -> dict[str, str]:
        """Return request headers for a valid token belonging to ``user``."""
        account = SimpleNamespace(
            uid=user.auth_user_id,
            email=user.email,
            email_verified=email_verified,
            disabled=False,
        )
        self.accounts[user.auth_user_id] = account
        token = f"token-{uuid.uuid4().hex}"
        self._tokens[token] = {
            "uid": user.auth_user_id,
            "email": user.email,
            "email_verified": email_verified,
            "auth_time": int(time.time()),
            **claims,
        }
        return {"Authorization": f"Bearer {token}"}

    def rejected_token(self, error: Exception) -> dict[str, str]:
        """Return request headers for a token Firebase rejects with ``error``."""
        token = f"token-{uuid.uuid4().hex}"
        self._tokens[token] = error
        return {"Authorization": f"Bearer {token}"}

    def revoke(self, headers: dict[str, str]) -> None:
        self._revoked.add(headers["Authorization"].removeprefix("Bearer "))

    def verify_id_token(
        self, token, app=None, check_revoked=False, clock_skew_seconds=0
    ):
        from firebase_admin import auth

        self.token_checks += 1
        if self.unavailable:
            raise auth.CertificateFetchError("Firebase is unavailable.", None)
        entry = self._tokens.get(token)
        if entry is None:
            raise auth.InvalidIdTokenError("Unknown token.")
        if isinstance(entry, Exception):
            raise entry
        # Firebase reports revocation only when the caller asks it to check.
        if check_revoked and token in self._revoked:
            raise auth.RevokedIdTokenError("Token revoked.")
        return dict(entry)

    def get_user(self, uid, app=None):
        from firebase_admin import auth

        account = self.accounts.get(uid)
        if account is None:
            raise auth.UserNotFoundError("No such Firebase user.")
        return account

    def delete_user(self, uid, app=None):
        from firebase_admin import auth

        if self.accounts.pop(uid, None) is None:
            raise auth.UserNotFoundError("No such Firebase user.")


@pytest.fixture
def firebase(monkeypatch: pytest.MonkeyPatch) -> FakeFirebase:
    """Replace Firebase Authentication with a fake for this test."""
    from firebase_admin import auth

    import backend.firebase_admin_client as firebase_client

    fake = FakeFirebase()
    monkeypatch.setattr(firebase_client, "initialize_firebase_admin", object)
    monkeypatch.setattr(auth, "verify_id_token", fake.verify_id_token)
    monkeypatch.setattr(auth, "get_user", fake.get_user)
    monkeypatch.setattr(auth, "delete_user", fake.delete_user)
    return fake
