import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { useCaseContext } from "../lib/case-context";
import { EmptyState, ErrorState, LoadingState, Panel } from "../components/ui";

export default function AuditPage() {
  const { caseId } = useCaseContext();

  const auditQuery = useQuery({
    queryKey: ["audit", caseId],
    queryFn: () => api.getAudit(caseId!),
    enabled: !!caseId,
  });

  if (!caseId) return <EmptyState message="Select a case from the Command Center first." />;

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-100">Audit</h1>
        <p className="mt-1 text-sm text-slate-500">Every consequential action against this case, in order.</p>
      </div>

      <Panel title="Event log">
        {auditQuery.isLoading && <LoadingState />}
        {auditQuery.isError && <ErrorState message={(auditQuery.error as Error).message} />}
        {auditQuery.data && auditQuery.data.length === 0 && <EmptyState message="No audit events yet." />}
        {auditQuery.data && auditQuery.data.length > 0 && (
          <ul className="flex flex-col gap-2">
            {auditQuery.data.map((ev) => (
              <li key={ev.id} className="rounded-md border border-brand-border bg-brand-bg p-3 text-sm">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs text-brand-accent">{ev.event_type}</span>
                  <span className="text-xs text-slate-500">{new Date(ev.created_at).toLocaleString()}</span>
                </div>
                <p className="mt-1 text-xs text-slate-400">actor: {ev.actor}</p>
                {Object.keys(ev.payload ?? {}).length > 0 && (
                  <pre className="mt-2 max-h-32 overflow-auto rounded bg-brand-panel/60 p-2 text-xs text-slate-500">
                    {JSON.stringify(ev.payload, null, 2)}
                  </pre>
                )}
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}
