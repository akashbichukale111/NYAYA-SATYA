"""Twin adapter for NYAYA-SATYA Causal Reasoning.

Maps CaseDigitalTwin structures into the causal graph.
Reuses existing twin contracts without duplication.
"""

from __future__ import annotations

from typing import Any

from nyaya_causal.contracts.causal_edge import CausalEdge, CausalRelationshipType
from nyaya_causal.contracts.causal_node import CausalNode, CausalNodeType
from nyaya_causal.graph.causal_graph import CausalGraph
from nyaya_twin.contracts.case_twin import CaseDigitalTwin
from nyaya_twin.contracts.relationships import RelationshipType

# Map twin RelationshipType to CausalRelationshipType
_RELATIONSHIP_MAP: dict[RelationshipType, CausalRelationshipType] = {
    RelationshipType.DEPENDS_ON: CausalRelationshipType.DEPENDS_ON,
    RelationshipType.SUPPORTS: CausalRelationshipType.SUPPORTS,
    RelationshipType.CONTRADICTS: CausalRelationshipType.CONTRADICTS,
    RelationshipType.CORROBORATES: CausalRelationshipType.SUPPORTS,
    RelationshipType.CHALLENGES: CausalRelationshipType.CONTRADICTS,
}


class TwinToCausalAdapter:
    """Adapts CaseDigitalTwin into a CausalGraph."""

    def build_causal_graph(self, twin: CaseDigitalTwin) -> CausalGraph:
        """Build a causal graph from the twin's nodes and relationships."""
        graph = CausalGraph(case_id=twin.case_id)

        # Add claims as nodes
        for cid, claim in twin.claims.items():
            node = CausalNode(
                node_id=cid,
                case_id=twin.case_id,
                node_type=CausalNodeType.CLAIM,
                label=claim.statement,
                twin_reference_id=cid,
            )
            graph.add_node(node)

        # Add events as nodes
        for eid, event in twin.events.items():
            node = CausalNode(
                node_id=eid,
                case_id=twin.case_id,
                node_type=CausalNodeType.EVENT,
                label=event.title,
                twin_reference_id=eid,
            )
            graph.add_node(node)

        # Add evidence as nodes
        for evid, ev_ref in twin.evidence_refs.items():
            node = CausalNode(
                node_id=evid,
                case_id=twin.case_id,
                node_type=CausalNodeType.EVIDENCE,
                label=f"Evidence {evid}",
                twin_reference_id=evid,
            )
            graph.add_node(node)

        # Add issues as nodes
        for iid, issue in twin.issues.items():
            node = CausalNode(
                node_id=iid,
                case_id=twin.case_id,
                node_type=CausalNodeType.ISSUE,
                label=issue.title,
                twin_reference_id=iid,
            )
            graph.add_node(node)

        # Add edges from twin relationships
        for rid, rel in twin.relationships.items():
            causal_type = _RELATIONSHIP_MAP.get(rel.relationship_type)
            if causal_type is None:
                continue  # Skip unmapped types

            # Only add edge if both endpoints exist
            if rel.source_id not in graph.nodes or rel.target_id not in graph.nodes:
                continue

            try:
                edge = CausalEdge(
                    edge_id=rid,
                    case_id=twin.case_id,
                    source_node_id=rel.source_id,
                    target_node_id=rel.target_id,
                    relationship_type=causal_type,
                    causal_basis=f"Derived from twin relationship {rid} ({rel.relationship_type.value})",
                )
                graph.add_edge(edge)
            except (ValueError, Exception):
                pass  # Skip edges that would create cycles or are invalid

        return graph
