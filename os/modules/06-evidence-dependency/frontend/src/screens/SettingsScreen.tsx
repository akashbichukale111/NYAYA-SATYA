import { useState } from 'react'
import { actor } from '../api'
import { Card, SectionHeading } from '../components/primitives'

const ROLES = ['CITIZEN', 'LEGAL_AID', 'ADVOCATE', 'ADMIN'] as const

export function SettingsScreen({ onChange }: { onChange: () => void }) {
  const [userId, setUserId] = useState(actor.userId)
  const [role, setRole] = useState(actor.role)

  return (
    <div className="max-w-lg space-y-6">
      <SectionHeading
        title="Settings"
        subtitle="Local session identity. There is no login system in this build — this simulates roles for RBAC testing (see docs/security.md)."
      />
      <Card className="space-y-4">
        <div>
          <label className="mb-1 block text-xs text-parchment-200/50">User ID</label>
          <input
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            className="focus-ring w-full rounded-md border border-ink-600 bg-ink-800 px-3 py-2 text-sm text-parchment-100"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs text-parchment-200/50">Role</label>
          <div className="flex gap-2">
            {ROLES.map((r) => (
              <button
                key={r}
                onClick={() => setRole(r)}
                className={`focus-ring rounded-md border px-3 py-1.5 text-xs ${
                  role === r ? 'border-parchment-200 bg-parchment-200 text-ink-950' : 'border-ink-600 text-parchment-200/70 hover:border-ink-500'
                }`}
              >
                {r}
              </button>
            ))}
          </div>
        </div>
        <button
          onClick={() => {
            actor.userId = userId
            actor.role = role
            onChange()
          }}
          className="focus-ring w-full rounded-md border border-signal-verified/40 bg-signal-verified/10 px-3 py-2 text-sm font-medium text-signal-verified hover:bg-signal-verified/20"
        >
          Apply
        </button>
        <p className="text-xs text-parchment-200/40">
          Approving or rejecting a review task requires role Advocate or higher. A Citizen viewing another user's
          non-demo case will be denied — try switching roles and reloading a case to see enforcement in action.
        </p>
      </Card>
    </div>
  )
}
