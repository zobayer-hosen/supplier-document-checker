"""Compare real evaluation results with the manually checked ground truth."""

import json
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from app.utils.text import normalize_text

GROUND_TRUTH_PATH = Path(__file__).resolve().parent / "ground_truth.json"

# Fields compared for extraction accuracy. Free-text fields (payment_terms,
# late_penalty_text) are left out because many wordings are equally correct;
# their meaning is covered by the numeric fields next to them.
COMPARED_FIELDS = [
    "supplier_name", "supplier_tin", "supplier_bin", "item_code", "item_name", "unit",
    "quantity", "unit_price", "line_total", "currency", "prices_include_vat",
    "subtotal", "vat_percentage", "vat_amount", "total_amount",
    "advance_payment_percentage", "payment_days_min", "payment_days_max",
    "delivery_period_value", "delivery_period_unit",
    "late_penalty_percentage", "late_penalty_period",
    "validity_period_value", "validity_period_unit",
]


@dataclass
class DocumentResult:
    """What the system produced for one document (read from the database)."""

    filename: str
    processing_status: str
    decision: str | None
    extracted_data: dict[str, Any]
    evidence: list[dict[str, Any]]  # {field_name, page_number, verification_status}
    rule_statuses: dict[str, str]


@dataclass
class Report:
    rows: list[dict[str, Any]] = field(default_factory=list)
    field_correct: int = 0
    field_total: int = 0
    evidence_correct: int = 0
    evidence_total: int = 0
    rule_correct: int = 0
    rule_total: int = 0
    decisions_correct: int = 0
    documents: int = 0
    completed: int = 0
    escalated: int = 0
    rules_seen: set[str] = field(default_factory=set)
    field_errors: list[str] = field(default_factory=list)


def load_ground_truth() -> dict[str, Any]:
    return json.loads(GROUND_TRUTH_PATH.read_text(encoding="utf-8"))["documents"]


def values_match(expected: Any, actual: Any) -> bool:
    if expected is None or actual is None:
        return expected is None and actual is None
    if isinstance(expected, bool) or isinstance(actual, bool):
        return expected == actual
    try:
        return Decimal(str(expected)) == Decimal(str(actual))
    except InvalidOperation:
        return normalize_text(str(expected)) == normalize_text(str(actual))


def build_report(results: list[DocumentResult]) -> Report:
    truth_by_file = load_ground_truth()
    report = Report()

    for result in results:
        truth = truth_by_file.get(result.filename)
        if truth is None:
            continue
        report.documents += 1
        report.completed += result.processing_status == "COMPLETED"
        report.escalated += result.decision == "NEEDS A PERSON TO CHECK" or result.processing_status == "FAILED"

        fields_ok = 0
        for name in COMPARED_FIELDS:
            ok = values_match(truth["fields"].get(name), result.extracted_data.get(name))
            fields_ok += ok
            if not ok:
                report.field_errors.append(
                    f"{result.filename}: {name} expected {truth['fields'].get(name)!r}, got {result.extracted_data.get(name)!r}"
                )
        report.field_correct += fields_ok
        report.field_total += len(COMPARED_FIELDS)

        evidence_by_field = {e["field_name"]: e for e in result.evidence}
        evidence_ok = 0
        for quote in truth["evidence"]:
            record = evidence_by_field.get(quote["field"])
            evidence_ok += bool(record and record["verification_status"] == "VERIFIED" and record["page_number"] == quote["page"])
        report.evidence_correct += evidence_ok
        report.evidence_total += len(truth["evidence"])

        rules_ok = sum(result.rule_statuses.get(code) == status for code, status in truth["expected_rules"].items())
        report.rule_correct += rules_ok
        report.rule_total += len(truth["expected_rules"])
        report.rules_seen |= set(result.rule_statuses)

        decision_ok = result.decision == truth["expected_decision"]
        report.decisions_correct += decision_ok
        report.rows.append({
            "filename": result.filename,
            "expected": truth["expected_decision"],
            "actual": result.decision or result.processing_status,
            "correct": decision_ok,
            "fields": f"{fields_ok}/{len(COMPARED_FIELDS)}",
            "evidence": f"{evidence_ok}/{len(truth['evidence'])}",
            "rules": f"{rules_ok}/{len(truth['expected_rules'])}",
        })
    return report


def percent(part: int, whole: int) -> str:
    return f"{part / whole * 100:.1f}%" if whole else "n/a"


def render_markdown(report: Report, model_name: str, batch_id: str, run_date: str) -> str:
    lines = [
        "# Evaluation Report",
        "",
        f"Measured on {run_date} with model `{model_name}` (batch `{batch_id}`).",
        "All numbers below were measured by `python -m scripts.evaluate_samples` against",
        "`backend/evaluation/ground_truth.json`, which was checked by hand from the PDFs.",
        "",
        "## Summary",
        "",
        "| Metric | Result |",
        "|---|---|",
        f"| Final decision accuracy | {report.decisions_correct}/{report.documents} ({percent(report.decisions_correct, report.documents)}) |",
        f"| Field extraction accuracy | {report.field_correct}/{report.field_total} ({percent(report.field_correct, report.field_total)}) |",
        f"| Evidence accuracy (verified, correct page) | {report.evidence_correct}/{report.evidence_total} ({percent(report.evidence_correct, report.evidence_total)}) |",
        f"| Rule outcome accuracy | {report.rule_correct}/{report.rule_total} ({percent(report.rule_correct, report.rule_total)}) |",
        f"| Rule coverage (rule codes executed) | {len(report.rules_seen)}/13 ({', '.join(sorted(report.rules_seen))}) |",
        f"| Processing success rate | {report.completed}/{report.documents} ({percent(report.completed, report.documents)}) |",
        f"| Documents escalated to a person | {report.escalated} |",
        "",
        "## Per document",
        "",
        "| Document | Expected | Actual | Correct | Fields | Evidence | Rules |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in report.rows:
        mark = "yes" if row["correct"] else "**no**"
        lines.append(
            f"| {row['filename']} | {row['expected']} | {row['actual']} | {mark} | {row['fields']} | {row['evidence']} | {row['rules']} |"
        )
    lines += ["", "## Field differences", ""]
    lines += [f"- {error}" for error in report.field_errors] or ["None."]
    return "\n".join(lines) + "\n"
