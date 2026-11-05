"""R05 and H04: promised delivery time after the purchase order.

    more than 45 days -> REJECT (R05)
    31 to 45 days     -> REVIEW (H04)
    30 days or less   -> PASS
"""

from app.validators.common import NOT_APPLICABLE, NEEDS_REVIEW, PASS, REJECT, UNVERIFIED, build_validation_result
from app.validators.rule_catalog import MAX_DELIVERY_DAYS, REVIEW_DELIVERY_FROM_DAYS


def check_delivery_rejection(delivery_days: int | None) -> dict:
    """R05: reject if delivery is later than 45 days after the PO."""
    expected = f"<= {MAX_DELIVERY_DAYS} days"
    if delivery_days is None:
        return build_validation_result(
            "R05", UNVERIFIED, "Delivery period is missing, unverified or not given in days/weeks.",
            None, expected, "delivery_period_value",
        )
    if delivery_days > MAX_DELIVERY_DAYS:
        return build_validation_result(
            "R05", REJECT, f"Delivery is promised in {delivery_days} days, later than {MAX_DELIVERY_DAYS} days.",
            f"{delivery_days} days", expected, "delivery_period_value",
        )
    return build_validation_result(
        "R05", PASS, f"Delivery is promised in {delivery_days} days.",
        f"{delivery_days} days", expected, "delivery_period_value",
    )


def check_delivery_review(delivery_days: int | None) -> dict:
    """H04: review if delivery is promised in 31-45 days."""
    expected = f"<= {REVIEW_DELIVERY_FROM_DAYS - 1} days"
    if delivery_days is None:
        return build_validation_result(
            "H04", UNVERIFIED, "Delivery period is missing, unverified or not given in days/weeks.",
            None, expected, "delivery_period_value",
        )
    actual = f"{delivery_days} days"
    if delivery_days > MAX_DELIVERY_DAYS:
        return build_validation_result(
            "H04", NOT_APPLICABLE, "Delivery is later than 45 days; see R05.", actual, expected, "delivery_period_value",
        )
    if delivery_days >= REVIEW_DELIVERY_FROM_DAYS:
        return build_validation_result(
            "H04", NEEDS_REVIEW, f"Delivery is promised in {delivery_days} days (31-45 days needs a person).",
            actual, expected, "delivery_period_value",
        )
    return build_validation_result(
        "H04", PASS, f"Delivery is promised in {delivery_days} days.", actual, expected, "delivery_period_value",
    )
