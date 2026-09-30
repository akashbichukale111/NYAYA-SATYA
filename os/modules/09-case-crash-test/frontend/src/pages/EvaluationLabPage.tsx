import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { useCaseContext } from "../lib/case-context";
import { EmptyState, ErrorState, LoadingState, Panel } from "../components/ui";

const STATUS_STYLE: Record<string, string> = {
  PASS: "text-emerald-400 border-emerald-500/40 bg-emerald-500/10",
  FAIL: "text-rose-400 border-rose-500/40 bg-rose-500/10",
  NOT_RUN: "text-slate-400 border-slate-600/40 bg-slate-700/10",
};

export default function EvaluationLabPage() {
  const { caseId } = useCaseContext();

  const evalQuery = useQuery({
    queryKey: ["evaluation", caseId],
    queryFn: () => api.getEvaluation(caseId!),
    enabled: !!caseId,
  });

  if (!caseId) return <EmptyState message="Select a case from the Command Center first." />;

  const data = evalQuery.data;
  const tests = data?.tests ?? [];

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-100">Evaluation Lab</h1>
        <p className="mt-1 text-sm text-slate-500">
          Deterministic resilience self-tests against this case's current graph. Only PASS / FAIL / NOT_RUN
          are ever reported here — never a fabricated resilience score or percentage.
        </p>
      </div>

      {evalQuery.isLoading && <LoadingState />}
      {evalQuery.isError && <ErrorState message={(evalQuery.error as Error).message} />}

      {data && (
        <>
          <div className="grid grid-cols-3 gap-4">
            <Panel title="Passed">
              <p className="text-3xl font-semibold text-emerald-400">{data.pass_count ?? 0}</p>
            </Panel>
            <Panel title="Failed">
              <p className="text-3xl font-semibold text-rose-400">{data.fail_count ?? 0}</p>
            </Panel>
            <Panel title="Not run">
              <p className="text-3xl font-semibold text-slate-400">{data.not_run_count ?? 0}</p>
            </Panel>
          </div>

          <Panel title="Test results">
            {tests.length === 0 ? (
              <EmptyState message="No resilience tests have run for this case yet." />
            ) : (
              <ul className="flex flex-col gap-2">
                {tests.map((t) => (
                  <li
                    key={t.name}
                    className="flex items-center justify-between rounded-md border border-brand-border bg-brand-bg p-3 text-sm"
                  >
                    <div>
                      <p className="font-mono text-xs text-slate-300">{t.name}</p>
                      {t.detail && <p className="mt-1 text-xs text-slate-500">{t.detail}</p>}
                    </div>
                    <span
                      className={`rounded-full border px-3 py-1 text-xs font-semibold ${
                        STATUS_STYLE[t.status] ?? STATUS_STYLE.NOT_RUN
                      }`}
                    >
                      {t.status}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </Panel>
        </>
      )}
    </div>
  );
}
