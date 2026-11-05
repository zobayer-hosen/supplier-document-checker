"""Create all tables.

Revision ID: 0001
Revises:
Create Date: 2026-11-05
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def _id() -> sa.Column:
    return sa.Column("id", UUID(as_uuid=True), primary_key=True)


def _document_fk() -> sa.Column:
    return sa.Column(
        "document_id", UUID(as_uuid=True),
        sa.ForeignKey("supplier_documents.id", ondelete="CASCADE"), nullable=False,
    )


def upgrade() -> None:
    op.create_table(
        "evaluation_batches",
        _id(),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("total_documents", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("purchase_request_filename", sa.String(255)),
        sa.Column("rules_filename", sa.String(255)),
        sa.Column("rules_sha256", sa.String(64)),
        sa.Column("rules_text_by_code", JSONB),
        sa.Column("error_message", sa.Text),
    )
    op.create_index("ix_evaluation_batches_status", "evaluation_batches", ["status"])

    op.create_table(
        "purchase_requests",
        _id(),
        sa.Column("batch_id", UUID(as_uuid=True), sa.ForeignKey("evaluation_batches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("pr_number", sa.String(50)),
        sa.Column("item_code", sa.String(50)),
        sa.Column("item_name", sa.String(255), nullable=False),
        sa.Column("unit", sa.String(50)),
        sa.Column("requested_quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("max_unit_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(10)),
    )
    op.create_index("ix_purchase_requests_batch_id", "purchase_requests", ["batch_id"])

    op.create_table(
        "supplier_documents",
        _id(),
        sa.Column("batch_id", UUID(as_uuid=True), sa.ForeignKey("evaluation_batches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("storage_path", sa.Text, nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("page_count", sa.Integer),
        sa.Column("supplier_name", sa.String(255)),
        sa.Column("processing_status", sa.String(40), nullable=False),
        sa.Column("error_message", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("batch_id", "sha256", name="uq_document_content_per_batch"),
    )
    op.create_index("ix_supplier_documents_batch_id", "supplier_documents", ["batch_id"])
    op.create_index("ix_supplier_documents_processing_status", "supplier_documents", ["processing_status"])

    op.create_table(
        "extraction_results",
        _id(),
        _document_fk(),
        sa.Column("extracted_data", JSONB, nullable=False),
        sa.Column("page_texts", JSONB, nullable=False),
        sa.Column("extraction_status", sa.String(30), nullable=False),
        sa.Column("extraction_attempts", sa.Integer, nullable=False),
        sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_extraction_results_document_id", "extraction_results", ["document_id"], unique=True)

    op.create_table(
        "evidence_records",
        _id(),
        _document_fk(),
        sa.Column("field_name", sa.String(100), nullable=False),
        sa.Column("extracted_value", JSONB),
        sa.Column("exact_text", sa.Text),
        sa.Column("page_number", sa.Integer),
        sa.Column("text_source", sa.String(20)),
        sa.Column("verification_status", sa.String(30), nullable=False),
        sa.Column("verification_note", sa.Text),
    )
    op.create_index("ix_evidence_records_document_id", "evidence_records", ["document_id"])
    op.create_index("ix_evidence_records_verification_status", "evidence_records", ["verification_status"])

    op.create_table(
        "validation_results",
        _id(),
        _document_fk(),
        sa.Column("rule_code", sa.String(10), nullable=False),
        sa.Column("rule_category", sa.String(30), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("expected_value", JSONB),
        sa.Column("actual_value", JSONB),
        sa.Column("evidence_id", UUID(as_uuid=True), sa.ForeignKey("evidence_records.id", ondelete="SET NULL")),
        sa.Column("message", sa.Text, nullable=False),
    )
    op.create_index("ix_validation_results_document_id", "validation_results", ["document_id"])
    op.create_index("ix_validation_results_rule_code", "validation_results", ["rule_code"])

    op.create_table(
        "evaluation_decisions",
        _id(),
        _document_fk(),
        sa.Column("decision", sa.String(40), nullable=False),
        sa.Column("reasons", JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_evaluation_decisions_document_id", "evaluation_decisions", ["document_id"], unique=True)
    op.create_index("ix_evaluation_decisions_decision", "evaluation_decisions", ["decision"])

    op.create_table(
        "human_reviews",
        _id(),
        _document_fk(),
        sa.Column("reviewer_name", sa.String(100), nullable=False),
        sa.Column("review_status", sa.String(30), nullable=False),
        sa.Column("reviewer_decision", sa.String(40)),
        sa.Column("review_note", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_human_reviews_document_id", "human_reviews", ["document_id"])


def downgrade() -> None:
    for table in (
        "human_reviews", "evaluation_decisions", "validation_results", "evidence_records",
        "extraction_results", "supplier_documents", "purchase_requests", "evaluation_batches",
    ):
        op.drop_table(table)
