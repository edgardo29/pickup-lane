from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, TimeoutError as SQLAlchemyTimeoutError

from backend.observability.timeouts import DATABASE_TIMEOUT_CODE, public_timeout_contract


def test_application_engine_applies_statement_and_lock_timeouts():
    from backend.database import DATABASE_TIMEOUT_SETTINGS, engine

    with engine.connect() as connection:
        statement_timeout = connection.execute(
            text("SELECT current_setting('statement_timeout')")
        ).scalar_one()
        lock_timeout = connection.execute(
            text("SELECT current_setting('lock_timeout')")
        ).scalar_one()

    assert statement_timeout in {
        "12s",
        f"{DATABASE_TIMEOUT_SETTINGS.statement_timeout_milliseconds}ms",
    }
    assert lock_timeout in {
        "2s",
        f"{DATABASE_TIMEOUT_SETTINGS.lock_timeout_milliseconds}ms",
    }


def test_pool_wait_timeout_maps_safely_and_pool_recovers():
    from backend.database import engine

    limited_engine = create_engine(
        engine.url,
        pool_size=1,
        max_overflow=0,
        pool_timeout=1,
    )
    held_connection = limited_engine.connect()
    try:
        try:
            limited_engine.connect()
        except SQLAlchemyTimeoutError as exc:
            contract = public_timeout_contract(exc)
        else:  # pragma: no cover - the dedicated limited pool must exhaust.
            raise AssertionError("limited test pool did not enforce pool wait timeout")

        assert contract is not None
        assert contract.code == DATABASE_TIMEOUT_CODE
        assert contract.details["timeout_kind"] == "pool_wait"
    finally:
        held_connection.close()
        limited_engine.dispose()

    with engine.connect() as connection:
        assert connection.execute(text("SELECT 1")).scalar_one() == 1


def test_statement_timeout_rolls_back_and_connection_remains_reusable():
    from backend.database import engine

    with engine.connect() as connection:
        connection.execute(text("SET statement_timeout = 50"))
        try:
            connection.execute(text("SELECT pg_sleep(0.2)"))
        except OperationalError as exc:
            contract = public_timeout_contract(exc)
            connection.rollback()
        else:  # pragma: no cover - PostgreSQL should cancel the slow statement.
            raise AssertionError("statement timeout did not cancel slow query")

        assert contract is not None
        assert contract.code == DATABASE_TIMEOUT_CODE
        assert contract.details["timeout_kind"] == "statement"
        assert connection.execute(text("SELECT 1")).scalar_one() == 1


def test_lock_timeout_precedes_statement_timeout_and_connection_remains_reusable():
    from backend.database import engine

    lock_id = 814_028_144
    with engine.connect() as holder, engine.connect() as waiter:
        holder.execute(text("SELECT pg_advisory_lock(:lock_id)"), {"lock_id": lock_id})
        holder.commit()
        try:
            waiter.execute(text("SET statement_timeout = 1000"))
            waiter.execute(text("SET lock_timeout = 50"))
            try:
                waiter.execute(
                    text("SELECT pg_advisory_lock(:lock_id)"),
                    {"lock_id": lock_id},
                )
            except OperationalError as exc:
                contract = public_timeout_contract(exc)
                waiter.rollback()
            else:  # pragma: no cover - PostgreSQL should cancel the lock wait.
                raise AssertionError("lock timeout did not cancel lock wait")

            assert contract is not None
            assert contract.code == DATABASE_TIMEOUT_CODE
            assert contract.details["timeout_kind"] == "lock"
            assert waiter.execute(text("SELECT 1")).scalar_one() == 1
        finally:
            holder.execute(
                text("SELECT pg_advisory_unlock(:lock_id)"),
                {"lock_id": lock_id},
            )
            holder.commit()
