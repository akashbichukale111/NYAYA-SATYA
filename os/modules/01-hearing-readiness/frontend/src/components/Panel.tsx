import type { ReactNode } from "react";

export function Panel({ title, action, children, className = "" }: {
  title?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`rounded-lg border border-[var(--hairline)] bg-[var(--ink-900)] ${className}`}>
      {(title || action) && (
        <div className="flex items-center justify-between border-b border-[var(--hairline)] px-5 py-3">
          {title && <h3 className="text-sm font-semibold text-[var(--text-primary)]" style={{ fontFamily: "var(--font-sans)" }}>{title}</h3>}
          {action}
        </div>
      )}
      <div className="px-5 py-4">{children}</div>
    </section>
  );
}

export function PageHeader({ title, subtitle, action }: { title: string; subtitle?: string; action?: ReactNode }) {
  return (
    <div className="mb-6 flex items-start justify-between gap-4">
      <div>
        <h1 className="text-2xl">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-[var(--text-secondary)]">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

export function StatGrid({ items }: { items: { label: string; value: string | number }[] }) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {items.map((item) => (
        <div key={item.label} className="rounded-md border border-[var(--hairline)] bg-[var(--ink-800)] px-4 py-3">
          <div className="text-2xl font-serif">{item.value}</div>
          <div className="mt-0.5 text-xs text-[var(--text-muted)]">{item.label}</div>
        </div>
      ))}
    </div>
  );
}
