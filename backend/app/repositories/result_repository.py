"""Save a finished evaluation: extraction, evidence, rule results and decision."""

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models import EvaluationDecision, EvidenceRecord, ExtractionResult, SupplierDocument, ValidationResult
from app.utils.json_values import to_json_value
from app.workflow.state import ProcessingStage


def save_evaluation(session: Session, document_id: uuid.UUID, state: dict[str, Any]) -> None:
    """Write all results for one document. Call inside `session_scope` so it is one transaction."""
    document = session.get(SupplierDocument, document_id)
    if document is None:
        raise LookupError(f"Document {document_id} not found")

    session.add(ExtractionResult(
        document_id=document_id,
        extracted_data=state["extracted_data"],
        page_texts=[{"page": p["page"], "source": p["source"], "text": p["text"]} for p in state["pages"]],
        extraction_status="VALIDATED",
        extraction_attempts=state.get("extraction_attempts", 1),
        model_name=state.get("model_name", "unknown"),
    ))

    evidence_ids: dict[str, uuid.UUID] = {}
    for record in state["evidence"]:
        evidence = EvidenceRecord(
            document_id=document_id,
            field_name=record["field"],
            extracted_value=to_json_value(record["value"]),
            exact_text=record["exact_text"],
            page_number=record["page"],
            text_source=record["source"],
            verification_status=record["verification_status"],
            verification_note=record["reason"],
        )
        session.add(evidence)
        session.flush()
        evidence_ids[record["field"]] = evidence.id

    for finding in state["validation_results"]:
        session.add(ValidationResult(
            document_id=document_id,
            rule_code=finding["rule_code"],
            rule_category=finding["rule_category"],
            status=finding["status"],
            expected_value=to_json_value(finding["expected_value"]),
            actual_value=to_json_value(finding["actual_value"]),
            evidence_id=evidence_ids.get(finding["evidence_field"]),
            message=finding["message"],
        ))

    session.add(EvaluationDecision(
        document_id=document_id,
        decision=state["final_decision"],
        reasons=to_json_value(state["decision_reasons"]),
    ))

    document.supplier_name = state["extracted_data"].get("supplier_name")
    document.processing_status = ProcessingStage.COMPLETED
    document.error_message = "; ".join(state.get("errors", [])) or None
