import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { useCaseContext } from "../lib/case-context";
import { MUTATION_GROUPS } from "../lib/mutation-taxonomy";
import { Button, EmptyState, ErrorState, LoadingState, Panel } from "../components/ui";

export default function CounterfactualLab() {
  const { caseId } = useCaseContext();
  const qc = useQueryClient();

  const [mutationType, setMutationType] = useState("");
  const [targetNodeId, setTargetNodeId] = useState("");
  const [simAId, setSimAId] = useState<string | null>(null);
  const [simBId, setSimBId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const graphQuery = useQuery({
    queryKey: ["graph", caseId],
    queryFn: () => api.getGraph(caseId!),
    enabled: !!caseId,
  });

  const snapshotsQuery = useQuery({
    queryKey: ["snapshots", caseId],
    queryFn: () => api.listSnapshots(caseId!),
    enabled: !!caseId,
  });

  const ask = useMutation({
    mutationFn: async () => {
      if (!mutationType || !targetNodeId) throw new Error("Choose both a failure type and a target node.");
      let snapshotId = snapshotsQuery.data?.[0]?.id;
      if (!snapshotId) {
        const snap = await api.createSnapshot(caseId!, "Counterfactual base snapshot");
        qc.invalidateQueries({ queryKey: ["snapshots", caseId] });
        snapshotId = snap.id;
      }
      return api.runSimulation(caseId!, {
        base_snapshot_id: snapshotId,
        inline_mutations: [{ mutation_type: mutationType, target_node_id: targetNodeId }],
        created_by: "akash",
        explain: true,
      });
    },
    onSuccess: (sim) => {
      setError(null);
      setSimAId((prev) => (prev ? prev : sim.id));
      setSimBId(sim.id);
    },
    onError: (e: Error) => setError(e.message),
  });

  const compare = useQuery({
    queryKey: ["compare", simAId, simBId],
    queryFn: () => api.compareSimulations(simAId!, simBId!),
    enabled: !!simAId && !!simBId && simAId !== simBId,
  });

  const currentSim = useQuery({
    queryKey: ["simulation", simBId],
    queryFn: () => api.getSimulation(simBId!),
    enabled: !!simBId,
  });

  if (!caseId) return <EmptyState message="Select a case from the Command Center first." />;

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-100">Counterfactual Lab</h1>
        <p className="mt-1 text-sm text-slate-500">
          "What if…" — ask a single what-if question and see the structural consequence, never a legal outcome.
        </p>
      </div>

      <Panel title="What if…">
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={mutationType}
            onChange={(e) => setMutationType(e.target.value)}
            className="rounded-md border border-brand-border bg-brand-bg px-2 py-1.5 text-sm text-slate-100"
          >
            <option value="">failure type…</option>
            {MUTATION_GROUPS.map((g) => (
              <optgroup key={g.group} label={g.group}>
                {g.mutations.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
          <span className="text-sm text-slate-500">happens to</span>
          <select
            value={targetNodeId}
            onChange={(e) => setTargetNodeId(e.target.value)}
            className="min-w-[220px] rounded-md border border-brand-border bg-brand-bg px-2 py-1.5 text-sm text-slate-100"
          >
            <option value="">select node…</option>
            {(graphQuery.data?.nodes ?? []).map((n) => (
              <option key={n.id} value={n.id}>
                [{n.node_type}] {n.label}
              </option>
            ))}
          </select>
          <Button onClick={() => ask.mutate()} disabled={ask.isPending}>
            {ask.isPending ? "Running…" : "Run counterfactual"}
          </Button>
        </div>
        {error && (
          <div className="mt-3">
            <ErrorState message={error} />
          </div>
        )}
      </Panel>

      {currentSim.data?.result && (
        <Panel title="Propagation & blast radius">
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <Metric label="Total affected" value={currentSim.data.result.blast_radius.total_affected_count} />
            <Metric label="New gaps" value={currentSim.data.result.blast_radius.new_unknowns.length} />
            <Metric label="New conflicts" value={currentSim.data.result.blast_radius.new_conflicts.length} />
            <Metric label="New blocks" value={currentSim.data.result.blast_radius.new_blocks.length} />
          </div>
          {currentSim.data.result.explanation && (
            <p className="mt-3 text-sm text-slate-300">{currentSim.data.result.explanation}</p>
          )}
          <div className="mt-3">
            <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Recovery options</p>
            {currentSim.data.result.recovery_options.length === 0 ? (
              <p className="text-xs text-slate-600">None proposed.</p>
            ) : (
              <ul className="flex flex-col gap-1">
                {currentSim.data.result.recovery_options.map((o, i) => (
                  <li key={i} className="text-xs text-slate-300">
                    {o.action} — {o.reason}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </Panel>
      )}

      {simAId && simBId && simAId !== simBId && (
        <Panel title="Scenario comparison">
          {compare.isLoading && <LoadingState />}
          {compare.isError && <ErrorState message={(compare.error as Error).message} />}
          {compare.data && (
            <pre className="max-h-72 overflow-auto rounded bg-brand-bg p-3 text-xs text-slate-400">
              {JSON.stringify(compare.data, null, 2)}
            </pre>
          )}
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
