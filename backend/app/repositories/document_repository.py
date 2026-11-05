"""Read and write supplier documents."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import SupplierDocument
from app.workflow.state import ProcessingStage


def add_document(
    session: Session, batch_id: uuid.UUID, filename: str, storage_path: str, sha256: str, page_count: int | None,
) -> SupplierDocument:
    document = SupplierDocument(
        batch_id=batch_id, filename=filename, storage_path=storage_path, sha256=sha256, page_count=page_count,
    )
    session.add(document)
    session.flush()
    return document


def get_document(session: Session, document_id: uuid.UUID) -> SupplierDocument | None:
    return session.get(SupplierDocument, document_id)


def get_document_with_results(session: Session, document_id: uuid.UUID) -> SupplierDocument | None:
    statement = (
        select(SupplierDocument)
        .where(SupplierDocument.id == document_id)
        .options(
            selectinload(SupplierDocument.extraction),
            selectinload(SupplierDocument.decision),
            selectinload(SupplierDocument.validation_results),
            selectinload(SupplierDocument.evidence_records),
            selectinload(SupplierDocument.reviews),
        )
    )
    return session.scalars(statement).first()


def list_documents(session: Session, batch_id: uuid.UUID, with_results: bool = False) -> list[SupplierDocument]:
    statement = select(SupplierDocument).where(SupplierDocument.batch_id == batch_id).order_by(SupplierDocument.filename)
    if with_results:
        statement = statement.options(
            selectinload(SupplierDocument.extraction),
            selectinload(SupplierDocument.decision),
            selectinload(SupplierDocument.validation_results),
        )
    return list(session.scalars(statement))


def existing_hashes(session: Session, batch_id: uuid.UUID) -> dict[str, str]:
    """Return {sha256: filename} of the PDFs already in the batch (for duplicate checks)."""
    statement = select(SupplierDocument.sha256, SupplierDocument.filename).where(SupplierDocument.batch_id == batch_id)
    return {sha256: filename for sha256, filename in session.execute(statement)}


def update_stage(session: Session, document_id: uuid.UUID, stage: str) -> None:
    document = session.get(SupplierDocument, document_id)
    if document is not None:
        document.processing_status = stage


def mark_failed(session: Session, document_id: uuid.UUID, errors: list[str]) -> None:
    document = session.get(SupplierDocument, document_id)
    if document is not None:
        document.processing_status = ProcessingStage.FAILED
        document.error_message = "; ".join(errors) or "Processing failed."
