import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { useCaseContext } from "../lib/case-context";
import { EmptyState, ErrorState, LoadingState, Panel, StatusPill } from "../components/ui";

export default function SimulationResultPage() {
  const { simulationId } = useCaseContext();

  const simQuery = useQuery({
    queryKey: ["simulation", simulationId],
    queryFn: () => api.getSimulation(simulationId!),
    enabled: !!simulationId,
  });

  if (!simulationId) {
    return <EmptyState message="Run a simulation from the Scenario Builder to see results here." />;
  }

  if (simQuery.isLoading) return <LoadingState />;
  if (simQuery.isError) return <ErrorState message={(simQuery.error as Error).message} />;

  const sim = simQuery.data;
  if (!sim) return null;

  if (sim.status === "FAILED" || !sim.result) {
    return (
      <div className="flex flex-col gap-4">
        <h1 className="text-xl font-semibold text-slate-100">Simulation Result</h1>
        <ErrorState message={sim.result?.error ?? "Simulation failed. No result was produced."} />
      </div>
    );
  }

  const r = sim.result;
  const br = r.blast_radius;

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-100">Simulation Result</h1>
        <p className="mt-1 text-sm font-mono text-xs text-slate-500">{sim.id}</p>
        {sim.human_review_required && (
          <p className="mt-2 inline-block rounded-md border border-amber-800 bg-amber-950/40 px-2 py-1 text-xs text-amber-300">
            This simulation flagged items requiring human review.
          </p>
        )}
      </div>

      <Panel title="Blast radius">
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <Metric label="Total affected" value={br.total_affected_count} />
          <Metric label="Directly affected" value={br.directly_affected_nodes.length} />
          <Metric label="Indirectly affected" value={br.indirectly_affected_nodes.length} />
          <Metric label="New conflicts" value={br.new_conflicts.length} />
          <Metric label="New blocks" value={br.new_blocks.length} />
          <Metric label="New unknowns" value={br.new_unknowns.length} />
          <Metric label="Verification gaps" value={br.verification_gaps.length} />
          <Metric label="Human review items" value={br.human_review_items.length} />
        </div>
      </Panel>

      <Panel title="Before / after (Diff)">
        {r.diff.changed_nodes.length === 0 ? (
          <EmptyState message="No node status changes detected." />
        ) : (
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="text-xs uppercase text-slate-500">
                <th className="pb-2">Node</th>
                <th className="pb-2">Real (base)</th>
                <th className="pb-2">Simulated</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-brand-border">
              {r.diff.changed_nodes.map((c) => (
                <tr key={c.node_id}>
                  <td className="py-2 pr-4 text-slate-200">{c.label}</td>
                  <td className="py-2 pr-4">
                    <StatusPill status={c.base_status ?? undefined} />
                  </td>
                  <td className="py-2">
                    <StatusPill status={c.simulated_status ?? "REMOVED"} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>

      <Panel title="Failure tree">
        {r.failure_trees.map((tree, i) => (
          <div key={i} className="mb-4 last:mb-0">
            <p className="mb-2 text-xs font-mono text-slate-500">Root failure: {tree.root_failure}</p>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              <TreeBranch label="Direct impact" leaves={tree.direct_impact} />
              <TreeBranch label="Dependency impact" leaves={tree.dependency_impact} />
              <TreeBranch label="Verification impact" leaves={tree.verification_impact} />
              <TreeBranch label="Workflow impact" leaves={tree.workflow_impact} />
            </div>
            {tree.human_review.length > 0 && (
              <div className="mt-3">
                <TreeBranch label="Human review required" leaves={tree.human_review} />
              </div>
            )}
          </div>
        ))}
      </Panel>

      <Panel title="Recovery options (require human approval)">
        {r.recovery_options.length === 0 ? (
          <EmptyState message="No recovery options were proposed for this simulation." />
        ) : (
          <ul className="flex flex-col gap-2">
            {r.recovery_options.map((opt, i) => (
              <li key={i} className="rounded-md border border-brand-border bg-brand-bg p-3 text-sm">
                <p className="font-medium text-slate-200">{opt.action}</p>
                <p className="mt-1 text-xs text-slate-400">{opt.reason}</p>
                <p className="mt-1 text-xs text-slate-500">
                  Human approval required · Verification required
                </p>
              </li>
            ))}
          </ul>
        )}
      </Panel>

      {r.explanation && (
        <Panel title="Scenario explanation (LLM-assisted, non-authoritative)">
          <p className="text-sm text-slate-300">{r.explanation}</p>
        </Panel>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border border-brand-border bg-brand-bg px-3 py-3">
      <p className="text-2xl font-semibold text-slate-100">{value}</p>
      <p className="mt-1 text-xs text-slate-500">{label}</p>
    </div>
  );
}

function TreeBranch({ label, leaves }: { label: string; leaves: { node_id: string; label: string }[] }) {
  return (
    <div className="rounded-md border border-brand-border bg-brand-bg p-2">
      <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
      {leaves.length === 0 ? (
        <p className="text-xs text-slate-600">None</p>
      ) : (
        <ul className="flex flex-col gap-1">
          {leaves.map((l) => (
            <li key={l.node_id} className="text-xs text-slate-300">
              {l.label}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
