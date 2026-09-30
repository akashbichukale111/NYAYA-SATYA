import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '../api'
import { useRunCrashTest } from '../hooks'
import { Card, LoadingState, ErrorState, StatusPill, SourceLocation } from './primitives'

const CRASH_TEST_EVENTS = [
  'REMOVE_EVIDENCE', 'EXCLUDE_EVIDENCE', 'MARK_UNVERIFIED', 'REVERSE_RELATIONSHIP',
  'INTRODUCE_CONTRADICTORY_EVIDENCE', 'SUPERSEDE_DOCUMENT', 'REMOVE_SOURCE_DOCUMENT',
  'INVALIDATE_PROVENANCE', 'BREAK_CLAIM_DEPENDENCY', 'CREATE_MISSING_EVIDENCE',
]

export function EvidenceDetailPanel({ evidenceId, caseId }: { evidenceId: string; caseId: string }) {
  const evidence = useQuery({ queryKey: ['evidence-detail', evidenceId], queryFn: () => api.getEvidence(evidenceId) })
  const impact = useQuery({ queryKey: ['impact', evidenceId], queryFn: () => api.getEvidenceImpact(evidenceId) })
  const history = useQuery({ queryKey: ['history', evidenceId], queryFn: () => api.getEvidenceHistory(evidenceId) })
  const crashTest = useRunCrashTest(caseId)
  const [selectedEvent, setSelectedEvent] = useState(CRASH_TEST_EVENTS[0])

  if (evidence.isLoading) return <Card><LoadingState /></Card>
  if (evidence.isError) return <Card><ErrorState error={evidence.error} /></Card>
  if (!evidence.data) return null
  const ev = evidence.data

  return (
    <div className="space-y-4">
      <Card>
        <h3 className="mb-3 text-xs font-medium uppercase tracking-wider text-parchment-200/40">Source Inspector</h3>
        <p className="mb-3 text-sm leading-relaxed text-parchment-100">{ev.source_text || '(no source text recorded)'}</p>
        <dl className="space-y-1.5 text-xs">
          <Row label="Source location">
            <SourceLocation known={ev.source_location_known} page={ev.page_number} section={ev.section} />
          </Row>
          <Row label="Extraction method"><span className="font-mono">{ev.extraction_method ?? '—'}</span></Row>
          <Row label="Document"><span className="font-mono">{ev.document_id ?? 'no linked document'}</span></Row>
          <Row label="State"><StatusPill label={ev.state} /></Row>
          <Row label="Verification"><StatusPill label={ev.verification_status} /></Row>
        </dl>
      </Card>

      <Card>
        <h3 className="mb-3 text-xs font-medium uppercase tracking-wider text-parchment-200/40">Dependency impact</h3>
        {impact.isLoading && <LoadingState />}
        {impact.isError && <ErrorState error={impact.error} />}
        {impact.data && (
          <div className="space-y-2 text-sm">
            <Row label="Criticality"><StatusPill label={impact.data.criticality} /></Row>
            <Row label="Affected claims"><span>{impact.data.affected_claims.length}</span></Row>
            <Row label="Affected issues"><span>{impact.data.affected_issues.length}</span></Row>
            <Row label="Human review required">
              <span>{impact.data.human_review_required ? 'Yes' : 'No'}</span>
            </Row>
          </div>
        )}
      </Card>

      <Card>
        <h3 className="mb-3 text-xs font-medium uppercase tracking-wider text-parchment-200/40">Evidence Crash Test</h3>
        <p className="mb-2 text-xs text-parchment-200/50">
          Simulation only — nothing about this evidence item is changed by running a crash test.
        </p>
        <div className="flex gap-2">
          <select
            value={selectedEvent}
            onChange={(e) => setSelectedEvent(e.target.value)}
            className="focus-ring flex-1 rounded-md border border-ink-600 bg-ink-800 px-2 py-1.5 text-xs text-parchment-100"
          >
            {CRASH_TEST_EVENTS.map((ev) => (
              <option key={ev} value={ev}>{ev.replace(/_/g, ' ')}</option>
            ))}
          </select>
          <button
            onClick={() => crashTest.mutate({ evidenceId, eventType: selectedEvent })}
            disabled={crashTest.isPending}
            className="focus-ring rounded-md border border-signal-review/40 bg-signal-review/10 px-3 py-1.5 text-xs font-medium text-signal-review hover:bg-signal-review/20 disabled:opacity-50"
          >
            {crashTest.isPending ? 'Running…' : 'Run'}
          </button>
        </div>
        {crashTest.isError && <div className="mt-2"><ErrorState error={crashTest.error} /></div>}
        {crashTest.data && (
          <div className="mt-3 space-y-2 rounded-md border border-ink-700 bg-ink-950/50 p-3 text-xs">
            <Row label="Criticality"><StatusPill label={crashTest.data.criticality} /></Row>
            <Row label="Affected claims"><span>{crashTest.data.affected_claims.length}</span></Row>
            <Row label="Affected issues"><span>{crashTest.data.affected_issues.length}</span></Row>
            <Row label="New gaps"><span>{crashTest.data.new_gaps.length}</span></Row>
            <Row label="New conflicts"><span>{crashTest.data.new_conflicts.length}</span></Row>
            <p className="pt-1 italic text-parchment-200/40">{crashTest.data.note}</p>
          </div>
        )}
      </Card>

      <Card>
        <h3 className="mb-3 text-xs font-medium uppercase tracking-wider text-parchment-200/40">History (Time Machine)</h3>
        {history.isLoading && <LoadingState />}
        {history.isError && <ErrorState error={history.error} />}
        {history.data && history.data.length === 0 && (
          <p className="text-xs text-parchment-200/40">No history recorded.</p>
        )}
        {history.data && history.data.length > 0 && (
          <ol className="space-y-2 border-l border-ink-700 pl-3 text-xs">
            {history.data.map((v) => (
              <li key={v.version_number} className="relative">
                <span className="absolute -left-[15px] top-1 h-2 w-2 rounded-full bg-parchment-200/40" />
                <p className="font-mono text-parchment-200/70">v{v.version_number} · {v.reason || 'change'}</p>
                <p className="text-parchment-200/40">{new Date(v.as_of).toLocaleString()}</p>
              </li>
            ))}
          </ol>
        )}
      </Card>
    </div>
  )
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <dt className="text-parchment-200/50">{label}</dt>
      <dd>{children}</dd>
    </div>
  )
}
