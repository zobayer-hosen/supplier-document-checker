"""Database engine and sessions.

A *session* is one conversation with the database. `session_scope()` opens a
session, commits if everything worked, and rolls back on any error, so a
half-saved evaluation is never left behind.
"""

from contextlib import contextmanager
from functools import lru_cache
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.errors import AppError


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    database_url = get_settings().database_url
    if not database_url or database_url.startswith("replace_with"):
        raise AppError(500, "DATABASE_NOT_CONFIGURED", "DATABASE_URL is not set in backend/.env.")
    # pool_pre_ping checks the connection first; Neon closes idle connections.
    engine = create_engine(database_url, pool_pre_ping=True, pool_recycle=300)
    return sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def session_scope(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
