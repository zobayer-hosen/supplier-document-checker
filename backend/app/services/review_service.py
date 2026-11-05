"""Human review notes. A review never changes the automated decision; both are kept."""

import uuid

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.repositories import review_repository
from app.schemas.evaluation import PendingReviewItem, ReviewCreate, ReviewOut
from app.services.results_service import get_document_or_404
from app.workflow.state import ProcessingStage


def add_review(session: Session, document_id: uuid.UUID, review: ReviewCreate) -> ReviewOut:
    document = get_document_or_404(session, document_id)
    if document.processing_status not in ProcessingStage.TERMINAL:
        raise AppError(409, "NOT_EVALUATED_YET", "A review can be added after the document has been evaluated.")
    saved = review_repository.add_review(
        session,
        document_id,
        reviewer_name=review.reviewer_name.strip(),
        review_status=review.review_status,
        review_note=review.review_note.strip(),
        reviewer_decision=review.reviewer_decision,
    )
    return ReviewOut.model_validate(saved)


def list_reviews(session: Session, document_id: uuid.UUID) -> list[ReviewOut]:
    get_document_or_404(session, document_id)
    return [ReviewOut.model_validate(review) for review in review_repository.list_reviews(session, document_id)]


def list_pending_reviews(session: Session) -> list[PendingReviewItem]:
    items = []
    for document in review_repository.list_pending_review_documents(session):
        latest = document.reviews[-1] if document.reviews else None
        items.append(PendingReviewItem(
            document_id=document.id,
            batch_id=document.batch_id,
            filename=document.filename,
            supplier_name=document.supplier_name,
            processing_status=document.processing_status,
            decision=document.decision.decision if document.decision else None,
            reasons=document.decision.reasons if document.decision else [{"message": document.error_message}],
            latest_review=ReviewOut.model_validate(latest) if latest else None,
        ))
    return items
