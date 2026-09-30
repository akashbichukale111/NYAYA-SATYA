import { useI18n } from "../i18n";

const STATE_STYLES: Record<string, string> = {
  READY: "bg-[var(--state-ready)]/15 text-[var(--state-ready)] border-[var(--state-ready)]/40",
  CONDITIONAL: "bg-[var(--state-conditional)]/15 text-[var(--state-conditional)] border-[var(--state-conditional)]/40",
  BLOCKED: "bg-[var(--state-blocked)]/15 text-[var(--state-blocked)] border-[var(--state-blocked)]/40",
  UNKNOWN: "bg-[var(--state-unknown)]/15 text-[var(--state-unknown)] border-[var(--state-unknown)]/40",
};

export function ReadinessBadge({ state, size = "md" }: { state: string; size?: "sm" | "md" | "lg" }) {
  const { t } = useI18n();
  const sizeClass = size === "lg" ? "text-lg px-4 py-1.5" : size === "sm" ? "text-xs px-2 py-0.5" : "text-sm px-3 py-1";
  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full border font-medium ${sizeClass} ${
        STATE_STYLES[state] ?? STATE_STYLES.UNKNOWN
      }`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {t(`readiness.${state}` as never)}
    </span>
  );
}

const SEVERITY_STYLES: Record<string, string> = {
  LOW: "text-[var(--text-secondary)] border-[var(--hairline)]",
  MEDIUM: "text-[var(--state-conditional)] border-[var(--state-conditional)]/40",
  HIGH: "text-[var(--state-blocked)] border-[var(--state-blocked)]/40",
  CRITICAL: "text-[var(--state-blocked)] border-[var(--state-blocked)]/70 bg-[var(--state-blocked)]/10",
};

export function SeverityBadge({ severity }: { severity: string }) {
  return (
    <span className={`inline-flex items-center rounded border px-2 py-0.5 text-xs font-medium ${SEVERITY_STYLES[severity] ?? SEVERITY_STYLES.MEDIUM}`}>
      {severity}
    </span>
  );
}

export function ConfidenceTag({ confidence }: { confidence: string }) {
  return (
    <span className="inline-flex items-center rounded bg-[var(--ink-700)] px-2 py-0.5 text-xs font-mono text-[var(--text-secondary)]">
      {confidence}
    </span>
  );
}
