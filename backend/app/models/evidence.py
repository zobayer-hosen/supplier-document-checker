import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, JsonColumn, UUIDPrimaryKey, created_at_column


class ExtractionResult(UUIDPrimaryKey, Base):
    """Table `extraction_results`: the validated structured output of the LLM."""

    __tablename__ = "extraction_results"

    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("supplier_documents.id", ondelete="CASCADE"), unique=True, index=True,
    )
    extracted_data: Mapped[dict[str, Any]] = mapped_column(JsonColumn)
    page_texts: Mapped[list[dict[str, Any]]] = mapped_column(JsonColumn)
    extraction_status: Mapped[str] = mapped_column(String(30))
    extraction_attempts: Mapped[int] = mapped_column(Integer, default=1)
    model_name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = created_at_column()


class EvidenceRecord(UUIDPrimaryKey, Base):
    """Table `evidence_records`: the exact text that supports one extracted field."""

    __tablename__ = "evidence_records"

    document_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("supplier_documents.id", ondelete="CASCADE"), index=True)
    field_name: Mapped[str] = mapped_column(String(100))
    extracted_value: Mapped[Any] = mapped_column(JsonColumn)
    exact_text: Mapped[str | None] = mapped_column(Text)
    page_number: Mapped[int | None] = mapped_column(Integer)
    text_source: Mapped[str | None] = mapped_column(String(20))  # "pdf_text" or "ocr"
    verification_status: Mapped[str] = mapped_column(String(30), index=True)
    verification_note: Mapped[str | None] = mapped_column(Text)
