import { useState } from 'react'
import { useReviewQueue, useReviewDecision } from '../hooks'
import { Card, SectionHeading, LoadingState, ErrorState, EmptyState, StatusPill } from '../components/primitives'

export function ReviewQueueScreen({ caseId }: { caseId: string }) {
  const queue = useReviewQueue(caseId)
  const decide = useReviewDecision(caseId)
  const [notes, setNotes] = useState<Record<string, string>>({})

  const pending = queue.data?.filter((t) => t.status === 'PENDING') ?? []
  const decided = queue.data?.filter((t) => t.status !== 'PENDING') ?? []

  return (
    <div className="space-y-6">
      <SectionHeading
        title="Human Legal Gate — Review Queue"
        subtitle="Every consequential, real change (verification, exclusion, a proposed relationship, an issue mapping) waits here for a human decision. Approving requires Advocate role or higher."
      />

      {queue.isLoading && <LoadingState />}
      {queue.isError && <ErrorState error={queue.error} />}

      <div>
        <h3 className="mb-2 text-xs font-medium uppercase tracking-wider text-parchment-200/40">
          Pending ({pending.length})
        </h3>
        {pending.length === 0 && <EmptyState title="Nothing pending." />}
        <div className="space-y-3">
          {pending.map((task) => (
            <Card key={task.id}>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm text-parchment-100">{task.action_type.replace(/_/g, ' ')}</p>
                  <p className="mt-0.5 text-xs text-parchment-200/40">
                    proposed by <span className="font-mono">{task.proposing_agent}</span> · target: {task.target_type}
                  </p>
                </div>
                <StatusPill label={task.status} />
              </div>
              <pre className="mt-2 overflow-x-auto rounded-md bg-ink-950/60 p-2 text-xs text-parchment-200/60">
                {JSON.stringify(task.proposed_change, null, 2)}
              </pre>
              <div className="mt-3 flex items-center gap-2">
                <input
                  placeholder="Decision note (optional)"
                  value={notes[task.id] ?? ''}
                  onChange={(e) => setNotes((n) => ({ ...n, [task.id]: e.target.value }))}
                  className="focus-ring flex-1 rounded-md border border-ink-600 bg-ink-800 px-2 py-1.5 text-xs text-parchment-100 placeholder:text-parchment-200/30"
                />
                <button
                  onClick={() => decide.mutate({ reviewId: task.id, approve: true, note: notes[task.id] })}
                  disabled={decide.isPending}
                  className="focus-ring rounded-md border border-signal-verified/40 bg-signal-verified/10 px-3 py-1.5 text-xs font-medium text-signal-verified hover:bg-signal-verified/20 disabled:opacity-50"
                >
                  Approve
                </button>
                <button
                  onClick={() => decide.mutate({ reviewId: task.id, approve: false, note: notes[task.id] })}
                  disabled={decide.isPending}
                  className="focus-ring rounded-md border border-signal-conflict/40 bg-signal-conflict/10 px-3 py-1.5 text-xs font-medium text-signal-conflict hover:bg-signal-conflict/20 disabled:opacity-50"
                >
                  Reject
                </button>
              </div>
            </Card>
          ))}
        </div>
      </div>

      {decided.length > 0 && (
        <div>
          <h3 className="mb-2 text-xs font-medium uppercase tracking-wider text-parchment-200/40">
            Decided ({decided.length})
          </h3>
          <div className="space-y-1.5">
            {decided.map((task) => (
              <div key={task.id} className="flex items-center justify-between rounded-md border border-ink-700 bg-ink-900/40 px-3 py-2 text-xs">
                <span className="text-parchment-200/70">{task.action_type.replace(/_/g, ' ')}</span>
                <StatusPill label={task.status} />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
