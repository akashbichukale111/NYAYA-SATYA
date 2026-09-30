import { useState } from "react";
import { useSelectedCase } from "../lib/selectedCase";
import { api, type SimulationResult } from "../lib/api";
import { useAsync } from "../hooks/useAsync";
import { PageHeader, Panel } from "../components/Panel";
import { ReadinessBadge } from "../components/ReadinessBadge";
import { LoadingState, ErrorState, EmptyState } from "../components/StatusStates";

export default function SimulatePage() {
  const { caseId } = useSelectedCase();
  const [selected, setSelected] = useState<string[]>([]);
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const evidence = useAsync(() => (caseId ? api.listEvidence(caseId) : Promise.reject("no case")), [caseId]);

  if (!caseId) return <EmptyState message="No case selected." />;

  const toggle = (id: string) => {
    setSelected((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  };

  const runSimulation = async () => {
    setRunning(true);
    setError(null);
    try {
      const hypothesis = selected.map((id) => ({ type: "resolve_evidence", evidence_id: id }));
      const sim = await api.simulate(caseId, hypothesis);
      setResult(sim);
    } catch (e) {
      setError(String(e));
    } finally {
      setRunning(false);
    }
  };

  const missingItems = (evidence.data ?? []).filter((e) => e.availability !== "AVAILABLE" || e.verification_state !== "VERIFIED");

  return (
    <div>
      <PageHeader
        title="Simulate"
        subtitle="What-if analysis. Nothing here ever changes real case state — results are labeled SIMULATION ONLY."
      />

      <Panel title="Choose evidence to hypothetically resolve" className="mb-6">
        {evidence.loading && <LoadingState />}
        {evidence.error && <ErrorState message={evidence.error} onRetry={evidence.reload} />}
        {missingItems.length === 0 ? (
          <EmptyState message="All evidence is already available and verified — nothing to simulate resolving." />
        ) : (
          <ul className="space-y-2">
            {missingItems.map((e) => (
              <li key={e.id}>
                <label className="flex cursor-pointer items-center gap-2 rounded-md border border-[var(--hairline)] px-3 py-2 text-sm hover:bg-[var(--ink-800)]">
                  <input type="checkbox" checked={selected.includes(e.id)} onChange={() => toggle(e.id)} />
                  <span>{e.label}</span>
                  <span className="ml-auto text-xs text-[var(--text-muted)]">
                    {e.availability} / {e.verification_state}
                  </span>
                </label>
              </li>
            ))}
          </ul>
        )}
        <button
          onClick={runSimulation}
          disabled={running || selected.length === 0}
          className="mt-4 rounded-md bg-[var(--brass-500)] px-3 py-2 text-sm font-medium text-[var(--ink-950)] hover:bg-[var(--brass-400)] disabled:opacity-50"
        >
          {running ? "Simulating…" : `Simulate resolving ${selected.length} item(s)`}
        </button>
        {error && <p className="mt-2 text-xs text-[var(--state-blocked)]">{error}</p>}
      </Panel>

      {result && (
        <Panel title="SIMULATION ONLY — result">
          <div className="mb-4 flex items-center gap-4">
            <div>
              <div className="mb-1 text-xs text-[var(--text-muted)]">Baseline</div>
              <ReadinessBadge state={result.baseline_readiness.overall} />
            </div>
            <div className="text-[var(--text-muted)]">→</div>
            <div>
              <div className="mb-1 text-xs text-[var(--text-muted)]">Simulated</div>
              <ReadinessBadge state={result.simulated_readiness.overall} />
            </div>
          </div>

          {result.diff.resolved_blockers.length > 0 ? (
            <p className="text-sm text-[var(--state-ready)]">
              {result.diff.resolved_blockers.length} blocker(s) would resolve under this hypothesis.
            </p>
          ) : (
            <p className="text-sm text-[var(--text-secondary)]">No blockers would resolve under this hypothesis.</p>
          )}

          {Object.keys(result.diff.category_changes).length > 0 && (
            <div className="mt-3 space-y-1 text-sm">
              {Object.entries(result.diff.category_changes).map(([cat, change]) => (
                <div key={cat}>
                  <span className="text-[var(--text-muted)]">{cat}: </span>
                  {change.before} → {change.after}
                </div>
              ))}
            </div>
          )}
        </Panel>
      )}
    </div>
  );
}
