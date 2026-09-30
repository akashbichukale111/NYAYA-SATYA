import type { ReactNode } from 'react'
import { ApiError } from '../api'

const STATE_STYLES: Record<string, string> = {
  VERIFIED: 'bg-signal-verified/15 text-signal-verified border border-signal-verified/30',
  SUPPORTED: 'bg-signal-verified/15 text-signal-verified border border-signal-verified/30',
  DOCUMENT_SUPPORTED: 'bg-signal-verified/15 text-signal-verified border border-signal-verified/30',
  PARTIALLY_SUPPORTED: 'bg-signal-review/15 text-signal-review border border-signal-review/30',
  USER_REPORTED: 'bg-signal-review/15 text-signal-review border border-signal-review/30',
  UNVERIFIED: 'bg-ink-600/30 text-parchment-200 border border-ink-500/40',
  REQUIRES_HUMAN_REVIEW: 'bg-signal-review/15 text-signal-review border border-signal-review/30',
  PENDING_REVIEW: 'bg-signal-review/15 text-signal-review border border-signal-review/30',
  CONTRADICTED: 'bg-signal-conflict/15 text-signal-conflict border border-signal-conflict/30',
  CONFLICTING: 'bg-signal-conflict/15 text-signal-conflict border border-signal-conflict/30',
  REJECTED: 'bg-signal-conflict/15 text-signal-conflict border border-signal-conflict/30',
  SUPERSEDED: 'bg-ink-600/30 text-parchment-200 border border-ink-500/40',
  EXCLUDED: 'bg-signal-conflict/15 text-signal-conflict border border-signal-conflict/30',
  MISSING: 'bg-signal-conflict/15 text-signal-conflict border border-signal-conflict/30',
  UNKNOWN: 'bg-ink-600/30 text-parchment-200/70 border border-ink-500/40',
  PENDING: 'bg-signal-review/15 text-signal-review border border-signal-review/30',
  APPROVED: 'bg-signal-verified/15 text-signal-verified border border-signal-verified/30',
  NONE: 'bg-ink-600/30 text-parchment-200/70 border border-ink-500/40',
  LOW: 'bg-signal-review/15 text-signal-review border border-signal-review/30',
  MODERATE: 'bg-signal-review/20 text-signal-review border border-signal-review/40',
  SINGLE_POINT_DEPENDENCY: 'bg-signal-conflict/20 text-signal-conflict border border-signal-conflict/40',
  PASS: 'bg-signal-verified/15 text-signal-verified border border-signal-verified/30',
  FAIL: 'bg-signal-conflict/15 text-signal-conflict border border-signal-conflict/30',
  NOT_RUN: 'bg-ink-600/30 text-parchment-200/70 border border-ink-500/40',
}

export function StatusPill({ label }: { label: string }) {
  const cls = STATE_STYLES[label] ?? 'bg-ink-600/30 text-parchment-200 border border-ink-500/40'
  return <span className={`status-pill ${cls}`}>{label.replace(/_/g, ' ')}</span>
}

export function SourceLocation({ known, page, section }: { known: boolean; page: number | null; section: string | null }) {
  if (!known || (page === null && !section)) {
    return <span className="text-xs font-mono text-parchment-200/50 italic">SOURCE_LOCATION_UNKNOWN</span>
  }
  return (
    <span className="text-xs font-mono text-parchment-200/70">
      {section ? `${section}` : ''}{section && page ? ' · ' : ''}{page ? `p. ${page}` : ''}
    </span>
  )
}

export function LoadingState({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 py-8 justify-center text-parchment-200/50 text-sm">
      <span className="h-3 w-3 rounded-full border-2 border-parchment-200/30 border-t-parchment-200 animate-spin" />
      {label}
    </div>
  )
}

export function ErrorState({ error }: { error: unknown }) {
  const message = error instanceof ApiError ? error.message : error instanceof Error ? error.message : 'Something went wrong.'
  return (
    <div className="rounded-lg border border-signal-conflict/40 bg-signal-conflict/10 px-4 py-3 text-sm text-signal-conflict">
      {message}
    </div>
  )
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="rounded-lg border border-dashed border-ink-600 px-4 py-8 text-center">
      <p className="text-sm text-parchment-200/70">{title}</p>
      {hint && <p className="mt-1 text-xs text-parchment-200/40">{hint}</p>}
    </div>
  )
}

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <div className={`card p-4 ${className}`}>{children}</div>
}

export function SectionHeading({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-4">
      <h2 className="font-serif text-xl text-parchment-50">{title}</h2>
      {subtitle && <p className="mt-0.5 text-sm text-parchment-200/50">{subtitle}</p>}
    </div>
  )
}
