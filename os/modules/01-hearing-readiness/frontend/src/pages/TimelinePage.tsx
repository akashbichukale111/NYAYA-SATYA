import { useSelectedCase } from "../lib/selectedCase";
import { api } from "../lib/api";
import { useAsync } from "../hooks/useAsync";
import { PageHeader, Panel } from "../components/Panel";
import { LoadingState, ErrorState, EmptyState } from "../components/StatusStates";

export default function TimelinePage() {
  const { caseId } = useSelectedCase();
  const actions = useAsync(() => (caseId ? api.listActions(caseId) : Promise.reject("no case")), [caseId]);

  if (!caseId) return <EmptyState message="No case selected." />;
  if (actions.loading) return <LoadingState />;
  if (actions.error) return <ErrorState message={actions.error} onRetry={actions.reload} />;

  const sorted = [...(actions.data ?? [])];

  return (
    <div>
      <PageHeader title="Timeline" subtitle="Every proposed action, in order, from proposal through verification." />
      <Panel>
        {sorted.length === 0 ? (
          <EmptyState message="No actions proposed yet. Run an agent pass from the Cases page." />
        ) : (
          <ol className="relative space-y-4 border-l border-[var(--hairline)] pl-6">
            {sorted.map((a) => (
              <li key={a.id} className="relative">
                <span className="absolute -left-[29px] top-1 h-3 w-3 rounded-full border-2 border-[var(--ink-950)] bg-[var(--brass-400)]" />
                <div className="rounded-md border border-[var(--hairline)] px-4 py-3">
                  <div className="mb-1 flex items-center justify-between">
                    <span className="font-medium">{a.description}</span>
                    <span className="rounded bg-[var(--ink-700)] px-2 py-0.5 text-xs font-mono">{a.status}</span>
                  </div>
                  <p className="text-xs text-[var(--text-secondary)]">{a.expected_effect}</p>
                </div>
              </li>
            ))}
          </ol>
        )}
      </Panel>
    </div>
  );
}
