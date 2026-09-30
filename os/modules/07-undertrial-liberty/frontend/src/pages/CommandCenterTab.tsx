import { useQuery } from "@tanstack/react-query";
import { CasesAPI } from "../api/client";
import type { DigitalTwin } from "../api/client";
import { Loading, ErrorBox, SectionTitle, SeverityBadge, EmptyState } from "../components/Primitives";

export default function CommandCenterTab({ caseId }: { caseId: string }) {
  const { data, isLoading, isError } = useQuery<DigitalTwin>({
    queryKey: ["twin", caseId],
    queryFn: () => CasesAPI.digitalTwin(caseId),
  });

  if (isLoading) return <Loading />;
  if (isError || !data) return <ErrorBox message="Could not load the Liberty Digital Twin." />;

  return (
    <div className="grid grid-cols-3 gap-5">
      <div className="col-span-2 space-y-5">
        <div className="card p-5">
          <SectionTitle subtitle="What the system currently believes, and how confident it is.">
            Current Case State
          </SectionTitle>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <div className="text-[color:var(--color-text-muted)] text-xs uppercase tracking-wide mb-1">Custody state</div>
              <div className="font-medium">{data.custody_state.replace(/_/g, " ")}</div>
              <div className="text-xs text-[color:var(--color-text-secondary)] mt-1">{data.custody_state_confidence}</div>
            </div>
            <div>
              <div className="text-[color:var(--color-text-muted)] text-xs uppercase tracking-wide mb-1">Latest verified event</div>
              {data.latest_verified_event ? (
                <div className="font-medium">{data.latest_verified_event.event_type.replace(/_/g, " ")}
                  <span className="text-[color:var(--color-text-secondary)]"> — {data.latest_verified_event.event_date || "date unknown"}</span>
                </div>
              ) : (
                <div className="text-[color:var(--color-text-muted)] italic">None verified yet</div>
              )}
            </div>
          </div>
        </div>

        <div className="card p-5">
          <SectionTitle>Attention Center — top items</SectionTitle>
          {data.attention_items.length === 0 && <EmptyState label="No open attention items." />}
          <div className="space-y-2">
            {data.attention_items.slice(0, 8).map((a) => (
              <div key={a.id} className="flex items-start justify-between border-b border-[color:var(--color-border)] pb-2 last:border-0">
                <div>
                  <div className="text-sm">{a.reason}</div>
                  <div className="text-xs text-[color:var(--color-text-muted)] mt-0.5">{a.category.replace(/_/g, " ")}</div>
                </div>
                <SeverityBadge severity={a.severity} />
              </div>
            ))}
          </div>
        </div>

        <div className="card p-5">
          <SectionTitle>Missing Information</SectionTitle>
          {data.missing_information.length === 0 ? (
            <EmptyState label="No known information gaps." />
          ) : (
            <ul className="list-disc list-inside text-sm space-y-1">
              {data.missing_information.map((m, i) => <li key={i}>{m}</li>)}
            </ul>
          )}
        </div>
      </div>

      <div className="space-y-5">
        <div className="card p-5">
          <SectionTitle>Upcoming Tracked Dates</SectionTitle>
          {data.upcoming_tracked_events.length === 0 ? (
            <EmptyState label="No upcoming source-stated dates tracked." />
          ) : (
            <ul className="text-sm space-y-2">
              {data.upcoming_tracked_events.map((e: any, i: number) => (
                <li key={i}>{e.date} — {e.purpose || e.type}</li>
              ))}
            </ul>
          )}
        </div>

        <div className="card p-5">
          <SectionTitle>Pending Human Review</SectionTitle>
          {data.pending_reviews.length === 0 ? (
            <EmptyState label="Nothing pending review." />
          ) : (
            <ul className="text-sm space-y-2">
              {data.pending_reviews.map((r: any) => (
                <li key={r.id}>{r.task_type.replace(/_/g, " ")}: {r.description}</li>
              ))}
            </ul>
          )}
        </div>

        <div className="card p-5">
          <SectionTitle>Conflicts</SectionTitle>
          {data.conflicts.length === 0 ? (
            <EmptyState label="No open conflicts." />
          ) : (
            <ul className="text-sm space-y-2">
              {data.conflicts.map((c: any) => (
                <li key={c.id}>{c.field}: "{c.value_a}" vs "{c.value_b}"</li>
              ))}
            </ul>
          )}
        </div>

        <div className="card p-5">
          <SectionTitle>Evidence & Documents</SectionTitle>
          <div className="text-sm">{data.documents_ingested} document(s) ingested</div>
        </div>
      </div>
    </div>
  );
}
