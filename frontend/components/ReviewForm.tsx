"use client";

import { useState } from "react";
import { api } from "@/services/api";
import type { ReviewCreate } from "@/types/api";

/** Saves a human review note. The automated decision is never changed by this. */
export function ReviewForm({ documentId, onSaved }: { documentId: string; onSaved: () => void }) {
  const [form, setForm] = useState<ReviewCreate>({
    reviewer_name: "",
    review_status: "COMPLETED",
    reviewer_decision: null,
    review_note: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!form.reviewer_name.trim() || !form.review_note.trim()) {
      setError("Enter your name and a review note.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await api.addReview(documentId, form);
      setSaved(true);
      setForm({ ...form, review_note: "" });
      onSaved();
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const input = "mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none";
  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div className="grid gap-3 sm:grid-cols-3">
        <label className="block text-sm">
          <span className="font-medium text-slate-700">Reviewer name</span>
          <input className={input} value={form.reviewer_name} onChange={(e) => setForm({ ...form, reviewer_name: e.target.value })} />
        </label>
        <label className="block text-sm">
          <span className="font-medium text-slate-700">Review status</span>
          <select
            className={input}
            value={form.review_status}
            onChange={(e) => setForm({ ...form, review_status: e.target.value as ReviewCreate["review_status"] })}
          >
            <option value="COMPLETED">Completed</option>
            <option value="IN_PROGRESS">In progress</option>
          </select>
        </label>
        <label className="block text-sm">
          <span className="font-medium text-slate-700">Reviewer&apos;s decision</span>
          <select
            className={input}
            value={form.reviewer_decision ?? ""}
            onChange={(e) => setForm({ ...form, reviewer_decision: (e.target.value || null) as ReviewCreate["reviewer_decision"] })}
          >
            <option value="">Not decided</option>
            <option value="APPROVE">Approve</option>
            <option value="REJECT">Reject</option>
          </select>
        </label>
      </div>
      <label className="block text-sm">
        <span className="font-medium text-slate-700">Note</span>
        <textarea
          rows={3}
          className={input}
          value={form.review_note}
          onChange={(e) => setForm({ ...form, review_note: e.target.value })}
          placeholder="What did you check, and what did you find?"
        />
      </label>
      {error && <p className="text-sm text-red-700">{error}</p>}
      {saved && !error && <p className="text-sm text-emerald-700">Review saved. The automated decision is kept unchanged.</p>}
      <button
        type="submit"
        disabled={busy}
        className="rounded-md bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700 disabled:bg-slate-400"
      >
        {busy ? "Saving..." : "Save review"}
      </button>
    </form>
  );
}
