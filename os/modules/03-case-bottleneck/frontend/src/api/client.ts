import type {
  CaseSummary, Bottleneck, RootCauseCandidate, ActionItem, AuditEvent,
  FlowGraph, FlowHealth, InvestigateResult, SimulationResult, CollapseTestResult,
  CrashTestResult, HistoryEntry, CaseDocument,
} from "../types/domain";

const BASE = (import.meta as any).env?.VITE_API_BASE || "http://localhost:8000";

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    });
  } catch (e) {
    throw new ApiError(0, `Could not reach the backend at ${BASE}. Is it running?`);
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail ?? body);
    } catch {
      /* body wasn't JSON — keep statusText */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string; service: string }>("/api/health"),

  listCases: () => request<CaseSummary[]>("/api/cases"),
  getCase: (caseId: string) => request<CaseSummary>(`/api/cases/${caseId}`),
  getFlow: (caseId: string) => request<FlowGraph>(`/api/cases/${caseId}/flow`),
  getFlowHealth: (caseId: string) => request<FlowHealth>(`/api/cases/${caseId}/flow-health`),
  getEvents: (caseId: string) => request<unknown[]>(`/api/cases/${caseId}/events`),
  getDocuments: (caseId: string) => request<CaseDocument[]>(`/api/cases/${caseId}/documents`),
  getHistory: (caseId: string) => request<HistoryEntry[]>(`/api/cases/${caseId}/history`),
  getAudit: (caseId: string) => request<AuditEvent[]>(`/api/cases/${caseId}/audit`),

  investigate: (caseId: string) =>
    request<InvestigateResult>(`/api/cases/${caseId}/investigate`, { method: "POST" }),

  listBottlenecks: (caseId: string) =>
    request<{ primary_bottleneck_id: string | null; bottlenecks: Bottleneck[] }>(
      `/api/cases/${caseId}/bottlenecks`,
    ),
  getBottleneck: (caseId: string, bottleneckId: string) =>
    request<{ bottleneck: Bottleneck; root_cause_candidates: RootCauseCandidate[]; impact: unknown }>(
      `/api/cases/${caseId}/bottlenecks/${bottleneckId}`,
    ),
  getRootCause: (caseId: string, bottleneckId: string) =>
    request<RootCauseCandidate>(`/api/cases/${caseId}/root-cause?bottleneck_id=${bottleneckId}`),
  getImpact: (caseId: string, bottleneckId: string) =>
    request<unknown>(`/api/cases/${caseId}/impact?bottleneck_id=${bottleneckId}`),

  listActions: (caseId: string) => request<ActionItem[]>(`/api/cases/${caseId}/actions`),
  approveAction: (caseId: string, actionId: string) =>
    request<{ action: ActionItem; verification: unknown; newly_visible_bottlenecks: string[] }>(
      `/api/cases/${caseId}/actions/${actionId}/approve`, { method: "POST" },
    ),
  rejectAction: (caseId: string, actionId: string, reason: string) =>
    request<ActionItem>(`/api/cases/${caseId}/actions/${actionId}/reject`, {
      method: "POST", body: JSON.stringify({ reason }),
    }),

  simulate: (caseId: string, dependencyId: string) =>
    request<SimulationResult>(`/api/cases/${caseId}/simulate`, {
      method: "POST", body: JSON.stringify({ dependency_id: dependencyId }),
    }),
  collapseTest: (caseId: string, dependencyId: string) =>
    request<CollapseTestResult>(`/api/cases/${caseId}/collapse-test`, {
      method: "POST", body: JSON.stringify({ dependency_id: dependencyId }),
    }),
  listMutations: (caseId: string) => request<string[]>(`/api/cases/${caseId}/crash-test/mutations`),
  runCrashTest: (caseId: string, mutation: string, targetDependencyId?: string) =>
    request<CrashTestResult>(`/api/cases/${caseId}/crash-test`, {
      method: "POST",
      body: JSON.stringify({ mutation, target_dependency_id: targetDependencyId }),
    }),
};

export { ApiError };
