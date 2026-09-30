import { useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { endpoints, type DocumentRow } from '../lib/api'
import { lifecycleStateLabel } from '../lib/status'

export function usePackageId() {
  const { packageId } = useParams<{ packageId: string }>()
  return packageId!
}

export function PackageHeader({ title }: { title: string }) {
  const packageId = usePackageId()
  const queryClient = useQueryClient()
  const precheck = useMutation({
    mutationFn: () => endpoints.runPrecheck(packageId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['defects', packageId] })
      queryClient.invalidateQueries({ queryKey: ['checklist', packageId] })
      queryClient.invalidateQueries({ queryKey: ['review-queue', packageId] })
      queryClient.invalidateQueries({ queryKey: ['objections', packageId] })
    },
  })

  return (
    <div className="mb-6 flex items-start justify-between gap-4">
      <div>
        <h1 className="text-xl font-semibold text-[var(--color-ink-900)]">{title}</h1>
        <p className="mt-1 max-w-xl text-sm text-[var(--color-ink-500)]">
          Running precheck re-scans documents, requirements, and metadata for defects. It never
          submits anything or contacts a registry — it only detects and records.
        </p>
      </div>
      <button
        onClick={() => precheck.mutate()}
        disabled={precheck.isPending}
        className="whitespace-nowrap rounded bg-[var(--color-accent-500)] px-4 py-2 text-sm font-medium text-white hover:bg-[var(--color-accent-600)] disabled:opacity-50"
      >
        {precheck.isPending ? 'Running precheck…' : 'Run precheck'}
      </button>
    </div>
  )
}

export function DocumentsTab() {
  const packageId = usePackageId()
  const queryClient = useQueryClient()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [displayName, setDisplayName] = useState('')
  const [documentKind, setDocumentKind] = useState('')

  const docsQuery = useQuery({ queryKey: ['documents', packageId], queryFn: () => endpoints.listDocuments(packageId) })

  const upload = useMutation({
    mutationFn: (file: File) => endpoints.uploadDocument(packageId, file, displayName.trim() || file.name, documentKind.trim() || undefined),
    onSuccess: () => {
      setDisplayName('')
      setDocumentKind('')
      if (fileInputRef.current) fileInputRef.current.value = ''
      queryClient.invalidateQueries({ queryKey: ['documents', packageId] })
    },
  })

  return (
    <div>
      <PackageHeader title="Documents" />

      <form
        onSubmit={(e) => {
          e.preventDefault()
          const file = fileInputRef.current?.files?.[0]
          if (file) upload.mutate(file)
        }}
        className="mb-6 flex flex-wrap items-end gap-3 rounded-lg border border-[var(--color-ink-200)] bg-white p-4"
      >
        <label className="text-sm text-[var(--color-ink-600)]">
          Display name
          <input
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="e.g. Petition"
            className="mt-1 block w-48 rounded border border-[var(--color-ink-300)] px-3 py-1.5 text-sm outline-none focus:border-[var(--color-accent-500)]"
          />
        </label>
        <label className="text-sm text-[var(--color-ink-600)]">
          Kind (optional)
          <input
            value={documentKind}
            onChange={(e) => setDocumentKind(e.target.value)}
            placeholder="e.g. annexure"
            className="mt-1 block w-40 rounded border border-[var(--color-ink-300)] px-3 py-1.5 text-sm outline-none focus:border-[var(--color-accent-500)]"
          />
        </label>
        <label className="text-sm text-[var(--color-ink-600)]">
          File
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx,.txt,.json,.csv"
            className="mt-1 block text-sm"
          />
        </label>
        <button
          type="submit"
          disabled={upload.isPending}
          className="rounded bg-[var(--color-ink-900)] px-3 py-1.5 text-sm font-medium text-white hover:bg-[var(--color-ink-800)] disabled:opacity-50"
        >
          {upload.isPending ? 'Uploading…' : 'Upload'}
        </button>
        {upload.isError && (
          <p className="w-full text-sm text-[var(--color-review-700)]">
            Upload failed. The file type may not be permitted, or it may exceed the size limit.
          </p>
        )}
      </form>

      <div className="divide-y divide-[var(--color-ink-200)] rounded-lg border border-[var(--color-ink-200)] bg-white">
        {(docsQuery.data ?? []).map((doc) => (
          <DocumentRowItem key={doc.id} doc={doc} />
        ))}
        {docsQuery.data?.length === 0 && (
          <div className="px-4 py-6 text-center text-sm text-[var(--color-ink-400)]">
            No documents uploaded yet.
          </div>
        )}
      </div>
    </div>
  )
}

function DocumentRowItem({ doc }: { doc: DocumentRow }) {
  const versionsQuery = useQuery({
    queryKey: ['document-versions', doc.id],
    queryFn: () => endpoints.listDocumentVersions(doc.id),
  })
  const current = versionsQuery.data?.find((v) => v.id === doc.current_version_id) ?? versionsQuery.data?.[0]

  return (
    <div className="px-4 py-3">
      <div className="flex items-center justify-between">
        <div>
          <span className="font-medium text-[var(--color-ink-900)]">{doc.display_name}</span>
          {doc.document_kind && (
            <span className="ml-2 text-xs text-[var(--color-ink-500)]">({doc.document_kind})</span>
          )}
        </div>
        <span className="text-xs text-[var(--color-ink-500)]">{lifecycleStateLabel(doc.status)}</span>
      </div>
      {current && (
        <div className="mt-1 flex flex-wrap gap-x-4 gap-y-0.5 font-mono text-[11px] text-[var(--color-ink-400)]">
          <span>{current.original_filename}</span>
          <span>{(current.size_bytes / 1024).toFixed(1)} KB</span>
          <span>
            sha256:{current.sha256 ? current.sha256.slice(0, 12) + '…' : 'SOURCE_LOCATION_UNKNOWN'}
          </span>
          <span
            className={current.extraction_status === 'OK' ? 'text-[var(--color-ok-700)]' : 'text-[var(--color-attention-700)]'}
          >
            {current.extraction_status}
            {current.extraction_error ? `: ${current.extraction_error}` : ''}
          </span>
        </div>
      )}
    </div>
  )
}
