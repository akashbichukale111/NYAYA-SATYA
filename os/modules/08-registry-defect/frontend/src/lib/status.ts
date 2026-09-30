/**
 * Central mapping from backend enum values to visual treatment. Keeping
 * this in one place means adding a new enum value never requires
 * hunting through every page for ad-hoc color logic.
 */

export function severityClasses(severity: string): string {
  switch (severity) {
    case 'REQUIRES_HUMAN_REVIEW':
      return 'bg-[var(--color-review-100)] text-[var(--color-review-700)] border-[var(--color-review-700)]/20'
    case 'HIGH_ATTENTION':
      return 'bg-[var(--color-attention-100)] text-[var(--color-attention-700)] border-[var(--color-attention-700)]/20'
    case 'ATTENTION':
      return 'bg-[var(--color-accent-100)] text-[var(--color-accent-600)] border-[var(--color-accent-600)]/20'
    case 'INFO':
    default:
      return 'bg-[var(--color-ink-100)] text-[var(--color-ink-600)] border-[var(--color-ink-600)]/20'
  }
}

export function checklistStatusClasses(status: string): string {
  switch (status) {
    case 'FOUND':
      return 'bg-[var(--color-ok-100)] text-[var(--color-ok-700)] border-[var(--color-ok-700)]/20'
    case 'MISSING':
    case 'CONFLICTING':
      return 'bg-[var(--color-attention-100)] text-[var(--color-attention-700)] border-[var(--color-attention-700)]/20'
    case 'REQUIRES_HUMAN_REVIEW':
      return 'bg-[var(--color-review-100)] text-[var(--color-review-700)] border-[var(--color-review-700)]/20'
    case 'PARTIAL':
    case 'UNVERIFIED':
      return 'bg-[var(--color-accent-100)] text-[var(--color-accent-600)] border-[var(--color-accent-600)]/20'
    default:
      return 'bg-[var(--color-ink-100)] text-[var(--color-ink-600)] border-[var(--color-ink-600)]/20'
  }
}

export function lifecycleStateLabel(state: string): string {
  return state.replaceAll('_', ' ').toLowerCase().replace(/^\w/, (c) => c.toUpperCase())
}

export function defectStatusClasses(status: string): string {
  switch (status) {
    case 'RESOLVED':
    case 'VERIFIED':
      return 'bg-[var(--color-ok-100)] text-[var(--color-ok-700)] border-[var(--color-ok-700)]/20'
    case 'REJECTED':
    case 'FALSE_POSITIVE':
      return 'bg-[var(--color-ink-100)] text-[var(--color-ink-500)] border-[var(--color-ink-400)]/30'
    case 'DETECTED':
    case 'TRIAGED':
    case 'HUMAN_REVIEW':
      return 'bg-[var(--color-review-100)] text-[var(--color-review-700)] border-[var(--color-review-700)]/20'
    default:
      return 'bg-[var(--color-ink-100)] text-[var(--color-ink-600)] border-[var(--color-ink-600)]/20'
  }
}
