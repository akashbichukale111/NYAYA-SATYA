import { useState } from "react";
import { useSelectedCase } from "../lib/selectedCase";
import { api } from "../lib/api";
import { useAsync } from "../hooks/useAsync";
import { PageHeader, Panel } from "../components/Panel";
import { ReadinessBadge, ConfidenceTag } from "../components/ReadinessBadge";
import { LoadingState, ErrorState, EmptyState } from "../components/StatusStates";

const STATUS_COLOR: Record<string, string> = {
  SATISFIED: "text-[var(--state-ready)]",
  UNRESOLVED: "text-[var(--state-blocked)]",
  UNKNOWN: "text-[var(--state-unknown)]",
};

export default function ReadinessPage() {
  const { caseId } = useSelectedCase();
  const [running, setRunning] = useState(false);
  const caseData = useAsync(() => (caseId ? api.getCase(caseId) : Promise.reject("no case")), [caseId]);
  const readiness = useAsync(() => (caseId ? api.getReadiness(caseId) : Promise.reject("no case")), [caseId]);

  if (!caseId) return <EmptyState message="No case selected." />;
  if (caseData.loading || readiness.loading) return <LoadingState />;
  if (caseData.error) return <ErrorState message={caseData.error} onRetry={caseData.reload} />;
  if (readiness.error) return <ErrorState message={readiness.error} onRetry={readiness.reload} />;

  const full = caseData.data!;
  const snap = readiness.data!;

  const runAudit = async () => {
    if (!caseId) return;
    setRunning(true);
    try {
      await api.runReadinessAudit(caseId);
      readiness.reload();
      caseData.reload();
    } finally {
      setRunning(false);
    }
  };

  return (
    <div>
      <PageHeader
        title="Readiness"
        subtitle="Evidence-backed, category-level readiness — never a single opaque score."
        action={
          <button
            onClick={runAudit}
            disabled={running}
            className="rounded-md bg-[var(--brass-500)] px-3 py-2 text-sm font-medium text-[var(--ink-950)] hover:bg-[var(--brass-400)] disabled:opacity-50"
          >
            {running ? "Running…" : "Re-run readiness audit"}
          </button>
        }
      />

      <div className="mb-6">
        <ReadinessBadge state={snap.overall} size="lg" />
      </div>

      <Panel title="By category" className="mb-6">
        {Object.keys(snap.categories).length === 0 ? (
          <EmptyState message="No requirements defined for this case yet." />
        ) : (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            {Object.entries(snap.categories).map(([category, state]) => (
              <div key={category} className="rounded-md border border-[var(--hairline)] px-3 py-2">
                <div className="text-xs text-[var(--text-muted)]">{category}</div>
                <div className={`mt-1 text-sm font-medium ${STATUS_COLOR[state] ?? ""}`}>{state}</div>
              </div>
            ))}
          </div>
        )}
      </Panel>

      <Panel title="Requirements">
        {full.requirements.length === 0 ? (
          <EmptyState />
        ) : (
          <ul className="space-y-2">
            {full.requirements.map((r) => (
              <li key={r.id} className="rounded-md border border-[var(--hairline)] px-3 py-2 text-sm">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium">{r.description}</span>
                  <span className={`shrink-0 text-xs font-medium ${STATUS_COLOR[r.status] ?? ""}`}>{r.status}</span>
                </div>
                <div className="mt-1 flex items-center gap-2 text-xs text-[var(--text-muted)]">
                  <span className="rounded bg-[var(--ink-700)] px-1.5 py-0.5">{r.category}</span>
                  <ConfidenceTag confidence={r.confidence} />
                </div>
                <p className="mt-1 text-xs text-[var(--text-secondary)]">{r.reason}</p>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}
