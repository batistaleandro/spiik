"""Database setup: SQLite via SQLAlchemy, file path from SPIIK_DB."""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

_DEFAULT_DB = Path(__file__).resolve().parents[1] / "data" / "spiik.db"


def db_file() -> Path:
    return Path(os.environ.get("SPIIK_DB") or _DEFAULT_DB)


class Base(DeclarativeBase):
    pass


engine = create_engine(
    f"sqlite:///{db_file()}",
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def _sqlite_pragmas(dbapi_conn, _record):
    """WAL + a write timeout so multi-worker deployments don't trip over
    SQLite's single-writer lock on busy instances."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    import app.models  # noqa: F401 — importing registers the mappers

    db_file().parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
