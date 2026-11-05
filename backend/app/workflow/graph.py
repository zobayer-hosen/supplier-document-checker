"""The fixed LangGraph workflow for ONE supplier document.

    load_document -> extract_text -> [ocr_fallback] -> extract_information
    -> validate_schema (retry on bad JSON) -> verify_evidence
    -> compare_purchase_request -> validate_company_rules -> make_decision
    -> save_result

Every arrow is decided by plain Python below. The LLM never chooses the next
step or which rules run. Any fatal problem goes to `record_failure`.
"""

from langgraph.graph import END, START, StateGraph

from app.workflow import nodes
from app.workflow.nodes import WorkflowDependencies
from app.workflow.state import ProcessingStage, SupplierEvaluationState


def _failed(state: SupplierEvaluationState) -> bool:
    return state.get("processing_status") == ProcessingStage.FAILED


def _has_readable_text(state: SupplierEvaluationState) -> bool:
    return any(page["text"].strip() for page in state.get("pages", []))


def route_after_load(state: SupplierEvaluationState) -> str:
    return "record_failure" if _failed(state) else "extract_text"


def route_after_text(state: SupplierEvaluationState) -> str:
    if _failed(state):
        return "record_failure"
    if any(page["needs_ocr"] for page in state["pages"]):
        return "ocr_fallback"
    return "extract_information"


def route_after_ocr(state: SupplierEvaluationState) -> str:
    return "extract_information" if _has_readable_text(state) else "record_failure"


def route_after_extraction(state: SupplierEvaluationState) -> str:
    return "record_failure" if _failed(state) else "validate_schema"


def route_after_schema(state: SupplierEvaluationState) -> str:
    if _failed(state):
        return "record_failure"
    if state.get("schema_error"):
        return "extract_information"  # limited retry; validate_schema fails after the limit
    return "verify_evidence"


def build_evaluation_graph(deps: WorkflowDependencies):
    """Create and compile the workflow. Call `.invoke({"document_id": ...})` on the result."""
    graph = StateGraph(SupplierEvaluationState)

    def add(name: str, function) -> None:
        graph.add_node(name, lambda state: function(state, deps))

    add("load_document", nodes.load_document)
    add("extract_text", nodes.extract_text)
    add("ocr_fallback", nodes.ocr_fallback)
    add("extract_information", nodes.extract_information)
    add("validate_schema", nodes.validate_schema)
    add("verify_evidence", nodes.verify_evidence)
    add("compare_purchase_request", nodes.compare_purchase_request)
    add("validate_company_rules", nodes.validate_company_rules)
    add("make_decision", nodes.make_decision)
    add("save_result", nodes.save_result)
    add("record_failure", nodes.record_failure)

    graph.add_edge(START, "load_document")
    graph.add_conditional_edges("load_document", route_after_load, ["extract_text", "record_failure"])
    graph.add_conditional_edges("extract_text", route_after_text, ["ocr_fallback", "extract_information", "record_failure"])
    graph.add_conditional_edges("ocr_fallback", route_after_ocr, ["extract_information", "record_failure"])
    graph.add_conditional_edges("extract_information", route_after_extraction, ["validate_schema", "record_failure"])
    graph.add_conditional_edges("validate_schema", route_after_schema, ["extract_information", "verify_evidence", "record_failure"])
    graph.add_edge("verify_evidence", "compare_purchase_request")
    graph.add_edge("compare_purchase_request", "validate_company_rules")
    graph.add_edge("validate_company_rules", "make_decision")
    graph.add_edge("make_decision", "save_result")
    graph.add_edge("save_result", END)
    graph.add_edge("record_failure", END)
    return graph.compile()
