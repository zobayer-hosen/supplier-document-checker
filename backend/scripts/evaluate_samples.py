"""Run the 10 sample documents through the real pipeline and measure accuracy.

Usage (from the backend folder, with the virtual environment active):

    python -m scripts.evaluate_samples                 # new batch, real LLM + Neon
    python -m scripts.evaluate_samples --batch-id ID   # measure a batch made in the UI

The report is written to docs/evaluation-report.md.
"""

import argparse
import uuid
from datetime import date
from pathlib import Path

from app.core.config import get_settings
from app.database.connection import get_session_factory, session_scope
from app.extraction.llm_extractor import create_extractor
from app.repositories import batch_repository, document_repository
from app.services import evaluation_service, upload_service
from evaluation.metrics import DocumentResult, build_report, render_markdown

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_DATA = PROJECT_ROOT / "sample-data"
REPORT_PATH = PROJECT_ROOT / "docs" / "evaluation-report.md"


def create_and_run_sample_batch(session_factory) -> uuid.UUID:
    files = [
        upload_service.IncomingFile(path.name, path.read_bytes())
        for path in sorted(SAMPLE_DATA.glob("supplier-pack-*.pdf"))
    ]
    files.append(upload_service.IncomingFile("purchase-request.csv", (SAMPLE_DATA / "purchase-request.csv").read_bytes()))
    files.append(upload_service.IncomingFile("company-rules.md", (SAMPLE_DATA / "company-rules.md").read_bytes()))

    extractor = create_extractor()
    with session_scope(session_factory) as session:
        batch = batch_repository.create_batch(session, f"Sample evaluation {date.today()}")
        upload_service.upload_files(session, batch, files, get_settings())
        batch_id = batch.id
    with session_scope(session_factory) as session:
        evaluation_service.start_processing(session, batch_id)

    print(f"Evaluating {len(files) - 2} documents in batch {batch_id} ...")
    evaluation_service.run_batch(batch_id, session_factory, extractor)
    return batch_id


def load_results(session_factory, batch_id: uuid.UUID) -> tuple[list[DocumentResult], str]:
    results, model_names = [], set()
    with session_scope(session_factory) as session:
        for document in document_repository.list_documents(session, batch_id, with_results=True):
            if document.extraction:
                model_names.add(document.extraction.model_name)
            results.append(DocumentResult(
                filename=document.filename,
                processing_status=document.processing_status,
                decision=document.decision.decision if document.decision else None,
                extracted_data=document.extraction.extracted_data if document.extraction else {},
                evidence=[
                    {"field_name": e.field_name, "page_number": e.page_number, "verification_status": e.verification_status}
                    for e in document.evidence_records
                ],
                # H08 can appear several times; ground truth only compares R01-R05 and H01-H07.
                rule_statuses={v.rule_code: v.status for v in document.validation_results},
            ))
    return results, ", ".join(sorted(model_names)) or "unknown"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--batch-id", type=uuid.UUID, help="measure an existing, processed batch")
    args = parser.parse_args()

    session_factory = get_session_factory()
    batch_id = args.batch_id or create_and_run_sample_batch(session_factory)
    results, model_name = load_results(session_factory, batch_id)
    report = build_report(results)

    markdown = render_markdown(report, model_name, str(batch_id), str(date.today()))
    REPORT_PATH.write_text(markdown, encoding="utf-8")
    print(markdown)
    print(f"Report saved to {REPORT_PATH}")


if __name__ == "__main__":
    main()
