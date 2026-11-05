"""Import every model here so SQLAlchemy and Alembic know about all tables."""

from app.models.base import Base
from app.models.batch import BatchStatus, EvaluationBatch, PurchaseRequestRow
from app.models.document import SupplierDocument
from app.models.evaluation import EvaluationDecision, HumanReview, ReviewStatus, ValidationResult
from app.models.evidence import EvidenceRecord, ExtractionResult

__all__ = [
    "Base",
    "BatchStatus",
    "EvaluationBatch",
    "EvaluationDecision",
    "EvidenceRecord",
    "ExtractionResult",
    "HumanReview",
    "PurchaseRequestRow",
    "ReviewStatus",
    "SupplierDocument",
    "ValidationResult",
]
