"""Case Multi-Graph for NYAYA-SATYA Case Digital Twin.

Integrates:
- Entities (Physical / Factual World)
- Evidence (Evidence World via SafeEvidenceRef)
- Claims, Issues & Dependencies (Legal Reasoning World)
- Timeline Events (Temporal Dimension)
"""

from __future__ import annotations

from typing import Any

from nyaya_evidence.contradiction.engine import ContradictionCandidate
from nyaya_evidence.tarka_integration.safe_refs import SafeEvidenceRef
from nyaya_twin.contracts.claims import Claim
from nyaya_twin.contracts.entities import Entity
from nyaya_twin.contracts.events import TimelineEvent
from nyaya_twin.contracts.issues import Issue
from nyaya_twin.contracts.relationships import CaseRelationship, RelationshipType
from nyaya_twin.graph.claim_graph import ClaimGraph
from nyaya_twin.graph.evidence_graph import EvidenceGraph
from nyaya_twin.graph.timeline_graph import TimelineGraph


class CaseGraph:
    """Unified multimodal graph representing the complete Case Digital Twin."""

    def __init__(self, case_id: str) -> None:
        self.case_id = case_id
        self.entities: dict[str, Entity] = {}
        self.claims: dict[str, Claim] = {}
        self.issues: dict[str, Issue] = {}
        self.events: dict[str, TimelineEvent] = {}
        self.evidence_refs: dict[str, SafeEvidenceRef] = {}
        self.relationships: dict[str, CaseRelationship] = {}
        self.contradictions: list[ContradictionCandidate] = []

        # Subgraphs
        self.claim_graph = ClaimGraph(case_id)
        self.evidence_graph = EvidenceGraph(case_id)
        self.timeline_graph = TimelineGraph(case_id)

    def add_entity(self, entity: Entity) -> None:
        if entity.case_id != self.case_id:
            raise ValueError(f"Cross-case contamination: entity {entity.entity_id} belongs to {entity.case_id}, expected {self.case_id}")
        self.entities[entity.entity_id] = entity

    def add_claim(self, claim: Claim) -> None:
        if claim.case_id != self.case_id:
            raise ValueError(f"Cross-case contamination: claim {claim.claim_id} belongs to {claim.case_id}, expected {self.case_id}")
        self.claims[claim.claim_id] = claim
        self.claim_graph.add_claim(claim)
        self.evidence_graph.register_claim(claim.claim_id)

    def add_issue(self, issue: Issue) -> None:
        if issue.case_id != self.case_id:
            raise ValueError(f"Cross-case contamination: issue {issue.issue_id} belongs to {issue.case_id}, expected {self.case_id}")
        self.issues[issue.issue_id] = issue

    def add_event(self, event: TimelineEvent) -> None:
        if event.case_id != self.case_id:
            raise ValueError(f"Cross-case contamination: event {event.event_id} belongs to {event.case_id}, expected {self.case_id}")
        self.events[event.event_id] = event
        self.timeline_graph.add_event(event)

    def add_evidence_ref(self, ref: SafeEvidenceRef) -> None:
        if ref.case_id != self.case_id:
            raise ValueError(f"Cross-case contamination: evidence {ref.evidence_id} belongs to {ref.case_id}, expected {self.case_id}")
        self.evidence_refs[ref.evidence_id] = ref
        self.evidence_graph.add_evidence_ref(ref)

    def add_relationship(self, rel: CaseRelationship) -> None:
        if rel.case_id != self.case_id:
            raise ValueError(f"Cross-case contamination: relationship {rel.relationship_id} belongs to {rel.case_id}, expected {self.case_id}")
        if rel.relationship_id in self.relationships:
            raise ValueError(f"Duplicate relationship_id: {rel.relationship_id}")
        self.relationships[rel.relationship_id] = rel

        # Route to appropriate subgraph
        if rel.relationship_type in (
            RelationshipType.SUPPORTS,
            RelationshipType.CONTRADICTS,
            RelationshipType.MENTIONS,
            RelationshipType.DERIVED_FROM,
            RelationshipType.QUALIFIES,
            RelationshipType.REFUTES,
        ):
            self.evidence_graph.add_relationship(rel)
        elif rel.relationship_type in (
            RelationshipType.DEPENDS_ON,
            RelationshipType.CORROBORATES,
            RelationshipType.CHALLENGES,
            RelationshipType.SUBMITTED_UNDER,
            RelationshipType.RELEVANT_TO,
        ):
            self.claim_graph.add_relationship(rel)

    def add_contradiction(self, candidate: ContradictionCandidate) -> None:
        if candidate.case_id != self.case_id:
            raise ValueError(f"Cross-case contamination: contradiction {candidate.contradiction_id} belongs to {candidate.case_id}")
        self.contradictions.append(candidate)
