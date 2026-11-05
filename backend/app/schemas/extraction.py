"""The exact shape we expect back from the LLM.

Rules for every field:
- If the value is not written in the document, it stays `None`. Never `0`.
- Numbers are copied as written (without thousands separators).
- Periods keep their original unit ("4 weeks" -> value 4, unit "weeks").
  Python converts them to days later, so the LLM never does arithmetic.
"""

from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field

PeriodUnit = Literal["days", "weeks", "months"]


class EvidenceQuote(BaseModel):
    """Exact text copied from the document that supports one field."""

    field: str
    exact_text: str
    page: int = Field(ge=1)


class ConflictNote(BaseModel):
    """The document gives two different values for the same field."""

    field: str
    details: str


class SupplierExtraction(BaseModel):
    # Supplier identification
    supplier_name: Optional[str] = None
    supplier_tin: Optional[str] = None
    supplier_bin: Optional[str] = None

    # Quotation header
    quotation_number: Optional[str] = None
    quotation_date: Optional[str] = None
    purchase_request_reference: Optional[str] = None

    # Quoted item (each sample pack quotes one item)
    line_item_count: Optional[int] = None
    item_code: Optional[str] = None
    item_name: Optional[str] = None
    unit: Optional[str] = None
    quantity: Optional[Decimal] = None
    unit_price: Optional[Decimal] = None
    line_total: Optional[Decimal] = None

    # Totals and tax
    currency: Optional[str] = None
    prices_include_vat: Optional[bool] = None
    subtotal: Optional[Decimal] = None
    vat_percentage: Optional[Decimal] = None
    vat_amount: Optional[Decimal] = None
    total_amount: Optional[Decimal] = None

    # Payment
    advance_payment_percentage: Optional[Decimal] = None
    payment_terms: Optional[str] = None
    payment_days_min: Optional[int] = None
    payment_days_max: Optional[int] = None
    payment_days_counted_from: Optional[str] = None

    # Delivery
    delivery_period_value: Optional[int] = None
    delivery_period_unit: Optional[PeriodUnit] = None

    # Late-delivery penalty
    late_penalty_text: Optional[str] = None
    late_penalty_percentage: Optional[Decimal] = None
    late_penalty_period: Optional[Literal["day", "week", "month"]] = None
    late_penalty_basis: Optional[str] = None

    # Quotation validity
    validity_period_value: Optional[int] = None
    validity_period_unit: Optional[PeriodUnit] = None

    conflicts: list[ConflictNote] = Field(default_factory=list)
    evidence: list[EvidenceQuote] = Field(default_factory=list)


# Fields that need an exact quote from the document before Python trusts them.
# Each field is checked against the quote listed for the evidence field on the
# right. Most fields have their own quote; a few share one (for example the
# delivery unit is checked inside the delivery quote).
EVIDENCE_FIELD_FOR = {
    "supplier_name": "supplier_name",
    "supplier_tin": "supplier_tin",
    "supplier_bin": "supplier_bin",
    "item_code": "item_code",
    "item_name": "item_name",
    "unit": "unit",
    "quantity": "quantity",
    "unit_price": "unit_price",
    "line_total": "line_total",
    "currency": "currency",
    "prices_include_vat": "prices_include_vat",
    "subtotal": "subtotal",
    "vat_percentage": "vat_percentage",
    "vat_amount": "vat_amount",
    "total_amount": "total_amount",
    "advance_payment_percentage": "advance_payment_percentage",
    "payment_terms": "payment_terms",
    "payment_days_min": "payment_terms",
    "payment_days_max": "payment_terms",
    "payment_days_counted_from": "payment_terms",
    "delivery_period_value": "delivery_period_value",
    "delivery_period_unit": "delivery_period_value",
    "late_penalty_text": "late_penalty_text",
    "late_penalty_percentage": "late_penalty_text",
    "late_penalty_period": "late_penalty_text",
    "late_penalty_basis": "late_penalty_text",
    "validity_period_value": "validity_period_value",
    "validity_period_unit": "validity_period_value",
}

# Values the rules cannot work without. If one is missing or unverified, the
# document can never be approved automatically.
REQUIRED_FIELDS = [
    "supplier_name",
    "quantity",
    "unit_price",
    "line_total",
    "advance_payment_percentage",
    "payment_terms",
    "delivery_period_value",
    "validity_period_value",
]
