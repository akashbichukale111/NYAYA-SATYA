import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './api'

export function useCases() {
  return useQuery({ queryKey: ['cases'], queryFn: api.listCases })
}

export function useCase(caseId: string | null) {
  return useQuery({
    queryKey: ['case', caseId],
    queryFn: () => api.getCase(caseId as string),
    enabled: !!caseId,
  })
}

export function useEvidence(caseId: string | null) {
  return useQuery({
    queryKey: ['evidence', caseId],
    queryFn: () => api.listEvidence(caseId as string),
    enabled: !!caseId,
  })
}

export function useClaims(caseId: string | null) {
  return useQuery({
    queryKey: ['claims', caseId],
    queryFn: () => api.listClaims(caseId as string),
    enabled: !!caseId,
  })
}

export function useIssues(caseId: string | null) {
  return useQuery({
    queryKey: ['issues', caseId],
    queryFn: () => api.listIssues(caseId as string),
    enabled: !!caseId,
  })
}

export function useRelationships(caseId: string | null) {
  return useQuery({
    queryKey: ['relationships', caseId],
    queryFn: () => api.listRelationships(caseId as string),
    enabled: !!caseId,
  })
}

export function useDependencyGraph(caseId: string | null) {
  return useQuery({
    queryKey: ['dependency-graph', caseId],
    queryFn: () => api.getDependencyGraph(caseId as string),
    enabled: !!caseId,
  })
}

export function useCoverage(caseId: string | null) {
  return useQuery({
    queryKey: ['coverage', caseId],
    queryFn: () => api.getCoverage(caseId as string),
    enabled: !!caseId,
  })
}

export function useFragility(caseId: string | null) {
  return useQuery({
    queryKey: ['fragility', caseId],
    queryFn: () => api.getFragility(caseId as string),
    enabled: !!caseId,
  })
}

export function useMissingEvidence(caseId: string | null) {
  return useQuery({
    queryKey: ['missing-evidence', caseId],
    queryFn: () => api.getMissingEvidence(caseId as string),
    enabled: !!caseId,
  })
}

export function useReviewQueue(caseId: string | null) {
  return useQuery({
    queryKey: ['review-queue', caseId],
    queryFn: () => api.getReviewQueue(caseId as string),
    enabled: !!caseId,
    refetchInterval: 5000,
  })
}

export function useAudit(caseId: string | null) {
  return useQuery({
    queryKey: ['audit', caseId],
    queryFn: () => api.getAudit(caseId as string),
    enabled: !!caseId,
  })
}

export function useEvaluation(caseId: string | null) {
  return useQuery({
    queryKey: ['evaluation', caseId],
    queryFn: () => api.getEvaluation(caseId as string),
    enabled: !!caseId,
  })
}

export function useIntegrationSummary(caseId: string | null) {
  return useQuery({
    queryKey: ['integration-summary', caseId],
    queryFn: () => api.getIntegrationSummary(caseId as string),
    enabled: !!caseId,
  })
}

export function useDocuments(caseId: string | null) {
  return useQuery({
    queryKey: ['documents', caseId],
    queryFn: () => api.listDocuments(caseId as string),
    enabled: !!caseId,
  })
}

export function useCreateCase() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ title, description }: { title: string; description?: string }) =>
      api.createCase(title, description),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['cases'] }),
  })
}

export function useSeedDemo() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (key: 'A' | 'B' | 'C') => api.seedDemo(key),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['cases'] }),
  })
}

export function useUploadDocument(caseId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (file: File) => api.uploadDocument(caseId, file),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['documents', caseId] }),
  })
}

export function useProcessDocument(caseId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (documentId: string) => api.processDocument(documentId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['documents', caseId] })
      qc.invalidateQueries({ queryKey: ['evidence', caseId] })
      qc.invalidateQueries({ queryKey: ['claims', caseId] })
      qc.invalidateQueries({ queryKey: ['dependency-graph', caseId] })
      qc.invalidateQueries({ queryKey: ['coverage', caseId] })
      qc.invalidateQueries({ queryKey: ['fragility', caseId] })
      qc.invalidateQueries({ queryKey: ['review-queue', caseId] })
      qc.invalidateQueries({ queryKey: ['audit', caseId] })
    },
  })
}

export function useRunCrashTest(caseId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ evidenceId, eventType }: { evidenceId: string; eventType: string }) =>
      api.runCrashTest(evidenceId, eventType),
    onSuccess: () => {
      // Crash tests are non-destructive simulations, but the run itself
      // is auditable, so refresh the audit trail view.
      qc.invalidateQueries({ queryKey: ['audit', caseId] })
    },
  })
}

export function useReviewDecision(caseId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ reviewId, approve, note }: { reviewId: string; approve: boolean; note?: string }) =>
      approve ? api.approveReview(reviewId, note) : api.rejectReview(reviewId, note),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['review-queue', caseId] })
      qc.invalidateQueries({ queryKey: ['evidence', caseId] })
      qc.invalidateQueries({ queryKey: ['claims', caseId] })
      qc.invalidateQueries({ queryKey: ['relationships', caseId] })
      qc.invalidateQueries({ queryKey: ['dependency-graph', caseId] })
      qc.invalidateQueries({ queryKey: ['coverage', caseId] })
      qc.invalidateQueries({ queryKey: ['audit', caseId] })
    },
  })
}
