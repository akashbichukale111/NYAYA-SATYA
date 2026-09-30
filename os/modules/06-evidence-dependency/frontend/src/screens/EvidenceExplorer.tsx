import { useState } from 'react'
import { useEvidence } from '../hooks'
import { Card, SectionHeading, LoadingState, ErrorState, EmptyState, StatusPill, SourceLocation } from '../components/primitives'
import { EvidenceDetailPanel } from '../components/EvidenceDetailPanel'

export function EvidenceExplorer({ caseId }: { caseId: string }) {
  const evidence = useEvidence(caseId)
  const [selectedId, setSelectedId] = useState<string | null>(null)

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_380px]">
      <div>
        <SectionHeading title="Evidence" subtitle="Every evidence item in this case, with its real provenance." />
        {evidence.isLoading && <LoadingState />}
        {evidence.isError && <ErrorState error={evidence.error} />}
        {evidence.data && evidence.data.length === 0 && (
          <EmptyState title="No evidence yet." hint="Upload a document and run the extraction pipeline from Documents." />
        )}
        {evidence.data && evidence.data.length > 0 && (
          <div className="space-y-2">
            {evidence.data.map((ev) => (
              <button
                key={ev.id}
                onClick={() => setSelectedId(ev.id)}
                className={`focus-ring block w-full rounded-lg border px-4 py-3 text-left transition ${
                  selectedId === ev.id ? 'border-parchment-200/50 bg-ink-800' : 'border-ink-700 bg-ink-900/60 hover:border-ink-600'
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <p className="text-sm text-parchment-100">{ev.label}</p>
                  <div className="flex shrink-0 gap-1.5">
                    <StatusPill label={ev.verification_status} />
                  </div>
                </div>
                <div className="mt-1.5 flex items-center gap-3">
                  <SourceLocation known={ev.source_location_known} page={ev.page_number} section={ev.section} />
                  <StatusPill label={ev.state} />
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      <div>
        {selectedId ? (
          <EvidenceDetailPanel evidenceId={selectedId} caseId={caseId} />
        ) : (
          <Card>
            <EmptyState title="Select an evidence item" hint="Its full source inspector will appear here." />
          </Card>
        )}
      </div>
    </div>
  )
}
