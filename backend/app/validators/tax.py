"""H05: VAT must be shown as a separate amount at 15%."""

from decimal import Decimal

from app.validators.common import NEEDS_REVIEW, PASS, build_validation_result
from app.validators.rule_catalog import REQUIRED_VAT_PERCENT


def check_vat(vat_percentage: Decimal | None, vat_amount: Decimal | None, prices_include_vat: bool | None) -> dict:
    expected = f"VAT {REQUIRED_VAT_PERCENT}% shown as a separate amount"
    actual = {"vat_percentage": vat_percentage, "vat_amount": vat_amount, "prices_include_vat": prices_include_vat}

    if prices_include_vat:
        return build_validation_result(
            "H05", NEEDS_REVIEW, "Prices include VAT, so VAT is not shown separately.", actual, expected, "prices_include_vat",
        )
    if vat_percentage is None or vat_amount is None:
        return build_validation_result(
            "H05", NEEDS_REVIEW, "A separate VAT percentage and amount could not be found and verified.",
            actual, expected, "vat_amount",
        )
    if vat_percentage != REQUIRED_VAT_PERCENT:
        return build_validation_result(
            "H05", NEEDS_REVIEW, f"VAT is shown at {vat_percentage}%, not {REQUIRED_VAT_PERCENT}%.",
            actual, expected, "vat_percentage",
        )
    return build_validation_result(
        "H05", PASS, f"VAT {vat_percentage}% is shown separately ({vat_amount}).", actual, expected, "vat_amount",
    )
