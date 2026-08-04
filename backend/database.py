from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.settings import get_database_url

DATABASE_URL = get_database_url()


# Base is the shared declarative parent for all SQLAlchemy models in the app.
class Base(DeclarativeBase):
    pass


# The shared engine is used by the app and by migration tooling to connect to
# the same PostgreSQL database.
engine = create_engine(DATABASE_URL)

# SessionLocal creates database sessions for individual FastAPI requests so
# each request gets its own unit of work against PostgreSQL.
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def check_database_connection() -> bool:
    # A simple connectivity check for the health endpoint and quick local
    # verification while the rest of the data layer is still being built out.
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return True


def get_db() -> Generator[Session, None, None]:
    # Yield one session per request and always close it afterward so
    # connections do not get left open.
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
