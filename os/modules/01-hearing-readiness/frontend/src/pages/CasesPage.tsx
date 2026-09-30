import { useRef, useState } from "react";
import { useSelectedCase } from "../lib/selectedCase";
import { api } from "../lib/api";
import { useAsync } from "../hooks/useAsync";
import { PageHeader, Panel } from "../components/Panel";
import { LoadingState, ErrorState, EmptyState } from "../components/StatusStates";

export default function CasesPage() {
  const { cases, caseId, setCaseId, reload: reloadCases } = useSelectedCase();
  const [runningAgent, setRunningAgent] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  const caseData = useAsync(() => (caseId ? api.getCase(caseId) : Promise.reject("no case")), [caseId]);

  const handleUpload = async (file: File) => {
    if (!caseId) return;
    setUploadError(null);
    try {
      await api.uploadDocument(caseId, file);
      caseData.reload();
    } catch (e) {
      setUploadError(String(e));
    }
  };

  const handleRunAgentPass = async () => {
    if (!caseId) return;
    setRunningAgent(true);
    try {
      await api.runAgentPass(caseId);
      caseData.reload();
    } finally {
      setRunningAgent(false);
    }
  };

  return (
    <div>
      <PageHeader title="Cases" subtitle="Synthetic demo cases A–G are seeded automatically in DEMO MODE." />

      <div className="mb-6 grid grid-cols-1 gap-2">
        {cases.map((c) => (
          <button
            key={c.id}
            onClick={() => setCaseId(c.id)}
            className={`rounded-md border px-4 py-3 text-left text-sm transition-colors ${
              c.id === caseId
                ? "border-[var(--brass-500)] bg-[var(--ink-800)]"
                : "border-[var(--hairline)] hover:bg-[var(--ink-800)]"
            }`}
          >
            <div className="font-medium">{c.title}</div>
            <div className="mt-0.5 text-xs text-[var(--text-muted)]">
              {c.case_type.replace(/_/g, " ")} · {c.is_synthetic === "true" ? "synthetic demo case" : "user-created"}
            </div>
          </button>
        ))}
      </div>

      {caseId && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Panel title="Documents">
            {caseData.loading && <LoadingState />}
            {caseData.error && <ErrorState message={caseData.error} onRetry={caseData.reload} />}
            {caseData.data && (
              <>
                {caseData.data.documents.length === 0 ? (
                  <EmptyState message="No documents uploaded yet." />
                ) : (
                  <ul className="mb-3 space-y-2">
                    {caseData.data.documents.map((d) => (
                      <li key={d.id} className="rounded-md border border-[var(--hairline)] px-3 py-2 text-sm">
                        <div className="flex items-center justify-between">
                          <span className="truncate">{d.original_filename}</span>
                          <span className="ml-2 shrink-0 rounded bg-[var(--ink-700)] px-2 py-0.5 text-xs font-mono">
                            {d.extraction_status}
                          </span>
                        </div>
                        {d.injection_flag === "true" && (
                          <div className="mt-1 text-xs text-[var(--state-blocked)]">
                            Flagged: contains instruction-like text (treated as inert data, not followed).
                          </div>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
                <input
                  ref={fileInput}
                  type="file"
                  accept=".pdf,.docx,.txt,.json,.csv"
                  className="hidden"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) handleUpload(file);
                    e.target.value = "";
                  }}
                />
                <button
                  onClick={() => fileInput.current?.click()}
                  className="w-full rounded-md border border-dashed border-[var(--hairline)] px-3 py-2 text-sm text-[var(--text-secondary)] hover:border-[var(--brass-400)] hover:text-[var(--text-primary)]"
                >
                  Upload document (.pdf .docx .txt .json .csv)
                </button>
                {uploadError && <p className="mt-2 text-xs text-[var(--state-blocked)]">{uploadError}</p>}
              </>
            )}
          </Panel>

          <Panel title="Agentic readiness pass">
            <p className="mb-3 text-sm text-[var(--text-secondary)]">
              Runs OBSERVE → UNDERSTAND → INVESTIGATE → IDENTIFY BLOCKER → PLAN SAFE ACTION for this case,
              then stops for human approval before anything consequential happens.
            </p>
            <button
              onClick={handleRunAgentPass}
              disabled={runningAgent}
              className="w-full rounded-md bg-[var(--brass-500)] px-3 py-2 text-sm font-medium text-[var(--ink-950)] hover:bg-[var(--brass-400)] disabled:opacity-50"
            >
              {runningAgent ? "Running agent pass…" : "Run agent pass"}
            </button>
          </Panel>
        </div>
      )}

      <button
        onClick={reloadCases}
        className="mt-6 text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)]"
      >
        Refresh case list
      </button>
    </div>
  );
}
