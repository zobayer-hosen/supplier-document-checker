"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { ApiError, api } from "@/services/api";
import { Card, PageHeader } from "@/components/StateMessages";

const MAX_FILE_MB = 20;

type Problem = { filename?: string; message: string };

/** Quick checks in the browser. The backend checks everything again, by content. */
function checkFiles(pdfs: File[], csv: File | null, rules: File | null): Problem[] {
  const problems: Problem[] = [];
  if (pdfs.length === 0) problems.push({ message: "Add at least one supplier PDF." });
  if (!csv) problems.push({ message: "Add the Purchase Request CSV." });
  if (!rules) problems.push({ message: "Add the company rules Markdown file." });

  const names = new Set<string>();
  for (const file of [...pdfs, csv, rules].filter((f): f is File => f !== null)) {
    if (file.size > MAX_FILE_MB * 1024 * 1024) problems.push({ filename: file.name, message: `is larger than ${MAX_FILE_MB} MB.` });
    if (names.has(file.name)) problems.push({ filename: file.name, message: "was added twice." });
    names.add(file.name);
  }
  return problems;
}

function FileField(props: { label: string; hint: string; accept: string; multiple?: boolean; onChange: (files: File[]) => void }) {
  return (
    <label className="block">
      <span className="text-sm font-medium text-slate-800">{props.label}</span>
      <span className="block text-xs text-slate-500">{props.hint}</span>
      <input
        type="file"
        accept={props.accept}
        multiple={props.multiple}
        onChange={(event) => props.onChange(Array.from(event.target.files ?? []))}
        className="mt-2 block w-full text-sm text-slate-600 file:mr-4 file:rounded-md file:border-0 file:bg-slate-100 file:px-4 file:py-2 file:text-sm file:font-medium hover:file:bg-slate-200"
      />
    </label>
  );
}

export function UploadForm() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [pdfs, setPdfs] = useState<File[]>([]);
  const [csv, setCsv] = useState<File | null>(null);
  const [rules, setRules] = useState<File | null>(null);
  const [problems, setProblems] = useState<Problem[]>([]);
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  // If the upload fails, the batch already exists; reuse it on the next try.
  const [batchId, setBatchId] = useState<string | null>(null);
  const [uploaded, setUploaded] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const found = checkFiles(pdfs, csv, rules);
    if (!name.trim()) found.unshift({ message: "Enter a batch name." });
    setProblems(found);
    if (found.length > 0) return;

    setBusy(true);
    try {
      let id = batchId;
      if (!id) {
        setStatus("Creating batch...");
        id = (await api.createBatch(name.trim())).id;
        setBatchId(id);
      }
      if (!uploaded) {
        setStatus("Uploading and validating files...");
        await api.uploadFiles(id, [...pdfs, csv!, rules!]);
        setUploaded(true);
      }
      setStatus("Starting evaluation...");
      await api.processBatch(id);
      router.push(`/results/${id}`);
    } catch (error) {
      const apiError = error as ApiError;
      setProblems(apiError.details?.length ? apiError.details : [{ message: apiError.message }]);
      setStatus(null);
      setBusy(false);
    }
  }

  return (
    <>
      <PageHeader title="New evaluation" subtitle="Upload supplier quotations, the Purchase Request and the company rules." />
      <form onSubmit={handleSubmit} className="space-y-6">
        <Card>
          <div className="space-y-5">
            <label className="block">
              <span className="text-sm font-medium text-slate-800">Batch name</span>
              <input
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="e.g. PR-2026-114 supplier quotes"
                disabled={batchId !== null}
                className="mt-2 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none disabled:bg-slate-100"
              />
            </label>
            <FileField label="Supplier PDFs" hint="One quotation per PDF. You can select several." accept=".pdf,application/pdf" multiple onChange={setPdfs} />
            <FileField label="Purchase Request (CSV)" hint="Items, requested quantities and maximum unit prices." accept=".csv,text/csv" onChange={(f) => setCsv(f[0] ?? null)} />
            <FileField label="Company rules (Markdown)" hint="The company-rules.md file." accept=".md,text/markdown" onChange={(f) => setRules(f[0] ?? null)} />
          </div>

          {pdfs.length > 0 && (
            <p className="mt-4 text-sm text-slate-600">
              {pdfs.length} PDF(s) selected: {pdfs.map((file) => file.name).join(", ")}
            </p>
          )}
        </Card>

        {problems.length > 0 && (
          <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
            <p className="font-semibold">Please fix these problems:</p>
            <ul className="mt-2 list-disc space-y-1 pl-5">
              {problems.map((problem, index) => (
                <li key={index}>
                  {problem.filename && <strong>{problem.filename} </strong>}
                  {problem.message}
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="flex items-center gap-4">
          <button
            type="submit"
            disabled={busy}
            className="rounded-md bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-blue-300"
          >
            {busy ? "Working..." : "Upload and start evaluation"}
          </button>
          {status && <span className="text-sm text-slate-600">{status}</span>}
        </div>
      </form>
    </>
  );
}
