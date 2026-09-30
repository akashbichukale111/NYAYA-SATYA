import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { CasesAPI } from "../api/client";
import { Loading, ErrorBox, SectionTitle, StatusBadge, SourceChip, EmptyState } from "../components/Primitives";

const SUBTABS = [
  { key: "hearings", label: "Hearings" },
  { key: "orders", label: "Orders" },
  { key: "bail", label: "Bail Events" },
  { key: "release", label: "Release Events" },
  { key: "verification", label: "Verification" },
] as const;

function RecordRow({ title, dateLabel, status, verification, documentId, snippet }: {
  title: string; dateLabel: string; status?: string; verification?: string;
  documentId?: string | null; snippet?: string | null;
}) {
  return (
    <div className="flex items-start justify-between border-b border-[color:var(--color-border)] py-3 last:border-0">
      <div>
        <div className="text-sm font-medium">{title}</div>
        <div className="text-xs text-[color:var(--color-text-secondary)] mt-0.5">{dateLabel}</div>
        <div className="mt-1"><SourceChip documentId={documentId} snippet={snippet} /></div>
      </div>
      <div className="flex flex-col items-end gap-1">
        {status && <StatusBadge status={status} />}
        {verification && <StatusBadge status={verification} />}
      </div>
    </div>
  );
}

function HearingsPanel({ caseId }: { caseId: string }) {
  const { data, isLoading, isError } = useQuery({ queryKey: ["hearings", caseId], queryFn: () => CasesAPI.hearings(caseId) });
  if (isLoading) return <Loading />;
  if (isError || !data) return <ErrorBox message="Could not load hearings." />;
  if (data.hearings.length === 0) return <EmptyState label="No hearings recorded yet." />;
  return (
    <div>
      {data.hearings.map((h: any) => (
        <RecordRow key={h.id} title={h.purpose || "Hearing"}
          dateLabel={`${h.hearing_date || "UNKNOWN_DATE"} · ${h.date_type}`}
          status={h.status} verification={h.verification_status}
          documentId={h.source_document_id} snippet={h.source_text_snippet} />
      ))}
    </div>
  );
}

function OrdersPanel({ caseId }: { caseId: string }) {
  const { data, isLoading, isError } = useQuery({ queryKey: ["orders", caseId], queryFn: () => CasesAPI.orders(caseId) });
  if (isLoading) return <Loading />;
  if (isError || !data) return <ErrorBox message="Could not load orders." />;
  if (data.orders.length === 0) return <EmptyState label="No orders recorded yet." />;
  return (
    <div>
      {data.orders.map((o: any) => (
        <RecordRow key={o.id} title={o.summary || "Order"}
          dateLabel={`${o.mentioned_date || "UNKNOWN_DATE"} · ${o.date_type}`}
          status={o.status} verification={o.verification_status}
          documentId={o.source_document_id} snippet={o.source_text_snippet} />
      ))}
    </div>
  );
}

function BailPanel({ caseId }: { caseId: string }) {
  const { data, isLoading, isError } = useQuery({ queryKey: ["bail-events", caseId], queryFn: () => CasesAPI.bailEvents(caseId) });
  if (isLoading) return <Loading />;
  if (isError || !data) return <ErrorBox message="Could not load bail events." />;
  if (data.bail_events.length === 0) return <EmptyState label="No bail events recorded yet." />;
  return (
    <div>
      {data.bail_events.map((b: any) => (
        <RecordRow key={b.id} title={b.event_type.replace(/_/g, " ")}
          dateLabel={`${b.event_date || "UNKNOWN_DATE"} · ${b.date_type}`}
          verification={b.verification_status}
          documentId={b.source_document_id} snippet={b.source_text_snippet} />
      ))}
    </div>
  );
}

function ReleasePanel({ caseId }: { caseId: string }) {
  const { data, isLoading, isError } = useQuery({ queryKey: ["release-events", caseId], queryFn: () => CasesAPI.releaseEvents(caseId) });
  if (isLoading) return <Loading />;
  if (isError || !data) return <ErrorBox message="Could not load release events." />;
  if (data.release_events.length === 0) return <EmptyState label="No release events recorded yet." />;
  return (
    <div>
      {data.release_events.map((r: any) => (
        <div key={r.id} className="border-b border-[color:var(--color-border)] py-3 last:border-0">
          <RecordRow title={r.event_type.replace(/_/g, " ")}
            dateLabel={`${r.event_date || "UNKNOWN_DATE"} · ${r.date_type}`}
            verification={r.verification_status}
            documentId={r.source_document_id} snippet={r.source_text_snippet} />
          <div className="mt-1 text-xs">
            Current status confidence: <StatusBadge status={r.current_status_confidence} />
            {r.current_status_confidence !== "CURRENT_STATUS_VERIFIED" && (
              <span className="ml-2 text-[color:var(--color-text-muted)] italic">
                Not treated as "currently released" until a human verifies this.
              </span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

function VerificationPanel({ caseId }: { caseId: string }) {
  const { data, isLoading, isError } = useQuery({ queryKey: ["verification", caseId], queryFn: () => CasesAPI.verification(caseId) });
  if (isLoading) return <Loading />;
  if (isError || !data) return <ErrorBox message="Could not load verification records." />;
  if (data.verifications.length === 0) return <EmptyState label="No verification decisions recorded yet." />;
  return (
    <div>
      {data.verifications.map((v: any) => (
        <div key={v.id} className="flex items-start justify-between border-b border-[color:var(--color-border)] py-3 last:border-0">
          <div>
            <div className="text-sm font-medium">{v.entity_type} · {v.entity_id.slice(0, 14)}…</div>
            <div className="text-xs text-[color:var(--color-text-secondary)] mt-0.5">
              {v.note || "No note provided"} — by {v.verified_by_user_id || "unknown"}
            </div>
          </div>
          <StatusBadge status={v.verification_status} />
        </div>
      ))}
    </div>
  );
}

export default function ProceduralRecordsTab({ caseId }: { caseId: string }) {
  const [sub, setSub] = useState<(typeof SUBTABS)[number]["key"]>("hearings");
  return (
    <div className="card p-5">
      <SectionTitle subtitle="Hearings, Orders, Bail Events, Release Events, and human verification decisions — each source-linked, none inferring a legal outcome.">
        Procedural Records
      </SectionTitle>
      <div className="flex gap-2 mb-4 border-b border-[color:var(--color-border)] pb-2">
        {SUBTABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setSub(t.key)}
            className={`text-xs px-3 py-1.5 rounded-md ${
              sub === t.key
                ? "bg-[color:var(--color-surface-raised)] text-[color:var(--color-accent)]"
                : "text-[color:var(--color-text-secondary)] hover:bg-[color:var(--color-surface-raised)]"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>
      {sub === "hearings" && <HearingsPanel caseId={caseId} />}
      {sub === "orders" && <OrdersPanel caseId={caseId} />}
      {sub === "bail" && <BailPanel caseId={caseId} />}
      {sub === "release" && <ReleasePanel caseId={caseId} />}
      {sub === "verification" && <VerificationPanel caseId={caseId} />}
    </div>
  );
}
