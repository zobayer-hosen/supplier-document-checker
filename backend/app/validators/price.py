"""R01 and H01: quoted unit price against the Purchase Request maximum.

    rejection_threshold = maximum_unit_price * 1.03
    REJECT when quoted price > threshold            (R01)
    REVIEW when maximum < quoted price <= threshold (H01)
"""

from decimal import Decimal

from app.validators.common import (
    NOT_APPLICABLE, NEEDS_REVIEW, PASS, REJECT, UNVERIFIED,
    build_validation_result, format_percent, percent_above,
)
from app.validators.rule_catalog import PRICE_TOLERANCE_PERCENT


def rejection_threshold(maximum_price: Decimal) -> Decimal:
    return maximum_price * (Decimal("1") + PRICE_TOLERANCE_PERCENT / Decimal("100"))


def check_price_rejection(quoted_price: Decimal | None, maximum_price: Decimal | None) -> dict:
    """R01: reject if the price is more than 3% above the maximum."""
    if quoted_price is None or maximum_price is None:
        return build_validation_result(
            "R01", UNVERIFIED, "Unit price or PR maximum price is missing or unverified.",
            quoted_price, maximum_price, "unit_price",
        )
    threshold = rejection_threshold(maximum_price)
    difference = format_percent(percent_above(quoted_price, maximum_price))
    if quoted_price > threshold:
        return build_validation_result(
            "R01", REJECT,
            f"Unit price {quoted_price} is {difference} above the PR maximum {maximum_price} "
            f"(limit {threshold}).",
            quoted_price, f"<= {threshold}", "unit_price",
        )
    return build_validation_result(
        "R01", PASS, f"Unit price {quoted_price} is within 3% of the PR maximum {maximum_price}.",
        quoted_price, f"<= {threshold}", "unit_price",
    )


def check_price_review(quoted_price: Decimal | None, maximum_price: Decimal | None) -> dict:
    """H01: review if the price is above the maximum but by no more than 3%."""
    if quoted_price is None or maximum_price is None:
        return build_validation_result(
            "H01", UNVERIFIED, "Unit price or PR maximum price is missing or unverified.",
            quoted_price, maximum_price, "unit_price",
        )
    if quoted_price > rejection_threshold(maximum_price):
        return build_validation_result(
            "H01", NOT_APPLICABLE, "Price is more than 3% above the maximum; see R01.",
            quoted_price, f"<= {maximum_price}", "unit_price",
        )
    if quoted_price > maximum_price:
        difference = format_percent(percent_above(quoted_price, maximum_price))
        return build_validation_result(
            "H01", NEEDS_REVIEW,
            f"Unit price {quoted_price} is {difference} above the PR maximum {maximum_price}.",
            quoted_price, f"<= {maximum_price}", "unit_price",
        )
    return build_validation_result(
        "H01", PASS, f"Unit price {quoted_price} is not above the PR maximum {maximum_price}.",
        quoted_price, f"<= {maximum_price}", "unit_price",
    )
