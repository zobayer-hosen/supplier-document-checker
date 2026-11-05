"""API shapes for batches, uploads and the dashboard."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BatchCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200, examples=["October supplier quotes"])


class DocumentStatus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    supplier_name: str | None
    processing_status: str
    error_message: str | None


class BatchSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    status: str
    total_documents: int
    created_at: datetime
    completed_at: datetime | None


class BatchDetail(BatchSummary):
    purchase_request_filename: str | None
    rules_filename: str | None
    purchase_request_item_count: int
    error_message: str | None
    documents: list[DocumentStatus]


class UploadedFile(BaseModel):
    filename: str
    kind: str
    detail: str


class UploadResult(BaseModel):
    batch: BatchDetail
    accepted_files: list[UploadedFile]


class ProcessResponse(BaseModel):
    batch_id: uuid.UUID
    status: str
    message: str


class DashboardSummary(BaseModel):
    total_batches: int
    total_documents: int
    approved: int
    rejected: int
    needs_review: int
    failed: int
    in_progress: int
    recent_batches: list[BatchSummary]
