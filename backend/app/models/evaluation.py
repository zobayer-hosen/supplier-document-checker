import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, JsonColumn, UUIDPrimaryKey, created_at_column


class ValidationResult(UUIDPrimaryKey, Base):
    """Table `validation_results`: the outcome of one rule for one document."""

    __tablename__ = "validation_results"

    document_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("supplier_documents.id", ondelete="CASCADE"), index=True)
    rule_code: Mapped[str] = mapped_column(String(10), index=True)
    rule_category: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(30))
    expected_value: Mapped[Any] = mapped_column(JsonColumn)
    actual_value: Mapped[Any] = mapped_column(JsonColumn)
    evidence_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("evidence_records.id", ondelete="SET NULL"))
    message: Mapped[str] = mapped_column(Text)

    evidence = relationship("EvidenceRecord")


class EvaluationDecision(UUIDPrimaryKey, Base):
    """Table `evaluation_decisions`: the automated decision. Never changed by a human review."""

    __tablename__ = "evaluation_decisions"

    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("supplier_documents.id", ondelete="CASCADE"), unique=True, index=True,
    )
    decision: Mapped[str] = mapped_column(String(40), index=True)
    reasons: Mapped[list[dict[str, Any]]] = mapped_column(JsonColumn)
    created_at: Mapped[datetime] = created_at_column()


class ReviewStatus:
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class HumanReview(UUIDPrimaryKey, Base):
    """Table `human_reviews`: a reviewer's note. Kept separate from the automated decision."""

    __tablename__ = "human_reviews"

    document_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("supplier_documents.id", ondelete="CASCADE"), index=True)
    reviewer_name: Mapped[str] = mapped_column(String(100))
    review_status: Mapped[str] = mapped_column(String(30))
    reviewer_decision: Mapped[str | None] = mapped_column(String(40))
    review_note: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at_column()
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
