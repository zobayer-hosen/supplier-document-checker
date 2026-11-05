"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback } from "react";
import { useApiData } from "@/hooks/useApiData";
import { api } from "@/services/api";
import { ReviewForm } from "@/components/ReviewForm";
import { Card, ErrorMessage, Loading, PageHeader } from "@/components/StateMessages";
import { DecisionBadge, FindingBadge, StageBadge } from "@/components/StatusBadge";
import type { Evidence } from "@/types/api";

const FIELD_GROUPS: { title: string; fields: [string, string][] }[] = [
  {
    title: "Supplier details",
    fields: [
      ["supplier_name", "Supplier"], ["supplier_tin", "TIN"], ["supplier_bin", "BIN"],
      ["quotation_number", "Quotation no."], ["quotation_date", "Quotation date"], ["purchase_request_reference", "PR reference"],
    ],
  },
  {
    title: "Quotation values",
    fields: [
      ["item_code", "Item"], ["item_name", "Description"], ["quantity", "Quantity"], ["unit", "Unit"],
      ["unit_price", "Unit price"], ["line_total", "Line total"], ["subtotal", "Subtotal"],
      ["vat_percentage", "VAT %"], ["vat_amount", "VAT amount"], ["total_amount", "Total"],
      ["currency", "Currency"], ["prices_include_vat", "Prices include VAT"],
    ],
  },
  {
    title: "Contract terms",
    fields: [
      ["advance_payment_percentage", "Advance payment %"], ["payment_terms", "Payment terms"],
      ["delivery_period_value", "Delivery period"], ["delivery_period_unit", "Delivery unit"],
      ["late_penalty_text", "Late-delivery penalty"], ["validity_period_value", "Validity"], ["validity_period_unit", "Validity unit"],
    ],
  },
];

function show(value: unknown): string {
  if (value === null || value === undefined || value === "") return "Not found";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function EvidenceQuote({ evidence, documentId }: { evidence: Evidence | null; documentId: string }) {
  if (!evidence?.exact_text) return <span className="text-xs text-slate-400">No quote</span>;
  return (
    <div className="space-y-1">
      <blockquote className="border-l-2 border-slate-300 pl-2 text-xs italic text-slate-700">&ldquo;{evidence.exact_text}&rdquo;</blockquote>
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <a href={api.documentFileUrl(documentId, evidence.page_number)} target="_blank" rel="noreferrer" className="text-blue-600 hover:underline">
          Page {evidence.page_number}
        </a>
        <span className={evidence.verification_status === "VERIFIED" ? "text-emerald-700" : "text-orange-700"}>
          {evidence.verification_status}
        </span>
        {evidence.text_source === "ocr" && <span className="text-orange-700">(OCR)</span>}
      </div>
    </div>
  );
}

export function DocumentDetails() {
  const { documentId } = useParams<{ documentId: string }>();
  const load = useCallback(
    () =>
      Promise.all([api.getDocument(documentId), api.getValidations(documentId), api.getEvidence(documentId), api.getReviews(documentId)])
        .then(([document, validations, evidence, reviews]) => ({ document, validations, evidence, reviews })),
    [documentId],
  );
  const { data, error, loading, reload } = useApiData(load);

  if (loading) return <Loading label="Loading supplier details..." />;
  if (error && !data) return <ErrorMessage message={error} onRetry={reload} />;
  if (!data) return null;

  const { document, validations, evidence, reviews } = data;
  const evidenceByField = Object.fromEntries(evidence.map((item) => [item.field_name, item]));
  const extracted = document.extracted_data ?? {};
  const pr = document.purchase_request_item;

  return (
    <>
      <Link href={`/results/${document.batch_id}`} className="text-sm text-blue-600 hover:underline">
        &larr; Back to batch results
      </Link>
      <PageHeader
        title={document.supplier_name ?? document.filename}
        subtitle={`${document.filename} · ${document.page_count ?? "?"} page(s) · extracted with ${document.model_name ?? "-"}`}
        actions={
          <a href={api.documentFileUrl(document.id)} target="_blank" rel="noreferrer" className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium hover:bg-slate-50">
            Open original PDF
          </a>
        }
      />

      <div className="space-y-6">
        <Card title="Automated decision">
          <div className="flex flex-wrap items-center gap-3">
            {document.processing_status === "COMPLETED" ? <DecisionBadge decision={document.decision} /> : <StageBadge stage={document.processing_status} />}
            {document.has_completed_review && <span className="text-sm text-slate-600">A person has reviewed this document.</span>}
          </div>
          {document.error_message && <p className="mt-3 text-sm text-red-700">{document.error_message}</p>}
          {document.decision_reasons.length > 0 && (
            <ul className="mt-4 space-y-2">
              {document.decision_reasons.map((reason, index) => (
                <li key={index} className="flex gap-3 text-sm">
                  <span className="w-14 shrink-0 font-mono font-semibold text-slate-700">{reason.rule_code}</span>
                  <span className="text-slate-700">{reason.message}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title="Purchase Request comparison">
          {pr ? (
            <div className="grid gap-4 text-sm sm:grid-cols-3">
              <div><p className="text-slate-500">PR item</p><p className="font-medium">{pr.item_code} - {pr.item_name}</p></div>
              <div><p className="text-slate-500">Requested quantity</p><p className="font-medium">{Number(pr.requested_quantity)} {pr.unit} (quoted: {show(extracted.quantity)})</p></div>
              <div><p className="text-slate-500">Maximum unit price</p><p className="font-medium">{Number(pr.max_unit_price).toFixed(2)} {pr.currency} (quoted: {show(extracted.unit_price)})</p></div>
            </div>
          ) : (
            <p className="text-sm text-amber-800">This quotation could not be matched to a Purchase Request item.</p>
          )}
        </Card>

        <Card title="Rule-by-rule outcomes">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-200 text-xs uppercase text-slate-500">
                <tr><th className="py-2 pr-3">Rule</th><th className="py-2 pr-3">Result</th><th className="py-2 pr-3">Finding</th><th className="py-2">Evidence</th></tr>
              </thead>
              <tbody className="divide-y divide-slate-100 align-top">
                {validations.map((finding) => (
                  <tr key={finding.id}>
                    <td className="py-3 pr-3">
                      <p className="font-mono font-semibold">{finding.rule_code}</p>
                      <p className="max-w-48 text-xs text-slate-500" title={finding.rule_text ?? ""}>{finding.rule_title}</p>
                    </td>
                    <td className="py-3 pr-3"><FindingBadge status={finding.status} /></td>
                    <td className="py-3 pr-3 text-slate-700">{finding.message}</td>
                    <td className="w-72 py-3"><EvidenceQuote evidence={finding.evidence} documentId={document.id} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        {FIELD_GROUPS.map((group) => (
          <Card key={group.title} title={group.title}>
            <dl className="grid gap-x-6 gap-y-4 sm:grid-cols-2">
              {group.fields.map(([field, label]) => (
                <div key={field}>
                  <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</dt>
                  <dd className="mt-0.5 text-sm font-medium text-slate-900">{show(extracted[field])}</dd>
                  {evidenceByField[field] && evidenceByField[field].verification_status !== "NOT_FOUND" && (
                    <div className="mt-1"><EvidenceQuote evidence={evidenceByField[field]} documentId={document.id} /></div>
                  )}
                </div>
              ))}
            </dl>
          </Card>
        ))}

        <Card title="Human review">
          {reviews.length > 0 && (
            <ul className="mb-5 space-y-3">
              {reviews.map((review) => (
                <li key={review.id} className="rounded-md bg-slate-50 p-3 text-sm">
                  <p className="font-medium text-slate-900">
                    {review.reviewer_name} · {review.review_status}
                    {review.reviewer_decision && ` · suggests ${review.reviewer_decision}`}
                  </p>
                  <p className="mt-1 text-slate-700">{review.review_note}</p>
                  <p className="mt-1 text-xs text-slate-500">{new Date(review.created_at).toLocaleString()}</p>
                </li>
              ))}
            </ul>
          )}
          {document.processing_status === "COMPLETED" || document.processing_status === "FAILED" ? (
            <ReviewForm documentId={document.id} onSaved={reload} />
          ) : (
            <p className="text-sm text-slate-500">Reviews can be added after the evaluation finishes.</p>
          )}
        </Card>
      </div>
    </>
  );
}
