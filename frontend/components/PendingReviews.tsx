"use client";

import Link from "next/link";
import { useApiData } from "@/hooks/useApiData";
import { api } from "@/services/api";
import { ReviewForm } from "@/components/ReviewForm";
import { Card, EmptyState, ErrorMessage, Loading, PageHeader } from "@/components/StateMessages";
import { DecisionBadge, StageBadge } from "@/components/StatusBadge";

export function PendingReviews() {
  const { data, error, loading, reload } = useApiData(api.pendingReviews);

  return (
    <>
      <PageHeader
        title="Human review"
        subtitle="Documents the system could not decide on its own. Your note is saved next to the automated decision; it does not replace it."
      />
      {loading && <Loading />}
      {error && <ErrorMessage message={error} onRetry={reload} />}
      {data && data.length === 0 && <EmptyState title="Nothing waiting for review.">Documents marked NEEDS A PERSON TO CHECK, or that failed, appear here.</EmptyState>}

      <div className="space-y-6">
        {data?.map((item) => (
          <Card
            key={item.document_id}
            title={item.supplier_name ?? item.filename}
            actions={
              <Link href={`/documents/${item.document_id}`} className="text-sm font-medium text-blue-600 hover:underline">
                Open details and evidence
              </Link>
            }
          >
            <div className="mb-3 flex flex-wrap items-center gap-3 text-sm text-slate-600">
              {item.processing_status === "FAILED" ? <StageBadge stage="FAILED" /> : <DecisionBadge decision={item.decision} />}
              <span>{item.filename}</span>
              {item.latest_review && <span>Last note by {item.latest_review.reviewer_name} ({item.latest_review.review_status})</span>}
            </div>
            <ul className="mb-4 list-disc space-y-1 pl-5 text-sm text-slate-700">
              {item.reasons.map((reason, index) => (
                <li key={index}>
                  {reason.rule_code && <span className="font-mono font-semibold">{reason.rule_code}: </span>}
                  {reason.message}
                </li>
              ))}
            </ul>
            <ReviewForm documentId={item.document_id} onSaved={reload} />
          </Card>
        ))}
      </div>
    </>
  );
}
