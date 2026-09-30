import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { useCaseContext } from "../lib/case-context";
import { Button, EmptyState, ErrorState, LoadingState, Panel } from "../components/ui";

export default function TimeMachinePage() {
  const { caseId } = useCaseContext();
  const qc = useQueryClient();
  const [reason, setReason] = useState("");
  const [approver, setApprover] = useState("akash");
  const [pendingRestoreId, setPendingRestoreId] = useState<string | null>(null);
  const [restoreError, setRestoreError] = useState<string | null>(null);

  const snapshotsQuery = useQuery({
    queryKey: ["snapshots", caseId],
    queryFn: () => api.listSnapshots(caseId!),
    enabled: !!caseId,
  });

  const createSnapshot = useMutation({
    mutationFn: () => api.createSnapshot(caseId!, `Manual snapshot ${new Date().toLocaleString()}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["snapshots", caseId] }),
  });

  const restore = useMutation({
    mutationFn: (snapshotId: string) => api.restoreSnapshot(caseId!, snapshotId, approver, reason),
    onSuccess: () => {
      setRestoreError(null);
      setPendingRestoreId(null);
      setReason("");
      qc.invalidateQueries({ queryKey: ["snapshots", caseId] });
      qc.invalidateQueries({ queryKey: ["graph", caseId] });
    },
    onError: (e: Error) => setRestoreError(e.message),
  });

  if (!caseId) return <EmptyState message="Select a case from the Command Center first." />;

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-100">Time Machine</h1>
        <p className="mt-1 text-sm text-slate-500">
          Snapshots are immutable points-in-time. Restoring one is the <em>only</em> operation in this system that
          can overwrite the real case graph — it requires an explicit human reason and is fully audited.
        </p>
      </div>

      <Panel
        title="Snapshots"
        actions={
          <Button variant="secondary" onClick={() => createSnapshot.mutate()} disabled={createSnapshot.isPending}>
            {createSnapshot.isPending ? "Creating…" : "Create snapshot of current state"}
          </Button>
        }
      >
        {snapshotsQuery.isLoading && <LoadingState />}
        {snapshotsQuery.isError && <ErrorState message={(snapshotsQuery.error as Error).message} />}
        {snapshotsQuery.data && snapshotsQuery.data.length === 0 && (
          <EmptyState message="No snapshots yet for this case." />
        )}
        {snapshotsQuery.data && snapshotsQuery.data.length > 0 && (
          <ul className="divide-y divide-brand-border">
            {snapshotsQuery.data.map((snap) => (
              <li key={snap.id} className="flex items-center justify-between py-2 text-sm">
                <div>
                  <p className="font-mono text-slate-200">
                    v{snap.version} {snap.label ? `— ${snap.label}` : ""}
                  </p>
                  <p className="text-xs text-slate-500">
                    Created {new Date(snap.created_at).toLocaleString()} by {snap.created_by}
                  </p>
                </div>
                <Button variant="secondary" onClick={() => setPendingRestoreId(snap.id)}>
                  Restore (requires approval)
                </Button>
              </li>
            ))}
          </ul>
        )}
      </Panel>

      {pendingRestoreId && (
        <Panel title="Confirm restore — this will overwrite the live case graph">
          <div className="flex flex-col gap-3">
            <label className="text-xs text-slate-400">
              Approved by
              <input
                value={approver}
                onChange={(e) => setApprover(e.target.value)}
                className="mt-1 block w-full rounded-md border border-brand-border bg-brand-bg px-2 py-1.5 text-sm text-slate-100"
              />
            </label>
            <label className="text-xs text-slate-400">
              Reason (required)
              <input
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Why is this restore necessary?"
                className="mt-1 block w-full rounded-md border border-brand-border bg-brand-bg px-2 py-1.5 text-sm text-slate-100"
              />
            </label>
            {restoreError && <ErrorState message={restoreError} />}
            <div className="flex gap-2">
              <Button
                variant="danger"
                onClick={() => restore.mutate(pendingRestoreId)}
                disabled={!reason.trim() || restore.isPending}
              >
                {restore.isPending ? "Restoring…" : "Confirm restore"}
              </Button>
              <Button variant="secondary" onClick={() => setPendingRestoreId(null)}>
                Cancel
              </Button>
            </div>
          </div>
        </Panel>
      )}
    </div>
  );
}
