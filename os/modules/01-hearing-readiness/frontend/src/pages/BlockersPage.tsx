import { Link } from "react-router-dom";
import { useSelectedCase } from "../lib/selectedCase";
import { api } from "../lib/api";
import { useAsync } from "../hooks/useAsync";
import { PageHeader, Panel } from "../components/Panel";
import { SeverityBadge, ConfidenceTag } from "../components/ReadinessBadge";
import { LoadingState, ErrorState, EmptyState } from "../components/StatusStates";

export default function BlockersPage() {
  const { caseId } = useSelectedCase();
  const blockers = useAsync(() => (caseId ? api.listBlockers(caseId) : Promise.reject("no case")), [caseId]);

  if (!caseId) return <EmptyState message="No case selected." />;
  if (blockers.loading) return <LoadingState />;
  if (blockers.error) return <ErrorState message={blockers.error} onRetry={blockers.reload} />;

  const open = (blockers.data ?? []).filter((b) => b.status === "OPEN");
  const resolved = (blockers.data ?? []).filter((b) => b.status !== "OPEN");

  return (
    <div>
      <PageHeader title="Blockers" subtitle="Only shown when a specific requirement is unresolved and matters for the next hearing." />

      <Panel title={`Open (${open.length})`} className="mb-6">
        {open.length === 0 ? (
          <EmptyState message="No open blockers." />
        ) : (
          <ul className="space-y-2">
            {open.map((b) => (
              <li key={b.id}>
                <Link
                  to={`/blockers/${b.id}`}
                  className="flex flex-col gap-1 rounded-md border border-[var(--hairline)] px-4 py-3 hover:bg-[var(--ink-800)]"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium">{b.description}</span>
                    <SeverityBadge severity={b.severity} />
                  </div>
                  <p className="text-xs text-[var(--text-secondary)]">{b.downstream_impact}</p>
                  <div className="flex items-center gap-2">
                    <ConfidenceTag confidence={b.confidence} />
                    {b.responsible_actor && (
                      <span className="text-xs text-[var(--text-muted)]">Responsible: {b.responsible_actor}</span>
                    )}
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Panel>

      <Panel title={`Resolved / other (${resolved.length})`}>
        {resolved.length === 0 ? (
          <EmptyState />
        ) : (
          <ul className="space-y-2">
            {resolved.map((b) => (
              <li key={b.id} className="flex items-center justify-between rounded-md border border-[var(--hairline)] px-4 py-2 text-sm">
                <span className="text-[var(--text-secondary)] line-through">{b.description}</span>
                <span className="text-xs text-[var(--state-ready)]">{b.status}</span>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}
