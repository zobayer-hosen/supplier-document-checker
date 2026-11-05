"""Decide what kind of file was uploaded by looking at its content.

The filename and the browser's MIME type can both be wrong, so we check:
- PDF: starts with "%PDF-", opens with PyMuPDF, page count within the limit.
- CSV: UTF-8 text that parses as a Purchase Request.
- Markdown: UTF-8 text that contains our company rules.
"""

import hashlib
from dataclasses import dataclass
from enum import Enum

import pymupdf

from app.inputs.csv_parser import PurchaseRequestError, parse_purchase_request
from app.inputs.rules_loader import CompanyRulesError, LoadedRules, load_company_rules
from app.schemas.purchase_request import PurchaseRequestItem


class FileKind(str, Enum):
    SUPPLIER_PDF = "SUPPLIER_PDF"
    PURCHASE_REQUEST_CSV = "PURCHASE_REQUEST_CSV"
    COMPANY_RULES_MD = "COMPANY_RULES_MD"


ALLOWED_EXTENSIONS = {
    ".pdf": FileKind.SUPPLIER_PDF,
    ".csv": FileKind.PURCHASE_REQUEST_CSV,
    ".md": FileKind.COMPANY_RULES_MD,
}


class FileValidationError(ValueError):
    def __init__(self, filename: str, message: str):
        super().__init__(f"{filename}: {message}")
        self.filename = filename
        self.message = message


@dataclass
class ValidatedFile:
    filename: str
    kind: FileKind
    content: bytes
    sha256: str
    page_count: int | None = None
    purchase_request_items: list[PurchaseRequestItem] | None = None
    company_rules: LoadedRules | None = None


def _extension(filename: str) -> str:
    dot = filename.rfind(".")
    return filename[dot:].casefold() if dot != -1 else ""


def check_pdf(filename: str, content: bytes, max_pages: int) -> int:
    """Return the page count, or raise if the PDF cannot be used."""
    if not content.startswith(b"%PDF-"):
        raise FileValidationError(filename, "is not a real PDF file (content does not start with %PDF-).")
    try:
        with pymupdf.open(stream=content, filetype="pdf") as document:
            if document.needs_pass:
                raise FileValidationError(filename, "is password protected.")
            page_count = document.page_count
    except FileValidationError:
        raise
    except Exception as error:
        raise FileValidationError(filename, "is damaged and cannot be opened.") from error

    if page_count == 0:
        raise FileValidationError(filename, "has no pages.")
    if page_count > max_pages:
        raise FileValidationError(filename, f"has {page_count} pages; the limit is {max_pages}.")
    return page_count


def validate_upload(filename: str, content: bytes, max_size_bytes: int, max_pdf_pages: int) -> ValidatedFile:
    """Validate one uploaded file and return its parsed details."""
    kind = ALLOWED_EXTENSIONS.get(_extension(filename))
    if kind is None:
        raise FileValidationError(filename, "has an unsupported type. Upload .pdf, .csv or .md files.")
    if not content:
        raise FileValidationError(filename, "is empty.")
    if len(content) > max_size_bytes:
        raise FileValidationError(filename, f"is larger than {max_size_bytes // (1024 * 1024)} MB.")

    validated = ValidatedFile(
        filename=filename,
        kind=kind,
        content=content,
        sha256=hashlib.sha256(content).hexdigest(),
    )

    try:
        if kind is FileKind.SUPPLIER_PDF:
            validated.page_count = check_pdf(filename, content, max_pdf_pages)
        elif kind is FileKind.PURCHASE_REQUEST_CSV:
            validated.purchase_request_items = parse_purchase_request(content)
        else:
            validated.company_rules = load_company_rules(content)
    except (PurchaseRequestError, CompanyRulesError) as error:
        raise FileValidationError(filename, str(error)) from error

    return validated
