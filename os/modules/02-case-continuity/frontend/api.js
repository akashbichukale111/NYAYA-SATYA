/**
 * Thin fetch wrapper for the Case Continuity Engine API.
 * Same-origin by default (the backend serves this frontend as static files);
 * override API_BASE below if you run the frontend separately from the API.
 */
const API_BASE = window.__CCE_API_BASE__ || "";

async function apiFetch(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: options.body && !(options.body instanceof FormData)
      ? { "Content-Type": "application/json", ...(options.headers || {}) }
      : (options.headers || {}),
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ? JSON.stringify(body.detail) : JSON.stringify(body);
    } catch (_) { /* noop */ }
    throw new Error(`API error ${res.status}: ${detail}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

const api = {
  healthz: () => apiFetch("/api/healthz"),
  seedDemo: () => apiFetch("/api/demo/seed", { method: "POST" }),

  listCases: () => apiFetch("/api/cases"),
  getCase: (id) => apiFetch(`/api/cases/${id}`),
  createCase: (payload) => apiFetch("/api/cases", { method: "POST", body: JSON.stringify(payload) }),

  getState: (id) => apiFetch(`/api/cases/${id}/state`),
  getVersions: (id) => apiFetch(`/api/cases/${id}/versions`),
  getVersion: (id, n) => apiFetch(`/api/cases/${id}/versions/${n}`),
  getDiff: (id, from, to) => apiFetch(`/api/cases/${id}/diff?from=${from}&to=${to}`),
  getEvents: (id) => apiFetch(`/api/cases/${id}/events`),
  getTimeline: (id) => apiFetch(`/api/cases/${id}/timeline`),
  getGraph: (id) => apiFetch(`/api/cases/${id}/graph`),
  getChanges: (id) => apiFetch(`/api/cases/${id}/changes`),
  getConflicts: (id) => apiFetch(`/api/cases/${id}/conflicts`),
  resolveConflict: (id, conflictId, payload) =>
    apiFetch(`/api/cases/${id}/conflicts/${conflictId}/resolve`, { method: "POST", body: JSON.stringify(payload) }),
  getProposals: (id, status) =>
    apiFetch(`/api/cases/${id}/proposals${status ? `?status=${status}` : ""}`),
  reviewProposal: (id, proposalId, payload) =>
    apiFetch(`/api/cases/${id}/proposals/${proposalId}/review`, { method: "POST", body: JSON.stringify(payload) }),
  getContinuityHealth: (id) => apiFetch(`/api/cases/${id}/continuity-health`),
  getAudit: (id) => apiFetch(`/api/cases/${id}/audit`),

  ingest: (id, formData) => apiFetch(`/api/cases/${id}/ingest`, { method: "POST", body: formData }),

  prepareHandoff: (id, payload) => apiFetch(`/api/cases/${id}/handoff`, { method: "POST", body: JSON.stringify(payload) }),
  approveHandoff: (id, handoffId, payload) =>
    apiFetch(`/api/cases/${id}/handoff/${handoffId}/approve`, { method: "POST", body: JSON.stringify(payload) }),

  simulateRemove: (id, payload) => apiFetch(`/api/cases/${id}/simulate/remove`, { method: "POST", body: JSON.stringify(payload) }),
  simulateFieldChange: (id, payload) => apiFetch(`/api/cases/${id}/simulate/field-change`, { method: "POST", body: JSON.stringify(payload) }),
  simulateFutureState: (id, payload) => apiFetch(`/api/cases/${id}/simulate/future-state`, { method: "POST", body: JSON.stringify(payload) }),
  getSimulationHistory: (id) => apiFetch(`/api/cases/${id}/simulate/history`),

  getEvaluation: (caseId) => apiFetch(`/api/evaluation${caseId ? `?case_id=${caseId}` : ""}`),
};
