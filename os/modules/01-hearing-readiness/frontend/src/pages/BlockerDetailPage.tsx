import { useParams } from "react-router-dom";
import { useState } from "react";
import { useSelectedCase } from "../lib/selectedCase";
import { api } from "../lib/api";
import { useAsync } from "../hooks/useAsync";
import { PageHeader, Panel } from "../components/Panel";
import { SeverityBadge, ConfidenceTag } from "../components/ReadinessBadge";
import { LoadingState, ErrorState, EmptyState } from "../components/StatusStates";
import { CausalGraph } from "../components/CausalGraph";

export default function BlockerDetailPage() {
  const { blockerId } = useParams<{ blockerId: string }>();
  const { caseId } = useSelectedCase();
  const [decisionInFlight, setDecisionInFlight] = useState<string | null>(null);

  const blockers = useAsync(() => (caseId ? api.listBlockers(caseId) : Promise.reject("no case")), [caseId]);
  const explanation = useAsync(
    () => (caseId && blockerId ? api.explainBlocker(caseId, blockerId) : Promise.reject("no blocker")),
    [caseId, blockerId]
  );
  const graph = useAsync(() => (caseId ? api.getGraph(caseId) : Promise.reject("no case")), [caseId]);
  const actions = useAsync(() => (caseId ? api.listActions(caseId) : Promise.reject("no case")), [caseId]);

  if (!caseId || !blockerId) return <EmptyState message="No blocker selected." />;
  if (blockers.loading || explanation.loading) return <LoadingState />;
  if (blockers.error) return <ErrorState message={blockers.error} onRetry={blockers.reload} />;
  if (explanation.error) return <ErrorState message={explanation.error} onRetry={explanation.reload} />;

  const blocker = (blockers.data ?? []).find((b) => b.id === blockerId);
  if (!blocker) return <EmptyState message="Blocker not found (it may have been resolved)." />;

  const relatedActions = (actions.data ?? []).filter((a) => a.blocker_id === blockerId);
  const pendingAction = relatedActions.find((a) => a.status === "PENDING_APPROVAL");

  const decide = async (decision: "APPROVE" | "REJECT") => {
    if (!pendingAction) return;
    setDecisionInFlight(decision);
    try {
      await api.approveAction(caseId, pendingAction.id, decision);
      actions.reload();
      blockers.reload();
    } finally {
      setDecisionInFlight(null);
    }
  };

  const exp = explanation.data!;

  return (
    <div>
      <PageHeader
        title={blocker.description}
        subtitle={`Category: ${blocker.category}`}
        action={<SeverityBadge severity={blocker.severity} />}
      />

      <Panel title="Why?" className="mb-6">
        <dl className="space-y-3 text-sm">
          <div>
            <dt className="text-xs uppercase tracking-wide text-[var(--text-muted)]">What</dt>
            <dd>{exp.what}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-[var(--text-muted)]">Why</dt>
            <dd>{exp.why}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-[var(--text-muted)]">Evidence</dt>
            <dd>
              <ul className="list-inside list-disc">
                {exp.evidence.map((e, i) => (
                  <li key={i}>{e}</li>
                ))}
              </ul>
            </dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-[var(--text-muted)]">Dependency</dt>
            <dd>{exp.dependency}</dd>
          </div>
          <div className="flex items-center gap-3">
            <dt className="text-xs uppercase tracking-wide text-[var(--text-muted)]">Confidence</dt>
            <dd><ConfidenceTag confidence={exp.confidence} /></dd>
          </div>
          {exp.unknown.length > 0 && (
            <div>
              <dt className="text-xs uppercase tracking-wide text-[var(--text-muted)]">Unknown</dt>
              <dd>
                <ul className="list-inside list-disc text-[var(--state-conditional)]">
                  {exp.unknown.map((u, i) => (
                    <li key={i}>{u}</li>
                  ))}
                </ul>
              </dd>
            </div>
          )}
          <div>
            <dt className="text-xs uppercase tracking-wide text-[var(--text-muted)]">Next safe action</dt>
            <dd>{exp.next_safe_action}</dd>
          </div>
        </dl>
      </Panel>

      <Panel title="Dependency graph" className="mb-6">
        {graph.loading && <LoadingState />}
        {graph.error && <ErrorState message={graph.error} onRetry={graph.reload} />}
        {graph.data && <CausalGraph graph={graph.data} highlightId={blocker.id} />}
      </Panel>

      <Panel title="Human approval gate">
        {relatedActions.length === 0 ? (
          <EmptyState message="No safe action proposed yet for this blocker. Run an agent pass from the Cases page." />
        ) : (
          <ul className="space-y-3">
            {relatedActions.map((a) => (
              <li key={a.id} className="rounded-md border border-[var(--hairline)] px-4 py-3">
                <div className="mb-2 flex items-center justify-between">
                  <span className="font-medium">{a.description}</span>
                  <span className="rounded bg-[var(--ink-700)] px-2 py-0.5 text-xs font-mono">{a.status}</span>
                </div>
                <dl className="grid grid-cols-1 gap-1 text-xs text-[var(--text-secondary)] sm:grid-cols-2">
                  <div><span className="text-[var(--text-muted)]">Reason: </span>{a.reason}</div>
                  <div><span className="text-[var(--text-muted)]">Risk: </span>{a.risk}</div>
                  <div className="sm:col-span-2"><span className="text-[var(--text-muted)]">Expected effect: </span>{a.expected_effect}</div>
                  {a.unknowns.length > 0 && (
                    <div className="sm:col-span-2 text-[var(--state-conditional)]">
                      Unknowns: {a.unknowns.join("; ")}
                    </div>
                  )}
                  {a.result && (
                    <div className="sm:col-span-2">
                      <span className="text-[var(--text-muted)]">Result artifact: </span>
                      <pre className="mt-1 whitespace-pre-wrap rounded bg-[var(--ink-950)] p-2 text-[11px]">
                        {JSON.stringify(a.result, null, 2)}
                      </pre>
                    </div>
                  )}
                </dl>
                {a.status === "PENDING_APPROVAL" && (
                  <div className="mt-3 flex gap-2">
                    <button
                      onClick={() => decide("APPROVE")}
                      disabled={decisionInFlight !== null}
                      className="rounded-md bg-[var(--state-ready)] px-3 py-1.5 text-xs font-medium text-[var(--ink-950)] disabled:opacity-50"
                    >
                      {decisionInFlight === "APPROVE" ? "Approving…" : "Approve"}
                    </button>
                    <button
                      onClick={() => decide("REJECT")}
                      disabled={decisionInFlight !== null}
                      className="rounded-md border border-[var(--hairline)] px-3 py-1.5 text-xs hover:bg-[var(--ink-800)] disabled:opacity-50"
                    >
                      {decisionInFlight === "REJECT" ? "Rejecting…" : "Reject"}
                    </button>
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}
