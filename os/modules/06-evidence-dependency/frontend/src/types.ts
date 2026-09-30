export interface Case {
  id: string
  title: string
  description: string
  is_demo: boolean
  status: string
  created_at: string
  updated_at: string
}

export interface EvidenceItem {
  id: string
  case_id: string
  document_id: string | null
  label: string
  source_text: string
  page_number: number | null
  section: string | null
  source_location_known: boolean
  extraction_method: string
  state: string
  verification_status: string
  created_at: string
  updated_at: string
}

export interface Claim {
  id: string
  case_id: string
  text: string
  source: string
  verification_status: string
  created_at: string
  updated_at: string
}

export interface Issue {
  id: string
  case_id: string
  question: string
  description: string
  status: string
  created_at: string
  updated_at: string
}

export interface RelationshipEdge {
  id: string
  case_id: string
  source_type: 'EVIDENCE' | 'CLAIM' | 'ISSUE'
  source_id: string
  target_type: 'EVIDENCE' | 'CLAIM' | 'ISSUE'
  target_id: string
  relationship_type: string
  support_kind: string | null
  verification_status: string
  is_active: boolean
  created_at: string
}

export interface GraphNode {
  id: string
  type: 'EVIDENCE' | 'CLAIM' | 'ISSUE'
  label: string
  state?: string
  status?: string
  verification_status?: string
}

export interface GraphEdge {
  id: string
  source: string
  target: string
  relationship_type: string
  support_kind: string | null
  verification_status: string
}

export interface DependencyGraph {
  case_id: string
  nodes: GraphNode[]
  edges: GraphEdge[]
}

export interface CoverageMetrics {
  claims_total: number
  claims_with_evidence: number
  claims_without_evidence: number
  issues_total: number
  issues_with_supporting_claims: number
  unsupported_issues: number
  conflicting_claims: number
  single_source_claims: number
  verified_evidence_items: number
  unverified_evidence_items: number
  evidence_items_total: number
}

export interface FragilityEntry {
  evidence_id: string
  label: string
  affected_claims: string[]
  affected_issues: string[]
  dependency_count: number
  criticality: 'NONE' | 'LOW' | 'MODERATE' | 'SINGLE_POINT_DEPENDENCY'
}

export interface MissingEvidenceReport {
  claims_without_evidence: { claim_id: string; text: string }[]
  claims_with_only_conflicting_evidence: { claim_id: string; text: string }[]
  claims_with_single_source_only: { claim_id: string; text: string }[]
  issues_without_supporting_claims: { issue_id: string; question: string }[]
}

export interface ImpactResult {
  node_type: string
  node_id: string
  affected_claims: string[]
  affected_issues: string[]
  criticality: string
  human_review_required: boolean
}

export interface CrashTestResult {
  id: string
  case_id: string
  event_type: string
  target_type: string
  target_id: string
  before_state: Record<string, unknown>
  after_state: Record<string, unknown>
  affected_claims: string[]
  affected_issues: string[]
  new_gaps: { type: string; [key: string]: unknown }[]
  new_conflicts: { type: string; [key: string]: unknown }[]
  criticality: string
  human_review_required: boolean
  note: string
}

export interface ReviewTaskSummary {
  id: string
  action_type: string
  target_type: string
  target_id: string
  proposed_change: Record<string, unknown>
  proposing_agent: string
  status: string
  created_at: string
}

export interface AuditEventSummary {
  id: string
  actor: string
  actor_type: string
  action: string
  target_type: string | null
  target_id: string | null
  detail: Record<string, unknown>
  created_at: string
}

export interface EvaluationResult {
  case_id: string
  checks: Record<string, 'PASS' | 'FAIL' | 'NOT_RUN'>
  summary: { pass_count: number; fail_count: number; not_run_count: number }
}

export interface IntegrationSummary {
  case_id: string
  evidence_count: number
  claim_count: number
  issue_count: number
  unsupported_claims: number
  unsupported_issues: number
  conflicting_claims: number
  critical_dependencies: Record<string, unknown>[]
  impact_items: Record<string, unknown>[]
  verification_pending: number
  provenance_refs: string[]
  attention_items: Record<string, unknown>[]
  last_updated: string
}

export interface DocumentSummary {
  id: string
  case_id: string
  filename: string
  mime_type: string | null
  file_size_bytes: number | null
  sha256_hash: string
  document_type: string
  status: string
  created_at: string
}

export interface PipelineRunSummary {
  ok: boolean
  document_id: string
  case_id: string
  evidence_created: string[]
  claims_created: string[]
  issue_mapping_review_tasks: string[]
  relationships_upgraded: string[]
  conflicts_flagged: string[]
  verification_review_tasks: string[]
  coverage_after: CoverageMetrics
}

export interface EvidenceVersionEntry {
  version_number: number
  as_of: string
  reason: string
  snapshot: Record<string, unknown>
}
