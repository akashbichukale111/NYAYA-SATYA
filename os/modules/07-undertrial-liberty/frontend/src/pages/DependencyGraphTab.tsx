import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import ReactFlow, { Background, Controls, MarkerType, type Edge, type Node } from "reactflow";
import "reactflow/dist/style.css";
import { CasesAPI } from "../api/client";
import { Loading, ErrorBox, SectionTitle, EmptyState } from "../components/Primitives";

const STATUS_COLOR: Record<string, string> = {
  SATISFIED: "#3fae6a",
  BLOCKED: "#c25a4d",
  UNKNOWN: "#8a8578",
};

/**
 * Lays nodes out in simple left-to-right lanes by entity type, since the
 * dependency graph is a DAG-ish structure (Document -> Event -> CustodyState
 * -> Hearing -> Order -> AttentionItem, plus cross-links). This keeps the
 * graph readable without pulling in a full auto-layout library for a
 * lean first build.
 */
const LANE_ORDER = [
  "Document", "CustodyEvent", "CustodyState", "Hearing", "BailEvent",
  "Order", "ReleaseRelatedEvent", "Conflict", "AttentionItem",
];

function laneIndex(entityType: string) {
  const i = LANE_ORDER.indexOf(entityType);
  return i === -1 ? LANE_ORDER.length : i;
}

export default function DependencyGraphTab({ caseId }: { caseId: string }) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["dependency-graph", caseId],
    queryFn: () => CasesAPI.dependencyGraph(caseId),
  });

  const { nodes, edges } = useMemo(() => {
    if (!data?.edges) return { nodes: [] as Node[], edges: [] as Edge[] };
    const nodeMap = new Map<string, Node>();
    const laneCounts: Record<number, number> = {};

    const ensureNode = (type: string, id: string) => {
      const key = `${type}:${id}`;
      if (nodeMap.has(key)) return key;
      const lane = laneIndex(type);
      const row = laneCounts[lane] ?? 0;
      laneCounts[lane] = row + 1;
      nodeMap.set(key, {
        id: key,
        position: { x: lane * 220, y: row * 90 },
        data: { label: `${type}\n${id.slice(0, 14)}${id.length > 14 ? "…" : ""}` },
        style: {
          fontSize: 11,
          whiteSpace: "pre-line",
          border: "1px solid var(--color-border)",
          background: "var(--color-surface-raised)",
          color: "var(--color-text-primary)",
          borderRadius: 8,
          padding: 8,
          width: 170,
        },
      });
      return key;
    };

    const flowEdges: Edge[] = data.edges.map((e: any, i: number) => {
      const from = ensureNode(e.from_entity_type, e.from_entity_id);
      const to = ensureNode(e.to_entity_type, e.to_entity_id);
      return {
        id: `e${i}`,
        source: from,
        target: to,
        label: e.dependency_type.replace(/_/g, " ").toLowerCase(),
        animated: e.status === "BLOCKED",
        style: { stroke: STATUS_COLOR[e.status] || "#8a8578" },
        markerEnd: { type: MarkerType.ArrowClosed, color: STATUS_COLOR[e.status] || "#8a8578" },
        labelStyle: { fontSize: 9, fill: "var(--color-text-secondary)" },
      };
    });

    return { nodes: Array.from(nodeMap.values()), edges: flowEdges };
  }, [data]);

  if (isLoading) return <Loading />;
  if (isError || !data) return <ErrorBox message="Could not load dependency graph." />;

  return (
    <div className="card p-5">
      <SectionTitle subtitle="Document → Event → Custody State → Hearing → Order → Attention Item, with provenance on every edge. Red/dashed edges are BLOCKED.">
        Dependency Graph
      </SectionTitle>
      {edges.length === 0 ? (
        <EmptyState label="No dependency edges yet. Upload a document to build the graph." />
      ) : (
        <div style={{ height: 520 }} className="rounded-lg border border-[color:var(--color-border)] overflow-hidden">
          <ReactFlow nodes={nodes} edges={edges} fitView proOptions={{ hideAttribution: true }}>
            <Background gap={16} color="var(--color-border)" />
            <Controls showInteractive={false} />
          </ReactFlow>
        </div>
      )}
      <div className="mt-3 flex gap-4 text-xs text-[color:var(--color-text-secondary)]">
        <span><span style={{ color: STATUS_COLOR.SATISFIED }}>●</span> Satisfied</span>
        <span><span style={{ color: STATUS_COLOR.BLOCKED }}>●</span> Blocked</span>
        <span><span style={{ color: STATUS_COLOR.UNKNOWN }}>●</span> Unknown</span>
      </div>
    </div>
  );
}
