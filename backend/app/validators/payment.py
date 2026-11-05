"""R02 (advance payment) and H03 (payment terms)."""

from decimal import Decimal

from app.validators.common import NEEDS_REVIEW, PASS, REJECT, UNVERIFIED, build_validation_result
from app.validators.rule_catalog import MAX_ADVANCE_PAYMENT_PERCENT, PAYMENT_DAYS_MAX, PAYMENT_DAYS_MIN


def check_advance_payment(advance_percentage: Decimal | None) -> dict:
    """R02: reject if the advance payment is more than 20%. Exactly 20% passes."""
    expected = f"<= {MAX_ADVANCE_PAYMENT_PERCENT}%"
    if advance_percentage is None:
        return build_validation_result(
            "R02", UNVERIFIED, "Advance payment percentage is missing or unverified.",
            None, expected, "advance_payment_percentage",
        )
    if advance_percentage > MAX_ADVANCE_PAYMENT_PERCENT:
        return build_validation_result(
            "R02", REJECT, f"Advance payment is {advance_percentage}%, more than {MAX_ADVANCE_PAYMENT_PERCENT}%.",
            f"{advance_percentage}%", expected, "advance_payment_percentage",
        )
    return build_validation_result(
        "R02", PASS, f"Advance payment is {advance_percentage}%.",
        f"{advance_percentage}%", expected, "advance_payment_percentage",
    )


def check_payment_terms(days_min: int | None, days_max: int | None, counted_from: str | None) -> dict:
    """H03: review if payment terms are unclear or outside 30-60 days after delivery.

    Assumption: "within N days of delivery" means payment is due N days after delivery.
    """
    expected = f"{PAYMENT_DAYS_MIN}-{PAYMENT_DAYS_MAX} days after delivery"
    if days_min is None or days_max is None:
        return build_validation_result(
            "H03", UNVERIFIED, "Number of payment days is missing or unverified.",
            None, expected, "payment_terms",
        )
    actual = f"{days_min} days" if days_min == days_max else f"{days_min}-{days_max} days"
    if counted_from:
        actual += f" from {counted_from}"

    if days_min != days_max:
        return build_validation_result(
            "H03", NEEDS_REVIEW, f"Payment terms give a range ({actual}) instead of a fixed term, so they are unclear.",
            actual, expected, "payment_terms",
        )
    if counted_from is None or "deliver" not in counted_from.casefold():
        return build_validation_result(
            "H03", NEEDS_REVIEW, "Payment terms do not say the days are counted from delivery.",
            actual, expected, "payment_terms",
        )
    if not PAYMENT_DAYS_MIN <= days_min <= PAYMENT_DAYS_MAX:
        return build_validation_result(
            "H03", NEEDS_REVIEW, f"Payment is due {actual}, outside {expected}.",
            actual, expected, "payment_terms",
        )
    return build_validation_result("H03", PASS, f"Payment is due {actual}.", actual, expected, "payment_terms")
