"""H08: send uncertain extractions to a person.

A finding is created when:
- a required value is missing,
- any important value could not be verified against the document text,
- the document gives conflicting values,
- a value was read with OCR (OCR can misread characters),
- the quotation has more than one item line (not supported automatically).
"""

from typing import Any

from app.evidence.verifier import CONFLICTING, NOT_FOUND, UNVERIFIED as EVIDENCE_UNVERIFIED, VERIFIED
from app.schemas.extraction import REQUIRED_FIELDS
from app.validators.common import NEEDS_REVIEW, build_validation_result


def check_uncertainty(evidence_records: list[dict[str, Any]], line_item_count: int | None) -> list[dict]:
    findings = []
    for record in evidence_records:
        field = record["field"]
        status = record["verification_status"]

        if status == CONFLICTING:
            message = f"'{field}' has conflicting values: {record['reason']}."
        elif status == EVIDENCE_UNVERIFIED:
            message = f"'{field}' = {record['value']} could not be verified: {record['reason']}."
        elif status == NOT_FOUND and field in REQUIRED_FIELDS:
            message = f"Required value '{field}' was not found in the document."
        elif status == VERIFIED and record.get("source") == "ocr":
            message = f"'{field}' was read with OCR and may contain reading mistakes."
        else:
            continue
        findings.append(build_validation_result("H08", NEEDS_REVIEW, message, record["value"], None, field))

    if line_item_count is not None and line_item_count > 1:
        findings.append(build_validation_result(
            "H08", NEEDS_REVIEW, f"The quotation has {line_item_count} item lines; only one-item quotations are checked automatically.",
            line_item_count, 1, None,
        ))
    return findings
