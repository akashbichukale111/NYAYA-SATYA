import { useState } from "react";
import { useSelectedCase } from "../lib/selectedCase";
import { api, type CrashTestResult } from "../lib/api";
import { PageHeader, Panel } from "../components/Panel";
import { EmptyState } from "../components/StatusStates";

export default function CrashTestPage() {
  const { caseId } = useSelectedCase();
  const [results, setResults] = useState<CrashTestResult[]>([]);
  const [running, setRunning] = useState(false);

  if (!caseId) return <EmptyState message="No case selected." />;

  const runAll = async () => {
    setRunning(true);
    try {
      const res = await api.runCrashTest(caseId);
      setResults(Array.isArray(res) ? res : [res]);
    } finally {
      setRunning(false);
    }
  };

  const passCount = results.filter((r) => r.passed === "true").length;

  return (
    <div>
      <PageHeader
        title="Crash Test"
        subtitle="Adversarial mutations run on a cloned copy of case state — real evidence is never touched."
        action={
          <button
            onClick={runAll}
            disabled={running}
            className="rounded-md bg-[var(--brass-500)] px-3 py-2 text-sm font-medium text-[var(--ink-950)] hover:bg-[var(--brass-400)] disabled:opacity-50"
          >
            {running ? "Running…" : "Run all mutations"}
          </button>
        }
      />

      {results.length === 0 ? (
        <EmptyState message="No crash test results yet for this session — run all mutations above." />
      ) : (
        <>
          <p className="mb-4 text-sm text-[var(--text-secondary)]">
            {passCount} / {results.length} mutations behaved as expected.
          </p>
          <div className="space-y-3">
            {results.map((r) => (
              <Panel key={r.id}>
                <div className="mb-1 flex items-center justify-between">
                  <span className="font-mono text-sm">{r.mutation}</span>
                  <span
                    className={`rounded px-2 py-0.5 text-xs font-medium ${
                      r.passed === "true"
                        ? "bg-[var(--state-ready)]/15 text-[var(--state-ready)]"
                        : "bg-[var(--state-blocked)]/15 text-[var(--state-blocked)]"
                    }`}
                  >
                    {r.passed === "true" ? "PASS" : "FAIL"}
                  </span>
                </div>
                <p className="text-xs text-[var(--text-secondary)]">{r.explanation}</p>
              </Panel>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
