// Thin typed fetch wrapper. Every function maps 1:1 to a real backend
// route -- nothing here fabricates data; a failed call surfaces as a
// thrown Error the UI turns into an error/empty state (see StatusBanner).

const BASE = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      /* no-op */
    }
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json();
}

export interface CaseSummary {
  id: string;
  title: string;
  case_type: string;
  current_stage: string;
  parties: { name: string; role: string }[];
  is_synthetic: string;
  created_at: string;
  updated_at: string;
}

export interface Hearing {
  id: string;
  case_id: string;
  hearing_date: string | null;
  is_next: string;
  purpose: string | null;
  purpose_status: "DETERMINED" | "UNCERTAIN";
  uncertainty_reasons: string[];
  stage_at_hearing: string | null;
}

export interface Evidence {
  id: string;
  case_id: string;
  document_id: string | null;
  label: string;
  evidence_type: string;
  availability: "AVAILABLE" | "MISSING" | "PARTIAL" | "UNKNOWN";
  verification_state: "VERIFIED" | "UNVERIFIED" | "DISPUTED";
  page_ref: string | null;
  confidence: string;
  notes: string[];
}

export interface Requirement {
  id: string;
  case_id: string;
  hearing_id: string | null;
  category: string;
  description: string;
  status: "SATISFIED" | "UNRESOLVED" | "UNKNOWN";
  reason: string;
  evidence_refs: string[];
  confidence: string;
  responsible_actor: string | null;
  recommended_next_step: string | null;
}

export interface Blocker {
  id: string;
  case_id: string;
  requirement_id: string;
  description: string;
  category: string;
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  evidence_refs: string[];
  dependent_requirements: string[];
  downstream_impact: string;
  responsible_actor: string | null;
  deadline: string | null;
  status: "OPEN" | "RESOLVED" | "SIMULATED_RESOLVED";
  confidence: string;
  suggested_safe_action: string | null;
  history: { event: string; timestamp: string }[];
}

export interface DocumentRow {
  id: string;
  case_id: string;
  original_filename: string;
  file_type: string;
  size_bytes: number;
  content_hash: string;
  extraction_method: string;
  extraction_status: string;
  extracted_sections: { page: number | null; section: string; text: string; confidence: string }[];
  doc_category: string | null;
  injection_flag: string;
  injection_notes: string[];
  created_at: string;
}

export interface Action {
  id: string;
  case_id: string;
  blocker_id: string | null;
  action_type: string;
  description: string;
  reason: string;
  evidence_refs: string[];
  risk: string;
  affected_case_state: { type: string; id: string }[];
  expected_effect: string;
  unknowns: string[];
  status: string;
  result: Record<string, unknown> | null;
}

export interface ReadinessSnapshot {
  overall: "READY" | "CONDITIONAL" | "BLOCKED" | "UNKNOWN";
  categories: Record<string, string>;
  hearing_context_uncertain: boolean;
  open_blocker_count: number;
  requirement_count: number;
  satisfied_count: number;
  unresolved_count: number;
  unknown_count: number;
  version_id?: string;
  version_number?: number;
}

export interface CaseFull {
  case: CaseSummary;
  documents: DocumentRow[];
  evidence: Evidence[];
  hearings: Hearing[];
  requirements: Requirement[];
  blockers: Blocker[];
}

export interface AgentRunStep {
  step: string;
  agent: string;
  tool_calls: string[];
  status: string;
  detail: unknown;
}
export interface AgentRun {
  id: string;
  case_id: string;
  correlation_id: string;
  steps: AgentRunStep[];
  status: string;
}

export interface AuditEvent {
  id: string;
  case_id: string | null;
  actor: string;
  event_type: string;
  action: string;
  input_ref: unknown;
  result: unknown;
  correlation_id: string;
  timestamp: string;
}

export interface GraphNode { type: string; id: string; }
export interface GraphEdge { id: string; from: GraphNode; to: GraphNode; reason: string; }
export interface Graph { nodes: GraphNode[]; edges: GraphEdge[]; }

export interface Explanation {
  what: string;
  why: string;
  evidence: string[];
  dependency: string;
  confidence: string;
  unknown: string[];
  next_safe_action: string;
}

export interface CaseVersion { id: string; case_id: string; version_number: number; trigger: string; created_at: string; }

export interface CrashTestResult {
  id: string;
  case_id: string;
  mutation: string;
  expected_effect: string;
  observed_effect: string;
  passed: string;
  explanation: string;
  impacted_state: string[];
  regression_status: string;
}

export interface SimulationResult {
  id: string;
  case_id: string;
  hypothesis: Record<string, unknown>[];
  baseline_readiness: ReadinessSnapshot;
  simulated_readiness: ReadinessSnapshot;
  diff: {
    resolved_blockers: string[];
    category_changes: Record<string, { before: string; after: string }>;
    overall_change: { before: string; after: string };
  };
  label: string;
}

export interface EvalSummary {
  scope: Record<string, string>;
  measured: Record<string, number | null>;
  not_yet_measured: Record<string, string>;
  sample_sizes: Record<string, number>;
}

export const api = {
  health: () => request<{ status: string; app: string; demo_mode: boolean; env: string }>("/health"),

  listCases: () => request<CaseSummary[]>("/cases"),
  getCase: (id: string) => request<CaseFull>(`/cases/${id}`),
  runAgentPass: (id: string) => request<AgentRun>(`/cases/${id}/run-agent-pass`, { method: "POST" }),

  uploadDocument: async (caseId: string, file: File): Promise<DocumentRow> => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${BASE}/cases/${caseId}/documents`, { method: "POST", body: form });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || res.statusText);
    }
    return res.json();
  },

  getReadiness: (id: string) => request<ReadinessSnapshot>(`/cases/${id}/readiness`),
  runReadinessAudit: (id: string) => request<ReadinessSnapshot>(`/cases/${id}/readiness/run`, { method: "POST" }),

  listBlockers: (id: string) => request<Blocker[]>(`/cases/${id}/blockers`),
  explainBlocker: (caseId: string, blockerId: string) =>
    request<Explanation>(`/cases/${caseId}/blockers/${blockerId}/why`),
  getGraph: (id: string) => request<Graph>(`/cases/${id}/graph`),
  listEvidence: (id: string) => request<Evidence[]>(`/cases/${id}/evidence`),

  simulate: (id: string, hypothesis: Record<string, unknown>[]) =>
    request<SimulationResult>(`/cases/${id}/simulate`, { method: "POST", body: JSON.stringify({ hypothesis }) }),

  runCrashTest: (id: string, mutation?: string) =>
    request<CrashTestResult | CrashTestResult[]>(`/cases/${id}/crash-test`, {
      method: "POST",
      body: JSON.stringify({ mutation: mutation ?? null }),
    }),
  listCrashTests: (id: string) => request<CrashTestResult[]>(`/cases/${id}/crash-test`),

  listVersions: (id: string) => request<CaseVersion[]>(`/cases/${id}/versions`),
  diffVersions: (id: string, from: number, to: number) =>
    request<Record<string, unknown>>(`/cases/${id}/versions/diff?from_version=${from}&to_version=${to}`),

  listActions: (id: string) => request<Action[]>(`/cases/${id}/actions`),
  approveAction: (caseId: string, actionId: string, decision: "APPROVE" | "EDIT" | "REJECT", notes?: string) =>
    request<{ action: Action; approval: unknown; agent_run?: AgentRun }>(
      `/cases/${caseId}/actions/${actionId}/approve`,
      { method: "POST", body: JSON.stringify({ decision, approved_by: "demo_user", notes }) }
    ),

  getAudit: (id: string) => request<AuditEvent[]>(`/cases/${id}/audit`),
  getEvalSummary: (caseId?: string) =>
    request<EvalSummary>(`/eval/summary${caseId ? `?case_id=${caseId}` : ""}`),
};
