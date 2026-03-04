from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime
from typing import Generator, Optional

from sqlalchemy import Column, Date, DateTime, Float, Integer, String, create_engine, func
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from ..config import get_settings


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""


class Metric(Base):
    """
    Simple metrics table storing daily aggregates.

    This schema is intentionally minimal and focused on values that are useful for
    Verified Builder justification: relayer tx counts, volume, and markets traded.
    """

    __tablename__ = "metrics"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    day: date = Column(Date, nullable=False, index=True)
    relayer_tx_count: int = Column(Integer, nullable=False, default=0)
    volume: float = Column(Float, nullable=False, default=0.0)
    markets_traded: int = Column(Integer, nullable=False, default=0)
    created_at: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


_engine = None
_SessionLocal: Optional[sessionmaker[Session]] = None


def get_engine():
    """Create or return the global SQLAlchemy engine."""

    global _engine  # noqa: PLW0603
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(settings.database_url, future=True)
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    """Return a session factory bound to the configured engine."""

    global _SessionLocal  # noqa: PLW0603
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)
    return _SessionLocal


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """
    Provide a transactional scope around a series of operations.

    This is the recommended way for the engine and web layer to interact with the DB.
    """

    session_factory = get_session_factory()
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:  # noqa: BLE001
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """Create all tables in the database."""

    engine = get_engine()
    Base.metadata.create_all(bind=engine)


def _main() -> None:
    """
    Lightweight CLI entrypoint.

    Intended usage (from project root):

        python -m polymarket_bot.storage.db init
    """

    import sys

    if len(sys.argv) >= 2 and sys.argv[1] == "init":
        init_db()
        print("Database initialized.")
    else:
        print("Usage: python -m polymarket_bot.storage.db init")


if __name__ == "__main__":
    _main()

