"""Shared test helpers.

- `FakeExtractor` replays the manually checked ground-truth answers instead of
  calling OpenAI, so tests are fast, free and always give the same result.
- `session_factory` is an in-memory SQLite database with all tables created.
"""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_extractor, get_sessionmaker
from app.core.config import get_settings
from app.extraction.llm_extractor import LLMResponse
from app.main import app
from app.models import Base

BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
SAMPLE_DATA = BACKEND_DIRECTORY.parent / "sample-data"
GROUND_TRUTH_PATH = BACKEND_DIRECTORY / "evaluation" / "ground_truth.json"
SAMPLE_PDFS = sorted(SAMPLE_DATA.glob("supplier-pack-*.pdf"))


def load_ground_truth() -> dict:
    return json.loads(GROUND_TRUTH_PATH.read_text(encoding="utf-8"))["documents"]


def ground_truth_answer(filename: str) -> str:
    """The JSON a perfect LLM would return for one sample PDF."""
    truth = load_ground_truth()[filename]
    return json.dumps({**truth["fields"], "evidence": truth["evidence"], "conflicts": []})


class FakeExtractor:
    """Returns prepared answers. Pick the answer by the document's first page text."""

    def __init__(self, answers_by_supplier: dict[str, list[str]] | None = None):
        self.answers_by_supplier = answers_by_supplier
        self.calls = 0

    def extract(self, pages: list[dict], previous_error: str | None = None) -> LLMResponse:
        self.calls += 1
        first_line = pages[0]["text"].strip().splitlines()[0]
        if self.answers_by_supplier is not None:
            answers = self.answers_by_supplier[first_line]
            return LLMResponse(raw_text=answers.pop(0), model_name="fake-llm")
        for filename, truth in load_ground_truth().items():
            if truth["fields"]["supplier_name"] == first_line:
                return LLMResponse(raw_text=ground_truth_answer(filename), model_name="fake-llm")
        raise AssertionError(f"No fake answer for supplier '{first_line}'")


@pytest.fixture
def ground_truth() -> dict:
    return load_ground_truth()


@pytest.fixture
def session_factory():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, expire_on_commit=False)
    engine.dispose()


@pytest.fixture
def upload_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "upload_directory", str(tmp_path / "uploads"))
    return tmp_path / "uploads"


@pytest.fixture
def fake_extractor() -> FakeExtractor:
    return FakeExtractor()


@pytest.fixture
def client(session_factory, upload_folder, fake_extractor):
    app.dependency_overrides[get_sessionmaker] = lambda: session_factory
    app.dependency_overrides[get_extractor] = lambda: fake_extractor
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
