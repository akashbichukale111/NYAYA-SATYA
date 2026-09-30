import { useState } from "react";
import { useSelectedCase } from "../lib/selectedCase";
import { api } from "../lib/api";
import { useAsync } from "../hooks/useAsync";
import { PageHeader, Panel } from "../components/Panel";
import { LoadingState, ErrorState, EmptyState } from "../components/StatusStates";

export default function TimeMachinePage() {
  const { caseId } = useSelectedCase();
  const versions = useAsync(() => (caseId ? api.listVersions(caseId) : Promise.reject("no case")), [caseId]);
  const [from, setFrom] = useState<number | null>(null);
  const [to, setTo] = useState<number | null>(null);
  const [diff, setDiff] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!caseId) return <EmptyState message="No case selected." />;
  if (versions.loading) return <LoadingState />;
  if (versions.error) return <ErrorState message={versions.error} onRetry={versions.reload} />;

  const list = versions.data ?? [];

  const runDiff = async () => {
    if (from === null || to === null) return;
    setError(null);
    try {
      setDiff(await api.diffVersions(caseId, from, to));
    } catch (e) {
      setError(String(e));
    }
  };

  return (
    <div>
      <PageHeader title="Time Machine" subtitle="Compare readiness state across any two saved versions. Nothing is ever overwritten." />

      <Panel title="Versions" className="mb-6">
        {list.length === 0 ? (
          <EmptyState message="No versions saved yet — run a readiness audit first." />
        ) : (
          <ul className="space-y-1 text-sm">
            {list.map((v) => (
              <li key={v.id} className="flex items-center justify-between rounded-md border border-[var(--hairline)] px-3 py-2">
                <span>
                  V{v.version_number} — {v.trigger}
                </span>
                <span className="text-xs text-[var(--text-muted)]">{new Date(v.created_at).toLocaleString()}</span>
              </li>
            ))}
          </ul>
        )}
      </Panel>

      {list.length >= 2 && (
        <Panel title="Compare versions" className="mb-6">
          <div className="flex flex-wrap items-center gap-3">
            <select
              value={from ?? ""}
              onChange={(e) => setFrom(Number(e.target.value))}
              className="rounded-md border border-[var(--hairline)] bg-[var(--ink-800)] px-3 py-1.5 text-sm"
            >
              <option value="" disabled>From</option>
              {list.map((v) => (
                <option key={v.id} value={v.version_number}>V{v.version_number}</option>
              ))}
            </select>
            <span className="text-[var(--text-muted)]">→</span>
            <select
              value={to ?? ""}
              onChange={(e) => setTo(Number(e.target.value))}
              className="rounded-md border border-[var(--hairline)] bg-[var(--ink-800)] px-3 py-1.5 text-sm"
            >
              <option value="" disabled>To</option>
              {list.map((v) => (
                <option key={v.id} value={v.version_number}>V{v.version_number}</option>
              ))}
            </select>
            <button
              onClick={runDiff}
              disabled={from === null || to === null}
              className="rounded-md bg-[var(--brass-500)] px-3 py-1.5 text-sm font-medium text-[var(--ink-950)] disabled:opacity-50"
            >
              Compare
            </button>
          </div>
          {error && <p className="mt-2 text-xs text-[var(--state-blocked)]">{error}</p>}
        </Panel>
      )}

      {diff && (
        <Panel title="Diff">
          <pre className="scrollbar-thin max-h-96 overflow-auto whitespace-pre-wrap rounded bg-[var(--ink-950)] p-3 text-xs">
            {JSON.stringify(diff, null, 2)}
          </pre>
        </Panel>
      )}
    </div>
  );
}
