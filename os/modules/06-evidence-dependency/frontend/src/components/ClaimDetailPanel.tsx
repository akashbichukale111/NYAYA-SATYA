import { useQuery } from '@tanstack/react-query'
import { api } from '../api'
import { Card, LoadingState, ErrorState, StatusPill } from './primitives'

export function ClaimDetailPanel({ claimId }: { claimId: string }) {
  const impact = useQuery({ queryKey: ['claim-impact', claimId], queryFn: () => api.getClaimImpact(claimId) })

  return (
    <Card>
      <h3 className="mb-3 text-xs font-medium uppercase tracking-wider text-parchment-200/40">Dependency impact</h3>
      {impact.isLoading && <LoadingState />}
      {impact.isError && <ErrorState error={impact.error} />}
      {impact.data && (
        <div className="space-y-2 text-sm">
          <Row label="Criticality"><StatusPill label={impact.data.criticality} /></Row>
          <Row label="Affected issues"><span>{impact.data.affected_issues.length}</span></Row>
          <Row label="Human review required"><span>{impact.data.human_review_required ? 'Yes' : 'No'}</span></Row>
        </div>
      )}
      <p className="mt-3 text-xs italic text-parchment-200/40">
        This shows what depends on this claim right now — not a legal conclusion about whether the claim is true.
      </p>
    </Card>
  )
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <dt className="text-parchment-200/50">{label}</dt>
      <dd>{children}</dd>
    </div>
  )
}
