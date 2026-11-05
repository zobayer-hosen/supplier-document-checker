"""Read the text layer of a PDF, one page at a time."""

from pathlib import Path
from typing import TypedDict

import pymupdf

# A page with fewer readable characters than this is treated as scanned.
MIN_CHARACTERS_FOR_TEXT_PAGE = 20


class PageText(TypedDict):
    page: int  # 1-based, like the page numbers people see
    text: str
    source: str  # "pdf_text" or "ocr"
    needs_ocr: bool


def extract_pages(pdf_path: str | Path) -> list[PageText]:
    """Return the text of every page. Raises ValueError if the PDF cannot be read."""
    try:
        document = pymupdf.open(pdf_path)
    except Exception as error:
        raise ValueError(f"Could not open PDF: {error}") from error

    pages: list[PageText] = []
    with document:
        for index, page in enumerate(document):
            text = page.get_text("text")
            pages.append(
                PageText(
                    page=index + 1,
                    text=text,
                    source="pdf_text",
                    needs_ocr=len(text.strip()) < MIN_CHARACTERS_FOR_TEXT_PAGE,
                )
            )
    return pages
