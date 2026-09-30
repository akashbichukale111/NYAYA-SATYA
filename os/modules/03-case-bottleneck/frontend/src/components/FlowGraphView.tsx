import type { FlowGraph as FlowGraphData } from "../types/domain";

const STATUS_COLOR: Record<string, string> = {
  SATISFIED: "var(--confirmed)",
  UNSATISFIED: "var(--high)",
  UNKNOWN: "var(--unknown)",
  CONTRADICTED: "var(--critical)",
  PENDING: "var(--high)",
  READY: "var(--confirmed)",
  COMPLETED: "var(--confirmed)",
};

/** A small, deterministic layered layout — transitions on the left, the
 * dependencies that gate them on the right, connected by straight edges.
 * This is intentionally NOT a force-directed / auto-layout graph library
 * (Section 63 lists React Flow as an option): for the case sizes this
 * system handles (tens of nodes, not thousands — see graph.py docstring),
 * a plain deterministic SVG is simpler, has zero extra dependencies, and
 * is easier to keep visually stable between re-renders. Documented as a
 * scope simplification, same as the backend's graph engine. */
export function FlowGraphView({ graph }: { graph: FlowGraphData }) {
  const transitions = graph.nodes.filter((n) => n.kind === "transition");
  const dependencies = graph.nodes.filter((n) => n.kind === "dependency");

  const rowHeight = 64;
  const width = 720;
  const leftX = 140;
  const rightX = width - 160;
  const height = Math.max(transitions.length, dependencies.length) * rowHeight + 40;

  const posOf: Record<string, { x: number; y: number }> = {};
  transitions.forEach((n, i) => (posOf[n.id] = { x: leftX, y: 40 + i * rowHeight }));
  dependencies.forEach((n, i) => (posOf[n.id] = { x: rightX, y: 40 + i * rowHeight }));

  if (graph.nodes.length === 0) {
    return <div className="empty-state">No flow graph data for this case yet.</div>;
  }

  return (
    <div className="flow-graph">
      <svg width={width} height={height} role="img" aria-label="Case flow dependency graph">
        {graph.edges.map((e, i) => {
          const a = posOf[e.from];
          const b = posOf[e.to];
          if (!a || !b) return null;
          return (
            <path
              key={i}
              className="flow-edge"
              d={`M ${a.x + 60} ${a.y} C ${(a.x + b.x) / 2} ${a.y}, ${(a.x + b.x) / 2} ${b.y}, ${b.x - 70} ${b.y}`}
            />
          );
        })}
        {[...transitions, ...dependencies].map((n) => {
          const p = posOf[n.id];
          if (!p) return null;
          const color = STATUS_COLOR[n.status] || "var(--text-dim)";
          const isTransition = n.kind === "transition";
          return (
            <g key={n.id} transform={`translate(${p.x}, ${p.y})`}>
              <rect
                x={isTransition ? -60 : -70}
                y={-18}
                width={isTransition ? 120 : 140}
                height={36}
                rx={8}
                fill="var(--bg-inset)"
                stroke={color}
                strokeWidth={1.5}
              />
              <circle cx={isTransition ? -52 : -62} cy={0} r={4} fill={color} />
              <text x={isTransition ? -40 : -50} y={-2} className="flow-node-label">
                {truncate(n.description, 20)}
              </text>
              <text x={isTransition ? -40 : -50} y={12} className="flow-node-sub">
                {n.kind === "transition" ? n.status : `${n.type} · ${n.status}`}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

function truncate(s: string, n: number) {
  return s.length > n ? s.slice(0, n - 1) + "…" : s;
}
