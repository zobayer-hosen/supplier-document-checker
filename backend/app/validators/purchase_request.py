"""Find the Purchase Request line that a supplier quotation is for.

Matching order:
1. Item code (for example "A") when the quotation shows a verified code.
2. Otherwise the exact item description.

Anything that does not match cleanly (item not found, a different
description, unit or currency) becomes an H08 finding for a person to check.
"""

from typing import Any

from app.schemas.purchase_request import PurchaseRequestItem
from app.utils.text import normalize_text
from app.validators.common import NEEDS_REVIEW, PASS, build_validation_result


def find_purchase_request_item(
    item_code: str | None, item_name: str | None, items: list[PurchaseRequestItem],
) -> PurchaseRequestItem | None:
    if item_code:
        for item in items:
            if item.item_code and normalize_text(item.item_code) == normalize_text(item_code):
                return item
    if item_name:
        for item in items:
            if normalize_text(item.item_name) == normalize_text(item_name):
                return item
    return None


def _same_text(first: str | None, second: str | None) -> bool:
    return first is None or second is None or normalize_text(first) == normalize_text(second)


def compare_with_purchase_request(
    facts: dict[str, Any], items: list[PurchaseRequestItem],
) -> tuple[PurchaseRequestItem | None, list[dict]]:
    """Return the matched PR item (or None) and the comparison findings."""
    item = find_purchase_request_item(facts.get("item_code"), facts.get("item_name"), items)
    if item is None:
        quoted = facts.get("item_code") or facts.get("item_name") or "unknown item"
        return None, [build_validation_result(
            "H08", NEEDS_REVIEW, f"The quoted item ({quoted}) could not be matched to a Purchase Request line.",
            quoted, [i.item_code or i.item_name for i in items], "item_name",
        )]

    findings = []
    checks = [
        ("item_name", "description", facts.get("item_name"), item.item_name),
        ("unit", "unit", facts.get("unit"), item.unit),
        ("currency", "currency", facts.get("currency"), item.currency),
        ("purchase_request_reference", "PR reference", facts.get("purchase_request_reference"), item.pr_number),
    ]
    for field, label, quoted, requested in checks:
        if not _same_text(quoted, requested):
            findings.append(build_validation_result(
                "H08", NEEDS_REVIEW, f"Quoted {label} '{quoted}' differs from the Purchase Request '{requested}'.",
                quoted, requested, field if field != "purchase_request_reference" else None,
            ))

    if not findings:
        findings.append(build_validation_result(
            "H08", PASS, f"Quotation matches Purchase Request item {item.item_code or item.item_name}.",
            facts.get("item_code") or facts.get("item_name"), item.item_code or item.item_name, "item_name",
        ))
    return item, findings
