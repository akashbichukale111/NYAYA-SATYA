import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { endpoints } from '../lib/api'
import { PackageHeader, usePackageId } from './FilingPackageTabs'

export function ReviewQueueTab() {
  const packageId = usePackageId()
  const queryClient = useQueryClient()
  const [reasons, setReasons] = useState<Record<string, string>>({})

  const queueQuery = useQuery({
    queryKey: ['review-queue', packageId],
    queryFn: () => endpoints.getReviewQueue(packageId),
  })

  const approve = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) => endpoints.approveReview(id, reason || undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['review-queue', packageId] })
      queryClient.invalidateQueries({ queryKey: ['defects', packageId] })
      queryClient.invalidateQueries({ queryKey: ['audit', packageId] })
    },
  })
  const reject = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) => endpoints.rejectReview(id, reason || undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['review-queue', packageId] })
      queryClient.invalidateQueries({ queryKey: ['defects', packageId] })
      queryClient.invalidateQueries({ queryKey: ['audit', packageId] })
    },
  })

  return (
    <div>
      <PackageHeader title="Review Queue" />
      <p className="mb-4 -mt-4 text-sm text-[var(--color-ink-500)]">
        Every automatically detected defect requires a human decision before it counts as confirmed
        or dismissed. Approving or rejecting here is recorded permanently in the audit trail.
      </p>

      <div className="divide-y divide-[var(--color-ink-200)] rounded-lg border border-[var(--color-ink-200)] bg-white">
        {(queueQuery.data ?? []).map((task) => (
          <div key={task.id} className="px-4 py-3">
            <div className="mb-2 text-sm text-[var(--color-ink-900)]">
              {task.action_requested.replaceAll('_', ' ').toLowerCase()} — {task.target_type} {task.target_id.slice(0, 12)}…
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <input
                placeholder="Reason (optional)"
                value={reasons[task.id] ?? ''}
                onChange={(e) => setReasons((r) => ({ ...r, [task.id]: e.target.value }))}
                className="flex-1 rounded border border-[var(--color-ink-300)] px-2 py-1 text-sm outline-none focus:border-[var(--color-accent-500)]"
              />
              <button
                onClick={() => approve.mutate({ id: task.id, reason: reasons[task.id] ?? '' })}
                className="rounded bg-[var(--color-ok-600)] px-3 py-1 text-xs font-medium text-white hover:opacity-90"
              >
                Approve / Confirm
              </button>
              <button
                onClick={() => reject.mutate({ id: task.id, reason: reasons[task.id] ?? '' })}
                className="rounded bg-[var(--color-ink-500)] px-3 py-1 text-xs font-medium text-white hover:opacity-90"
              >
                Reject
              </button>
            </div>
          </div>
        ))}
        {queueQuery.data?.length === 0 && (
          <div className="px-4 py-6 text-center text-sm text-[var(--color-ink-400)]">
            Nothing pending review.
          </div>
        )}
      </div>
    </div>
  )
}

export function AuditTab() {
  const packageId = usePackageId()
  const auditQuery = useQuery({ queryKey: ['audit', packageId], queryFn: () => endpoints.getAuditTrail(packageId) })

  return (
    <div>
      <PackageHeader title="Audit" />
      <div className="divide-y divide-[var(--color-ink-200)] rounded-lg border border-[var(--color-ink-200)] bg-white font-mono text-xs">
        {(auditQuery.data ?? []).map((event) => (
          <div key={event.id} className="flex items-start justify-between gap-4 px-4 py-2">
            <div>
              <span className="text-[var(--color-ink-900)]">{event.action}</span>
              {event.entity_type && (
                <span className="text-[var(--color-ink-400)]"> · {event.entity_type}</span>
              )}
              {event.reason && <div className="text-[var(--color-ink-500)]">reason: {event.reason}</div>}
            </div>
            <div className="whitespace-nowrap text-[var(--color-ink-400)]">
              {event.actor_role ?? 'system'} · {new Date(event.timestamp).toLocaleString()}
            </div>
          </div>
        ))}
        {auditQuery.data?.length === 0 && (
          <div className="px-4 py-6 text-center text-sm text-[var(--color-ink-400)]">
            No audit events recorded yet.
          </div>
        )}
      </div>
    </div>
  )
}
