import { useSelectedCase } from "../lib/selectedCase";
import { api } from "../lib/api";
import { useAsync } from "../hooks/useAsync";
import { PageHeader, Panel } from "../components/Panel";
import { LoadingState, ErrorState } from "../components/StatusStates";

function formatMetricName(key: string): string {
  return key.replace(/_pct$/, "").replace(/_/g, " ");
}

export default function EvaluationLabPage() {
  const { caseId } = useSelectedCase();
  const evalSummary = useAsync(() => api.getEvalSummary(caseId ?? undefined), [caseId]);

  if (evalSummary.loading) return <LoadingState />;
  if (evalSummary.error) return <ErrorState message={evalSummary.error} onRetry={evalSummary.reload} />;
  const data = evalSummary.data!;

  return (
    <div>
      <PageHeader
        title="Evaluation Lab"
        subtitle="Every number below is computed live from this case's data. Nothing is a hard-coded benchmark."
      />

      <Panel title="Measured" className="mb-6">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {Object.entries(data.measured).map(([key, value]) => (
            <div key={key} className="rounded-md border border-[var(--hairline)] px-4 py-3">
              <div className="text-2xl font-serif">
                {value === null ? <span className="text-[var(--text-muted)] text-base">n/a</span> : `${value}%`}
              </div>
              <div className="mt-0.5 text-xs capitalize text-[var(--text-muted)]">{formatMetricName(key)}</div>
            </div>
          ))}
        </div>
      </Panel>

      <Panel title="Not yet measured" className="mb-6">
        <p className="mb-3 text-xs text-[var(--text-muted)]">
          Honestly reported rather than faked — these require infrastructure this build doesn't include yet.
        </p>
        <ul className="space-y-2 text-sm">
          {Object.entries(data.not_yet_measured).map(([key, why]) => (
            <li key={key} className="rounded-md border border-dashed border-[var(--hairline)] px-3 py-2">
              <div className="font-medium capitalize">{formatMetricName(key)}</div>
              <div className="text-xs text-[var(--text-muted)]">{why}</div>
            </li>
          ))}
        </ul>
      </Panel>

      <Panel title="Sample sizes">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-5 text-sm">
          {Object.entries(data.sample_sizes).map(([key, value]) => (
            <div key={key}>
              <div className="text-lg font-serif">{value}</div>
              <div className="text-xs capitalize text-[var(--text-muted)]">{key.replace(/_/g, " ")}</div>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}
