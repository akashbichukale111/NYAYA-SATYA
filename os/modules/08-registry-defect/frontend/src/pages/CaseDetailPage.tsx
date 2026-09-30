import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { endpoints } from '../lib/api'
import { lifecycleStateLabel } from '../lib/status'
import { Badge } from '../components/Badge'

export function CaseDetailPage() {
  const { caseId } = useParams<{ caseId: string }>()
  const queryClient = useQueryClient()
  const [name, setName] = useState('')

  const caseQuery = useQuery({
    queryKey: ['case', caseId],
    queryFn: () => endpoints.getCase(caseId!),
    enabled: !!caseId,
  })
  const packagesQuery = useQuery({
    queryKey: ['filing-packages', caseId],
    queryFn: () => endpoints.listFilingPackages(caseId!),
    enabled: !!caseId,
  })
  const summaryQuery = useQuery({
    queryKey: ['nyaya-summary', caseId],
    queryFn: () => endpoints.getNyayaSatyaSummary(caseId!),
    enabled: !!caseId,
  })

  const createPackage = useMutation({
    mutationFn: () => endpoints.createFilingPackage(caseId!, name.trim()),
    onSuccess: () => {
      setName('')
      queryClient.invalidateQueries({ queryKey: ['filing-packages', caseId] })
    },
  })

  if (!caseId) return null
  const kase = caseQuery.data

  return (
    <div className="mx-auto max-w-4xl px-8 py-8">
      {kase?.is_demo && (
        <div className="mb-4">
          <Badge className="border-[var(--color-review-700)]/30 bg-[var(--color-review-100)] text-[var(--color-review-700)]">
            DEMONSTRATION DATA — NOT A REAL CASE
          </Badge>
        </div>
      )}
      <h1 className="text-xl font-semibold text-[var(--color-ink-900)]">{kase?.title ?? 'Loading…'}</h1>
      {kase?.case_reference && (
        <div className="mt-0.5 font-mono text-xs text-[var(--color-ink-500)]">{kase.case_reference}</div>
      )}

      {summaryQuery.data && (
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatTile label="Filing packages" value={summaryQuery.data.filing_packages} />
          <StatTile label="Open defects" value={summaryQuery.data.open_defects} />
          <StatTile
            label="High-attention defects"
            value={summaryQuery.data.high_attention_defects}
            emphasize={summaryQuery.data.high_attention_defects > 0}
          />
          <StatTile label="Open objections" value={summaryQuery.data.open_objections.length} />
        </div>
      )}

      <h2 className="mb-3 mt-8 text-xs font-medium uppercase tracking-wide text-[var(--color-ink-500)]">
        Filing packages
      </h2>

      <form
        onSubmit={(e) => {
          e.preventDefault()
          if (name.trim()) createPackage.mutate()
        }}
        className="mb-4 flex gap-3"
      >
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="New filing package name"
          className="flex-1 rounded border border-[var(--color-ink-300)] bg-white px-3 py-1.5 text-sm outline-none focus:border-[var(--color-accent-500)]"
        />
        <button
          type="submit"
          disabled={createPackage.isPending}
          className="rounded bg-[var(--color-ink-900)] px-3 py-1.5 text-sm font-medium text-white hover:bg-[var(--color-ink-800)] disabled:opacity-50"
        >
          Create
        </button>
      </form>

      <div className="divide-y divide-[var(--color-ink-200)] rounded-lg border border-[var(--color-ink-200)] bg-white">
        {(packagesQuery.data ?? []).map((p) => (
          <Link
            key={p.id}
            to={`/packages/${p.id}/documents`}
            className="flex items-center justify-between px-4 py-3 hover:bg-[var(--color-ink-50)]"
          >
            <span className="font-medium text-[var(--color-ink-900)]">{p.name}</span>
            <span className="text-xs text-[var(--color-ink-500)]">{lifecycleStateLabel(p.lifecycle_state)}</span>
          </Link>
        ))}
        {packagesQuery.data?.length === 0 && (
          <div className="px-4 py-6 text-center text-sm text-[var(--color-ink-400)]">
            No filing packages yet.
          </div>
        )}
      </div>
    </div>
  )
}

function StatTile({ label, value, emphasize }: { label: string; value: number; emphasize?: boolean }) {
  return (
    <div className="rounded-lg border border-[var(--color-ink-200)] bg-white p-3">
      <div
        className={`text-2xl font-semibold ${emphasize ? 'text-[var(--color-review-700)]' : 'text-[var(--color-ink-900)]'}`}
      >
        {value}
      </div>
      <div className="text-xs text-[var(--color-ink-500)]">{label}</div>
    </div>
  )
}
