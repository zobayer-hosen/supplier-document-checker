"""H02: quoted quantity against the requested quantity.

    difference_percent = abs(quoted - requested) / requested * 100
    REVIEW when difference_percent > 5
"""

from decimal import Decimal

from app.validators.common import NEEDS_REVIEW, PASS, UNVERIFIED, build_validation_result, format_percent
from app.validators.rule_catalog import MAX_QUANTITY_DIFFERENCE_PERCENT


def check_quantity(quoted_quantity: Decimal | None, requested_quantity: Decimal | None) -> dict:
    if quoted_quantity is None or requested_quantity is None or requested_quantity <= 0:
        return build_validation_result(
            "H02", UNVERIFIED, "Quoted or requested quantity is missing or unverified.",
            quoted_quantity, requested_quantity, "quantity",
        )
    difference = abs(quoted_quantity - requested_quantity) / requested_quantity * Decimal("100")
    expected = f"{requested_quantity} (+/- {MAX_QUANTITY_DIFFERENCE_PERCENT}%)"
    if difference > MAX_QUANTITY_DIFFERENCE_PERCENT:
        return build_validation_result(
            "H02", NEEDS_REVIEW,
            f"Quoted quantity {quoted_quantity} differs from the requested {requested_quantity} "
            f"by {format_percent(difference)}.",
            quoted_quantity, expected, "quantity",
        )
    return build_validation_result(
        "H02", PASS, f"Quoted quantity {quoted_quantity} is within 5% of the requested {requested_quantity}.",
        quoted_quantity, expected, "quantity",
    )
