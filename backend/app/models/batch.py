import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, JsonColumn, UUIDPrimaryKey, created_at_column


class BatchStatus:
    CREATED = "CREATED"  # waiting for files
    READY = "READY"  # PDFs, CSV and rules uploaded
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"  # every document is COMPLETED or FAILED
    FAILED = "FAILED"  # the batch itself could not be processed


class EvaluationBatch(UUIDPrimaryKey, Base):
    __tablename__ = "evaluation_batches"

    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(30), default=BatchStatus.CREATED, index=True)
    total_documents: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = created_at_column()
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Inputs shared by every document in the batch
    purchase_request_filename: Mapped[str | None] = mapped_column(String(255))
    rules_filename: Mapped[str | None] = mapped_column(String(255))
    rules_sha256: Mapped[str | None] = mapped_column(String(64))
    rules_text_by_code: Mapped[dict[str, Any] | None] = mapped_column(JsonColumn)
    error_message: Mapped[str | None] = mapped_column(Text)

    documents = relationship("SupplierDocument", back_populates="batch", cascade="all, delete-orphan")
    purchase_request_items = relationship("PurchaseRequestRow", back_populates="batch", cascade="all, delete-orphan")


class PurchaseRequestRow(UUIDPrimaryKey, Base):
    """Table `purchase_requests`: one normalized CSV row."""

    __tablename__ = "purchase_requests"

    batch_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("evaluation_batches.id", ondelete="CASCADE"), index=True)
    pr_number: Mapped[str | None] = mapped_column(String(50))
    item_code: Mapped[str | None] = mapped_column(String(50))
    item_name: Mapped[str] = mapped_column(String(255))
    unit: Mapped[str | None] = mapped_column(String(50))
    requested_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    max_unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    currency: Mapped[str | None] = mapped_column(String(10))

    batch = relationship("EvaluationBatch", back_populates="purchase_request_items")
