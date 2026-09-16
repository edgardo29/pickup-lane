"""Real acquisition/execution origins, passive pool state, and timeout recovery."""

import os
import uuid
from datetime import timedelta
from threading import Event
from types import SimpleNamespace

import pytest
from psycopg import errors
from sqlalchemy import Column, Integer, MetaData, Table, create_engine, event, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.exc import TimeoutError as PoolTimeout
from sqlalchemy.orm import Session, registry, sessionmaker
from sqlalchemy.pool import NullPool

from backend import database
from backend.observability.metrics import MetricsRecorder, metrics_context

pytestmark = pytest.mark.no_db_cleanup


@pytest.fixture
def small_engine():
    engine = create_engine(
        os.environ["DATABASE_URL"],
        poolclass=database.ObservableQueuePool,
        pool_size=1,
        max_overflow=0,
        pool_timeout=0.02,
    )
    database.instrument_database_engine(engine)
    database.instrument_database_engine(engine)
    yield engine
    engine.dispose()


def _timeouts(recorder):
    return {
        dict(item.dimensions)["operation"]: item.value
        for item in recorder.snapshot().series
        if item.name == "database.timeout.total"
    }


@pytest.mark.parametrize("source", ["api", "worker"])
def test_pool_wait_observed_once_without_changing_acquisition(small_engine, source):
    recorder = MetricsRecorder(source, "test", "database-test")
    with small_engine.connect(), metrics_context(recorder):
        with pytest.raises(PoolTimeout) as failure:
            small_engine.connect()
        database.observe_database_timeout(failure.value)
    assert _timeouts(recorder) == {"database.pool_wait": 1}
    with small_engine.connect() as connection:
        assert connection.execute(text("SELECT 1")).scalar_one() == 1


@pytest.mark.parametrize("source", ["api", "worker"])
def test_statement_origin_wrapping_and_independent_recovery_errors(
    small_engine, source
):
    recorder = MetricsRecorder(source, "test", "database-test")
    with metrics_context(recorder), Session(small_engine) as session:
        session.execute(text("SET statement_timeout = 20"))
        try:
            session.execute(text("SELECT pg_sleep(0.1)"))
        except DBAPIError as first:
            assert isinstance(first.orig, errors.QueryCanceled)
            database.observe_database_timeout(first)
            session.rollback()
            # Run recovery inside the except block: implicit context is the old origin.
            try:
                session.execute(text("SET statement_timeout = 20"))
                session.execute(text("SELECT pg_sleep(0.1)"))
            except DBAPIError as second:
                assert second.orig is not first.orig
                database.observe_database_timeout(second)
                session.rollback()
                with pytest.raises(DBAPIError):
                    session.execute(text("SELECT * FROM ws09_nonexistent_table"))
                session.rollback()
            else:
                pytest.fail("Recovery query must time out")
        else:
            pytest.fail("Original query must time out")
    assert _timeouts(recorder) == {"database.statement": 2}
    assert "pg_sleep" not in repr(recorder.snapshot())


@pytest.mark.parametrize("source", ["api", "worker"])
def test_lock_timeout_against_independent_postgres_lock_owner(small_engine, source):
    lock_engine = create_engine(os.environ["DATABASE_URL"], poolclass=NullPool)
    recorder = MetricsRecorder(source, "test", "database-test")
    try:
        with lock_engine.connect() as owner, small_engine.connect() as contender:
            owner.execute(text("SELECT pg_advisory_xact_lock(903001)"))
            contender.execute(text("SET LOCAL lock_timeout = 20"))
            with metrics_context(recorder), pytest.raises(DBAPIError) as failure:
                contender.execute(text("SELECT pg_advisory_xact_lock(903001)"))
            assert isinstance(failure.value.orig, errors.LockNotAvailable)
            contender.rollback()
            owner.rollback()
    finally:
        lock_engine.dispose()
    assert _timeouts(recorder) == {"database.lock": 1}


def test_raw_checkout_setting_failure_has_same_passive_owner(small_engine):
    def checkout(connection, record, proxy):
        with connection.cursor() as cursor:
            cursor.execute("SET statement_timeout = 20")
            connection.commit()
            cursor.execute("SELECT pg_sleep(0.1)")

    event.listen(small_engine, "checkout", checkout)
    recorder = MetricsRecorder("api", "test", "database-test")
    with metrics_context(recorder), pytest.raises(DBAPIError) as failure:
        small_engine.connect()
    assert isinstance(failure.value.orig, errors.QueryCanceled)
    assert _timeouts(recorder) == {"database.statement": 1}


def test_pool_collection_is_passive_and_unsupported_pool_is_absent(
    monkeypatch, small_engine
):
    monkeypatch.setattr(database, "engine", small_engine)
    monkeypatch.setattr(
        database, "DATABASE_POOL_SETTINGS", SimpleNamespace(pool_size=1, max_overflow=0)
    )
    recorder = MetricsRecorder("worker", "test", "database-test")
    database.register_pool_metrics(recorder)
    assert {item.name: item.value for item in recorder.collect().series} == {
        "database.pool.checked_out": 0,
        "database.pool.capacity": 1,
    }
    with small_engine.connect():
        assert {item.name: item.value for item in recorder.collect().series}[
            "database.pool.checked_out"
        ] == 1
    assert {item.name: item.value for item in recorder.collect().series}[
        "database.pool.checked_out"
    ] == 0
    monkeypatch.setattr(
        database, "engine", SimpleNamespace(pool=NullPool(lambda: None))
    )
    monkeypatch.setattr(
        database,
        "DATABASE_POOL_SETTINGS",
        SimpleNamespace(pool_size=None, max_overflow=None),
    )
    assert recorder.collect().series == ()


def test_uninstrumented_engine_and_no_active_runtime_do_not_count(small_engine):
    recorder = MetricsRecorder("api", "test", "database-test")
    plain = create_engine(os.environ["DATABASE_URL"], poolclass=NullPool)
    try:
        with metrics_context(recorder), plain.connect() as connection:
            connection.execute(text("SET LOCAL statement_timeout = 20"))
            with pytest.raises(DBAPIError):
                connection.execute(text("SELECT pg_sleep(0.1)"))
        with small_engine.connect() as connection:
            connection.execute(text("SET LOCAL statement_timeout = 20"))
            with pytest.raises(DBAPIError):
                connection.execute(text("SELECT pg_sleep(0.1)"))
    finally:
        plain.dispose()
    assert recorder.snapshot().series == ()


@pytest.mark.parametrize("phase", ["flush", "commit"])
def test_session_write_timeouts_are_observed_through_engine_hook(small_engine, phase):
    class Inserted:
        pass

    mapper = registry()
    mapper.map_imperatively(
        Inserted,
        Table(
            "runtime_timeout_rows",
            MetaData(),
            Column("value", Integer, primary_key=True),
        ),
    )
    try:
        with small_engine.begin() as connection:
            connection.execute(
                text(
                    "CREATE TEMP TABLE runtime_timeout_rows(value integer primary key)"
                )
            )
            connection.execute(
                text(
                    "CREATE FUNCTION pg_temp.timeout_insert() RETURNS trigger LANGUAGE plpgsql "
                    "AS $$ BEGIN RAISE query_canceled USING MESSAGE = 'synthetic timeout'; END $$"
                )
            )
            deferred = "DEFERRABLE INITIALLY DEFERRED" if phase == "commit" else ""
            connection.execute(
                text(
                    f"CREATE CONSTRAINT TRIGGER timeout_insert AFTER INSERT ON runtime_timeout_rows {deferred} FOR EACH ROW EXECUTE FUNCTION pg_temp.timeout_insert()"
                )
            )
        recorder = MetricsRecorder("worker", "test", "database-test")
        with Session(small_engine) as session, metrics_context(recorder):
            row = Inserted()
            row.value = 1
            session.add(row)
            with pytest.raises(DBAPIError) as failure:
                session.flush() if phase == "flush" else session.commit()
            assert isinstance(failure.value.orig, errors.QueryCanceled)
            database.observe_database_timeout(failure.value)
            session.rollback()
        assert _timeouts(recorder) == {"database.statement": 1}
    finally:
        mapper.dispose()


def test_readiness_handles_timeout_without_hiding_metric(monkeypatch, small_engine):
    from backend import main

    monkeypatch.setattr(database, "engine", small_engine)
    recorder = MetricsRecorder("api", "test", "database-test")
    with small_engine.connect(), metrics_context(recorder):
        assert main._database_ready() is False
    assert _timeouts(recorder) == {"database.pool_wait": 1}


def test_collector_failure_discards_stale_family_and_observes_execution_timeout(
    small_engine,
):
    recorder = MetricsRecorder("api", "test", "database-test")
    fail = False

    def collect():
        with small_engine.connect() as connection:
            if fail:
                connection.execute(text("SET LOCAL statement_timeout = 20"))
                connection.execute(text("SELECT pg_sleep(0.1)"))
            return [("database.pool.checked_out", 1, {})]

    recorder.register_observable("database_pool", collect)
    assert any(
        item.name == "database.pool.checked_out" for item in recorder.collect().series
    )
    fail = True
    snapshot = recorder.collect()
    assert snapshot.unavailable_families == ("database_pool",)
    assert not any(item.name.startswith("database.pool.") for item in snapshot.series)
    assert _timeouts(recorder) == {"database.statement": 1}


def test_lease_renewer_thread_explicitly_activates_worker_recorder(
    monkeypatch, small_engine
):
    from backend.services import durable_job_service as jobs

    attempted = Event()

    def heartbeat(db, **kwargs):
        try:
            db.execute(text("SET LOCAL statement_timeout = 20"))
            db.execute(text("SELECT pg_sleep(0.1)"))
        finally:
            attempted.set()

    monkeypatch.setattr(jobs, "heartbeat_job", heartbeat)
    recorder = MetricsRecorder("worker", "test", "database-test")
    policy = jobs.DurableJobQueuePolicy(
        lease_duration=timedelta(seconds=30),
        heartbeat_interval=timedelta(seconds=0.1),
        fairness_age=timedelta(seconds=5),
    )
    with metrics_context(recorder):
        renewer = jobs._ActiveLeaseRenewer(
            session_factory=sessionmaker(bind=small_engine),
            job_id=uuid.uuid4(),
            lease_token=uuid.uuid4(),
            policy=policy,
        )
    renewer.start()
    try:
        assert attempted.wait(5)
    finally:
        renewer.stop()
    assert _timeouts(recorder) == {"database.statement": 1}
