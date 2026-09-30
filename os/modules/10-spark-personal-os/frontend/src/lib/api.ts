/**
 * Spark Personal OS — API client.
 *
 * This module ONLY moves data between the backend and the UI. It never
 * fabricates case facts, deadlines, or attention items — everything the UI
 * shows must come from a real response object here.
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const TOKEN_KEY = "spark.auth.token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> | undefined),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (res.status === 204) return undefined as T;

  let body: unknown = null;
  try {
    body = await res.json();
  } catch {
    // no body
  }

  if (!res.ok) {
    const detail =
      body && typeof body === "object" && "detail" in body
        ? String((body as { detail: unknown }).detail)
        : res.statusText;
    throw new ApiError(res.status, detail);
  }
  return body as T;
}

// ---- Types (mirroring backend schemas.py) ----

export type Role = "citizen" | "legal_aid" | "paralegal" | "advocate" | "admin";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
}

export interface Case {
  id: string;
  case_number: string;
  title: string;
  status: string;
  current_state_summary: string | null;
  is_demo: boolean;
  updated_at: string;
}

export interface AttentionItem {
  id: string;
  case_id: string;
  source_engine: string;
  source_entity: string;
  type: string;
  priority: "INFO" | "ATTENTION" | "HIGH_ATTENTION" | "REQUIRES_HUMAN_REVIEW";
  reason: string;
  status: string;
  provenance_refs: string[];
  requires_human_review: boolean;
  recommended_safe_action: string | null;
  what_changed: string | null;
  created_at: string;
  updated_at: string;
}

export interface Task {
  id: string;
  case_id: string;
  title: string;
  description: string | null;
  source_engine: string | null;
  status: string;
  priority: string;
  requires_verification: boolean;
  completed_at: string | null;
  created_at: string;
}

export interface Deadline {
  id: string;
  case_id: string;
  label: string;
  tracked_date: string;
  date_source_type: "SOURCE_STATED" | "USER_ENTERED" | "SYSTEM_DERIVED" | "UNKNOWN";
  source_engine: string | null;
}

export interface ReviewTask {
  id: string;
  case_id: string;
  kind: string;
  what: string;
  why: string;
  source_engine: string;
  evidence_refs: string[];
  current_state: string;
  proposed_action: string;
  status: string;
}

export interface ApprovalRequest {
  id: string;
  case_id: string;
  action_type: string;
  description: string;
  requested_by: string;
  status: string;
}

export interface WorkspaceSummary {
  my_cases_count: number;
  my_attention_count: number;
  my_tasks_open_count: number;
  my_deadlines_upcoming_count: number;
  my_reviews_pending_count: number;
  my_approvals_pending_count: number;
  my_handoffs_pending_count: number;
}

export interface CaseDigest {
  case_id: string;
  current_state: string;
  what_changed: string[];
  needs_attention: string[];
  blocked: string[];
  unknown: string[];
  needs_review: string[];
  next_safe_actions: string[];
  generated_at: string;
}

// ---- Endpoints actually used by the UI ----

export const api = {
  register: (email: string, password: string, full_name: string, role: Role = "citizen") =>
    request<User>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, full_name, role }),
    }),
  login: (email: string, password: string) =>
    request<{ access_token: string; token_type: string }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  me: () => request<User>("/api/auth/me"),

  workspaceSummary: () => request<WorkspaceSummary>("/api/workspace/summary"),
  cases: () => request<Case[]>("/api/cases"),
  caseDigest: (caseId: string) => request<CaseDigest>(`/api/cases/${caseId}/digest`),
  attention: () => request<AttentionItem[]>("/api/attention"),
  tasks: () => request<Task[]>("/api/tasks"),
  deadlines: () => request<Deadline[]>("/api/deadlines"),
  reviews: () => request<ReviewTask[]>("/api/reviews"),
  approvals: () => request<ApprovalRequest[]>("/api/approvals"),
  search: (q: string) =>
    request<{ query: string; results: unknown[] }>(`/api/search?q=${encodeURIComponent(q)}`),
};
