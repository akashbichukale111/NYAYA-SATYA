import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { endpoints } from '../lib/api'
import { lifecycleStateLabel } from '../lib/status'
import { Badge } from '../components/Badge'

export function CasesPage() {
  const queryClient = useQueryClient()
  const casesQuery = useQuery({ queryKey: ['cases'], queryFn: endpoints.listCases })
  const [title, setTitle] = useState('')
  const [reference, setReference] = useState('')

  const createCase = useMutation({
    mutationFn: () => endpoints.createCase(title.trim(), reference.trim() || undefined),
    onSuccess: () => {
      setTitle('')
      setReference('')
      queryClient.invalidateQueries({ queryKey: ['cases'] })
    },
  })

  return (
    <div className="mx-auto max-w-4xl px-8 py-8">
      <h1 className="mb-1 text-xl font-semibold text-[var(--color-ink-900)]">Cases</h1>
      <p className="mb-6 text-sm text-[var(--color-ink-500)]">
        Each case can hold one or more filing packages. Case data is strictly isolated — you can
        only see cases you own, unless you are signed in as Admin.
      </p>

      <form
        onSubmit={(e) => {
          e.preventDefault()
          if (title.trim()) createCase.mutate()
        }}
        className="mb-8 flex flex-wrap items-end gap-3 rounded-lg border border-[var(--color-ink-200)] bg-white p-4"
      >
        <label className="flex-1 text-sm text-[var(--color-ink-600)]">
          Case title
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
            placeholder="e.g. Kumar v. State Registry"
            className="mt-1 w-full rounded border border-[var(--color-ink-300)] px-3 py-1.5 text-sm outline-none focus:border-[var(--color-accent-500)]"
          />
        </label>
        <label className="text-sm text-[var(--color-ink-600)]">
          Case reference (optional)
          <input
            value={reference}
            onChange={(e) => setReference(e.target.value)}
            placeholder="e.g. 2026/CIV/0042"
            className="mt-1 w-48 rounded border border-[var(--color-ink-300)] px-3 py-1.5 text-sm outline-none focus:border-[var(--color-accent-500)]"
          />
        </label>
        <button
          type="submit"
          disabled={createCase.isPending}
          className="rounded bg-[var(--color-ink-900)] px-3 py-1.5 text-sm font-medium text-white hover:bg-[var(--color-ink-800)] disabled:opacity-50"
        >
          {createCase.isPending ? 'Creating…' : 'Create case'}
        </button>
      </form>

      <div className="divide-y divide-[var(--color-ink-200)] rounded-lg border border-[var(--color-ink-200)] bg-white">
        {(casesQuery.data ?? []).map((c) => (
          <Link
            key={c.id}
            to={`/cases/${c.id}`}
            className="flex items-center justify-between gap-3 px-4 py-3 hover:bg-[var(--color-ink-50)]"
          >
            <div>
              <div className="flex items-center gap-2">
                <span className="font-medium text-[var(--color-ink-900)]">{c.title}</span>
                {c.is_demo && (
                  <Badge className="border-[var(--color-review-700)]/30 bg-[var(--color-review-100)] text-[var(--color-review-700)]">
                    DEMO
                  </Badge>
                )}
              </div>
              {c.case_reference && (
                <div className="font-mono text-xs text-[var(--color-ink-500)]">{c.case_reference}</div>
              )}
            </div>
            <span className="text-xs text-[var(--color-ink-500)]">{lifecycleStateLabel(c.status)}</span>
          </Link>
        ))}
        {casesQuery.data?.length === 0 && (
          <div className="px-4 py-6 text-center text-sm text-[var(--color-ink-400)]">No cases yet.</div>
        )}
      </div>
    </div>
  )
}
