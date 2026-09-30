import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useSession } from '../lib/session'

const ROLES = [
  { value: 'CITIZEN', label: 'Citizen', blurb: 'Filing on your own behalf' },
  { value: 'LEGAL_AID', label: 'Legal Aid', blurb: 'Supporting citizens through a legal-aid org' },
  { value: 'ADVOCATE', label: 'Advocate', blurb: 'Reviews and confirms defects, approves corrections' },
  { value: 'ADMIN', label: 'Admin', blurb: 'Full oversight across cases' },
]

export function SignInPage() {
  const { signIn } = useSession()
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [role, setRole] = useState('ADVOCATE')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      await signIn(name.trim() || 'Unnamed User', email.trim(), role)
      navigate('/')
    } catch {
      setError('Could not create a session. Check the backend is running and try again.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex h-full items-center justify-center bg-[var(--color-ink-950)] px-4">
      <div className="w-full max-w-sm rounded-lg border border-[var(--color-ink-800)] bg-[var(--color-ink-900)] p-6">
        <div className="mb-1 font-mono text-[11px] uppercase tracking-wide text-[var(--color-accent-400)]">
          Project 08
        </div>
        <h1 className="mb-1 text-lg font-semibold text-white">Registry Defect Engine</h1>
        <p className="mb-5 text-sm text-[var(--color-ink-400)]">
          Sign in to open a case. This build has no password auth yet — see docs/security.md — a
          session is just an identified role for RBAC and audit purposes.
        </p>

        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <label className="text-sm text-[var(--color-ink-300)]">
            Name
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="mt-1 w-full rounded border border-[var(--color-ink-700)] bg-[var(--color-ink-950)] px-3 py-2 text-sm text-white outline-none focus:border-[var(--color-accent-500)]"
              placeholder="Your name"
              required
            />
          </label>
          <label className="text-sm text-[var(--color-ink-300)]">
            Email
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 w-full rounded border border-[var(--color-ink-700)] bg-[var(--color-ink-950)] px-3 py-2 text-sm text-white outline-none focus:border-[var(--color-accent-500)]"
              placeholder="you@example.org"
              required
            />
          </label>
          <fieldset className="text-sm text-[var(--color-ink-300)]">
            <legend className="mb-1">Role</legend>
            <div className="flex flex-col gap-1.5">
              {ROLES.map((r) => (
                <label
                  key={r.value}
                  className={`flex cursor-pointer items-start gap-2 rounded border px-3 py-2 ${
                    role === r.value
                      ? 'border-[var(--color-accent-500)] bg-[var(--color-accent-600)]/10'
                      : 'border-[var(--color-ink-700)]'
                  }`}
                >
                  <input
                    type="radio"
                    name="role"
                    value={r.value}
                    checked={role === r.value}
                    onChange={() => setRole(r.value)}
                    className="mt-0.5"
                  />
                  <span>
                    <span className="block text-[var(--color-ink-100)]">{r.label}</span>
                    <span className="block text-xs text-[var(--color-ink-500)]">{r.blurb}</span>
                  </span>
                </label>
              ))}
            </div>
          </fieldset>

          {error && <div className="text-sm text-[var(--color-review-600)]">{error}</div>}

          <button
            type="submit"
            disabled={busy}
            className="mt-1 rounded bg-[var(--color-accent-500)] px-3 py-2 text-sm font-medium text-white hover:bg-[var(--color-accent-600)] disabled:opacity-50"
          >
            {busy ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      </div>
    </div>
  )
}
