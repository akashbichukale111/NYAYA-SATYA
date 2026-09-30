import { useState } from 'react'
import { useClaims } from '../hooks'
import { Card, SectionHeading, LoadingState, ErrorState, EmptyState, StatusPill } from '../components/primitives'
import { ClaimDetailPanel } from '../components/ClaimDetailPanel'

export function ClaimsExplorer({ caseId }: { caseId: string }) {
  const claims = useClaims(caseId)
  const [selectedId, setSelectedId] = useState<string | null>(null)

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_380px]">
      <div>
        <SectionHeading title="Claims" subtitle="Factual propositions and the evidence behind them." />
        {claims.isLoading && <LoadingState />}
        {claims.isError && <ErrorState error={claims.error} />}
        {claims.data && claims.data.length === 0 && (
          <EmptyState title="No claims yet." hint="Claims appear from the extraction pipeline or manual entry." />
        )}
        {claims.data && claims.data.length > 0 && (
          <div className="space-y-2">
            {claims.data.map((c) => (
              <button
                key={c.id}
                onClick={() => setSelectedId(c.id)}
                className={`focus-ring block w-full rounded-lg border px-4 py-3 text-left transition ${
                  selectedId === c.id ? 'border-parchment-200/50 bg-ink-800' : 'border-ink-700 bg-ink-900/60 hover:border-ink-600'
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <p className="text-sm text-parchment-100">{c.text}</p>
                  <StatusPill label={c.verification_status} />
                </div>
                <p className="mt-1 text-xs text-parchment-200/40">{c.source}</p>
              </button>
            ))}
          </div>
        )}
      </div>
      <div>
        {selectedId ? (
          <ClaimDetailPanel claimId={selectedId} />
        ) : (
          <Card><EmptyState title="Select a claim" hint="Its supporting evidence and impact will appear here." /></Card>
        )}
      </div>
    </div>
  )
}
