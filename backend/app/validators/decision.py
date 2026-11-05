"""Turn all findings into one decision.

Priority: REJECT > NEEDS A PERSON TO CHECK > APPROVE.
APPROVE is only possible when every rule ran and every rule passed.
"""

from typing import Any

from app.validators.common import BLOCKING_REVIEW_STATUSES, REJECT
from app.validators.rule_catalog import RULES

APPROVE_DECISION = "APPROVE"
REJECT_DECISION = "REJECT"
REVIEW_DECISION = "NEEDS A PERSON TO CHECK"

# Every one of these rules must have a finding before we may approve.
REQUIRED_RULE_CODES = {rule.code for rule in RULES}


def make_decision(findings: list[dict[str, Any]], errors: list[str] | None = None) -> tuple[str, list[dict]]:
    """Return (decision, reasons). Reasons list the findings that caused the decision."""
    errors = errors or []
    reject_flags = [f for f in findings if f["status"] == REJECT]
    review_flags = [f for f in findings if f["status"] in BLOCKING_REVIEW_STATUSES]
    missing_rules = sorted(REQUIRED_RULE_CODES - {f["rule_code"] for f in findings})

    if reject_flags:
        # Keep the review flags too, so the reviewer sees every issue.
        return REJECT_DECISION, reject_flags + review_flags

    reasons = list(review_flags)
    reasons += [{"rule_code": "SYSTEM", "status": "ERROR", "message": error} for error in errors]
    if missing_rules:
        reasons.append({
            "rule_code": "SYSTEM", "status": "INCOMPLETE",
            "message": f"Evaluation is incomplete; these rules did not run: {', '.join(missing_rules)}.",
        })
    if reasons:
        return REVIEW_DECISION, reasons

    return APPROVE_DECISION, [{"rule_code": "ALL", "status": "PASS", "message": "All company rules passed."}]
