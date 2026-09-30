import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { endpoints } from '../lib/api'
import { lifecycleStateLabel } from '../lib/status'
import { Badge } from '../components/Badge'

export function CommandCenterPage() {
  const queryClient = useQueryClient()
  const casesQuery = useQuery({ queryKey: ['cases'], queryFn: endpoints.listCases })

  async function handleSeedDemo() {
    await endpoints.seedDemo()
    queryClient.invalidateQueries({ queryKey: ['cases'] })
  }

  const cases = casesQuery.data ?? []
  const demoCases = cases.filter((c) => c.is_demo)
  const realCases = cases.filter((c) => !c.is_demo)

  return (
    <div className="mx-auto max-w-5xl px-8 py-8">
      <header className="mb-8 flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold text-[var(--color-ink-900)]">Registry Defect Command Center</h1>
          <p className="mt-1 max-w-2xl text-sm text-[var(--color-ink-500)]">
            An operational summary across your cases: filing packages, open defects, unresolved
            objections, and what needs human review right now. This is not a legal determination —
            it surfaces documented or structurally detected issues for you to review.
          </p>
        </div>
        {demoCases.length === 0 && (
          <button
            onClick={handleSeedDemo}
            className="whitespace-nowrap rounded border border-[var(--color-ink-300)] bg-white px-3 py-1.5 text-sm text-[var(--color-ink-700)] hover:border-[var(--color-accent-500)]"
          >
            Load demo cases
          </button>
        )}
      </header>

      {casesQuery.isLoading && <p className="text-sm text-[var(--color-ink-400)]">Loading cases…</p>}
      {casesQuery.isError && (
        <p className="text-sm text-[var(--color-review-700)]">
          Could not reach the backend. Is the API running on :8000?
        </p>
      )}

      {!casesQuery.isLoading && cases.length === 0 && !casesQuery.isError && (
        <div className="rounded-lg border border-dashed border-[var(--color-ink-300)] bg-white p-8 text-center">
          <p className="text-sm text-[var(--color-ink-500)]">
            No cases yet. Create one from the Cases page, or load the demonstration cases to see the
            engine in action.
          </p>
        </div>
      )}

      {realCases.length > 0 && (
        <section className="mb-8">
          <h2 className="mb-3 text-xs font-medium uppercase tracking-wide text-[var(--color-ink-500)]">
            Your cases
          </h2>
          <CaseGrid cases={realCases} />
        </section>
      )}

      {demoCases.length > 0 && (
        <section>
          <h2 className="mb-3 text-xs font-medium uppercase tracking-wide text-[var(--color-ink-500)]">
            Demonstration cases
          </h2>
          <CaseGrid cases={demoCases} />
        </section>
      )}
    </div>
  )
}

function CaseGrid({ cases }: { cases: Array<{ id: string; title: string; case_reference: string | null; status: string; is_demo: boolean }> }) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      {cases.map((c) => (
        <Link
          key={c.id}
          to={`/cases/${c.id}`}
          className="rounded-lg border border-[var(--color-ink-200)] bg-white p-4 transition-colors hover:border-[var(--color-accent-500)]"
        >
          {c.is_demo && (
            <div className="mb-2">
              <Badge className="border-[var(--color-review-700)]/30 bg-[var(--color-review-100)] text-[var(--color-review-700)]">
                DEMONSTRATION DATA — NOT A REAL CASE
              </Badge>
            </div>
          )}
          <div className="font-medium text-[var(--color-ink-900)]">{c.title}</div>
          {c.case_reference && (
            <div className="mt-0.5 font-mono text-xs text-[var(--color-ink-500)]">{c.case_reference}</div>
          )}
          <div className="mt-2 text-xs text-[var(--color-ink-500)]">{lifecycleStateLabel(c.status)}</div>
        </Link>
      ))}
    </div>
  )
}
