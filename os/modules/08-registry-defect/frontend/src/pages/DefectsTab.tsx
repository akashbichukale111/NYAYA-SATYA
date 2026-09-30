import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { endpoints, type Defect } from '../lib/api'
import { severityClasses, defectStatusClasses } from '../lib/status'
import { Badge } from '../components/Badge'
import { PackageHeader, usePackageId } from './FilingPackageTabs'

export function DefectsTab() {
  const packageId = usePackageId()
  const [selected, setSelected] = useState<Defect | null>(null)
  const defectsQuery = useQuery({ queryKey: ['defects', packageId], queryFn: () => endpoints.listDefects(packageId) })

  return (
    <div>
      <PackageHeader title="Defects" />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="divide-y divide-[var(--color-ink-200)] rounded-lg border border-[var(--color-ink-200)] bg-white lg:col-span-2">
          {(defectsQuery.data ?? []).map((d) => (
            <button
              key={d.id}
              onClick={() => setSelected(d)}
              className={`block w-full px-4 py-3 text-left hover:bg-[var(--color-ink-50)] ${
                selected?.id === d.id ? 'bg-[var(--color-ink-50)]' : ''
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-sm font-medium text-[var(--color-ink-900)]">{d.defect_type}</div>
                  <div className="mt-0.5 text-xs text-[var(--color-ink-500)]">{d.category}</div>
                </div>
                <div className="flex flex-col items-end gap-1">
                  <Badge className={severityClasses(d.severity)}>{d.severity}</Badge>
                  <Badge className={defectStatusClasses(d.status)}>{d.status}</Badge>
                </div>
              </div>
            </button>
          ))}
          {defectsQuery.data?.length === 0 && (
            <div className="px-4 py-6 text-center text-sm text-[var(--color-ink-400)]">
              No defects detected. Run precheck after uploading documents and requirements.
            </div>
          )}
        </div>

        <div className="rounded-lg border border-[var(--color-ink-200)] bg-white p-4">
          {selected ? (
            <div>
              <h3 className="text-sm font-semibold text-[var(--color-ink-900)]">Defect inspector</h3>
              <dl className="mt-3 space-y-3 text-sm">
                <div>
                  <dt className="text-xs uppercase tracking-wide text-[var(--color-ink-500)]">Type</dt>
                  <dd className="text-[var(--color-ink-900)]">{selected.defect_type}</dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-wide text-[var(--color-ink-500)]">Description</dt>
                  <dd className="text-[var(--color-ink-900)]">{selected.description}</dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-wide text-[var(--color-ink-500)]">Detected by</dt>
                  <dd className="text-[var(--color-ink-900)]">{selected.detected_by}</dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-wide text-[var(--color-ink-500)]">Verification status</dt>
                  <dd className="text-[var(--color-ink-900)]">{selected.verification_status}</dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-wide text-[var(--color-ink-500)]">Human review required</dt>
                  <dd className="text-[var(--color-ink-900)]">{selected.human_review_required ? 'Yes' : 'No'}</dd>
                </div>
                {selected.resolution_note && (
                  <div>
                    <dt className="text-xs uppercase tracking-wide text-[var(--color-ink-500)]">Resolution</dt>
                    <dd className="text-[var(--color-ink-900)]">{selected.resolution_note}</dd>
                  </div>
                )}
              </dl>
            </div>
          ) : (
            <div className="text-sm text-[var(--color-ink-400)]">Select a defect to inspect it.</div>
          )}
        </div>
      </div>
    </div>
  )
}
