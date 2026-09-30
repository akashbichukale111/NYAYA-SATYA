import type { ReactNode } from "react";

export function Panel({ title, actions, children }: { title?: string; actions?: ReactNode; children: ReactNode }) {
  return (
    <div className="rounded-lg border border-brand-border bg-brand-panel/60 p-4">
      {(title || actions) && (
        <div className="mb-3 flex items-center justify-between">
          {title && <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-400">{title}</h3>}
          {actions}
        </div>
      )}
      {children}
    </div>
  );
}

const STATUS_COLORS: Record<string, string> = {
  KNOWN: "bg-slate-700 text-slate-200",
  VERIFIED: "bg-emerald-900 text-emerald-300",
  UNVERIFIED: "bg-amber-900 text-amber-300",
  UNKNOWN: "bg-slate-700 text-slate-300",
  CONFLICTING: "bg-red-900 text-red-300",
  BLOCKED: "bg-red-950 text-red-300",
  SUPERSEDED: "bg-purple-950 text-purple-300",
  EXCLUDED: "bg-slate-800 text-slate-400 line-through",
  MISSING: "bg-red-950 text-red-400",
  REQUIRES_HUMAN_REVIEW: "bg-amber-800 text-amber-100",
};

export function StatusPill({ status }: { status: string | null | undefined }) {
  if (!status) return <span className="status-pill bg-slate-800 text-slate-500">—</span>;
  return <span className={`status-pill ${STATUS_COLORS[status] ?? "bg-slate-700 text-slate-200"}`}>{status}</span>;
}

export function Button({
  children,
  onClick,
  variant = "primary",
  disabled,
  type = "button",
}: {
  children: ReactNode;
  onClick?: () => void;
  variant?: "primary" | "secondary" | "danger";
  disabled?: boolean;
  type?: "button" | "submit";
}) {
  const styles = {
    primary: "bg-brand-accent text-slate-900 hover:bg-teal-300",
    secondary: "bg-slate-800 text-slate-100 hover:bg-slate-700 border border-brand-border",
    danger: "bg-red-900 text-red-100 hover:bg-red-800",
  }[variant];
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed ${styles}`}
    >
      {children}
    </button>
  );
}

export function EmptyState({ message }: { message: string }) {
  return <p className="py-6 text-center text-sm text-slate-500">{message}</p>;
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="rounded-md border border-red-900 bg-red-950/40 px-3 py-2 text-sm text-red-300">{message}</div>
  );
}

export function LoadingState() {
  return <p className="py-6 text-center text-sm text-slate-500">Loading…</p>;
}

export function DemoBanner() {
  return (
    <div className="mb-4 rounded-md border border-amber-800 bg-amber-950/40 px-3 py-2 text-xs font-medium tracking-wide text-amber-300">
      DEMONSTRATION DATA — NOT A REAL CASE
    </div>
  );
}
