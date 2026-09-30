import { useState } from 'react'
import { useCases, useCreateCase, useSeedDemo } from '../hooks'
import { Card, SectionHeading, LoadingState, ErrorState, EmptyState, StatusPill } from '../components/primitives'

export function CaseExplorer({ onOpenCase }: { onOpenCase: (caseId: string) => void }) {
  const cases = useCases()
  const createCase = useCreateCase()
  const seedDemo = useSeedDemo()
  const [title, setTitle] = useState('')

  return (
    <div className="space-y-6">
      <SectionHeading title="Cases" subtitle="Create a case, or load a deterministic offline demo — no API key required." />

      <Card>
        <div className="flex flex-wrap items-center gap-2">
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="New case title…"
            className="focus-ring min-w-[220px] flex-1 rounded-md border border-ink-600 bg-ink-800 px-3 py-2 text-sm text-parchment-100 placeholder:text-parchment-200/30"
          />
          <button
            onClick={() => title.trim() && createCase.mutate({ title }, { onSuccess: () => setTitle('') })}
            disabled={!title.trim() || createCase.isPending}
            className="focus-ring rounded-md border border-signal-verified/40 bg-signal-verified/10 px-3 py-2 text-sm font-medium text-signal-verified hover:bg-signal-verified/20 disabled:opacity-50"
          >
            Create case
          </button>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-ink-700 pt-3">
          <span className="text-xs text-parchment-200/40">Demo cases:</span>
          {(['A', 'B', 'C'] as const).map((key) => (
            <button
              key={key}
              onClick={() => seedDemo.mutate(key, { onSuccess: (c) => onOpenCase(c.id) })}
              disabled={seedDemo.isPending}
              className="focus-ring rounded-md border border-ink-600 px-3 py-1.5 text-xs text-parchment-200/80 hover:border-ink-500 disabled:opacity-50"
            >
              Seed demo {key}
            </button>
          ))}
        </div>
        {createCase.isError && <div className="mt-2"><ErrorState error={createCase.error} /></div>}
        {seedDemo.isError && <div className="mt-2"><ErrorState error={seedDemo.error} /></div>}
      </Card>

      {cases.isLoading && <LoadingState />}
      {cases.isError && <ErrorState error={cases.error} />}
      {cases.data && cases.data.length === 0 && <EmptyState title="No cases yet." />}
      {cases.data && cases.data.length > 0 && (
        <div className="grid gap-3 sm:grid-cols-2">
          {cases.data.map((c) => (
            <button
              key={c.id}
              onClick={() => onOpenCase(c.id)}
              className="focus-ring block rounded-lg border border-ink-700 bg-ink-900/60 p-4 text-left transition hover:border-ink-600"
            >
              <div className="flex items-start justify-between gap-2">
                <p className="font-serif text-base text-parchment-50">{c.title}</p>
                {c.is_demo && <StatusPill label="DEMO" />}
              </div>
              {c.description && <p className="mt-1 line-clamp-2 text-xs text-parchment-200/50">{c.description}</p>}
              <p className="mt-2 font-mono text-[11px] text-parchment-200/30">
                {new Date(c.created_at).toLocaleDateString()}
              </p>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
