"""Validate uploaded files and attach them to a batch.

An upload is all-or-nothing: if any file is invalid, nothing is saved and the
user gets one error per bad file.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AppError
from app.inputs.file_validation import FileKind, FileValidationError, ValidatedFile, validate_upload
from app.models import BatchStatus, EvaluationBatch
from app.repositories import batch_repository, document_repository


@dataclass
class IncomingFile:
    filename: str
    content: bytes


def _safe_filename(filename: str) -> str:
    name = Path(filename).name  # drop any folder part such as "../../"
    return re.sub(r"[^A-Za-z0-9._-]", "_", name) or "file"


def _validate_all(files: list[IncomingFile], batch: EvaluationBatch, session: Session, settings: Settings) -> list[ValidatedFile]:
    """Validate every file and return them, or raise one error listing every problem."""
    errors: list[dict[str, str]] = []
    validated: list[ValidatedFile] = []
    seen_hashes = document_repository.existing_hashes(session, batch.id)

    for incoming in files:
        try:
            file = validate_upload(incoming.filename, incoming.content, settings.max_file_size_bytes, settings.max_pdf_pages)
        except FileValidationError as error:
            errors.append({"filename": error.filename, "message": error.message})
            continue

        if file.kind is FileKind.SUPPLIER_PDF:
            if file.sha256 in seen_hashes:
                errors.append({
                    "filename": file.filename,
                    "message": f"is a duplicate of '{seen_hashes[file.sha256]}' already in this batch.",
                })
                continue
            seen_hashes[file.sha256] = file.filename
        validated.append(file)

    for kind, label in ((FileKind.PURCHASE_REQUEST_CSV, "Purchase Request CSV"), (FileKind.COMPANY_RULES_MD, "company rules file")):
        if sum(1 for file in validated if file.kind is kind) > 1:
            errors.append({"filename": "(upload)", "message": f"Upload only one {label} per batch."})

    if errors:
        raise AppError(400, "INVALID_FILES", "Some files could not be accepted. Nothing was saved.", errors)
    return validated


def _batch_is_ready(session: Session, batch: EvaluationBatch) -> bool:
    has_documents = bool(document_repository.existing_hashes(session, batch.id))
    has_purchase_request = bool(batch_repository.get_purchase_request_items(session, batch.id))
    return has_documents and has_purchase_request and batch.rules_sha256 is not None


def upload_files(session: Session, batch: EvaluationBatch, files: list[IncomingFile], settings: Settings) -> list[dict]:
    """Validate and store files. Returns a short description of each accepted file."""
    if batch.status not in (BatchStatus.CREATED, BatchStatus.READY):
        raise AppError(409, "BATCH_LOCKED", f"Files cannot be added to a batch that is {batch.status}.")
    if not files:
        raise AppError(400, "NO_FILES", "Select at least one file to upload.")

    validated = _validate_all(files, batch, session, settings)

    batch_folder = settings.upload_path / str(batch.id)
    batch_folder.mkdir(parents=True, exist_ok=True)
    accepted = []

    for file in validated:
        if file.kind is FileKind.SUPPLIER_PDF:
            storage_path = batch_folder / f"{file.sha256[:12]}_{_safe_filename(file.filename)}"
            storage_path.write_bytes(file.content)
            document_repository.add_document(
                session, batch.id, file.filename, str(storage_path), file.sha256, file.page_count,
            )
            detail = f"{file.page_count} page(s)"
        elif file.kind is FileKind.PURCHASE_REQUEST_CSV:
            batch_repository.replace_purchase_request(session, batch.id, file.purchase_request_items)
            batch.purchase_request_filename = file.filename
            detail = f"{len(file.purchase_request_items)} item row(s)"
        else:
            batch.rules_filename = file.filename
            batch.rules_sha256 = file.company_rules.sha256
            batch.rules_text_by_code = file.company_rules.rule_text_by_code
            detail = f"{len(file.company_rules.rule_text_by_code)} rules matched"
        accepted.append({"filename": file.filename, "kind": file.kind.value, "detail": detail})

    session.flush()
    batch.total_documents = len(document_repository.existing_hashes(session, batch.id))
    batch.status = BatchStatus.READY if _batch_is_ready(session, batch) else BatchStatus.CREATED
    return accepted
