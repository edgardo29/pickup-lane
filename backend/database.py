from collections.abc import Generator

from psycopg import errors as psycopg_errors
from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import TimeoutError as SQLAlchemyTimeoutError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from backend.database_metadata import Base  # noqa: F401 - compatibility import surface.
from backend.observability.metrics import MetricsRecorder, record_metric
from backend.settings import (
    get_database_pool_settings,
    get_database_timeout_settings,
    get_database_url,
)

DATABASE_URL = get_database_url()
DATABASE_TIMEOUT_SETTINGS = get_database_timeout_settings()
DATABASE_POOL_SETTINGS = get_database_pool_settings()


def observe_database_timeout(
    exception: BaseException, *, original_exception: BaseException | None = None
) -> None:
    """Observe this failure origin, never unrelated implicit exception context."""
    try:
        origin = original_exception if original_exception is not None else exception
        seen: set[int] = set()
        while id(origin) not in seen:
            seen.add(id(origin))
            nested = getattr(origin, "orig", None)
            if not isinstance(nested, BaseException):
                break
            origin = nested
        if isinstance(origin, SQLAlchemyTimeoutError):
            operation = "database.pool_wait"
        elif isinstance(origin, psycopg_errors.QueryCanceled):
            operation = "database.statement"
        elif isinstance(origin, psycopg_errors.LockNotAvailable):
            operation = "database.lock"
        else:
            return
        if getattr(origin, "_pickup_lane_timeout_observed", False):
            return
        origin._pickup_lane_timeout_observed = True
        record_metric(
            "database.timeout.total", 1, {"operation": operation, "result": "timed_out"}
        )
    except Exception:  # noqa: BLE001, S110 - preserve the original database failure.
        pass


class ObservableQueuePool(QueuePool):
    """Passive acquisition observation, preserving SQLAlchemy queue semantics."""

    def connect(self):
        try:
            return super().connect()
        except Exception as exc:
            observe_database_timeout(exc)
            raise


def _observe_engine_error(context) -> None:
    observe_database_timeout(
        context.sqlalchemy_exception or context.original_exception,
        original_exception=context.original_exception,
    )


def instrument_database_engine(target_engine) -> None:
    if not event.contains(target_engine, "handle_error", _observe_engine_error):
        event.listen(target_engine, "handle_error", _observe_engine_error)


def register_pool_metrics(recorder: MetricsRecorder) -> None:
    def collect_pool():
        observations = []
        checked_out = getattr(engine.pool, "checkedout", None)
        if callable(checked_out):
            observations.append(("database.pool.checked_out", checked_out(), {}))
        if (
            DATABASE_POOL_SETTINGS.pool_size is not None
            and DATABASE_POOL_SETTINGS.max_overflow is not None
        ):
            observations.append(
                (
                    "database.pool.capacity",
                    DATABASE_POOL_SETTINGS.pool_size
                    + DATABASE_POOL_SETTINGS.max_overflow,
                    {},
                )
            )
        return observations

    recorder.register_observable("database_pool", collect_pool)


def _database_engine_kwargs() -> dict[str, object]:
    kwargs: dict[str, object] = {
        "poolclass": ObservableQueuePool,
        "pool_timeout": DATABASE_TIMEOUT_SETTINGS.pool_wait_timeout_seconds,
    }
    if DATABASE_POOL_SETTINGS.pool_size is not None:
        kwargs["pool_size"] = DATABASE_POOL_SETTINGS.pool_size
    if DATABASE_POOL_SETTINGS.max_overflow is not None:
        kwargs["max_overflow"] = DATABASE_POOL_SETTINGS.max_overflow
    return kwargs


# The shared engine is used by normal application traffic only.
engine = create_engine(DATABASE_URL, **_database_engine_kwargs())
instrument_database_engine(engine)


@event.listens_for(engine, "checkout")
def _apply_database_timeout_settings(
    dbapi_connection, connection_record, connection_proxy
):
    del connection_record, connection_proxy
    with dbapi_connection.cursor() as cursor:
        cursor.execute(
            "SELECT set_config('statement_timeout', %s, false)",
            (str(DATABASE_TIMEOUT_SETTINGS.statement_timeout_milliseconds),),
        )
        cursor.execute(
            "SELECT set_config('lock_timeout', %s, false)",
            (str(DATABASE_TIMEOUT_SETTINGS.lock_timeout_milliseconds),),
        )


# SessionLocal creates database sessions for individual FastAPI requests so
# each request gets its own unit of work against PostgreSQL.
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def check_database_connection() -> bool:
    # A simple connectivity check for the health endpoint and quick local
    # verification while the rest of the data layer is still being built out.
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return True


def dispose_database_engine() -> None:
    # Dispose pooled connections during application shutdown without changing
    # pool sizing or connection behavior.
    engine.dispose()


def get_db() -> Generator[Session, None, None]:
    # Yield one session per request and always close it afterward so
    # connections do not get left open.
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
