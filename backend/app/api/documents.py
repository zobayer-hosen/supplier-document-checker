import uuid
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.core.errors import AppError
from app.schemas.evaluation import DocumentDetail, EvidenceOut, ReviewCreate, ReviewOut, ValidationOut
from app.services import results_service, review_service

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document(document_id: uuid.UUID, session: Session = Depends(get_db)):
    """Supplier details, extracted values, matched PR line and the automated decision."""
    return results_service.document_detail(session, document_id)


@router.get("/{document_id}/validations", response_model=list[ValidationOut])
def get_validations(document_id: uuid.UUID, session: Session = Depends(get_db)):
    """Rule-by-rule outcomes, each with its supporting evidence."""
    return results_service.document_validations(session, document_id)


@router.get("/{document_id}/evidence", response_model=list[EvidenceOut])
def get_evidence(document_id: uuid.UUID, session: Session = Depends(get_db)):
    return results_service.document_evidence(session, document_id)


@router.get("/{document_id}/file", response_class=FileResponse)
def get_document_file(document_id: uuid.UUID, session: Session = Depends(get_db)):
    """The original PDF, so the reviewer can compare evidence with the page."""
    document = results_service.get_document_or_404(session, document_id)
    path = Path(document.storage_path)
    if not path.is_file():
        raise AppError(404, "FILE_NOT_FOUND", "The uploaded PDF is no longer on disk.")
    return FileResponse(path, media_type="application/pdf", filename=document.filename, content_disposition_type="inline")


@router.post("/{document_id}/reviews", response_model=ReviewOut, status_code=201)
def add_review(document_id: uuid.UUID, body: ReviewCreate, session: Session = Depends(get_db)):
    """Save a reviewer's note. The automated decision is kept unchanged."""
    return review_service.add_review(session, document_id, body)


@router.get("/{document_id}/reviews", response_model=list[ReviewOut])
def get_reviews(document_id: uuid.UUID, session: Session = Depends(get_db)):
    return review_service.list_reviews(session, document_id)
