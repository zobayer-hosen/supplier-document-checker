"""Shared FastAPI dependencies. Tests replace these with fakes via `app.dependency_overrides`."""

from typing import Iterator

from fastapi import Depends
from sqlalchemy.orm import Session, sessionmaker

from app.core.errors import AppError
from app.database.connection import get_session_factory, session_scope
from app.extraction.llm_extractor import ExtractionError, InformationExtractor, create_extractor


def get_sessionmaker() -> sessionmaker[Session]:
    return get_session_factory()


def get_db(session_factory: sessionmaker[Session] = Depends(get_sessionmaker)) -> Iterator[Session]:
    """One database session per request; committed when the request succeeds."""
    with session_scope(session_factory) as session:
        yield session


def get_extractor() -> InformationExtractor:
    try:
        return create_extractor()
    except ExtractionError as error:
        raise AppError(500, "LLM_NOT_CONFIGURED", str(error)) from error
