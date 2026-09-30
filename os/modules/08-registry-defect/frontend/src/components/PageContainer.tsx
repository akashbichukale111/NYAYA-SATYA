import type { ReactNode } from 'react'

export function PageContainer({ children }: { children: ReactNode }) {
  return <div className="mx-auto max-w-5xl px-8 py-8">{children}</div>
}
