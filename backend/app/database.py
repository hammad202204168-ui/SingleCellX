"""
Database connection and session management.

Uses SQLAlchemy 2.0 declarative style with SQLite as the default
backend. The `get_db` dependency is consumed by FastAPI routes
to obtain a scoped session per request.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session
from typing import Generator

from .config import settings


# SQLite needs check_same_thread=False because FastAPI uses multiple threads
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables. Called at application startup."""
    # Import models so SQLAlchemy registers them with Base.metadata
    from . import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
