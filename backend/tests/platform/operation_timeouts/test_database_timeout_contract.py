from __future__ import annotations

import asyncio

import pytest
from psycopg import errors as psycopg_errors
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, TimeoutError as SQLAlchemyTimeoutError

from backend.observability.timeouts import (
    database_timeout_from_exception,
    is_database_timeout_exception,
)

pytestmark = pytest.mark.no_db_cleanup


def _postgres_timeout_milliseconds(raw_value: str) -> int:
    normalized = raw_value.strip().lower()
    if normalized.endswith("ms"):
        return int(normalized.removesuffix("ms"))
    if normalized.endswith("s"):
        return int(float(normalized.removesuffix("s")) * 1000)
    return int(normalized)


def _operational_error_from_cause(cause: BaseException) -> OperationalError:
    try:
        raise cause
    except BaseException as raised:
        try:
            raise OperationalError("SELECT 1", {}, raised) from raised
        except OperationalError as exc:
            return exc


@pytest.mark.requirement("WS02-04C1-R5")
def test_checked_out_database_connection_has_approved_statement_and_lock_timeouts() -> None:
    from backend.database import engine

    with engine.connect() as connection:
        statement_timeout = connection.execute(text("SHOW statement_timeout")).scalar_one()
        lock_timeout = connection.execute(text("SHOW lock_timeout")).scalar_one()

    assert _postgres_timeout_milliseconds(statement_timeout) == 12_000
    assert _postgres_timeout_milliseconds(lock_timeout) == 2_000


@pytest.mark.requirement("WS02-04C1-R5")
def test_database_engine_pool_wait_timeout_uses_approved_setting() -> None:
    from backend import database

    assert database.DATABASE_TIMEOUT_SETTINGS.pool_wait_timeout_seconds == 2
    assert getattr(database.engine.pool, "_timeout") == 2


@pytest.mark.requirement("WS02-04C1-R5", "WS02-04C1-R6")
def test_database_timeout_classification_maps_pool_statement_and_lock() -> None:
    pool_timeout = SQLAlchemyTimeoutError("pool exhausted")
    statement_timeout = _operational_error_from_cause(
        psycopg_errors.QueryCanceled("statement timeout")
    )
    lock_timeout = _operational_error_from_cause(
        psycopg_errors.LockNotAvailable("lock timeout")
    )

    assert is_database_timeout_exception(pool_timeout)
    assert database_timeout_from_exception(pool_timeout).timeout_kind == "pool_wait"

    assert is_database_timeout_exception(statement_timeout)
    assert isinstance(statement_timeout.orig, psycopg_errors.QueryCanceled)
    assert database_timeout_from_exception(statement_timeout).timeout_kind == "statement"

    assert is_database_timeout_exception(lock_timeout)
    assert isinstance(lock_timeout.orig, psycopg_errors.LockNotAvailable)
    assert database_timeout_from_exception(lock_timeout).timeout_kind == "lock"


class _FakeSession:
    def __init__(self) -> None:
        self.rollback_calls = 0
        self.close_calls = 0

    def rollback(self) -> None:
        self.rollback_calls += 1

    def close(self) -> None:
        self.close_calls += 1


@pytest.mark.requirement("WS02-04C1-R5")
def test_database_request_session_rolls_back_on_ordinary_exception_and_closes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend import database

    fake_session = _FakeSession()
    monkeypatch.setattr(database, "SessionLocal", lambda: fake_session)

    generator = database.get_db()
    yielded = next(generator)
    assert yielded is fake_session
    with pytest.raises(RuntimeError, match="synthetic failure"):
        generator.throw(RuntimeError("synthetic failure"))

    assert fake_session.rollback_calls == 1
    assert fake_session.close_calls == 1


@pytest.mark.requirement("WS02-04C1-R5", "WS02-04C1-R7")
def test_database_request_session_closes_on_cancellation_without_timeout_classification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend import database

    fake_session = _FakeSession()
    monkeypatch.setattr(database, "SessionLocal", lambda: fake_session)

    generator = database.get_db()
    yielded = next(generator)
    assert yielded is fake_session
    cancellation = asyncio.CancelledError()
    with pytest.raises(asyncio.CancelledError) as exc_info:
        generator.throw(cancellation)

    assert exc_info.value is cancellation
    assert fake_session.rollback_calls == 0
    assert fake_session.close_calls == 1
    assert not is_database_timeout_exception(cancellation)
    assert database_timeout_from_exception(cancellation) is None


@pytest.mark.requirement("WS02-04C1-R5")
def test_database_request_session_closes_after_success_without_rollback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend import database

    fake_session = _FakeSession()
    monkeypatch.setattr(database, "SessionLocal", lambda: fake_session)

    generator = database.get_db()
    yielded = next(generator)
    assert yielded is fake_session
    with pytest.raises(StopIteration):
        next(generator)

    assert fake_session.rollback_calls == 0
    assert fake_session.close_calls == 1
