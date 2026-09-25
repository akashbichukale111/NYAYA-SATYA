"""Case Digital Twin Master Builder for NYAYA-SATYA.

Assembles:
1. Physical / Factual World (Entities, Timeline Events)
2. Evidence World (SafeEvidenceRef, Provenance, Content Hashes)
3. Legal Reasoning World (Claims, Issues, Dependencies)
4. Contradictions & Temporal Conflicts
5. Deterministic Integrity Hash & Validation
"""

from __future__ import annotations

import uuid
from typing import Any

from nyaya_evidence.contradiction.engine import ContradictionCandidate
from nyaya_evidence.contracts.evidence import EvidenceItem
from nyaya_evidence.tarka_integration.safe_refs import SafeEvidenceRef
from nyaya_twin.builders.claim_builder import ClaimBuilder
from nyaya_twin.builders.entity_builder import EntityBuilder
from nyaya_twin.builders.timeline_builder import TimelineBuilder
from nyaya_twin.contracts.case_twin import CaseDigitalTwin, compute_twin_hash
from nyaya_twin.contracts.claims import Claim
from nyaya_twin.contracts.entities import Entity
from nyaya_twin.contracts.events import TimelineEvent
from nyaya_twin.contracts.issues import Issue
from nyaya_twin.contracts.relationships import CaseRelationship, RelationshipType
from nyaya_twin.graph.timeline_graph import TimelineGraph
from nyaya_twin.validation.graph_validator import validate_case_graph


class CaseTwinBuilder:
    """Master builder for constructing and updating a Case Digital Twin."""

    def __init__(self, case_id: str, twin_id: str | None = None) -> None:
        self.case_id = case_id
        self.twin_id = twin_id or f"twin_{case_id}_{uuid.uuid4().hex[:6]}"
        self.entity_builder = EntityBuilder(case_id)
        self.claim_builder = ClaimBuilder(case_id)
        self.timeline_builder = TimelineBuilder(case_id)

        self._issues: dict[str, Issue] = {}
        self._evidence_refs: dict[str, SafeEvidenceRef] = {}
        self._relationships: dict[str, CaseRelationship] = {}
        self._contradictions: list[ContradictionCandidate] = []
        self._unresolved_items: list[str] = []

    def add_issue(
        self,
        *,
        title: str,
        issue_id: str | None = None,
        description: str = "",
        related_claim_ids: list[str] | None = None,
        related_evidence_ids: list[str] | None = None,
        unresolved_questions: list[str] | None = None,
    ) -> Issue:
        if issue_id is None:
            issue_id = f"iss_{uuid.uuid4().hex[:8]}"

        issue = Issue(
            issue_id=issue_id,
            case_id=self.case_id,
            title=title.strip(),
            description=description.strip(),
            related_claim_ids=list(related_claim_ids or []),
            related_evidence_ids=list(related_evidence_ids or []),
            unresolved_questions=list(unresolved_questions or []),
        )
        self._issues[issue.issue_id] = issue
        return issue

    def add_evidence_ref(self, ref: SafeEvidenceRef) -> None:
        if ref.case_id != self.case_id:
            raise ValueError(
                f"Cross-case contamination: evidence {ref.evidence_id} belongs to case {ref.case_id}, expected {self.case_id}"
            )
        self._evidence_refs[ref.evidence_id] = ref

    def add_relationship(
        self,
        *,
        source_id: str,
        source_type: str,
        target_id: str,
        target_type: str,
        relationship_type: RelationshipType,
        relationship_id: str | None = None,
        weight: float = 1.0,
        metadata: dict[str, Any] | None = None,
    ) -> CaseRelationship:
        if relationship_id is None:
            relationship_id = f"rel_{source_id}_{relationship_type.value.lower()}_{target_id}_{uuid.uuid4().hex[:4]}"

        rel = CaseRelationship(
            relationship_id=relationship_id,
            case_id=self.case_id,
            source_id=source_id,
            source_type=source_type,
            target_id=target_id,
            target_type=target_type,
            relationship_type=relationship_type,
            weight=weight,
            metadata=dict(metadata or {}),
        )
        self._relationships[rel.relationship_id] = rel
        return rel

    def add_contradiction(self, contradiction: ContradictionCandidate) -> None:
        if contradiction.case_id != self.case_id:
            raise ValueError(
                f"Cross-case contamination: contradiction {contradiction.contradiction_id} belongs to {contradiction.case_id}"
            )
        self._contradictions.append(contradiction)

    def add_unresolved_item(self, item: str) -> None:
        if item and item.strip() not in self._unresolved_items:
            self._unresolved_items.append(item.strip())

    def build(
        self,
        *,
        evidence_items: dict[str, EvidenceItem] | None = None,
    ) -> CaseDigitalTwin:
        """Assembles and validates the CaseDigitalTwin."""
        entities = self.entity_builder.get_entities()
        claims = self.claim_builder.get_claims()
        events = self.timeline_builder.get_events()

        # Detect temporal conflicts automatically
        tg = TimelineGraph(self.case_id)
        for ev in events.values():
            tg.add_event(ev)
        temporal_conflicts = tg.detect_temporal_conflicts()

        # Aggregate unresolved items
        unresolved = list(self._unresolved_items)
        for cand in self._contradictions:
            unresolved.append(f"Evidence contradiction between {cand.evidence_a_id} and {cand.evidence_b_id} ({cand.contradiction_type.value})")
        for tc in temporal_conflicts:
            unresolved.append(f"Temporal conflict between {tc['event_a_id']} and {tc['event_b_id']} ({tc['date_a']} vs {tc['date_b']})")

        twin = CaseDigitalTwin(
            twin_id=self.twin_id,
            case_id=self.case_id,
            version=1,
            entities=entities,
            claims=claims,
            issues=self._issues,
            events=events,
            evidence_refs=self._evidence_refs,
            relationships=self._relationships,
            contradictions=list(self._contradictions),
            temporal_conflicts=temporal_conflicts,
            unresolved_items=sorted(set(unresolved)),
            source_version="3.0.0",
        )

        # Validate graph integrity
        validation_result = validate_case_graph(twin, evidence_items=evidence_items)
        twin.graph_integrity = validation_result.to_dict()

        return twin
