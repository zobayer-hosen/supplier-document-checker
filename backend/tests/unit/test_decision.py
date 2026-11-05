from app.validators.common import NEEDS_REVIEW, PASS, REJECT, build_validation_result
from app.validators.decision import APPROVE_DECISION, REJECT_DECISION, REVIEW_DECISION, REQUIRED_RULE_CODES, make_decision


def all_rules_passing() -> list[dict]:
    return [build_validation_result(code, PASS, "ok") for code in sorted(REQUIRED_RULE_CODES)]


def test_approve_only_when_every_rule_passes():
    decision, _ = make_decision(all_rules_passing())
    assert decision == APPROVE_DECISION


def test_reject_wins_over_review_and_keeps_all_findings():
    findings = all_rules_passing() + [
        build_validation_result("R01", REJECT, "price too high"),
        build_validation_result("H02", NEEDS_REVIEW, "quantity differs"),
    ]
    decision, reasons = make_decision(findings)
    assert decision == REJECT_DECISION
    assert {reason["rule_code"] for reason in reasons} == {"R01", "H02"}


def test_review_finding_blocks_approval():
    decision, _ = make_decision(all_rules_passing() + [build_validation_result("H06", NEEDS_REVIEW, "bad total")])
    assert decision == REVIEW_DECISION


def test_incomplete_evaluation_is_never_approved():
    findings = [f for f in all_rules_passing() if f["rule_code"] != "R03"]
    decision, reasons = make_decision(findings)
    assert decision == REVIEW_DECISION
    assert "R03" in reasons[-1]["message"]


def test_processing_errors_block_approval():
    decision, _ = make_decision(all_rules_passing(), errors=["OCR failed on page 2"])
    assert decision == REVIEW_DECISION
