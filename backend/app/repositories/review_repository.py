"""Read and write human review notes."""

import uuid

from sqlalchemy import exists, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import EvaluationDecision, HumanReview, ReviewStatus, SupplierDocument
from app.models.base import utc_now
from app.validators.decision import REVIEW_DECISION
from app.workflow.state import ProcessingStage


def add_review(
    session: Session,
    document_id: uuid.UUID,
    reviewer_name: str,
    review_status: str,
    review_note: str,
    reviewer_decision: str | None,
) -> HumanReview:
    review = HumanReview(
        document_id=document_id,
        reviewer_name=reviewer_name,
        review_status=review_status,
        review_note=review_note,
        reviewer_decision=reviewer_decision,
        reviewed_at=utc_now() if review_status == ReviewStatus.COMPLETED else None,
    )
    session.add(review)
    session.flush()
    return review


def list_reviews(session: Session, document_id: uuid.UUID) -> list[HumanReview]:
    statement = select(HumanReview).where(HumanReview.document_id == document_id).order_by(HumanReview.created_at)
    return list(session.scalars(statement))


def list_pending_review_documents(session: Session) -> list[SupplierDocument]:
    """Documents that need a person (or failed) and have no COMPLETED review yet."""
    completed_review = exists().where(
        HumanReview.document_id == SupplierDocument.id,
        HumanReview.review_status == ReviewStatus.COMPLETED,
    )
    statement = (
        select(SupplierDocument)
        .outerjoin(EvaluationDecision, EvaluationDecision.document_id == SupplierDocument.id)
        .where(
            or_(
                EvaluationDecision.decision == REVIEW_DECISION,
                SupplierDocument.processing_status == ProcessingStage.FAILED,
            ),
            ~completed_review,
        )
        .options(selectinload(SupplierDocument.decision), selectinload(SupplierDocument.reviews))
        .order_by(SupplierDocument.created_at.desc())
    )
    return list(session.scalars(statement))
