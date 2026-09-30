// Thin, explicit API client for the Case Crash Test & Resilience Lab backend.
// Every function maps to exactly one real backend endpoint (see docs/api.md
// and backend/app/api/routes.py). Nothing here fabricates data — an
// empty/error response is surfaced to the UI as an empty/error state.

const BASE = "/api";

// RBAC: backend/app/rbac.py reads a caller-supplied X-User-Role header
// (ANALYST | REVIEWER | ADMIN). No login system exists yet in Section 1/2,
// so the frontend exposes an explicit "acting as" role switcher (see
// components/RoleSwitcher.tsx) rather than silently assuming privilege.
export function getActingRole(): string {
  return localStorage.getItem("cct.actingRole") ?? "ANALYST";
}
export function setActingRole(role: string) {
  localStorage.setItem("cct.actingRole", role);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", "X-User-Role": getActingRole() },
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {
      /* ignore parse failure, fall back to statusText */
    }
    throw new Error(`${res.status}: ${detail}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string; service: string; section: number }>("/health"),

  loadDemo: () =>
    request<{ disclaimer: string; message?: string; cases: { id: string; title: string }[] }>("/demo/load", {
      method: "POST",
    }),

  listCases: () => request<CaseOut[]>("/cases"),
  createCase: (payload: { title: string; description?: string; is_demo?: boolean }) =>
    request<CaseOut>("/cases", { method: "POST", body: JSON.stringify(payload) }),
  getCase: (caseId: string) => request<CaseOut>(`/cases/${caseId}`),
  getGraph: (caseId: string) => request<GraphOut>(`/cases/${caseId}/graph`),

  listSnapshots: (caseId: string) => request<SnapshotOut[]>(`/cases/${caseId}/snapshots`),
  createSnapshot: (caseId: string, label?: string, created_by = "user") =>
    request<SnapshotOut>(`/cases/${caseId}/snapshots`, {
      method: "POST",
      body: JSON.stringify({ label, created_by }),
    }),
  restoreSnapshot: (caseId: string, snapshotId: string, approved_by: string, reason: string) =>
    request<Record<string, unknown>>(`/cases/${caseId}/snapshots/${snapshotId}/restore`, {
      method: "POST",
      body: JSON.stringify({ approved_by, reason }),
    }),

  listScenarios: (caseId: string) => request<ScenarioOut[]>(`/cases/${caseId}/scenarios`),
  createScenario: (
    caseId: string,
    payload: { name: string; description?: string; mutations: MutationSpec[]; is_technical_resilience_test?: boolean },
  ) => request<ScenarioOut>(`/cases/${caseId}/scenarios`, { method: "POST", body: JSON.stringify(payload) }),

  listSimulations: (caseId: string) => request<SimulationOut[]>(`/cases/${caseId}/simulations`),
  runSimulation: (
    caseId: string,
    payload: {
      base_snapshot_id: string;
      scenario_id?: string;
      inline_mutations?: MutationSpec[];
      created_by?: string;
      explain?: boolean;
    },
  ) => request<SimulationOut>(`/cases/${caseId}/simulations`, { method: "POST", body: JSON.stringify(payload) }),

  getSimulation: (simId: string) => request<SimulationOut>(`/simulations/${simId}`),
  getDiff: (simId: string) => request<StateDiff | null>(`/simulations/${simId}/diff`),
  getBlastRadius: (simId: string) => request<BlastRadius | null>(`/simulations/${simId}/blast-radius`),
  getFailureTree: (simId: string) => request<FailureTree[] | null>(`/simulations/${simId}/failure-tree`),
  getRecoveryOptions: (simId: string) => request<RecoveryOption[] | null>(`/simulations/${simId}/recovery-options`),
  rerunSimulation: (simId: string) => request<SimulationOut>(`/simulations/${simId}/rerun`, { method: "POST" }),
  compareSimulations: (simulationIdA: string, simulationIdB: string) =>
    request<Record<string, unknown>>(`/simulations/${simulationIdA}/compare`, {
      method: "POST",
      body: JSON.stringify({ simulation_id_a: simulationIdA, simulation_id_b: simulationIdB }),
    }),
  runRecoverySimulation: (simId: string, additionalMutations: MutationSpec[]) =>
    request<{ base_simulation_id: string; recovery_mutations: MutationSpec[]; result: Record<string, unknown>; note: string }>(
      `/simulations/${simId}/recovery-simulation`,
      { method: "POST", body: JSON.stringify({ additional_mutations: additionalMutations }) },
    ),

  getReviewQueue: (caseId: string) => request<ReviewTaskOut[]>(`/cases/${caseId}/review-queue`),
  approveReview: (reviewId: string, decided_by: string, note?: string) =>
    request<ReviewTaskOut>(`/reviews/${reviewId}/approve`, {
      method: "POST",
      body: JSON.stringify({ decided_by, note }),
    }),
  rejectReview: (reviewId: string, decided_by: string, note?: string) =>
    request<ReviewTaskOut>(`/reviews/${reviewId}/reject`, {
      method: "POST",
      body: JSON.stringify({ decided_by, note }),
    }),

  getAudit: (caseId: string) => request<AuditEventOut[]>(`/cases/${caseId}/audit`),
  getEvaluation: (caseId: string) => request<EvaluationResult>(`/cases/${caseId}/evaluation`),
  getIntegrationSummary: (caseId: string) => request<IntegrationSummary>(`/cases/${caseId}/integration-summary`),
};

// ---- Types mirroring backend/app/schemas/schemas.py exactly ----

export interface CaseOut {
  id: string;
  title: string;
  description?: string | null;
  is_demo: boolean;
  created_at: string;
  updated_at: string;
}

export interface NodeOut {
  id: string;
  case_id: string;
  node_type: string;
  label: string;
  status: string;
  attributes: Record<string, unknown>;
  provenance_ref?: string | null;
}

export interface RelationshipOut {
  id: string;
  case_id: string;
  source_id: string;
  target_id: string;
  rel_type: string;
  attributes: Record<string, unknown>;
}

export interface GraphOut {
  nodes: NodeOut[];
  relationships: RelationshipOut[];
}

export interface SnapshotOut {
  id: string;
  case_id: string;
  version: number;
  label?: string | null;
  created_at: string;
  created_by: string;
}

export interface MutationSpec {
  mutation_type: string;
  target_node_id: string;
}

export interface ScenarioOut {
  id: string;
  case_id: string;
  name: string;
  description?: string | null;
  mutations: MutationSpec[];
  is_technical_resilience_test: boolean;
  created_at: string;
}

export interface SimulationOut {
  id: string;
  case_id: string;
  base_snapshot_id: string;
  scenario_id?: string | null;
  status: string;
  created_at: string;
  created_by: string;
  result?: SimulationResultPayload | null;
  human_review_required: boolean;
}

export interface AffectedNode {
  node_id: string;
  node_type: string;
  label: string;
  order: number;
  impact_types: string[];
  new_status: string;
  path_from_root: string[];
}

export interface SimulationResultPayload {
  status: string;
  mutations_applied?: Record<string, unknown>[];
  affected_nodes: AffectedNode[];
  cascade_chains?: unknown[];
  blast_radius: BlastRadius;
  criticality?: Record<string, string | null>;
  failure_trees: FailureTree[];
  diff: StateDiff;
  recovery_options: RecoveryOption[];
  human_review_required: boolean;
  simulated_state?: Record<string, unknown>;
  explanation?: string;
  explanation_error?: string;
  error?: string;
}

export interface DiffChangedNode {
  node_id: string;
  label: string;
  node_type?: string;
  change: "STATUS_CHANGED" | "REMOVED_IN_SIMULATION";
  base_status: string | null;
  simulated_status: string | null;
}

export interface StateDiff {
  changed_node_count: number;
  changed_nodes: DiffChangedNode[];
  added_nodes: { node_id: string; label: string; change: string; simulated_status: string }[];
  base_node_count: number;
  simulated_node_count: number;
}

export interface BlastRadius {
  root_node_ids: string[];
  directly_affected_nodes: string[];
  indirectly_affected_nodes: string[];
  affected_documents: string[];
  affected_evidence: string[];
  affected_claims: string[];
  affected_issues: string[];
  affected_obligations: string[];
  affected_deadlines: string[];
  affected_hearings: string[];
  affected_registry_defects: string[];
  affected_workflows: string[];
  new_unknowns: string[];
  new_conflicts: string[];
  new_blocks: string[];
  verification_gaps: string[];
  human_review_items: string[];
  total_affected_count: number;
}

export interface FailureTreeLeaf {
  node_id: string;
  node_type: string;
  label: string;
  impact_types: string[];
  new_status: string;
  path_from_root: string[];
}

export interface FailureTree {
  root_failure: string;
  direct_impact: FailureTreeLeaf[];
  dependency_impact: FailureTreeLeaf[];
  verification_impact: FailureTreeLeaf[];
  workflow_impact: FailureTreeLeaf[];
  human_review: FailureTreeLeaf[];
  cascade_chains?: unknown[];
}

export interface RecoveryOption {
  action: string;
  reason: string;
  affected_nodes: string[];
  required_evidence: boolean;
  dependencies: string[];
  verification_required: boolean;
  human_approval_required: boolean;
}

export interface ReviewTaskOut {
  id: string;
  case_id: string;
  simulation_id?: string | null;
  node_id?: string | null;
  reason: string;
  status: string;
  created_at: string;
  resolved_at?: string | null;
  resolved_by?: string | null;
}

export interface AuditEventOut {
  id: string;
  case_id: string;
  event_type: string;
  actor: string;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface EvaluationResult {
  case_id?: string;
  tests?: { name: string; status: "PASS" | "FAIL" | "NOT_RUN"; detail?: string }[];
  pass_count?: number;
  fail_count?: number;
  not_run_count?: number;
  [key: string]: unknown;
}

export interface IntegrationSummary {
  case_id: string;
  base_state_version?: number | null;
  active_simulations: number;
  critical_dependencies: string[];
  fragile_nodes: string[];
  recent_failures: { simulation_id: string; status: string; created_at: string }[];
  affected_claims: string[];
  affected_issues: string[];
  affected_obligations: string[];
  affected_deadlines: string[];
  affected_hearings: string[];
  affected_registry_defects: string[];
  blocked_workflows: string[];
  verification_gaps: string[];
  human_review_items: string[];
  provenance_refs: string[];
  last_updated?: string | null;
}
