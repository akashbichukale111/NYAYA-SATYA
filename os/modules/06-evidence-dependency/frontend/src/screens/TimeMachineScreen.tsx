import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api'
import { useEvidence } from '../hooks'
import { Card, SectionHeading, LoadingState, ErrorState, EmptyState } from '../components/primitives'

export function TimeMachineScreen({ caseId }: { caseId: string }) {
  const evidence = useEvidence(caseId)
  const [timestamp, setTimestamp] = useState(() => new Date().toISOString().slice(0, 16))

  const snapshot = useQuery({
    queryKey: ['time-machine', caseId, timestamp],
    queryFn: () => api.getCaseTimeMachine(caseId, new Date(timestamp).toISOString()),
    enabled: !!timestamp,
  })

  return (
    <div className="space-y-6">
      <SectionHeading
        title="Time Machine"
        subtitle="Reconstructs case state from real, append-only evidence version snapshots — nothing here is simulated or guessed."
      />

      <Card className="flex items-center gap-3">
        <label className="text-xs text-parchment-200/50">Reconstruct case as of</label>
        <input
          type="datetime-local"
          value={timestamp}
          onChange={(e) => setTimestamp(e.target.value)}
          className="focus-ring rounded-md border border-ink-600 bg-ink-800 px-2 py-1.5 text-xs text-parchment-100"
        />
        <button
          onClick={() => setTimestamp(new Date().toISOString().slice(0, 16))}
          className="focus-ring rounded-md border border-ink-600 px-2 py-1.5 text-xs text-parchment-200/70 hover:border-ink-500"
        >
          Now
        </button>
      </Card>

      {snapshot.isLoading && <LoadingState />}
      {snapshot.isError && <ErrorState error={snapshot.error} />}
      {snapshot.data && (
        <div>
          <p className="mb-3 text-xs text-parchment-200/40">
            {snapshot.data.evidence_states.length} evidence item(s) existed as of {new Date(snapshot.data.as_of).toLocaleString()}
          </p>
          {snapshot.data.evidence_states.length === 0 ? (
            <EmptyState title="No evidence existed at this point in time." />
          ) : (
            <div className="space-y-2">
              {snapshot.data.evidence_states.map((s: Record<string, unknown>) => {
                const snap = s.snapshot as Record<string, unknown>
                return (
                  <Card key={s.evidence_id as string}>
                    <p className="text-sm text-parchment-100">{snap.label as string}</p>
                    <p className="mt-1 font-mono text-xs text-parchment-200/40">
                      v{s.version_number as number} · {snap.verification_status as string} · {snap.state as string}
                    </p>
                  </Card>
                )
              })}
            </div>
          )}
        </div>
      )}

      <div>
        <h3 className="mb-2 text-xs font-medium uppercase tracking-wider text-parchment-200/40">
          Browse full history per evidence item
        </h3>
        {evidence.isLoading && <LoadingState />}
        {evidence.data && (
          <div className="grid gap-2 sm:grid-cols-2">
            {evidence.data.map((ev) => (
              <EvidenceHistoryMini key={ev.id} evidenceId={ev.id} label={ev.label} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function EvidenceHistoryMini({ evidenceId, label }: { evidenceId: string; label: string }) {
  const history = useQuery({ queryKey: ['mini-history', evidenceId], queryFn: () => api.getEvidenceHistory(evidenceId) })
  return (
    <Card>
      <p className="truncate text-xs text-parchment-100">{label}</p>
      <p className="mt-1 text-xs text-parchment-200/40">
        {history.data ? `${history.data.length} version(s)` : '…'}
      </p>
    </Card>
  )
}
