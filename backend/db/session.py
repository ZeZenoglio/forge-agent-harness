"""Database session and connection management."""

from __future__ import annotations

import logging
import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.db.models import Base

logger = logging.getLogger(__name__)

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
    try:
        from sqlalchemy import text

        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.commit()
    except Exception as exc:  # noqa: BLE001
        logger.debug("vector extension init skipped: %s", exc)

    Base.metadata.create_all(bind=engine)

    try:
        with SessionLocal() as db:
            from backend.db.models import User

            user = db.query(User).filter(User.id == "anonymous_user").first()
            if not user:
                anon = User(
                    id="anonymous_user",
                    email="anonymous@forge.local",
                    name="Anonymous User",
                    provider="local",
                )
                db.add(anon)
                db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.debug("anonymous_user seed skipped: %s", exc)


def get_db() -> Generator[Session]:
    """FastAPI dependency for obtaining a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
