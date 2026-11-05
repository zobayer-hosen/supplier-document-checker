"use client";

import Link from "next/link";
import { useApiData } from "@/hooks/useApiData";
import { api } from "@/services/api";
import { Card, EmptyState, ErrorMessage, Loading, PageHeader } from "@/components/StateMessages";

function StatCard({ label, value, tone }: { label: string; value: number; tone: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`mt-1 text-3xl font-bold ${tone}`}>{value}</p>
    </div>
  );
}

export function DashboardView() {
  const { data, error, loading, reload } = useApiData(api.getDashboard);

  return (
    <>
      <PageHeader
        title="Dashboard"
        subtitle="Overview of all supplier document evaluations."
        actions={
          <Link href="/upload" className="rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700">
            New evaluation
          </Link>
        }
      />

      {loading && <Loading />}
      {error && <ErrorMessage message={error} onRetry={reload} />}

      {data && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-6">
            <StatCard label="Batches" value={data.total_batches} tone="text-slate-900" />
            <StatCard label="Documents" value={data.total_documents} tone="text-slate-900" />
            <StatCard label="Approved" value={data.approved} tone="text-emerald-600" />
            <StatCard label="Rejected" value={data.rejected} tone="text-red-600" />
            <StatCard label="Needs review" value={data.needs_review} tone="text-amber-600" />
            <StatCard label="Failed" value={data.failed} tone="text-slate-500" />
          </div>

          <Card title="Recent batches">
            {data.recent_batches.length === 0 ? (
              <EmptyState title="No evaluations yet">
                Start one on the <Link href="/upload" className="text-blue-600 underline">New evaluation</Link> page.
              </EmptyState>
            ) : (
              <ul className="divide-y divide-slate-100">
                {data.recent_batches.map((batch) => (
                  <li key={batch.id}>
                    <Link href={`/results/${batch.id}`} className="flex items-center justify-between gap-4 py-3 hover:bg-slate-50">
                      <div>
                        <p className="font-medium text-slate-900">{batch.name}</p>
                        <p className="text-xs text-slate-500">
                          {new Date(batch.created_at).toLocaleString()} · {batch.total_documents} document(s)
                        </p>
                      </div>
                      <span className="text-sm font-medium text-slate-600">{batch.status}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      )}
    </>
  );
}
