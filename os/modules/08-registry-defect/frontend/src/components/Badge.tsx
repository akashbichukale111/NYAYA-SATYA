import type { ReactNode } from 'react'

export function Badge({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded border px-2 py-0.5 text-xs font-medium ${className}`}
    >
      {children}
    </span>
  )
}
