from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from backend.database_metadata import Base
from backend.settings import (
    get_database_pool_settings,
    get_database_timeout_settings,
    get_database_url,
)

DATABASE_URL = get_database_url()
DATABASE_TIMEOUT_SETTINGS = get_database_timeout_settings()
DATABASE_POOL_SETTINGS = get_database_pool_settings()


def _database_engine_kwargs() -> dict[str, object]:
    kwargs: dict[str, object] = {
        "pool_timeout": DATABASE_TIMEOUT_SETTINGS.pool_wait_timeout_seconds,
    }
    if DATABASE_POOL_SETTINGS.pool_size is not None:
        kwargs["pool_size"] = DATABASE_POOL_SETTINGS.pool_size
    if DATABASE_POOL_SETTINGS.max_overflow is not None:
        kwargs["max_overflow"] = DATABASE_POOL_SETTINGS.max_overflow
    return kwargs


# The shared engine is used by normal application traffic only.
engine = create_engine(DATABASE_URL, **_database_engine_kwargs())


@event.listens_for(engine, "checkout")
def _apply_database_timeout_settings(dbapi_connection, connection_record, connection_proxy):
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
