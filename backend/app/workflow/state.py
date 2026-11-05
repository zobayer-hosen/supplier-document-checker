"""The data passed from one workflow step to the next.

LangGraph gives each node the current state. A node returns only the keys it
changed, and LangGraph merges them into the state for the next node.
"""

from typing import Any, TypedDict

from app.schemas.purchase_request import PurchaseRequestItem


class ProcessingStage:
    """Values stored in `supplier_documents.processing_status` and shown in the UI."""

    UPLOADED = "UPLOADED"
    EXTRACTING_TEXT = "EXTRACTING_TEXT"
    EXTRACTING_INFORMATION = "EXTRACTING_INFORMATION"
    VALIDATING_DATA = "VALIDATING_DATA"
    CHECKING_EVIDENCE = "CHECKING_EVIDENCE"
    COMPARING_PURCHASE_REQUEST = "COMPARING_PURCHASE_REQUEST"
    APPLYING_RULES = "APPLYING_RULES"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

    TERMINAL = {COMPLETED, FAILED}


class SupplierEvaluationState(TypedDict, total=False):
    # Which document we are working on
    batch_id: str
    document_id: str
    filename: str
    storage_path: str
    purchase_request_items: list[PurchaseRequestItem]

    # Text and extraction
    pages: list[dict[str, Any]]
    raw_llm_output: str
    model_name: str
    extraction_attempts: int
    schema_error: str | None
    extracted_data: dict[str, Any]

    # Checks
    evidence: list[dict[str, Any]]
    verified_facts: dict[str, Any]
    purchase_request_item: PurchaseRequestItem | None
    validation_results: list[dict[str, Any]]
    reject_flags: list[dict[str, Any]]
    review_flags: list[dict[str, Any]]

    # Result
    final_decision: str
    decision_reasons: list[dict[str, Any]]
    processing_status: str
    errors: list[str]
