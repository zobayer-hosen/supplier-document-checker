"""Read and write evaluation batches and their Purchase Request rows."""

import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import EvaluationBatch, PurchaseRequestRow
from app.schemas.purchase_request import PurchaseRequestItem


def create_batch(session: Session, name: str) -> EvaluationBatch:
    batch = EvaluationBatch(name=name)
    session.add(batch)
    session.flush()  # assigns the id now
    return batch


def get_batch(session: Session, batch_id: uuid.UUID) -> EvaluationBatch | None:
    return session.get(EvaluationBatch, batch_id)


def get_batch_for_update(session: Session, batch_id: uuid.UUID) -> EvaluationBatch | None:
    """Lock the batch row so two "start processing" requests cannot both start it."""
    statement = select(EvaluationBatch).where(EvaluationBatch.id == batch_id).with_for_update()
    return session.scalars(statement).first()


def list_batches(session: Session, limit: int = 50) -> list[EvaluationBatch]:
    statement = select(EvaluationBatch).order_by(EvaluationBatch.created_at.desc()).limit(limit)
    return list(session.scalars(statement))


def replace_purchase_request(session: Session, batch_id: uuid.UUID, items: list[PurchaseRequestItem]) -> None:
    session.execute(delete(PurchaseRequestRow).where(PurchaseRequestRow.batch_id == batch_id))
    for item in items:
        session.add(PurchaseRequestRow(batch_id=batch_id, **item.model_dump()))


def get_purchase_request_items(session: Session, batch_id: uuid.UUID) -> list[PurchaseRequestItem]:
    statement = select(PurchaseRequestRow).where(PurchaseRequestRow.batch_id == batch_id)
    return [
        PurchaseRequestItem(
            pr_number=row.pr_number,
            item_code=row.item_code,
            item_name=row.item_name,
            unit=row.unit,
            requested_quantity=row.requested_quantity,
            max_unit_price=row.max_unit_price,
            currency=row.currency,
        )
        for row in session.scalars(statement)
    ]
