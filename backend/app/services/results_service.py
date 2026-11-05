"""Turn stored database records into the shapes the API returns."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import not_found
from app.models import EvaluationBatch, EvaluationDecision, ReviewStatus, SupplierDocument
from app.repositories import batch_repository, document_repository
from app.schemas.batch import BatchDetail, BatchSummary, DashboardSummary, DocumentStatus
from app.schemas.evaluation import (
    DocumentDetail, EvidenceOut, PurchaseRequestOut, SupplierResultRow, ValidationOut,
)
from app.validators.common import PASS, NOT_APPLICABLE
from app.validators.decision import APPROVE_DECISION, REJECT_DECISION, REVIEW_DECISION
from app.validators.purchase_request import find_purchase_request_item
from app.validators.rule_catalog import RULES_BY_CODE
from app.workflow.state import ProcessingStage


def get_batch_or_404(session: Session, batch_id: uuid.UUID) -> EvaluationBatch:
    batch = batch_repository.get_batch(session, batch_id)
    if batch is None:
        raise not_found("batch", batch_id)
    return batch


def get_document_or_404(session: Session, document_id: uuid.UUID, with_results: bool = False) -> SupplierDocument:
    if with_results:
        document = document_repository.get_document_with_results(session, document_id)
    else:
        document = document_repository.get_document(session, document_id)
    if document is None:
        raise not_found("document", document_id)
    return document


def batch_detail(session: Session, batch: EvaluationBatch) -> BatchDetail:
    documents = document_repository.list_documents(session, batch.id)
    return BatchDetail(
        **BatchSummary.model_validate(batch).model_dump(),
        purchase_request_filename=batch.purchase_request_filename,
        rules_filename=batch.rules_filename,
        purchase_request_item_count=len(batch_repository.get_purchase_request_items(session, batch.id)),
        error_message=batch.error_message,
        documents=[DocumentStatus.model_validate(document) for document in documents],
    )


def batch_results(
    session: Session, batch_id: uuid.UUID, decision: str | None = None, processing_status: str | None = None,
) -> list[SupplierResultRow]:
    get_batch_or_404(session, batch_id)
    rows = []
    for document in document_repository.list_documents(session, batch_id, with_results=True):
        data = document.extraction.extracted_data if document.extraction else {}
        row = SupplierResultRow(
            document_id=document.id,
            filename=document.filename,
            supplier_name=document.supplier_name,
            item=" - ".join(part for part in (data.get("item_code"), data.get("item_name")) if part) or None,
            quantity=data.get("quantity"),
            unit_price=data.get("unit_price"),
            processing_status=document.processing_status,
            decision=document.decision.decision if document.decision else None,
            findings_count=sum(1 for f in document.validation_results if f.status not in (PASS, NOT_APPLICABLE)),
            error_message=document.error_message,
        )
        if decision and row.decision != decision:
            continue
        if processing_status and row.processing_status != processing_status:
            continue
        rows.append(row)
    return rows


def document_detail(session: Session, document_id: uuid.UUID) -> DocumentDetail:
    document = get_document_or_404(session, document_id, with_results=True)
    data = document.extraction.extracted_data if document.extraction else None

    pr_item = None
    if data:
        match = find_purchase_request_item(
            data.get("item_code"), data.get("item_name"),
            batch_repository.get_purchase_request_items(session, document.batch_id),
        )
        if match:
            pr_item = PurchaseRequestOut(
                **match.model_dump(exclude={"requested_quantity", "max_unit_price"}),
                requested_quantity=str(match.requested_quantity),
                max_unit_price=str(match.max_unit_price),
            )

    return DocumentDetail(
        id=document.id,
        batch_id=document.batch_id,
        filename=document.filename,
        supplier_name=document.supplier_name,
        page_count=document.page_count,
        processing_status=document.processing_status,
        error_message=document.error_message,
        model_name=document.extraction.model_name if document.extraction else None,
        extracted_data=data,
        purchase_request_item=pr_item,
        decision=document.decision.decision if document.decision else None,
        decision_reasons=document.decision.reasons if document.decision else [],
        has_completed_review=any(r.review_status == ReviewStatus.COMPLETED for r in document.reviews),
    )


def document_validations(session: Session, document_id: uuid.UUID) -> list[ValidationOut]:
    document = get_document_or_404(session, document_id, with_results=True)
    rule_texts = document.batch.rules_text_by_code or {}
    return [
        ValidationOut(
            id=finding.id,
            rule_code=finding.rule_code,
            rule_category=finding.rule_category,
            rule_title=RULES_BY_CODE[finding.rule_code].title if finding.rule_code in RULES_BY_CODE else finding.rule_code,
            rule_text=rule_texts.get(finding.rule_code),
            status=finding.status,
            expected_value=finding.expected_value,
            actual_value=finding.actual_value,
            message=finding.message,
            evidence=EvidenceOut.model_validate(finding.evidence) if finding.evidence else None,
        )
        for finding in sorted(document.validation_results, key=lambda f: f.rule_code)
    ]


def document_evidence(session: Session, document_id: uuid.UUID) -> list[EvidenceOut]:
    document = get_document_or_404(session, document_id, with_results=True)
    return [EvidenceOut.model_validate(record) for record in document.evidence_records]


def dashboard_summary(session: Session) -> DashboardSummary:
    decision_counts = dict(session.execute(
        select(EvaluationDecision.decision, func.count()).group_by(EvaluationDecision.decision)
    ).all())
    status_counts = dict(session.execute(
        select(SupplierDocument.processing_status, func.count()).group_by(SupplierDocument.processing_status)
    ).all())
    total_documents = sum(status_counts.values())
    finished = status_counts.get(ProcessingStage.COMPLETED, 0) + status_counts.get(ProcessingStage.FAILED, 0)

    return DashboardSummary(
        total_batches=session.scalar(select(func.count()).select_from(EvaluationBatch)) or 0,
        total_documents=total_documents,
        approved=decision_counts.get(APPROVE_DECISION, 0),
        rejected=decision_counts.get(REJECT_DECISION, 0),
        needs_review=decision_counts.get(REVIEW_DECISION, 0),
        failed=status_counts.get(ProcessingStage.FAILED, 0),
        in_progress=total_documents - finished,
        recent_batches=[BatchSummary.model_validate(b) for b in batch_repository.list_batches(session, limit=5)],
    )
