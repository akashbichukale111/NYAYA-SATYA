import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export function setUserId(userId: string | null) {
  if (userId) {
    api.defaults.headers.common['X-User-Id'] = userId
  } else {
    delete api.defaults.headers.common['X-User-Id']
  }
}

// ---- Types (mirrors backend/app/schemas.py) ----

export interface Case {
  id: string
  title: string
  case_reference: string | null
  status: string
  is_demo: boolean
  created_at: string
  updated_at: string
}

export interface FilingPackage {
  id: string
  case_id: string
  name: string
  lifecycle_state: string
  created_at: string
  updated_at: string
}

export interface Requirement {
  id: string
  case_id: string
  filing_package_id: string
  requirement_type: string
  description: string
  source: string
  source_reference: string | null
  version: number
  status: string
  verification_status: string
  target_reference_label: string | null
  jurisdiction: string | null
  effective_from: string | null
  effective_until: string | null
}

export interface DocumentRow {
  id: string
  case_id: string
  filing_package_id: string
  display_name: string
  document_kind: string | null
  status: string
  current_version_id: string | null
}

export interface DocumentVersion {
  id: string
  document_id: string
  version_number: number
  original_filename: string
  mime_type: string | null
  detected_format: string | null
  size_bytes: number
  sha256: string | null
  extraction_status: string
  extraction_error: string | null
  page_count: number | null
  quarantined: boolean
  quarantine_reason: string | null
  source_location_known: boolean
}

export interface ChecklistItem {
  id: string
  requirement_id: string
  status: string
  source: string | null
  document_refs: string[]
  evidence_refs: unknown[]
  verification: string
  review_state: string
  explanation: string | null
}

export interface Defect {
  id: string
  case_id: string
  filing_package_id: string
  defect_type: string
  category: string
  severity: string
  status: string
  description: string
  source_refs: unknown[]
  document_refs: string[]
  requirement_refs: string[]
  detected_by: string
  detected_at: string
  verification_status: string
  human_review_required: boolean
  resolution_note: string | null
}

export interface Objection {
  id: string
  case_id: string
  filing_package_id: string
  original_text: string
  source_reference: string | null
  status: string
  linked_defect_id: string | null
}

export interface Correction {
  id: string
  case_id: string
  filing_package_id: string
  defect_id: string | null
  objection_id: string | null
  description: string
  suggested_action: string | null
  status: string
}

export interface ReviewTask {
  id: string
  case_id: string
  target_type: string
  target_id: string
  action_requested: string
  decision: string
  reason: string | null
}

export interface AuditEvent {
  id: string
  actor_user_id: string | null
  actor_role: string | null
  action: string
  entity_type: string | null
  entity_id: string | null
  reason: string | null
  timestamp: string
}

export interface PrecheckResult {
  filing_package_id: string
  new_defect_count: number
  open_defect_count: number
  lifecycle_state: string
}

export interface NyayaSatyaSummary {
  case_id: string
  filing_packages: number
  open_defects: number
  high_attention_defects: number
  missing_documents: unknown[]
  missing_references: unknown[]
  metadata_conflicts: unknown[]
  duplicate_groups: unknown[]
  open_objections: unknown[]
  corrections_pending: unknown[]
  verification_pending: unknown[]
  blocked_workflows: unknown[]
  attention_items: unknown[]
  provenance_refs: unknown[]
  last_updated: string
}

// ---- Endpoints ----

export const endpoints = {
  seedDemo: () => api.post('/demo/seed').then((r) => r.data as { marker: string; demo_case_ids: string[] }),

  createUser: (name: string, email: string, role: string) =>
    api.post('/users', { name, email, role }).then((r) => r.data as { id: string; name: string; email: string; role: string }),

  listCases: () => api.get('/cases').then((r) => r.data as Case[]),
  getCase: (caseId: string) => api.get(`/cases/${caseId}`).then((r) => r.data as Case),
  createCase: (title: string, case_reference?: string) =>
    api.post('/cases', { title, case_reference }).then((r) => r.data as Case),

  listFilingPackages: (caseId: string) =>
    api.get(`/cases/${caseId}/filing-packages`).then((r) => r.data as FilingPackage[]),
  createFilingPackage: (caseId: string, name: string) =>
    api.post(`/cases/${caseId}/filing-packages`, { name }).then((r) => r.data as FilingPackage),

  listDocuments: (packageId: string) =>
    api.get(`/filing-packages/${packageId}/documents`).then((r) => r.data as DocumentRow[]),
  listDocumentVersions: (documentId: string) =>
    api.get(`/documents/${documentId}/versions`).then((r) => r.data as DocumentVersion[]),
  uploadDocument: (packageId: string, file: File, displayName: string, documentKind?: string) => {
    const form = new FormData()
    form.append('display_name', displayName)
    if (documentKind) form.append('document_kind', documentKind)
    form.append('file', file)
    return api
      .post(`/filing-packages/${packageId}/documents`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      .then((r) => r.data as DocumentRow)
  },

  listRequirements: (packageId: string) =>
    api.get(`/filing-packages/${packageId}/requirements`).then((r) => r.data as Requirement[]),
  createRequirement: (packageId: string, payload: Partial<Requirement> & { requirement_type: string; description: string; source: string }) =>
    api.post(`/filing-packages/${packageId}/requirements`, payload).then((r) => r.data as Requirement),

  getChecklist: (packageId: string) =>
    api.get(`/filing-packages/${packageId}/checklist`).then((r) => r.data as ChecklistItem[]),

  runPrecheck: (packageId: string) =>
    api.post(`/filing-packages/${packageId}/precheck`).then((r) => r.data as PrecheckResult),

  listDefects: (packageId: string) =>
    api.get(`/filing-packages/${packageId}/defects`).then((r) => r.data as Defect[]),
  getDefect: (defectId: string) => api.get(`/defects/${defectId}`).then((r) => r.data as Defect),

  listObjections: (packageId: string) =>
    api.get(`/filing-packages/${packageId}/objections`).then((r) => r.data as Objection[]),
  createObjection: (packageId: string, original_text: string, source_reference?: string) =>
    api.post(`/filing-packages/${packageId}/objections`, { original_text, source_reference }).then((r) => r.data as Objection),

  listCorrections: (packageId: string) =>
    api.get(`/filing-packages/${packageId}/corrections`).then((r) => r.data as Correction[]),
  createCorrection: (packageId: string, payload: { defect_id?: string; objection_id?: string; description: string; suggested_action?: string }) =>
    api.post(`/filing-packages/${packageId}/corrections`, payload).then((r) => r.data as Correction),

  getReviewQueue: (packageId: string) =>
    api.get(`/filing-packages/${packageId}/review-queue`).then((r) => r.data as ReviewTask[]),
  approveReview: (reviewId: string, reason?: string) =>
    api.post(`/reviews/${reviewId}/approve`, { reason }).then((r) => r.data as ReviewTask),
  rejectReview: (reviewId: string, reason?: string) =>
    api.post(`/reviews/${reviewId}/reject`, { reason }).then((r) => r.data as ReviewTask),

  getAuditTrail: (packageId: string) =>
    api.get(`/filing-packages/${packageId}/audit`).then((r) => r.data as AuditEvent[]),

  getNyayaSatyaSummary: (caseId: string) =>
    api.get(`/integration/nyaya-satya/cases/${caseId}/summary`).then((r) => r.data as NyayaSatyaSummary),
}

export default api
