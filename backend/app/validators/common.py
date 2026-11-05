"""The one result shape that every rule returns."""

from decimal import Decimal
from typing import Any

from app.validators.rule_catalog import rule_category

# Finding statuses
PASS = "PASS"
REJECT = "REJECT"
NEEDS_REVIEW = "NEEDS_REVIEW"
UNVERIFIED = "UNVERIFIED"  # the rule could not be checked (value missing or unverified)
NOT_APPLICABLE = "NOT_APPLICABLE"  # another rule already covers this case

BLOCKING_REVIEW_STATUSES = {NEEDS_REVIEW, UNVERIFIED}


def build_validation_result(
    rule_code: str,
    status: str,
    message: str,
    actual_value: Any = None,
    expected_value: Any = None,
    evidence_field: str | None = None,
) -> dict[str, Any]:
    """Create a finding. `evidence_field` links the finding to the quote that supports it."""
    return {
        "rule_code": rule_code,
        "rule_category": rule_category(rule_code),
        "status": status,
        "message": message,
        "actual_value": actual_value,
        "expected_value": expected_value,
        "evidence_field": evidence_field,
    }


def percent_above(value: Decimal, reference: Decimal) -> Decimal:
    """How many percent `value` is above `reference` (negative when below)."""
    return (value - reference) / reference * Decimal("100")


def period_in_days(value: int | None, unit: str | None) -> int | None:
    """Convert a period to days. Months are not converted (28-31 days is ambiguous)."""
    if value is None or unit is None:
        return None
    if unit == "days":
        return value
    if unit == "weeks":
        return value * 7
    return None


def format_percent(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01'))}%"
