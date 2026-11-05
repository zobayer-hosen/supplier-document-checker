"""Start a batch evaluation and run the workflow for each supplier document.

Flow:
1. `start_processing` (inside the HTTP request) checks the batch is READY and
   marks it PROCESSING. A second request gets a 409 instead of a duplicate run.
2. `run_batch` (in the background) runs the LangGraph workflow once per
   document, then marks the batch COMPLETED.
"""

import logging
import uuid

from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.errors import AppError, not_found
from app.database.connection import session_scope
from app.extraction.llm_extractor import InformationExtractor
from app.models import BatchStatus
from app.models.base import utc_now
from app.repositories import batch_repository, document_repository, result_repository
from app.workflow.graph import build_evaluation_graph
from app.workflow.nodes import DocumentContext, WorkflowDependencies
from app.workflow.state import ProcessingStage, SupplierEvaluationState

logger = logging.getLogger(__name__)


def start_processing(session: Session, batch_id: uuid.UUID) -> None:
    batch = batch_repository.get_batch_for_update(session, batch_id)
    if batch is None:
        raise not_found("batch", batch_id)
    if batch.status in (BatchStatus.PROCESSING, BatchStatus.COMPLETED):
        raise AppError(409, "ALREADY_PROCESSED", f"This batch is already {batch.status}.")
    if batch.status != BatchStatus.READY:
        raise AppError(
            400, "BATCH_NOT_READY",
            "Upload at least one supplier PDF, the Purchase Request CSV and the company rules file first.",
        )
    batch.status = BatchStatus.PROCESSING


def build_workflow_dependencies(session_factory: sessionmaker[Session], extractor: InformationExtractor) -> WorkflowDependencies:
    """Connect the workflow to the real database. Each call uses its own short transaction."""

    def load_document_context(document_id: str) -> DocumentContext:
        with session_scope(session_factory) as session:
            document = document_repository.get_document(session, uuid.UUID(document_id))
            if document is None:
                raise LookupError(f"Document {document_id} not found")
            return DocumentContext(
                batch_id=str(document.batch_id),
                filename=document.filename,
                storage_path=document.storage_path,
                purchase_request_items=batch_repository.get_purchase_request_items(session, document.batch_id),
            )

    def update_stage(document_id: str, stage: str) -> None:
        with session_scope(session_factory) as session:
            document_repository.update_stage(session, uuid.UUID(document_id), stage)

    def save_result(state: SupplierEvaluationState) -> None:
        with session_scope(session_factory) as session:
            result_repository.save_evaluation(session, uuid.UUID(state["document_id"]), state)

    def mark_failed(document_id: str, errors: list[str]) -> None:
        with session_scope(session_factory) as session:
            document_repository.mark_failed(session, uuid.UUID(document_id), errors)

    return WorkflowDependencies(
        extractor=extractor,
        load_document_context=load_document_context,
        update_stage=update_stage,
        save_result=save_result,
        mark_failed=mark_failed,
        max_extraction_retries=get_settings().max_extraction_retries,
    )


def run_batch(batch_id: uuid.UUID, session_factory: sessionmaker[Session], extractor: InformationExtractor) -> None:
    """Evaluate every document in the batch. The batch never stays stuck in PROCESSING."""
    try:
        _evaluate_documents(batch_id, session_factory, extractor)
    except Exception:
        logger.exception("Batch %s failed", batch_id)
        with session_scope(session_factory) as session:
            batch = batch_repository.get_batch(session, batch_id)
            batch.status = BatchStatus.FAILED
            batch.error_message = "The batch could not be processed. Check the server log."
            batch.completed_at = utc_now()


def _evaluate_documents(batch_id: uuid.UUID, session_factory: sessionmaker[Session], extractor: InformationExtractor) -> None:
    """Run the workflow for each document, one after another, independently."""
    deps = build_workflow_dependencies(session_factory, extractor)
    workflow = build_evaluation_graph(deps)

    with session_scope(session_factory) as session:
        document_ids = [
            str(document.id)
            for document in document_repository.list_documents(session, batch_id)
            if document.processing_status not in ProcessingStage.TERMINAL
        ]

    for document_id in document_ids:
        try:
            workflow.invoke({"document_id": document_id})
        except Exception as error:  # one broken document must not stop the others
            logger.exception("Unexpected error while evaluating document %s", document_id)
            deps.mark_failed(document_id, [f"Unexpected error: {type(error).__name__}"])

    with session_scope(session_factory) as session:
        batch = batch_repository.get_batch(session, batch_id)
        documents = document_repository.list_documents(session, batch_id)
        if all(document.processing_status in ProcessingStage.TERMINAL for document in documents):
            batch.status = BatchStatus.COMPLETED
        else:
            batch.status = BatchStatus.FAILED
            batch.error_message = "Some documents did not reach a final state."
        batch.completed_at = utc_now()
