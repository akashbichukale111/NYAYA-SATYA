import React from "react";

export function SeverityBadge({ severity }: { severity: string }) {
  const label = severity.replace(/_/g, " ");
  return <span className={`badge severity-${severity}`}>{label}</span>;
}

export function StatusBadge({ status }: { status: string }) {
  return <span className="badge text-[color:var(--color-text-secondary)]">{status.replace(/_/g, " ")}</span>;
}

export function SourceChip({ documentId, snippet }: { documentId?: string | null; snippet?: string | null }) {
  if (!documentId) {
    return <span className="text-xs text-[color:var(--color-text-muted)] italic">SOURCE LOCATION UNKNOWN</span>;
  }
  return (
    <span className="text-xs text-[color:var(--color-text-secondary)]" title={snippet || undefined}>
      Source: doc {documentId.slice(0, 12)}…{snippet ? ` — "${snippet.slice(0, 80)}${snippet.length > 80 ? "…" : ""}"` : ""}
    </span>
  );
}

export function EmptyState({ label }: { label: string }) {
  return (
    <div className="card p-6 text-sm text-[color:var(--color-text-muted)]">
      {label}
    </div>
  );
}

export function SectionTitle({ children, subtitle }: { children: React.ReactNode; subtitle?: string }) {
  return (
    <div className="mb-4">
      <h2 className="text-xl font-display text-[color:var(--color-text-primary)]">{children}</h2>
      {subtitle && <p className="text-sm text-[color:var(--color-text-secondary)] mt-1">{subtitle}</p>}
    </div>
  );
}

export function Loading() {
  return <div className="text-sm text-[color:var(--color-text-muted)] p-6">Loading…</div>;
}

export function ErrorBox({ message }: { message: string }) {
  return (
    <div className="card p-4 border-[color:var(--color-review)] text-sm text-[color:var(--color-review)]">
      {message}
    </div>
  );
}
