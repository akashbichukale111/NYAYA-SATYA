import { NavLink, Outlet, useParams } from 'react-router-dom'
import { useSession } from '../lib/session'

const navItemClass = ({ isActive }: { isActive: boolean }) =>
  `block rounded px-3 py-1.5 text-sm transition-colors ${
    isActive
      ? 'bg-[var(--color-ink-800)] text-white'
      : 'text-[var(--color-ink-300)] hover:bg-[var(--color-ink-800)]/60 hover:text-white'
  }`

export function Layout() {
  const { user, signOut } = useSession()
  const { caseId, packageId } = useParams()

  return (
    <div className="flex h-full">
      <aside className="flex w-60 shrink-0 flex-col bg-[var(--color-ink-950)] px-3 py-4 text-[var(--color-ink-300)]">
        <div className="mb-6 px-3">
          <div className="font-mono text-[11px] uppercase tracking-wide text-[var(--color-accent-400)]">
            Project 08
          </div>
          <div className="text-base font-semibold text-white">Registry Defect Engine</div>
          <div className="mt-1 text-xs text-[var(--color-ink-400)]">
            Find the filing defect before it becomes the case bottleneck.
          </div>
        </div>

        <nav className="flex flex-col gap-0.5">
          <NavLink to="/" end className={navItemClass}>
            Command Center
          </NavLink>
          <NavLink to="/cases" className={navItemClass}>
            Cases
          </NavLink>

          {caseId && (
            <>
              <div className="mt-3 px-3 text-[10px] uppercase tracking-wide text-[var(--color-ink-500)]">
                Current case
              </div>
              <NavLink to={`/cases/${caseId}`} end className={navItemClass}>
                Filing Packages
              </NavLink>
            </>
          )}

          {packageId && (
            <>
              <div className="mt-3 px-3 text-[10px] uppercase tracking-wide text-[var(--color-ink-500)]">
                Filing package
              </div>
              <NavLink to={`/packages/${packageId}/documents`} className={navItemClass}>
                Documents
              </NavLink>
              <NavLink to={`/packages/${packageId}/requirements`} className={navItemClass}>
                Requirements
              </NavLink>
              <NavLink to={`/packages/${packageId}/checklist`} className={navItemClass}>
                Checklist
              </NavLink>
              <NavLink to={`/packages/${packageId}/defects`} className={navItemClass}>
                Defects
              </NavLink>
              <NavLink to={`/packages/${packageId}/objections`} className={navItemClass}>
                Registry Objections
              </NavLink>
              <NavLink to={`/packages/${packageId}/corrections`} className={navItemClass}>
                Corrections
              </NavLink>
              <NavLink to={`/packages/${packageId}/review-queue`} className={navItemClass}>
                Review Queue
              </NavLink>
              <NavLink to={`/packages/${packageId}/audit`} className={navItemClass}>
                Audit
              </NavLink>
            </>
          )}
        </nav>

        <div className="mt-auto px-3 pt-4 text-xs text-[var(--color-ink-400)]">
          {user && (
            <div className="flex items-center justify-between gap-2">
              <div>
                <div className="text-[var(--color-ink-200)]">{user.name}</div>
                <div className="font-mono text-[10px]">{user.role}</div>
              </div>
              <button onClick={signOut} className="text-[var(--color-ink-400)] underline hover:text-white">
                Sign out
              </button>
            </div>
          )}
        </div>
      </aside>

      <main className="flex-1 overflow-y-auto bg-[var(--color-ink-50)]">
        <Outlet />
      </main>
    </div>
  )
}
