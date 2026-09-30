import { useMemo, useCallback, useState } from 'react'
import ReactFlow, {
  Background, Controls, MiniMap, type Node, type Edge, type NodeMouseHandler,
  Position, MarkerType,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { useDependencyGraph } from '../hooks'
import { SectionHeading, LoadingState, ErrorState, EmptyState, Card } from '../components/primitives'
import { EvidenceDetailPanel } from '../components/EvidenceDetailPanel'
import { ClaimDetailPanel } from '../components/ClaimDetailPanel'

const COLUMN_X: Record<string, number> = { EVIDENCE: 40, CLAIM: 360, ISSUE: 680 }
const TYPE_COLOR: Record<string, string> = {
  EVIDENCE: '#4a5570', CLAIM: '#b8862b', ISSUE: '#2e7d5b',
}

export function DependencyGraphView({ caseId }: { caseId: string }) {
  const graph = useDependencyGraph(caseId)
  const [selected, setSelected] = useState<{ id: string; type: string } | null>(null)
  const [filterType, setFilterType] = useState<'ALL' | 'EVIDENCE' | 'CLAIM' | 'ISSUE'>('ALL')

  const { nodes, edges } = useMemo(() => {
    if (!graph.data) return { nodes: [] as Node[], edges: [] as Edge[] }
    const columnCounts: Record<string, number> = { EVIDENCE: 0, CLAIM: 0, ISSUE: 0 }
    const visibleNodeIds = new Set(
      graph.data.nodes.filter((n) => filterType === 'ALL' || n.type === filterType).map((n) => n.id)
    )

    const flowNodes: Node[] = graph.data.nodes
      .filter((n) => filterType === 'ALL' || n.type === filterType)
      .map((n) => {
        const row = columnCounts[n.type]++
        return {
          id: n.id,
          position: { x: COLUMN_X[n.type], y: row * 90 + 20 },
          data: { label: n.label.length > 60 ? n.label.slice(0, 57) + '…' : n.label, nodeType: n.type },
          sourcePosition: Position.Right,
          targetPosition: Position.Left,
          style: {
            border: `1px solid ${TYPE_COLOR[n.type]}88`,
            background: '#111520',
            color: '#f3efe6',
            borderRadius: 8,
            padding: 8,
            fontSize: 12,
            width: 260,
          },
        }
      })

    const flowEdges: Edge[] = graph.data.edges
      .filter((e) => visibleNodeIds.has(e.source) && visibleNodeIds.has(e.target))
      .map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        label: e.relationship_type,
        animated: e.relationship_type === 'CONTRADICTS',
        style: { stroke: e.relationship_type === 'CONTRADICTS' ? '#a13d3d' : '#4a5570' },
        labelStyle: { fill: '#f3efe6', fontSize: 10 },
        labelBgStyle: { fill: '#0b0e14' },
        markerEnd: { type: MarkerType.ArrowClosed, color: e.relationship_type === 'CONTRADICTS' ? '#a13d3d' : '#4a5570' },
      }))

    return { nodes: flowNodes, edges: flowEdges }
  }, [graph.data, filterType])

  const onNodeClick: NodeMouseHandler = useCallback((_evt, node) => {
    const nodeType = (node.data as { nodeType: string }).nodeType
    setSelected({ id: node.id, type: nodeType })
  }, [])

  return (
    <div className="space-y-4">
      <SectionHeading title="Dependency Graph" subtitle="Evidence → Claim → Issue, and lateral relationships, built from real data." />

      <div className="flex items-center gap-2">
        {(['ALL', 'EVIDENCE', 'CLAIM', 'ISSUE'] as const).map((t) => (
          <button
            key={t}
            onClick={() => setFilterType(t)}
            className={`focus-ring rounded-full px-3 py-1 text-xs ${
              filterType === t ? 'bg-parchment-200 text-ink-950' : 'border border-ink-600 text-parchment-200/70 hover:border-ink-500'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {graph.isLoading && <LoadingState />}
      {graph.isError && <ErrorState error={graph.error} />}
      {graph.data && graph.data.nodes.length === 0 && (
        <EmptyState title="Nothing to graph yet." hint="Add evidence, claims, issues, and relationships (or run the extraction pipeline)." />
      )}

      {graph.data && graph.data.nodes.length > 0 && (
        <div className="grid gap-4 lg:grid-cols-[1fr_380px]">
          <div className="h-[560px] overflow-hidden rounded-lg border border-ink-700 bg-ink-950">
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodeClick={onNodeClick}
              fitView
              proOptions={{ hideAttribution: true }}
            >
              <Background color="#232a3d" gap={20} />
              <Controls />
              <MiniMap
                nodeColor={(n) => TYPE_COLOR[(n.data as { nodeType: string })?.nodeType] ?? '#4a5570'}
                maskColor="#0b0e14cc"
                style={{ background: '#111520' }}
              />
            </ReactFlow>
          </div>
          <div>
            {selected ? (
              selected.type === 'EVIDENCE' ? (
                <EvidenceDetailPanel evidenceId={selected.id} caseId={caseId} />
              ) : selected.type === 'CLAIM' ? (
                <ClaimDetailPanel claimId={selected.id} />
              ) : (
                <IssueInspector />
              )
            ) : (
              <Card><EmptyState title="Click a node" hint="Evidence, claim, or issue detail will appear here." /></Card>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function IssueInspector() {
  return (
    <Card>
      <h3 className="mb-2 text-xs font-medium uppercase tracking-wider text-parchment-200/40">Issue</h3>
      <p className="text-xs text-parchment-200/50">
        Issues are terminal nodes in the dependency graph — inspect the claims feeding into them from this graph view
        or from the Issues screen.
      </p>
    </Card>
  )
}
