import { useSelectedCase } from "../lib/selectedCase";
import { api } from "../lib/api";
import { useAsync } from "../hooks/useAsync";
import { PageHeader, Panel } from "../components/Panel";
import { LoadingState, ErrorState, EmptyState } from "../components/StatusStates";

export default function AuditPage() {
  const { caseId } = useSelectedCase();
  const audit = useAsync(() => (caseId ? api.getAudit(caseId) : Promise.reject("no case")), [caseId]);

  if (!caseId) return <EmptyState message="No case selected." />;
  if (audit.loading) return <LoadingState />;
  if (audit.error) return <ErrorState message={audit.error} onRetry={audit.reload} />;

  const events = [...(audit.data ?? [])].reverse();

  return (
    <div>
      <PageHeader title="Audit" subtitle="Append-only. Every user action, agent step, tool call, and state transition." />
      <Panel>
        {events.length === 0 ? (
          <EmptyState />
        ) : (
          <ul className="scrollbar-thin max-h-[70vh] space-y-2 overflow-y-auto">
            {events.map((e) => (
              <li key={e.id} className="rounded-md border border-[var(--hairline)] px-3 py-2 text-sm">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs text-[var(--brass-400)]">{e.event_type}</span>
                  <span className="text-xs text-[var(--text-muted)]">{new Date(e.timestamp).toLocaleString()}</span>
                </div>
                <div className="mt-1">
                  <span className="text-[var(--text-muted)]">actor:</span> {e.actor} ·{" "}
                  <span className="text-[var(--text-muted)]">action:</span> {e.action}
                </div>
                <div className="mt-1 text-xs text-[var(--text-muted)]">correlation: {e.correlation_id}</div>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}
