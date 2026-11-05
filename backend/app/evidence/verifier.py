"""Check that the LLM's evidence really supports each extracted value.

An LLM quote is never trusted just because the LLM returned it. A field is
VERIFIED only when all of these are true:
1. The quoted page exists.
2. The quote is really on that page (ignoring line breaks and letter case).
3. The quote contains the extracted value.

Field statuses:
- VERIFIED     value is supported by text on the page
- UNVERIFIED   value given, but no quote supports it
- NOT_FOUND    the LLM says the value is not in the document
- CONFLICTING  the document gives two different values
"""

from decimal import Decimal
from typing import Any

from app.schemas.extraction import EVIDENCE_FIELD_FOR, EvidenceQuote, SupplierExtraction
from app.utils.text import contains_phrase, find_numbers, normalize_text

VERIFIED = "VERIFIED"
UNVERIFIED = "UNVERIFIED"
NOT_FOUND = "NOT_FOUND"
CONFLICTING = "CONFLICTING"

_ZERO_WORDS = ("no", "nil", "none", "without", "zero")
_UNIT_WORDS = {"days": "day", "weeks": "week", "months": "month", "day": "day", "week": "week", "month": "month"}


def value_is_supported(field: str, value: Any, quote: str) -> bool:
    """True when the quote contains the extracted value."""
    if isinstance(value, bool):
        keyword = "includ" if value else "vat"
        return keyword in normalize_text(quote)

    if isinstance(value, (int, Decimal)):
        if value == 0 and any(contains_phrase(quote, word) for word in _ZERO_WORDS):
            return True
        return any(number == Decimal(value) for number in find_numbers(quote))

    text_value = str(value)
    if field.endswith("_unit") or field == "late_penalty_period":
        return _UNIT_WORDS.get(text_value, text_value) in normalize_text(quote)
    return contains_phrase(quote, text_value)


def _check_quote(field: str, value: Any, quote: EvidenceQuote, pages_by_number: dict[int, dict]) -> str | None:
    """Return None if the quote is good, otherwise the reason it is not."""
    page = pages_by_number.get(quote.page)
    if page is None:
        return f"page {quote.page} does not exist"
    if normalize_text(quote.exact_text) not in normalize_text(page["text"]):
        return f"quoted text was not found on page {quote.page}"
    if not value_is_supported(field, value, quote.exact_text):
        return "quoted text does not contain the extracted value"
    return None


def verify_evidence(extraction: SupplierExtraction, pages: list[dict]) -> list[dict[str, Any]]:
    """Return one evidence record per important field."""
    pages_by_number = {page["page"]: page for page in pages}
    conflicting_fields = {conflict.field for conflict in extraction.conflicts}
    records: list[dict[str, Any]] = []

    for field, evidence_field in EVIDENCE_FIELD_FOR.items():
        value = getattr(extraction, field)
        quotes = [quote for quote in extraction.evidence if quote.field == evidence_field]
        record: dict[str, Any] = {
            "field": field,
            "value": value,
            "exact_text": quotes[0].exact_text if quotes else None,
            "page": quotes[0].page if quotes else None,
            "source": None,
            "verification_status": UNVERIFIED,
            "reason": None,
        }

        if field in conflicting_fields or evidence_field in conflicting_fields:
            details = "; ".join(c.details for c in extraction.conflicts if c.field in (field, evidence_field))
            record.update(verification_status=CONFLICTING, reason=f"document gives conflicting values: {details}")
        elif value is None:
            record.update(verification_status=NOT_FOUND, reason="value not found in the document")
        elif not quotes:
            record["reason"] = "no evidence quote was given"
        else:
            reasons = []
            for quote in quotes:
                problem = _check_quote(field, value, quote, pages_by_number)
                if problem is None:
                    record.update(
                        exact_text=quote.exact_text,
                        page=quote.page,
                        source=pages_by_number[quote.page]["source"],
                        verification_status=VERIFIED,
                        reason=None,
                    )
                    break
                reasons.append(problem)
            else:
                record["reason"] = "; ".join(reasons)

        records.append(record)
    return records


def verified_values(extraction: SupplierExtraction, evidence_records: list[dict[str, Any]]) -> dict[str, Any]:
    """Values the rules may trust. Anything not VERIFIED becomes None."""
    statuses = {record["field"]: record["verification_status"] for record in evidence_records}
    values = {}
    for field in SupplierExtraction.model_fields:
        if field in ("evidence", "conflicts"):
            continue
        if field in statuses and statuses[field] != VERIFIED:
            values[field] = None
        else:
            values[field] = getattr(extraction, field)
    return values
