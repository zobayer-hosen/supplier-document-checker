"""One test per business rule case listed in the PRD (section 17.1)."""

from decimal import Decimal as D

import pytest

from app.evidence.verifier import NOT_FOUND, VERIFIED
from app.validators.arithmetic import check_arithmetic
from app.validators.common import NEEDS_REVIEW, NOT_APPLICABLE, PASS, REJECT, UNVERIFIED
from app.validators.contract import check_late_penalty, check_quotation_validity, check_supplier_tax_ids
from app.validators.delivery import check_delivery_rejection, check_delivery_review
from app.validators.payment import check_advance_payment, check_payment_terms
from app.validators.price import check_price_rejection, check_price_review
from app.validators.quantity import check_quantity
from app.validators.tax import check_vat

DOCUMENT_WITH_IDS = "Supplier TIN: 101458013391 BIN: 000170141-0101"


# ---------- Price: R01 and H01 ----------

@pytest.mark.parametrize(
    "quoted, r01, h01",
    [
        ("100.00", PASS, PASS),            # equals maximum
        ("90.00", PASS, PASS),             # below maximum
        ("103.00", PASS, NEEDS_REVIEW),    # exactly 3% above -> review, not reject
        ("103.01", REJECT, NOT_APPLICABLE),  # 3.01% above -> reject
    ],
)
def test_price_rules(quoted, r01, h01):
    assert check_price_rejection(D(quoted), D("100.00"))["status"] == r01
    assert check_price_review(D(quoted), D("100.00"))["status"] == h01


def test_price_missing_is_unverified():
    assert check_price_rejection(None, D("100"))["status"] == UNVERIFIED
    assert check_price_review(D("100"), None)["status"] == UNVERIFIED


# ---------- Advance payment: R02 ----------

@pytest.mark.parametrize("advance, expected", [("0", PASS), ("20", PASS), ("20.01", REJECT), ("40", REJECT)])
def test_advance_payment(advance, expected):
    assert check_advance_payment(D(advance))["status"] == expected


def test_advance_payment_missing_is_unverified():
    assert check_advance_payment(None)["status"] == UNVERIFIED


# ---------- Penalty: R03 ----------

def test_missing_penalty_clause_rejects():
    result = check_late_penalty(NOT_FOUND, None, None, None, "1. Payment. 2. Delivery within 20 days of PO.")
    assert result["status"] == REJECT


def test_missing_penalty_but_document_mentions_delay_needs_person():
    result = check_late_penalty(NOT_FOUND, None, None, None, "Delay. Supplier will compensate the buyer.")
    assert result["status"] == UNVERIFIED


@pytest.mark.parametrize("percentage, expected", [("0.5", PASS), ("1", PASS), ("0.49", REJECT)])
def test_penalty_threshold(percentage, expected):
    assert check_late_penalty(VERIFIED, D(percentage), "week", "order value", "")["status"] == expected


def test_daily_penalty_is_converted_to_weekly():
    assert check_late_penalty(VERIFIED, D("0.1"), "day", "order value", "")["status"] == PASS  # 0.7% per week


def test_penalty_without_order_value_base_needs_person():
    assert check_late_penalty(VERIFIED, D("0.5"), "week", None, "")["status"] == UNVERIFIED


def test_monthly_penalty_needs_person():
    assert check_late_penalty(VERIFIED, D("2"), "month", "order value", "")["status"] == UNVERIFIED


# ---------- TIN / BIN: R04 ----------

def test_both_ids_present_pass():
    assert check_supplier_tax_ids("1", VERIFIED, "2", VERIFIED, DOCUMENT_WITH_IDS)["status"] == PASS


def test_missing_tin_rejects():
    result = check_supplier_tax_ids(None, NOT_FOUND, "000170141-0101", VERIFIED, "BIN: 000170141-0101")
    assert result["status"] == REJECT
    assert "TIN" in result["message"]


def test_missing_bin_rejects():
    result = check_supplier_tax_ids("101458013391", VERIFIED, None, NOT_FOUND, "TIN: 101458013391")
    assert result["status"] == REJECT
    assert "BIN" in result["message"]


def test_id_not_extracted_but_written_in_document_needs_person():
    result = check_supplier_tax_ids(None, NOT_FOUND, "2", VERIFIED, DOCUMENT_WITH_IDS)
    assert result["status"] == UNVERIFIED


# ---------- Delivery: R05 and H04 ----------

@pytest.mark.parametrize(
    "days, r05, h04",
    [(30, PASS, PASS), (31, PASS, NEEDS_REVIEW), (45, PASS, NEEDS_REVIEW), (46, REJECT, NOT_APPLICABLE), (60, REJECT, NOT_APPLICABLE)],
)
def test_delivery_rules(days, r05, h04):
    assert check_delivery_rejection(days)["status"] == r05
    assert check_delivery_review(days)["status"] == h04


# ---------- Quantity: H02 ----------

@pytest.mark.parametrize("quoted, expected", [("1000", PASS), ("1050", PASS), ("950", PASS), ("1051", NEEDS_REVIEW), ("825", NEEDS_REVIEW)])
def test_quantity(quoted, expected):
    assert check_quantity(D(quoted), D("1000"))["status"] == expected


# ---------- Payment terms: H03 ----------

def test_payment_within_range_passes():
    assert check_payment_terms(30, 30, "delivery")["status"] == PASS
    assert check_payment_terms(60, 60, "delivery and acceptance of goods")["status"] == PASS


def test_payment_outside_range_needs_person():
    assert check_payment_terms(90, 90, "delivery")["status"] == NEEDS_REVIEW
    assert check_payment_terms(15, 15, "delivery")["status"] == NEEDS_REVIEW


def test_unclear_payment_terms_need_person():
    assert check_payment_terms(30, 90, None)["status"] == NEEDS_REVIEW  # a range is unclear
    assert check_payment_terms(30, 30, "invoice")["status"] == NEEDS_REVIEW  # not counted from delivery
    assert check_payment_terms(None, None, None)["status"] == UNVERIFIED


# ---------- VAT: H05 ----------

def test_vat_shown_separately_passes():
    assert check_vat(D("15"), D("849600.00"), False)["status"] == PASS


def test_missing_separate_vat_needs_person():
    assert check_vat(None, None, True)["status"] == NEEDS_REVIEW
    assert check_vat(None, None, None)["status"] == NEEDS_REVIEW


def test_wrong_vat_rate_needs_person():
    assert check_vat(D("10"), D("100"), False)["status"] == NEEDS_REVIEW


# ---------- Arithmetic: H06 ----------

def test_correct_amounts_pass():
    result = check_arithmetic(D("12000"), D("472.00"), D("5664000.00"), D("5664000.00"), D("15"), D("849600.00"), D("6513600.00"))
    assert result["status"] == PASS


def test_incorrect_line_total_needs_person():
    result = check_arithmetic(D("50000"), D("6.40"), D("322000.00"), D("322000.00"), D("15"), D("48300.00"), D("370300.00"))
    assert result["status"] == NEEDS_REVIEW
    assert "320000.00" in result["message"]


def test_incorrect_subtotal_needs_person():
    result = check_arithmetic(D("100"), D("10"), D("1000"), D("1100"), None, None, None)
    assert result["status"] == NEEDS_REVIEW


def test_vat_included_total_passes():
    assert check_arithmetic(D("3000"), D("94.00"), D("282000.00"), None, None, None, D("282000.00"))["status"] == PASS


# ---------- Validity: H07 ----------

@pytest.mark.parametrize("value, unit, expected", [(30, "days", PASS), (45, "days", PASS), (29, "days", NEEDS_REVIEW), (4, "weeks", NEEDS_REVIEW), (1, "months", UNVERIFIED)])
def test_quotation_validity(value, unit, expected):
    assert check_quotation_validity(value, unit)["status"] == expected

