import type {
  Case, EvidenceItem, Claim, Issue, DependencyGraph, CoverageMetrics,
  FragilityEntry, MissingEvidenceReport, ImpactResult, CrashTestResult,
  ReviewTaskSummary, AuditEventSummary, EvaluationResult, IntegrationSummary,
  DocumentSummary, PipelineRunSummary, EvidenceVersionEntry, RelationshipEdge,
} from './types'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

/** The current actor. Held in memory only (no login system yet -- see
 * docs/security.md); the role switcher in Settings just changes these
 * headers for the rest of the session. */
export const actor = {
  userId: 'demo-user',
  role: 'ADVOCATE',
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  headers.set('X-User-Id', actor.userId)
  headers.set('X-User-Role', actor.role)
  if (!(options.body instanceof FormData) && options.body) {
    headers.set('Content-Type', 'application/json')
  }
  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = body.detail || detail
    } catch {
      // ignore parse failure, fall back to statusText
    }
    throw new ApiError(res.status, detail)
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

export const api = {
  health: () => request<{ status: string }>('/health'),

  listCases: () => request<Case[]>('/cases'),
  getCase: (id: string) => request<Case>(`/cases/${id}`),
  createCase: (title: string, description = '') =>
    request<Case>('/cases', { method: 'POST', body: JSON.stringify({ title, description }) }),
  seedDemo: (key: 'A' | 'B' | 'C') =>
    request<Case>(`/cases/demo/seed/${key}`, { method: 'POST', body: JSON.stringify({}) }),

  listEvidence: (caseId: string) => request<EvidenceItem[]>(`/cases/${caseId}/evidence`),
  getEvidence: (id: string) => request<EvidenceItem>(`/evidence/${id}`),
  createEvidence: (caseId: string, payload: { label: string; source_text?: string }) =>
    request<EvidenceItem>(`/cases/${caseId}/evidence`, { method: 'POST', body: JSON.stringify(payload) }),

  listClaims: (caseId: string) => request<Claim[]>(`/cases/${caseId}/claims`),
  createClaim: (caseId: string, text: string) =>
    request<Claim>(`/cases/${caseId}/claims`, { method: 'POST', body: JSON.stringify({ text }) }),

  listIssues: (caseId: string) => request<Issue[]>(`/cases/${caseId}/issues`),
  createIssue: (caseId: string, question: string, description = '') =>
    request<Issue>(`/cases/${caseId}/issues`, { method: 'POST', body: JSON.stringify({ question, description }) }),

  listRelationships: (caseId: string) => request<RelationshipEdge[]>(`/cases/${caseId}/relationships`),

  getDependencyGraph: (caseId: string) => request<DependencyGraph>(`/cases/${caseId}/dependency-graph`),
  getCoverage: (caseId: string) => request<CoverageMetrics>(`/cases/${caseId}/coverage`),
  getFragility: (caseId: string) => request<FragilityEntry[]>(`/cases/${caseId}/fragility`),
  getMissingEvidence: (caseId: string) => request<MissingEvidenceReport>(`/cases/${caseId}/missing-evidence`),

  getEvidenceImpact: (evidenceId: string) => request<ImpactResult>(`/evidence/${evidenceId}/impact`),
  getClaimImpact: (claimId: string) => request<ImpactResult>(`/claims/${claimId}/impact`),

  runCrashTest: (evidenceId: string, eventType: string) =>
    request<CrashTestResult>(`/evidence/${evidenceId}/crash-test`, {
      method: 'POST',
      body: JSON.stringify({ event_type: eventType, target_type: 'EVIDENCE', target_id: evidenceId }),
    }),

  getReviewQueue: (caseId: string) => request<ReviewTaskSummary[]>(`/cases/${caseId}/review-queue`),
  approveReview: (reviewId: string, note = '') =>
    request<{ id: string; status: string }>(`/reviews/${reviewId}/approve`, {
      method: 'POST', body: JSON.stringify({ note }),
    }),
  rejectReview: (reviewId: string, note = '') =>
    request<{ id: string; status: string }>(`/reviews/${reviewId}/reject`, {
      method: 'POST', body: JSON.stringify({ note }),
    }),

  getAudit: (caseId: string) => request<AuditEventSummary[]>(`/cases/${caseId}/audit`),
  getEvaluation: (caseId: string) => request<EvaluationResult>(`/cases/${caseId}/evaluation`),
  getIntegrationSummary: (caseId: string) => request<IntegrationSummary>(`/cases/${caseId}/integration-summary`),

  listDocuments: (caseId: string) => request<DocumentSummary[]>(`/cases/${caseId}/documents`),
  uploadDocument: (caseId: string, file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request<DocumentSummary>(`/cases/${caseId}/documents`, { method: 'POST', body: form })
  },
  processDocument: (documentId: string) =>
    request<PipelineRunSummary>(`/documents/${documentId}/process`, { method: 'POST' }),

  getEvidenceHistory: (evidenceId: string) => request<EvidenceVersionEntry[]>(`/evidence/${evidenceId}/history`),
  getCaseTimeMachine: (caseId: string, at: string) =>
    request<{ case_id: string; as_of: string; evidence_states: Record<string, unknown>[] }>(
      `/cases/${caseId}/time-machine?at=${encodeURIComponent(at)}`
    ),
}
