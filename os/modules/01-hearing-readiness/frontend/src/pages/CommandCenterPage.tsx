import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { useSelectedCase } from "../lib/selectedCase";
import { api } from "../lib/api";
import { useAsync } from "../hooks/useAsync";
import { PageHeader, Panel, StatGrid } from "../components/Panel";
import { ReadinessBadge, SeverityBadge } from "../components/ReadinessBadge";
import { LoadingState, ErrorState, EmptyState } from "../components/StatusStates";

export default function CommandCenterPage() {
  const { caseId } = useSelectedCase();

  const caseData = useAsync(() => (caseId ? api.getCase(caseId) : Promise.reject("no case")), [caseId]);
  const readiness = useAsync(() => (caseId ? api.getReadiness(caseId) : Promise.reject("no case")), [caseId]);
  const actions = useAsync(() => (caseId ? api.listActions(caseId) : Promise.reject("no case")), [caseId]);

  if (!caseId) return <EmptyState message="No case selected." />;
  if (caseData.loading || readiness.loading) return <LoadingState />;
  if (caseData.error) return <ErrorState message={caseData.error} onRetry={caseData.reload} />;
  if (readiness.error) return <ErrorState message={readiness.error} onRetry={readiness.reload} />;

  const full = caseData.data!;
  const snap = readiness.data!;
  const nextHearing = full.hearings.find((h) => h.is_next === "true");
  const openBlockers = full.blockers.filter((b) => b.status === "OPEN");
  const pendingApprovals = (actions.data ?? []).filter((a) => a.status === "PENDING_APPROVAL");

  return (
    <div>
      <PageHeader
        title={full.case.title}
        subtitle={`${full.case.case_type.replace(/_/g, " ")} · ${full.case.parties.map((p) => p.name).join(", ")}`}
      />

      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-3"
      >
        <Panel title="Overall readiness" className="md:col-span-1">
          <div className="flex flex-col items-start gap-3">
            <ReadinessBadge state={snap.overall} size="lg" />
            {snap.hearing_context_uncertain && (
              <p className="text-xs text-[var(--state-conditional)]">
                HEARING CONTEXT UNCERTAIN — see hearing details below.
              </p>
            )}
          </div>
        </Panel>

        <Panel title="Next hearing" className="md:col-span-2">
          {nextHearing ? (
            <div className="space-y-1 text-sm">
              <div>
                <span className="text-[var(--text-muted)]">Date: </span>
                {nextHearing.hearing_date ? new Date(nextHearing.hearing_date).toLocaleDateString() : "Not set"}
              </div>
              <div>
                <span className="text-[var(--text-muted)]">Purpose: </span>
                {nextHearing.purpose_status === "DETERMINED" ? (
                  nextHearing.purpose?.replace(/_/g, " ")
                ) : (
                  <span className="text-[var(--state-conditional)]">HEARING CONTEXT UNCERTAIN</span>
                )}
              </div>
              {nextHearing.purpose_status === "UNCERTAIN" && nextHearing.uncertainty_reasons.length > 0 && (
                <ul className="mt-1 list-inside list-disc text-xs text-[var(--text-muted)]">
                  {nextHearing.uncertainty_reasons.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              )}
            </div>
          ) : (
            <EmptyState message="No upcoming hearing on record." />
          )}
        </Panel>
      </motion.div>

      <div className="mb-6">
        <StatGrid
          items={[
            { label: "Requirements", value: snap.requirement_count },
            { label: "Satisfied", value: snap.satisfied_count },
            { label: "Unresolved", value: snap.unresolved_count },
            { label: "Open blockers", value: snap.open_blocker_count },
          ]}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Panel
          title="Unresolved blockers"
          action={
            <Link to="/blockers" className="text-xs text-[var(--brass-400)] hover:underline">
              View all
            </Link>
          }
        >
          {openBlockers.length === 0 ? (
            <EmptyState message="No open blockers." />
          ) : (
            <ul className="space-y-2">
              {openBlockers.slice(0, 5).map((b) => (
                <li key={b.id}>
                  <Link
                    to={`/blockers/${b.id}`}
                    className="flex items-center justify-between rounded-md border border-[var(--hairline)] px-3 py-2 text-sm hover:bg-[var(--ink-800)]"
                  >
                    <span className="truncate pr-2">{b.description}</span>
                    <SeverityBadge severity={b.severity} />
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Panel
          title="Pending human approvals"
          action={
            <Link to="/timeline" className="text-xs text-[var(--brass-400)] hover:underline">
              View all actions
            </Link>
          }
        >
          {pendingApprovals.length === 0 ? (
            <EmptyState message="No actions awaiting approval." />
          ) : (
            <ul className="space-y-2">
              {pendingApprovals.map((a) => (
                <li key={a.id} className="rounded-md border border-[var(--hairline)] px-3 py-2 text-sm">
                  <div className="font-medium">{a.description}</div>
                  <div className="mt-0.5 text-xs text-[var(--text-muted)]">{a.expected_effect}</div>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>

      <div className="mt-4 flex items-center gap-2 text-xs text-[var(--text-muted)]">
        <span>System health:</span>
        <span className="rounded bg-[var(--ink-700)] px-2 py-0.5">API reachable</span>
        <span className="rounded bg-[var(--ink-700)] px-2 py-0.5">DEMO MODE</span>
      </div>
    </div>
  );
}
