"""Database session and connection management."""

from __future__ import annotations

import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.db.models import Base

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://forge:forge_password@localhost:5432/forge",
)

# Engine configuration with fallback to sqlite for test environments if needed
try:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
except Exception:  # noqa: BLE001
    engine = create_engine("sqlite:///./forge_dev.db")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Initialize database tables if they do not exist."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session]:
    """FastAPI dependency for obtaining a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
