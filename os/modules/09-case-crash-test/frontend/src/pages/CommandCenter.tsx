import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { useState } from "react";
import { api } from "../lib/api";
import { useCaseContext } from "../lib/case-context";
import { Button, EmptyState, ErrorState, LoadingState, Panel, DemoBanner } from "../components/ui";

export default function CommandCenter() {
  const { caseId, setCaseId } = useCaseContext();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [newTitle, setNewTitle] = useState("");

  const casesQuery = useQuery({ queryKey: ["cases"], queryFn: api.listCases });

  const loadDemo = useMutation({
    mutationFn: api.loadDemo,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cases"] }),
  });

  const createCase = useMutation({
    mutationFn: () => api.createCase({ title: newTitle }),
    onSuccess: (c) => {
      setNewTitle("");
      qc.invalidateQueries({ queryKey: ["cases"] });
      setCaseId(c.id);
    },
  });

  const activeCase = casesQuery.data?.find((c) => c.id === caseId);

  const integrationQuery = useQuery({
    queryKey: ["integration-summary", caseId],
    queryFn: () => api.getIntegrationSummary(caseId!),
    enabled: !!caseId,
  });

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-100">Case Resilience Command Center</h1>
        <p className="mt-1 text-sm text-slate-500">
          Structural health, critical dependencies, and recent simulations — never a predicted outcome.
        </p>
      </div>

      {activeCase?.is_demo && <DemoBanner />}

      <Panel
        title="Cases"
        actions={
          <Button variant="secondary" onClick={() => loadDemo.mutate()} disabled={loadDemo.isPending}>
            {loadDemo.isPending ? "Loading demo…" : "Load demo cases"}
          </Button>
        }
      >
        {casesQuery.isLoading && <LoadingState />}
        {casesQuery.isError && <ErrorState message={(casesQuery.error as Error).message} />}
        {casesQuery.data && casesQuery.data.length === 0 && (
          <EmptyState message="No cases yet. Load the demo cases or create a new one below." />
        )}
        {casesQuery.data && casesQuery.data.length > 0 && (
          <ul className="divide-y divide-brand-border">
            {casesQuery.data.map((c) => (
              <li key={c.id} className="flex items-center justify-between py-2">
                <div>
                  <p className="text-sm font-medium text-slate-200">{c.title}</p>
                  <p className="text-xs text-slate-500">
                    {c.is_demo ? "Demo case" : "Live case"} · created {new Date(c.created_at).toLocaleString()}
                  </p>
                </div>
                <Button variant={c.id === caseId ? "primary" : "secondary"} onClick={() => setCaseId(c.id)}>
                  {c.id === caseId ? "Active" : "Select"}
                </Button>
              </li>
            ))}
          </ul>
        )}

        <div className="mt-4 flex gap-2 border-t border-brand-border pt-4">
          <input
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            placeholder="New case title"
            className="flex-1 rounded-md border border-brand-border bg-brand-bg px-3 py-1.5 text-sm text-slate-100 placeholder:text-slate-600"
          />
          <Button onClick={() => createCase.mutate()} disabled={!newTitle.trim() || createCase.isPending}>
            Create case
          </Button>
        </div>
      </Panel>

      {caseId && (
        <Panel title="Case Health Structure (Integration Summary)">
          {integrationQuery.isLoading && <LoadingState />}
          {integrationQuery.isError && <ErrorState message={(integrationQuery.error as Error).message} />}
          {integrationQuery.data && (
            <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
              <Stat label="Active simulations" value={integrationQuery.data.active_simulations} />
              <Stat label="Critical dependencies" value={integrationQuery.data.critical_dependencies.length} />
              <Stat label="Fragile (single-point) nodes" value={integrationQuery.data.fragile_nodes.length} />
              <Stat label="Verification gaps" value={integrationQuery.data.verification_gaps.length} />
              <Stat label="Human review items" value={integrationQuery.data.human_review_items.length} />
              <Stat label="Blocked workflows" value={integrationQuery.data.blocked_workflows.length} />
              <Stat label="Recent simulations" value={integrationQuery.data.recent_failures.length} />
              <Stat label="Base state version" value={integrationQuery.data.base_state_version ?? "—"} />
            </div>
          )}
          <div className="mt-4 flex gap-2">
            <Button onClick={() => navigate("/graph")}>Open Case Graph</Button>
            <Button variant="secondary" onClick={() => navigate("/scenarios")}>
              Build a scenario
            </Button>
          </div>
        </Panel>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-md border border-brand-border bg-brand-bg px-3 py-3">
      <p className="text-2xl font-semibold text-slate-100">{value}</p>
      <p className="mt-1 text-xs text-slate-500">{label}</p>
    </div>
  );
}
