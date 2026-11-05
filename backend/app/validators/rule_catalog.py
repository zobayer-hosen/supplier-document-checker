"""The single list of company rules this system implements.

The thresholds live here as Python constants. The LLM never sees or changes
them. When a company-rules Markdown file is uploaded, `rules_loader.py`
checks that each rule below is really written in that file, using the
`markdown_keywords`, so we notice if the policy document has changed.
"""

from dataclasses import dataclass
from decimal import Decimal

# Thresholds (from company-rules.md)
PRICE_TOLERANCE_PERCENT = Decimal("3")
MAX_ADVANCE_PAYMENT_PERCENT = Decimal("20")
MIN_LATE_PENALTY_PERCENT_PER_WEEK = Decimal("0.5")
MAX_DELIVERY_DAYS = 45
REVIEW_DELIVERY_FROM_DAYS = 31
MAX_QUANTITY_DIFFERENCE_PERCENT = Decimal("5")
PAYMENT_DAYS_MIN = 30
PAYMENT_DAYS_MAX = 60
REQUIRED_VAT_PERCENT = Decimal("15")
MIN_QUOTATION_VALIDITY_DAYS = 30
AMOUNT_TOLERANCE = Decimal("0.01")  # allowed rounding difference in BDT


@dataclass(frozen=True)
class RuleDefinition:
    code: str
    category: str
    title: str
    section: str  # which Markdown section must contain it: "reject", "review" or "notes"
    markdown_keywords: tuple[str, ...]


RULES: list[RuleDefinition] = [
    RuleDefinition("R01", "price", "Unit price more than 3% above the PR maximum", "reject", ("unit price", "3%")),
    RuleDefinition("R02", "payment", "Advance payment more than 20%", "reject", ("advance", "20%")),
    RuleDefinition("R03", "contract", "Late-delivery penalty missing or below 0.5% per week", "reject", ("penalty",)),
    RuleDefinition("R04", "supplier", "Supplier TIN or BIN missing", "reject", ("tin", "bin")),
    RuleDefinition("R05", "delivery", "Delivery later than 45 days after the PO", "reject", ("delivery", "45 days")),
    RuleDefinition("H01", "price", "Unit price above the maximum by no more than 3%", "review", ("unit price", "3%")),
    RuleDefinition("H02", "quantity", "Quantity differs from the request by more than 5%", "review", ("quantity", "5%")),
    RuleDefinition("H03", "payment", "Payment terms unclear or outside 30-60 days after delivery", "review", ("payment", "30 to 60 days")),
    RuleDefinition("H04", "delivery", "Delivery promised in 31-45 days", "review", ("delivery", "31 to 45 days")),
    RuleDefinition("H05", "tax", "VAT not shown separately at 15%", "review", ("vat", "15%")),
    RuleDefinition("H06", "arithmetic", "Line total, subtotal, VAT or total does not add up", "review", ("total",)),
    RuleDefinition("H07", "contract", "Quotation valid for less than 30 days", "review", ("valid", "30 days")),
    RuleDefinition("H08", "uncertainty", "Important value missing, unverified or conflicting", "notes", ("not sure",)),
]

# The penalty threshold is written in the "Other notes" section.
PENALTY_NOTE_KEYWORDS = ("penalty", "0.5%", "week")

RULES_BY_CODE = {rule.code: rule for rule in RULES}


def rule_category(code: str) -> str:
    return RULES_BY_CODE[code].category
