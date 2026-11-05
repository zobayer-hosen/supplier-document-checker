// All calls to the FastAPI backend live here, so pages never build URLs themselves.

import type {
  ApiErrorBody,
  BatchDetail,
  DashboardSummary,
  DocumentDetail,
  Evidence,
  PendingReview,
  Review,
  ReviewCreate,
  SupplierResultRow,
  UploadResult,
  Validation,
} from "@/types/api";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

/** An error from the backend, with the per-file or per-field details it sent. */
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public details: ApiErrorBody["error"]["details"] = [],
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, { cache: "no-store", ...init });
  } catch {
    throw new ApiError("Cannot reach the backend. Is it running on " + API_URL + "?", 0);
  }

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as ApiErrorBody | null;
    throw new ApiError(body?.error.message ?? `Request failed (${response.status})`, response.status, body?.error.details);
  }
  return (await response.json()) as T;
}

function sendJson<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export const api = {
  getDashboard: () => request<DashboardSummary>("/dashboard"),
  createBatch: (name: string) => sendJson<BatchDetail>("/batches", { name }),
  getBatch: (batchId: string) => request<BatchDetail>(`/batches/${batchId}`),
  processBatch: (batchId: string) => request<{ message: string }>(`/batches/${batchId}/process`, { method: "POST" }),
  getResults: (batchId: string) => request<SupplierResultRow[]>(`/batches/${batchId}/results`),

  uploadFiles: (batchId: string, files: File[]) => {
    const form = new FormData();
    files.forEach((file) => form.append("files", file));
    return request<UploadResult>(`/batches/${batchId}/upload`, { method: "POST", body: form });
  },

  getDocument: (documentId: string) => request<DocumentDetail>(`/documents/${documentId}`),
  getValidations: (documentId: string) => request<Validation[]>(`/documents/${documentId}/validations`),
  getEvidence: (documentId: string) => request<Evidence[]>(`/documents/${documentId}/evidence`),
  getReviews: (documentId: string) => request<Review[]>(`/documents/${documentId}/reviews`),
  addReview: (documentId: string, review: ReviewCreate) => sendJson<Review>(`/documents/${documentId}/reviews`, review),
  pendingReviews: () => request<PendingReview[]>("/reviews/pending"),

  documentFileUrl: (documentId: string, page?: number | null) =>
    `${API_URL}/documents/${documentId}/file${page ? `#page=${page}` : ""}`,
};
