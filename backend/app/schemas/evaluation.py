"""API shapes for results, evidence, rule outcomes and human reviews."""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class SupplierResultRow(BaseModel):
    """One row of the batch results table."""

    document_id: uuid.UUID
    filename: str
    supplier_name: str | None
    item: str | None
    quantity: str | None
    unit_price: str | None
    processing_status: str
    decision: str | None
    findings_count: int
    error_message: str | None


class EvidenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    field_name: str
    extracted_value: Any
    exact_text: str | None
    page_number: int | None
    text_source: str | None
    verification_status: str
    verification_note: str | None


class ValidationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    rule_code: str
    rule_category: str
    rule_title: str
    rule_text: str | None
    status: str
    expected_value: Any
    actual_value: Any
    message: str
    evidence: EvidenceOut | None


class PurchaseRequestOut(BaseModel):
    pr_number: str | None
    item_code: str | None
    item_name: str
    unit: str | None
    requested_quantity: str
    max_unit_price: str
    currency: str | None


class DocumentDetail(BaseModel):
    id: uuid.UUID
    batch_id: uuid.UUID
    filename: str
    supplier_name: str | None
    page_count: int | None
    processing_status: str
    error_message: str | None
    model_name: str | None
    extracted_data: dict[str, Any] | None
    purchase_request_item: PurchaseRequestOut | None
    decision: str | None
    decision_reasons: list[dict[str, Any]]
    has_completed_review: bool


class ReviewCreate(BaseModel):
    reviewer_name: str = Field(min_length=1, max_length=100)
    review_status: Literal["IN_PROGRESS", "COMPLETED"] = "COMPLETED"
    reviewer_decision: Literal["APPROVE", "REJECT"] | None = None
    review_note: str = Field(min_length=1, max_length=5000)


class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    reviewer_name: str
    review_status: str
    reviewer_decision: str | None
    review_note: str
    created_at: datetime
    reviewed_at: datetime | None


class PendingReviewItem(BaseModel):
    document_id: uuid.UUID
    batch_id: uuid.UUID
    filename: str
    supplier_name: str | None
    processing_status: str
    decision: str | None
    reasons: list[dict[str, Any]]
    latest_review: ReviewOut | None
