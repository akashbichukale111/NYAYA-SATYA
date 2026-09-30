import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import ReactFlow, { Background, Controls, MiniMap, type Edge, type Node } from "reactflow";
import "reactflow/dist/style.css";
import { api, type NodeOut } from "../lib/api";
import { useCaseContext } from "../lib/case-context";
import { EmptyState, ErrorState, LoadingState, Panel, StatusPill } from "../components/ui";

const COLUMN_ORDER = [
  "DOCUMENT", "EVIDENCE", "CLAIM", "ISSUE", "OBLIGATION", "DEADLINE",
  "HEARING", "ORDER", "FILING_PACKAGE", "REGISTRY_DEFECT", "CUSTODY_EVENT",
  "WORKFLOW", "ACTION", "VERIFICATION",
];

const STATUS_BORDER: Record<string, string> = {
  VERIFIED: "#10b981",
  UNVERIFIED: "#f59e0b",
  CONFLICTING: "#f87171",
  BLOCKED: "#dc2626",
  SUPERSEDED: "#a855f7",
  MISSING: "#ef4444",
  REQUIRES_HUMAN_REVIEW: "#fbbf24",
};

export default function CaseGraphPage() {
  const { caseId } = useCaseContext();
  const [selected, setSelected] = useState<NodeOut | null>(null);

  const graphQuery = useQuery({
    queryKey: ["graph", caseId],
    queryFn: () => api.getGraph(caseId!),
    enabled: !!caseId,
  });

  const { nodes, edges } = useMemo(() => {
    if (!graphQuery.data) return { nodes: [] as Node[], edges: [] as Edge[] };
    const byColumn: Record<string, NodeOut[]> = {};
    for (const n of graphQuery.data.nodes) {
      (byColumn[n.node_type] ??= []).push(n);
    }
    const flowNodes: Node[] = [];
    COLUMN_ORDER.forEach((type, colIdx) => {
      (byColumn[type] ?? []).forEach((n, rowIdx) => {
        flowNodes.push({
          id: n.id,
          position: { x: colIdx * 220, y: rowIdx * 110 },
          data: { label: n.label, node: n },
          style: {
            background: "#111827",
            color: "#e2e8f0",
            border: `2px solid ${STATUS_BORDER[n.status] ?? "#334155"}`,
            borderRadius: 8,
            fontSize: 12,
            width: 190,
          },
        });
      });
    });
    const flowEdges: Edge[] = graphQuery.data.relationships.map((r) => ({
      id: r.id,
      source: r.source_id,
      target: r.target_id,
      label: r.rel_type,
      labelStyle: { fill: "#94a3b8", fontSize: 9 },
      style: { stroke: "#334155" },
      animated: r.rel_type === "BLOCKS" || r.rel_type === "CONTRADICTS",
    }));
    return { nodes: flowNodes, edges: flowEdges };
  }, [graphQuery.data]);

  if (!caseId) return <EmptyState message="Select a case from the Command Center first." />;

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-xl font-semibold text-slate-100">Case Graph</h1>
        <p className="mt-1 text-sm text-slate-500">Columns are node types; edges are dependency relationships.</p>
      </div>

      {graphQuery.isLoading && <LoadingState />}
      {graphQuery.isError && <ErrorState message={(graphQuery.error as Error).message} />}

      {graphQuery.data && (
        <div className="grid grid-cols-3 gap-4">
          <div className="col-span-2 h-[560px] rounded-lg border border-brand-border bg-brand-panel/40">
            <ReactFlow
              nodes={nodes}
              edges={edges}
              fitView
              onNodeClick={(_, node) => setSelected((node.data as { node: NodeOut }).node)}
              proOptions={{ hideAttribution: true }}
            >
              <Background color="#1f2937" gap={16} />
              <Controls />
              <MiniMap pannable zoomable style={{ background: "#0b0f17" }} nodeColor="#334155" />
            </ReactFlow>
          </div>
          <Panel title="Node inspector">
            {!selected && <EmptyState message="Click a node to inspect it." />}
            {selected && (
              <div className="flex flex-col gap-2 text-sm">
                <p className="font-semibold text-slate-100">{selected.label}</p>
                <p className="text-xs text-slate-500">{selected.node_type}</p>
                <div>
                  <StatusPill status={selected.status} />
                </div>
                {selected.provenance_ref && (
                  <p className="text-xs text-slate-500">Provenance: {selected.provenance_ref}</p>
                )}
                {Object.keys(selected.attributes ?? {}).length > 0 && (
                  <pre className="mt-2 max-h-64 overflow-auto rounded bg-brand-bg p-2 text-xs text-slate-400">
                    {JSON.stringify(selected.attributes, null, 2)}
                  </pre>
                )}
              </div>
            )}
          </Panel>
        </div>
      )}
    </div>
  );
}
