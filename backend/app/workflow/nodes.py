"""One function per workflow step.

Each node receives the current state plus `deps` (the outside services it may
use: the LLM, the database, ...). Passing `deps` in, instead of importing them,
lets the tests swap in fakes.

A node that hits a fatal problem sets `processing_status` to FAILED. The
routing functions in `graph.py` then send the document to `record_failure`.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from pydantic import ValidationError

from app.evidence.verifier import verified_values, verify_evidence as check_evidence
from app.extraction.llm_extractor import ExtractionError, InformationExtractor
from app.extraction.ocr_extractor import ocr_page
from app.extraction.pdf_extractor import extract_pages
from app.schemas.extraction import SupplierExtraction
from app.schemas.purchase_request import PurchaseRequestItem
from app.validators.common import BLOCKING_REVIEW_STATUSES, REJECT
from app.validators.decision import make_decision as decide
from app.validators.purchase_request import compare_with_purchase_request
from app.validators.rule_engine import run_company_rules
from app.workflow.state import ProcessingStage, SupplierEvaluationState


@dataclass
class DocumentContext:
    batch_id: str
    filename: str
    storage_path: str
    purchase_request_items: list[PurchaseRequestItem]


@dataclass
class WorkflowDependencies:
    extractor: InformationExtractor
    load_document_context: Callable[[str], DocumentContext]
    update_stage: Callable[[str, str], None]
    save_result: Callable[[SupplierEvaluationState], None]
    mark_failed: Callable[[str, list[str]], None]
    max_extraction_retries: int = 2
    read_page_with_ocr: Callable[[str, int], str] = field(default=ocr_page)


def _fail(state: SupplierEvaluationState, message: str) -> dict:
    return {"processing_status": ProcessingStage.FAILED, "errors": state.get("errors", []) + [message]}


def load_document(state: SupplierEvaluationState, deps: WorkflowDependencies) -> dict:
    """Load the document's file path and the batch's Purchase Request."""
    try:
        context = deps.load_document_context(state["document_id"])
    except LookupError as error:
        return _fail(state, str(error))
    if not Path(context.storage_path).is_file():
        return _fail(state, f"Uploaded file is missing on disk: {context.filename}")
    return {
        "batch_id": context.batch_id,
        "filename": context.filename,
        "storage_path": context.storage_path,
        "purchase_request_items": context.purchase_request_items,
        "errors": [],
        "extraction_attempts": 0,
    }


def extract_text(state: SupplierEvaluationState, deps: WorkflowDependencies) -> dict:
    deps.update_stage(state["document_id"], ProcessingStage.EXTRACTING_TEXT)
    try:
        pages = extract_pages(state["storage_path"])
    except ValueError as error:
        return _fail(state, f"The PDF is corrupted or unreadable: {error}")
    return {"pages": pages}


def ocr_fallback(state: SupplierEvaluationState, deps: WorkflowDependencies) -> dict:
    """Run OCR only on the pages that have no usable text layer."""
    pages = [dict(page) for page in state["pages"]]
    errors = list(state.get("errors", []))
    for page in pages:
        if not page["needs_ocr"]:
            continue
        try:
            page["text"] = deps.read_page_with_ocr(state["storage_path"], page["page"])
            page["source"] = "ocr"
            page["needs_ocr"] = False
        except Exception as error:
            # Not fatal on its own: other pages may still be readable. The error
            # is kept, so the document cannot be approved automatically.
            errors.append(f"OCR failed on page {page['page']}: {error}")
    return {"pages": pages, "errors": errors}


def extract_information(state: SupplierEvaluationState, deps: WorkflowDependencies) -> dict:
    """Ask the LLM for structured fields. Only readable pages are sent."""
    deps.update_stage(state["document_id"], ProcessingStage.EXTRACTING_INFORMATION)
    readable_pages = [page for page in state["pages"] if page["text"].strip()]
    attempts = state.get("extraction_attempts", 0) + 1
    try:
        response = deps.extractor.extract(readable_pages, previous_error=state.get("schema_error"))
    except ExtractionError as error:
        return {**_fail(state, f"Information extraction failed: {error}"), "extraction_attempts": attempts}
    return {"raw_llm_output": response.raw_text, "model_name": response.model_name, "extraction_attempts": attempts}


def validate_schema(state: SupplierEvaluationState, deps: WorkflowDependencies) -> dict:
    """Check the LLM's JSON with Pydantic. On failure, keep the error for a retry."""
    deps.update_stage(state["document_id"], ProcessingStage.VALIDATING_DATA)
    try:
        extraction = SupplierExtraction.model_validate_json(state["raw_llm_output"])
    except ValidationError as error:
        message = str(error)[:2000]
        if state["extraction_attempts"] > deps.max_extraction_retries:
            return {**_fail(state, f"LLM answer did not match the schema after {state['extraction_attempts']} attempts."), "schema_error": message}
        return {"schema_error": message}
    return {"extracted_data": extraction.model_dump(mode="json"), "schema_error": None}


def verify_evidence(state: SupplierEvaluationState, deps: WorkflowDependencies) -> dict:
    deps.update_stage(state["document_id"], ProcessingStage.CHECKING_EVIDENCE)
    extraction = SupplierExtraction.model_validate(state["extracted_data"])
    evidence = check_evidence(extraction, state["pages"])
    return {"evidence": evidence, "verified_facts": verified_values(extraction, evidence)}


def compare_purchase_request(state: SupplierEvaluationState, deps: WorkflowDependencies) -> dict:
    deps.update_stage(state["document_id"], ProcessingStage.COMPARING_PURCHASE_REQUEST)
    item, findings = compare_with_purchase_request(state["verified_facts"], state["purchase_request_items"])
    return {"purchase_request_item": item, "validation_results": findings}


def validate_company_rules(state: SupplierEvaluationState, deps: WorkflowDependencies) -> dict:
    deps.update_stage(state["document_id"], ProcessingStage.APPLYING_RULES)
    document_text = "\n".join(page["text"] for page in state["pages"])
    findings = state.get("validation_results", []) + run_company_rules(
        state["verified_facts"], state["evidence"], state.get("purchase_request_item"), document_text,
    )
    return {
        "validation_results": findings,
        "reject_flags": [f for f in findings if f["status"] == REJECT],
        "review_flags": [f for f in findings if f["status"] in BLOCKING_REVIEW_STATUSES],
    }


def make_decision(state: SupplierEvaluationState, deps: WorkflowDependencies) -> dict:
    decision, reasons = decide(state["validation_results"], state.get("errors", []))
    return {"final_decision": decision, "decision_reasons": reasons}


def save_result(state: SupplierEvaluationState, deps: WorkflowDependencies) -> dict:
    """Save everything in one transaction. Only a successful save means COMPLETED."""
    try:
        deps.save_result(state)
    except Exception as error:
        failed = _fail(state, f"Saving the result failed: {type(error).__name__}")
        deps.mark_failed(state["document_id"], failed["errors"])
        return failed
    return {"processing_status": ProcessingStage.COMPLETED}


def record_failure(state: SupplierEvaluationState, deps: WorkflowDependencies) -> dict:
    deps.mark_failed(state["document_id"], state.get("errors", []))
    return {"processing_status": ProcessingStage.FAILED}
