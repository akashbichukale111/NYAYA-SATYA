import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { CasesAPI } from "../api/client";
import { Loading, ErrorBox, SectionTitle, SeverityBadge, StatusBadge, SourceChip, EmptyState } from "../components/Primitives";

export function TimelineTab({ caseId }: { caseId: string }) {
  const { data, isLoading, isError } = useQuery({ queryKey: ["timeline", caseId], queryFn: () => CasesAPI.timeline(caseId) });
  if (isLoading) return <Loading />;
  if (isError || !data) return <ErrorBox message="Could not load timeline." />;
  return (
    <div className="card p-5">
      <SectionTitle subtitle="Chronological, source-linked. Undated items are listed separately, never guessed.">
        Custody Timeline
      </SectionTitle>
      <div className="space-y-3">
        {data.timeline.map((item: any, i: number) => (
          <div key={i} className="flex items-start justify-between border-b border-[color:var(--color-border)] pb-3 last:border-0">
            <div>
              <div className="text-sm font-medium">{item.label?.replace(/_/g, " ") || item.kind}</div>
              <div className="text-xs text-[color:var(--color-text-secondary)] mt-0.5">
                {item.kind} · {item.date ? item.date : <em>UNKNOWN_DATE</em>} · {item.date_type}
              </div>
              <div className="mt-1"><SourceChip documentId={item.source_document_id} /></div>
            </div>
            {item.verification_status && <StatusBadge status={item.verification_status} />}
          </div>
        ))}
        {data.timeline.length === 0 && <EmptyState label="No timeline events yet. Upload a document to begin." />}
      </div>
    </div>
  );
}

export function AttentionTab({ caseId }: { caseId: string }) {
  const { data, isLoading, isError } = useQuery({ queryKey: ["attention", caseId], queryFn: () => CasesAPI.attention(caseId) });
  if (isLoading) return <Loading />;
  if (isError || !data) return <ErrorBox message="Could not load attention items." />;
  return (
    <div className="card p-5">
      <SectionTitle subtitle="Operational attention priority — never a measure of legal seriousness.">
        Attention Center
      </SectionTitle>
      <div className="space-y-3">
        {data.attention_items.map((a: any) => (
          <div key={a.id} className="border-b border-[color:var(--color-border)] pb-3 last:border-0">
            <div className="flex items-center justify-between">
              <div className="text-sm">{a.reason}</div>
              <SeverityBadge severity={a.severity} />
            </div>
            <div className="text-xs text-[color:var(--color-text-muted)] mt-1">{a.category.replace(/_/g, " ")}</div>
          </div>
        ))}
        {data.attention_items.length === 0 && <EmptyState label="No open attention items." />}
      </div>
    </div>
  );
}

export function ConflictsTab({ caseId }: { caseId: string }) {
  const qc = useQueryClient();
  const { data, isLoading, isError } = useQuery({ queryKey: ["conflicts", caseId], queryFn: () => CasesAPI.conflicts(caseId) });
  const resolveMutation = useMutation({
    mutationFn: ({ id, value }: { id: string; value: string }) => CasesAPI.resolveConflict(id, value, "Resolved via UI"),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["conflicts", caseId] });
      qc.invalidateQueries({ queryKey: ["attention", caseId] });
      qc.invalidateQueries({ queryKey: ["twin", caseId] });
    },
  });
  if (isLoading) return <Loading />;
  if (isError || !data) return <ErrorBox message="Could not load conflicts." />;
  return (
    <div className="card p-5">
      <SectionTitle subtitle="The system never auto-resolves a conflict. A human reviewer chooses.">
        Conflicts
      </SectionTitle>
      <div className="space-y-4">
        {data.conflicts.map((c: any) => (
          <div key={c.id} className="border border-[color:var(--color-border)] rounded-lg p-3">
            <div className="text-sm font-medium mb-2">{c.entity_type} · {c.field_name}</div>
            <div className="grid grid-cols-2 gap-3 text-sm mb-2">
              <div className="p-2 rounded bg-[color:var(--color-surface-raised)]">
                <div className="text-xs text-[color:var(--color-text-muted)] mb-1">Source A</div>
                <div>{c.value_a}</div>
                <SourceChip documentId={c.source_a_ref?.document_id} snippet={c.source_a_ref?.snippet} />
              </div>
              <div className="p-2 rounded bg-[color:var(--color-surface-raised)]">
                <div className="text-xs text-[color:var(--color-text-muted)] mb-1">Source B</div>
                <div>{c.value_b}</div>
                <SourceChip documentId={c.source_b_ref?.document_id} snippet={c.source_b_ref?.snippet} />
              </div>
            </div>
            {c.status === "OPEN" ? (
              <div className="flex gap-2">
                <button className="text-xs px-3 py-1 rounded bg-[color:var(--color-accent)] text-black"
                  onClick={() => resolveMutation.mutate({ id: c.id, value: c.value_a })}>
                  Accept Source A
                </button>
                <button className="text-xs px-3 py-1 rounded bg-[color:var(--color-accent)] text-black"
                  onClick={() => resolveMutation.mutate({ id: c.id, value: c.value_b })}>
                  Accept Source B
                </button>
              </div>
            ) : (
              <StatusBadge status={c.status} />
            )}
          </div>
        ))}
        {data.conflicts.length === 0 && <EmptyState label="No conflicts detected." />}
      </div>
    </div>
  );
}

export function DocumentsTab({ caseId }: { caseId: string }) {
  const qc = useQueryClient();
  const { data, isLoading, isError } = useQuery({ queryKey: ["documents", caseId], queryFn: () => CasesAPI.documents(caseId) });
  const uploadMutation = useMutation({
    mutationFn: (file: File) => CasesAPI.uploadDocument(caseId, file),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["documents", caseId] });
      qc.invalidateQueries({ queryKey: ["timeline", caseId] });
      qc.invalidateQueries({ queryKey: ["attention", caseId] });
      qc.invalidateQueries({ queryKey: ["twin", caseId] });
      qc.invalidateQueries({ queryKey: ["conflicts", caseId] });
    },
  });
  if (isLoading) return <Loading />;
  if (isError || !data) return <ErrorBox message="Could not load documents." />;
  return (
    <div className="card p-5">
      <SectionTitle subtitle="Uploaded documents are untrusted data — parsed and pattern-matched only, never followed as instructions.">
        Documents
      </SectionTitle>
      <label className="inline-block mb-4 text-xs px-3 py-2 rounded bg-[color:var(--color-accent)] text-black cursor-pointer">
        Upload document (.txt, .pdf, .docx, .csv, .json)
        <input type="file" className="hidden" accept=".txt,.pdf,.docx,.csv,.json"
          onChange={(e) => e.target.files?.[0] && uploadMutation.mutate(e.target.files[0])} />
      </label>
      {uploadMutation.isPending && <div className="text-sm text-[color:var(--color-text-muted)] mb-2">Uploading and extracting…</div>}
      {uploadMutation.isError && <ErrorBox message="Upload failed." />}
      <div className="space-y-2">
        {data.map((d: any) => (
          <div key={d.id} className="flex items-center justify-between border-b border-[color:var(--color-border)] pb-2 last:border-0 text-sm">
            <div>
              <div>{d.filename}</div>
              <div className="text-xs text-[color:var(--color-text-muted)]">sha256: {d.sha256.slice(0, 16)}… · {d.extraction_method || "no extraction"}</div>
            </div>
            <StatusBadge status={d.status} />
          </div>
        ))}
        {data.length === 0 && <EmptyState label="No documents uploaded yet." />}
      </div>
    </div>
  );
}

export function ReviewQueueTab({ caseId }: { caseId: string }) {
  const qc = useQueryClient();
  const { data, isLoading, isError } = useQuery({ queryKey: ["review-queue", caseId], queryFn: () => CasesAPI.reviewQueue(caseId) });
  const approve = useMutation({
    mutationFn: (id: string) => CasesAPI.approveReview(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["review-queue", caseId] }),
  });
  const reject = useMutation({
    mutationFn: (id: string) => CasesAPI.rejectReview(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["review-queue", caseId] }),
  });
  if (isLoading) return <Loading />;
  if (isError || !data) return <ErrorBox message="Could not load review queue." />;
  return (
    <div className="card p-5">
      <SectionTitle subtitle="Human legal review is required before any of these become authoritative.">
        Review Queue
      </SectionTitle>
      <div className="space-y-3">
        {data.review_tasks.map((t: any) => (
          <div key={t.id} className="border-b border-[color:var(--color-border)] pb-3 last:border-0">
            <div className="flex items-center justify-between">
              <div className="text-sm">{t.description}</div>
              <StatusBadge status={t.status} />
            </div>
            <div className="text-xs text-[color:var(--color-text-muted)] mt-1">{t.task_type.replace(/_/g, " ")}</div>
            {t.status === "PENDING" && (
              <div className="flex gap-2 mt-2">
                <button className="text-xs px-3 py-1 rounded bg-[color:var(--color-success)] text-black" onClick={() => approve.mutate(t.id)}>Approve</button>
                <button className="text-xs px-3 py-1 rounded bg-[color:var(--color-review)] text-white" onClick={() => reject.mutate(t.id)}>Reject</button>
              </div>
            )}
          </div>
        ))}
        {data.review_tasks.length === 0 && <EmptyState label="No review tasks." />}
      </div>
    </div>
  );
}

export function AuditTab({ caseId }: { caseId: string }) {
  const { data, isLoading, isError } = useQuery({ queryKey: ["audit", caseId], queryFn: () => CasesAPI.audit(caseId) });
  if (isLoading) return <Loading />;
  if (isError || !data) return <ErrorBox message="Could not load audit trail." />;
  return (
    <div className="card p-5">
      <SectionTitle subtitle="Append-only. Every consequential action is logged.">Audit Trail</SectionTitle>
      <div className="space-y-2 text-sm">
        {data.audit_events.map((e: any) => (
          <div key={e.id} className="flex justify-between border-b border-[color:var(--color-border)] pb-2 last:border-0">
            <div>{e.action} {e.entity_type ? `· ${e.entity_type}` : ""}</div>
            <div className="text-xs text-[color:var(--color-text-muted)]">{new Date(e.created_at).toLocaleString()}</div>
          </div>
        ))}
        {data.audit_events.length === 0 && <EmptyState label="No audit events yet." />}
      </div>
    </div>
  );
}

export function EvaluationTab({ caseId }: { caseId: string }) {
  const { data, isLoading, isError } = useQuery({ queryKey: ["evaluation", caseId], queryFn: () => CasesAPI.evaluation(caseId) });
  if (isLoading) return <Loading />;
  if (isError || !data) return <ErrorBox message="Could not load evaluation results." />;
  const statusColor: Record<string, string> = { PASS: "var(--color-success)", FAIL: "var(--color-review)", NOT_RUN: "var(--color-text-muted)" };
  return (
    <div className="card p-5">
      <SectionTitle subtitle="Deterministic checks against this case's actual data. No invented percentages.">
        Evaluation Lab
      </SectionTitle>
      <div className="flex gap-4 mb-4 text-sm">
        <div>PASS: {data.summary.PASS}</div>
        <div>FAIL: {data.summary.FAIL}</div>
        <div>NOT_RUN: {data.summary.NOT_RUN}</div>
      </div>
      <div className="space-y-2">
        {Object.entries(data.checks).map(([name, result]: [string, any]) => (
          <div key={name} className="flex justify-between border-b border-[color:var(--color-border)] pb-2 last:border-0 text-sm">
            <div>
              <div>{name.replace(/_/g, " ")}</div>
              <div className="text-xs text-[color:var(--color-text-muted)]">{result.reason}</div>
            </div>
            <span style={{ color: statusColor[result.status] }} className="font-semibold text-xs">{result.status}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function CrashTestTab({ caseId }: { caseId: string }) {
  const { data: supported } = useQuery({ queryKey: ["sim-events", caseId], queryFn: () => CasesAPI.supportedSimulationEvents(caseId) });
  const { data: orders } = useQuery({ queryKey: ["orders", caseId], queryFn: () => CasesAPI.orders(caseId) });
  const [eventType, setEventType] = useState("");
  const [targetId, setTargetId] = useState("");
  const [result, setResult] = useState<any>(null);
  const runMutation = useMutation({
    mutationFn: () => CasesAPI.crashTest(caseId, eventType, targetId || undefined),
    onSuccess: (r) => setResult(r),
  });

  return (
    <div className="card p-5">
      <SectionTitle subtitle="Runs against a real database SAVEPOINT that is always rolled back. Production data is never mutated.">
        Liberty Crash Test
      </SectionTitle>
      <div className="flex gap-2 mb-4">
        <select className="bg-transparent border border-[color:var(--color-border)] rounded px-3 py-2 text-sm"
          value={eventType} onChange={(e) => setEventType(e.target.value)}>
          <option value="">Select a scenario…</option>
          {supported && Object.keys(supported.supported_events).map((k) => (
            <option key={k} value={k}>{k.replace(/_/g, " ")}</option>
          ))}
        </select>
        <select className="bg-transparent border border-[color:var(--color-border)] rounded px-3 py-2 text-sm"
          value={targetId} onChange={(e) => setTargetId(e.target.value)}>
          <option value="">(optional) target order…</option>
          {orders?.orders?.map((o: any) => <option key={o.id} value={o.id}>{o.id.slice(0, 12)} — {o.summary?.slice(0, 40)}</option>)}
        </select>
        <button disabled={!eventType} className="text-xs px-4 py-2 rounded bg-[color:var(--color-review)] text-white disabled:opacity-40"
          onClick={() => runMutation.mutate()}>
          Run Crash Test
        </button>
      </div>
      {runMutation.isPending && <div className="text-sm text-[color:var(--color-text-muted)]">Running against a rolled-back SAVEPOINT…</div>}
      {result && (
        <div className="space-y-3 text-sm">
          <div>production_state_mutated: <strong>{String(result.production_state_mutated)}</strong></div>
          <div>
            <div className="text-xs text-[color:var(--color-text-muted)] mb-1">Affected attention items in simulation</div>
            {result.affected_attention_items.length === 0 ? <EmptyState label="None." /> : (
              <ul className="list-disc list-inside">
                {result.affected_attention_items.map((a: any, i: number) => (
                  <li key={i}>{a.category.replace(/_/g, " ")} — {a.reason}</li>
                ))}
              </ul>
            )}
          </div>
          <div>human_review_required: <strong>{String(result.human_review_required)}</strong></div>
        </div>
      )}
    </div>
  );
}
