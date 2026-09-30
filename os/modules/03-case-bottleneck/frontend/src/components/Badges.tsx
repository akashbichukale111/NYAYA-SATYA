import type { ReactNode } from "react";

export function ConfidenceBadge({ value }: { value: string }) {
  const cls = `badge badge-${value}`;
  return (
    <span className={cls}>
      <span className="badge-dot" style={{ background: "currentColor" }} />
      {value}
    </span>
  );
}

export function AttentionBadge({ value }: { value: string }) {
  const key = value.replace(/ /g, "_");
  return <span className={`badge badge-${key}`}>{value}</span>;
}

export function ModeFlag({ children }: { children: ReactNode }) {
  return <div className="mode-flag">{children}</div>;
}

export function ErrorBanner({ message }: { message: string }) {
  return <div className="toast error" style={{ position: "static", marginBottom: 14 }}>{message}</div>;
}

export function EmptyState({ children }: { children: ReactNode }) {
  return <div className="empty-state">{children}</div>;
}

export function Spinner() {
  return <span className="spinner" aria-label="Loading" />;
}

export function StatusPill({ status }: { status: string }) {
  const tone =
    status === "COMPLETED" || status === "RESOLVED" ? "CONFIRMED" :
    status === "VERIFICATION_FAILED" || status === "REJECTED" ? "UNKNOWN" :
    status === "PENDING_APPROVAL" || status === "ACTION_PENDING_APPROVAL" ? "LIKELY" :
    "POSSIBLE";
  return <span className={`badge badge-${tone}`}>{status.replace(/_/g, " ")}</span>;
}
