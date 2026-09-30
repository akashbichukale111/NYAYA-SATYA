import { useCoverage, useFragility, useMissingEvidence, useReviewQueue, useAudit } from '../hooks'
import { Card, SectionHeading, LoadingState, ErrorState, EmptyState, StatusPill } from '../components/primitives'
import type { Case } from '../types'

export function CommandCenter({ activeCase, onNavigate }: { activeCase: Case; onNavigate: (view: string) => void }) {
  const coverage = useCoverage(activeCase.id)
  const fragility = useFragility(activeCase.id)
  const missing = useMissingEvidence(activeCase.id)
  const reviewQueue = useReviewQueue(activeCase.id)
  const audit = useAudit(activeCase.id)

  return (
    <div className="space-y-6">
      <SectionHeading
        title="Evidence Dependency Command Center"
        subtitle={activeCase.is_demo ? 'DEMONSTRATION DATA — NOT A REAL CASE' : activeCase.title}
      />

      {/* Case overview */}
      <section>
        <h3 className="mb-2 text-xs font-medium uppercase tracking-wider text-parchment-200/40">Case overview</h3>
        {coverage.isLoading && <LoadingState />}
        {coverage.isError && <ErrorState error={coverage.error} />}
        {coverage.data && (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <StatTile label="Evidence items" value={coverage.data.evidence_items_total} />
            <StatTile label="Claims" value={coverage.data.claims_total} />
            <StatTile label="Issues" value={coverage.data.issues_total} />
            <StatTile label="Verified evidence" value={coverage.data.verified_evidence_items} tone="verified" />
            <StatTile label="Unverified evidence" value={coverage.data.unverified_evidence_items} tone="review" />
            <StatTile label="Conflicting claims" value={coverage.data.conflicting_claims} tone="conflict" />
            <StatTile label="Claims w/o evidence" value={coverage.data.claims_without_evidence} tone="conflict" />
            <StatTile label="Unsupported issues" value={coverage.data.unsupported_issues} tone="conflict" />
          </div>
        )}
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Critical dependencies */}
        <section>
          <h3 className="mb-2 text-xs font-medium uppercase tracking-wider text-parchment-200/40">
            Critical dependencies
          </h3>
          <Card>
            {fragility.isLoading && <LoadingState />}
            {fragility.isError && <ErrorState error={fragility.error} />}
            {fragility.data && fragility.data.filter((f) => f.criticality !== 'NONE').length === 0 && (
              <EmptyState title="No single-point-of-failure evidence detected." />
            )}
            {fragility.data && (
              <ul className="space-y-2">
                {fragility.data
                  .filter((f) => f.criticality !== 'NONE')
                  .slice(0, 6)
                  .map((f) => (
                    <li key={f.evidence_id} className="flex items-center justify-between gap-2 text-sm">
                      <span className="truncate text-parchment-100">{f.label}</span>
                      <span className="flex shrink-0 items-center gap-2">
                        <span className="text-xs text-parchment-200/50">{f.dependency_count} downstream</span>
                        <StatusPill label={f.criticality} />
                      </span>
                    </li>
                  ))}
              </ul>
            )}
          </Card>
        </section>

        {/* Evidence gaps */}
        <section>
          <h3 className="mb-2 text-xs font-medium uppercase tracking-wider text-parchment-200/40">Evidence gaps</h3>
          <Card>
            {missing.isLoading && <LoadingState />}
            {missing.isError && <ErrorState error={missing.error} />}
            {missing.data && (
              <div className="space-y-3 text-sm">
                <GapRow label="Claims with no evidence" count={missing.data.claims_without_evidence.length} />
                <GapRow
                  label="Claims with only conflicting evidence"
                  count={missing.data.claims_with_only_conflicting_evidence.length}
                />
                <GapRow
                  label="Claims resting on a single source"
                  count={missing.data.claims_with_single_source_only.length}
                />
                <GapRow
                  label="Issues with no supporting claim"
                  count={missing.data.issues_without_supporting_claims.length}
                />
              </div>
            )}
          </Card>
        </section>

        {/* Human review queue */}
        <section>
          <h3 className="mb-2 text-xs font-medium uppercase tracking-wider text-parchment-200/40">
            Human review queue
          </h3>
          <Card>
            {reviewQueue.isLoading && <LoadingState />}
            {reviewQueue.isError && <ErrorState error={reviewQueue.error} />}
            {reviewQueue.data && reviewQueue.data.filter((t) => t.status === 'PENDING').length === 0 && (
              <EmptyState title="Nothing pending review." />
            )}
            {reviewQueue.data && reviewQueue.data.filter((t) => t.status === 'PENDING').length > 0 && (
              <button
                onClick={() => onNavigate('review')}
                className="focus-ring w-full rounded-md border border-signal-review/30 bg-signal-review/10 px-3 py-2 text-left text-sm text-signal-review hover:bg-signal-review/15"
              >
                {reviewQueue.data.filter((t) => t.status === 'PENDING').length} item(s) awaiting a human decision →
              </button>
            )}
          </Card>
        </section>

        {/* Recent changes */}
        <section>
          <h3 className="mb-2 text-xs font-medium uppercase tracking-wider text-parchment-200/40">Recent changes</h3>
          <Card>
            {audit.isLoading && <LoadingState />}
            {audit.isError && <ErrorState error={audit.error} />}
            {audit.data && audit.data.length === 0 && <EmptyState title="No activity recorded yet." />}
            {audit.data && (
              <ul className="space-y-1.5 text-xs">
                {audit.data.slice(0, 6).map((e) => (
                  <li key={e.id} className="flex items-center justify-between gap-2 text-parchment-200/70">
                    <span className="truncate">
                      <span className="font-mono text-parchment-200/40">{e.actor}</span> · {e.action.replace(/_/g, ' ').toLowerCase()}
                    </span>
                    <span className="shrink-0 font-mono text-parchment-200/30">
                      {new Date(e.created_at).toLocaleTimeString()}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </section>
      </div>
    </div>
  )
}

function StatTile({ label, value, tone }: { label: string; value: number; tone?: 'verified' | 'review' | 'conflict' }) {
  const toneClass =
    tone === 'verified' ? 'text-signal-verified' : tone === 'review' ? 'text-signal-review' : tone === 'conflict' ? 'text-signal-conflict' : 'text-parchment-50'
  return (
    <Card className="flex flex-col gap-1">
      <span className="text-xs uppercase tracking-wide text-parchment-200/40">{label}</span>
      <span className={`font-serif text-2xl ${toneClass}`}>{value}</span>
    </Card>
  )
}

function GapRow({ label, count }: { label: string; count: number }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-parchment-200/80">{label}</span>
      <span className={`font-mono text-sm ${count > 0 ? 'text-signal-conflict' : 'text-parchment-200/40'}`}>{count}</span>
    </div>
  )
}
