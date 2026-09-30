import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { endpoints } from '../lib/api'
import { checklistStatusClasses } from '../lib/status'
import { Badge } from '../components/Badge'
import { PackageHeader, usePackageId } from './FilingPackageTabs'

const REQUIREMENT_SOURCES = [
  'USER_PROVIDED_CHECKLIST',
  'SOURCE_DOCUMENT',
  'AUTHORIZED_TEMPLATE',
  'CONFIGURED_REGISTRY_RULE',
  'IMPORTED_REQUIREMENT_SET',
  'UNKNOWN',
]

const REQUIREMENT_TYPES = [
  'DOCUMENT_REQUIRED',
  'ATTACHMENT_REQUIRED',
  'FIELD_REQUIRED',
  'METADATA_REQUIRED',
  'FORMAT_REQUIRED',
  'REFERENCE_REQUIRED',
  'SIGNATURE_REQUIRED_WHEN_EXPLICITLY_SPECIFIED',
  'CHECKLIST_ITEM',
  'CUSTOM',
]

export function RequirementsTab() {
  const packageId = usePackageId()
  const queryClient = useQueryClient()
  const [description, setDescription] = useState('')
  const [requirementType, setRequirementType] = useState('DOCUMENT_REQUIRED')
  const [source, setSource] = useState('USER_PROVIDED_CHECKLIST')
  const [sourceReference, setSourceReference] = useState('')
  const [targetLabel, setTargetLabel] = useState('')

  const reqQuery = useQuery({
    queryKey: ['requirements', packageId],
    queryFn: () => endpoints.listRequirements(packageId),
  })

  const create = useMutation({
    mutationFn: () =>
      endpoints.createRequirement(packageId, {
        requirement_type: requirementType,
        description: description.trim(),
        source,
        source_reference: sourceReference.trim() || undefined,
        target_reference_label: targetLabel.trim() || undefined,
      }),
    onSuccess: () => {
      setDescription('')
      setSourceReference('')
      setTargetLabel('')
      queryClient.invalidateQueries({ queryKey: ['requirements', packageId] })
    },
  })

  return (
    <div>
      <PackageHeader title="Requirements" />

      <form
        onSubmit={(e) => {
          e.preventDefault()
          if (description.trim()) create.mutate()
        }}
        className="mb-6 flex flex-col gap-3 rounded-lg border border-[var(--color-ink-200)] bg-white p-4"
      >
        <div className="text-xs text-[var(--color-ink-500)]">
          Every requirement must declare its source. Requirements without a real source are
          recorded as UNKNOWN and never treated as active — the engine does not invent filing
          rules.
        </div>
        <div className="flex flex-wrap gap-3">
          <label className="text-sm text-[var(--color-ink-600)]">
            Type
            <select
              value={requirementType}
              onChange={(e) => setRequirementType(e.target.value)}
              className="mt-1 block rounded border border-[var(--color-ink-300)] px-3 py-1.5 text-sm outline-none focus:border-[var(--color-accent-500)]"
            >
              {REQUIREMENT_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm text-[var(--color-ink-600)]">
            Source
            <select
              value={source}
              onChange={(e) => setSource(e.target.value)}
              className="mt-1 block rounded border border-[var(--color-ink-300)] px-3 py-1.5 text-sm outline-none focus:border-[var(--color-accent-500)]"
            >
              {REQUIREMENT_SOURCES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm text-[var(--color-ink-600)]">
            Named item (optional)
            <input
              value={targetLabel}
              onChange={(e) => setTargetLabel(e.target.value)}
              placeholder="e.g. Annexure B"
              className="mt-1 block w-40 rounded border border-[var(--color-ink-300)] px-3 py-1.5 text-sm outline-none focus:border-[var(--color-accent-500)]"
            />
          </label>
        </div>
        <label className="text-sm text-[var(--color-ink-600)]">
          Description
          <input
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            required
            placeholder="e.g. Annexure B must be included in the filing package"
            className="mt-1 block w-full rounded border border-[var(--color-ink-300)] px-3 py-1.5 text-sm outline-none focus:border-[var(--color-accent-500)]"
          />
        </label>
        <label className="text-sm text-[var(--color-ink-600)]">
          Source reference
          <input
            value={sourceReference}
            onChange={(e) => setSourceReference(e.target.value)}
            placeholder="e.g. Uploaded checklist.pdf, item 3"
            className="mt-1 block w-full rounded border border-[var(--color-ink-300)] px-3 py-1.5 text-sm outline-none focus:border-[var(--color-accent-500)]"
          />
        </label>
        <button
          type="submit"
          disabled={create.isPending}
          className="self-start rounded bg-[var(--color-ink-900)] px-3 py-1.5 text-sm font-medium text-white hover:bg-[var(--color-ink-800)] disabled:opacity-50"
        >
          Add requirement
        </button>
      </form>

      <div className="divide-y divide-[var(--color-ink-200)] rounded-lg border border-[var(--color-ink-200)] bg-white">
        {(reqQuery.data ?? []).map((r) => (
          <div key={r.id} className="px-4 py-3">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="text-sm text-[var(--color-ink-900)]">{r.description}</div>
                <div className="mt-1 flex flex-wrap gap-2 text-xs text-[var(--color-ink-500)]">
                  <Badge className="border-[var(--color-ink-300)] text-[var(--color-ink-600)]">
                    {r.requirement_type}
                  </Badge>
                  <Badge className="border-[var(--color-ink-300)] text-[var(--color-ink-600)]">
                    source: {r.source}
                  </Badge>
                  {r.status === 'UNKNOWN' && (
                    <Badge className="border-[var(--color-review-700)]/30 bg-[var(--color-review-100)] text-[var(--color-review-700)]">
                      REQUIREMENT_UNKNOWN
                    </Badge>
                  )}
                </div>
                {r.source_reference && (
                  <div className="mt-1 text-xs text-[var(--color-ink-400)]">{r.source_reference}</div>
                )}
              </div>
            </div>
          </div>
        ))}
        {reqQuery.data?.length === 0 && (
          <div className="px-4 py-6 text-center text-sm text-[var(--color-ink-400)]">
            No requirements recorded yet.
          </div>
        )}
      </div>
    </div>
  )
}

export function ChecklistTab() {
  const packageId = usePackageId()
  const checklistQuery = useQuery({
    queryKey: ['checklist', packageId],
    queryFn: () => endpoints.getChecklist(packageId),
  })
  const reqQuery = useQuery({
    queryKey: ['requirements', packageId],
    queryFn: () => endpoints.listRequirements(packageId),
  })

  const requirementsById = new Map((reqQuery.data ?? []).map((r) => [r.id, r]))

  return (
    <div>
      <PackageHeader title="Checklist" />
      <div className="divide-y divide-[var(--color-ink-200)] rounded-lg border border-[var(--color-ink-200)] bg-white">
        {(checklistQuery.data ?? []).map((item) => {
          const req = requirementsById.get(item.requirement_id)
          return (
            <div key={item.id} className="px-4 py-3">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-sm text-[var(--color-ink-900)]">
                    {req?.description ?? 'Requirement'}
                  </div>
                  {item.explanation && (
                    <div className="mt-1 text-xs text-[var(--color-ink-500)]">{item.explanation}</div>
                  )}
                </div>
                <Badge className={checklistStatusClasses(item.status)}>{item.status}</Badge>
              </div>
            </div>
          )
        })}
        {checklistQuery.data?.length === 0 && (
          <div className="px-4 py-6 text-center text-sm text-[var(--color-ink-400)]">
            No checklist items yet. Add requirements, then run precheck.
          </div>
        )}
      </div>
    </div>
  )
}
