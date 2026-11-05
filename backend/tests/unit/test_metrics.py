"""The accuracy calculator itself must be correct, or the report means nothing."""

from evaluation.metrics import DocumentResult, build_report, load_ground_truth, values_match


def perfect_result(filename: str, truth: dict) -> DocumentResult:
    return DocumentResult(
        filename=filename,
        processing_status="COMPLETED",
        decision=truth["expected_decision"],
        extracted_data=truth["fields"],
        evidence=[{"field_name": q["field"], "page_number": q["page"], "verification_status": "VERIFIED"} for q in truth["evidence"]],
        rule_statuses=truth["expected_rules"],
    )


def test_values_match_compares_numbers_by_value():
    assert values_match("472.00", "472")
    assert values_match(None, None)
    assert not values_match("0", None)
    assert values_match("Cotton twill fabric, 280 GSM", "cotton twill fabric, 280 gsm")


def test_perfect_results_score_100_percent():
    truth = load_ground_truth()
    report = build_report([perfect_result(name, item) for name, item in truth.items()])
    assert report.decisions_correct == report.documents == 10
    assert report.field_correct == report.field_total
    assert report.evidence_correct == report.evidence_total


def test_wrong_decision_and_field_are_counted():
    truth = load_ground_truth()
    result = perfect_result("supplier-pack-03.pdf", truth["supplier-pack-03.pdf"])
    result.decision = "APPROVE"
    result.extracted_data = {**result.extracted_data, "unit_price": "210.00"}
    report = build_report([result])
    assert report.decisions_correct == 0
    assert report.field_correct == report.field_total - 1
    assert "unit_price" in report.field_errors[0]
