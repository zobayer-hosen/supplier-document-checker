"""Optional tests that use the real Neon database and the real OpenAI API.

They are skipped by default. Run them with:

    $env:RUN_NEON_TESTS="1"; pytest -m neon
    $env:RUN_OPENAI_TESTS="1"; pytest -m openai
"""

import os
import uuid

import pytest
from sqlalchemy import text

from app.database.connection import get_session_factory, session_scope
from app.evidence.verifier import VERIFIED, verify_evidence
from app.extraction.llm_extractor import OpenAIExtractor
from app.extraction.pdf_extractor import extract_pages
from app.models import EvaluationBatch, SupplierDocument
from app.schemas.extraction import SupplierExtraction
from tests.conftest import SAMPLE_PDFS


@pytest.mark.neon
@pytest.mark.skipif(os.getenv("RUN_NEON_TESTS") != "1", reason="set RUN_NEON_TESTS=1 to use Neon")
def test_neon_round_trip():
    """Write a batch and a document to Neon, read them back, then delete them."""
    session_factory = get_session_factory()
    batch_id = uuid.uuid4()
    with session_scope(session_factory) as session:
        assert session.execute(text("select 1")).scalar() == 1
        batch = EvaluationBatch(id=batch_id, name="neon test")
        batch.documents.append(SupplierDocument(filename="x.pdf", storage_path="x.pdf", sha256="0" * 64))
        session.add(batch)

    with session_scope(session_factory) as session:
        saved = session.get(EvaluationBatch, batch_id)
        assert saved.name == "neon test" and len(saved.documents) == 1
        session.delete(saved)


@pytest.mark.openai
@pytest.mark.skipif(os.getenv("RUN_OPENAI_TESTS") != "1", reason="set RUN_OPENAI_TESTS=1 to call OpenAI")
def test_openai_extracts_sample_pack_01(ground_truth):
    pages = extract_pages(SAMPLE_PDFS[0])
    response = OpenAIExtractor().extract(pages)
    extraction = SupplierExtraction.model_validate_json(response.raw_text)

    assert extraction.supplier_name == ground_truth["supplier-pack-01.pdf"]["fields"]["supplier_name"]
    records = {r["field"]: r for r in verify_evidence(extraction, pages)}
    assert records["unit_price"]["verification_status"] == VERIFIED
