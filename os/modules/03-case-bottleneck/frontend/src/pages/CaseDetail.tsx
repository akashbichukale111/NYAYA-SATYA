import { useEffect, useState, useCallback } from "react";
import { useParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type {
  CaseSummary, Bottleneck, RootCauseCandidate, ActionItem, AuditEvent,
  FlowGraph, FlowHealth, HistoryEntry, CaseDocument, SimulationResult, CrashTestResult,
} from "../types/domain";
import { ConfidenceBadge, AttentionBadge, StatusPill, ModeFlag, ErrorBanner, Spinner, EmptyState } from "../components/Badges";
import { RootCauseChain } from "../components/RootCauseChain";
import { FlowGraphView } from "../components/FlowGraphView";

type Tab = "stuck" | "flow" | "actions" | "simulate" | "crashtest" | "history" | "audit" | "documents";

export function CaseDetail() {
  const { caseId } = useParams<{ caseId: string }>();
  const [tab, setTab] = useState<Tab>("stuck");
  const [caseInfo, setCaseInfo] = useState<CaseSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    if (!caseId) return;
    api.getCase(caseId).then(setCaseInfo).catch((e) => setError(e instanceof ApiError ? e.message : String(e)));
  }, [caseId]);

  useEffect(load, [load]);

  if (!caseId) return null;

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">{caseInfo?.title ?? caseId}</div>
          <div className="page-subtitle mono">{caseId} {caseInfo?.demo_scenario ? `· Scenario ${caseInfo.demo_scenario}` : ""}</div>
        </div>
      </div>
      {error && <ErrorBanner message={error} />}

      <div className="tabs">
        <TabBtn tab={tab} value="stuck" onClick={setTab}>Why is this case stuck?</TabBtn>
        <TabBtn tab={tab} value="flow" onClick={setTab}>Flow map</TabBtn>
        <TabBtn tab={tab} value="actions" onClick={setTab}>Actions</TabBtn>
        <TabBtn tab={tab} value="simulate" onClick={setTab}>Simulate</TabBtn>
        <TabBtn tab={tab} value="crashtest" onClick={setTab}>Crash test</TabBtn>
        <TabBtn tab={tab} value="documents" onClick={setTab}>Documents</TabBtn>
        <TabBtn tab={tab} value="history" onClick={setTab}>History</TabBtn>
        <TabBtn tab={tab} value="audit" onClick={setTab}>Audit</TabBtn>
      </div>

      {tab === "stuck" && <WhyStuckTab caseId={caseId} />}
      {tab === "flow" && <FlowTab caseId={caseId} />}
      {tab === "actions" && <ActionsTab caseId={caseId} />}
      {tab === "simulate" && <SimulateTab caseId={caseId} />}
      {tab === "crashtest" && <CrashTestTab caseId={caseId} />}
      {tab === "documents" && <DocumentsTab caseId={caseId} />}
      {tab === "history" && <HistoryTab caseId={caseId} />}
      {tab === "audit" && <AuditTab caseId={caseId} />}
    </div>
  );
}

function TabBtn({ tab, value, onClick, children }: { tab: Tab; value: Tab; onClick: (t: Tab) => void; children: React.ReactNode }) {
  return (
    <div className={`tab ${tab === value ? "active" : ""}`} onClick={() => onClick(value)}>
      {children}
    </div>
  );
}

// ---------------------------------------------------------------------
// TAB: "Why is this case stuck?" — the flagship screen (Section 19/46)
// ---------------------------------------------------------------------
function WhyStuckTab({ caseId }: { caseId: string }) {
  const [bottlenecks, setBottlenecks] = useState<Bottleneck[] | null>(null);
  const [primaryId, setPrimaryId] = useState<string | null>(null);
  const [rootCauses, setRootCauses] = useState<Record<string, RootCauseCandidate>>({});
  const [health, setHealth] = useState<FlowHealth | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [{ primary_bottleneck_id, bottlenecks: bns }, h] = await Promise.all([
        api.listBottlenecks(caseId),
        api.getFlowHealth(caseId),
      ]);
      setBottlenecks(bns);
      setPrimaryId(primary_bottleneck_id);
      setHealth(h);
      const chains: Record<string, RootCauseCandidate> = {};
      await Promise.all(
        bns.map(async (b) => {
          try {
            chains[b.id] = await api.getRootCause(caseId, b.id);
          } catch {
            /* no root-cause analysis yet for this bottleneck — fine, tab shows a prompt instead */
          }
        }),
      );
      setRootCauses(chains);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    }
  }, [caseId]);

  useEffect(() => { refresh(); }, [refresh]);

  const investigate = async () => {
    setLoading(true);
    setError(null);
    try {
      await api.investigate(caseId);
      await refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  const primary = bottlenecks?.find((b) => b.id === primaryId) ?? null;
  const secondary = bottlenecks?.filter((b) => b.id !== primaryId) ?? [];

  return (
    <div>
      <div className="btn-row" style={{ marginTop: 0, marginBottom: 16 }}>
        <button className="primary" onClick={investigate} disabled={loading}>
          {loading ? <Spinner /> : "Investigate this case"}
        </button>
        {health && (
          <span className="small muted" style={{ alignSelf: "center" }}>
            {health.open_bottlenecks} open · {health.resolved_bottlenecks} resolved ·{" "}
            {health.contradiction_count} contradictions · {health.recurring_count} recurring
          </span>
        )}
      </div>

      {error && <ErrorBanner message={error} />}

      {bottlenecks && bottlenecks.length === 0 && (
        <EmptyState>
          No bottleneck detected yet — click &ldquo;Investigate this case&rdquo; to run the Bottleneck Discovery Agent.
        </EmptyState>
      )}

      {primary && (
        <div className="hero-bottleneck">
          <div className="row between" style={{ marginBottom: 6 }}>
            <span className="small faint" style={{ textTransform: "uppercase", letterSpacing: "0.06em" }}>
              Primary bottleneck
            </span>
            <div className="row">
              <ConfidenceBadge value={primary.confidence} />
              <AttentionBadge value={primary.attention_state} />
            </div>
          </div>
          <div style={{ fontSize: 17, fontWeight: 650 }}>{primary.description}</div>
          <div className="small muted" style={{ marginTop: 6 }}>
            Type: {primary.type.replace(/_/g, " ")} · Status: {primary.status.replace(/_/g, " ")} ·
            Observed since {new Date(primary.first_observed_at).toLocaleDateString()}
          </div>
          {primary.blocked_items.length > 0 && (
            <div className="small" style={{ marginTop: 8 }}>
              <strong>Blocks:</strong> {primary.blocked_items.join(", ")}
            </div>
          )}
          {primary.missing_evidence.length > 0 && (
            <div className="small" style={{ marginTop: 4, color: "var(--high)" }}>
              {primary.missing_evidence.join(" ")}
            </div>
          )}
          <div className="small faint" style={{ marginTop: 10 }}>
            <strong>Why &ldquo;{primary.attention_state}&rdquo;:</strong>{" "}
            {explainAttention(primary)}
          </div>

          {rootCauses[primary.id] && (
            <>
              <div className="divider" />
              <div className="small faint" style={{ marginBottom: 10, textTransform: "uppercase", letterSpacing: "0.06em" }}>
                Root-cause chain
              </div>
              <RootCauseChain candidate={rootCauses[primary.id]} />
            </>
          )}
        </div>
      )}

      {secondary.length > 0 && (
        <div className="card" style={{ marginTop: 16 }}>
          <div className="small faint" style={{ marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.06em" }}>
            Secondary bottlenecks ({secondary.length})
          </div>
          <div className="stack">
            {secondary.map((b) => (
              <div key={b.id} className="card-flat">
                <div className="row between">
                  <strong className="small">{b.description}</strong>
                  <ConfidenceBadge value={b.confidence} />
                </div>
                <div className="small muted" style={{ marginTop: 4 }}>{b.type.replace(/_/g, " ")}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function explainAttention(b: Bottleneck): string {
  const f = b.severity_factors as Record<string, unknown>;
  const parts: string[] = [];
  if (typeof f.affected_transitions === "number") parts.push(`blocks ${f.affected_transitions} workflow transition(s)`);
  if (typeof f.age_days === "number") parts.push(`observed for ${f.age_days} day(s)`);
  if (f.confidence) parts.push(`confidence is ${f.confidence}`);
  return parts.length ? parts.join("; ") + "." : "explainable factors not available.";
}

// ---------------------------------------------------------------------
// TAB: Flow map (Section 6/33)
// ---------------------------------------------------------------------
function FlowTab({ caseId }: { caseId: string }) {
  const [graph, setGraph] = useState<FlowGraph | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getFlow(caseId).then(setGraph).catch((e) => setError(e instanceof ApiError ? e.message : String(e)));
  }, [caseId]);

  return (
    <div className="card">
      {error && <ErrorBanner message={error} />}
      {!graph && !error && <Spinner />}
      {graph && <FlowGraphView graph={graph} />}
      <div className="small faint" style={{ marginTop: 10 }}>
        Left column: pending transitions. Right column: dependencies gating them.
        Colour reflects status (green = satisfied, orange = unsatisfied, red = contradicted, grey = unknown).
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------
// TAB: Actions — "What can move it?" + Human Action Gate (Sections 20-25)
// ---------------------------------------------------------------------
function ActionsTab({ caseId }: { caseId: string }) {
  const [actions, setActions] = useState<ActionItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<{ actionId: string; newlyVisible: string[] } | null>(null);

  const refresh = useCallback(() => {
    api.listActions(caseId).then(setActions).catch((e) => setError(e instanceof ApiError ? e.message : String(e)));
  }, [caseId]);
  useEffect(refresh, [refresh]);

  const approve = async (a: ActionItem) => {
    setBusyId(a.id);
    setError(null);
    try {
      const res = await api.approveAction(caseId, a.id);
      setLastResult({ actionId: a.id, newlyVisible: res.newly_visible_bottlenecks });
      refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setBusyId(null);
    }
  };

  const reject = async (a: ActionItem) => {
    const reason = window.prompt("Reason for rejecting this proposed action?");
    if (reason === null) return;
    setBusyId(a.id);
    try {
      await api.rejectAction(caseId, a.id, reason || "No reason given.");
      refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div>
      {error && <ErrorBanner message={error} />}
      {!actions && !error && <Spinner />}
      {actions && actions.length === 0 && (
        <EmptyState>No safe actions proposed yet. Run &ldquo;Investigate this case&rdquo; first.</EmptyState>
      )}

      {lastResult && lastResult.newlyVisible.length > 0 && (
        <div className="card" style={{ borderColor: "var(--accent)" }}>
          <strong className="small">Reassessment:</strong>{" "}
          <span className="small">Resolving that action revealed {lastResult.newlyVisible.length} new bottleneck(s) that were previously hidden downstream.</span>
        </div>
      )}

      {actions?.map((a) => (
        <div key={a.id} className="card">
          <div className="row between">
            <strong className="small">{a.action_type.replace(/_/g, " ")}</strong>
            <StatusPill status={a.status} />
          </div>
          <div className="small" style={{ marginTop: 6 }}>{a.purpose}</div>
          <dl className="kv" style={{ marginTop: 10 }}>
            <dt>Required actor</dt><dd className="small">{a.required_actor}</dd>
            <dt>Expected effect</dt><dd className="small">{a.expected_effect}</dd>
            <dt>Risk</dt><dd className="small">{a.risk}</dd>
            <dt>Verification method</dt><dd className="small">{a.verification_method}</dd>
            {a.rejection_reason && (<><dt>Rejection reason</dt><dd className="small">{a.rejection_reason}</dd></>)}
            {Object.keys(a.result || {}).length > 0 && (
              <><dt>Result</dt><dd className="small mono">{JSON.stringify(a.result)}</dd></>
            )}
          </dl>
          {a.status === "PENDING_APPROVAL" && (
            <div className="btn-row">
              <button className="primary" disabled={busyId === a.id} onClick={() => approve(a)}>
                {busyId === a.id ? <Spinner /> : "Approve"}
              </button>
              <button className="danger" disabled={busyId === a.id} onClick={() => reject(a)}>Reject</button>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------
// TAB: Simulate — "What if we remove this bottleneck?" (Section 26/50)
// ---------------------------------------------------------------------
function SimulateTab({ caseId }: { caseId: string }) {
  const [graph, setGraph] = useState<FlowGraph | null>(null);
  const [selected, setSelected] = useState<string>("");
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.getFlow(caseId).then((g) => {
      setGraph(g);
      const firstDep = g.nodes.find((n) => n.kind === "dependency");
      if (firstDep) setSelected(firstDep.id);
    }).catch((e) => setError(e instanceof ApiError ? e.message : String(e)));
  }, [caseId]);

  const run = async () => {
    if (!selected) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      setResult(await api.simulate(caseId, selected));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  const dependencies = graph?.nodes.filter((n) => n.kind === "dependency") ?? [];

  return (
    <div className="card">
      <ModeFlag>Simulation only — never modifies real case state</ModeFlag>
      {error && <ErrorBanner message={error} />}
      <div className="row" style={{ marginBottom: 12 }}>
        <select value={selected} onChange={(e) => setSelected(e.target.value)} style={{ flex: 1, padding: "7px 10px", background: "var(--bg-inset)", color: "var(--text)", border: "1px solid var(--border-strong)", borderRadius: 6 }}>
          {dependencies.map((d) => <option key={d.id} value={d.id}>{d.description}</option>)}
        </select>
        <button className="primary" onClick={run} disabled={loading || !selected}>
          {loading ? <Spinner /> : "What if we remove this?"}
        </button>
      </div>

      {result && (
        <div className="stack">
          <div className="small"><strong>Removed:</strong> {result.removed_dependency}</div>
          <Row label="Unblocked transitions" items={result.unblocked_transitions} tone="CONFIRMED" />
          <Row label="Remains blocked" items={result.remains_blocked_transitions} tone="UNKNOWN" />
          <Row label="Newly relevant bottlenecks" items={result.newly_relevant_bottlenecks} tone="LIKELY" />
          <Row label="Remaining bottlenecks" items={result.remaining_bottlenecks} tone="POSSIBLE" />
        </div>
      )}
    </div>
  );
}

function Row({ label, items, tone }: { label: string; items: string[]; tone: string }) {
  return (
    <div className="card-flat">
      <div className="row between" style={{ marginBottom: items.length ? 6 : 0 }}>
        <span className="small faint">{label}</span>
        <span className={`badge badge-${tone}`}>{items.length}</span>
      </div>
      {items.length > 0 && <div className="small">{items.join(", ")}</div>}
    </div>
  );
}

// ---------------------------------------------------------------------
// TAB: Crash test — adversarial mutation testing (Section 29/59)
// ---------------------------------------------------------------------
function CrashTestTab({ caseId }: { caseId: string }) {
  const [mutations, setMutations] = useState<string[]>([]);
  const [mutation, setMutation] = useState("");
  const [graph, setGraph] = useState<FlowGraph | null>(null);
  const [target, setTarget] = useState("");
  const [result, setResult] = useState<CrashTestResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    Promise.all([api.listMutations(caseId), api.getFlow(caseId)]).then(([m, g]) => {
      setMutations(m);
      setMutation(m[0] ?? "");
      setGraph(g);
      const firstDep = g.nodes.find((n) => n.kind === "dependency");
      if (firstDep) setTarget(firstDep.id);
    }).catch((e) => setError(e instanceof ApiError ? e.message : String(e)));
  }, [caseId]);

  const run = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      setResult(await api.runCrashTest(caseId, mutation, target || undefined));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  const dependencies = graph?.nodes.filter((n) => n.kind === "dependency") ?? [];
  const resultTone = result?.result === "PASS" ? "CONFIRMED" : result?.result === "FAIL" ? "UNKNOWN" : "LIKELY";

  return (
    <div className="card">
      <ModeFlag>Simulation only — mutates a clone, never the real case</ModeFlag>
      {error && <ErrorBanner message={error} />}
      <div className="stack" style={{ marginBottom: 12 }}>
        <select value={mutation} onChange={(e) => setMutation(e.target.value)} style={{ padding: "7px 10px", background: "var(--bg-inset)", color: "var(--text)", border: "1px solid var(--border-strong)", borderRadius: 6 }}>
          {mutations.map((m) => <option key={m} value={m}>{m.replace(/_/g, " ")}</option>)}
        </select>
        <select value={target} onChange={(e) => setTarget(e.target.value)} style={{ padding: "7px 10px", background: "var(--bg-inset)", color: "var(--text)", border: "1px solid var(--border-strong)", borderRadius: 6 }}>
          {dependencies.map((d) => <option key={d.id} value={d.id}>{d.description}</option>)}
        </select>
        <button className="primary" onClick={run} disabled={loading}>{loading ? <Spinner /> : "Run mutation"}</button>
      </div>

      {result && (
        <div className="card-flat">
          <div className="row between" style={{ marginBottom: 8 }}>
            <strong className="small">{result.mutation.replace(/_/g, " ")} → {result.target_dependency}</strong>
            <span className={`badge badge-${resultTone}`}>{result.result}</span>
          </div>
          <div className="kv">
            <dt>Expected</dt><dd className="small">{result.expected_effect}</dd>
            <dt>Observed</dt><dd className="small">{result.observed_effect}</dd>
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------
// TAB: Documents — shows quarantine state (Section 41 security)
// ---------------------------------------------------------------------
function DocumentsTab({ caseId }: { caseId: string }) {
  const [docs, setDocs] = useState<CaseDocument[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getDocuments(caseId).then(setDocs).catch((e) => setError(e instanceof ApiError ? e.message : String(e)));
  }, [caseId]);

  return (
    <div>
      {error && <ErrorBanner message={error} />}
      {docs && docs.length === 0 && <EmptyState>No documents on file for this case.</EmptyState>}
      {docs?.map((d) => (
        <div key={d.id} className="card">
          <div className="row between">
            <strong className="small">{d.name}</strong>
            {d.quarantined && <span className="badge badge-UNKNOWN">QUARANTINED — suspected prompt injection</span>}
          </div>
          <div className="card-flat mono small" style={{ marginTop: 8, whiteSpace: "pre-wrap" }}>{d.content_text}</div>
          {d.quarantined && (
            <div className="small" style={{ marginTop: 8, color: "var(--high)" }}>
              This document contains embedded text resembling an instruction to the system.
              It is displayed here verbatim for human review only — its content was excluded
              from anything the agents used as case fact or evidence.
            </div>
          )}
          <div className="small faint mono" style={{ marginTop: 6 }}>sha256: {d.sha256}</div>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------
// TAB: History — bottleneck lifecycle timeline (Section 17)
// ---------------------------------------------------------------------
function HistoryTab({ caseId }: { caseId: string }) {
  const [entries, setEntries] = useState<HistoryEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getHistory(caseId).then(setEntries).catch((e) => setError(e instanceof ApiError ? e.message : String(e)));
  }, [caseId]);

  return (
    <div className="card">
      {error && <ErrorBanner message={error} />}
      {entries && entries.length === 0 && <EmptyState>No lifecycle transitions recorded yet.</EmptyState>}
      <div className="stack">
        {entries?.map((h) => (
          <div key={h.id} className="chain-step">
            <div className="chain-rail">
              <div className="chain-node" />
              <div className="chain-line" />
            </div>
            <div className="chain-body">
              <div className="small faint mono">{new Date(h.timestamp).toLocaleString()}</div>
              <div className="small"><strong>{h.from_status}</strong> → <strong>{h.to_status}</strong></div>
              {h.note && <div className="small muted">{h.note}</div>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------
// TAB: Audit — full correlation-id trail (Section 40)
// ---------------------------------------------------------------------
function AuditTab({ caseId }: { caseId: string }) {
  const [events, setEvents] = useState<AuditEvent[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getAudit(caseId).then(setEvents).catch((e) => setError(e instanceof ApiError ? e.message : String(e)));
  }, [caseId]);

  return (
    <div className="card">
      {error && <ErrorBanner message={error} />}
      {events && events.length === 0 && <EmptyState>No audit events recorded yet.</EmptyState>}
      {events && events.length > 0 && (
        <div>
          <div className="audit-row small faint" style={{ fontWeight: 700 }}>
            <span>Timestamp</span><span>Actor</span><span>Event</span>
          </div>
          {events.map((e) => (
            <div key={e.id} className="audit-row">
              <span className="mono faint">{new Date(e.timestamp).toLocaleTimeString()}</span>
              <span className="mono">{e.actor}</span>
              <span>
                {e.event}
                {Object.keys(e.result || {}).length > 0 && (
                  <span className="faint mono"> — {JSON.stringify(e.result)}</span>
                )}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
