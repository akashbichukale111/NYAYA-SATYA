import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { CasesAPI } from "../api/client";
import { Loading, ErrorBox, SectionTitle, EmptyState } from "../components/Primitives";

export function TimeMachineTab({ caseId }: { caseId: string }) {
  const [a, setA] = useState("");
  const [b, setB] = useState("");
  const { data, isLoading, isError } = useQuery({
    queryKey: ["time-machine", caseId, a, b],
    queryFn: () => CasesAPI.timeMachine(caseId, a || undefined, b || undefined),
  });

  if (isLoading) return <Loading />;
  if (isError || !data) return <ErrorBox message="Could not load Time Machine data." />;

  return (
    <div className="card p-5">
      <SectionTitle subtitle="Compare any two points in this case's history. Historical records are never rewritten.">
        Time Machine
      </SectionTitle>
      <div className="flex gap-2 mb-4">
        <select className="bg-transparent border border-[color:var(--color-border)] rounded px-3 py-2 text-sm" value={a} onChange={(e) => setA(e.target.value)}>
          <option value="">Snapshot A…</option>
          {data.snapshots.map((s: any) => <option key={s.id} value={s.id}>{new Date(s.created_at).toLocaleString()} — {s.reason}</option>)}
        </select>
        <select className="bg-transparent border border-[color:var(--color-border)] rounded px-3 py-2 text-sm" value={b} onChange={(e) => setB(e.target.value)}>
          <option value="">Snapshot B…</option>
          {data.snapshots.map((s: any) => <option key={s.id} value={s.id}>{new Date(s.created_at).toLocaleString()} — {s.reason}</option>)}
        </select>
      </div>

      {data.diff && Object.keys(data.diff).length > 0 ? (
        <div className="space-y-2 text-sm">
          {Object.entries(data.diff).map(([key, val]: [string, any]) => (
            <div key={key} className="flex justify-between border-b border-[color:var(--color-border)] pb-2">
              <span>{key.replace(/_/g, " ")}</span>
              <span>{JSON.stringify(val.before)} → {JSON.stringify(val.after)}</span>
            </div>
          ))}
        </div>
      ) : data.diff_earliest_vs_current && Object.keys(data.diff_earliest_vs_current).length > 0 ? (
        <div className="space-y-2 text-sm">
          <div className="text-xs text-[color:var(--color-text-muted)] mb-2">Earliest snapshot vs. current live state:</div>
          {Object.entries(data.diff_earliest_vs_current).map(([key, val]: [string, any]) => (
            <div key={key} className="flex justify-between border-b border-[color:var(--color-border)] pb-2">
              <span>{key.replace(/_/g, " ")}</span>
              <span>{JSON.stringify(val.before)} → {JSON.stringify(val.after)}</span>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState label="No differences to show yet, or select two snapshots to compare." />
      )}

      <div className="mt-5 text-xs text-[color:var(--color-text-muted)]">
        {data.snapshots.length} snapshot(s) recorded for this case.
      </div>
    </div>
  );
}
