"""Run the real LangGraph workflow with in-memory fakes for the LLM and database."""

import json
from pathlib import Path

import pytest

from app.extraction.pdf_extractor import extract_pages
from app.inputs.csv_parser import parse_purchase_request
from app.workflow.graph import build_evaluation_graph
from app.workflow.nodes import DocumentContext, WorkflowDependencies
from app.workflow.state import ProcessingStage
from tests.conftest import SAMPLE_DATA, SAMPLE_PDFS, FakeExtractor, ground_truth_answer

PURCHASE_REQUEST = parse_purchase_request((SAMPLE_DATA / "purchase-request.csv").read_bytes())


class InMemoryStore:
    """Records what the workflow would write to the database."""

    def __init__(self, fail_on_save: bool = False):
        self.stages: list[str] = []
        self.saved: dict | None = None
        self.failed_with: list[str] | None = None
        self.fail_on_save = fail_on_save

    def save(self, state):
        if self.fail_on_save:
            raise ConnectionError("database is down")
        self.saved = state

    def mark_failed(self, document_id, errors):
        self.failed_with = errors


def run_workflow(pdf_path: Path, extractor, store: InMemoryStore | None = None, ocr=None) -> tuple[dict, InMemoryStore]:
    store = store or InMemoryStore()
    deps = WorkflowDependencies(
        extractor=extractor,
        load_document_context=lambda _id: DocumentContext("batch-1", pdf_path.name, str(pdf_path), PURCHASE_REQUEST),
        update_stage=lambda _id, stage: store.stages.append(stage),
        save_result=store.save,
        mark_failed=store.mark_failed,
        max_extraction_retries=2,
    )
    if ocr is not None:
        deps.read_page_with_ocr = ocr
    result = build_evaluation_graph(deps).invoke({"document_id": "doc-1"})
    return result, store


def test_pdf_text_is_extracted_page_by_page():
    pages = extract_pages(SAMPLE_PDFS[0])
    assert len(pages) == 1
    assert pages[0]["page"] == 1 and not pages[0]["needs_ocr"]
    assert "Padma Textile Mills Ltd" in pages[0]["text"]


@pytest.mark.parametrize("pdf_path", SAMPLE_PDFS, ids=lambda p: p.name)
def test_sample_document_gets_expected_decision_and_rules(pdf_path, ground_truth):
    """With correct extraction, the rule engine must match the manual ground truth exactly."""
    truth = ground_truth[pdf_path.name]
    result, store = run_workflow(pdf_path, FakeExtractor())

    assert result["processing_status"] == ProcessingStage.COMPLETED
    assert result["final_decision"] == truth["expected_decision"]
    statuses = {f["rule_code"]: f["status"] for f in result["validation_results"] if f["rule_code"] != "H08"}
    assert statuses == truth["expected_rules"]
    # Every quote in the ground truth must be verified against the real PDF text.
    unverified = [r for r in result["evidence"] if r["verification_status"] == "UNVERIFIED"]
    assert unverified == []
    assert store.saved is not None


def test_workflow_runs_every_stage_in_order():
    _, store = run_workflow(SAMPLE_PDFS[0], FakeExtractor())
    assert store.stages == [
        ProcessingStage.EXTRACTING_TEXT,
        ProcessingStage.EXTRACTING_INFORMATION,
        ProcessingStage.VALIDATING_DATA,
        ProcessingStage.CHECKING_EVIDENCE,
        ProcessingStage.COMPARING_PURCHASE_REQUEST,
        ProcessingStage.APPLYING_RULES,
    ]


def test_invalid_llm_answer_is_retried():
    answers = {"Padma Textile Mills Ltd": ["not json", '{"quantity": "many"}', ground_truth_answer("supplier-pack-01.pdf")]}
    extractor = FakeExtractor(answers)
    result, _ = run_workflow(SAMPLE_PDFS[0], extractor)
    assert extractor.calls == 3
    assert result["final_decision"] == "APPROVE"


def test_document_fails_after_retry_limit():
    extractor = FakeExtractor({"Padma Textile Mills Ltd": ["bad"] * 5})
    result, store = run_workflow(SAMPLE_PDFS[0], extractor)
    assert extractor.calls == 3  # first try + 2 retries
    assert result["processing_status"] == ProcessingStage.FAILED
    assert "final_decision" not in result
    assert store.failed_with and store.saved is None


def test_invented_evidence_prevents_approval():
    answer = json.loads(ground_truth_answer("supplier-pack-01.pdf"))
    for quote in answer["evidence"]:
        if quote["field"] == "unit_price":
            quote["exact_text"] = "Unit price 472.00 BDT, special offer"  # not in the PDF
    result, _ = run_workflow(SAMPLE_PDFS[0], FakeExtractor({"Padma Textile Mills Ltd": [json.dumps(answer)]}))
    assert result["final_decision"] == "NEEDS A PERSON TO CHECK"
    assert any(f["rule_code"] == "H08" and f["evidence_field"] == "unit_price" for f in result["review_flags"])


def test_item_not_in_purchase_request_needs_person():
    answer = json.loads(ground_truth_answer("supplier-pack-01.pdf"))
    answer["item_code"] = None
    answer["item_name"] = None
    result, _ = run_workflow(SAMPLE_PDFS[0], FakeExtractor({"Padma Textile Mills Ltd": [json.dumps(answer)]}))
    assert result["final_decision"] == "NEEDS A PERSON TO CHECK"


def test_corrupted_pdf_fails(tmp_path):
    broken = tmp_path / "broken.pdf"
    broken.write_bytes(b"%PDF-1.4 this is not really a pdf")
    result, store = run_workflow(broken, FakeExtractor())
    assert result["processing_status"] == ProcessingStage.FAILED
    assert store.failed_with


def test_database_save_failure_is_not_completed():
    result, store = run_workflow(SAMPLE_PDFS[0], FakeExtractor(), store=InMemoryStore(fail_on_save=True))
    assert result["processing_status"] == ProcessingStage.FAILED
    assert "Saving the result failed" in store.failed_with[-1]


def test_scanned_pdf_goes_through_ocr(tmp_path):
    """A PDF with no text layer is sent to OCR. A fake OCR returns the real page text."""
    import pymupdf

    scanned = tmp_path / "scanned.pdf"
    with pymupdf.open() as document:
        document.new_page()
        document.save(scanned)

    real_text = extract_pages(SAMPLE_PDFS[0])[0]["text"]
    result, _ = run_workflow(scanned, FakeExtractor(), ocr=lambda path, page: real_text)
    assert result["pages"][0]["source"] == "ocr"
    # OCR can misread characters, so an OCR document always goes to a person.
    assert result["final_decision"] == "NEEDS A PERSON TO CHECK"


def test_scanned_pdf_without_ocr_fails(tmp_path):
    import pymupdf

    scanned = tmp_path / "scanned.pdf"
    with pymupdf.open() as document:
        document.new_page()
        document.save(scanned)

    def no_ocr(path, page):
        raise RuntimeError("GEMINI_API_KEY is not set")

    result, _ = run_workflow(scanned, FakeExtractor(), ocr=no_ocr)
    assert result["processing_status"] == ProcessingStage.FAILED
