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

import hashlib
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
# The test database keeps its schema between runs while it still matches the
# migrations. The record of what it was built from lives outside the public
# schema, which every rebuild drops.
TEST_DATABASE_META_SCHEMA = "pickup_lane_test_meta"
TEST_DATABASE_LOCK_KEY = 6150421

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
    parser.addoption(
        "--rebuild-test-db",
        action="store_true",
        help="rebuild the test database schema even if it is current",
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


def _migration_fingerprint() -> str:
    """A digest of every file the test schema is built from."""
    alembic_dir = REPO_ROOT / "backend" / "alembic"
    digest = hashlib.sha256()
    for path in sorted(
        [alembic_dir / "env.py", *(alembic_dir / "versions").glob("*.py")]
    ):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _alembic_config(engine):
    from alembic.config import Config

    config = Config()
    config.set_main_option("script_location", str(REPO_ROOT / "backend" / "alembic"))
    config.attributes["connection"] = engine
    return config


def _schema_is_reusable(engine, fingerprint: str) -> bool:
    """True when the schema was built from these migrations and holds no rows."""
    from alembic.script import ScriptDirectory
    from sqlalchemy import text

    with engine.connect() as connection:
        record = f"{TEST_DATABASE_META_SCHEMA}.schema_build"
        if connection.scalar(text(f"SELECT to_regclass('{record}')")) is None:
            return False
        if connection.scalar(text(f"SELECT fingerprint FROM {record}")) != fingerprint:
            return False
        if (
            connection.scalar(text("SELECT to_regclass('public.alembic_version')"))
            is None
        ):
            return False
        applied = set(
            connection.scalars(text("SELECT version_num FROM alembic_version"))
        )
        heads = set(ScriptDirectory.from_config(_alembic_config(engine)).get_heads())
        if applied != heads:
            return False
        tables = connection.scalars(
            text(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public' "
                "AND tablename <> 'alembic_version'"
            )
        ).all()
        # A run that was killed mid-test can leave rows behind.
        return not any(
            connection.scalar(text(f'SELECT EXISTS (SELECT 1 FROM public."{table}")'))
            for table in tables
        )


def _rebuild_schema(engine, fingerprint: str) -> None:
    from alembic import command
    from sqlalchemy import text

    record = f"{TEST_DATABASE_META_SCHEMA}.schema_build"
    with engine.begin() as connection:
        connection.execute(
            text(f"CREATE SCHEMA IF NOT EXISTS {TEST_DATABASE_META_SCHEMA}")
        )
        connection.execute(text(f"DROP TABLE IF EXISTS {record}"))
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    command.upgrade(_alembic_config(engine), "head")
    with engine.begin() as connection:
        connection.execute(text(f"CREATE TABLE {record} (fingerprint text NOT NULL)"))
        connection.execute(
            text(f"INSERT INTO {record} (fingerprint) VALUES (:fingerprint)"),
            {"fingerprint": fingerprint},
        )


@pytest.fixture(scope="session")
def _test_database(request: pytest.FixtureRequest):
    """Check the database, then reuse its schema or rebuild it from the migrations.

    The schema is reused only when it was built from the current migration
    files, is at the latest migration, and holds no rows. ``--rebuild-test-db``
    always rebuilds. A lock keeps two runs from using the database at once.
    """
    from sqlalchemy import create_engine, text
    from sqlalchemy.pool import NullPool

    engine = create_engine(os.environ["DATABASE_URL"], poolclass=NullPool)
    lock_connection = engine.connect()
    try:
        name = lock_connection.scalar(text("SELECT current_database()"))
        if name != TEST_DATABASE_NAME:
            pytest.exit(
                f"Refusing to run tests against {name!r}; "
                f"expected {TEST_DATABASE_NAME!r}.",
                returncode=pytest.ExitCode.USAGE_ERROR,
            )
        lock_connection.execute(
            text("SELECT pg_advisory_lock(:key)"), {"key": TEST_DATABASE_LOCK_KEY}
        )
        lock_connection.commit()
        fingerprint = _migration_fingerprint()
        if request.config.getoption("--rebuild-test-db") or not _schema_is_reusable(
            engine, fingerprint
        ):
            _rebuild_schema(engine, fingerprint)
        yield
    finally:
        lock_connection.close()
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


# Stripe, faked like Firebase above. App modules are imported inside functions:
# importing them at module level would load the app's settings too early.


class FakeStripe:
    """Answers the Stripe calls checkout and card management make, without the network."""

    def __init__(self) -> None:
        self.intents: dict = {}
        self.cards: dict = {}
        self.setup_intents: dict = {}
        # The card each customer has as its Stripe default, if any.
        self.customer_defaults: dict = {}
        self.detached: set[str] = set()
        # Names of Stripe calls that should fail, to simulate a provider error.
        self.failing: set[str] = set()
        # What confirming a payment returns: "succeeded", "requires_action",
        # "requires_payment_method", or "processing".
        self.confirm_status = "succeeded"
        self.created: list[dict] = []

    def _fail_if_set(self, name: str) -> None:
        if name in self.failing:
            raise RuntimeError(f"Stripe {name} failed.")

    def create_customer(self, *, email, name, idempotency_key, metadata):
        from backend.services.stripe_service import StripeCustomerResult

        self._fail_if_set("create_customer")
        return StripeCustomerResult(id=f"cus_test_{uuid.uuid4().hex[:12]}")

    def create_setup_intent(self, *, customer_id, idempotency_key, metadata):
        from backend.services.stripe_service import StripeSetupIntentResult

        self._fail_if_set("create_setup_intent")
        setup_id = f"seti_test_{uuid.uuid4().hex[:12]}"
        setup_intent = StripeSetupIntentResult(
            id=setup_id,
            client_secret=f"{setup_id}_secret",
            status="requires_payment_method",
            customer_id=customer_id,
            payment_method_id=None,
        )
        self.setup_intents[setup_id] = setup_intent
        return setup_intent

    def retrieve_setup_intent(self, setup_intent_id):
        self._fail_if_set("retrieve_setup_intent")
        return self.setup_intents[setup_intent_id]

    def enter_card(
        self,
        setup_intent_id,
        *,
        fingerprint,
        brand="visa",
        last4="4242",
        exp_month=12,
        exp_year=2035,
    ):
        """The player enters a card in Stripe's form and Stripe accepts it."""
        from backend.services.stripe_service import (
            StripePaymentMethodCardResult,
            StripeSetupIntentResult,
        )

        setup_intent = self.setup_intents[setup_intent_id]
        card_id = f"pm_test_{uuid.uuid4().hex[:12]}"
        self.cards[card_id] = StripePaymentMethodCardResult(
            id=card_id,
            customer_id=setup_intent.customer_id,
            card_fingerprint=fingerprint,
            card_brand=brand,
            card_last4=last4,
            exp_month=exp_month,
            exp_year=exp_year,
        )
        self.setup_intents[setup_intent_id] = StripeSetupIntentResult(
            id=setup_intent.id,
            client_secret=setup_intent.client_secret,
            status="succeeded",
            customer_id=setup_intent.customer_id,
            payment_method_id=card_id,
        )
        return card_id

    def set_customer_default_payment_method(
        self, *, customer_id, payment_method_id, idempotency_key=None
    ):
        self._fail_if_set("set_customer_default_payment_method")
        self.customer_defaults[customer_id] = payment_method_id

    def clear_customer_default_payment_method(
        self, *, customer_id, idempotency_key=None
    ):
        self._fail_if_set("clear_customer_default_payment_method")
        self.customer_defaults.pop(customer_id, None)

    def detach_payment_method(self, payment_method_id, idempotency_key=None):
        self._fail_if_set("detach_payment_method")
        self.detached.add(payment_method_id)

    def create_payment_intent(
        self, *, amount_cents, currency, idempotency_key, metadata, customer_id=None
    ):
        from backend.services.stripe_service import StripePaymentIntentResult

        for intent in self.intents.values():
            if intent.metadata.get("_key") == idempotency_key:
                return intent
        intent_id = f"pi_test_{uuid.uuid4().hex[:12]}"
        intent = StripePaymentIntentResult(
            id=intent_id,
            client_secret=f"{intent_id}_secret",
            status="requires_payment_method",
            amount_cents=amount_cents,
            currency=currency.lower(),
            customer_id=customer_id,
            metadata={
                **{key: str(value) for key, value in metadata.items()},
                "_key": idempotency_key,
            },
        )
        self.intents[intent_id] = intent
        self.created.append({"amount_cents": amount_cents, "metadata": metadata})
        return intent

    def confirm_payment_intent(
        self,
        payment_intent_id,
        *,
        payment_method_id,
        return_url=None,
        off_session=False,
        idempotency_key=None,
    ):
        return self._set_status(payment_intent_id, self.confirm_status)

    def retrieve_payment_intent(self, payment_intent_id):
        return self.intents[payment_intent_id]

    def retrieve_payment_method(self, payment_method_id):
        return self.cards[payment_method_id]

    def _set_status(self, payment_intent_id, status):
        from backend.services.stripe_service import StripePaymentIntentResult

        intent = self.intents[payment_intent_id]
        updated = StripePaymentIntentResult(
            id=intent.id,
            client_secret=intent.client_secret,
            status=status,
            latest_charge_id=f"ch_{intent.id}" if status == "succeeded" else None,
            amount_cents=intent.amount_cents,
            amount_received_cents=intent.amount_cents if status == "succeeded" else 0,
            currency=intent.currency,
            customer_id=intent.customer_id,
            metadata=intent.metadata,
            failure_code="card_declined"
            if status == "requires_payment_method"
            else None,
        )
        self.intents[payment_intent_id] = updated
        return updated

    def report(self, db, payment, status: str) -> None:
        """Simulate Stripe telling the app a payment's new status."""
        from backend.models import Payment
        from backend.services.stripe_webhook_service import (
            apply_authoritative_payment_intent_observation,
            lock_booking_payment_domain,
        )

        observation = self._set_status(payment.provider_payment_intent_id, status)
        # A real webhook runs in a fresh session; drop what this test session
        # remembers so the handler reads the current rows.
        db.expire_all()
        lock_booking_payment_domain(db, payment)
        apply_authoritative_payment_intent_observation(
            db,
            payment=db.get(Payment, payment.id),
            observation=observation,
            source=f"test_webhook_{uuid.uuid4().hex[:8]}",
            now=database_now(db),
        )
        db.commit()


@pytest.fixture
def stripe(monkeypatch: pytest.MonkeyPatch) -> FakeStripe:
    """Turn payments on and replace Stripe with FakeStripe for this test."""
    from backend.services import (
        checkout_service,
        game_waitlist_service,
        payment_method_service,
        payment_transition_service,
    )

    fake = FakeStripe()
    for module in (checkout_service, game_waitlist_service, payment_transition_service):
        for name in (
            "create_payment_intent",
            "confirm_payment_intent",
            "retrieve_payment_intent",
            "retrieve_payment_method",
        ):
            if hasattr(module, name):
                monkeypatch.setattr(module, name, getattr(fake, name))
    for name in (
        "create_customer",
        "create_setup_intent",
        "retrieve_setup_intent",
        "retrieve_payment_method",
        "set_customer_default_payment_method",
        "clear_customer_default_payment_method",
        "detach_payment_method",
    ):
        monkeypatch.setattr(payment_method_service, name, getattr(fake, name))
    monkeypatch.setattr(payment_method_service, "stripe_payments_enabled", lambda: True)
    monkeypatch.setattr(checkout_service, "stripe_payments_enabled", lambda: True)
    monkeypatch.setattr(checkout_service, "get_stripe_currency", lambda: "USD")
    monkeypatch.setattr(
        payment_method_service,
        "verify_saved_payment_method_with_stripe",
        lambda *args, **kwargs: None,
    )
    return fake


def database_now(db) -> datetime:
    """Checkout and payments read PostgreSQL's clock, so tests build times from it."""
    from sqlalchemy import func, select

    return db.scalar(select(func.now()))
