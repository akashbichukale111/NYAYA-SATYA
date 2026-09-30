import { useRef, useState } from 'react'
import { useDocuments, useUploadDocument, useProcessDocument } from '../hooks'
import { Card, SectionHeading, LoadingState, ErrorState, EmptyState, StatusPill } from '../components/primitives'
import type { PipelineRunSummary } from '../types'

export function DocumentsScreen({ caseId }: { caseId: string }) {
  const documents = useDocuments(caseId)
  const upload = useUploadDocument(caseId)
  const process = useProcessDocument(caseId)
  const fileInput = useRef<HTMLInputElement>(null)
  const [lastRun, setLastRun] = useState<PipelineRunSummary | null>(null)

  return (
    <div className="space-y-6">
      <SectionHeading
        title="Documents"
        subtitle="Upload PDF, DOCX, TXT, JSON, or CSV. Every file is hashed, validated, and either ingested or quarantined."
      />

      <Card>
        <div className="flex items-center gap-3">
          <input
            ref={fileInput}
            type="file"
            accept=".pdf,.docx,.txt,.json,.csv"
            onChange={(e) => {
              const file = e.target.files?.[0]
              if (file) upload.mutate(file)
              e.target.value = ''
            }}
            className="hidden"
          />
          <button
            onClick={() => fileInput.current?.click()}
            disabled={upload.isPending}
            className="focus-ring rounded-md border border-ink-600 bg-ink-800 px-3 py-2 text-sm text-parchment-100 hover:border-ink-500 disabled:opacity-50"
          >
            {upload.isPending ? 'Uploading…' : 'Upload document'}
          </button>
          <span className="text-xs text-parchment-200/40">.pdf .docx .txt .json .csv — max 20 MB</span>
        </div>
        {upload.isError && <div className="mt-3"><ErrorState error={upload.error} /></div>}
      </Card>

      {documents.isLoading && <LoadingState />}
      {documents.isError && <ErrorState error={documents.error} />}
      {documents.data && documents.data.length === 0 && (
        <EmptyState title="No documents uploaded yet." />
      )}
      {documents.data && documents.data.length > 0 && (
        <div className="space-y-2">
          {documents.data.map((doc) => (
            <Card key={doc.id} className="flex items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate text-sm text-parchment-100">{doc.filename}</p>
                <p className="mt-0.5 truncate font-mono text-xs text-parchment-200/40">
                  {doc.document_type} · {doc.file_size_bytes ?? 0} bytes · {doc.sha256_hash.slice(0, 16)}…
                </p>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                <StatusPill label={doc.status} />
                {doc.status === 'INGESTED' && (
                  <button
                    onClick={() => process.mutate(doc.id, { onSuccess: (data) => setLastRun(data) })}
                    disabled={process.isPending}
                    className="focus-ring rounded-md border border-signal-verified/40 bg-signal-verified/10 px-3 py-1.5 text-xs font-medium text-signal-verified hover:bg-signal-verified/20 disabled:opacity-50"
                  >
                    {process.isPending ? 'Processing…' : 'Run extraction pipeline'}
                  </button>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}

      {process.isError && <ErrorState error={process.error} />}

      {lastRun && (
        <Card>
          <h3 className="mb-2 text-xs font-medium uppercase tracking-wider text-parchment-200/40">
            Last pipeline run
          </h3>
          <dl className="grid grid-cols-2 gap-2 text-xs sm:grid-cols-3">
            <PipelineStat label="Evidence created" value={lastRun.evidence_created.length} />
            <PipelineStat label="Claims created" value={lastRun.claims_created.length} />
            <PipelineStat label="Issue mappings proposed" value={lastRun.issue_mapping_review_tasks.length} />
            <PipelineStat label="Relationships upgraded" value={lastRun.relationships_upgraded.length} />
            <PipelineStat label="Conflicts flagged" value={lastRun.conflicts_flagged.length} />
            <PipelineStat label="Verification proposals" value={lastRun.verification_review_tasks.length} />
          </dl>
          <p className="mt-3 text-xs italic text-parchment-200/40">
            Every evidence item created above is a verbatim excerpt of the uploaded document. Claims, issue
            mappings, and verifications from this run wait in the Review Queue for a human decision.
          </p>
        </Card>
      )}
    </div>
  )
}

function PipelineStat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border border-ink-700 bg-ink-950/50 px-2 py-1.5">
      <p className="text-parchment-200/40">{label}</p>
      <p className="font-serif text-lg text-parchment-50">{value}</p>
    </div>
  )
}
