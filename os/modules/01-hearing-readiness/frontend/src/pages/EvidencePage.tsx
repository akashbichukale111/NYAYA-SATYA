import { useSelectedCase } from "../lib/selectedCase";
import { api } from "../lib/api";
import { useAsync } from "../hooks/useAsync";
import { PageHeader, Panel } from "../components/Panel";
import { ConfidenceTag } from "../components/ReadinessBadge";
import { LoadingState, ErrorState, EmptyState } from "../components/StatusStates";

const AVAILABILITY_COLOR: Record<string, string> = {
  AVAILABLE: "text-[var(--state-ready)]",
  MISSING: "text-[var(--state-blocked)]",
  PARTIAL: "text-[var(--state-conditional)]",
  UNKNOWN: "text-[var(--state-unknown)]",
};
const VERIFICATION_COLOR: Record<string, string> = {
  VERIFIED: "text-[var(--state-ready)]",
  UNVERIFIED: "text-[var(--state-conditional)]",
  DISPUTED: "text-[var(--state-blocked)]",
};

export default function EvidencePage() {
  const { caseId } = useSelectedCase();
  const evidence = useAsync(() => (caseId ? api.listEvidence(caseId) : Promise.reject("no case")), [caseId]);

  if (!caseId) return <EmptyState message="No case selected." />;
  if (evidence.loading) return <LoadingState />;
  if (evidence.error) return <ErrorState message={evidence.error} onRetry={evidence.reload} />;

  return (
    <div>
      <PageHeader title="Evidence" subtitle="Every requirement's status traces back to one of these items." />
      <Panel>
        {(evidence.data ?? []).length === 0 ? (
          <EmptyState />
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--hairline)] text-left text-xs uppercase tracking-wide text-[var(--text-muted)]">
                <th className="py-2 pr-3">Label</th>
                <th className="py-2 pr-3">Type</th>
                <th className="py-2 pr-3">Availability</th>
                <th className="py-2 pr-3">Verification</th>
                <th className="py-2 pr-3">Confidence</th>
              </tr>
            </thead>
            <tbody>
              {(evidence.data ?? []).map((e) => (
                <tr key={e.id} className="border-b border-[var(--hairline)]/50">
                  <td className="py-2 pr-3">{e.label}</td>
                  <td className="py-2 pr-3 text-[var(--text-muted)]">{e.evidence_type}</td>
                  <td className={`py-2 pr-3 font-medium ${AVAILABILITY_COLOR[e.availability]}`}>{e.availability}</td>
                  <td className={`py-2 pr-3 font-medium ${VERIFICATION_COLOR[e.verification_state]}`}>{e.verification_state}</td>
                  <td className="py-2 pr-3"><ConfidenceTag confidence={e.confidence} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>
    </div>
  );
}
