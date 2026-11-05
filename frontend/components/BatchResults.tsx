"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useState } from "react";
import { useApiData } from "@/hooks/useApiData";
import { api } from "@/services/api";
import { Card, EmptyState, ErrorMessage, Loading, PageHeader } from "@/components/StateMessages";
import { DecisionBadge, STAGE_LABELS, StageBadge } from "@/components/StatusBadge";
import type { Decision, ProcessingStage } from "@/types/api";

const DECISIONS: Decision[] = ["APPROVE", "REJECT", "NEEDS A PERSON TO CHECK"];
const POLL_MS = 2000;

export function BatchResults() {
  const { batchId } = useParams<{ batchId: string }>();
  const [decisionFilter, setDecisionFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [startError, setStartError] = useState<string | null>(null);

  // useCallback keeps the same function between renders, so the hook does not reload in a loop.
  const load = useCallback(
    () => Promise.all([api.getBatch(batchId), api.getResults(batchId)]).then(([batch, results]) => ({ batch, results })),
    [batchId],
  );
  const { data, error, loading, reload } = useApiData(load, {
    pollEveryMs: POLL_MS,
    pollWhile: (latest) => latest.batch.status === "PROCESSING",
  });
  const isRunning = data?.batch.status === "PROCESSING";

  async function startEvaluation() {
    setStartError(null);
    try {
      await api.processBatch(batchId);
      reload();
    } catch (reason) {
      setStartError((reason as Error).message);
    }
  }

  if (loading) return <Loading label="Loading batch..." />;
  if (error && !data) return <ErrorMessage message={error} onRetry={reload} />;
  if (!data) return null;

  const { batch, results } = data;
  const finished = batch.documents.filter((d) => d.processing_status === "COMPLETED" || d.processing_status === "FAILED").length;
  const rows = results.filter(
    (row) => (!decisionFilter || row.decision === decisionFilter) && (!statusFilter || row.processing_status === statusFilter),
  );

  return (
    <>
      <PageHeader
        title={batch.name}
        subtitle={`Batch status: ${batch.status} · ${batch.total_documents} document(s) · PR: ${batch.purchase_request_filename ?? "-"} · Rules: ${batch.rules_filename ?? "-"}`}
        actions={
          batch.status === "READY" && (
            <button onClick={startEvaluation} className="rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700">
              Start evaluation
            </button>
          )
        }
      />
      {startError && <div className="mb-4"><ErrorMessage message={startError} /></div>}
      {batch.error_message && <div className="mb-4"><ErrorMessage message={batch.error_message} /></div>}

      <div className="space-y-6">
        {(isRunning || batch.status === "READY" || batch.status === "CREATED") && (
          <Card title={`Processing progress (${finished}/${batch.documents.length} finished)`}>
            <div className="mb-4 h-2 w-full overflow-hidden rounded-full bg-slate-100">
              <div
                className="h-full bg-blue-600 transition-all"
                style={{ width: `${batch.documents.length ? (finished / batch.documents.length) * 100 : 0}%` }}
              />
            </div>
            <ul className="divide-y divide-slate-100">
              {batch.documents.map((document) => (
                <li key={document.id} className="flex items-center justify-between py-2 text-sm">
                  <span className="text-slate-700">{document.filename}</span>
                  <StageBadge stage={document.processing_status} />
                </li>
              ))}
            </ul>
          </Card>
        )}

        <Card
          title="Supplier results"
          actions={
            <div className="flex flex-wrap gap-2 text-sm">
              <select value={decisionFilter} onChange={(e) => setDecisionFilter(e.target.value)} className="rounded-md border border-slate-300 px-2 py-1">
                <option value="">All decisions</option>
                {DECISIONS.map((d) => <option key={d} value={d}>{d}</option>)}
              </select>
              <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="rounded-md border border-slate-300 px-2 py-1">
                <option value="">All statuses</option>
                {(Object.keys(STAGE_LABELS) as ProcessingStage[]).map((s) => <option key={s} value={s}>{STAGE_LABELS[s]}</option>)}
              </select>
            </div>
          }
        >
          {rows.length === 0 ? (
            <EmptyState title={results.length === 0 ? "No documents in this batch yet." : "No documents match these filters."} />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-slate-200 text-xs uppercase text-slate-500">
                  <tr>
                    <th className="py-2 pr-4">Supplier</th>
                    <th className="py-2 pr-4">File</th>
                    <th className="py-2 pr-4">Item</th>
                    <th className="py-2 pr-4 text-right">Quantity</th>
                    <th className="py-2 pr-4 text-right">Unit price</th>
                    <th className="py-2 pr-4">Decision</th>
                    <th className="py-2 pr-4 text-right">Findings</th>
                    <th className="py-2" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {rows.map((row) => (
                    <tr key={row.document_id} className="hover:bg-slate-50">
                      <td className="py-2 pr-4 font-medium text-slate-900">{row.supplier_name ?? "-"}</td>
                      <td className="py-2 pr-4 text-slate-600">{row.filename}</td>
                      <td className="py-2 pr-4 text-slate-600">{row.item ?? "-"}</td>
                      <td className="py-2 pr-4 text-right tabular-nums">{row.quantity ?? "-"}</td>
                      <td className="py-2 pr-4 text-right tabular-nums">{row.unit_price ?? "-"}</td>
                      <td className="py-2 pr-4">
                        {row.processing_status === "COMPLETED" ? <DecisionBadge decision={row.decision} /> : <StageBadge stage={row.processing_status} />}
                      </td>
                      <td className="py-2 pr-4 text-right tabular-nums">{row.findings_count}</td>
                      <td className="py-2 text-right">
                        <Link href={`/documents/${row.document_id}`} className="font-medium text-blue-600 hover:underline">
                          Details
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    </>
  );
}
