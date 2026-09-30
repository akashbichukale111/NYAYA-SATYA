import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { endpoints } from '../lib/api'
import { Badge } from '../components/Badge'
import { PackageHeader, usePackageId } from './FilingPackageTabs'

export function ObjectionsTab() {
  const packageId = usePackageId()
  const queryClient = useQueryClient()
  const [text, setText] = useState('')
  const [ref, setRef] = useState('')

  const objectionsQuery = useQuery({
    queryKey: ['objections', packageId],
    queryFn: () => endpoints.listObjections(packageId),
  })

  const create = useMutation({
    mutationFn: () => endpoints.createObjection(packageId, text.trim(), ref.trim() || undefined),
    onSuccess: () => {
      setText('')
      setRef('')
      queryClient.invalidateQueries({ queryKey: ['objections', packageId] })
    },
  })

  return (
    <div>
      <PackageHeader title="Registry Objections" />

      <form
        onSubmit={(e) => {
          e.preventDefault()
          if (text.trim()) create.mutate()
        }}
        className="mb-6 flex flex-col gap-3 rounded-lg border border-[var(--color-ink-200)] bg-white p-4"
      >
        <div className="text-xs text-[var(--color-ink-500)]">
          Enter the objection exactly as received. The original text is preserved permanently —
          the engine never edits or paraphrases it.
        </div>
        <label className="text-sm text-[var(--color-ink-600)]">
          Objection text
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            required
            rows={2}
            placeholder="e.g. Annexure missing: proof of authorization was not found."
            className="mt-1 block w-full rounded border border-[var(--color-ink-300)] px-3 py-1.5 text-sm outline-none focus:border-[var(--color-accent-500)]"
          />
        </label>
        <label className="text-sm text-[var(--color-ink-600)]">
          Source reference
          <input
            value={ref}
            onChange={(e) => setRef(e.target.value)}
            placeholder="e.g. Registry letter dated 12 March"
            className="mt-1 block w-full rounded border border-[var(--color-ink-300)] px-3 py-1.5 text-sm outline-none focus:border-[var(--color-accent-500)]"
          />
        </label>
        <button
          type="submit"
          disabled={create.isPending}
          className="self-start rounded bg-[var(--color-ink-900)] px-3 py-1.5 text-sm font-medium text-white hover:bg-[var(--color-ink-800)] disabled:opacity-50"
        >
          Record objection
        </button>
      </form>

      <div className="divide-y divide-[var(--color-ink-200)] rounded-lg border border-[var(--color-ink-200)] bg-white">
        {(objectionsQuery.data ?? []).map((o) => (
          <div key={o.id} className="px-4 py-3">
            <div className="flex items-start justify-between gap-3">
              <div className="text-sm text-[var(--color-ink-900)]">{o.original_text}</div>
              <Badge className="border-[var(--color-ink-300)] text-[var(--color-ink-600)]">{o.status}</Badge>
            </div>
            {o.source_reference && (
              <div className="mt-1 text-xs text-[var(--color-ink-500)]">{o.source_reference}</div>
            )}
          </div>
        ))}
        {objectionsQuery.data?.length === 0 && (
          <div className="px-4 py-6 text-center text-sm text-[var(--color-ink-400)]">
            No registry objections recorded.
          </div>
        )}
      </div>
    </div>
  )
}

export function CorrectionsTab() {
  const packageId = usePackageId()
  const queryClient = useQueryClient()
  const [description, setDescription] = useState('')

  const correctionsQuery = useQuery({
    queryKey: ['corrections', packageId],
    queryFn: () => endpoints.listCorrections(packageId),
  })

  const create = useMutation({
    mutationFn: () => endpoints.createCorrection(packageId, { description: description.trim() }),
    onSuccess: () => {
      setDescription('')
      queryClient.invalidateQueries({ queryKey: ['corrections', packageId] })
    },
  })

  return (
    <div>
      <PackageHeader title="Corrections" />

      <form
        onSubmit={(e) => {
          e.preventDefault()
          if (description.trim()) create.mutate()
        }}
        className="mb-6 flex flex-col gap-3 rounded-lg border border-[var(--color-ink-200)] bg-white p-4"
      >
        <div className="text-xs text-[var(--color-ink-500)]">
          A correction here is a planned, simulated action — it does not edit or submit any real
          filing. It records what should be done and who approved it.
        </div>
        <label className="text-sm text-[var(--color-ink-600)]">
          Description
          <input
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            required
            placeholder="e.g. Attach proof of authorization to resolve the registry objection"
            className="mt-1 block w-full rounded border border-[var(--color-ink-300)] px-3 py-1.5 text-sm outline-none focus:border-[var(--color-accent-500)]"
          />
        </label>
        <button
          type="submit"
          disabled={create.isPending}
          className="self-start rounded bg-[var(--color-ink-900)] px-3 py-1.5 text-sm font-medium text-white hover:bg-[var(--color-ink-800)] disabled:opacity-50"
        >
          Plan correction
        </button>
      </form>

      <div className="divide-y divide-[var(--color-ink-200)] rounded-lg border border-[var(--color-ink-200)] bg-white">
        {(correctionsQuery.data ?? []).map((c) => (
          <div key={c.id} className="px-4 py-3">
            <div className="flex items-start justify-between gap-3">
              <div className="text-sm text-[var(--color-ink-900)]">{c.description}</div>
              <Badge className="border-[var(--color-ink-300)] text-[var(--color-ink-600)]">{c.status}</Badge>
            </div>
          </div>
        ))}
        {correctionsQuery.data?.length === 0 && (
          <div className="px-4 py-6 text-center text-sm text-[var(--color-ink-400)]">
            No corrections planned yet.
          </div>
        )}
      </div>
    </div>
  )
}
