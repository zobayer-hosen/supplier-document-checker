"""CSV parsing, company-rules loading and upload file checks."""

from decimal import Decimal

import pytest

from app.inputs.csv_parser import PurchaseRequestError, parse_purchase_request
from app.inputs.file_validation import FileKind, FileValidationError, validate_upload
from app.inputs.rules_loader import CompanyRulesError, load_company_rules
from tests.conftest import SAMPLE_DATA

LIMIT = 20 * 1024 * 1024


def test_sample_purchase_request_is_parsed():
    items = parse_purchase_request((SAMPLE_DATA / "purchase-request.csv").read_bytes())
    assert [item.item_code for item in items] == ["A", "B", "C", "D", "E"]
    assert items[0].item_name == "Cotton twill fabric, 280 gsm"
    assert items[0].requested_quantity == Decimal("12000")
    assert items[3].max_unit_price == Decimal("6.50")
    assert items[0].currency == "BDT"  # read from the header "(BDT)"


def test_csv_with_different_column_names_is_mapped():
    content = b"Item code,Item name,Qty,Max unit price,Currency\nX1,Buttons,100,2.5,USD\n"
    item = parse_purchase_request(content)[0]
    assert (item.item_code, item.item_name, item.requested_quantity, item.currency) == ("X1", "Buttons", Decimal("100"), "USD")


def test_csv_missing_a_required_column_is_rejected():
    with pytest.raises(PurchaseRequestError, match="max_unit_price"):
        parse_purchase_request(b"Item,Description,Quantity requested\nA,Fabric,10\n")


def test_csv_with_non_numeric_value_is_rejected():
    with pytest.raises(PurchaseRequestError, match="Row 2"):
        parse_purchase_request(b"Description,Quantity,Maximum unit price\nFabric,ten,5\n")


def test_sample_company_rules_match_the_rule_engine():
    rules = load_company_rules((SAMPLE_DATA / "company-rules.md").read_bytes())
    assert set(rules.rule_text_by_code) == {f"R0{i}" for i in range(1, 6)} | {f"H0{i}" for i in range(1, 9)}
    assert "20%" in rules.rule_text_by_code["R02"]
    assert "0.5%" in rules.rule_text_by_code["R03"]


def test_changed_company_rules_are_detected():
    changed = (SAMPLE_DATA / "company-rules.md").read_text(encoding="utf-8").replace("more than 20%", "more than 30%")
    with pytest.raises(CompanyRulesError, match="R02"):
        load_company_rules(changed.encode())


def test_real_pdf_is_accepted():
    content = (SAMPLE_DATA / "supplier-pack-01.pdf").read_bytes()
    result = validate_upload("supplier-pack-01.pdf", content, LIMIT, 100)
    assert result.kind is FileKind.SUPPLIER_PDF and result.page_count == 1


def test_fake_pdf_is_rejected():
    with pytest.raises(FileValidationError, match="not a real PDF"):
        validate_upload("quote.pdf", b"hello, I am not a PDF", LIMIT, 100)


def test_corrupted_pdf_is_rejected():
    with pytest.raises(FileValidationError, match="damaged"):
        validate_upload("quote.pdf", b"%PDF-1.4 broken content", LIMIT, 100)


def test_unsupported_extension_is_rejected():
    with pytest.raises(FileValidationError, match="unsupported"):
        validate_upload("quote.docx", b"data", LIMIT, 100)


def test_too_large_file_is_rejected():
    with pytest.raises(FileValidationError, match="larger than"):
        validate_upload("rules.md", b"x" * 11, 10, 100)
