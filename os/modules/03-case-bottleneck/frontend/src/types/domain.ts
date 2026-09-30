export type Confidence = "CONFIRMED" | "LIKELY" | "POSSIBLE" | "UNKNOWN";
export type Attention = "CRITICAL ATTENTION" | "HIGH ATTENTION" | "NORMAL" | "LOW" | "UNKNOWN";

export interface CaseSummary {
  id: string;
  title: string;
  case_type: string;
  description: string;
  is_demo: boolean;
  demo_scenario?: string | null;
  created_at: string;
  open_bottlenecks: number;
  total_bottlenecks: number;
}

export interface Bottleneck {
  id: string;
  case_id: string;
  type: string;
  description: string;
  root_cause_candidate: string;
  evidence_refs: string[];
  dependency_refs: string[];
  affected_transitions: string[];
  blocked_items: string[];
  responsible_actor_if_known: string | null;
  first_observed_at: string;
  last_confirmed_at: string;
  last_updated_at: string;
  resolved_at: string | null;
  severity_factors: Record<string, unknown>;
  attention_state: Attention;
  confidence: Confidence;
  status: string;
  verification_state: string;
  contradicting_evidence: string[];
  missing_evidence: string[];
  recurrence_count: number;
}

export interface RootCauseCandidate {
  id: string;
  bottleneck_id: string;
  case_id: string;
  chain: Array<{
    step: string;
    description: string;
    evidence?: string[];
    confidence?: string;
    debate?: Array<{ agent: string; claim: string }>;
  }>;
  confidence: Confidence;
  is_primary: boolean;
  created_at: string;
}

export interface ActionItem {
  id: string;
  case_id: string;
  bottleneck_id: string;
  action_type: string;
  purpose: string;
  required_actor: string;
  status: string;
  expected_effect: string;
  risk: string;
  verification_method: string;
  created_at: string;
  approved_at: string | null;
  executed_at: string | null;
  result: Record<string, unknown>;
  rejection_reason: string | null;
}

export interface AuditEvent {
  id: string;
  case_id: string;
  correlation_id: string;
  actor: string;
  event: string;
  source: string;
  result: Record<string, unknown>;
  timestamp: string;
}

export interface FlowNode {
  id: string;
  kind: "dependency" | "transition";
  description: string;
  type: string;
  status: string;
}
export interface FlowEdge { from: string; to: string; relationship: string; }
export interface FlowGraph { nodes: FlowNode[]; edges: FlowEdge[]; }

export interface FlowHealth {
  open_bottlenecks: number;
  resolved_bottlenecks: number;
  unknown_confidence_count: number;
  contradiction_count: number;
  recurring_count: number;
  total_blocked_transitions: number;
}

export interface InvestigateResult {
  correlation_id: string;
  bottleneck_count: number;
  primary_bottleneck_id: string | null;
  bottlenecks: Bottleneck[];
}

export interface SimulationResult {
  mode: "SIMULATION_ONLY";
  removed_dependency: string;
  unblocked_transitions: string[];
  remains_blocked_transitions: string[];
  newly_relevant_bottlenecks: string[];
  remaining_bottlenecks: string[];
}

export interface CollapseTestResult {
  mode: "SIMULATION_ONLY";
  transitions_unblocked: number;
  dependencies_removed: number;
  remaining_bottlenecks: number;
  new_primary_candidate: string | null;
}

export interface CrashTestResult {
  mode: "SIMULATION_ONLY";
  mutation: string;
  target_dependency: string;
  expected_effect: string;
  observed_effect: string;
  result: "PASS" | "WARNING" | "FAIL";
}

export interface HistoryEntry {
  id: string;
  bottleneck_id: string;
  case_id: string;
  from_status: string;
  to_status: string;
  timestamp: string;
  note: string;
}

export interface CaseDocument {
  id: string;
  case_id: string;
  name: string;
  content_text: string;
  uploaded_at: string;
  contains_injection_attempt: boolean;
  quarantined: boolean;
  sha256: string | null;
}
