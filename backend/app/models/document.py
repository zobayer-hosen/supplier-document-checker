import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKey, created_at_column
from app.workflow.state import ProcessingStage


class SupplierDocument(UUIDPrimaryKey, Base):
    """Table `supplier_documents`: an uploaded supplier PDF.

    The PDF itself is stored on local disk (`storage_path`), not in the database.
    """

    __tablename__ = "supplier_documents"
    __table_args__ = (UniqueConstraint("batch_id", "sha256", name="uq_document_content_per_batch"),)

    batch_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("evaluation_batches.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    storage_path: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64))
    page_count: Mapped[int | None] = mapped_column(Integer)
    supplier_name: Mapped[str | None] = mapped_column(String(255))
    processing_status: Mapped[str] = mapped_column(String(40), default=ProcessingStage.UPLOADED, index=True)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at_column()

    batch = relationship("EvaluationBatch", back_populates="documents")
    extraction = relationship("ExtractionResult", uselist=False, cascade="all, delete-orphan")
    evidence_records = relationship("EvidenceRecord", cascade="all, delete-orphan")
    validation_results = relationship("ValidationResult", cascade="all, delete-orphan")
    decision = relationship("EvaluationDecision", uselist=False, cascade="all, delete-orphan")
    reviews = relationship("HumanReview", cascade="all, delete-orphan", order_by="HumanReview.created_at")
