import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies import get_db, get_extractor, get_sessionmaker
from app.core.config import get_settings
from app.extraction.llm_extractor import InformationExtractor
from app.repositories import batch_repository
from app.schemas.batch import BatchCreate, BatchDetail, BatchSummary, ProcessResponse, UploadedFile, UploadResult
from app.schemas.evaluation import SupplierResultRow
from app.services import evaluation_service, results_service, upload_service

router = APIRouter(prefix="/batches", tags=["batches"])


@router.post("", response_model=BatchDetail, status_code=201)
def create_batch(body: BatchCreate, session: Session = Depends(get_db)):
    """Create an empty evaluation batch."""
    batch = batch_repository.create_batch(session, body.name.strip())
    return results_service.batch_detail(session, batch)


@router.get("", response_model=list[BatchSummary])
def list_batches(session: Session = Depends(get_db)):
    return batch_repository.list_batches(session)


@router.get("/{batch_id}", response_model=BatchDetail)
def get_batch(batch_id: uuid.UUID, session: Session = Depends(get_db)):
    """Batch details, including each document's current processing stage."""
    return results_service.batch_detail(session, results_service.get_batch_or_404(session, batch_id))


@router.post("/{batch_id}/upload", response_model=UploadResult)
async def upload_files(batch_id: uuid.UUID, files: list[UploadFile] = File(...), session: Session = Depends(get_db)):
    """Upload supplier PDFs, the Purchase Request CSV and the company rules Markdown file."""
    settings = get_settings()
    incoming = []
    for upload in files:
        # Read one byte more than the limit so oversized files are detected without reading everything.
        content = await upload.read(settings.max_file_size_bytes + 1)
        incoming.append(upload_service.IncomingFile(filename=upload.filename or "unnamed", content=content))

    batch = results_service.get_batch_or_404(session, batch_id)
    accepted = upload_service.upload_files(session, batch, incoming, settings)
    return UploadResult(
        batch=results_service.batch_detail(session, batch),
        accepted_files=[UploadedFile(**item) for item in accepted],
    )


@router.post("/{batch_id}/process", response_model=ProcessResponse, status_code=202)
def process_batch(
    batch_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db),
    session_factory: sessionmaker[Session] = Depends(get_sessionmaker),
    extractor: InformationExtractor = Depends(get_extractor),
):
    """Start the evaluation. It runs in the background; poll GET /batches/{batch_id} for progress."""
    evaluation_service.start_processing(session, batch_id)
    # Commit now, so the background task and other requests see PROCESSING.
    session.commit()
    background_tasks.add_task(evaluation_service.run_batch, batch_id, session_factory, extractor)
    return ProcessResponse(batch_id=batch_id, status="PROCESSING", message="Evaluation started.")


@router.get("/{batch_id}/results", response_model=list[SupplierResultRow])
def get_results(
    batch_id: uuid.UUID,
    decision: str | None = Query(None, description="APPROVE, REJECT or NEEDS A PERSON TO CHECK"),
    processing_status: str | None = Query(None, description="For example COMPLETED or FAILED"),
    session: Session = Depends(get_db),
):
    return results_service.batch_results(session, batch_id, decision, processing_status)
