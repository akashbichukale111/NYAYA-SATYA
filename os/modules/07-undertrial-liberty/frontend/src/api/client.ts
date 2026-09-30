import axios from "axios";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

// Runtime-mutable DEMO identity. Real deployments replace this with a
// proper JWT/session flow (see docs/security.md) -- this exists purely so
// the Settings page can demonstrate RBAC by switching roles without a
// rebuild. Persisted to localStorage only for developer convenience across
// reloads; never used to store anything sensitive.
const STORAGE_KEY = "uls-demo-identity";
type DemoIdentity = { role: string; user: string };

function loadIdentity(): DemoIdentity {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch {
    // ignore
  }
  return { role: "ADVOCATE", user: "frontend-demo-advocate" };
}

let identity: DemoIdentity = loadIdentity();

export function getDemoIdentity(): DemoIdentity {
  return identity;
}

export function setDemoIdentity(next: DemoIdentity) {
  identity = next;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  } catch {
    // ignore
  }
}

export const ROLES = ["CITIZEN", "LEGAL_AID", "ADVOCATE", "ADMIN"] as const;

export const api = axios.create({ baseURL: API_BASE });

api.interceptors.request.use((config) => {
  config.headers = config.headers || {};
  config.headers["X-Demo-Role"] = identity.role;
  config.headers["X-Demo-User"] = identity.user;
  return config;
});

export interface Case {
  id: string;
  case_reference: string;
  title: string;
  jurisdiction_note: string | null;
  is_demo: boolean;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface AttentionItem {
  id: string;
  case_id: string;
  category: string;
  severity: string;
  reason: string;
  source_refs: any[];
  status: string;
  requires_human_review: boolean;
  related_entity_type: string | null;
  related_entity_id: string | null;
  created_at: string;
}

export interface DigitalTwin {
  case_id: string;
  case_reference: string;
  is_demo: boolean;
  custody_state: string;
  custody_state_confidence: string;
  latest_verified_event: any;
  current_custody_events: any[];
  upcoming_tracked_events: any[];
  recent_orders: any[];
  bail_events: any[];
  release_events: any[];
  pending_reviews: any[];
  missing_information: string[];
  conflicts: any[];
  attention_items: AttentionItem[];
  documents_ingested: number;
  provenance_refs: string[];
  last_updated: string | null;
}

export const CasesAPI = {
  list: () => api.get<Case[]>("/api/cases").then((r) => r.data),
  get: (id: string) => api.get<Case>(`/api/cases/${id}`).then((r) => r.data),
  create: (payload: { case_reference: string; title: string; person_full_name: string; jurisdiction_note?: string }) =>
    api.post<Case>("/api/cases", payload).then((r) => r.data),
  digitalTwin: (id: string) => api.get<DigitalTwin>(`/api/cases/${id}/digital-twin`).then((r) => r.data),
  documents: (id: string) => api.get(`/api/cases/${id}/documents`).then((r) => r.data),
  uploadDocument: (id: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return api.post(`/api/cases/${id}/documents`, form, {
      headers: { "Content-Type": "multipart/form-data" },
    }).then((r) => r.data);
  },
  timeline: (id: string) => api.get(`/api/cases/${id}/timeline`).then((r) => r.data),
  custody: (id: string) => api.get(`/api/cases/${id}/custody`).then((r) => r.data),
  hearings: (id: string) => api.get(`/api/cases/${id}/hearings`).then((r) => r.data),
  orders: (id: string) => api.get(`/api/cases/${id}/orders`).then((r) => r.data),
  bailEvents: (id: string) => api.get(`/api/cases/${id}/bail-events`).then((r) => r.data),
  releaseEvents: (id: string) => api.get(`/api/cases/${id}/release-events`).then((r) => r.data),
  attention: (id: string) => api.get<{ attention_items: AttentionItem[] }>(`/api/cases/${id}/attention`).then((r) => r.data),
  dependencyGraph: (id: string) => api.get(`/api/cases/${id}/dependency-graph`).then((r) => r.data),
  conflicts: (id: string) => api.get(`/api/cases/${id}/conflicts`).then((r) => r.data),
  verification: (id: string) => api.get(`/api/cases/${id}/verification`).then((r) => r.data),
  resolveConflict: (conflictId: string, resolved_value: string, note: string) =>
    api.post(`/api/conflicts/${conflictId}/resolve`, null, { params: { resolved_value, note } }).then((r) => r.data),
  reviewQueue: (id: string) => api.get(`/api/cases/${id}/review-queue`).then((r) => r.data),
  approveReview: (reviewId: string, note?: string) =>
    api.post(`/api/reviews/${reviewId}/approve`, { note }).then((r) => r.data),
  rejectReview: (reviewId: string, note?: string) =>
    api.post(`/api/reviews/${reviewId}/reject`, { note }).then((r) => r.data),
  audit: (id: string) => api.get(`/api/cases/${id}/audit`).then((r) => r.data),
  timeMachine: (id: string, compareA?: string, compareB?: string) =>
    api.get(`/api/cases/${id}/time-machine`, { params: { compare_a: compareA, compare_b: compareB } }).then((r) => r.data),
  simulate: (id: string, event_type: string, target_entity_id?: string) =>
    api.post(`/api/cases/${id}/simulation`, { event_type, target_entity_id }).then((r) => r.data),
  crashTest: (id: string, event_type: string, target_entity_id?: string) =>
    api.post(`/api/cases/${id}/crash-test`, { event_type, target_entity_id }).then((r) => r.data),
  supportedSimulationEvents: (id: string) =>
    api.get(`/api/cases/${id}/simulation/supported-events`).then((r) => r.data),
  evaluation: (id: string) => api.get(`/api/cases/${id}/evaluation`).then((r) => r.data),
  integrationAdapter: (id: string) => api.get(`/api/cases/${id}/integration/nyaya-satya`).then((r) => r.data),
};
