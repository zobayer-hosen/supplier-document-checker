import type { Decision, FindingStatus, ProcessingStage } from "@/types/api";

const DECISION_STYLES: Record<Decision, string> = {
  APPROVE: "bg-emerald-100 text-emerald-800 ring-emerald-300",
  REJECT: "bg-red-100 text-red-800 ring-red-300",
  "NEEDS A PERSON TO CHECK": "bg-amber-100 text-amber-900 ring-amber-300",
};

const FINDING_STYLES: Record<FindingStatus, string> = {
  PASS: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  REJECT: "bg-red-50 text-red-700 ring-red-200",
  NEEDS_REVIEW: "bg-amber-50 text-amber-800 ring-amber-200",
  UNVERIFIED: "bg-orange-50 text-orange-800 ring-orange-200",
  NOT_APPLICABLE: "bg-slate-50 text-slate-500 ring-slate-200",
};

export const STAGE_LABELS: Record<ProcessingStage, string> = {
  UPLOADED: "Uploaded",
  EXTRACTING_TEXT: "Extracting text",
  EXTRACTING_INFORMATION: "Extracting information",
  VALIDATING_DATA: "Validating data",
  CHECKING_EVIDENCE: "Checking evidence",
  COMPARING_PURCHASE_REQUEST: "Comparing purchase request",
  APPLYING_RULES: "Applying rules",
  COMPLETED: "Completed",
  FAILED: "Failed",
};

const BASE = "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset whitespace-nowrap";

export function DecisionBadge({ decision }: { decision: Decision | null }) {
  if (!decision) return <span className={`${BASE} bg-slate-100 text-slate-500 ring-slate-200`}>No decision</span>;
  return <span className={`${BASE} ${DECISION_STYLES[decision]}`}>{decision}</span>;
}

export function FindingBadge({ status }: { status: FindingStatus }) {
  return <span className={`${BASE} ${FINDING_STYLES[status]}`}>{status.replace("_", " ")}</span>;
}

export function StageBadge({ stage }: { stage: ProcessingStage }) {
  const style =
    stage === "COMPLETED"
      ? "bg-emerald-50 text-emerald-700 ring-emerald-200"
      : stage === "FAILED"
        ? "bg-red-50 text-red-700 ring-red-200"
        : stage === "UPLOADED"
          ? "bg-slate-100 text-slate-600 ring-slate-200"
          : "bg-blue-50 text-blue-700 ring-blue-200 animate-pulse";
  return <span className={`${BASE} ${style}`}>{STAGE_LABELS[stage]}</span>;
}
