import { useAudit } from '../hooks'
import { SectionHeading, LoadingState, ErrorState, EmptyState } from '../components/primitives'

const ACTOR_TYPE_COLOR: Record<string, string> = {
  USER: 'text-signal-verified',
  AGENT: 'text-signal-review',
  SYSTEM: 'text-parchment-200/50',
}

export function AuditScreen({ caseId }: { caseId: string }) {
  const audit = useAudit(caseId)

  return (
    <div>
      <SectionHeading
        title="Audit Timeline"
        subtitle="Append-only. Nothing here is ever edited or deleted — every proposal, approval, rejection, and agent action is recorded."
      />
      {audit.isLoading && <LoadingState />}
      {audit.isError && <ErrorState error={audit.error} />}
      {audit.data && audit.data.length === 0 && <EmptyState title="No events recorded yet." />}
      {audit.data && audit.data.length > 0 && (
        <ol className="space-y-0 border-l border-ink-700 pl-4">
          {audit.data.map((e) => (
            <li key={e.id} className="relative pb-4">
              <span className="absolute -left-[21px] top-1 h-2.5 w-2.5 rounded-full border-2 border-ink-950 bg-ink-600" />
              <div className="flex items-center gap-2 text-xs">
                <span className={`font-mono font-medium ${ACTOR_TYPE_COLOR[e.actor_type] ?? 'text-parchment-200/50'}`}>
                  {e.actor}
                </span>
                <span className="text-parchment-200/30">·</span>
                <span className="text-parchment-100">{e.action.replace(/_/g, ' ').toLowerCase()}</span>
                {e.target_type && <span className="text-parchment-200/30">({e.target_type})</span>}
              </div>
              <p className="mt-0.5 font-mono text-[11px] text-parchment-200/30">
                {new Date(e.created_at).toLocaleString()}
              </p>
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}
