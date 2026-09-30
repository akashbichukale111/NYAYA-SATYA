import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { useCaseContext } from "../lib/case-context";
import { Button, EmptyState, ErrorState, LoadingState, Panel } from "../components/ui";

export default function ReviewQueuePage() {
  const { caseId } = useCaseContext();
  const qc = useQueryClient();

  const queueQuery = useQuery({
    queryKey: ["review-queue", caseId],
    queryFn: () => api.getReviewQueue(caseId!),
    enabled: !!caseId,
  });

  const approve = useMutation({
    mutationFn: (id: string) => api.approveReview(id, "akash"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["review-queue", caseId] }),
  });
  const reject = useMutation({
    mutationFn: (id: string) => api.rejectReview(id, "akash"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["review-queue", caseId] }),
  });

  if (!caseId) return <EmptyState message="Select a case from the Command Center first." />;

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-100">Review Queue</h1>
        <p className="mt-1 text-sm text-slate-500">
          Items simulations flagged as requiring human review. Approving or rejecting requires REVIEWER role or
          higher.
        </p>
      </div>

      <Panel title="Pending review">
        {queueQuery.isLoading && <LoadingState />}
        {queueQuery.isError && <ErrorState message={(queueQuery.error as Error).message} />}
        {queueQuery.data && queueQuery.data.length === 0 && <EmptyState message="Nothing pending review." />}
        {queueQuery.data && queueQuery.data.length > 0 && (
          <ul className="flex flex-col gap-2">
            {queueQuery.data.map((task) => (
              <li key={task.id} className="rounded-md border border-brand-border bg-brand-bg p-3">
                <p className="text-sm text-slate-200">{task.reason}</p>
                <p className="mt-1 text-xs text-slate-500">
                  Created {new Date(task.created_at).toLocaleString()}
                  {task.simulation_id ? ` · simulation ${task.simulation_id}` : ""}
                </p>
                <div className="mt-2 flex gap-2">
                  <Button onClick={() => approve.mutate(task.id)} disabled={approve.isPending}>
                    Approve
                  </Button>
                  <Button variant="danger" onClick={() => reject.mutate(task.id)} disabled={reject.isPending}>
                    Reject
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}
