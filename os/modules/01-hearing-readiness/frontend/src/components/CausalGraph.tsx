import { useMemo } from "react";
import ReactFlow, { Background, Controls, MarkerType, type Edge, type Node } from "reactflow";
import "reactflow/dist/style.css";
import type { Graph } from "../lib/api";

const COLUMN_ORDER = ["HEARING", "REQUIREMENT", "EVIDENCE", "BLOCKER", "ACTOR", "ACTION", "VERIFICATION", "STATE"];
const COLUMN_COLOR: Record<string, string> = {
  HEARING: "#5b8def",
  REQUIREMENT: "#9AA4B3",
  EVIDENCE: "#c89b3c",
  BLOCKER: "#c1443c",
  ACTOR: "#3fa34d",
  ACTION: "#d9b563",
  VERIFICATION: "#5b8def",
  STATE: "#9AA4B3",
};

function shortLabel(type: string, id: string): string {
  if (type === "ACTOR") return id; // actor ids are free-text names, not opaque ids
  return `${type}\n${id.slice(0, 14)}`;
}

export function CausalGraph({ graph, highlightId }: { graph: Graph; highlightId?: string }) {
  const { nodes, edges } = useMemo<{ nodes: Node[]; edges: Edge[] }>(() => {
    const columns: Record<string, string[]> = {};
    for (const n of graph.nodes) {
      const col = COLUMN_ORDER.includes(n.type) ? n.type : "STATE";
      columns[col] = columns[col] || [];
      columns[col].push(n.id);
    }

    const nodes: Node[] = [];
    COLUMN_ORDER.forEach((type, colIdx) => {
      (columns[type] || []).forEach((id, rowIdx) => {
        const isHighlighted = id === highlightId;
        nodes.push({
          id: `${type}:${id}`,
          position: { x: colIdx * 190, y: rowIdx * 90 },
          data: { label: shortLabel(type, id) },
          style: {
            background: isHighlighted ? COLUMN_COLOR[type] : "#161c25",
            color: isHighlighted ? "#0b0e13" : "#e9ecf1",
            border: `1px solid ${COLUMN_COLOR[type]}`,
            borderRadius: 8,
            fontSize: 11,
            padding: 8,
            width: 170,
            whiteSpace: "pre-line",
          },
        });
      });
    });

    const edges: Edge[] = graph.edges.map((e) => ({
      id: e.id,
      source: `${e.from.type}:${e.from.id}`,
      target: `${e.to.type}:${e.to.id}`,
      label: undefined,
      animated: false,
      style: { stroke: "#2b3644" },
      markerEnd: { type: MarkerType.ArrowClosed, color: "#2b3644" },
    }));

    return { nodes, edges };
  }, [graph, highlightId]);

  if (nodes.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center rounded-md border border-dashed border-[var(--hairline)] text-sm text-[var(--text-muted)]">
        No dependency edges yet for this case — run a readiness audit first.
      </div>
    );
  }

  return (
    <div style={{ height: 420 }} className="rounded-md border border-[var(--hairline)] bg-[var(--ink-950)]">
      <ReactFlow nodes={nodes} edges={edges} fitView proOptions={{ hideAttribution: true }}>
        <Background color="#1f2733" gap={20} />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
