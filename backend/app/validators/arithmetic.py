"""H06: the numbers on the quotation must add up.

Checks (each only when the values exist):
1. line total = quantity x unit price
2. subtotal   = line total (each pack quotes one item)
3. VAT amount = subtotal x VAT% (rounded to 2 decimals)
4. total      = subtotal + VAT amount
"""

from decimal import ROUND_HALF_UP, Decimal

from app.validators.common import NEEDS_REVIEW, PASS, UNVERIFIED, build_validation_result
from app.validators.rule_catalog import AMOUNT_TOLERANCE

CENT = Decimal("0.01")


def _amounts_match(expected: Decimal, actual: Decimal) -> bool:
    return abs(expected - actual) <= AMOUNT_TOLERANCE


def check_arithmetic(
    quantity: Decimal | None,
    unit_price: Decimal | None,
    line_total: Decimal | None,
    subtotal: Decimal | None,
    vat_percentage: Decimal | None,
    vat_amount: Decimal | None,
    total_amount: Decimal | None,
) -> dict:
    if quantity is None or unit_price is None or line_total is None:
        return build_validation_result(
            "H06", UNVERIFIED, "Quantity, unit price or line total is missing or unverified, so the line total cannot be checked.",
            None, None, "line_total",
        )

    # Each entry: (description, expected value, value written in the document, evidence field)
    comparisons: list[tuple[str, Decimal, Decimal, str]] = [
        ("Line total (quantity x unit price)", (quantity * unit_price).quantize(CENT, ROUND_HALF_UP), line_total, "line_total"),
    ]
    if subtotal is not None:
        comparisons.append(("Subtotal (sum of line totals)", line_total, subtotal, "subtotal"))

    base_amount = subtotal if subtotal is not None else line_total
    if vat_percentage is not None and vat_amount is not None:
        expected_vat = (base_amount * vat_percentage / Decimal("100")).quantize(CENT, ROUND_HALF_UP)
        comparisons.append((f"VAT amount ({vat_percentage}% of {base_amount})", expected_vat, vat_amount, "vat_amount"))
    if total_amount is not None:
        expected_total = base_amount + (vat_amount or Decimal("0"))
        comparisons.append(("Total (subtotal + VAT)", expected_total, total_amount, "total_amount"))

    mismatches = [item for item in comparisons if not _amounts_match(item[1], item[2])]
    if mismatches:
        description, expected, actual, evidence_field = mismatches[0]
        details = "; ".join(f"{name}: should be {exp}, document shows {act}" for name, exp, act, _ in mismatches)
        return build_validation_result(
            "H06", NEEDS_REVIEW, f"The numbers do not add up. {details}.",
            str(actual), str(expected), evidence_field,
        )
    checked = ", ".join(item[0] for item in comparisons)
    return build_validation_result("H06", PASS, f"All amounts add up ({checked}).", None, None, "line_total")
