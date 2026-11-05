// TypeScript copies of the backend response shapes (backend/app/schemas/*.py).

export type Decision = "APPROVE" | "REJECT" | "NEEDS A PERSON TO CHECK";

export type ProcessingStage =
  | "UPLOADED"
  | "EXTRACTING_TEXT"
  | "EXTRACTING_INFORMATION"
  | "VALIDATING_DATA"
  | "CHECKING_EVIDENCE"
  | "COMPARING_PURCHASE_REQUEST"
  | "APPLYING_RULES"
  | "COMPLETED"
  | "FAILED";

export type BatchStatus = "CREATED" | "READY" | "PROCESSING" | "COMPLETED" | "FAILED";

export interface BatchSummary {
  id: string;
  name: string;
  status: BatchStatus;
  total_documents: number;
  created_at: string;
  completed_at: string | null;
}

export interface DocumentStatus {
  id: string;
  filename: string;
  supplier_name: string | null;
  processing_status: ProcessingStage;
  error_message: string | null;
}

export interface BatchDetail extends BatchSummary {
  purchase_request_filename: string | null;
  rules_filename: string | null;
  purchase_request_item_count: number;
  error_message: string | null;
  documents: DocumentStatus[];
}

export interface UploadResult {
  batch: BatchDetail;
  accepted_files: { filename: string; kind: string; detail: string }[];
}

export interface DashboardSummary {
  total_batches: number;
  total_documents: number;
  approved: number;
  rejected: number;
  needs_review: number;
  failed: number;
  in_progress: number;
  recent_batches: BatchSummary[];
}

export interface SupplierResultRow {
  document_id: string;
  filename: string;
  supplier_name: string | null;
  item: string | null;
  quantity: string | null;
  unit_price: string | null;
  processing_status: ProcessingStage;
  decision: Decision | null;
  findings_count: number;
  error_message: string | null;
}

export interface Evidence {
  id: string;
  field_name: string;
  extracted_value: unknown;
  exact_text: string | null;
  page_number: number | null;
  text_source: string | null;
  verification_status: "VERIFIED" | "UNVERIFIED" | "NOT_FOUND" | "CONFLICTING";
  verification_note: string | null;
}

export type FindingStatus = "PASS" | "REJECT" | "NEEDS_REVIEW" | "UNVERIFIED" | "NOT_APPLICABLE";

export interface Validation {
  id: string;
  rule_code: string;
  rule_category: string;
  rule_title: string;
  rule_text: string | null;
  status: FindingStatus;
  expected_value: unknown;
  actual_value: unknown;
  message: string;
  evidence: Evidence | null;
}

export interface DecisionReason {
  rule_code: string;
  status: string;
  message: string;
}

export interface DocumentDetail {
  id: string;
  batch_id: string;
  filename: string;
  supplier_name: string | null;
  page_count: number | null;
  processing_status: ProcessingStage;
  error_message: string | null;
  model_name: string | null;
  extracted_data: Record<string, unknown> | null;
  purchase_request_item: {
    pr_number: string | null;
    item_code: string | null;
    item_name: string;
    unit: string | null;
    requested_quantity: string;
    max_unit_price: string;
    currency: string | null;
  } | null;
  decision: Decision | null;
  decision_reasons: DecisionReason[];
  has_completed_review: boolean;
}

export interface Review {
  id: string;
  document_id: string;
  reviewer_name: string;
  review_status: "IN_PROGRESS" | "COMPLETED";
  reviewer_decision: "APPROVE" | "REJECT" | null;
  review_note: string;
  created_at: string;
  reviewed_at: string | null;
}

export interface ReviewCreate {
  reviewer_name: string;
  review_status: "IN_PROGRESS" | "COMPLETED";
  reviewer_decision: "APPROVE" | "REJECT" | null;
  review_note: string;
}

export interface PendingReview {
  document_id: string;
  batch_id: string;
  filename: string;
  supplier_name: string | null;
  processing_status: ProcessingStage;
  decision: Decision | null;
  reasons: DecisionReason[];
  latest_review: Review | null;
}

export interface ApiErrorBody {
  error: { code: string; message: string; details: { filename?: string; field?: string; message: string }[] };
}
