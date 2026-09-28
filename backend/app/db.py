"""Database setup: SQLite via SQLAlchemy, file path from SPIIK_DB."""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine, event, select
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
    _migrate_users_table()
    _promote_admin()


def _migrate_users_table() -> None:
    """create_all only adds columns for *new* tables, so databases
    provisioned before v0.5 need the user-management columns by hand."""
    with engine.connect() as conn:
        columns = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(users)")}
        if not columns:
            return  # fresh database — create_all already made the full schema
        if "is_admin" not in columns:
            conn.exec_driver_sql(
                "ALTER TABLE users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0"
            )
        if "is_active" not in columns:
            conn.exec_driver_sql(
                "ALTER TABLE users ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1"
            )
        conn.commit()


def _promote_admin() -> None:
    """SPIIK_ADMIN_EMAIL promotes that account to operator at startup —
    the no-email way for a self-hoster to bootstrap their first admin."""
    email = os.environ.get("SPIIK_ADMIN_EMAIL", "").strip().lower()
    if not email:
        return
    from app.models import User

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        if user is not None and not user.is_admin:
            user.is_admin = True
            db.commit()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
