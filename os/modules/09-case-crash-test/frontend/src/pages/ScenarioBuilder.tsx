import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api, type MutationSpec } from "../lib/api";
import { useCaseContext } from "../lib/case-context";
import { MUTATION_GROUPS } from "../lib/mutation-taxonomy";
import { Button, EmptyState, ErrorState, LoadingState, Panel } from "../components/ui";

export default function ScenarioBuilder() {
  const { caseId, setSimulationId } = useCaseContext();
  const qc = useQueryClient();
  const navigate = useNavigate();

  const [selectedSnapshotId, setSelectedSnapshotId] = useState<string>("");
  const [rows, setRows] = useState<MutationSpec[]>([{ mutation_type: "", target_node_id: "" }]);
  const [runError, setRunError] = useState<string | null>(null);

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

  const createSnapshot = useMutation({
    mutationFn: () => api.createSnapshot(caseId!, `Snapshot ${new Date().toISOString()}`),
    onSuccess: (snap) => {
      qc.invalidateQueries({ queryKey: ["snapshots", caseId] });
      setSelectedSnapshotId(snap.id);
    },
  });

  const runSimulation = useMutation({
    mutationFn: () => {
      const mutations = rows.filter((r) => r.mutation_type && r.target_node_id);
      if (!selectedSnapshotId) throw new Error("Select or create a base snapshot first.");
      if (mutations.length === 0) throw new Error("Add at least one mutation (failure type + target node).");
      return api.runSimulation(caseId!, {
        base_snapshot_id: selectedSnapshotId,
        inline_mutations: mutations,
        created_by: "akash",
      });
    },
    onSuccess: (sim) => {
      setRunError(null);
      setSimulationId(sim.id);
      navigate("/simulation");
    },
    onError: (e: Error) => setRunError(e.message),
  });

  if (!caseId) return <EmptyState message="Select a case from the Command Center first." />;

  const nodes = graphQuery.data?.nodes ?? [];

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-100">Scenario Builder</h1>
        <p className="mt-1 text-sm text-slate-500">
          Select a base snapshot, then configure one or more mutations. Nothing here touches the real case.
        </p>
      </div>

      <Panel title="1. Base snapshot">
        {snapshotsQuery.isLoading && <LoadingState />}
        {snapshotsQuery.isError && <ErrorState message={(snapshotsQuery.error as Error).message} />}
        <div className="flex flex-wrap items-center gap-2">
          {snapshotsQuery.data?.map((snap) => (
            <button
              key={snap.id}
              onClick={() => setSelectedSnapshotId(snap.id)}
              className={`rounded-md border px-3 py-1.5 text-xs font-mono ${
                selectedSnapshotId === snap.id
                  ? "border-brand-accent text-brand-accent"
                  : "border-brand-border text-slate-400 hover:text-slate-200"
              }`}
            >
              v{snap.version} {snap.label ? `— ${snap.label}` : ""}
            </button>
          ))}
          <Button variant="secondary" onClick={() => createSnapshot.mutate()} disabled={createSnapshot.isPending}>
            {createSnapshot.isPending ? "Creating…" : "Create new snapshot"}
          </Button>
        </div>
      </Panel>

      <Panel title="2. Mutations (failure type + target node)">
        <div className="flex flex-col gap-3">
          {rows.map((row, idx) => (
            <div key={idx} className="flex items-center gap-2">
              <select
                value={row.mutation_type}
                onChange={(e) => {
                  const next = [...rows];
                  next[idx] = { ...next[idx], mutation_type: e.target.value };
                  setRows(next);
                }}
                className="rounded-md border border-brand-border bg-brand-bg px-2 py-1.5 text-sm text-slate-100"
              >
                <option value="">Select failure type…</option>
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
              <select
                value={row.target_node_id}
                onChange={(e) => {
                  const next = [...rows];
                  next[idx] = { ...next[idx], target_node_id: e.target.value };
                  setRows(next);
                }}
                className="min-w-[220px] flex-1 rounded-md border border-brand-border bg-brand-bg px-2 py-1.5 text-sm text-slate-100"
              >
                <option value="">Select target node…</option>
                {nodes.map((n) => (
                  <option key={n.id} value={n.id}>
                    [{n.node_type}] {n.label} ({n.status})
                  </option>
                ))}
              </select>
              <Button
                variant="secondary"
                onClick={() => setRows(rows.filter((_, i) => i !== idx))}
                disabled={rows.length === 1}
              >
                Remove
              </Button>
            </div>
          ))}
          <div>
            <Button variant="secondary" onClick={() => setRows([...rows, { mutation_type: "", target_node_id: "" }])}>
              + Add another mutation (multi-scenario)
            </Button>
          </div>
        </div>
      </Panel>

      {runError && <ErrorState message={runError} />}

      <div>
        <Button onClick={() => runSimulation.mutate()} disabled={runSimulation.isPending}>
          {runSimulation.isPending ? "Running simulation…" : "Run simulation"}
        </Button>
      </div>
    </div>
  );
}
