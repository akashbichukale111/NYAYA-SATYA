import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { CasesAPI } from "../api/client";
import CommandCenterTab from "./CommandCenterTab";
import {
  TimelineTab, AttentionTab, ConflictsTab, DocumentsTab,
  ReviewQueueTab, AuditTab, EvaluationTab, CrashTestTab,
} from "./CaseTabs";
import { TimeMachineTab } from "./TimeMachineTab";
import DependencyGraphTab from "./DependencyGraphTab";
import ProceduralRecordsTab from "./ProceduralRecordsTab";
import { Loading, ErrorBox } from "../components/Primitives";

const NAV = [
  { key: "command-center", label: "Command Center" },
  { key: "timeline", label: "Custody Timeline" },
  { key: "records", label: "Hearings / Orders / Bail / Release" },
  { key: "attention", label: "Attention Center" },
  { key: "dependency-graph", label: "Dependency Graph" },
  { key: "conflicts", label: "Conflicts" },
  { key: "documents", label: "Documents" },
  { key: "review-queue", label: "Review Queue" },
  { key: "crash-test", label: "Simulation & Crash Test" },
  { key: "time-machine", label: "Time Machine" },
  { key: "audit", label: "Audit" },
  { key: "evaluation", label: "Evaluation Lab" },
];

export default function CaseDetailPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const [tab, setTab] = useState("command-center");
  const { data: caseData, isLoading, isError } = useQuery({
    queryKey: ["case", caseId],
    queryFn: () => CasesAPI.get(caseId!),
    enabled: !!caseId,
  });

  if (!caseId) return null;
  if (isLoading) return <Loading />;
  if (isError || !caseData) return <ErrorBox message="Case not found." />;

  return (
    <div className="flex min-h-screen">
      <aside className="w-64 border-r border-[color:var(--color-border)] p-5 flex-shrink-0">
        <Link to="/" className="text-xs text-[color:var(--color-text-secondary)] hover:text-[color:var(--color-accent)]">
          ← All cases
        </Link>
        <div className="mt-3 mb-6">
          <div className="font-medium">{caseData.title}</div>
          <div className="text-xs text-[color:var(--color-text-secondary)]">{caseData.case_reference}</div>
          {caseData.is_demo && (
            <div className="badge mt-2">DEMONSTRATION DATA — NOT A REAL CASE</div>
          )}
        </div>
        <nav className="space-y-1">
          {NAV.map((n) => (
            <button
              key={n.key}
              onClick={() => setTab(n.key)}
              className={`block w-full text-left text-sm px-3 py-2 rounded-md transition-colors ${
                tab === n.key
                  ? "bg-[color:var(--color-surface-raised)] text-[color:var(--color-accent)]"
                  : "text-[color:var(--color-text-secondary)] hover:bg-[color:var(--color-surface-raised)]"
              }`}
            >
              {n.label}
            </button>
          ))}
        </nav>
      </aside>

      <main className="flex-1 p-8 overflow-y-auto">
        {tab === "command-center" && <CommandCenterTab caseId={caseId} />}
        {tab === "timeline" && <TimelineTab caseId={caseId} />}
        {tab === "records" && <ProceduralRecordsTab caseId={caseId} />}
        {tab === "attention" && <AttentionTab caseId={caseId} />}
        {tab === "dependency-graph" && <DependencyGraphTab caseId={caseId} />}
        {tab === "conflicts" && <ConflictsTab caseId={caseId} />}
        {tab === "documents" && <DocumentsTab caseId={caseId} />}
        {tab === "review-queue" && <ReviewQueueTab caseId={caseId} />}
        {tab === "crash-test" && <CrashTestTab caseId={caseId} />}
        {tab === "time-machine" && <TimeMachineTab caseId={caseId} />}
        {tab === "audit" && <AuditTab caseId={caseId} />}
        {tab === "evaluation" && <EvaluationTab caseId={caseId} />}
      </main>
    </div>
  );
}
