from app.evidence.verifier import CONFLICTING, NOT_FOUND, UNVERIFIED, VERIFIED, verified_values, verify_evidence
from app.schemas.extraction import SupplierExtraction
from app.validators.uncertainty import check_uncertainty

PAGES = [{
    "page": 1,
    "source": "pdf_text",
    "text": "Padma Textile Mills Ltd\nUnit price (BDT)\nmetre\n472.00\n1. Payment. 10% advance payable with the purchase order. Balance payable within 45 days after delivery and\nacceptance of goods.",
}]


def status_of(extraction: SupplierExtraction, field: str) -> str:
    records = verify_evidence(extraction, PAGES)
    return next(r for r in records if r["field"] == field)["verification_status"]


def test_quote_found_on_page_is_verified():
    extraction = SupplierExtraction(unit_price="472.00", evidence=[{"field": "unit_price", "exact_text": "metre 472.00", "page": 1}])
    assert status_of(extraction, "unit_price") == VERIFIED


def test_quote_split_over_two_lines_is_still_verified():
    text = "Balance payable within 45 days after delivery and acceptance of goods."
    extraction = SupplierExtraction(payment_terms=text, evidence=[{"field": "payment_terms", "exact_text": text, "page": 1}])
    assert status_of(extraction, "payment_terms") == VERIFIED


def test_missing_evidence_is_unverified():
    extraction = SupplierExtraction(unit_price="472.00")
    assert status_of(extraction, "unit_price") == UNVERIFIED


def test_invented_quote_is_unverified():
    extraction = SupplierExtraction(unit_price="450.00", evidence=[{"field": "unit_price", "exact_text": "Unit Price: 450.00", "page": 1}])
    assert status_of(extraction, "unit_price") == UNVERIFIED


def test_quote_that_does_not_contain_the_value_is_unverified():
    extraction = SupplierExtraction(unit_price="480.00", evidence=[{"field": "unit_price", "exact_text": "metre 472.00", "page": 1}])
    assert status_of(extraction, "unit_price") == UNVERIFIED


def test_wrong_page_number_is_unverified():
    extraction = SupplierExtraction(unit_price="472.00", evidence=[{"field": "unit_price", "exact_text": "472.00", "page": 3}])
    assert status_of(extraction, "unit_price") == UNVERIFIED


def test_null_value_is_not_found():
    assert status_of(SupplierExtraction(), "supplier_tin") == NOT_FOUND


def test_conflicting_values_are_flagged_and_removed():
    extraction = SupplierExtraction(
        unit_price="472.00",
        evidence=[{"field": "unit_price", "exact_text": "472.00", "page": 1}],
        conflicts=[{"field": "unit_price", "details": "table says 472.00, terms say 470.00"}],
    )
    records = verify_evidence(extraction, PAGES)
    assert next(r for r in records if r["field"] == "unit_price")["verification_status"] == CONFLICTING
    assert verified_values(extraction, records)["unit_price"] is None
    assert any(f["evidence_field"] == "unit_price" for f in check_uncertainty(records, 1))


def test_unverified_values_are_hidden_from_rules():
    extraction = SupplierExtraction(unit_price="999.00", evidence=[{"field": "unit_price", "exact_text": "999.00", "page": 1}])
    records = verify_evidence(extraction, PAGES)
    assert verified_values(extraction, records)["unit_price"] is None


def test_zero_advance_supported_by_no_advance_wording():
    pages = [{"page": 1, "source": "pdf_text", "text": "No advance payment required."}]
    extraction = SupplierExtraction(
        advance_payment_percentage="0",
        evidence=[{"field": "advance_payment_percentage", "exact_text": "No advance payment required.", "page": 1}],
    )
    record = next(r for r in verify_evidence(extraction, pages) if r["field"] == "advance_payment_percentage")
    assert record["verification_status"] == VERIFIED


def test_missing_required_value_creates_review_finding():
    records = verify_evidence(SupplierExtraction(), PAGES)
    fields = {f["evidence_field"] for f in check_uncertainty(records, 1)}
    assert {"unit_price", "quantity", "supplier_name"} <= fields
