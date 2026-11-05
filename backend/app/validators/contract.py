"""R03 (late-delivery penalty), R04 (TIN/BIN) and H07 (quotation validity).

R03 and R04 reject when something is MISSING. Missing is a strong claim, so we
do not rely on the LLM alone: a value counts as missing only when the LLM
found nothing AND a plain keyword search of the document also finds nothing.
If the two disagree, a person checks it.
"""

from decimal import Decimal

from app.evidence.verifier import NOT_FOUND, VERIFIED
from app.utils.text import contains_phrase
from app.validators.common import (
    NEEDS_REVIEW, PASS, REJECT, UNVERIFIED, build_validation_result, period_in_days,
)
from app.validators.rule_catalog import MIN_LATE_PENALTY_PERCENT_PER_WEEK, MIN_QUOTATION_VALIDITY_DAYS

PENALTY_KEYWORDS = ("penalty", "liquidated damages", "late delivery", "delay")
TIN_KEYWORDS = ("tin", "e-tin", "taxpayer identification")
BIN_KEYWORDS = ("bin", "business identification")
ORDER_VALUE_WORDS = ("order value", "contract value", "value of the order", "po value")


def _mentions_any(document_text: str, keywords: tuple[str, ...]) -> bool:
    return any(contains_phrase(document_text, keyword) for keyword in keywords)


def check_late_penalty(
    penalty_status: str,
    percentage: Decimal | None,
    period: str | None,
    basis: str | None,
    document_text: str,
) -> dict:
    """R03: reject if there is no penalty clause, or the penalty is below 0.5% of order value per week."""
    expected = f">= {MIN_LATE_PENALTY_PERCENT_PER_WEEK}% of order value per week"

    if penalty_status == NOT_FOUND:
        if _mentions_any(document_text, PENALTY_KEYWORDS):
            return build_validation_result(
                "R03", UNVERIFIED,
                "No penalty clause was extracted, but the document mentions a penalty or delay. A person must check.",
                None, expected, "late_penalty_text",
            )
        return build_validation_result(
            "R03", REJECT, "The contract has no late-delivery penalty clause.", None, expected, "late_penalty_text",
        )
    if penalty_status != VERIFIED:
        return build_validation_result(
            "R03", UNVERIFIED, "The penalty clause could not be verified in the document.",
            None, expected, "late_penalty_text",
        )
    if percentage is None or period is None:
        return build_validation_result(
            "R03", UNVERIFIED, "A penalty clause exists, but its rate or period is unclear.",
            None, expected, "late_penalty_text",
        )
    if basis is None or not any(word in basis.casefold() for word in ORDER_VALUE_WORDS):
        return build_validation_result(
            "R03", UNVERIFIED,
            f"Penalty is {percentage}% per {period}, but it does not say it is a percentage of the order value.",
            f"{percentage}% per {period}", expected, "late_penalty_text",
        )

    # Assumption: a daily rate is converted to weekly (x7). Monthly rates are
    # not converted because weeks per month is not a fixed number.
    if period == "week":
        weekly_percentage = percentage
    elif period == "day":
        weekly_percentage = percentage * 7
    else:
        return build_validation_result(
            "R03", UNVERIFIED, f"Penalty is given per {period}; it cannot be compared to a weekly rate reliably.",
            f"{percentage}% per {period}", expected, "late_penalty_text",
        )

    actual = f"{weekly_percentage}% of {basis} per week"
    if weekly_percentage < MIN_LATE_PENALTY_PERCENT_PER_WEEK:
        return build_validation_result(
            "R03", REJECT, f"Late-delivery penalty is {actual}, below the minimum.", actual, expected, "late_penalty_text",
        )
    return build_validation_result("R03", PASS, f"Late-delivery penalty is {actual}.", actual, expected, "late_penalty_text")


def _identifier_state(status: str, document_text: str, keywords: tuple[str, ...]) -> str:
    """Return "present", "missing" or "unclear" for a TIN or BIN."""
    if status == VERIFIED:
        return "present"
    if status == NOT_FOUND and not _mentions_any(document_text, keywords):
        return "missing"
    return "unclear"


def check_supplier_tax_ids(
    tin: str | None, tin_status: str, bin_number: str | None, bin_status: str, document_text: str,
) -> dict:
    """R04: reject if the supplier's TIN or BIN is missing (both are required)."""
    tin_state = _identifier_state(tin_status, document_text, TIN_KEYWORDS)
    bin_state = _identifier_state(bin_status, document_text, BIN_KEYWORDS)
    actual = {"tin": tin, "bin": bin_number}
    expected = "Both TIN and BIN shown"

    missing = [name for name, state in (("TIN", tin_state), ("BIN", bin_state)) if state == "missing"]
    if missing:
        return build_validation_result(
            "R04", REJECT, f"Supplier {' and '.join(missing)} missing from the document.",
            actual, expected, "supplier_tin" if "TIN" in missing else "supplier_bin",
        )
    if tin_state == "present" and bin_state == "present":
        return build_validation_result("R04", PASS, f"Supplier TIN {tin} and BIN {bin_number} are shown.", actual, expected, "supplier_tin")
    return build_validation_result(
        "R04", UNVERIFIED, "Supplier TIN or BIN could not be verified.", actual, expected, "supplier_tin",
    )


def check_quotation_validity(validity_value: int | None, validity_unit: str | None) -> dict:
    """H07: review if the quotation is valid for less than 30 days. Exactly 30 passes."""
    expected = f">= {MIN_QUOTATION_VALIDITY_DAYS} days"
    validity_days = period_in_days(validity_value, validity_unit)
    if validity_days is None:
        return build_validation_result(
            "H07", UNVERIFIED, "Quotation validity is missing, unverified or not given in days/weeks.",
            None, expected, "validity_period_value",
        )
    actual = f"{validity_days} days"
    if validity_days < MIN_QUOTATION_VALIDITY_DAYS:
        return build_validation_result(
            "H07", NEEDS_REVIEW, f"Quotation is valid for only {validity_days} days.", actual, expected, "validity_period_value",
        )
    return build_validation_result(
        "H07", PASS, f"Quotation is valid for {validity_days} days.", actual, expected, "validity_period_value",
    )
