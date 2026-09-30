/* Case Continuity Engine - frontend application (vanilla JS, no build step) */

const state = {
  cases: [],
  caseId: null,
  view: "command-center",
  provider: null,
};

const NAV = [
  ["command-center", "◆", "Command Center"],
  ["cases", "▤", "Cases"],
  ["current-state", "●", "Current State"],
  ["what-changed", "↯", "What Changed"],
  ["timeline", "─", "Timeline"],
  ["graph", "◈", "Case Graph"],
  ["handoff", "⇥", "Handoff"],
  ["conflicts", "!", "Conflicts"],
  ["simulate", "≈", "Simulate"],
  ["time-machine", "◷", "Time Machine"],
  ["evaluation", "✓", "Evaluation Lab"],
  ["audit", "▦", "Audit"],
  ["settings", "⚙", "Settings"],
];

function h(tag, attrs = {}, children = []) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (k === "class") el.className = v;
    else if (k === "html") el.innerHTML = v;
    else if (k.startsWith("on") && typeof v === "function") el.addEventListener(k.slice(2), v);
    else if (v !== null && v !== undefined) el.setAttribute(k, v);
  }
  for (const c of [].concat(children)) {
    if (c === null || c === undefined) continue;
    el.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
  }
  return el;
}

function toast(msg, isError = false) {
  const t = h("div", { class: `toast ${isError ? "error" : ""}` }, msg);
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 4200);
}

function fmtDate(iso) {
  if (!iso) return "—";
  try { return new Date(iso).toLocaleString(); } catch (_) { return iso; }
}

function pill(text, cls) {
  return h("span", { class: `pill ${cls || text}` }, text);
}

function statusPillClass(status) {
  return { open: "open", resolved: "resolved", superseded: "superseded", blocked: "blocked",
    approved: "approved", pending: "pending", rejected: "rejected", edited: "approved",
    passed: "passed", failed: "failed" }[status] || "";
}

// ---------------------------------------------------------------------------
// Shell / navigation
// ---------------------------------------------------------------------------

async function init() {
  renderShell();
  try {
    const health = await api.healthz();
    state.provider = health.llm_provider;
  } catch (e) { /* backend not reachable yet */ }
  await refreshCases();
  const hashView = location.hash.replace("#", "");
  state.view = NAV.find(([id]) => id === hashView) ? hashView : "command-center";
  renderNav();
  await renderView();
}

function renderShell() {
  const app = document.getElementById("app");
  app.innerHTML = "";
  const topbar = h("div", { id: "topbar" }, [
    h("div", { class: "brand" }, ["Case Continuity Engine", h("small", {}, "Never lose the state of a case.")]),
    h("div", { class: "case-picker" }, [
      h("select", { id: "case-select", onchange: onCaseChange }, []),
      h("span", { id: "freshness-badge" }, []),
    ]),
    h("button", { class: "btn small", onclick: seedDemo }, "Seed demo cases"),
    h("button", { class: "btn small primary", onclick: () => openNewCaseModal() }, "+ New case"),
  ]);
  const sidebar = h("div", { id: "sidebar" });
  const main = h("div", { id: "main" });
  app.appendChild(topbar);
  app.appendChild(sidebar);
  app.appendChild(main);
}

function renderNav() {
  const sidebar = document.getElementById("sidebar");
  sidebar.innerHTML = "";
  for (const [id, icon, label] of NAV) {
    sidebar.appendChild(h("div", {
      class: `nav-item ${state.view === id ? "active" : ""}`,
      onclick: () => setView(id),
    }, [h("span", { class: "icon" }, icon), label]));
  }
}

async function setView(id) {
  state.view = id;
  location.hash = id;
  renderNav();
  await renderView();
}

async function refreshCases() {
  try {
    state.cases = await api.listCases();
  } catch (e) {
    state.cases = [];
    toast("Could not reach the API. Is the backend running?", true);
  }
  const sel = document.getElementById("case-select");
  sel.innerHTML = "";
  if (!state.cases.length) {
    sel.appendChild(h("option", { value: "" }, "No cases yet"));
  }
  for (const c of state.cases) {
    sel.appendChild(h("option", { value: c.id }, `${c.demo_case_key ? `[${c.demo_case_key}] ` : ""}${c.title}`));
  }
  if (!state.caseId && state.cases.length) state.caseId = state.cases[0].id;
  if (state.caseId) sel.value = state.caseId;
  updateFreshnessBadge();
}

function updateFreshnessBadge() {
  const badge = document.getElementById("freshness-badge");
  const c = state.cases.find((c) => c.id === state.caseId);
  badge.innerHTML = "";
  if (!c) return;
  badge.appendChild(h("span", { class: `badge ${c.freshness.toLowerCase()}` }, c.freshness));
  if (c.is_demo) badge.appendChild(h("span", { class: "badge demo", style: "margin-left:6px" }, "demo data"));
}

async function onCaseChange(e) {
  state.caseId = e.target.value;
  updateFreshnessBadge();
  await renderView();
}

async function seedDemo() {
  try {
    const r = await api.seedDemo();
    toast(r.created_case_ids.length ? `Seeded ${r.created_case_ids.length} demo case(s).` : "Demo cases already present.");
    await refreshCases();
    await renderView();
  } catch (e) { toast(e.message, true); }
}

// ---------------------------------------------------------------------------
// View dispatch
// ---------------------------------------------------------------------------

async function renderView() {
  const main = document.getElementById("main");
  main.innerHTML = "";
  const needsCase = state.view !== "cases" && state.view !== "settings" && state.view !== "evaluation";
  if (needsCase && !state.caseId) {
    main.appendChild(h("div", { class: "empty-state" }, "No case selected. Seed the demo cases or create a new one."));
    return;
  }
  try {
    const renderer = {
      "command-center": renderCommandCenter,
      "cases": renderCasesView,
      "current-state": renderCurrentState,
      "what-changed": renderWhatChanged,
      "timeline": renderTimeline,
      "graph": renderGraph,
      "handoff": renderHandoff,
      "conflicts": renderConflicts,
      "simulate": renderSimulate,
      "time-machine": renderTimeMachine,
      "evaluation": renderEvaluation,
      "audit": renderAudit,
      "settings": renderSettings,
    }[state.view];
    await renderer(main);
  } catch (e) {
    main.appendChild(h("div", { class: "empty-state" }, `Error loading view: ${e.message}`));
  }
}

// ---------------------------------------------------------------------------
// Command Center (section 36)
// ---------------------------------------------------------------------------

async function renderCommandCenter(main) {
  const [st, health, changes, conflicts, proposals] = await Promise.all([
    api.getState(state.caseId), api.getContinuityHealth(state.caseId),
    api.getChanges(state.caseId), api.getConflicts(state.caseId),
    api.getProposals(state.caseId, "pending"),
  ]);
  main.appendChild(h("h1", { class: "view-title" }, "Command Center"));
  main.appendChild(h("div", { class: "view-subtitle" }, `${st.snapshot.title} — ${st.snapshot.procedural_stage}`));

  const cards = h("div", { class: "grid cols-4 section" }, [
    metricCard("Current State", `v${st.current_version_number}`, "Click Current State for full board", () => setView("current-state")),
    metricCard("State Freshness", st.freshness.level, st.freshness.reasons[0] || "", () => setView("current-state")),
    metricCard("Open Items", st.snapshot.open_items_count, "obligations + actions still open", () => setView("current-state")),
    metricCard("Pending Reviews", proposals.length, "awaiting human decision", () => setView("current-state")),
    metricCard("Recent Changes", changes.changes ? changes.changes.length : 0, `since v${changes.from_version ?? "—"}`, () => setView("what-changed")),
    metricCard("Conflicts", conflicts.filter((c) => c.human_review_status === "pending").length, "unresolved", () => setView("conflicts")),
    metricCard("Unprocessed Artifacts", health.unprocessed_artifacts.count, "documents with no derived event", () => setView("audit")),
    metricCard("Missing Source Refs", health.missing_source_references.count, "broken provenance links", () => setView("audit")),
  ]);
  main.appendChild(cards);

  main.appendChild(h("div", { class: "section" }, [
    h("h2", {}, "Continuity Health"),
    h("div", { class: "card" }, renderHealthSummary(health)),
  ]));
}

function metricCard(label, metric, hint, onclick) {
  return h("div", { class: "card clickable", onclick }, [
    h("div", { class: "label" }, label),
    h("div", { class: "metric" }, String(metric)),
    h("div", { class: "hint" }, hint || ""),
  ]);
}

function renderHealthSummary(health) {
  const rows = Object.entries(health).map(([key, v]) =>
    h("tr", {}, [
      h("td", {}, key.replace(/_/g, " ")),
      h("td", {}, String(v.count)),
      h("td", {}, v.count === 0 ? pill("clear", "resolved") : pill("attention", "blocked")),
    ])
  );
  return h("table", {}, [
    h("thead", {}, h("tr", {}, [h("th", {}, "Category"), h("th", {}, "Count"), h("th", {}, "")])),
    h("tbody", {}, rows),
  ]);
}

// ---------------------------------------------------------------------------
// Cases view (list + create)
// ---------------------------------------------------------------------------

async function renderCasesView(main) {
  main.appendChild(h("h1", { class: "view-title" }, "Cases"));
  main.appendChild(h("div", { class: "view-subtitle" }, `${state.cases.length} case(s)`));
  const rows = state.cases.map((c) => h("tr", { class: "clickable", onclick: () => { state.caseId = c.id; setView("command-center"); } }, [
    h("td", {}, c.demo_case_key ? `[${c.demo_case_key}]` : ""),
    h("td", {}, c.title),
    h("td", {}, c.case_number || "—"),
    h("td", {}, c.procedural_stage),
    h("td", {}, `v${c.current_version_number}`),
    h("td", {}, h("span", { class: `badge ${c.freshness.toLowerCase()}` }, c.freshness)),
    h("td", {}, fmtDate(c.created_at)),
  ]));
  main.appendChild(h("table", {}, [
    h("thead", {}, h("tr", {}, ["Demo", "Title", "Case #", "Stage", "Version", "Freshness", "Created"].map((t) => h("th", {}, t)))),
    h("tbody", {}, rows),
  ]));
}

function openNewCaseModal() {
  const backdrop = h("div", { class: "modal-backdrop", onclick: (e) => { if (e.target === backdrop) backdrop.remove(); } });
  const titleInput = h("input", { type: "text", placeholder: "e.g. Fictional Petitioner v. Fictional Respondent" });
  const numberInput = h("input", { type: "text", placeholder: "Case number (optional)" });
  const courtInput = h("input", { type: "text", placeholder: "Court (optional)" });
  const modal = h("div", { class: "modal" }, [
    h("h3", {}, "New case"),
    h("div", { class: "section" }, [h("label", {}, "Title"), titleInput]),
    h("div", { class: "section" }, [h("label", {}, "Case number"), numberInput]),
    h("div", { class: "section" }, [h("label", {}, "Court"), courtInput]),
    h("div", { class: "modal-actions" }, [
      h("button", { class: "btn", onclick: () => backdrop.remove() }, "Cancel"),
      h("button", {
        class: "btn primary", onclick: async () => {
          if (!titleInput.value.trim()) { toast("Title is required.", true); return; }
          try {
            const created = await api.createCase({ title: titleInput.value, case_number: numberInput.value, court: courtInput.value });
            backdrop.remove();
            await refreshCases();
            state.caseId = created.id;
            document.getElementById("case-select").value = created.id;
            setView("command-center");
          } catch (e) { toast(e.message, true); }
        },
      }, "Create"),
    ]),
  ]);
  backdrop.appendChild(modal);
  document.body.appendChild(backdrop);
}

// ---------------------------------------------------------------------------
// Current State (sections 16-17, 37)
// ---------------------------------------------------------------------------

async function renderCurrentState(main) {
  const [st, proposals, conflicts] = await Promise.all([
    api.getState(state.caseId), api.getProposals(state.caseId, "pending"), api.getConflicts(state.caseId),
  ]);
  const snap = st.snapshot;
  main.appendChild(h("h1", { class: "view-title" }, "Current Case State"));
  main.appendChild(h("div", { class: "view-subtitle" }, [
    h("span", { class: `badge ${st.freshness.level.toLowerCase()}` }, `Freshness: ${st.freshness.level}`),
    " — ", st.freshness.reasons.join(" "),
  ]));

  main.appendChild(h("div", { class: "grid cols-4 section" }, [
    metricCard("Procedural Stage", st.procedural_stage, "", null),
    metricCard("Open Items", snap.open_items_count, "obligations + actions", null),
    metricCard("Unresolved Conflicts", snap.unresolved_conflicts_count, "", () => setView("conflicts")),
    metricCard("Pending Human Reviews", proposals.length, "", () => setView("current-state")),
  ]));

  main.appendChild(entityBoard("Deadlines", snap.deadlines, ["label", "due_date", "status"]));
  main.appendChild(entityBoard("Obligations", snap.obligations, ["description", "owner_party", "status"]));
  main.appendChild(entityBoard("Orders", snap.orders, ["order_date", "summary", "status"]));
  main.appendChild(entityBoard("Hearings", snap.hearings, ["scheduled_date", "occurred", "status"]));
  main.appendChild(entityBoard("Evidence", snap.evidence, ["label", "status"]));
  main.appendChild(entityBoard("Actions", snap.actions, ["description", "assignee", "status"]));
  main.appendChild(entityBoard("Documents", snap.documents, ["filename", "doc_type"]));

  main.appendChild(h("div", { class: "section" }, [
    h("h2", {}, "Pending Human Review Gate"),
    proposals.length ? h("div", {}, proposals.map(proposalCard)) : h("div", { class: "empty-state" }, "Nothing awaiting review."),
  ]));
}

function entityBoard(title, dict, fields) {
  const entries = Object.entries(dict || {});
  const rows = entries.map(([id, item]) => h("tr", {}, [
    ...fields.map((f) => h("td", {}, f === "status" ? pill(String(item[f]), statusPillClass(item[f])) : String(item[f] ?? "—"))),
  ]));
  return h("div", { class: "section" }, [
    h("h2", {}, `${title} (${entries.length})`),
    entries.length
      ? h("div", { class: "card" }, h("table", {}, [
          h("thead", {}, h("tr", {}, fields.map((f) => h("th", {}, f.replace(/_/g, " "))))),
          h("tbody", {}, rows),
        ]))
      : h("div", { class: "empty-state" }, "None."),
  ]);
}

function proposalCard(p) {
  const container = h("div", { class: "card", style: "margin-bottom: 10px" });
  container.appendChild(h("div", { class: "label" }, `${p.entity_type.toUpperCase()} — ${p.nature}`));
  container.appendChild(h("div", { class: "kv" }, [
    h("dt", {}, "Reason"), h("dd", {}, p.reason),
    h("dt", {}, "Confidence"), h("dd", {}, p.confidence.toFixed(2)),
    h("dt", {}, "Before"), h("dd", { class: "mono" }, JSON.stringify(p.proposed_before)),
    h("dt", {}, "After"), h("dd", { class: "mono" }, JSON.stringify(p.proposed_after)),
    h("dt", {}, "Source event"), h("dd", { class: "mono" }, p.source_event_id),
  ]));
  const actions = h("div", { class: "modal-actions", style: "justify-content:flex-start" }, [
    h("button", { class: "btn primary small", onclick: () => decide(p.id, "approve") }, "Approve"),
    h("button", { class: "btn small", onclick: () => decide(p.id, "edit") }, "Edit & approve"),
    h("button", { class: "btn danger small", onclick: () => decide(p.id, "reject") }, "Reject"),
  ]);
  container.appendChild(actions);
  return container;

  async function decide(id, decision) {
    let edited_after = null;
    if (decision === "edit") {
      const raw = prompt("Edit proposed_after JSON:", JSON.stringify(p.proposed_after));
      if (raw === null) return;
      try { edited_after = JSON.parse(raw); } catch (e) { toast("Invalid JSON.", true); return; }
    }
    try {
      const result = await api.reviewProposal(state.caseId, id, { decision, reviewer: "user", edited_after });
      if (result.status === "verification_failed") {
        toast(`VERIFICATION FAILED: ${result.failure_reasons.join("; ")}`, true);
      } else {
        toast(`Proposal ${result.status}.`);
      }
      await refreshCases();
      await renderView();
    } catch (e) { toast(e.message, true); }
  }
}

// ---------------------------------------------------------------------------
// What Changed (section 15, 38)
// ---------------------------------------------------------------------------

async function renderWhatChanged(main) {
  const data = await api.getChanges(state.caseId);
  main.appendChild(h("h1", { class: "view-title" }, "What Changed?"));
  if (!data.changes || !data.changes.length) {
    main.appendChild(h("div", { class: "view-subtitle" }, data.message || "No changes yet."));
    return;
  }
  main.appendChild(h("div", { class: "view-subtitle" }, `Comparing state v${data.from_version} → v${data.to_version}`));
  const grouped = {};
  for (const c of data.changes) {
    grouped[c.category] = grouped[c.category] || [];
    grouped[c.category].push(c);
  }
  for (const [category, items] of Object.entries(grouped)) {
    main.appendChild(h("div", { class: "section" }, [
      h("h2", {}, `${category} (${items.length})`),
      h("div", {}, items.map((c) => h("div", { class: "card", style: "margin-bottom:8px" }, [
        h("div", { class: "label" }, c.entity_type),
        c.before && Object.keys(c.before).length ? h("div", { class: "mono diff-removed" }, JSON.stringify(c.before)) : null,
        c.after && Object.keys(c.after).length ? h("div", { class: "mono diff-added" }, JSON.stringify(c.after)) : null,
        h("div", { class: "hint" }, c.reason),
        h("span", { class: "provenance-chip", onclick: () => viewSource(c.source_event_id) }, `VIEW SOURCE: ${c.source_event_id.slice(0, 8)}`),
      ]))),
    ]));
  }
}

async function viewSource(eventId) {
  try {
    const events = await api.getEvents(state.caseId);
    const ev = events.find((e) => e.event_id === eventId);
    if (!ev) { toast("Source event not found.", true); return; }
    const backdrop = h("div", { class: "modal-backdrop", onclick: (e) => { if (e.target === backdrop) backdrop.remove(); } });
    const modal = h("div", { class: "modal" }, [
      h("h3", {}, "Source event"),
      h("div", { class: "kv" }, [
        h("dt", {}, "Type"), h("dd", {}, ev.event_type),
        h("dt", {}, "Actor"), h("dd", {}, ev.actor),
        h("dt", {}, "Timestamp"), h("dd", {}, fmtDate(ev.timestamp)),
        h("dt", {}, "Confidence"), h("dd", {}, String(ev.confidence)),
        h("dt", {}, "Provenance"), h("dd", { class: "mono" }, JSON.stringify(ev.provenance)),
      ]),
      h("div", {}, ev.description),
      h("div", { class: "modal-actions" }, [h("button", { class: "btn", onclick: () => backdrop.remove() }, "Close")]),
    ]);
    backdrop.appendChild(modal);
    document.body.appendChild(backdrop);
  } catch (e) { toast(e.message, true); }
}

// ---------------------------------------------------------------------------
// Timeline (section 39) + ingestion
// ---------------------------------------------------------------------------

async function renderTimeline(main) {
  main.appendChild(h("h1", { class: "view-title" }, "Case Timeline"));
  main.appendChild(uploadWidget());

  const filterBar = h("div", { class: "section" });
  let activeFilter = "";
  const timelineHost = h("div", { class: "section" });
  main.appendChild(filterBar);
  main.appendChild(timelineHost);

  const nodes = await api.getTimeline(state.caseId);
  const types = [...new Set(nodes.map((n) => n.event_type))];
  filterBar.appendChild(h("select", {
    onchange: (e) => { activeFilter = e.target.value; draw(); },
  }, [h("option", { value: "" }, "All event types"), ...types.map((t) => h("option", { value: t }, t))]));

  draw();
  function draw() {
    timelineHost.innerHTML = "";
    const filtered = activeFilter ? nodes.filter((n) => n.event_type === activeFilter) : nodes;
    if (!filtered.length) { timelineHost.appendChild(h("div", { class: "empty-state" }, "No events.")); return; }
    const tl = h("div", { class: "timeline" });
    for (const n of filtered) {
      tl.appendChild(h("div", { class: "tl-node" }, [
        h("div", { class: "tl-type" }, n.event_type),
        h("div", { class: "tl-meta" }, `${fmtDate(n.timestamp)} — ${n.actor} — confidence ${n.confidence.toFixed(2)}`),
        h("div", { class: "tl-desc" }, n.description),
        h("span", { class: "provenance-chip", onclick: () => viewSource(n.event_id) }, "provenance"),
      ]));
    }
    timelineHost.appendChild(tl);
  }
}

function uploadWidget() {
  const fileInput = h("input", { type: "file" });
  const typeInput = h("input", { type: "text", placeholder: "doc type hint (optional): order, filing, notice..." });
  const status = h("div", { class: "hint" });
  const box = h("div", { class: "card section" }, [
    h("div", { class: "label" }, "Ingest a new artifact"),
    h("div", { class: "grid cols-2", style: "margin-bottom:8px" }, [fileInput, typeInput]),
    h("button", {
      class: "btn primary", onclick: async () => {
        if (!fileInput.files.length) { toast("Choose a file first.", true); return; }
        const fd = new FormData();
        fd.append("file", fileInput.files[0]);
        fd.append("doc_type_hint", typeInput.value || "");
        fd.append("actor", "user");
        status.textContent = "Processing through Intake → Extraction → Change Detection → Verification…";
        try {
          const result = await api.ingest(state.caseId, fd);
          status.textContent = `Done. ${result.proposals.length} proposal(s) generated, ` +
            `${result.committed_versions.length} auto-committed, ${result.conflicts_detected.length} conflict(s) detected.` +
            (result.prompt_injection_flagged ? " ⚠ Possible prompt-injection content flagged — forced to human review." : "");
          await refreshCases();
          await renderView();
        } catch (e) { status.textContent = ""; toast(e.message, true); }
      },
    }, "Upload & process"),
    status,
  ]);
  return box;
}

// ---------------------------------------------------------------------------
// Case Graph (section 40) - lightweight layered SVG, no external deps
// ---------------------------------------------------------------------------

async function renderGraph(main) {
  main.appendChild(h("h1", { class: "view-title" }, "Continuity Graph"));
  main.appendChild(h("div", { class: "view-subtitle" }, "Typed nodes and edges, derived live from case state. Click a node for details."));
  const data = await api.getGraph(state.caseId);
  const svg = buildGraphSvg(data);
  main.appendChild(svg);
}

function buildGraphSvg(data) {
  const width = 1100, height = 560;
  const svgNS = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(svgNS, "svg");
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.setAttribute("class", "graph-svg");

  const typeOrder = ["CASE", "EVENT", "DOCUMENT", "ORDER", "HEARING", "DEADLINE", "OBLIGATION", "EVIDENCE", "ACTION", "STATE_VERSION"];
  const byType = {};
  for (const n of data.nodes) { (byType[n.type] = byType[n.type] || []).push(n); }
  const cols = typeOrder.filter((t) => byType[t]);
  const colWidth = width / cols.length;
  const pos = {};
  cols.forEach((type, ci) => {
    const items = byType[type];
    items.forEach((n, ri) => {
      const x = colWidth * ci + colWidth / 2;
      const y = 40 + (height - 80) * (items.length > 1 ? ri / (items.length - 1) : 0.5);
      pos[n.id] = { x, y, node: n };
    });
  });

  for (const e of data.edges) {
    const a = pos[e.from], b = pos[e.to];
    if (!a || !b) continue;
    const line = document.createElementNS(svgNS, "line");
    line.setAttribute("x1", a.x); line.setAttribute("y1", a.y);
    line.setAttribute("x2", b.x); line.setAttribute("y2", b.y);
    line.setAttribute("class", `graph-edge ${e.provenance ? "provenance" : ""}`);
    svg.appendChild(line);
  }

  for (const { x, y, node } of Object.values(pos)) {
    const g = document.createElementNS(svgNS, "g");
    g.style.cursor = "pointer";
    const circle = document.createElementNS(svgNS, "circle");
    circle.setAttribute("cx", x); circle.setAttribute("cy", y); circle.setAttribute("r", 6);
    circle.setAttribute("fill", colorForType(node.type));
    g.appendChild(circle);
    const label = document.createElementNS(svgNS, "text");
    label.setAttribute("x", x); label.setAttribute("y", y - 10);
    label.setAttribute("text-anchor", "middle");
    label.setAttribute("class", "graph-node-label");
    label.textContent = node.label.length > 18 ? node.label.slice(0, 18) + "…" : node.label;
    g.appendChild(label);
    g.addEventListener("click", () => alert(`${node.type}\n${JSON.stringify(node, null, 2)}`));
    svg.appendChild(g);
  }

  const wrapper = document.createElement("div");
  wrapper.style.overflowX = "auto";
  wrapper.appendChild(svg);
  return wrapper;
}

function colorForType(type) {
  const map = {
    CASE: "#c9a86a", EVENT: "#4f8cff", DOCUMENT: "#7c8898", ORDER: "#e8b445",
    HEARING: "#e5677a", DEADLINE: "#3ecf8e", OBLIGATION: "#4f8cff", EVIDENCE: "#c9a86a",
    ACTION: "#e8b445", STATE_VERSION: "#eef1f5",
  };
  return map[type] || "#7c8898";
}

// ---------------------------------------------------------------------------
// Handoff (section 20, 41)
// ---------------------------------------------------------------------------

async function renderHandoff(main) {
  main.appendChild(h("h1", { class: "view-title" }, "Case Handoff"));
  const fromInput = h("input", { type: "text", placeholder: "From role (e.g. Legal Aid Intake)", value: "Legal Aid Intake" });
  const toInput = h("input", { type: "text", placeholder: "To role (e.g. Advocate Review)", value: "Advocate Review" });
  const resultHost = h("div", { class: "section" });
  main.appendChild(h("div", { class: "card section" }, [
    h("div", { class: "grid cols-2", style: "margin-bottom:8px" }, [fromInput, toInput]),
    h("button", {
      class: "btn primary", onclick: async () => {
        try {
          const handoff = await api.prepareHandoff(state.caseId, { from_role: fromInput.value, to_role: toInput.value });
          renderHandoffResult(resultHost, handoff);
        } catch (e) { toast(e.message, true); }
      },
    }, "Prepare handoff context"),
  ]));
  main.appendChild(resultHost);
}

function renderHandoffResult(host, handoff) {
  host.innerHTML = "";
  const ctx = handoff.context;
  host.appendChild(h("div", { class: "card" }, [
    h("div", { class: "label" }, `HANDOFF — ${handoff.status.toUpperCase()}`),
    h("div", { class: "kv" }, [
      h("dt", {}, "State freshness"), h("dd", {}, ctx.state_freshness.level),
      h("dt", {}, "Open obligations"), h("dd", {}, ctx.unresolved_items.open_obligations.length),
      h("dt", {}, "Open deadlines"), h("dd", {}, ctx.unresolved_items.open_deadlines.length),
      h("dt", {}, "Contradictions"), h("dd", {}, ctx.contradictions.length),
      h("dt", {}, "Uncertainties (pending review)"), h("dd", {}, ctx.uncertainties.length),
    ]),
    h("h2", {}, "Suggested review points"),
    ctx.suggested_review_points.length
      ? h("ul", {}, ctx.suggested_review_points.map((p) => h("li", {}, p)))
      : h("div", { class: "empty-state" }, "None."),
    h("div", { class: "modal-actions", style: "justify-content:flex-start" }, [
      h("button", {
        class: "btn primary", onclick: async () => {
          await api.approveHandoff(state.caseId, handoff.id, { reviewer: "user" });
          toast("Handoff approved.");
          renderHandoffResult(host, { ...handoff, status: "approved" });
        },
      }, "Approve handoff"),
    ]),
  ]));
}

// ---------------------------------------------------------------------------
// Conflicts (sections 13, 27)
// ---------------------------------------------------------------------------

async function renderConflicts(main) {
  main.appendChild(h("h1", { class: "view-title" }, "Conflicts"));
  const conflicts = await api.getConflicts(state.caseId);
  if (!conflicts.length) { main.appendChild(h("div", { class: "empty-state" }, "No conflicts recorded.")); return; }
  for (const c of conflicts) {
    main.appendChild(h("div", { class: "card section" }, [
      h("div", { class: "label" }, c.conflict_type),
      h("div", {}, c.what_conflicts),
      h("div", { class: "hint" }, c.possible_explanation),
      h("div", { class: "kv", style: "margin-top:8px" }, [
        h("dt", {}, "Source A"), h("dd", {}, h("span", { class: "provenance-chip", onclick: () => viewSource(c.source_a_event_id) }, c.source_a_event_id.slice(0, 10))),
        h("dt", {}, "Source B"), h("dd", {}, h("span", { class: "provenance-chip", onclick: () => viewSource(c.source_b_event_id) }, c.source_b_event_id.slice(0, 10))),
        h("dt", {}, "Confidence"), h("dd", {}, c.confidence.toFixed(2)),
        h("dt", {}, "Status"), h("dd", {}, pill(c.human_review_status, statusPillClass(c.human_review_status))),
      ]),
      c.human_review_status === "pending" ? h("button", {
        class: "btn primary small", onclick: async () => {
          await api.resolveConflict(state.caseId, c.id, { reviewer: "user", resolution_note: "Reviewed in UI." });
          toast("Conflict marked resolved.");
          await renderView();
        },
      }, "Mark resolved") : null,
    ]));
  }
}

// ---------------------------------------------------------------------------
// Simulate (sections 23-24)
// ---------------------------------------------------------------------------

async function renderSimulate(main) {
  main.appendChild(h("h1", { class: "view-title" }, "Simulation"));
  main.appendChild(h("div", { class: "sim-banner" }, "SIMULATION ONLY — operates on a cloned state, never affects the real case"));

  const st = await api.getState(state.caseId);
  const snap = st.snapshot;
  const resultHost = h("div", { class: "section" });

  // Counterfactual removal
  const collSelect = h("select", {}, ["deadlines", "obligations", "orders", "hearings", "evidence", "actions"].map((c) => h("option", { value: c }, c)));
  const entitySelect = h("select", {});
  function fillEntities() {
    entitySelect.innerHTML = "";
    Object.keys(snap[collSelect.value] || {}).forEach((id) => entitySelect.appendChild(h("option", { value: id }, `${id.slice(0, 8)} — ${JSON.stringify(snap[collSelect.value][id]).slice(0, 40)}`)));
  }
  collSelect.addEventListener("change", fillEntities);
  fillEntities();

  main.appendChild(h("div", { class: "card section" }, [
    h("div", { class: "label" }, "What if this item had not happened?"),
    h("div", { class: "grid cols-2", style: "margin-bottom:8px" }, [collSelect, entitySelect]),
    h("button", {
      class: "btn primary", onclick: async () => {
        if (!entitySelect.value) { toast("No entity to remove.", true); return; }
        const r = await api.simulateRemove(state.caseId, { collection: collSelect.value, entity_id: entitySelect.value });
        renderSimResult(resultHost, r);
      },
    }, "Run counterfactual"),
  ]));

  // Future state preview
  const eventTypeSelect = h("select", {}, ["order_received", "obligation_created", "deadline_created", "hearing_occurred", "reply_received", "evidence_added"].map((t) => h("option", { value: t }, t)));
  main.appendChild(h("div", { class: "card section" }, [
    h("div", { class: "label" }, "Future State Preview (workflow projection, not a legal outcome prediction)"),
    eventTypeSelect,
    h("button", {
      class: "btn primary", style: "margin-top:8px",
      onclick: async () => {
        const r = await api.simulateFutureState(state.caseId, { current_event_type: eventTypeSelect.value });
        renderSimResult(resultHost, r);
      },
    }, "Project next states"),
  ]));

  main.appendChild(resultHost);
}

function renderSimResult(host, r) {
  host.innerHTML = "";
  host.appendChild(h("div", { class: "card" }, [
    h("div", { class: "sim-banner" }, r.label || "SIMULATION ONLY"),
    h("div", {}, r.hypothesis || ""),
    r.simulated_next_state ? h("div", { class: "kv" }, [
      h("dt", {}, "Current"), h("dd", {}, r.current),
      h("dt", {}, "Simulated next"), h("dd", {}, (r.simulated_next_state || []).join(", ") || "—"),
      h("dt", {}, "Simulated follow-up"), h("dd", {}, (r.simulated_follow_up || []).join(", ") || "—"),
    ]) : h("pre", { class: "mono" }, JSON.stringify(r.diff_vs_actual?.summary || {}, null, 2)),
  ]));
}

// ---------------------------------------------------------------------------
// Time Machine (sections 21-22, 42-43)
// ---------------------------------------------------------------------------

async function renderTimeMachine(main) {
  main.appendChild(h("h1", { class: "view-title" }, "Time Machine"));
  const versions = await api.getVersions(state.caseId);
  if (!versions.length) { main.appendChild(h("div", { class: "empty-state" }, "No versions yet.")); return; }

  const slider = h("input", { type: "range", min: "0", max: String(versions.length - 1), value: String(versions.length - 1) });
  const label = h("div", { class: "hint" });
  const host = h("div", { class: "section" });
  main.appendChild(h("div", { class: "scrubber" }, [
    h("span", {}, "V" + versions[0].version_number), slider, h("span", {}, "V" + versions[versions.length - 1].version_number),
  ]));
  main.appendChild(label);
  main.appendChild(host);
  main.appendChild(h("button", { class: "btn", onclick: replay }, "▶ Replay from V0"));

  slider.addEventListener("input", () => draw(versions[+slider.value].version_number));
  draw(versions[versions.length - 1].version_number);

  async function draw(versionNumber) {
    const v = await api.getVersion(state.caseId, versionNumber);
    label.textContent = `V${v.version_number} — ${v.label} — ${fmtDate(v.created_at)} — freshness at the time: ${v.freshness}`;
    host.innerHTML = "";
    host.appendChild(entityBoard("Deadlines", v.snapshot.deadlines, ["label", "due_date", "status"]));
    host.appendChild(entityBoard("Obligations", v.snapshot.obligations, ["description", "owner_party", "status"]));
    host.appendChild(entityBoard("Orders", v.snapshot.orders, ["order_date", "summary", "status"]));
    host.appendChild(entityBoard("Actions", v.snapshot.actions, ["description", "assignee", "status"]));
    if (versionNumber < versions[versions.length - 1].version_number) {
      const compareBtn = h("button", {
        class: "btn small", onclick: async () => {
          const d = await api.getDiff(state.caseId, versionNumber, versions[versions.length - 1].version_number);
          alert(`Diff v${versionNumber} → v${versions[versions.length - 1].version_number}:\n` +
            JSON.stringify(d.diff.summary, null, 2));
        },
      }, "Compare with current");
      host.appendChild(compareBtn);
    }
  }

  async function replay() {
    for (const v of versions) {
      slider.value = String(v.version_number);
      await draw(v.version_number);
      await new Promise((r) => setTimeout(r, 900));
    }
  }
}

// ---------------------------------------------------------------------------
// Evaluation Lab (section 50)
// ---------------------------------------------------------------------------

async function renderEvaluation(main) {
  main.appendChild(h("h1", { class: "view-title" }, "Evaluation Lab"));
  main.appendChild(h("div", { class: "view-subtitle" }, "Every metric below is either MEASURED from this instance's real data, or explicitly NOT_MEASURED. Nothing here is invented."));
  const scope = h("select", {}, [h("option", { value: "" }, "All cases"), ...state.cases.map((c) => h("option", { value: c.id }, c.title))]);
  const host = h("div", { class: "section" });
  main.appendChild(scope);
  main.appendChild(host);
  scope.addEventListener("change", () => load());
  await load();

  async function load() {
    const data = await api.getEvaluation(scope.value || undefined);
    host.innerHTML = "";
    for (const [key, v] of Object.entries(data)) {
      const card = h("div", { class: "card section" }, [
        h("div", { class: "label" }, key.replace(/_/g, " ")),
        h("span", { class: `badge ${v.status === "MEASURED" ? "fresh" : "unknown"}` }, v.status),
        h("pre", { class: "mono", style: "margin-top:8px;white-space:pre-wrap" }, JSON.stringify(
          Object.fromEntries(Object.entries(v).filter(([k]) => k !== "status")), null, 2)),
      ]);
      host.appendChild(card);
    }
  }
}

// ---------------------------------------------------------------------------
// Audit (section 30)
// ---------------------------------------------------------------------------

async function renderAudit(main) {
  main.appendChild(h("h1", { class: "view-title" }, "Audit Trail"));
  const data = await api.getAudit(state.caseId);
  main.appendChild(h("div", { class: "section" }, [
    h("h2", {}, `Audit events (${data.audit_trail.length})`),
    h("table", {}, [
      h("thead", {}, h("tr", {}, ["Time", "Actor", "Type", "Source", "Result"].map((t) => h("th", {}, t)))),
      h("tbody", {}, data.audit_trail.map((a) => h("tr", {}, [
        h("td", {}, fmtDate(a.timestamp)), h("td", {}, a.actor), h("td", {}, a.event_type),
        h("td", { class: "mono" }, (a.source || "").slice(0, 14)), h("td", {}, a.result),
      ]))),
    ]),
  ]));
  main.appendChild(h("div", { class: "section" }, [
    h("h2", {}, `Agent runs (${data.agent_runs.length})`),
    h("table", {}, [
      h("thead", {}, h("tr", {}, ["Started", "Agent", "Latency (ms)", "Success", "Output"].map((t) => h("th", {}, t)))),
      h("tbody", {}, data.agent_runs.map((r) => h("tr", {}, [
        h("td", {}, fmtDate(r.started_at)), h("td", {}, r.agent_name), h("td", {}, r.latency_ms.toFixed(1)),
        h("td", {}, r.success ? pill("passed", "passed") : pill("failed", "failed")),
        h("td", { class: "mono" }, (r.output_summary || "").slice(0, 40)),
      ]))),
    ]),
  ]));
}

// ---------------------------------------------------------------------------
// Settings
// ---------------------------------------------------------------------------

async function renderSettings(main) {
  main.appendChild(h("h1", { class: "view-title" }, "Settings"));
  let health;
  try { health = await api.healthz(); } catch (e) { health = { status: "unreachable", llm_provider: "?", app_env: "?" }; }
  main.appendChild(h("div", { class: "card" }, [
    h("div", { class: "kv" }, [
      h("dt", {}, "API status"), h("dd", {}, health.status),
      h("dt", {}, "LLM provider"), h("dd", {}, health.llm_provider + (health.llm_provider === "mock" ? " (offline demo mode)" : "")),
      h("dt", {}, "App environment"), h("dd", {}, health.app_env),
    ]),
    h("div", { class: "hint" }, "To use a real LLM provider, set LLM_PROVIDER=anthropic and LLM_API_KEY in the backend's environment (.env). The frontend never receives an API key."),
  ]));
}

window.addEventListener("hashchange", () => {
  const v = location.hash.replace("#", "");
  if (NAV.find(([id]) => id === v)) setView(v);
});

init();
