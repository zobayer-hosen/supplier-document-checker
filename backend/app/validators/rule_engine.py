"""Run every company rule, in a fixed order, on verified values only."""

from typing import Any

from app.schemas.purchase_request import PurchaseRequestItem
from app.validators.arithmetic import check_arithmetic
from app.validators.common import period_in_days
from app.validators.contract import check_late_penalty, check_quotation_validity, check_supplier_tax_ids
from app.validators.delivery import check_delivery_rejection, check_delivery_review
from app.validators.payment import check_advance_payment, check_payment_terms
from app.validators.price import check_price_rejection, check_price_review
from app.validators.quantity import check_quantity
from app.validators.tax import check_vat
from app.validators.uncertainty import check_uncertainty


def run_company_rules(
    facts: dict[str, Any],
    evidence_records: list[dict[str, Any]],
    purchase_request_item: PurchaseRequestItem | None,
    document_text: str,
) -> list[dict]:
    """Return one finding per rule (H08 may produce several).

    `facts` holds only verified values; anything unverified is None, so a rule
    can never reject or approve based on an unsupported value.
    """
    status_of = {record["field"]: record["verification_status"] for record in evidence_records}
    max_price = purchase_request_item.max_unit_price if purchase_request_item else None
    requested_quantity = purchase_request_item.requested_quantity if purchase_request_item else None
    delivery_days = period_in_days(facts["delivery_period_value"], facts["delivery_period_unit"])

    findings = [
        # Rejection rules
        check_price_rejection(facts["unit_price"], max_price),
        check_advance_payment(facts["advance_payment_percentage"]),
        check_late_penalty(
            status_of["late_penalty_text"],
            facts["late_penalty_percentage"],
            facts["late_penalty_period"],
            facts["late_penalty_basis"],
            document_text,
        ),
        check_supplier_tax_ids(
            facts["supplier_tin"], status_of["supplier_tin"],
            facts["supplier_bin"], status_of["supplier_bin"],
            document_text,
        ),
        check_delivery_rejection(delivery_days),
        # Human-review rules
        check_price_review(facts["unit_price"], max_price),
        check_quantity(facts["quantity"], requested_quantity),
        check_payment_terms(facts["payment_days_min"], facts["payment_days_max"], facts["payment_days_counted_from"]),
        check_delivery_review(delivery_days),
        check_vat(facts["vat_percentage"], facts["vat_amount"], facts["prices_include_vat"]),
        check_arithmetic(
            facts["quantity"], facts["unit_price"], facts["line_total"], facts["subtotal"],
            facts["vat_percentage"], facts["vat_amount"], facts["total_amount"],
        ),
        check_quotation_validity(facts["validity_period_value"], facts["validity_period_unit"]),
    ]
    findings += check_uncertainty(evidence_records, facts["line_item_count"])
    return findings
